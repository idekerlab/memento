"""NDEx MCP Server — exposes NDEx operations as MCP tools.

Run with:  python -m tools.ndex_mcp.server [--profile NAME]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import load_ndex_config
from .ndex_client_wrapper import NDExClientWrapper
from .network_builder import spec_to_cx2, cx2_to_summary, cx2_to_spec

mcp = FastMCP("ndex", log_level="INFO")

# Multi-profile support: default wrapper set at startup, per-profile cache for overrides.
_default_profile: str | None = None
_wrappers: dict[str | None, NDExClientWrapper] = {}


def _init_wrapper(profile: str | None = None) -> NDExClientWrapper:
    """Create the NDExClientWrapper for the given profile."""
    config = load_ndex_config(profile=profile)
    return NDExClientWrapper(config)


def _get_wrapper(profile: str | None = None) -> NDExClientWrapper:
    """Return a wrapper for the given profile, using cache.

    If profile is None, uses the default profile set at startup.
    Wrappers are lazily created and cached by profile name.
    """
    key = profile if profile is not None else _default_profile
    if key not in _wrappers:
        _wrappers[key] = _init_wrapper(key)
    return _wrappers[key]

# ── Search & Discovery ────────────────────────────────────────────────


@mcp.tool()
def search_networks(
    query: str,
    account_name: str | None = None,
    start: int = 0,
    size: int = 25,
) -> dict:
    """Search NDEx for networks matching a query string.

    Args:
        query: Search terms (e.g. gene names, pathway names).
        account_name: Restrict search to a specific account.
        start: Pagination offset.
        size: Number of results to return.
    """
    return _get_wrapper().search_networks(query, account_name=account_name, start=start, size=size)


@mcp.tool()
def get_network_summary(network_id: str) -> dict:
    """Get metadata for a single NDEx network.

    Args:
        network_id: UUID of the network.
    """
    return _get_wrapper().get_network_summary(network_id)


# NOTE ON MULTI-PROFILE SUPPORT:
# Write operations accept an optional `profile` parameter to authenticate
# as a specific agent (e.g., profile="drh"). The profile must exist in
# ~/.ndex/config.json under "profiles". If omitted, uses the default
# profile set at server startup (--profile flag).
# Read operations use the default profile (identity doesn't matter for reads).


# ── Network CRUD ──────────────────────────────────────────────────────


@mcp.tool()
def create_network(network_spec: str, profile: str | None = None) -> dict:
    """Create a new network on NDEx from a JSON specification.

    Args:
        network_spec: JSON string with the following structure:
            {
              "name": "My Network" (required),
              "description": "Optional description",
              "version": "1.0",
              "properties": {"key": "value", ...},
              "nodes": [
                {"id": 0, "v": {"name": "TP53", "type": "protein"}},
                {"id": 1, "v": {"name": "MDM2", "type": "protein"}}
              ],
              "edges": [
                {"source": 0, "target": 1, "v": {"interaction": "inhibits"}}
              ]
            }
            Node attributes go under "v" (or "attributes"). IDs are auto-assigned if omitted.
            Edge source/target use "source"/"target" (or "s"/"t"). Edge attributes go under "v" (or "attributes").
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    spec = json.loads(network_spec)
    cx2 = spec_to_cx2(spec)
    wrapper = _get_wrapper(profile)
    result = wrapper.create_network(cx2)
    if result["status"] == "success":
        network_url = result["data"]
        # Extract UUID from URL if it's a URL string
        uuid = network_url.split("/")[-1] if isinstance(network_url, str) and "/" in network_url else network_url
        result["data"] = {"network_id": uuid, "url": network_url}
        # NDEx defaults to index_level=NONE, making networks unsearchable.
        # Set to ALL so both public and private networks are discoverable.
        wrapper.set_network_system_properties(
            uuid, {"index_level": "ALL"}
        )
    return result


@mcp.tool()
def update_network(network_id: str, network_spec: str, profile: str | None = None) -> dict:
    """Replace an existing NDEx network with a new specification.

    Args:
        network_id: UUID of the network to update.
        network_spec: JSON string with the same format as create_network:
            nodes use "source"/"target" (or "s"/"t"), attributes under "v" (or "attributes").
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    spec = json.loads(network_spec)
    cx2 = spec_to_cx2(spec)
    return _get_wrapper(profile).update_network(network_id, cx2)


@mcp.tool()
def delete_network(network_id: str, profile: str | None = None) -> dict:
    """Delete a network from NDEx. Requires authentication.

    Args:
        network_id: UUID of the network to delete.
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    return _get_wrapper(profile).delete_network(network_id)


@mcp.tool()
def update_network_profile(
    network_id: str,
    name: str | None = None,
    description: str | None = None,
    version: str | None = None,
    profile: str | None = None,
) -> dict:
    """Update a network's profile (name, description, version).

    Args:
        network_id: UUID of the network.
        name: New network name.
        description: New description.
        version: New version string.
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    prof = {}
    if name is not None:
        prof["name"] = name
    if description is not None:
        prof["description"] = description
    if version is not None:
        prof["version"] = version
    if not prof:
        return {"status": "error", "message": "No profile fields provided", "error_type": "ValueError"}
    return _get_wrapper(profile).update_network_profile(network_id, prof)


@mcp.tool()
def set_network_properties(network_id: str, properties: str, profile: str | None = None) -> dict:
    """Set custom properties on a network.

    Args:
        network_id: UUID of the network.
        properties: JSON string — list of property dicts, each with keys:
            subNetworkId, predicateString, dataType, value.
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    props = json.loads(properties)
    return _get_wrapper(profile).set_network_properties(network_id, props)


