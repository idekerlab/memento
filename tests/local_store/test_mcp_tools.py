"""Tests for local store MCP tools.

Tests the tool functions directly (not via MCP protocol).
"""

import pytest

from ndex2.cx2 import CX2Network

from tools.local_store.store import LocalStore
from tools.local_store import server as mcp_server
from tests.local_store.conftest import make_bel_cx2, make_second_bel_cx2, make_plans_cx2


@pytest.fixture(autouse=True)
def setup_store(tmp_path):
    """Set up a fresh LocalStore and inject it into the MCP server module."""
    store = LocalStore(cache_dir=tmp_path / "cache")
    mcp_server._store = store
    mcp_server._ndex = None  # No NDEx for unit tests
    yield store
    store.close()
    mcp_server._store = None


@pytest.fixture
def loaded_store(setup_store):
    """Store pre-loaded with two BEL networks."""
    cx2_1 = make_bel_cx2()
    cx2_2 = make_second_bel_cx2()
    setup_store.import_network(cx2_1, "bel-trim25", agent="rdaneel", category="science-kg")
    setup_store.import_network(cx2_2, "bel-ns1", agent="rdaneel", category="science-kg")
    return setup_store


class TestCatalogTools:

    def test_query_catalog_all(self, loaded_store):
        result = mcp_server.query_catalog()
        assert result["status"] == "success"
        assert result["count"] == 2

    def test_query_catalog_by_agent(self, loaded_store):
        result = mcp_server.query_catalog(agent="rdaneel")
        assert result["count"] == 2

        result = mcp_server.query_catalog(agent="drh")
        assert result["count"] == 0

    def test_query_catalog_by_category(self, loaded_store):
        result = mcp_server.query_catalog(category="science-kg")
        assert result["count"] == 2

        result = mcp_server.query_catalog(category="plan")
        assert result["count"] == 0

    def test_get_cached_network(self, loaded_store):
        result = mcp_server.get_cached_network("bel-trim25")
        assert result["status"] == "success"
        assert result["data"]["name"] == "TRIM25 BEL Analysis"
        assert result["data"]["node_count"] == 5

    def test_get_cached_network_missing(self, setup_store):
        result = mcp_server.get_cached_network("nonexistent")
        assert result["status"] == "error"


class TestGraphQueryTools:

    def test_query_graph(self, loaded_store):
        result = mcp_server.query_graph("MATCH (n:BioNode) RETURN count(n)")
        assert result["status"] == "success"
        assert result["rows"][0][0] == 10  # 5 + 5 nodes

    def test_query_graph_error(self, loaded_store):
        result = mcp_server.query_graph("INVALID CYPHER")
        assert result["status"] == "error"

    def test_get_network_nodes(self, loaded_store):
        result = mcp_server.get_network_nodes("bel-trim25")
        assert result["status"] == "success"
        assert result["count"] == 5
        names = {n["name"] for n in result["nodes"]}
        assert "TRIM25" in names

    def test_get_network_edges(self, loaded_store):
        result = mcp_server.get_network_edges("bel-trim25")
        assert result["status"] == "success"
        assert result["count"] == 5

    def test_find_neighbors(self, loaded_store):
        result = mcp_server.find_neighbors("TRIM25")
        assert result["status"] == "success"
        assert result["count"] >= 2
        neighbor_names = {n["name"] for n in result["neighbors"]}
        assert "RIG-I" in neighbor_names
        assert "NS1" in neighbor_names

    def test_find_neighbors_in_network(self, loaded_store):
        result = mcp_server.find_neighbors("TRIM25", network_uuid="bel-trim25")
        assert result["status"] == "success"
        # Only neighbors within bel-trim25
        for n in result["neighbors"]:
            assert n["network_uuid"] == "bel-trim25"

    def test_find_path(self, loaded_store):
        result = mcp_server.find_path("NS1", "ISG15")
        assert result["status"] == "success"
        assert result["count"] > 0
        # Shortest path should be <= 4 hops
        assert result["paths"][0]["hops"] <= 4

    def test_find_path_no_connection(self, loaded_store):
        result = mcp_server.find_path("TRIM25", "NONEXISTENT")
        assert result["status"] == "success"
        assert result["count"] == 0

    def test_find_contradictions(self, loaded_store):
        result = mcp_server.find_contradictions("bel-trim25", "bel-ns1")
        assert result["status"] == "success"
        assert result["count"] > 0
        pairs = [(c["source"], c["target"]) for c in result["contradictions"]]
        assert ("NS1", "TRIM25") in pairs


class TestCacheManagementTools:

    def test_cache_network_no_ndex(self, setup_store):
        """cache_network fails gracefully without NDEx client."""
        result = mcp_server.cache_network("some-uuid")
        assert result["status"] == "error"
        assert "not configured" in result["message"]

    def test_publish_network_no_ndex(self, loaded_store):
        """publish_network fails gracefully without NDEx client."""
        result = mcp_server.publish_network("bel-trim25")
        assert result["status"] == "error"

    def test_check_staleness_no_ndex(self, loaded_store):
        """check_staleness fails gracefully without NDEx client."""
        result = mcp_server.check_staleness("bel-trim25")
        assert result["status"] == "error"

    def test_delete_cached_network(self, loaded_store):
        result = mcp_server.delete_cached_network("bel-trim25")
        assert result["status"] == "success"

        # Verify it's gone
        result = mcp_server.get_cached_network("bel-trim25")
        assert result["status"] == "error"

        # Other network still there
        result = mcp_server.get_cached_network("bel-ns1")
        assert result["status"] == "success"

    def test_delete_cached_network_missing(self, setup_store):
        result = mcp_server.delete_cached_network("nonexistent")
        assert result["status"] == "error"


class TestSelfKnowledgeWorkflow:
    """Test a realistic agent workflow: cache plans, query, modify, export."""

    def test_plans_workflow(self, setup_store):
        # Import plans network
        cx2 = make_plans_cx2()
        setup_store.import_network(cx2, "plans-drh", agent="drh", category="plan")

        # Query catalog
        result = mcp_server.query_catalog(agent="drh", category="plan")
        assert result["count"] == 1

        # Find planned actions via Cypher
        result = mcp_server.query_graph(
            "MATCH (n:BioNode {network_uuid: 'plans-drh', node_type: 'action'}) "
            "RETURN n.name, n.properties"
        )
        assert result["status"] == "success"
        assert result["row_count"] == 5

        # Find neighbors of a goal
        result = mcp_server.find_neighbors("Map TRIM25 interactions", network_uuid="plans-drh")
        assert result["count"] >= 3  # mission + actions

        # Delete from cache
        result = mcp_server.delete_cached_network("plans-drh")
        assert result["status"] == "success"
