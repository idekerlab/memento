# Local Store Lock Isolation Design

**Status**: Proposed  
**Date**: 2026-04-16  
**Context**: LadybugDB lock contention observed 2026-04-15; affects scheduled agent sessions

---

## Problem Statement

LadybugDB (via `real_ladybug`) takes an **exclusive file lock** on each `graph.db` when `lbug.Database(path)` is called. The lock is held for the entire lifetime of the `Database` object — which in the current architecture means the entire lifetime of the MCP server process.

The current `.mcp.json` has a single `local_store` entry:

```json
"local_store": {
  "command": ".venv/bin/python3",
  "args": ["-m", "tools.local_store.server", "--profile", "local-rgiskard"],
  "cwd": "."
}
```

This one process serves all tool calls. In `server.py`, `_get_store(store_agent)` lazily opens a `LocalStore` — and therefore a `GraphStore` (LadybugDB connection) — for each distinct `store_agent` value it receives. Once opened, those connections live in `_stores: dict[str, LocalStore]` for the server's lifetime.

**Result**: An interactive Claude Code session that issues tool calls with `store_agent="rzenith"` and `store_agent="rgiskard"` causes the MCP process to hold exclusive locks on **both** `~/.ndex/cache/rzenith/graph.db` and `~/.ndex/cache/rgiskard/graph.db`.

When scheduled tasks then launch their own MCP server processes (one per scheduled session), those processes call `lbug.Database()` on the same paths and fail immediately with a lock error.

### Observed Failure (2026-04-15)

- Interactive session (PID 90037) opened stores for both rzenith and rgiskard.
- Scheduled rzenith task (16:09): `session_init` failed — lock on `rzenith/graph.db`.
- Scheduled rgiskard task (16:24): `session_init` failed — lock on `rgiskard/graph.db`.
- Both agents improvised with `download_network` → `/tmp` → bash file reads, violating the Unattended Session Protocol.

### Scope at 10 Agents

With 10 agents, the risk surface increases sharply. Any interactive session that touches multiple agents' stores will block all of them. Lock contention is no longer an occasional edge case — it becomes a near-certainty during any active development session that explores multiple agents' data.

---

## Current Code Surfaces

| File | Role | Lock relevance |
|------|------|----------------|
| `tools/local_store/server.py` | MCP entry point | `_stores` dict holds open `LocalStore` instances; no per-agent entry-point filtering |
| `tools/local_store/graph_store.py` | LadybugDB wrapper | `__init__` opens `lbug.Database` + `lbug.Connection`, holds them open; `close()` exists but is never called from the server |
| `tools/local_store/store.py` | Two-tier coordinator | Instantiates both `Catalog` (SQLite) and `GraphStore` (LadybugDB) in `__init__` |
| `.mcp.json` | MCP process config | Single `local_store` entry; no agent scoping |

Key lines in `graph_store.py`:

```python
# GraphStore.__init__ — lock acquired here, never released while server runs
self.db = lbug.Database(self.db_path)      # acquires exclusive lock
self.conn = lbug.Connection(self.db)

# GraphStore.close — exists but not wired into server teardown
def close(self):
    del self.conn
    del self.db                             # lock released here
```

---

## Three Design Options

### Option A: Per-Agent MCP Server Entries (Recommended)

**Concept**: Add an `--agent-scope <agent>` CLI flag to `server.py`. When set, the server rejects any tool call whose `store_agent` does not match the scope, returning an error before opening any database. Each scheduled task's MCP config has its own scoped server entry. The lock for agent X is only ever held by agent X's server process.

#### Implementation

**1. `tools/local_store/server.py`** — add argparse and scope enforcement

```python
import argparse

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    parser.add_argument("--agent-scope", default=None,
        help="Restrict this server to one agent's cache. "
             "Tool calls with a different store_agent are rejected.")
    return parser.parse_args()

_args = _parse_args()
_AGENT_SCOPE: str | None = _args.agent_scope

_SCOPE_VIOLATION_MSG = (
    "This local_store server is scoped to agent '{scope}'. "
    "Received store_agent='{got}'. "
    "Use the local_store_{got} MCP server for that agent."
)

def _check_scope(store_agent: str) -> dict | None:
    """Return error dict if store_agent violates the server's scope, else None."""
    if _AGENT_SCOPE and store_agent != _AGENT_SCOPE:
        return {"status": "error", "message": _SCOPE_VIOLATION_MSG.format(
            scope=_AGENT_SCOPE, got=store_agent)}
    return None
```

Every tool that accepts `store_agent` inserts a `_check_scope` call before `_require_store`:

```python
@mcp.tool()
def session_init(agent: str, profile: str, ...):
    err = _check_scope(agent)
    if err:
        return err
    ...
```

