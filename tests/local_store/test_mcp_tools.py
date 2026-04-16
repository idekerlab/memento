"""Tests for local store MCP tools.

Tests the tool functions directly (not via MCP protocol).
All tools now require explicit store_agent; we use "test" as the agent name.
"""

import pytest

from ndex2.cx2 import CX2Network

from tools.local_store.store import LocalStore
from tools.local_store import server as mcp_server
from tests.local_store.conftest import make_bel_cx2, make_second_bel_cx2, make_plans_cx2

# All tests use this agent name for store routing.
AGENT = "test"


@pytest.fixture(autouse=True)
def setup_store(tmp_path):
    """Set up a fresh LocalStore and inject it into the MCP server module."""
    store = LocalStore(cache_dir=tmp_path / "cache" / AGENT)
    # Inject test store keyed by agent name so _get_store(AGENT) finds it.
    mcp_server._stores[AGENT] = store
    mcp_server._ndex_clients.clear()  # No NDEx for unit tests
    yield store
    store.close()
    mcp_server._stores.pop(AGENT, None)


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
        result = mcp_server.query_catalog(store_agent=AGENT)
        assert result["status"] == "success"
        assert result["count"] == 2

    def test_query_catalog_by_agent(self, loaded_store):
        result = mcp_server.query_catalog(store_agent=AGENT, agent="rdaneel")
        assert result["count"] == 2

        result = mcp_server.query_catalog(store_agent=AGENT, agent="drh")
        assert result["count"] == 0

    def test_query_catalog_by_category(self, loaded_store):
        result = mcp_server.query_catalog(store_agent=AGENT, category="science-kg")
        assert result["count"] == 2

        result = mcp_server.query_catalog(store_agent=AGENT, category="plan")
        assert result["count"] == 0

    def test_query_catalog_missing_store_agent(self, loaded_store):
        """Omitting store_agent returns an error."""
        result = mcp_server.query_catalog(store_agent=None)
        assert result["status"] == "error"
        assert "store_agent is required" in result["message"]

    def test_get_cached_network(self, loaded_store):
        result = mcp_server.get_cached_network("bel-trim25", store_agent=AGENT)
        assert result["status"] == "success"
        assert result["data"]["name"] == "TRIM25 BEL Analysis"
        assert result["data"]["node_count"] == 5

    def test_get_cached_network_missing(self, setup_store):
        result = mcp_server.get_cached_network("nonexistent", store_agent=AGENT)
        assert result["status"] == "error"


class TestGraphQueryTools:

    def test_query_graph(self, loaded_store):
        result = mcp_server.query_graph(
            "MATCH (n:BioNode) RETURN count(n)", store_agent=AGENT
        )
        assert result["status"] == "success"
        assert result["rows"][0][0] == 10  # 5 + 5 nodes

    def test_query_graph_error(self, loaded_store):
        result = mcp_server.query_graph("INVALID CYPHER", store_agent=AGENT)
        assert result["status"] == "error"

    def test_get_network_nodes(self, loaded_store):
        result = mcp_server.get_network_nodes("bel-trim25", store_agent=AGENT)
        assert result["status"] == "success"
        assert result["count"] == 5
        names = {n["name"] for n in result["nodes"]}
        assert "TRIM25" in names

    def test_get_network_edges(self, loaded_store):
        result = mcp_server.get_network_edges("bel-trim25", store_agent=AGENT)
        assert result["status"] == "success"
        assert result["count"] == 5

    def test_find_neighbors(self, loaded_store):
        result = mcp_server.find_neighbors("TRIM25", store_agent=AGENT)
        assert result["status"] == "success"
        assert result["count"] >= 2
        neighbor_names = {n["name"] for n in result["neighbors"]}
        assert "RIG-I" in neighbor_names
        assert "NS1" in neighbor_names

    def test_find_neighbors_in_network(self, loaded_store):
        result = mcp_server.find_neighbors(
            "TRIM25", store_agent=AGENT, network_uuid="bel-trim25"
        )
        assert result["status"] == "success"
        for n in result["neighbors"]:
            assert n["network_uuid"] == "bel-trim25"

    def test_find_path(self, loaded_store):
        result = mcp_server.find_path("NS1", "ISG15", store_agent=AGENT)
        assert result["status"] == "success"
        assert result["count"] > 0
        assert result["paths"][0]["hops"] <= 4

    def test_find_path_no_connection(self, loaded_store):
        result = mcp_server.find_path("TRIM25", "NONEXISTENT", store_agent=AGENT)
        assert result["status"] == "success"
        assert result["count"] == 0

    def test_find_contradictions(self, loaded_store):
        result = mcp_server.find_contradictions(
            "bel-trim25", "bel-ns1", store_agent=AGENT
        )
        assert result["status"] == "success"
        assert result["count"] > 0
        pairs = [(c["source"], c["target"]) for c in result["contradictions"]]
        assert ("NS1", "TRIM25") in pairs


