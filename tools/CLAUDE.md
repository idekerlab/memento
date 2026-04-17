# MCP Server Configuration Guide

## Authoritative Config Location

**One file wires up MCPs for every Memento agent:**

```
~/Documents/agents/.mcp.json
```

The desktop Claude app reads this when the "agents" project is opened. Memento is a sibling directory under `agents/GitHub/memento/`; this repo provides the Python implementations of the servers, but the config lives one level up.

**Do not create a `.mcp.json` inside `memento/` itself.** Prior versions of this repo had one, and it caused extended confusion — agents (human and AI) assumed that file was active when in fact the desktop app never reads it. If you need a CLI-from-memento config, generate one at session time; do not commit it.

**When you edit `~/Documents/agents/.mcp.json`, you must fully quit and relaunch the desktop app.** There is no hot-reload — the app reads the config at startup and caches the result. `/mcp reconnect` does not pick up new server entries added after the session was spawned.

## MCP Servers in This Repo

Five MCP servers live in `tools/`:

| Server | Module | Purpose |
|---|---|---|
| `ndex` | `tools.ndex_mcp.server` | Network CRUD, search, sharing on NDEx |
| `local_store` | `tools.local_store.server` | SQLite catalog + LadybugDB graph DB |
| `biorxiv` | `tools.biorxiv.server` | Paper discovery from bioRxiv |
| `pubmed` | `tools.pubmed.server` | PubMed search + Europe PMC full-text |
| `sl_tools` | `tools.sl_tools.mcp_server` | DepMap + GDSC analysis (40 tools) |

**All servers are identity-less at launch.** None of them take a `--profile` CLI flag. The caller chooses identity per call via tool arguments:

- `ndex` tools: `profile="<name>"` — looks up `<name>` in `~/.ndex/config.json`
- `local_store` tools: `store_agent="<name>"` — selects the agent's cache dir under `~/.ndex/cache/<name>/`

The profile name determines which NDEx server (public, dev, local-127.0.0.1, etc.) is contacted and which credentials are used. There is no server-side enforcement that ties a given MCP entry to one identity — agents must pass the right profile name per call. See `agents/SHARED.md` for the convention.

## Startup Behavior

MCP servers are launched as stdio subprocesses by the desktop app. Two rules for writing a new server module:

1. **Never `print()` to stdout before or during `mcp.run()`.** Stdout is the JSON-RPC channel — any stray output corrupts the handshake and the client drops the server silently (no error surfaced to the user). All startup diagnostics must go to `sys.stderr`:
   ```python
   print("my-server starting...", file=sys.stderr)
   ```
   This applies inside plugin-registration loops too — see the `sl_tools/registry.py` incident (Apr 2026) where a single `print()` without `file=sys.stderr` caused the server to fail to load for weeks.

2. **Don't block on network calls before `mcp.run()`.** The `local_store` server defers its NDEx connection check to first tool use, so the desktop app doesn't time out waiting for the handshake.

## Setting Up on a New Machine

### 1. Install dependencies

This project standardizes on **`.venv`** (Python built-in venv). Do not use conda — the config expects `.venv/bin/python3`.