No changes to `graph_store.py` or `store.py`.

**2. `.mcp.json`** — add scoped entries alongside the unscoped one

```json
{
  "mcpServers": {
    "ndex": { ... },
    "local_store": {
      "command": ".venv/bin/python3",
      "args": ["-m", "tools.local_store.server"],
      "cwd": "."
    },
    "local_store_rzenith": {
      "command": ".venv/bin/python3",
      "args": ["-m", "tools.local_store.server", "--agent-scope", "rzenith"],
      "cwd": "."
    },
    "local_store_rgiskard": {
      "command": ".venv/bin/python3",
      "args": ["-m", "tools.local_store.server", "--agent-scope", "rgiskard"],
      "cwd": "."
    }
  }
}
```

The unscoped `local_store` entry remains for interactive sessions that legitimately need to read across multiple agents (e.g., the agent-hub-dev webapp, analysis scripts). Interactive use of the unscoped server can still cause contention if a scheduled task is running simultaneously — but this is an operator-awareness problem, not a scheduler problem. The scheduled tasks, which are the critical reliability concern, are protected.

**3. Scheduled task MCP configs** — each scheduled task's `.mcp.json` or Cowork config should use only its scoped entry. If Cowork scheduled tasks use `claude_desktop_config.json`, add:

```json
"local_store_rzenith": {
  "command": "/absolute/path/to/memento/.venv/bin/python3",
  "args": ["-m", "tools.local_store.server", "--agent-scope", "rzenith"],
  "cwd": "/absolute/path/to/memento"
}
```

**4. Agent CLAUDE.md / SHARED.md** — update the MCP server table to document scoped entries. No change to the `store_agent` protocol in tool calls; agents continue passing `store_agent="rzenith"` etc. as before.

#### Tradeoffs

| | |
|---|---|
| **Fixes** | Scheduled tasks never compete for locks with each other or with interactive sessions using their scoped server. Lock contention is eliminated for all scheduled-task scenarios. |
| **Does not fix** | Interactive sessions using the unscoped `local_store` entry can still hold multiple agents' locks. This is acceptable because interactive sessions are human-supervised; the Unattended Session Protocol applies only to scheduled tasks. |
| **Performance** | No change. LadybugDB open-time cost is unchanged; the database remains open for the server's lifetime exactly as today. |
| **Transaction safety** | `session_init`'s clear-then-reimport sequence is unaffected — it runs within a single, long-lived connection. |
| **Code complexity** | ~20 lines of argparse + scope-check calls. Minimal surface area; easy to audit. |
| **Migration** | Additive. Existing unscoped entry continues working. Scheduled tasks switch to scoped entries one agent at a time. No data migration. |
| **Scaling to 10 agents** | Add one `.mcp.json` entry per agent. Entry names are predictable (`local_store_<agent>`). A helper script or Makefile target can regenerate the config from `agents/*/CLAUDE.md`. |

---

### Option B: Open/Query/Close Pattern

**Concept**: Remove the persistent `lbug.Database` + `lbug.Connection` from `GraphStore.__init__`. Instead, open the database, execute the query, and close the connection (releasing the lock) before returning from every method call.

#### Implementation

**`tools/local_store/graph_store.py`** — convert from persistent to ephemeral connections:

```python
class GraphStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or DEFAULT_CACHE_DIR / "graph.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # No longer opens lbug.Database here.
        # Schema init deferred to first _run() call.
        self._schema_initialized = False

    def _run(self, fn):
        """Open database, call fn(conn), close, return result."""
        db = lbug.Database(self.db_path)
        try:
            conn = lbug.Connection(db)
            if not self._schema_initialized:
                for stmt in SCHEMA_STATEMENTS:
                    conn.execute(stmt)
                self._schema_initialized = True
            return fn(conn)
        finally:
            del conn
            del db   # releases lock

    def execute(self, query, parameters=None):
        def _exec(conn):
            result = conn.execute(query, parameters) if parameters else conn.execute(query)
            rows = []
            while result.has_next():
                rows.append(result.get_next())
            return rows
        return self._run(_exec)

    def add_node(self, ...):
        def _add(conn):
            # ... same logic as today but using conn not self.conn
        return self._run(_add)

    # ... all other methods refactored similarly
    def close(self):
        pass  # nothing to close
```

`store.py` and `server.py` require no structural changes (the `LocalStore` and server layers are unaffected by how `GraphStore` manages its connection internally).

#### Tradeoffs

