# Procedure: create-claude-code-routine

**Owner**: rdaneel (development persona)
**Flavor**: dev-agent (this markdown is the source of truth; `rdaneel-procedures` network carries a pointer via `workflow_path`)
**Current version**: v1.0
**Last refined**: 2026-04-18

## Summary

Create a Claude Code Routine (a scheduled Claude session that runs on a cron schedule) via the `scheduled-tasks` MCP. Tasks are stored as `{taskId}/SKILL.md` under `~/.claude/scheduled-tasks/` and dispatched by the desktop app. Use this to schedule recurring agent sessions (e.g., `rsolar-session-morning` firing at 05:25 local daily) or one-off tasks.

## When to use

- Onboarding a new scheduled agent — e.g. after `bootstrap-agent-self-knowledge`, schedule morning/afternoon runs.
- Changing the cadence of an existing scheduled agent (update, not recreate).
- Creating a one-shot task (date-specific migration, benchmark run).
- Creating a dev-ops review routine (e.g. `rdaneel-review-*`).

## Preconditions

- You are running in a Claude Code session where the `mcp__scheduled-tasks__*` tools are loaded.
- The agent's CLAUDE.md is already committed on main at `/Users/dexterpratt/Documents/agents/GitHub/memento/agents/<agent>/CLAUDE.md`.
- The agent is bootstrapped (`onboard-new-agent-ndex-account` + `bootstrap-agent-self-knowledge` completed) — a scheduled run of an un-bootstrapped agent will fail at `session_init`.
- You know the desired cron expression in the user's local time (not UTC — the tool evaluates cron in local time).

## Key facts about Claude Code Routines

- **Storage**: `~/.claude/scheduled-tasks/{taskId}/SKILL.md` (YAML frontmatter + prompt body).
- **Scheduler**: `mcp__scheduled-tasks__{create,update,list,delete}_scheduled_task`. This MCP **is** Claude Code Routines — the name "scheduled-tasks" in the MCP is the same thing the project doc `tools/CLAUDE.md` refers to as Routines.
- **Cron evaluation is in local time**, not UTC. Write `0 5 * * *` for 5 AM local.
- **Jitter**: the scheduler applies a small deterministic delay of several minutes (up to ~6 min observed; `jitterSeconds` field shows the actual delay for each task) to balance load. Space adjacent tasks ≥ 10 min apart to avoid overlap.
- **One cron per task.** If you need two runs per day (morning + afternoon), create two tasks (`<agent>-session-morning`, `<agent>-session-afternoon`). Alternatively, use multi-value cron (`0 5,12 * * *` for 5am + 12pm) if the same prompt suffices.
- **Tool approvals**: permissions approved during a run persist for future runs of the same task. On first run, the user may need to click "Run now" and approve prompts interactively.
- **notifyOnCompletion**: defaults to `true` — the session that created the task gets pinged on each run. For routine scheduled agents, pass `false` to avoid notification spam.

## Steps

**1. Choose the taskId.**

Kebab-case, descriptive. Conventions for this project:
- `<agent>-session-morning` / `<agent>-session-afternoon` for scientist-agent twice-daily runs.
- `<agent>-health-check` for monitor-style (rsentinel).
- `<agent>-review-{morning,afternoon}` for rdaneel scheduled-review mode.
- `<agent>-<one-off-descriptor>` for single-fire tasks.

**2. Compute the cron expression in local time.**

Format: `minute hour dayOfMonth month dayOfWeek`. Common patterns:
- `0 5 * * *` — daily at 5:00 AM local
- `0 5,18 * * *` — daily at 5:00 AM and 6:00 PM local
- `15 5 * * *` — daily at 5:15 AM local
- `0 5,7,18,21 * * *` — 5am, 7am, 6pm, 9pm daily (rsentinel pattern)
- `0 9 * * 1-5` — weekdays at 9:00 AM local

**3. Draft the prompt.**

Use the minimal template (scientist-agent scheduled session):

```
Run a session as the <agent> agent.

Instructions:
- Agent CLAUDE.md: /Users/dexterpratt/Documents/agents/GitHub/memento/agents/<agent>/CLAUDE.md
- Shared protocols: /Users/dexterpratt/Documents/agents/GitHub/memento/agents/SHARED.md

Read both files, then session_init(agent="<agent>", profile="local-<agent>") and follow the standard session lifecycle defined in SHARED.md.

Deployment context:
- NDEx profile: local-<agent>
- Store agent: <agent>
- Working directory: /Users/dexterpratt/Documents/agents

Use local-<agent> wherever the agent instructions say profile="<agent>". Session time budget: target ≤15 minutes.
```

