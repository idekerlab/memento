# Procedure: diagnose-scheduled-session-permission-hang

**Owner**: rdaneel (development persona)
**Flavor**: dev-agent (this markdown is the source of truth; `rdaneel-procedures` network carries a pointer via `workflow_path`)
**Current version**: v1.0
**Last refined**: 2026-04-19

## Summary

When a Claude Code Routine (scheduled task) appears to hang or produce no output, and downstream tasks in the same batch are skipped or delayed, the most common cause is a **Bash permission prompt that the scheduler has no way to surface to a user**. This procedure walks through identifying the stuck task, reading the underlying permission pattern, and applying the right fix — which is almost always an agent-guidance change (SHARED.md / per-agent CLAUDE.md) rather than a permission override.

## When to use

- A scheduled-tasks listing shows one task with a recent `lastRunAt` but no corresponding session-history node on NDEx.
- A scheduled batch that usually completes in order shows selective skips (e.g., rsolar ran, rzenith ran, rgiskard ran, rcorona/rsolstice skipped, rvernal ran late).
- The user observed a permission dialog appear while a scheduled session was running, and the session did not exit cleanly.
- rsentinel reports `failed_tool` status on an agent that was supposed to run but didn't finalize a session-history node.

## Preconditions

- You have the `scheduled-tasks` MCP tools loaded (`list_scheduled_tasks`, `update_scheduled_task`).
- You have `ndex` MCP access to read the affected agent's session-history network.
- The user can describe (or share a screenshot of) the permission dialog that surfaced.

## Steps

**1. Identify the hung task.**

```python
mcp__scheduled-tasks__list_scheduled_tasks()
```

Look for anomalies: tasks where `lastRunAt` is very recent (minutes ago) but the agent's NDEx session-history has no new node matching that timestamp. Also look for tasks in the same time window that didn't update `lastRunAt` at all — those are the ones that got silently skipped because an earlier task held the slot.

**2. Recover the underlying Bash pattern.**

Ask the user to share the permission dialog. The screenshot or text will include:
- The exact command the agent tried to run
- A short validator message (e.g. "Newline followed by # inside a quoted argument can hide arguments from path validation")
- Deny / Allow options

**3. Classify the block.**

Compare against known blocked patterns:

| Pattern | Block reason | Correct replacement |
|---|---|---|
| `python3 -c "... # comment ..."` with multi-line + comments | `#` inside quoted multi-line arg can hide subsequent args from path validation; validator blocks unconditionally | Use Read tool for files; use MCP tools for their intended I/O; if scripting is truly needed use heredoc: `python3 << 'PY'` ... `PY` |
| `python3 -c` reading `~/.claude/projects/.../tool-results/*.json` | Agent is bash-mining its own session's tool-result cache — an anti-pattern even when it works | Re-call the MCP tool (idempotent) OR persist the content as a CX2 analysis network + query via `local_store` |
| `cd <path> && git <command>` compound | Compound commands mixing `cd` and `git` can be exploited via a bare repository planted at `<path>` (git hooks execute on operations); validator requires approval unconditionally | Use `git -C <path> <command>` — git's built-in flag runs as if git were started in `<path>` without the compound-with-cd pattern. For multiple git ops, issue them as separate Bash calls (the tool persists cwd across calls) or chain `git -C <path> a && git -C <path> b`. |
| `curl http://127.0.0.1:8080/v2/...` | Scheduled sessions must not HTTP-call NDEx (SHARED.md Unattended Session Protocol) | Use the `ndex` MCP tools |
| `rm -rf` / `git push --force` / any destructive command | High-risk, validator blocks | Reconsider the task; in scheduled mode, destructive ops should be explicitly out of scope |
| New pattern not in the table above | Unknown | Document it — append a row to this table with the reason and replacement. **These security fixes are evolving** — expect to discover new patterns; the table grows. |

**4. Apply the fix at the right layer.**

The fix is almost always at the **agent-guidance level**, not the **permission level**:

- **If all agents are likely to hit the same pattern**: update `agents/SHARED.md` § Unattended Session Protocol → Bash discipline. Add the specific pattern to the prohibited list with a one-sentence replacement.
- **If the pattern is specific to one agent's work style**: update that agent's CLAUDE.md with explicit guidance. Example: rzenith's paper-processor invocation → result-handling section might need tightening.
- **If the pattern is a symptom of a missing MCP tool**: queue a tool-development action in `rdaneel-plans` rather than patching around.
- **Do not** add broad permission overrides in `~/.claude/settings.json` to allow the blocked pattern — the validator is blocking for a reason (subtle argument hiding in shells), and the right fix is to stop generating the pattern.

**5. Get the session unstuck.**

The user clicks **Deny** on the permission dialog (or the agent's own retry-limit eventually ends the session). The task's next scheduled run will use the updated agent guidance. No code change required to the scheduled task itself (the prompt references CLAUDE.md / SHARED.md by path, so guidance updates are picked up automatically next run).

If the hang is actively blocking downstream tasks (other agents scheduled later in the same morning / afternoon window got silently skipped), the user may choose to manually "Run now" on skipped tasks after the dialog is resolved.

**6. Log the learning.**

- Add a session node to `rdaneel-session-history` describing the hang, the pattern, and the SHARED.md / CLAUDE.md change made.
- If a new blocked pattern was documented, bump this procedure's `procedure_version` in `rdaneel-procedures` and update the pattern table in step 3.
- If the root cause exposed an architectural gap (e.g., scheduled tasks skipping silently instead of queueing), capture it as a `planned` action in `rdaneel-plans` for investigation.

## Pitfalls

- **Don't whitelist the blocked pattern** in `~/.claude/settings.json`. The validator is protecting against real shell-argument-hiding hazards. The blocked pattern is a symptom, not the problem.
- **Don't add a retry-in-loop** to the agent's prompt. Permission hangs aren't tool failures — they're indefinite waits. SHARED.md's 3-retry limit doesn't apply because the tool call never fails; it just never returns.
- **Don't "fix" by deleting the tool-result cache**. That cache belongs to the session and may contain results the agent legitimately wants to re-examine (via MCP re-call or via persisted CX2 network — not via Bash).
- **Don't conclude the scheduler is broken** just because some tasks got skipped while one hung. The skip pattern may be a separate scheduler-behavior quirk worth investigating — but the permission hang is always a valid problem to fix independently.
- **Be careful interpreting `lastRunAt`**: the field is updated whenever the task runs (scheduled or manual). A recent `lastRunAt` without a matching NDEx session-history node means the session started but didn't finalize — likely hung or failed.
- **Interactive sessions won't reproduce the hang**: the user can click Allow in an interactive session, so the Bash pattern "works" in dev but fails in production. Test agent behavior in scheduled mode whenever introducing a new workflow.

## When to refine

- **A new blocked Bash pattern surfaces** — add a row to the pattern table in step 3.
- **The Bash permission validator's rules change** — update the known-blocked-patterns list.
- **The scheduled-tasks skip-vs-queue behavior gets documented or changes** — update step 1 diagnostic guidance.
- **A legitimate case emerges where a broad settings.json permission change is the right fix** (unlikely but possible) — add the reasoning here so future dev sessions know.
- **An MCP tool change eliminates a pattern** (e.g., a new `read_tool_result` helper eliminates Bash-mining) — update the replacement column.
