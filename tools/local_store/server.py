"""Local Store MCP Server — exposes local graph database operations as MCP tools.

Provides cached, queryable access to NDEx networks via a two-tier
local store (SQLite catalog + LadybugDB graph database).

Every tool requires an explicit ``store_agent`` parameter that selects
which agent's isolated cache to operate on (``~/.ndex/cache/<agent>/``).
Tools that interact with NDEx also require an explicit ``profile``
parameter identifying the NDEx server and credentials.

Run with:  python -m tools.local_store.server
Optional:  python -m tools.local_store.server --agent-scope <agent_name>
"""

import argparse
import atexit
import json
import signal
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from ndex2.cx2 import CX2Network

from tools.ndex_mcp.config import load_ndex_config, has_credentials
from tools.ndex_mcp.ndex_client_wrapper import NDExClientWrapper
from tools.local_store.store import LocalStore

# ── Agent scope (set from --agent-scope CLI flag) ────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Store MCP server")
    parser.add_argument("--profile", default=None,
        help="Default NDEx profile (unused by server; kept for config compat).")
    parser.add_argument("--agent-scope", default=None,
        help="Restrict this server to one agent's cache. "
             "Tool calls with a different store_agent are rejected immediately "
             "before any database is opened. Use the local_store_<agent> MCP "
             "entry for each agent's scheduled tasks.")
    return parser.parse_args()


_args = _parse_args()
_AGENT_SCOPE: str | None = _args.agent_scope

_SCOPE_VIOLATION_TMPL = (
    "This local_store server is scoped to agent '{scope}'. "
    "Received store_agent='{got}'. "
    "Use the local_store_{got} MCP server entry for that agent."
)


def _check_scope(store_agent: str) -> dict | None:
    """Return error dict if store_agent violates the server's scope, else None.

    If no scope was set (unscoped server for interactive multi-agent queries),
    this always returns None and any store_agent is accepted.
    """
    if _AGENT_SCOPE and store_agent != _AGENT_SCOPE:
        return {
            "status": "error",
            "message": _SCOPE_VIOLATION_TMPL.format(scope=_AGENT_SCOPE, got=store_agent),
        }
    return None


mcp = FastMCP("local_store", log_level="INFO")

# Caches keyed by agent name / profile name.
_stores: dict[str, LocalStore] = {}
_ndex_clients: dict[str, NDExClientWrapper] = {}

_STORE_AGENT_REQUIRED_MSG = (
    "store_agent is required — specify which agent's local cache to use "
    "(e.g. store_agent='rgiskard'). Each agent has an isolated cache "
    "at ~/.ndex/cache/<agent>/."
)

_PROFILE_REQUIRED_MSG = (
    "profile is required — specify which NDEx server/identity to use "
    "(e.g. profile='local-rgiskard' or profile='rdaneel'). "
    "Profiles are defined in ~/.ndex/config.json."
)


def _get_store(store_agent: str) -> LocalStore:
    """Get a LocalStore for the given agent. Each agent has isolated storage."""
    cache_dir = Path.home() / ".ndex" / "cache" / store_agent
    key = store_agent
    if key not in _stores:
        _stores[key] = LocalStore(cache_dir=cache_dir)
    return _stores[key]


def _get_ndex(profile: str) -> NDExClientWrapper | None:
    """Get an NDEx client for the given profile."""
    if profile not in _ndex_clients:
        try:
            config = load_ndex_config(profile=profile)
            if has_credentials(config):
                _ndex_clients[profile] = NDExClientWrapper(config)
            else:
                return None
        except (ValueError, FileNotFoundError):
            return None
    return _ndex_clients.get(profile)


def _require_store(store_agent: str | None) -> tuple[LocalStore | None, dict | None]:
    """Return (store, None) or (None, error_dict) if store_agent is missing."""
    if not store_agent:
        return None, {"status": "error", "message": _STORE_AGENT_REQUIRED_MSG}
    return _get_store(store_agent), None


def _require_ndex(profile: str | None) -> tuple[NDExClientWrapper | None, dict | None]:
    """Return (ndex, None) or (None, error_dict) if profile is missing."""
    if not profile:
        return None, {"status": "error", "message": _PROFILE_REQUIRED_MSG}
    ndex = _get_ndex(profile)
    if ndex is None:
        return None, {"status": "error", "message": f"NDEx client not configured for profile '{profile}'"}
    return ndex, None


# ── Catalog Operations ───────────────────────────────────────────────


