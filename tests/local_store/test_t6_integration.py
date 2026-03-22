"""T6: Catalog + Graph Integration.

Test the two tiers working together via the LocalStore class.
"""

import json
from pathlib import Path

import pytest

from tests.local_store.conftest import make_minimal_cx2, make_bel_cx2


class TestT6Integration:
    """Test the two tiers working together."""

    def test_t6_1_full_import_pipeline(self, local_store):
        """T6.1: Import a CX2 network creates catalog entry AND graph data."""
        cx2 = make_minimal_cx2()
        uuid = "int-001"

        stats = local_store.import_network(cx2, uuid, agent="rdaneel")

        # Verify catalog entry
        entry = local_store.get_catalog_entry(uuid)
        assert entry is not None
        assert entry["name"] == "Test Minimal Network"
        assert entry["agent"] == "rdaneel"
        assert entry["node_count"] == 2
        assert entry["edge_count"] == 1
        assert entry["is_dirty"] == 1

        # Verify graph data
        nodes = local_store.graph.get_network_nodes(uuid)
        assert len(nodes) == 2

        # Verify CX2 file saved
        assert entry["local_path"] is not None
        assert Path(entry["local_path"]).exists()

    def test_t6_2_catalog_then_graph_query(self, local_store):
        """T6.2: Query catalog for network by category, then query graph for its nodes."""
        cx2 = make_bel_cx2()
        local_store.import_network(cx2, "bel-001", category="science-kg")

        # Tier 1: find by category
        kg_nets = local_store.query_catalog(category="science-kg")
        assert len(kg_nets) == 1
        uuid = kg_nets[0]["uuid"]

        # Tier 2: query its nodes
        nodes = local_store.graph.get_network_nodes(uuid)
        assert len(nodes) == 5
        names = {n["name"] for n in nodes}
        assert "TRIM25" in names

    def test_t6_3_dirty_flag_lifecycle(self, local_store):
        """T6.3: Mark network dirty, export, mark published."""
        cx2 = make_minimal_cx2()
        uuid = "dirty-001"

        local_store.import_network(cx2, uuid)
        entry = local_store.get_catalog_entry(uuid)
        assert entry["is_dirty"] == 1

        # "Publish" — mark as clean
        local_store.mark_published(uuid, ndex_modified="2026-03-16T12:00:00Z")

        entry = local_store.get_catalog_entry(uuid)
        assert entry["is_dirty"] == 0
        assert entry["ndex_modified"] == "2026-03-16T12:00:00Z"

    def test_t6_4_delete_consistency(self, local_store):
        """T6.4: Import network, delete, verify both tiers cleaned up."""
        cx2 = make_minimal_cx2()
        uuid = "del-001"

        local_store.import_network(cx2, uuid)
        assert local_store.get_catalog_entry(uuid) is not None
        assert len(local_store.graph.get_network_nodes(uuid)) == 2

        local_store.delete_network(uuid)

        assert local_store.get_catalog_entry(uuid) is None
        assert len(local_store.graph.get_network_nodes(uuid)) == 0
        # CX2 file should be gone
        cx2_path = local_store.networks_dir / f"{uuid}.cx2"
        assert not cx2_path.exists()

    def test_t6_5_idempotent_import(self, local_store):
        """T6.5: Import same network twice — update rather than duplicate."""
        cx2 = make_minimal_cx2()
        uuid = "idem-001"

        local_store.import_network(cx2, uuid, agent="rdaneel")
        local_store.import_network(cx2, uuid, agent="rdaneel")

        # Should have exactly one catalog entry
        entries = local_store.query_catalog(agent="rdaneel")
        assert len(entries) == 1
        assert entries[0]["node_count"] == 2

        # Should have exactly 2 nodes in graph
        nodes = local_store.graph.get_network_nodes(uuid)
        assert len(nodes) == 2

    def test_t6_query_graph_via_store(self, local_store):
        """Bonus: query_graph convenience method works."""
        cx2 = make_bel_cx2()
        local_store.import_network(cx2, "q-001")

        rows = local_store.query_graph(
            "MATCH (n:BioNode {name: 'TRIM25'})-[r:Interacts]-(m) RETURN m.name"
        )
        assert len(rows) >= 1

    def test_t6_export_round_trip(self, local_store):
        """Bonus: import then export via LocalStore produces valid CX2."""
        cx2 = make_bel_cx2()
        uuid = "rt-001"
        local_store.import_network(cx2, uuid)

        exported = local_store.export_network(uuid)
        nodes = exported.get_nodes()
        edges = exported.get_edges()
        assert len(nodes) == 5
        assert len(edges) == 5
