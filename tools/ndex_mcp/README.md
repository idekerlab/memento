# NDEx MCP Server

MCP server exposing 15 NDEx database operations as tools. Uses FastMCP with stdio transport.

## Architecture

```
server.py              -- FastMCP entry point, 15 @mcp.tool() functions
ndex_client_wrapper.py -- Thin wrapper around ndex2.client.Ndex2, lazy-init, uniform error dicts
network_builder.py     -- JSON spec <-> CX2Network conversion
config.py              -- Reads ~/.ndex/config.json (read-only)
```

## Running

```bash
python -m tools.ndex_mcp.server          # stdio transport
```

## Credentials

Place in `~/.ndex/config.json`:
```json
{
  "server": "https://www.ndexbio.org",
  "username": "rdaneel",
  "password": "<password>"
}
```

Anonymous mode (search/download only) works without credentials.

## Testing

```bash
# Unit tests (42 tests, all mocked, no network needed)
python -m pytest tools/ndex_mcp/tests/ -v

# Integration test against live NDEx server (needs network + credentials)
python tools/ndex_mcp/integration_test.py
```

## Tools (15 total)

| Tool | Auth? | Description |
|------|-------|-------------|
| `search_networks` | No | Search by query string |
| `get_network_summary` | No | Get network metadata by UUID |
| `create_network` | Yes | Create from JSON spec |
| `update_network` | Yes | Replace network content |
| `delete_network` | Yes | Delete by UUID |
| `update_network_profile` | Yes | Update name/description/version |
| `set_network_properties` | Yes | Set custom properties |
| `download_network` | No | Download as CX2 JSON file |
| `set_network_visibility` | Yes | PUBLIC or PRIVATE |
| `set_network_read_only` | Yes | Toggle read-only flag |
| `share_network` | Yes | Grant user permission |
| `get_user_info` | No | User profile by username |
| `get_user_networks` | No | List user's networks |
| `get_connection_status` | No | Current server/auth status |
| `get_my_account_info` | Yes | Authenticated user's profile + network count |

## Error handling

All wrapper methods return `{"status": "success", "data": ...}` or `{"status": "error", "message": ..., "error_type": ...}`. Connection failures (including Ndex2 constructor errors) are caught within this pattern.