@mcp.tool()
def query_catalog(
    store_agent: str,
    category: str | None = None,
    agent: str | None = None,
    data_type: str | None = None,
) -> dict:
    """List cached networks, optionally filtered by category, agent, or data_type.

    Categories: science-kg, interaction-data, plan, episodic-memory,
    collaborator-map, review-log, request, message.

    Args:
        store_agent: Which agent's local cache to query (required).
        category: Filter by network category.
        agent: Filter by owning agent in catalog metadata (rdaneel, drh, etc.).
        data_type: Filter by data type (graph, tabular, agent-state).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    filters = {}
    if category:
        filters["category"] = category
    if agent:
        filters["agent"] = agent
    if data_type:
        filters["data_type"] = data_type
    results = store.query_catalog(**filters)
    return {
        "status": "success",
        "count": len(results),
        "networks": results,
    }


@mcp.tool()
def get_cached_network(network_uuid: str, store_agent: str) -> dict:
    """Get catalog metadata for a cached network.

    Args:
        network_uuid: UUID of the network.
        store_agent: Which agent's local cache to query (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    entry = store.get_catalog_entry(network_uuid)
    if entry is None:
        return {"status": "error", "message": f"Network {network_uuid} not in cache"}
    return {"status": "success", "data": entry}


# ── Graph Queries ────────────────────────────────────────────────────


@mcp.tool()
def query_graph(cypher: str, store_agent: str) -> dict:
    """Execute a Cypher query against the local graph database.

    Schema:
        Node tables: BioNode, Network
        Relationship tables: Interacts (BioNode→BioNode), InNetwork (BioNode→Network)

    BioNode columns: id, cx2_id, network_uuid, name, node_type, properties (MAP)
    Interacts columns: edge_id, network_uuid, interaction, properties (MAP)
    Network columns: uuid, name, description, properties (MAP)

    IMPORTANT — properties is a MAP(STRING, STRING) column. LadybugDB does NOT
    support dot-access on MAP columns (e.g. `a.properties.status` will fail).
    Instead, filter by indexed columns (name, node_type, network_uuid) in Cypher,
    then filter by properties values in your own logic after receiving results.

    Example queries:
    - All actions in a plans network:
      MATCH (a:BioNode {network_uuid: '<uuid>'}) WHERE a.node_type = 'action'
      RETURN a.name, a.properties
      (then filter by properties['status'] == 'active' in your code)

    - Neighborhood: MATCH (n:BioNode {name: 'TRIM25'})-[r:Interacts]-(m) RETURN m.name, r.interaction
    - Cross-network: MATCH (n:BioNode)-[:InNetwork]->(net1:Network {uuid: 'X'}) ...
    - Path: MATCH path = (a:BioNode {name: 'NS1'})-[:Interacts*1..3]-(b:BioNode {name: 'RIG-I'}) RETURN path

    Args:
        cypher: Cypher query string.
        store_agent: Which agent's local cache to query (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    try:
        rows = store.query_graph(cypher)
        return {
            "status": "success",
            "row_count": len(rows),
            "rows": rows,
        }
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_network_nodes(network_uuid: str, store_agent: str) -> dict:
    """Get all nodes for a cached network.

    Args:
        network_uuid: UUID of the network.
        store_agent: Which agent's local cache to query (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    nodes = store.graph.get_network_nodes(network_uuid)
    return {
        "status": "success",
        "count": len(nodes),
        "nodes": nodes,
    }


@mcp.tool()
def get_network_edges(network_uuid: str, store_agent: str) -> dict:
    """Get all edges for a cached network.

    Args:
        network_uuid: UUID of the network.
        store_agent: Which agent's local cache to query (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    edges = store.graph.get_network_edges(network_uuid)
    return {
        "status": "success",
        "count": len(edges),
        "edges": edges,
    }


@mcp.tool()
def find_neighbors(node_name: str, store_agent: str, network_uuid: str | None = None) -> dict:
    """Find all neighbors of a node by name.

    Args:
        node_name: Name of the node to find neighbors for.
        store_agent: Which agent's local cache to query (required).
        network_uuid: Optional — restrict to a specific network.
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    if network_uuid:
        query = (
            "MATCH (n:BioNode {name: $name, network_uuid: $uuid})"
            "-[r:Interacts]-(m:BioNode) "
            "RETURN m.name, m.node_type, r.interaction, r.network_uuid"
        )
        rows = store.query_graph(query, {"name": node_name, "uuid": network_uuid})
    else:
        query = (
            "MATCH (n:BioNode {name: $name})-[r:Interacts]-(m:BioNode) "
            "RETURN DISTINCT m.name, m.node_type, r.interaction, r.network_uuid"
        )
        rows = store.query_graph(query, {"name": node_name})
    neighbors = [
        {"name": r[0], "type": r[1], "interaction": r[2], "network_uuid": r[3]}
        for r in rows
    ]
    return {"status": "success", "count": len(neighbors), "neighbors": neighbors}


