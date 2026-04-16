"""NDEx MCP Server — exposes NDEx operations as MCP tools.

Every tool requires an explicit `profile` parameter that identifies
which NDEx server and credentials to use.  Profiles are defined in
``~/.ndex/config.json`` under the ``"profiles"`` key.

Run with:  python -m tools.ndex_mcp.server
"""

import json
import sys
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import load_ndex_config
from .ndex_client_wrapper import NDExClientWrapper
from .network_builder import spec_to_cx2, cx2_to_summary, cx2_to_spec

mcp = FastMCP("ndex", log_level="INFO")

# Profile-keyed wrapper cache (lazily populated).
_wrappers: dict[str, NDExClientWrapper] = {}

_PROFILE_REQUIRED_MSG = (
    "profile is required — specify which NDEx server/identity to use "
    "(e.g. profile='local-rgiskard' or profile='rdaneel'). "
    "Profiles are defined in ~/.ndex/config.json."
)


def _get_wrapper(profile: str | None) -> NDExClientWrapper | None:
    """Return a wrapper for the given profile, using cache.

    Returns None if profile is not provided.
    """
    if profile is None:
        return None
    if profile not in _wrappers:
        config = load_ndex_config(profile=profile)
        _wrappers[profile] = NDExClientWrapper(config)
    return _wrappers[profile]


def _require_wrapper(profile: str | None) -> tuple[NDExClientWrapper | None, dict | None]:
    """Return (wrapper, None) or (None, error_dict) if profile is missing."""
    if profile is None:
        return None, {"status": "error", "message": _PROFILE_REQUIRED_MSG}
    try:
        return _get_wrapper(profile), None
    except (ValueError, FileNotFoundError) as e:
        return None, {"status": "error", "message": str(e)}


# ── Search & Discovery ────────────────────────────────────────────────


@mcp.tool()
def search_networks(
    query: str,
    profile: str,
    account_name: str | None = None,
    start: int = 0,
    size: int = 25,
) -> dict:
    """Search NDEx for networks matching a query string.

    Args:
        query: Search terms (e.g. gene names, pathway names).
        profile: NDEx profile (required). Identifies server and credentials.
        account_name: Restrict search to a specific account.
        start: Pagination offset.
        size: Number of results to return.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.search_networks(query, account_name=account_name, start=start, size=size)


@mcp.tool()
def get_network_summary(network_id: str, profile: str) -> dict:
    """Get metadata for a single NDEx network.

    Args:
        network_id: UUID of the network.
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.get_network_summary(network_id)


# ── Network CRUD ──────────────────────────────────────────────────────


@mcp.tool()
def create_network(network_spec: str, profile: str) -> dict:
    """Create a new network on NDEx from a JSON specification.

    IMPORTANT — attribute values must be flat (strings, numbers, booleans).
    Nested dicts or lists of dicts are NOT supported by CX2 and will cause errors.

    Good: {"name": "TP53", "type": "protein", "status": "active", "priority": "high"}
    Bad:  {"name": "TP53", "properties": {"status": "active", "priority": "high"}}

    Args:
        network_spec: JSON string with the following structure:
            {
              "name": "My Network" (required),
              "description": "Optional description",
              "version": "1.0",
              "properties": {"key": "value", ...},
              "nodes": [
                {"id": 0, "v": {"name": "TP53", "type": "protein", "status": "active"}},
                {"id": 1, "v": {"name": "MDM2", "type": "protein"}}
              ],
              "edges": [
                {"source": 0, "target": 1, "v": {"interaction": "inhibits"}}
              ]
            }
            Node attributes go under "v" (or "attributes"). All values must be flat
            (string, number, boolean) — no nested objects or arrays.
            IDs are auto-assigned if omitted.
            Edge source/target use "source"/"target" (or "s"/"t").
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    spec = json.loads(network_spec)
    cx2 = spec_to_cx2(spec)
    result = wrapper.create_network(cx2)
    if result["status"] == "success":
        network_url = result["data"]
        uuid = network_url.split("/")[-1] if isinstance(network_url, str) and "/" in network_url else network_url
        result["data"] = {"network_id": uuid, "url": network_url}
        wrapper.set_network_system_properties(
            uuid, {"index_level": "ALL"}
        )
    return result


@mcp.tool()
def update_network(network_id: str, network_spec: str, profile: str) -> dict:
    """Replace an existing NDEx network with a new specification.

    Args:
        network_id: UUID of the network to update.
        network_spec: JSON string with the same format as create_network:
            nodes use "source"/"target" (or "s"/"t"), attributes under "v" (or "attributes").
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    spec = json.loads(network_spec)
    cx2 = spec_to_cx2(spec)
    return wrapper.update_network(network_id, cx2)


