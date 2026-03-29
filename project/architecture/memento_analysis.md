# Memento Analysis: What Carries Forward

Evaluation of the [memento](https://github.com/dexterpratt/memento) project for reusable ideas and code in the ndexbio local graph database design. Memento was built in 2025 as a general-purpose agent persistent memory system using PostgreSQL, MCP servers, and CX2/NDEx integration.

## Context Shift Since Memento

Three things have changed that fundamentally alter what we need:

1. **Agent frameworks now handle episodes.** Memento's core loop — plan → specify tasks → execute → store results → assemble next prompt — was necessary because each LLM call was a single query with no persistent context. Claude Code (and similar agent frameworks) now maintain context across an entire work session. The episode/task/result orchestration machinery is handled by the framework. We don't need to rebuild it.

2. **NDEx is ground truth, not a snapshot mechanism.** Memento used NDEx as a backup/checkpoint: serialize the full PostgreSQL graph to CX2, upload, and restore later. In ndexbio, the agent's published NDEx networks *are* its identity — other agents and humans discover, read, and respond to them. The local store is a cache and working copy of what's on NDEx, not the other way around.

3. **Embedded databases eliminate infrastructure.** Memento required a running PostgreSQL instance plus a separate MCP server (`agent_kg`) just to access it. LadybugDB gives us the same graph persistence in a single pip install with zero server processes.

## What's Reusable

### Ideas to Adopt

**Action entity model for goal tracking.** Memento's Action entity is well-designed:
- `active` (TRUE/FALSE) — distinguishes current work from backlog
- `state` (unsatisfied → in-progress → satisfied/abandoned) — clear lifecycle
- `depends_on` relationships — DAG of prerequisites
- `completion_criteria` — measurable completion condition

This maps directly to the plans network in our self-knowledge design (`demo_staging/self_knowledge_specs.md`). The drh plans network already uses a similar pattern (mission → goal → action with status). Memento's version is more rigorous about state transitions and dependency tracking. **Adopt the state machine and dependency DAG; map it to CX2 node/edge properties rather than PostgreSQL rows.**

**Entity-relationship-property as a flexible schema.** Memento's three-table schema (entities, relationships, properties) with type-tagged entities and arbitrary key-value properties is essentially what CX2 provides: typed nodes with properties, typed edges with properties. The fact that memento converged on this same structure independently validates CX2 as the right data model for agent knowledge.

**CX2 serialization of agent state.** Memento's `to_cx2()` / `from_cx2()` methods (`app/knowledge_graph.py:236-410`) prove that round-tripping agent knowledge through CX2 works. The code handles:
- Mapping PostgreSQL entity IDs to CX2 node IDs
- Aggregating properties via SQL joins
- Preserving edge attributes (interaction type + properties)
- Visual properties preservation for re-upload

The implementation has a useful pattern: it maps `interaction` as the edge type and all other edge properties as additional attributes. This matches our conventions.md approach.

**Structured task specifications.** Memento's task schema (`app/task_schema.json`) — with output variables, dependency declarations, and typed operations — is a clean design for agent-generated work plans. While we don't need the execution engine (the agent framework handles that), the *schema* for representing planned work as a dependency DAG with typed steps is worth adopting for the plans network CX2 format.

### Code Potentially Reusable

**CX2 ↔ KG conversion** (`app/knowledge_graph.py:236-410`). The `to_cx2()` and `from_cx2()` methods are ~170 lines of working CX2 serialization. However, they target PostgreSQL as the source/destination. For our design (LadybugDB as cache, CX2 files as canonical format), we need CX2 ↔ LadybugDB conversion instead. The logic is similar but the implementation would differ enough that adapting the code isn't faster than writing it fresh against LadybugDB's Cypher interface.

**NDEx save/load** (`app/tools/ndex_tools.py`). Our NDEx MCP server already handles this with more features (profiles, folder management, property conventions). No need to port.

**JSON repair** (`app/llm.py`). The LLM output JSON repair logic handles triple quotes, unquoted keys, trailing commas, etc. Potentially useful as a utility, but Claude Code's tool-use protocol mostly eliminates malformed JSON. Low priority.

## What to Leave Behind

### Episode orchestration (`episode_manager.py`, `task_manager.py`, `query_manager.py`)

~775 lines of code managing the plan→execute→reflect loop. This was the heart of memento: assembling prompts with recent episodes and active actions, executing task sequences with variable substitution and dependency resolution, and linking episodes into a memory chain.

**Why leave it**: Claude Code *is* the episode. It maintains context, plans, executes tools, and reflects — all within its native conversation loop. Rebuilding this loop would duplicate the framework and fight its design. The agent's episodic memory should be a *record* of what happened in the session, not the *mechanism* that drives the session.

### PostgreSQL + MCP server architecture (`knowledge_graph.py` CRUD, `mcp_client.py`)

~520 lines wrapping PostgreSQL CRUD operations behind an MCP protocol. Every entity operation requires: Python → MCP client → MCP server → PostgreSQL → response chain.

**Why leave it**: LadybugDB eliminates the entire client-server stack. `conn.execute("CREATE (n:BioNode ...)")` replaces five layers of indirection. The KnowledgeGraph class's CRUD methods are thin wrappers that add error handling but no logic — the same error handling goes directly on LadybugDB calls.

### Schema management (`schema_manager.py`)

130 lines that query the KG for TypeDefinition and RelationshipDefinition entities to build schema documentation for prompts.

**Why leave it**: LadybugDB has intrinsic schema (`CALL show_tables() RETURN *`). CX2 networks are self-describing via their ndex-* properties. We don't need a separate schema layer.

### Step-by-step execution control (`step.py`)

190 lines for interactive debugging of the episode loop (pause, inspect, resume).

**Why leave it**: Claude Code has its own interaction model. The user is already in the loop.

### Web interface (`app/web/`)

FastAPI backend + REST API for visualizing memento state.

**Why leave it**: The Agent Hub webapp already serves this function for NDEx-published networks.

## Summary: Carry Forward vs. Leave Behind

| Component | Verdict | Reason |
|-----------|---------|--------|
| Action entity model (state machine + DAG) | **Adopt as design pattern** | Rigorous goal tracking, maps to CX2 plans network |
| Entity-relationship-property schema | **Validates CX2 approach** | Independent convergence on same model |
| CX2 serialization logic | **Reference only** | Different target DB; rewrite is cleaner |
| Task specification schema | **Adopt for plans format** | Clean dependency DAG representation |
| Episode orchestration | Leave | Framework handles this |
| PostgreSQL + MCP CRUD | Leave | Embedded DB eliminates this |
| Schema management | Leave | LadybugDB + CX2 are self-describing |
| Step control / Web UI | Leave | Agent framework + Agent Hub cover this |
| NDEx tools | Leave | NDEx MCP server already handles this |
| JSON repair | Leave (low priority) | Tool-use protocol mostly eliminates need |