@mcp.tool()
def find_path(
    source_name: str,
    target_name: str,
    store_agent: str,
    max_hops: int = 4,
) -> dict:
    """Find paths between two nodes by name across all cached networks.

    Args:
        source_name: Name of the source node.
        target_name: Name of the target node.
        store_agent: Which agent's local cache to query (required).
        max_hops: Maximum path length (default 4).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    query = (
        f"MATCH path = (a:BioNode {{name: $src}})"
        f"-[:Interacts*1..{max_hops}]-"
        f"(b:BioNode {{name: $tgt}}) "
        f"RETURN nodes(path), length(path) AS hops "
        f"ORDER BY hops LIMIT 10"
    )
    try:
        rows = store.query_graph(query, {"src": source_name, "tgt": target_name})
        paths = []
        for r in rows:
            node_names = [n.get("name", "") if isinstance(n, dict) else str(n) for n in r[0]]
            paths.append({"nodes": node_names, "hops": r[1]})
        return {"status": "success", "count": len(paths), "paths": paths}
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def find_contradictions(network_uuid_1: str, network_uuid_2: str, store_agent: str) -> dict:
    """Find contradictions: same node pair with opposite interaction types across two networks.

    Args:
        network_uuid_1: UUID of the first network.
        network_uuid_2: UUID of the second network.
        store_agent: Which agent's local cache to query (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    query = (
        "MATCH (a:BioNode)-[r1:Interacts {network_uuid: $uuid1}]->(b:BioNode), "
        "      (c:BioNode)-[r2:Interacts {network_uuid: $uuid2}]->(d:BioNode) "
        "WHERE a.name = c.name AND b.name = d.name "
        "  AND ((r1.interaction CONTAINS 'ecreases' AND r2.interaction CONTAINS 'ncreases') "
        "    OR (r1.interaction CONTAINS 'ncreases' AND r2.interaction CONTAINS 'ecreases')) "
        "RETURN a.name, b.name, r1.interaction, r2.interaction"
    )
    rows = store.query_graph(query, {"uuid1": network_uuid_1, "uuid2": network_uuid_2})
    contradictions = [
        {
            "source": r[0], "target": r[1],
            "interaction_1": r[2], "interaction_2": r[3],
            "network_1": network_uuid_1, "network_2": network_uuid_2,
        }
        for r in rows
    ]
    return {"status": "success", "count": len(contradictions), "contradictions": contradictions}


# ── Cache Management ─────────────────────────────────────────────────


