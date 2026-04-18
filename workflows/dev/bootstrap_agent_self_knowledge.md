# Procedure: bootstrap-agent-self-knowledge

**Owner**: rdaneel (development persona)
**Flavor**: dev-agent (this markdown is the source of truth; `rdaneel-procedures` network carries a pointer via `workflow_path`)
**Current version**: v1.0
**Last refined**: 2026-04-18

## Summary

After an NDEx account exists for a new agent (see `onboard-new-agent-ndex-account`), create that agent's five standard self-knowledge networks (session-history, plans, collaborator-map, papers-read, procedures) plus any agent-specific extras (e.g., rcorona's query-history, rvernal's papers-reviewed + hypothesis-ledger, rboreal's mechanism-map-index, rsolstice's network-inventory, rgiskard's domain-model) plus an expertise-guide network. Publish each PUBLIC + Solr-indexed. The agent is then ready for its first autonomous session.

## When to use

- User has committed a new agent's CLAUDE.md to the repo (on main branch).
- `onboard-new-agent-ndex-account` has been run for the agent.
- No self-knowledge networks exist yet on NDEx for this agent (verify via `get_user_networks(username=<agent>, profile=local-<agent>)` — expect empty `data`).

## Preconditions

- New agent's CLAUDE.md is already merged on `main` and available at `GitHub/memento/agents/<agent>/CLAUDE.md`.
- Agent's expertise-guide network content — you should be able to extract it from the new CLAUDE.md (role, team, scope, protocols, what-they-do-not-do).
- Agent's NDEx account exists (`onboard-new-agent-ndex-account` completed).
- `local-<agent>` profile configured in `~/.ndex/config.json`, auth verified working.
- Workspace directory `~/.ndex/cache/<agent>/` exists.

## Steps

**1. Count the networks needed.**

Read the agent's CLAUDE.md Self-Knowledge section to count:
- 5 standard networks (session-history, plans, collaborator-map, papers-read, procedures) — always.
- N agent-specific extras (check CLAUDE.md — rvernal has 2, rboreal/rcorona/rsolstice/rgiskard have 1 each, rsolar has 0).
- 1 expertise-guide network — always.

Total = `5 + N + 1`. Verify you have the time budget: each network costs ~2 MCP calls (create + set_network_system_properties).

**2. Create the standard five + extras.**

For each network, use `mcp__ndex__create_network(network_spec=<json>, profile="local-<agent>")` with:

- `name`: simple `<agent>-<purpose>` form for self-knowledge (naming-exempt from `ndexagent` prefix per SHARED.md).
- `description`: one-sentence statement of purpose plus "authored by rdaneel on YYYY-MM-DD during bootstrap" when applicable.
- `properties`: always set `ndex-agent: <agent>`, `ndex-message-type: self-knowledge`, `ndex-workflow: <type>`, `ndex-network-type: <type>`.
- `nodes`: minimum root node. For plans, include mission + goals + seed actions (pull from the prior draft's Seed Mission if available, or craft from CLAUDE.md Role + Workflow). For session-history, include root + one "Session YYYY-MM-DD — Bootstrap (authored by rdaneel)" node with `status: completed`, `session_type: bootstrap`, `authored_by: rdaneel`, `actions_taken: ...`.
- `edges`: minimum for connectivity (root → chain-head; goal → action for plans).

**Procedures network specifics** — scientist-agent flavor for scientist agents: the network has one root node `"<agent> procedures root"` with `flavor: "scientist-agent"`, no procedure nodes yet. The agent populates it organically.

**3. Create the expertise-guide.**

Name: `ndexagent <agent> <descriptor> expertise guide` (uses `ndexagent` prefix; this is community-facing, not self-knowledge).

Properties: `ndex-agent: <agent>`, `ndex-message-type: expertise-guide`, `ndex-workflow: expertise-guide`.

Content: summarize from CLAUDE.md — agent-profile root, scope, workflow references, output-format contract, request-contract (how other agents ask for work), out-of-scope list. Make it self-contained: a peer agent reading this guide alone should understand how to interact with this agent.

**4. Set each network PUBLIC + indexed.**

For each created network UUID:
```
mcp__ndex__set_network_system_properties(
  network_id=<uuid>,
  properties='{"visibility": "PUBLIC", "index_level": "ALL"}',
  profile="local-<agent>"
)
```

Parallelize these calls — they're independent per network.

**5. Record in rdaneel self-knowledge.**

- Append a session node to `rdaneel-session-history` listing the agent bootstrapped, the N networks created, and their UUIDs under `networks_produced`.
- Append to `rdaneel-procedures` the `used_in_sessions` of this procedure-node.
- If anything was learned that should refine this procedure (new agent-specific extra, new field, new pitfall), update this markdown and bump `procedure_version` on the rdaneel-procedures node.

**6. Verify.**

Call `get_user_networks(username=<agent>, profile=local-<agent>, limit=20)` and confirm all expected networks are present, PUBLIC, `indexLevel: "ALL"`. Smoke-test `session_init(agent=<agent>, profile=local-<agent>)` — it should cache all self-knowledge into the local store and return `active_plans` populated from the plans network, `last_session` populated from the bootstrap session node.

## Pitfalls

- **Don't forget `index_level: ALL`.** Without it, the agent's self-knowledge is not discoverable via `search_networks` — other agents and rsentinel's watch loop will not find the agent. `visibility: PUBLIC` alone is not sufficient.
- **Plans network must be non-empty and have `active` actions.** A bootstrapped plans network with only a mission root node means the agent will wake up on first run with no actionable work and no clear starting point. Always seed 2–5 active actions drawn from the agent's Role / Workflow section.
- **`name` vs `ndexagent` prefix.** Self-knowledge networks are naming-exempt (`<agent>-<purpose>`). Expertise guide and other community-facing networks use `ndexagent <agent> ...`. Mixing these up breaks discovery.
- **Flat attributes only.** CX2 rejects nested dicts/arrays. If Seed Mission content contained nested structure, flatten to sibling keys. `multi_value_fields` can join with `, ` or ` ; `.
- **Agent-specific extras vary.** Re-read the agent's CLAUDE.md each time; don't copy a prior bootstrap blindly. rvernal has two extras, rsolar has zero, etc.
- **Expertise-guide content must track CLAUDE.md.** After a CLAUDE.md refactor, expertise guides may drift. Plan to re-publish them when role content changes substantially.

## When to refine

- **New standard self-knowledge network added** (e.g., if something joins the standard 5). Update Step 2 and the count.
- **New per-agent archetype** with a new kind of extra (if a future HPMI-X team introduces a new extra network shape).
- **Changes to network property schema** (e.g., new required `ndex-*` key).
- **Changes to bootstrapping tooling** — if a future `session_init` variant auto-creates empty self-knowledge networks, Step 2 may simplify dramatically.
- **Discovered issues** during bootstrap (e.g., today's 401-before-account-exists issue → linked back to onboard-new-agent-ndex-account as a dependency; if a similar class of dependency surfaces, add it to this procedure's Preconditions).