# ── Download ──────────────────────────────────────────────────────────


@mcp.tool()
def download_network(network_id: str, output_dir: str | None = None) -> dict:
    """Download a network as CX2 JSON and return file path + summary stats.

    Args:
        network_id: UUID of the network to download.
        output_dir: Directory to save the file. Defaults to a temp directory.
    """
    result = _get_wrapper().download_network(network_id)
    if result["status"] != "success":
        return result

    raw_cx2 = result["data"]

    # Determine output path
    if output_dir:
        out_path = Path(output_dir)
    else:
        out_path = Path(tempfile.mkdtemp(prefix="ndex_"))
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{network_id}.cx2"
    file_path.write_text(json.dumps(raw_cx2, indent=2), encoding="utf-8")

    # Build summary from the CX2 data
    from ndex2.cx2 import CX2Network
    net = CX2Network()
    net.create_from_raw_cx2(raw_cx2)
    summary = cx2_to_summary(net)
    summary["file_path"] = str(file_path)

    return {"status": "success", "data": summary}


# ── Access Control ────────────────────────────────────────────────────


@mcp.tool()
def set_network_visibility(network_id: str, visibility: str, profile: str | None = None) -> dict:
    """Set a network's visibility to PUBLIC or PRIVATE.

    Args:
        network_id: UUID of the network.
        visibility: Either "PUBLIC" or "PRIVATE".
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    return _get_wrapper(profile).set_network_visibility(network_id, visibility)


@mcp.tool()
def set_network_read_only(network_id: str, value: bool, profile: str | None = None) -> dict:
    """Set or clear the read-only flag on a network.

    Args:
        network_id: UUID of the network.
        value: True to make read-only, False to make writable.
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    return _get_wrapper(profile).set_read_only(network_id, value)


@mcp.tool()
def share_network(network_id: str, username: str, permission: str, profile: str | None = None) -> dict:
    """Grant a user permission on a network.

    Args:
        network_id: UUID of the network.
        username: NDEx username to share with.
        permission: One of "READ", "WRITE", or "ADMIN".
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    return _get_wrapper(profile).share_network(network_id, username, permission)


# ── User Operations ───────────────────────────────────────────────────


@mcp.tool()
def get_user_info(username: str) -> dict:
    """Get profile information for an NDEx user.

    Args:
        username: NDEx username.
    """
    return _get_wrapper().get_user_info(username)


@mcp.tool()
def get_user_networks(
    username: str, offset: int = 0, limit: int = 25
) -> dict:
    """List networks owned by a user.

    Args:
        username: NDEx username.
        offset: Pagination offset.
        limit: Number of results to return.
    """
    return _get_wrapper().get_user_networks(username, offset=offset, limit=limit)


# ── Connection Management ─────────────────────────────────────────────


@mcp.tool()
def set_network_system_properties(network_id: str, properties: str, profile: str | None = None) -> dict:
    """Set system properties on a network (visibility, index_level, showcase, readOnly).

    Args:
        network_id: UUID of the network.
        properties: JSON string with any subset of keys:
            visibility ("PUBLIC" or "PRIVATE"),
            index_level ("NONE", "META", or "ALL"),
            showcase (true/false),
            readOnly (true/false).
        profile: NDEx profile to authenticate as (e.g. "drh"). Uses default if omitted.
    """
    props = json.loads(properties)
    return _get_wrapper(profile).set_network_system_properties(network_id, props)


@mcp.tool()
def get_connection_status(profile: str | None = None) -> dict:
    """Check current NDEx connection: server URL, username, auth status.

    Args:
        profile: NDEx profile to check. Uses default if omitted.
    """
    return _get_wrapper(profile).get_connection_status()


@mcp.tool()
def get_my_account_info(profile: str | None = None) -> dict:
    """Get the authenticated user's profile and network count.

    Args:
        profile: NDEx profile to check. Uses default if omitted.
    """
    return _get_wrapper(profile).get_my_account_info()


# ── Entry point ───────────────────────────────────────────────────────


def main():
    global _default_profile
    parser = argparse.ArgumentParser(description="NDEx MCP Server")
    parser.add_argument(
        "--profile",
        default=None,
        help="Default NDEx profile from ~/.ndex/config.json. "
        "Individual tool calls can override with their own profile parameter.",
    )
    args = parser.parse_args()
    _default_profile = args.profile
    # Pre-initialize the default wrapper to validate credentials at startup
    wrapper = _get_wrapper()
    user = wrapper._config.username or "anonymous"
    server = wrapper._config.server
    print(
        f"NDEx MCP server started — default_profile={args.profile or 'default'}, "
        f"user={user}, server={server} (multi-profile enabled)",
        file=sys.stderr,
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