Variations:
- **Service-provider agents (rcorona, rsolstice)**: add "Demand-driven: if no requests on the feed, update self-knowledge and end." Note dual profiles for rsolstice.
- **Monitor agents (rsentinel)**: skip `session_init` — use NDEx MCP tools only (see rsentinel-health-check SKILL.md).
- **Review-mode agents (rdaneel-review-*)**: explicitly reference the scheduled-review mode section of the agent's CLAUDE.md and enumerate constraints (read-only, no repo, no decisions, no AskUserQuestion).
- **One-off tasks**: describe the specific change / migration / benchmark, and reference the originating session or design doc.

**4. Create the task.**

```python
mcp__scheduled-tasks__create_scheduled_task(
  taskId="<agent>-session-morning",
  cronExpression="15 5 * * *",
  description="<one-line description>",
  prompt="<full prompt from step 3>",
  notifyOnCompletion=False,  # routine tasks: don't ping your dev session on each run
)
```

For a one-off: pass `fireAt="2026-04-20T14:30:00-07:00"` instead of `cronExpression`. Mutually exclusive.

Omit both `cronExpression` and `fireAt` to create an **ad-hoc** task that only runs when manually triggered.

**5. Verify.**

`mcp__scheduled-tasks__list_scheduled_tasks()` should show the new task with `enabled: true`, `nextRunAt`, and non-zero `jitterSeconds`. Also confirm the SKILL.md file was created under `~/.claude/scheduled-tasks/<taskId>/SKILL.md`.

**6. Record in rdaneel self-knowledge.**

- Note the task creation in `rdaneel-session-history`.
- Append this procedure's node to `rdaneel-procedures` `used_in_sessions`.
- If anything was learned that should refine this procedure (new constraint, new pattern, new pitfall), update this markdown + bump `procedure_version`.

## Updating an existing task

Use `mcp__scheduled-tasks__update_scheduled_task(taskId=..., cronExpression=..., prompt=..., description=..., enabled=...)` — partial update, only fields you pass change.

Pass `enabled=False` to pause a task without deleting it (preserves history).

To change from cron-recurring to one-off, pass `fireAt=...` (clears cron). To change from one-off to cron-recurring, pass `cronExpression=...` (clears fireAt).

## Pitfalls

- **Cron is LOCAL time, not UTC.** Writing `0 13 * * *` meaning 1 PM UTC will actually fire at 1 PM local. Confirm the user's timezone if unclear.
- **Jitter adds minutes.** A task scheduled at `0 5 * * *` with jitterSeconds=358 fires at 5:05:58. For sequences (morning batch with tight dependencies like rsolar → rvernal → rboreal), space runs ≥ 10 minutes apart so jitter doesn't cause overlap.
- **`notifyOnCompletion=true` (default) pings every run.** For routine agent runs this is spammy. Always pass `false` unless this is a critical one-off you want direct feedback on.
- **Prompt must reference absolute paths.** Scheduled sessions don't inherit a cwd from an interactive context — use absolute paths (`/Users/dexterpratt/Documents/agents/...`). Confirm `/Users/<username>/` matches the user the task runs as.
- **A task running in scheduled mode for a normally-interactive agent (e.g. rdaneel)** needs explicit scheduled-mode instructions in the prompt, because the agent's CLAUDE.md may say "interactive only." Enumerate the scheduled-mode constraints in the prompt so the agent doesn't default to its interactive scope.
- **Permission prompts pause the task.** First run of a new task may need `Run now` + manual approval of tools. Once approved, tools stick. If a task is expected to use non-standard MCPs (web, browser), consider running it manually first.
- **Scheduled tasks run in sandboxed tmp dirs.** Use explicit `output_dir` with `~/.ndex/cache/<agent>/scratch/` for any file operations. See rsentinel-health-check SKILL.md for the pattern.
- **Session_init is local_store-backed** — agents that deliberately skip `session_init` (rsentinel) need explicit NDEx-MCP-only instructions. Other agents should always call `session_init`.
- **Jitter is NOT user-configurable.** Don't try to eliminate it. Just space tasks accordingly.
- **Tasks persist across desktop restarts** — they're filesystem-backed. But a task that references an MCP server that failed to start will silently no-op until the MCP is back.

## When to refine

- **New archetype of scheduled agent** (e.g., a digest-mode like rdaneel-review) with new prompt-template constraints — add a variation under Step 3.
- **New `scheduled-tasks` MCP feature** (new field, new option) — document here.
- **New convention for taskId naming** — update Step 1.
- **Observed jitter range changes** — update the key-facts section.
- **The scheduled-tasks MCP changes which directory tasks are stored in** — update the key-facts section (and any cross-references in `tools/CLAUDE.md`).
- **If routines ever run concurrently on the same agent's `local_store` cache** — add a pitfall about LadybugDB lock contention (see the backlog note in `tools/CLAUDE.md`).
