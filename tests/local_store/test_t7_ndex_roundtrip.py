"""T7: NDEx Round-Trip (Integration).

End-to-end tests requiring NDEx API access.
Uses rdaneel profile for authenticated operations.

Run with: pytest tests/local_store/test_t7_ndex_roundtrip.py -v
Skip with: pytest tests/local_store/ -v --ignore=tests/local_store/test_t7_ndex_roundtrip.py
"""

import json
import time

import pytest
from ndex2.cx2 import CX2Network

from tools.ndex_mcp.config import load_ndex_config, has_credentials
from tools.ndex_mcp.ndex_client_wrapper import NDExClientWrapper
from tools.local_store.store import LocalStore
from tools.local_store.cx2_import import import_cx2_network
from tools.local_store.cx2_export import export_cx2_network


# Skip entire module if credentials aren't available
@pytest.fixture(scope="module")
def ndex_wrapper():
    """NDEx client wrapper using rdaneel profile."""
    try:
        config = load_ndex_config(profile="rdaneel")
    except (ValueError, FileNotFoundError):
        pytest.skip("NDEx rdaneel profile not configured")
    if not has_credentials(config):
        pytest.skip("NDEx credentials not available")
    return NDExClientWrapper(config)


@pytest.fixture
def local_store(tmp_path):
    """Fresh LocalStore for each test."""
    store = LocalStore(cache_dir=tmp_path / "cache")
    yield store
    store.close()


def _make_test_network(suffix: str = "") -> CX2Network:
    """Create a small test network for NDEx upload."""
    cx2 = CX2Network()
    cx2.set_network_attributes({
        "name": f"ndexagent t7 test{suffix}",
        "description": f"Automated T7 round-trip test network{suffix}. Safe to delete.",
        "ndex-workflow": "test",
        "ndex-agent": "rdaneel",
    })
    cx2.add_node(node_id=0, attributes={"name": "TestProteinA", "type": "protein"})
    cx2.add_node(node_id=1, attributes={"name": "TestProteinB", "type": "protein"})
    cx2.add_node(node_id=2, attributes={"name": "TestGeneC", "type": "gene"})
    cx2.add_edge(edge_id=0, source=0, target=1, attributes={
        "interaction": "increases",
        "evidence": "T7 test evidence",
    })
    cx2.add_edge(edge_id=1, source=1, target=2, attributes={
        "interaction": "regulates",
    })
    return cx2


