"""T2: LadybugDB Schema and Basic Operations."""

import pytest

from tools.local_store.graph_store import GraphStore, make_global_id


class TestT2GraphStore:
    """Test graph database operations with our CX2-oriented schema."""

    def test_t2_1_schema_creation(self, graph_store):
        """T2.1: Create BioNode, Network, Interacts, InNetwork tables."""
        rows = graph_store.execute("MATCH (n:BioNode) RETURN count(n)")
        assert rows[0][0] == 0
        rows = graph_store.execute("MATCH (n:Network) RETURN count(n)")
        assert rows[0][0] == 0

    def test_t2_2_insert_node_with_map(self, graph_store):
        """T2.2: Insert a single BioNode with MAP properties."""
        graph_store.add_node(
            node_id=1,
            network_uuid="net-1",
            name="TRIM25",
            node_type="protein",
            properties={"function": "p", "organism": "human"},
        )
        rows = graph_store.execute(
            "MATCH (n:BioNode {name: 'TRIM25'}) RETURN n.name, n.properties"
        )
        assert rows[0][0] == "TRIM25"
        assert rows[0][1]["function"] == "p"

    def test_t2_3_insert_edge(self, graph_store):
        """T2.3: Insert two BioNodes, create Interacts edge."""
        graph_store.add_node(1, "net-1", name="A")
        graph_store.add_node(2, "net-1", name="B")
        graph_store.add_edge(1, 2, edge_id=0, network_uuid="net-1", interaction="increases")

        rows = graph_store.execute(
            "MATCH (a:BioNode)-[r:Interacts]->(b:BioNode) RETURN a.name, r.interaction, b.name"
        )
        assert len(rows) == 1
        assert rows[0] == ["A", "increases", "B"]

    def test_t2_4_network_membership(self, graph_store):
        """T2.4: Insert Network node, create InNetwork edges for BioNodes."""
        graph_store.add_network(uuid="net-1", name="Test Network")
        graph_store.add_node(1, "net-1", name="A")
        graph_store.add_node(2, "net-1", name="B")
        graph_store.link_node_to_network(1, "net-1")
        graph_store.link_node_to_network(2, "net-1")

        rows = graph_store.execute(
            "MATCH (n:BioNode)-[:InNetwork]->(net:Network {uuid: 'net-1'}) RETURN n.name"
        )
        names = sorted(r[0] for r in rows)
        assert names == ["A", "B"]

    def test_t2_5_return_all_nodes(self, graph_store):
        """T2.5: MATCH (n:BioNode) RETURN n.name — verify all nodes returned."""
        for i in range(5):
            graph_store.add_node(i, "net-1", name=f"Node{i}")
        rows = graph_store.execute("MATCH (n:BioNode) RETURN n.name")
        assert len(rows) == 5

    def test_t2_6_neighborhood_query(self, graph_store):
        """T2.6: Neighborhood query — find neighbors of a specific node."""
        graph_store.add_node(0, "net-1", name="TRIM25")
        graph_store.add_node(1, "net-1", name="RIG-I")
        graph_store.add_node(2, "net-1", name="NS1")
        graph_store.add_node(3, "net-1", name="Unrelated")
        graph_store.add_edge(0, 1, 0, "net-1", "increases")
        graph_store.add_edge(2, 0, 1, "net-1", "decreases")

        rows = graph_store.execute(
            "MATCH (n:BioNode {name: 'TRIM25'})-[r:Interacts]-(m:BioNode) RETURN m.name, r.interaction"
        )
        neighbor_names = sorted(r[0] for r in rows)
        assert neighbor_names == ["NS1", "RIG-I"]

    def test_t2_7_network_membership_query(self, graph_store):
        """T2.7: Query nodes belonging to a specific network."""
        graph_store.add_network("net-1", name="Net1")
        graph_store.add_network("net-2", name="Net2")
        graph_store.add_node(0, "net-1", name="A")
        graph_store.add_node(1, "net-2", name="B")
        graph_store.link_node_to_network(0, "net-1")
        graph_store.link_node_to_network(1, "net-2")

        rows = graph_store.execute(
            "MATCH (n:BioNode)-[:InNetwork]->(net:Network {uuid: 'net-1'}) RETURN n.name"
        )
        assert len(rows) == 1
        assert rows[0][0] == "A"

    def test_t2_8_update_properties(self, graph_store):
        """T2.8: Update a node's properties MAP via SET."""
        graph_store.add_node(1, "net-1", name="A", properties={"k1": "v1"})
        graph_store.execute(
            "MATCH (n:BioNode {name: 'A'}) "
            "SET n.properties = map(['k1','k2'], ['updated','new'])"
        )
        rows = graph_store.execute(
            "MATCH (n:BioNode {name: 'A'}) RETURN n.properties"
        )
        assert rows[0][0] == {"k1": "updated", "k2": "new"}

    def test_t2_9_delete_node(self, graph_store):
        """T2.9: Delete a node, verify edges handled correctly."""
        graph_store.add_node(1, "net-1", name="A")
        graph_store.add_node(2, "net-1", name="B")
        graph_store.add_edge(1, 2, 0, "net-1", "increases")

        # Must delete edges first in LadybugDB
        graph_store.execute("MATCH (a:BioNode {name: 'A'})-[r:Interacts]->() DELETE r")
        graph_store.execute("MATCH (n:BioNode {name: 'A'}) DELETE n")

        rows = graph_store.execute("MATCH (n:BioNode) RETURN n.name")
        assert len(rows) == 1
        assert rows[0][0] == "B"

    def test_t2_10_null_and_empty_values(self, graph_store):
        """T2.10: Insert nodes with empty name or empty MAP."""
        graph_store.add_node(1, "net-1", name="", properties={})
        graph_store.add_node(2, "net-1", name=None, properties=None)

        nodes = graph_store.get_network_nodes("net-1")
        assert len(nodes) == 2
        for node in nodes:
            assert node["name"] == ""
            assert node["properties"] == {}

    def test_t2_global_id_uniqueness(self, graph_store):
        """Bonus: Same CX2 node ID in different networks gets unique global IDs."""
        graph_store.add_node(0, "net-A", name="ProteinA")
        graph_store.add_node(0, "net-B", name="ProteinB")

        rows = graph_store.execute("MATCH (n:BioNode) RETURN n.name ORDER BY n.name")
        assert len(rows) == 2
        assert rows[0][0] == "ProteinA"
        assert rows[1][0] == "ProteinB"