```bash
cd ~/Documents/agents/GitHub/memento
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Verify all servers import cleanly:

```bash
.venv/bin/python3 -c "from tools.ndex_mcp.server import main; print('ndex OK')"
.venv/bin/python3 -c "from tools.local_store.server import main; print('local_store OK')"
.venv/bin/python3 -c "from tools.biorxiv.server import main; print('biorxiv OK')"
.venv/bin/python3 -c "from tools.pubmed.server import main; print('pubmed OK')"
.venv/bin/python3 -c "from tools.sl_tools.mcp_server import main; print('sl_tools OK')"
```

### 2. Configure NDEx credentials

Create `~/.ndex/config.json` with a profile per agent identity. For each agent, typically both a public and a local variant:

```json
{
  "server": "https://www.ndexbio.org",
  "profiles": {
    "<agent>":        { "username": "<agent>", "password": "..." },
    "local-<agent>":  { "server": "http://127.0.0.1:8080", "username": "<agent>", "password": "..." }
  }
}
```

### 3. Place the MCP config

`~/Documents/agents/.mcp.json` (absolute paths only, since the desktop app does not run from a project directory):

```json
{
  "mcpServers": {
    "ndex": {
      "command": "/Users/<you>/Documents/agents/GitHub/memento/.venv/bin/python3",
      "args": ["-m", "tools.ndex_mcp.server"],
      "cwd":  "/Users/<you>/Documents/agents/GitHub/memento"
    },
    ... (entries for local_store, biorxiv, pubmed, sl_tools)
  }
}
```

Fully quit and relaunch the desktop app. In your next session, verify via the `/mcp` slash command — it lists the servers currently loaded with their connect/fail status.

**The Customize → Connectors → Desktop panel is NOT the right UI for this check.** That panel reflects `claude_desktop_config.json` (chat mode), which is a *separate registry* from project `.mcp.json`. A Code-mode MCP server will not appear there even when it is loaded and working. See the "Two Config Files" section below.

## Two Config Files = Two Desktop Modes

Claude Desktop has two modes, each with its own MCP registry:

| Mode | Config file | How to verify | Used by |
|---|---|---|---|
| **Code** (project-aware) | `~/Documents/agents/.mcp.json` | `/mcp` inside a session | Memento agent sessions, Claude Code Routines |
| **Chat** (general assistant) | `~/Library/Application Support/Claude/claude_desktop_config.json` | Customize → Connectors → Desktop (shows "LOCAL DEV" badge) | Cowork Scheduled Tasks, free-form chat queries |

For this project, Code mode is the only mode that matters for agent work. The Chat config is incidental. Do not assume the Connectors UI tells you anything about Code-mode MCP availability — those are separate systems.

If you find the two files disagreeing (e.g., `sl_tools` in Code config but not Chat config), that's a consistency question — not a bug. Either mirror them or delete the Chat entries and accept that chat mode has no local MCP tools. Project decision: we will not keep them in sync (Routines is the only scheduling path; chat mode is not load-bearing for agent work).

## Adding a New Agent

1. **Create an NDEx account** for the agent (manual step at ndexbio.org, or POST to `/v2/user` on local test server)
2. **Add a profile** to `~/.ndex/config.json` (typically `<name>` for public, `local-<name>` for local 127.0.0.1:8080)
3. **Create the workspace**: `mkdir -p ~/.ndex/cache/<name>/`
4. **Add `agents/<name>/CLAUDE.md`** referencing SHARED.md

**No `.mcp.json` changes.** The five shared servers handle any agent via per-call `profile=` / `store_agent=` arguments.

## Backlog: Scoped local_store Entries

The `local_store` server supports an `--agent-scope <name>` flag that restricts it to a single agent's cache and rejects any other `store_agent` value. This is needed **only if** concurrent processes (e.g., an interactive session and a scheduled task) might both open the same agent's LadybugDB file — exclusive locks otherwise cause failures.

As of this writing, the project runs all agents via Claude Code Routines from a single desktop session, so concurrent cache access is not a concern and the unscoped `local_store` entry is sufficient. If/when Cowork scheduled tasks come online, add per-agent scoped entries (`local_store_<name>` with `--agent-scope <name>`) to `~/Documents/agents/.mcp.json` at that time.

## Scheduling

**Project decision: use Claude Code Routines, not Cowork Scheduled Tasks.** One reason: Routines use `~/Documents/agents/.mcp.json` (the single source of truth), while Cowork Tasks would reintroduce `claude_desktop_config.json` as a second config file. We accept giving up Dispatch remote-monitor visibility — a tradeoff that can be revisited later. Migration from Routines → Cowork is mechanical if/when needed.

Existing Routines can be viewed in the desktop app's sidebar under "Routines". Add new ones via the same panel.

## Troubleshooting

- **A server is missing from the session**: Run `/mcp` in the session — it shows all configured servers with their connect/fail status. If a server is present but failed, check its stderr for the launch error.
- **Server loaded in Code mode but missing from Customize → Connectors → Desktop**: Expected. That panel reflects `claude_desktop_config.json` (Chat mode), not project `.mcp.json`. They are separate registries. See "Two Config Files" above.
- **All servers missing / "No MCP servers configured"**: The desktop app probably spawned the session before `~/Documents/agents/.mcp.json` existed (or was edited). Fully quit and relaunch — `/mcp reconnect` does not pick up new entries.
- **Server fails handshake silently (loads in `/mcp` as "failed"** or doesn't appear at all): check that the server isn't printing to stdout anywhere during startup — see "Startup Behavior" above.
- **`local_store` hangs on startup**: If someone re-added a network call before `mcp.run()`, remove it.
- **Module not found errors**: Ensure `cwd` in the `.mcp.json` entry points to the memento repo root and that `.venv` is installed there.
- **Wrong agent identity on a network**: Not a config problem — the agent passed the wrong `profile=` argument on the tool call. Check agent CLAUDE.md for profile-name conventions.
- **Local NDEx container fails with `/ndexbio-rest/v3/` errors**: The ndex2 Python library hardcodes a path override when it sees "localhost" in the URL. Use `http://127.0.0.1:8080` instead of `http://localhost:8080` in your profile's `server` field.

## Data Format Constraints

These constraints arise from the interaction between CX2, ndex2, and LadybugDB. They are documented here for maintainers; agents see summaries in `agents/SHARED.md` and in tool docstrings.

### CX2 attribute values must be flat

The `ndex2` library's `CX2Network.add_node()` calls `_get_cx2_type(value)` on every attribute value. This rejects `dict` and `list` types with `NDExError: Unsupported value type`. All node/edge attribute values in the `v` dict must be scalar: string, int, float, or boolean.

**Implication for self-knowledge networks**: Agent schemas that previously used nested `"properties"` dicts (e.g., session history nodes with `"properties": {"timestamp": "...", "outcome": "..."}`) must be flattened to top-level keys in the `v` dict.

### LadybugDB MAP column access

LadybugDB stores node/edge properties as `MAP(STRING, STRING)`. These MAP columns:

- **Cannot be accessed with dot syntax** in Cypher: `a.properties.status` throws `Binder exception: has data type MAP but (NODE,REL,STRUCT,ANY) was expected`.
- **`MAP_EXTRACT()` has type-casting issues**: `MAP_EXTRACT(a.properties, 'status') = 'active'` can fail with `Cast failed. active is not in STRING[] range`.
- **Empty MAPs** require a sentinel key `{"__empty__": ""}` due to LadybugDB parameterization limitations. The `graph_store.py` `_clean_map()` function strips this on retrieval.

**Workaround**: Filter by indexed columns (`name`, `node_type`, `network_uuid`) in Cypher, then filter MAP properties in Python. This is what `session_init` does for active plan filtering.

### ndex2 localhost override

The `ndex2` library (v3.11.0) hardcodes `self.host = "http://localhost:8080/ndexbio-rest"` whenever the host URL contains "localhost" (line 56 of `ndex2/client.py`). This breaks with Docker containers that serve at root. Use `127.0.0.1` instead. The `skip_version_check=True` parameter (added to `ndex_client_wrapper.py`) prevents an unnecessary version-probe HTTP call on client init.