class TestT7NDExRoundTrip:
    """End-to-end tests requiring NDEx API access."""

    def test_t7_1_download_public_network(self, ndex_wrapper, local_store):
        """T7.1: Download public network from NDEx -> import to local store -> query."""
        # Use one of rdaneel's known public networks
        # First, find a small public network
        result = ndex_wrapper.search_networks("ndexagent", account_name="rdaneel", size=5)
        assert result["status"] == "success", f"Search failed: {result}"
        networks = result["data"].get("networks", [])
        assert len(networks) > 0, "No rdaneel networks found on NDEx"

        # Pick the smallest network
        net = min(networks, key=lambda n: n.get("nodeCount", 0) + n.get("edgeCount", 0))
        net_uuid = net["externalId"]
        print(f"\nDownloading: {net['name']} ({net.get('nodeCount', '?')} nodes)")

        # Download
        dl_result = ndex_wrapper.download_network(net_uuid)
        assert dl_result["status"] == "success", f"Download failed: {dl_result}"

        # Parse into CX2Network
        cx2 = CX2Network()
        cx2.create_from_raw_cx2(dl_result["data"])

        # Import to local store
        stats = local_store.import_network(cx2, net_uuid, agent="rdaneel")
        assert stats["node_count"] > 0

        # Verify catalog entry
        entry = local_store.get_catalog_entry(net_uuid)
        assert entry is not None
        assert entry["node_count"] == stats["node_count"]

        # Query the graph
        nodes = local_store.graph.get_network_nodes(net_uuid)
        assert len(nodes) == stats["node_count"]
        print(f"Imported {stats['node_count']} nodes, {stats['edge_count']} edges")

    def test_t7_2_create_download_compare(self, ndex_wrapper, local_store):
        """T7.2: Create network locally -> upload to NDEx -> download -> compare."""
        cx2_original = _make_test_network(" round-trip")
        local_uuid = "t7-local-roundtrip"

        # Import locally
        local_store.import_network(cx2_original, local_uuid)

        # Upload to NDEx
        create_result = ndex_wrapper.create_network(cx2_original)
        assert create_result["status"] == "success", f"Create failed: {create_result}"
        ndex_url = create_result["data"]
        ndex_uuid = ndex_url.strip().split("/")[-1]
        print(f"\nUploaded as: {ndex_uuid}")

        try:
            # Wait briefly for NDEx to process
            time.sleep(2)

            # Download back from NDEx
            dl_result = ndex_wrapper.download_network(ndex_uuid)
            assert dl_result["status"] == "success", f"Download failed: {dl_result}"

            cx2_downloaded = CX2Network()
            cx2_downloaded.create_from_raw_cx2(dl_result["data"])

            # Compare node counts
            orig_nodes = cx2_original.get_nodes()
            dl_nodes = cx2_downloaded.get_nodes()
            assert len(dl_nodes) == len(orig_nodes), (
                f"Node count mismatch: uploaded {len(orig_nodes)}, downloaded {len(dl_nodes)}"
            )

            # Compare edge counts
            orig_edges = cx2_original.get_edges()
            dl_edges = cx2_downloaded.get_edges()
            assert len(dl_edges) == len(orig_edges), (
                f"Edge count mismatch: uploaded {len(orig_edges)}, downloaded {len(dl_edges)}"
            )

            # Compare node names
            orig_names = sorted(n["v"].get("name", "") for n in orig_nodes.values())
            dl_names = sorted(n["v"].get("name", "") for n in dl_nodes.values())
            assert orig_names == dl_names, f"Node names differ: {orig_names} vs {dl_names}"

            # Import downloaded version to local store and verify graph
            dl_local_uuid = "t7-downloaded"
            local_store.import_network(cx2_downloaded, dl_local_uuid)
            dl_graph_nodes = local_store.graph.get_network_nodes(dl_local_uuid)
            assert len(dl_graph_nodes) == len(orig_nodes)

            print(f"Round-trip verified: {len(orig_nodes)} nodes, {len(orig_edges)} edges")

        finally:
            # Clean up: delete test network from NDEx
            ndex_wrapper.delete_network(ndex_uuid)
            print(f"Cleaned up NDEx network {ndex_uuid}")

    def test_t7_3_local_edit_and_sync(self, ndex_wrapper, local_store):
        """T7.3: Download agent's network -> modify locally -> re-upload -> verify."""
        cx2_original = _make_test_network(" edit-sync")

        # Upload initial version
        create_result = ndex_wrapper.create_network(cx2_original)
        assert create_result["status"] == "success"
        ndex_url = create_result["data"]
        ndex_uuid = ndex_url.strip().split("/")[-1]
        print(f"\nCreated: {ndex_uuid}")

        try:
            time.sleep(2)

            # Download and import to local store
            dl_result = ndex_wrapper.download_network(ndex_uuid)
            assert dl_result["status"] == "success"
            cx2 = CX2Network()
            cx2.create_from_raw_cx2(dl_result["data"])
            local_store.import_network(cx2, ndex_uuid, agent="rdaneel")

            # Modify locally: add a node and edge via the graph store
            local_store.graph.add_node(
                node_id=99,
                network_uuid=ndex_uuid,
                name="NewProteinD",
                node_type="protein",
                properties={"added_by": "t7_test"},
            )
            local_store.graph.link_node_to_network(99, ndex_uuid)
            # Find an existing node to connect to
            nodes = local_store.graph.get_network_nodes(ndex_uuid)
            existing_id = nodes[0]["id"]  # CX2 ID of first node
            local_store.graph.add_edge(
                src_id=existing_id,
                tgt_id=99,
                edge_id=99,
                network_uuid=ndex_uuid,
                interaction="binds",
            )

            # Mark as dirty
            local_store.catalog.update(ndex_uuid, is_dirty=True)

            # Export modified version
            cx2_modified = local_store.export_network(ndex_uuid)
            mod_nodes = cx2_modified.get_nodes()
            mod_edges = cx2_modified.get_edges()
            assert len(mod_nodes) == 4  # 3 original + 1 new
            assert len(mod_edges) == 3  # 2 original + 1 new

            # Re-upload to NDEx
            update_result = ndex_wrapper.update_network(ndex_uuid, cx2_modified)
            assert update_result["status"] == "success", f"Update failed: {update_result}"

            time.sleep(2)

            # Download again and verify modifications persisted
            dl2_result = ndex_wrapper.download_network(ndex_uuid)
            assert dl2_result["status"] == "success"
            cx2_final = CX2Network()
            cx2_final.create_from_raw_cx2(dl2_result["data"])

            final_nodes = cx2_final.get_nodes()
            final_edges = cx2_final.get_edges()
            assert len(final_nodes) == 4, f"Expected 4 nodes, got {len(final_nodes)}"
            assert len(final_edges) == 3, f"Expected 3 edges, got {len(final_edges)}"

            # Verify new node exists
            final_names = {n["v"].get("name", "") for n in final_nodes.values()}
            assert "NewProteinD" in final_names

            # Mark as published
            local_store.mark_published(ndex_uuid)
            entry = local_store.get_catalog_entry(ndex_uuid)
            assert entry["is_dirty"] == 0

            print(f"Edit-sync verified: 3->4 nodes, 2->3 edges")

        finally:
            ndex_wrapper.delete_network(ndex_uuid)
            print(f"Cleaned up NDEx network {ndex_uuid}")

    def test_t7_4_staleness_detection(self, ndex_wrapper, local_store):
        """T7.4: Import network, check NDEx modification timestamp for staleness."""
        cx2 = _make_test_network(" staleness")

        # Upload
        create_result = ndex_wrapper.create_network(cx2)
        assert create_result["status"] == "success"
        ndex_url = create_result["data"]
        ndex_uuid = ndex_url.strip().split("/")[-1]

        try:
            time.sleep(2)

            # Get NDEx summary for modification time
            summary = ndex_wrapper.get_network_summary(ndex_uuid)
            assert summary["status"] == "success"
            ndex_modified = str(summary["data"].get("modificationTime", ""))

            # Download and import with NDEx timestamp
            dl_result = ndex_wrapper.download_network(ndex_uuid)
            assert dl_result["status"] == "success"
            cx2_dl = CX2Network()
            cx2_dl.create_from_raw_cx2(dl_result["data"])
            local_store.import_network(cx2_dl, ndex_uuid, agent="rdaneel")
            local_store.mark_published(ndex_uuid, ndex_modified=ndex_modified)

            # Verify timestamp stored
            entry = local_store.get_catalog_entry(ndex_uuid)
            assert entry["ndex_modified"] == ndex_modified
            assert entry["is_dirty"] == 0

            # Check again — timestamp should be the same (not stale)
            summary2 = ndex_wrapper.get_network_summary(ndex_uuid)
            assert summary2["status"] == "success"
            current_modified = str(summary2["data"].get("modificationTime", ""))
            is_stale = current_modified != entry["ndex_modified"]
            assert not is_stale, "Network should not be stale (nothing changed)"

            print(f"Staleness check passed, timestamp: {ndex_modified}")

        finally:
            ndex_wrapper.delete_network(ndex_uuid)
            print(f"Cleaned up NDEx network {ndex_uuid}")