@mcp.tool()
def delete_network(network_id: str, profile: str) -> dict:
    """Delete a network from NDEx. Requires authentication.

    Args:
        network_id: UUID of the network to delete.
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.delete_network(network_id)


@mcp.tool()
def update_network_profile(
    network_id: str,
    profile: str,
    name: str | None = None,
    description: str | None = None,
    version: str | None = None,
) -> dict:
    """Update a network's profile (name, description, version).

    Args:
        network_id: UUID of the network.
        profile: NDEx profile (required). Identifies server and credentials.
        name: New network name.
        description: New description.
        version: New version string.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    prof = {}
    if name is not None:
        prof["name"] = name
    if description is not None:
        prof["description"] = description
    if version is not None:
        prof["version"] = version
    if not prof:
        return {"status": "error", "message": "No profile fields provided", "error_type": "ValueError"}
    return wrapper.update_network_profile(network_id, prof)


@mcp.tool()
def set_network_properties(network_id: str, properties: str, profile: str) -> dict:
    """Set custom properties on a network.

    Args:
        network_id: UUID of the network.
        properties: JSON string — list of property dicts, each with keys:
            subNetworkId, predicateString, dataType, value.
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    props = json.loads(properties)
    return wrapper.set_network_properties(network_id, props)


# ── Download ──────────────────────────────────────────────────────────


@mcp.tool()
def download_network(network_id: str, profile: str, output_dir: str | None = None) -> dict:
    """Download a network as CX2 JSON and return file path + summary stats.

    Args:
        network_id: UUID of the network to download.
        profile: NDEx profile (required). Identifies server and credentials.
        output_dir: Directory to save the file. Defaults to a temp directory.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    result = wrapper.download_network(network_id)
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
def set_network_visibility(network_id: str, visibility: str, profile: str) -> dict:
    """Set a network's visibility to PUBLIC or PRIVATE.

    Args:
        network_id: UUID of the network.
        visibility: Either "PUBLIC" or "PRIVATE".
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.set_network_visibility(network_id, visibility)


@mcp.tool()
def set_network_read_only(network_id: str, value: bool, profile: str) -> dict:
    """Set or clear the read-only flag on a network.

    Args:
        network_id: UUID of the network.
        value: True to make read-only, False to make writable.
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.set_read_only(network_id, value)


@mcp.tool()
def share_network(network_id: str, username: str, permission: str, profile: str) -> dict:
    """Grant a user permission on a network.

    Args:
        network_id: UUID of the network.
        username: NDEx username to share with.
        permission: One of "READ", "WRITE", or "ADMIN".
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.share_network(network_id, username, permission)


# ── User Operations ───────────────────────────────────────────────────


@mcp.tool()
def get_user_info(username: str, profile: str) -> dict:
    """Get profile information for an NDEx user.

    Args:
        username: NDEx username.
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.get_user_info(username)


@mcp.tool()
def get_user_networks(
    username: str, profile: str, offset: int = 0, limit: int = 25,
) -> dict:
    """List networks owned by a user.

    Args:
        username: NDEx username.
        profile: NDEx profile (required). Identifies server and credentials.
        offset: Pagination offset.
        limit: Number of results to return.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.get_user_networks(username, offset=offset, limit=limit)


# ── Connection Management ─────────────────────────────────────────────


@mcp.tool()
def set_network_system_properties(network_id: str, properties: str, profile: str) -> dict:
    """Set system properties on a network (visibility, index_level, showcase, readOnly).

    Args:
        network_id: UUID of the network.
        properties: JSON string with any subset of keys:
            visibility ("PUBLIC" or "PRIVATE"),
            index_level ("NONE", "META", or "ALL"),
            showcase (true/false),
            readOnly (true/false).
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    props = json.loads(properties)
    return wrapper.set_network_system_properties(network_id, props)


@mcp.tool()
def get_connection_status(profile: str) -> dict:
    """Check current NDEx connection: server URL, username, auth status.

    Args:
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.get_connection_status()


@mcp.tool()
def get_my_account_info(profile: str) -> dict:
    """Get the authenticated user's profile and network count.

    Args:
        profile: NDEx profile (required). Identifies server and credentials.
    """
    wrapper, err = _require_wrapper(profile)
    if err:
        return err
    return wrapper.get_my_account_info()


# ── Entry point ───────────────────────────────────────────────────────


def main():
    print(
        "NDEx MCP server started — no default profile, "
        "all tools require explicit profile parameter",
        file=sys.stderr,
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