| | |
|---|---|
| **Fixes** | Lock contention fully eliminated for all access patterns, including multiple simultaneous interactive sessions on the same agent. True concurrent read access becomes possible. |
| **Performance cost** | `lbug.Database()` opens a file and applies any pending WAL changes at open time. For small databases (< ~50 networks), this is probably 10–50ms per call. For a `session_init` that imports 4 networks (each requiring multiple `add_node`/`add_edge`/`link_node_to_network` calls), the total overhead could be several seconds. This requires benchmarking before committing. |
| **Transaction semantics** | `session_init` does `clear_all()` followed by multiple `import_network()` calls. In the current design these share a connection; if the process is killed mid-import, the LadybugDB WAL may leave a partial state. With open/close, each call is a separate open/close cycle. There is no cross-call atomicity. If `session_init` crashes between `clear_all` and the first successful import, the cache is empty with no way to detect the partial state. |
| **`_schema_initialized` flag** | The flag is in-process state. If two processes run concurrently, both may observe `_schema_initialized = False` and both will issue `CREATE TABLE IF NOT EXISTS` — which is safe (idempotent), but illustrates that per-instance flags do not provide real coordination. |
| **Code churn** | Every `GraphStore` method must be refactored to the `_run(fn)` pattern. ~15 methods. Each one requires lifting local variable captures into a closure, which is mechanical but error-prone to review. |
| **Migration** | Drop-in replacement if performance is acceptable. Schema is unchanged. No data migration. |
| **Scaling to 10 agents** | Scales well — no `.mcp.json` changes, no per-agent configuration. |

Option B is the correct long-term architecture if LadybugDB ever supports concurrent readers (e.g., WAL mode with shared-cache). It eliminates the lock problem at the source. But the performance cost and transaction-atomicity regression for `session_init` make it risky to deploy without benchmarking.

---

### Option C: WAL Mode + Shared-Cache for Concurrent Readers

**Concept**: Configure LadybugDB (which wraps KuzuDB) to use WAL (Write-Ahead Logging) mode, if supported. In WAL mode, multiple readers can access the database simultaneously; only concurrent writers block each other. Since most agent tool calls are reads (queries, catalog lookups), this would allow the interactive session to hold a read connection while a scheduled task acquires a write connection for `session_init`.

#### Investigation Required

This option cannot be fully specified without checking KuzuDB's concurrency model:

1. **Does `real_ladybug` / KuzuDB support WAL mode?** KuzuDB (the underlying embedded graph engine) uses a different storage architecture than SQLite. As of KuzuDB 0.7.x, it supports a single-writer/multiple-reader model via its own connection concurrency control, not SQLite-style WAL. The specific version packaged in `real_ladybug` must be checked.

2. **Is shared-cache or read-only open available?** KuzuDB connections can potentially be opened read-only (`lbug.Connection(db, read_only=True)`). If so, the interactive session could use read-only connections for queries and the scheduled task could get an exclusive write connection for `session_init`.

3. **What is the granularity of the lock?** If KuzuDB's lock is at the database level (not connection level), even read-only connections may block writers, defeating the purpose.

#### Provisional Implementation Sketch

If KuzuDB supports read-only connections:

```python
# graph_store.py
class GraphStore:
    def __init__(self, db_path, read_only=False):
        self.db = lbug.Database(self.db_path)
        self.conn = lbug.Connection(self.db, read_only=read_only)
```

The `_get_store` function in `server.py` would use `read_only=True` for query tools and `read_only=False` only for write tools (`cache_network`, `session_init`, `clear_cache`, `delete_cached_network`).

#### Tradeoffs

| | |
|---|---|
| **Fixes** | If KuzuDB supports concurrent readers: interactive read-only queries don't block scheduled writes. |
| **Does not fix** | Two writers still contend. Two scheduled tasks running simultaneously would still block each other (though this is less common). The unscoped interactive session holding a write connection (from any write tool call) would still block. |
| **Dependency on library internals** | The solution depends on undocumented or version-specific KuzuDB behavior. `real_ladybug` is a thin wrapper and may expose the necessary primitives, or may not. |
| **Partial mitigation** | Even if read-only connections are available, the interactive sessions most likely to cause contention include `session_init` calls (e.g., "let me quickly re-run this agent's init to check its state"), which are write operations. |
| **Investigation cost** | Non-trivial upfront research cost before writing any code. No guarantee of a usable result. |
| **Migration** | If viable: add `read_only` parameter to `GraphStore` and `LocalStore`; update `server.py` to distinguish read vs write tools. Moderate churn. |

Option C is not recommended as a primary fix given the uncertainty about KuzuDB's concurrency primitives in the version used by `real_ladybug`. It may become viable as a performance optimization later (e.g., allowing multiple readers on a read-heavy agent), but it does not reliably solve the write-lock contention that is the primary failure mode.

---

## Recommendation: Option A

**Implement Option A (per-agent MCP server entries).** It directly solves the observed failure mode — scheduled tasks losing their lock to interactive sessions — with the least code risk and no behavioral regression.