class TestCacheManagementTools:

    def test_cache_network_missing_profile(self, setup_store):
        """cache_network fails with clear error when profile is missing."""
        result = mcp_server.cache_network(
            "some-uuid", store_agent=AGENT, profile=None
        )
        assert result["status"] == "error"
        assert "profile is required" in result["message"]

    def test_cache_network_missing_store_agent(self, setup_store):
        """cache_network fails with clear error when store_agent is missing."""
        result = mcp_server.cache_network(
            "some-uuid", store_agent=None, profile="rdaneel"
        )
        assert result["status"] == "error"
        assert "store_agent is required" in result["message"]

    def test_publish_network_missing_profile(self, loaded_store):
        """publish_network fails with clear error when profile is missing."""
        result = mcp_server.publish_network(
            "bel-trim25", store_agent=AGENT, profile=None
        )
        assert result["status"] == "error"
        assert "profile is required" in result["message"]

    def test_check_staleness_missing_profile(self, loaded_store):
        """check_staleness fails with clear error when profile is missing."""
        result = mcp_server.check_staleness(
            "bel-trim25", store_agent=AGENT, profile=None
        )
        assert result["status"] == "error"
        assert "profile is required" in result["message"]

    def test_delete_cached_network(self, loaded_store):
        result = mcp_server.delete_cached_network("bel-trim25", store_agent=AGENT)
        assert result["status"] == "success"

        result = mcp_server.get_cached_network("bel-trim25", store_agent=AGENT)
        assert result["status"] == "error"

        result = mcp_server.get_cached_network("bel-ns1", store_agent=AGENT)
        assert result["status"] == "success"

    def test_delete_cached_network_missing(self, setup_store):
        result = mcp_server.delete_cached_network("nonexistent", store_agent=AGENT)
        assert result["status"] == "error"


class TestSelfKnowledgeWorkflow:
    """Test a realistic agent workflow: cache plans, query, modify, export."""

    def test_plans_workflow(self, setup_store):
        cx2 = make_plans_cx2()
        setup_store.import_network(cx2, "plans-drh", agent="drh", category="plan")

        result = mcp_server.query_catalog(store_agent=AGENT, agent="drh", category="plan")
        assert result["count"] == 1

        result = mcp_server.query_graph(
            "MATCH (n:BioNode {network_uuid: 'plans-drh', node_type: 'action'}) "
            "RETURN n.name, n.properties",
            store_agent=AGENT,
        )
        assert result["status"] == "success"
        assert result["row_count"] == 5

        result = mcp_server.find_neighbors(
            "Map TRIM25 interactions", store_agent=AGENT, network_uuid="plans-drh"
        )
        assert result["count"] >= 3

        result = mcp_server.delete_cached_network("plans-drh", store_agent=AGENT)
        assert result["status"] == "success"
