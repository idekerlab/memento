# MCP Server Configuration Guide

## MCP Servers in This Repo

Four MCP servers live in `tools/`:

| Server | Module | Profile needed | Purpose |
|---|---|---|---|
| `ndex` | `tools.ndex_mcp.server` | Yes | Network CRUD, search, sharing on NDEx |
| `local_store` | `tools.local_store.server` | Yes | SQLite catalog + LadybugDB graph for persistent memory |
| `biorxiv` | `tools.biorxiv.server` | No | Paper discovery from bioRxiv |
| `pubmed` | `tools.pubmed.server` | No | PubMed search + Europe PMC full-text |

The `--profile <agent>` flag controls which NDEx agent identity is used. New agents need a corresponding profile in `~/.ndex/config.json` and an NDEx account.

## Startup Behavior

All servers are designed to start fast and not block on network calls. The `local_store` server defers its NDEx connection check to first tool use — this is intentional so Claude Desktop/Cowork doesn't timeout waiting for the server to start. Do not add blocking network calls before `mcp.run()`.

## Three Places MCP Servers Can Be Configured

1. **Project `.mcp.json`** (repo root) — Used by **Claude Code** (CLI, VS Code extension, Desktop Code mode). Paths can be relative to the project. This is what agents use during interactive Claude Code sessions.

2. **`claude_desktop_config.json`** — Used by **Claude Desktop / Cowork**. Paths must be **absolute** because Desktop doesn't run from a project directory. Servers appear as "LOCAL DEV" in the Connectors panel. Location varies by OS:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

3. **Claude Code user-scope settings** (`~/.claude/settings.json`) — Global MCP servers available across all Claude Code projects.

**Common mistake**: On macOS, there is also a `config.json` in the same directory. That file is for general Desktop app settings (theme, locale, etc.) — MCP entries there are ignored by the UI.

## Setting Up on a New Machine

### 1. Install dependencies

This project standardizes on **`.venv`** (Python built-in venv). Do not use conda — the `.mcp.json` and Desktop config expect `.venv/bin/python3`.

```bash
cd /path/to/memento
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

The key dependency is `real_ladybug` (embedded graph DB for local_store). Verify all servers import cleanly:

```bash
.venv/bin/python3 -c "from tools.ndex_mcp.server import main; print('ndex OK')"
.venv/bin/python3 -c "from tools.local_store.server import main; print('local_store OK')"
.venv/bin/python3 -c "from tools.biorxiv.server import main; print('biorxiv OK')"
.venv/bin/python3 -c "from tools.pubmed.server import main; print('pubmed OK')"
```

### 2. Configure NDEx credentials

Create `~/.ndex/config.json` with profiles for each agent:

```json
{
  "profiles": {
    "rdaneel": { "server": "https://www.ndexbio.org/v3", "username": "rdaneel", "password": "..." },
    "drh": { "server": "https://www.ndexbio.org/v3", "username": "drh", "password": "..." }
  }
}
```

### 3. Configure Claude Code (`.mcp.json`)

The project `.mcp.json` uses `.venv/bin/python3` with relative paths and works out of the box after creating the venv. No changes needed.

### 4. Configure Claude Desktop / Cowork

Add entries to `claude_desktop_config.json` with **absolute paths** to both the Python interpreter and the project root:

```json
"server_name": {
  "command": "/absolute/path/to/memento/.venv/bin/python3",
  "args": ["-m", "tools.<module>.server", "--profile", "<agent>"],
  "cwd": "/absolute/path/to/memento"
}
```

Restart Claude Desktop after changes. Servers should appear as "LOCAL DEV" connectors.

## Adding a New Agent

When adding a new agent to the system:

1. **Create an NDEx account** for the agent (manual step)
2. **Add a profile** to `~/.ndex/config.json` on each machine that will run the agent
3. **Add a `CLAUDE.md`** in `agents/<agent_name>/CLAUDE.md` with role-specific instructions
4. **No MCP server changes needed** — the existing servers support any agent via the `--profile` parameter. Each Cowork task or Claude Code session just passes the appropriate profile.

For Desktop/Cowork, you can either:
- Reuse the same server entries and switch profiles per task
- Add dedicated server entries per agent (e.g., `ndex_drh`, `local_store_drh`) if you want parallel agents

## Scheduling: Cowork vs Claude Code

These are **two different scheduling systems**:

### Cowork Scheduled Tasks (Claude Desktop)
- Configured in the **Cowork tab** of the Claude Desktop app
- Runs locally on your machine (must be on and Desktop must be running)
- Uses MCP servers from `claude_desktop_config.json`
- Good for: interactive research tasks, tasks needing Desktop connectors (Google Drive, GitHub, etc.)

### Claude Code `/schedule` (Remote Triggers)
- Configured via `/schedule` command in Claude Code CLI or VS Code extension
- **Cloud tasks** run on Anthropic infrastructure (machine can be off) but cannot use local MCP servers
- **Desktop/local tasks** run on your machine and can use project `.mcp.json` servers
- Good for: automated CI-like workflows, tasks that should run even when you're away

## Troubleshooting

- **Servers not appearing in Desktop**: You're probably editing `config.json` instead of `claude_desktop_config.json`. Edit the right file and restart Desktop.
- **Server fails to connect in Desktop**: Check that the `command` path points to a Python with all dependencies installed. Run the import check above.
- **`local_store` hangs on startup**: If someone re-added a network call before `mcp.run()`, remove it — startup must not block on HTTP.
- **Module not found errors**: Ensure `cwd` is set to the memento project root.
- **Wrong agent identity**: Check the `--profile` argument matches a profile in `~/.ndex/config.json`.