### Why not B now

Option B is architecturally cleaner but introduces:
1. Unknown performance cost of per-call open/close (needs benchmarking before any production use)
2. Loss of cross-call connection state — affects `session_init` atomicity
3. High code churn across all `GraphStore` methods

These risks are not justified when Option A solves the real problem with ~20 lines of code.

### Why not C

Option C has prerequisite research that may yield nothing actionable. It is not a reliable fix for the write-lock scenario that caused the 2026-04-15 failures.

### What Option A does not solve

Option A does **not** prevent an interactive user from running the unscoped `local_store` server and holding locks on multiple agents while scheduled tasks run. This is an operator-awareness issue. The mitigation is:

1. Document in `tools/CLAUDE.md` that the unscoped entry should be used for read-only cross-agent analysis, not for operations that touch many agents in the same session.
2. Consider adding a startup warning to the unscoped server: "No agent scope set — this server will open and hold locks on every store_agent it receives. Use local_store_<agent> entries for scheduled tasks."
3. Long-term, if interactive sessions routinely need cross-agent access, implement Option B for the query methods only (open/query/close for reads; persistent connection for writes), which captures most of the concurrency benefit at lower risk.

---

## Implementation Plan

### Phase 1 — Core change (1–2 hours)

1. Add `--agent-scope` argparse to `tools/local_store/server.py`.
2. Add `_check_scope()` helper and call it at the top of every tool handler that accepts `store_agent` or `agent`.
3. Add scoped entries to `.mcp.json` for currently active agents (rzenith, rgiskard).
4. Test: start scoped server with `--agent-scope rzenith`, verify `store_agent="rgiskard"` returns error, `store_agent="rzenith"` succeeds.

### Phase 2 — Scheduled task configs (30 min)

5. Update Cowork/Claude Desktop `claude_desktop_config.json` with absolute-path scoped entries for rzenith and rgiskard.
6. Verify each scheduled task's MCP config references only its scoped entry, not the unscoped one.
7. Run both scheduled tasks back-to-back and confirm no lock errors.

### Phase 3 — Documentation (30 min)

8. Update `tools/CLAUDE.md` MCP server table to document scoped vs unscoped entries.
9. Update `memento/CLAUDE.md` server table to mention per-agent entries.
10. Add a new agent onboarding step: "Add `local_store_<name>` entry to `.mcp.json` and `claude_desktop_config.json`."
11. Optionally update `ndexbio/project/deferred_tasks.md` to mark the lock contention issue resolved.

### Phase 4 — Scaling (as agents are added)

For each new agent added to the system:
- Add one `.mcp.json` entry: `local_store_<name>` with `--agent-scope <name>`.
- Add one `claude_desktop_config.json` entry with absolute paths.
- The unscoped `local_store` entry requires no changes.

No code changes are needed for new agents — only config changes.

---

## File Change Summary

| File | Change type | Description |
|------|-------------|-------------|
| `tools/local_store/server.py` | Modify | Add `--agent-scope` argparse flag; add `_check_scope()` helper; call it in all tool handlers |
| `.mcp.json` | Modify | Add `local_store_rzenith`, `local_store_rgiskard` entries |
| `~/Library/.../claude_desktop_config.json` | Modify | Add absolute-path scoped entries for scheduled tasks (machine-local, not in repo) |
| `tools/CLAUDE.md` | Modify | Document scoped server entries in the MCP config table |
| `memento/CLAUDE.md` | Modify | Update MCP server table; add new-agent onboarding note |

No changes to `graph_store.py`, `store.py`, `catalog.py`, or any test files.

---

## Future Work

- **Option B partial implementation**: Once LadybugDB open-time cost is benchmarked, consider open/query/close for read-only methods (`query_graph`, `get_network_nodes`, `get_network_edges`, `find_neighbors`, `find_path`, `find_contradictions`, `query_catalog`, `get_cached_network`, `check_staleness`). Write methods (`session_init`, `cache_network`, `clear_cache`, `delete_cached_network`, `publish_network`, `save_new_network`) keep persistent connections for atomicity. This hybrid approach captures most of the concurrency benefit of Option B at lower risk.

- **WAL recovery handling**: Separately from lock isolation, the WAL recovery issue documented in `deferred_tasks.md` ("when a second process holding the lock is killed, leaves `graph.db.wal`") should be addressed. The surviving MCP server needs to detect the stale WAL condition and reopen the database. This is independent of which option is chosen here.

- **Partial cache reload**: `session_init` currently clears and re-downloads all self-knowledge networks unconditionally. A staleness check before clearing (compare NDEx modificationTime to `ndex_modified` in catalog) would reduce write operations and therefore reduce the window in which locks are held during `session_init`. This compounds well with any of the three options above.
