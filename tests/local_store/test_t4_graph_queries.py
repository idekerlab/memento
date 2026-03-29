"""T4: Graph Queries on Real Data.

Test Cypher queries against imported biological networks.
Uses two BEL networks with overlapping proteins and a contradiction.
"""

import pytest

from tools.local_store.cx2_import import import_cx2_network
from tools.local_store.graph_store import _clean_map
from tests.local_store.conftest import make_bel_cx2, make_second_bel_cx2


@pytest.fixture
def two_networks(graph_store):
    """Import two BEL networks with overlapping proteins."""
    cx2_1 = make_bel_cx2()
    cx2_2 = make_second_bel_cx2()
    import_cx2_network(graph_store, cx2_1, "bel-trim25")
    import_cx2_network(graph_store, cx2_2, "bel-ns1")
    return graph_store


class TestT4GraphQueries:
    """Test Cypher queries against imported biological networks."""

    def test_t4_1_neighborhood(self, two_networks):
        """T4.1: Find all neighbors of TRIM25."""
        rows = two_networks.execute(
            "MATCH (n:BioNode {name: 'TRIM25'})-[r:Interacts]-(m:BioNode) "
            "RETURN DISTINCT m.name, r.interaction"
        )
        neighbor_names = sorted(set(r[0] for r in rows))
        # TRIM25 connects to RIG-I and NS1 in both networks
        assert "RIG-I" in neighbor_names
        assert "NS1" in neighbor_names

    def test_t4_2_two_hop_neighborhood(self, two_networks):
        """T4.2: 2-hop neighborhood with variable-length path."""
        rows = two_networks.execute(
            "MATCH (n:BioNode {name: 'TRIM25'})-[:Interacts*1..2]-(m:BioNode) "
            "RETURN DISTINCT m.name"
        )
        names = {r[0] for r in rows}
        # 1-hop: RIG-I, NS1; 2-hop should reach further
        assert "RIG-I" in names
        assert "NS1" in names
        assert len(names) >= 3  # Should reach at least 3 distinct neighbors

    def test_t4_3_path_finding(self, two_networks):
        """T4.3: Find path between two known-connected proteins."""
        rows = two_networks.execute(
            "MATCH path = (a:BioNode {name: 'NS1'})-[:Interacts*1..4]-(b:BioNode {name: 'ISG15'}) "
            "RETURN length(path) AS hops"
        )
        assert len(rows) > 0  # At least one path should exist
        # NS1 -> TRIM25 -> RIG-I -> IFNB1 -> ISG15 (in first network)
        hop_counts = [r[0] for r in rows]
        assert min(hop_counts) <= 4

    def test_t4_4_cross_network(self, two_networks):
        """T4.4: Find proteins present in both networks."""
        rows = two_networks.execute(
            "MATCH (n:BioNode)-[:InNetwork]->(net1:Network {uuid: 'bel-trim25'}) "
            "MATCH (m:BioNode)-[:InNetwork]->(net2:Network {uuid: 'bel-ns1'}) "
            "WHERE n.name = m.name "
            "RETURN DISTINCT n.name"
        )
        shared = {r[0] for r in rows}
        # NS1, TRIM25, RIG-I appear in both networks
        assert "NS1" in shared
        assert "TRIM25" in shared
        assert "RIG-I" in shared

    def test_t4_5_filter_by_edge_type(self, two_networks):
        """T4.5: Find all 'increases' relationships."""
        rows = two_networks.execute(
            "MATCH (a:BioNode)-[r:Interacts {interaction: 'increases'}]->(b:BioNode) "
            "RETURN a.name, b.name, r.network_uuid"
        )
        assert len(rows) >= 2  # Multiple increases edges across both networks
        interactions = [(r[0], r[1]) for r in rows]
        # RIG-I increases IFNB1 in first network
        assert ("RIG-I", "IFNB1") in interactions

    def test_t4_6_filter_by_node_property(self, two_networks):
        """T4.6: Find all nodes where type = 'protein' via MAP property."""
        rows = two_networks.execute(
            "MATCH (n:BioNode) WHERE n.node_type = 'protein' RETURN DISTINCT n.name"
        )
        names = {r[0] for r in rows}
        assert "TRIM25" in names
        assert "NS1" in names
        # IFNB1 is type 'rna', should not be in results
        assert "IFNB1" not in names

    def test_t4_7_aggregation(self, two_networks):
        """T4.7: Count nodes per network."""
        rows = two_networks.execute(
            "MATCH (n:BioNode)-[:InNetwork]->(net:Network) "
            "RETURN net.uuid, count(n) AS node_count ORDER BY net.uuid"
        )
        counts = {r[0]: r[1] for r in rows}
        assert counts["bel-trim25"] == 5
        assert counts["bel-ns1"] == 5

    def test_t4_8_contradiction_detection(self, two_networks):
        """T4.8: Find same node pair with opposite edge types across networks.

        First network: NS1 -[directlyDecreases]-> TRIM25
        Second network: NS1 -[increases]-> TRIM25
        """
        rows = two_networks.execute(
            "MATCH (a:BioNode)-[r1:Interacts]->(b:BioNode), "
            "      (c:BioNode)-[r2:Interacts]->(d:BioNode) "
            "WHERE a.name = c.name AND b.name = d.name "
            "  AND r1.network_uuid <> r2.network_uuid "
            "  AND ((r1.interaction CONTAINS 'ecreases' AND r2.interaction CONTAINS 'ncreases') "
            "    OR (r1.interaction CONTAINS 'ncreases' AND r2.interaction CONTAINS 'ecreases')) "
            "RETURN a.name, b.name, r1.interaction, r1.network_uuid, r2.interaction, r2.network_uuid"
        )
        assert len(rows) > 0
        # Should find NS1->TRIM25 contradiction
        pairs = [(r[0], r[1]) for r in rows]
        assert ("NS1", "TRIM25") in pairs