@mcp.tool()
def cache_network(
    network_uuid: str,
    store_agent: str,
    profile: str,
    agent: str | None = None,
    category: str | None = None,
) -> dict:
    """Download a network from NDEx and cache it in the local store.

    Downloads the CX2 data, imports it into the graph database, and
    creates a catalog entry. If the network is already cached, it is
    re-downloaded and replaced.

    The source NDEx profile is recorded in the catalog so the agent
    knows which server the network came from.

    Node/edge attributes are stored in the graph as MAP(STRING, STRING).
    All values are coerced to strings. Nested objects are not preserved —
    use flat key-value attributes when creating networks.

    Args:
        network_uuid: NDEx UUID of the network to cache.
        store_agent: Which agent's local cache to write to (required).
        profile: NDEx profile to download from (required).
        agent: Owning agent name in catalog metadata (rdaneel, drh, etc.).
        category: Network category override.
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    ndex, err = _require_ndex(profile)
    if err:
        return err

    # Download from NDEx
    dl_result = ndex.download_network(network_uuid)
    if dl_result["status"] != "success":
        return dl_result

    # Parse CX2
    cx2 = CX2Network()
    cx2.create_from_raw_cx2(dl_result["data"])

    # Import to local store
    stats = store.import_network(
        cx2, network_uuid, agent=agent, category=category,
        source_profile=profile,
    )

    # Get NDEx modification timestamp
    summary = ndex.get_network_summary(network_uuid)
    if summary["status"] == "success":
        ndex_modified = str(summary["data"].get("modificationTime", ""))
        store.mark_published(network_uuid, ndex_modified=ndex_modified)

    return {
        "status": "success",
        "data": {
            "network_uuid": network_uuid,
            "node_count": stats["node_count"],
            "edge_count": stats["edge_count"],
            "name": (cx2.get_network_attributes() or {}).get("name", ""),
            "source_profile": profile,
        },
    }


def _make_network_public(ndex: NDExClientWrapper, network_id: str) -> dict | None:
    """Set a network to PUBLIC, searchable (index_level=ALL), and showcased."""
    props = {"visibility": "PUBLIC", "index_level": "ALL", "showcase": True}
    result = ndex.set_network_system_properties(network_id, props)
    if result["status"] != "success":
        return result
    return None


@mcp.tool()
def publish_network(
    network_uuid: str,
    store_agent: str,
    profile: str,
) -> dict:
    """Update an existing network on NDEx with the local cached version.

    The network must already exist on NDEx and the authenticated user
    must have write permission. After updating, the network is made
    PUBLIC, searchable, and showcased by default.

    Use save_new_network instead when:
    - The source network is read-only or owned by someone else.
    - You want to create a modified copy rather than overwriting.

    Args:
        network_uuid: UUID of the cached network to update on NDEx.
        store_agent: Which agent's local cache to publish from (required).
        profile: NDEx profile for publishing (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    ndex, err = _require_ndex(profile)
    if err:
        return err

    entry = store.get_catalog_entry(network_uuid)
    if entry is None:
        return {"status": "error", "message": f"Network {network_uuid} not in cache"}

    # Export from graph
    cx2 = store.export_network(network_uuid)

    # Update existing network on NDEx
    result = ndex.update_network(network_uuid, cx2)

    if result["status"] == "success":
        pub_err = _make_network_public(ndex, network_uuid)
        if pub_err:
            result["visibility_warning"] = pub_err["message"]

        summary = ndex.get_network_summary(network_uuid)
        ndex_modified = ""
        if summary["status"] == "success":
            ndex_modified = str(summary["data"].get("modificationTime", ""))
        store.mark_published(network_uuid, ndex_modified=ndex_modified)

    return result


@mcp.tool()
def save_new_network(
    network_uuid: str,
    store_agent: str,
    profile: str,
    name: str | None = None,
) -> dict:
    """Export a cached network and save it as a NEW network on NDEx.

    Creates a fresh network under the authenticated user's account,
    regardless of where the original came from. The new network is
    made PUBLIC, searchable, and showcased by default.

    Use this when:
    - The source network is read-only or owned by someone else.
    - You want to publish a modified copy without overwriting the original.

    Use publish_network instead when you want to update an existing
    network in place.

    Args:
        network_uuid: UUID of the cached network to export.
        store_agent: Which agent's local cache to export from (required).
        profile: NDEx profile for publishing (required).
        name: Optional new name for the network. If omitted, keeps the cached name.
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    ndex, err = _require_ndex(profile)
    if err:
        return err

    entry = store.get_catalog_entry(network_uuid)
    if entry is None:
        return {"status": "error", "message": f"Network {network_uuid} not in cache"}

    cx2 = store.export_network(network_uuid)

    if name:
        attrs = cx2.get_network_attributes()
        if isinstance(attrs, dict):
            attrs["name"] = name
            cx2.set_network_attributes(attrs)
        else:
            cx2.set_name(name)

    result = ndex.create_network(cx2)

    if result["status"] == "success":
        new_network_id = result["data"]
        if isinstance(new_network_id, str) and "/" in new_network_id:
            new_network_id = new_network_id.rstrip("/").split("/")[-1]

        pub_err = _make_network_public(ndex, new_network_id)
        if pub_err:
            result["visibility_warning"] = pub_err["message"]

        result["data"] = {
            "network_id": new_network_id,
            "url": f"https://www.ndexbio.org/v3/networks/{new_network_id}",
            "source_uuid": network_uuid,
        }

    return result


@mcp.tool()
def check_staleness(
    network_uuid: str,
    store_agent: str,
    profile: str,
) -> dict:
    """Check if a cached network is stale compared to NDEx.

    Args:
        network_uuid: UUID of the cached network.
        store_agent: Which agent's local cache to check (required).
        profile: NDEx profile for checking (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    ndex, err = _require_ndex(profile)
    if err:
        return err

    entry = store.get_catalog_entry(network_uuid)
    if entry is None:
        return {"status": "error", "message": f"Network {network_uuid} not in cache"}

    summary = ndex.get_network_summary(network_uuid)
    if summary["status"] != "success":
        return summary

    current_modified = str(summary["data"].get("modificationTime", ""))
    cached_modified = entry.get("ndex_modified", "")
    is_stale = current_modified != cached_modified

    return {
        "status": "success",
        "data": {
            "network_uuid": network_uuid,
            "is_stale": is_stale,
            "cached_modified": cached_modified,
            "ndex_modified": current_modified,
            "is_dirty": bool(entry.get("is_dirty")),
        },
    }


@mcp.tool()
def delete_cached_network(network_uuid: str, store_agent: str) -> dict:
    """Remove a network from the local cache (does not affect NDEx).

    Args:
        network_uuid: UUID of the network to remove.
        store_agent: Which agent's local cache to delete from (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    entry = store.get_catalog_entry(network_uuid)
    if entry is None:
        return {"status": "error", "message": f"Network {network_uuid} not in cache"}
    store.delete_network(network_uuid)
    return {"status": "success", "message": f"Removed {network_uuid} from cache"}


# ── Session Initialization ──────────────────────────────────────────


@mcp.tool()
def clear_cache(store_agent: str) -> dict:
    """Delete all networks from the local cache.

    Removes every network from both the graph database and the SQLite
    catalog. Does not affect NDEx. Use this at session start for a
    clean slate before re-caching self-knowledge networks.

    Args:
        store_agent: Which agent's local cache to clear (required).
    """
    err = _check_scope(store_agent)
    if err:
        return err
    store, err = _require_store(store_agent)
    if err:
        return err
    count = store.clear_all()
    return {
        "status": "success",
        "message": f"Cleared {count} networks from {store_agent} cache",
        "networks_removed": count,
    }


@mcp.tool()
def session_init(
    agent: str,
    profile: str,
    self_network_uuids: dict | None = None,
) -> dict:
    """Procedural session initialization: clear cache, fetch self-knowledge, return context.

    This tool automates the mechanical parts of session startup:
    1. Clears the local cache (clean slate)
    2. Downloads and caches the agent's self-knowledge networks from NDEx
    3. Queries active plans and last session from the freshly cached data
    4. Returns everything the agent needs to begin reasoning

    The agent still handles social feed checking and action selection.

    Args:
        agent: Agent name (e.g. "rdaneel"). Used as store_agent and
               to construct self-knowledge network names if UUIDs not provided.
        profile: NDEx profile for downloading (required).
        self_network_uuids: Optional dict mapping self-knowledge types to NDEx
            UUIDs. Keys: "session_history", "plans", "collaborator_map",
            "papers_read", "procedures". If omitted, searches NDEx for networks
            named "<agent>-session-history", etc.

            Note on "procedures": this is the fifth standard self-knowledge
            network (SHARED.md §Procedural Knowledge). Agents without a
            "<agent>-procedures" network yet will have it silently skipped —
            the search returns numFound=0 and no error is raised.
    """
    err = _check_scope(agent)
    if err:
        return err
    ndex, err = _require_ndex(profile)
    if err:
        return err

    store = _get_store(agent)

    # Step 1: Clear cache
    cleared = store.clear_all()

    # Step 2: Resolve self-knowledge network UUIDs
    #
    # SHARED.md §Self-Knowledge Networks defines five standard networks.
    # The fifth ("procedures") was added 2026-04-18; agents that haven't
    # bootstrapped a procedures network yet will have it silently skipped
    # below (search returns numFound=0 → the key is never added to `uuids`).
    sk_types = ["session-history", "plans", "collaborator-map", "papers-read", "procedures"]
    uuids = {}

    if self_network_uuids:
        key_map = {
            "session_history": "session-history",
            "plans": "plans",
            "collaborator_map": "collaborator-map",
            "papers_read": "papers-read",
            "procedures": "procedures",
        }
        for param_key, sk_key in key_map.items():
            if param_key in self_network_uuids:
                uuids[sk_key] = self_network_uuids[param_key]
    else:
        for sk_type in sk_types:
            name = f"{agent}-{sk_type}"
            search_result = ndex.search_networks(
                query=name, account_name=agent, start=0, size=1
            )
            if (search_result["status"] == "success"
                    and search_result["data"].get("numFound", 0) > 0):
                nets = search_result["data"]["networks"]
                if nets:
                    uuids[sk_type] = nets[0]["externalId"]

    # Step 3: Cache each self-knowledge network
    cached = {}
    errors = {}
    for sk_type, uuid in uuids.items():
        try:
            dl_result = ndex.download_network(uuid)
            if dl_result["status"] != "success":
                errors[sk_type] = dl_result.get("message", "download failed")
                continue

            cx2 = CX2Network()
            cx2.create_from_raw_cx2(dl_result["data"])
            stats = store.import_network(
                cx2, uuid, agent=agent, category=sk_type,
                source_profile=profile,
            )

            summary = ndex.get_network_summary(uuid)
            if summary["status"] == "success":
                ndex_modified = str(summary["data"].get("modificationTime", ""))
                store.mark_published(uuid, ndex_modified=ndex_modified)

            cached[sk_type] = {
                "uuid": uuid,
                "node_count": stats["node_count"],
                "edge_count": stats["edge_count"],
                "name": (cx2.get_network_attributes() or {}).get("name", ""),
            }
        except Exception as e:
            errors[sk_type] = str(e)

    # Step 4: Query plans and last session from freshly cached data
    active_plans = []
    last_session = None

    if "plans" in uuids:
        try:
            rows = store.query_graph(
                "MATCH (a:BioNode {network_uuid: $uuid}) "
                "WHERE a.node_type = 'action' "
                "RETURN a.name, a.properties",
                {"uuid": uuids["plans"]},
            )
            all_plans = [{"name": r[0], "properties": r[1]} for r in rows]
            active_plans = [p for p in all_plans if p["properties"].get("status") == "active"]
        except Exception:
            pass

    if "session-history" in uuids:
        try:
            rows = store.query_graph(
                "MATCH (s:BioNode {network_uuid: $uuid}) "
                "RETURN s.name, s.properties "
                "ORDER BY s.cx2_id DESC LIMIT 1",
                {"uuid": uuids["session-history"]},
            )
            if rows:
                last_session = {"name": rows[0][0], "properties": rows[0][1]}
        except Exception:
            pass

    # Step 5: Get full catalog for reference
    catalog = store.query_catalog()

    return {
        "status": "success",
        "data": {
            "cache_cleared": cleared,
            "self_knowledge": cached,
            "errors": errors,
            "active_plans": active_plans,
            "last_session": last_session,
            "catalog": catalog,
            "self_network_uuids": uuids,
        },
    }


# ── Shutdown: checkpoint + close ─────────────────────────────────────

def _shutdown_local_stores() -> None:
    """Best-effort CHECKPOINT + close of every open agent store.

    Kuzu does not auto-checkpoint on Database destruction (upstream issue
    #4013), so abrupt process exit leaves uncommitted writes in the WAL.
    A torn record at the tail then blocks the next open with "Corrupted
    wal file." Running CHECKPOINT on graceful shutdown folds the WAL into
    the main db file and truncates it. SIGKILL still leaves a stale WAL,
    which GraphStore._open_database_with_wal_recovery handles at open time.
    """
    for agent, store in list(_stores.items()):
        try:
            store.graph.conn.execute("CHECKPOINT")
        except Exception as e:
            print(
                f"local_store shutdown: CHECKPOINT failed for '{agent}': {e}",
                file=sys.stderr,
            )
        try:
            store.close()
        except Exception as e:
            print(
                f"local_store shutdown: close failed for '{agent}': {e}",
                file=sys.stderr,
            )
        _stores.pop(agent, None)


def _sigterm_handler(signum, frame):
    # Raising SystemExit runs atexit callbacks; the default SIGTERM disposition
    # does not. SIGINT already flows through KeyboardInterrupt → atexit, so we
    # only need an explicit handler for SIGTERM.
    sys.exit(0)


atexit.register(_shutdown_local_stores)
signal.signal(signal.SIGTERM, _sigterm_handler)


# ── Entry point ──────────────────────────────────────────────────────


def main():
    if _AGENT_SCOPE:
        print(
            f"Local Store MCP server started — scoped to agent '{_AGENT_SCOPE}'. "
            f"Tool calls for other agents will be rejected before opening any database.",
            file=sys.stderr,
        )
    else:
        print(
            "Local Store MCP server started (unscoped) — accepts any store_agent. "
            "NOTE: this server will open and hold locks on every agent's cache it receives. "
            "For scheduled tasks, use local_store_<agent> scoped entries instead.",
            file=sys.stderr,
        )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
