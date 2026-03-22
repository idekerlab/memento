"""T3: CX2 Import/Export Round-Trip tests."""

import pytest

from ndex2.cx2 import CX2Network

from tools.local_store.cx2_import import import_cx2_network
from tools.local_store.cx2_export import export_cx2_network
from tests.local_store.conftest import make_minimal_cx2, make_bel_cx2


class TestT3CX2RoundTrip:
    """Verify CX2 networks survive import into LadybugDB and export back."""

    def test_t3_1_minimal_network(self, graph_store):
        """T3.1: Minimal network — 2 nodes, 1 edge, round-trip."""
        cx2 = make_minimal_cx2()
        uuid = "test-minimal-001"

        # Import
        stats = import_cx2_network(graph_store, cx2, uuid)
        assert stats["node_count"] == 2
        assert stats["edge_count"] == 1

        # Export
        exported = export_cx2_network(graph_store, uuid)

        # Verify network attributes
        attrs = exported.get_network_attributes()
        assert attrs["name"] == "Test Minimal Network"
        assert attrs["description"] == "A minimal test network"

        # Verify nodes
        nodes = exported.get_nodes()
        assert len(nodes) == 2
        node_0 = nodes[0]["v"]
        assert node_0["name"] == "ProteinA"
        assert node_0["type"] == "protein"

        # Verify edges
        edges = exported.get_edges()
        assert len(edges) == 1
        edge_0 = edges[0]
        assert edge_0["s"] == 0
        assert edge_0["t"] == 1
        assert edge_0["v"]["interaction"] == "increases"
        assert edge_0["v"]["evidence"] == "PMID:12345"

    def test_t3_3_bel_knowledge_graph(self, graph_store):
        """T3.3: BEL knowledge graph with BEL-specific properties."""
        cx2 = make_bel_cx2()
        uuid = "test-bel-001"

        stats = import_cx2_network(graph_store, cx2, uuid)
        assert stats["node_count"] == 5
        assert stats["edge_count"] == 5

        exported = export_cx2_network(graph_store, uuid)

        # Verify node count
        nodes = exported.get_nodes()
        assert len(nodes) == 5

        # Find TRIM25 node and verify properties
        trim25_nodes = [n for n in nodes.values() if n["v"].get("name") == "TRIM25"]
        assert len(trim25_nodes) == 1
        assert trim25_nodes[0]["v"]["function"] == "p"

        # Verify edges
        edges = exported.get_edges()
        assert len(edges) == 5

        # Find directlyIncreases edge
        di_edges = [e for e in edges.values() if e["v"].get("interaction") == "directlyIncreases"]
        assert len(di_edges) == 1
        assert "evidence" in di_edges[0]["v"]

    def test_t3_5_properties_edge_cases(self, graph_store):
        """T3.5: Properties edge cases — empty, many, special characters."""
        cx2 = CX2Network()
        cx2.set_network_attributes({"name": "Edge Cases"})

        # Node with no extra properties
        cx2.add_node(node_id=0, attributes={"name": "Bare"})

        # Node with many properties
        many_props = {"name": "Rich"}
        for i in range(10):
            many_props[f"prop_{i}"] = f"value_{i}"
        cx2.add_node(node_id=1, attributes=many_props)

        # Node with special characters
        cx2.add_node(node_id=2, attributes={
            "name": "Special",
            "desc": "has 'quotes' and \"doubles\"",
            "unicode": "alpha \u03b1 beta \u03b2",
        })

        # Edge with properties
        cx2.add_edge(edge_id=0, source=0, target=1, attributes={
            "interaction": "binds",
            "note": "test edge",
        })
        # Edge with no extra properties beyond interaction
        cx2.add_edge(edge_id=1, source=1, target=2, attributes={})

        uuid = "test-edge-cases"
        import_cx2_network(graph_store, cx2, uuid)
        exported = export_cx2_network(graph_store, uuid)

        nodes = exported.get_nodes()
        assert len(nodes) == 3

        # Check many-property node
        rich_nodes = [n for n in nodes.values() if n["v"].get("name") == "Rich"]
        assert len(rich_nodes) == 1
        for i in range(10):
            assert rich_nodes[0]["v"][f"prop_{i}"] == f"value_{i}"

        # Check special character node
        special_nodes = [n for n in nodes.values() if n["v"].get("name") == "Special"]
        assert len(special_nodes) == 1
        assert "quotes" in special_nodes[0]["v"]["desc"]
        assert "\u03b1" in special_nodes[0]["v"]["unicode"]

        # Verify edges
        edges = exported.get_edges()
        assert len(edges) == 2

    def test_t3_6_multiple_networks(self, graph_store):
        """T3.6: Multiple networks in one database — no cross-contamination."""
        # Create three different networks
        for i in range(3):
            cx2 = CX2Network()
            cx2.set_network_attributes({"name": f"Network {i}"})
            for j in range(3):
                node_id = i * 100 + j  # Use different ID ranges per network
                cx2.add_node(node_id=node_id, attributes={"name": f"Node_{i}_{j}"})
            cx2.add_edge(edge_id=i * 100, source=i * 100, target=i * 100 + 1,
                         attributes={"interaction": "test"})
            import_cx2_network(graph_store, cx2, f"net-{i}")

        # Verify each network has exactly 3 nodes
        for i in range(3):
            nodes = graph_store.get_network_nodes(f"net-{i}")
            assert len(nodes) == 3, f"Network net-{i} has {len(nodes)} nodes, expected 3"

        # Verify InNetwork relationships are correct
        for i in range(3):
            rows = graph_store.execute(
                "MATCH (n:BioNode)-[:InNetwork]->(net:Network {uuid: $uuid}) RETURN count(n)",
                {"uuid": f"net-{i}"},
            )
            assert rows[0][0] == 3

        # Export each and verify isolation
        for i in range(3):
            exported = export_cx2_network(graph_store, f"net-{i}")
            nodes = exported.get_nodes()
            assert len(nodes) == 3
            # All node names should belong to this network
            for n in nodes.values():
                assert n["v"]["name"].startswith(f"Node_{i}_")

    def test_t3_idempotent_reimport(self, graph_store):
        """Bonus: Re-importing the same network replaces data, not duplicates."""
        cx2 = make_minimal_cx2()
        uuid = "test-idem"

        import_cx2_network(graph_store, cx2, uuid)
        import_cx2_network(graph_store, cx2, uuid)  # Re-import

        nodes = graph_store.get_network_nodes(uuid)
        assert len(nodes) == 2  # Not 4
