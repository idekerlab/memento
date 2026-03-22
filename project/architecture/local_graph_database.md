# Local Graph Database and Agent Knowledge Store

## Problem

Agents currently interact with networks only through the NDEx API — downloading full CX2 JSON into LLM context for every query. This creates three compounding problems:

1. **Repeated downloads**: Every session re-fetches the same networks. An agent checking its own plans, collaborator map, or episodic memory re-downloads them each time.

2. **Context window waste**: Loading a 500-edge BEL network into LLM context to answer "what regulates TRIM25?" wastes tokens on hundreds of irrelevant edges. The agent cannot query the graph — it can only read it linearly.

3. **No cross-network operations**: The most valuable analytical operations — finding shared nodes across papers, detecting contradictions between knowledge graphs, tracing paths through merged networks — require holding multiple networks in memory simultaneously and performing graph traversals. This is impractical in LLM context and impossible through the NDEx API alone.

## Design: Two-Tier Local Store

### Tier 1: SQLite Metadata Catalog

Every network the agent has downloaded or created gets a row in a SQLite database:

| Column | Type | Purpose |
|--------|------|---------|
| uuid | TEXT PK | NDEx UUID (or local UUID for unpublished networks) |
| name | TEXT | Network name |
| data_type | TEXT | graph, tabular, agent-state |
| category | TEXT | science-kg, interaction-data, plan, episodic-memory, collaborator-map, review-log, request, message |
| agent | TEXT | Owning agent (rdaneel, drh, etc.) |
| node_count | INTEGER | Number of nodes |
| edge_count | INTEGER | Number of edges |
| ndex_modified | TEXT | NDEx modification timestamp |
| local_modified | TEXT | Local modification timestamp |
| local_path | TEXT | Path to cached CX2 JSON file |
| is_dirty | BOOLEAN | Local changes not yet pushed to NDEx |
| properties | JSON | All ndex-* properties as key-value pairs |

The catalog is the agent's first stop for any network-related question. Before downloading anything, the agent (or a subagent) queries the catalog: "Do I have this network? When was it last updated? What type is it?"

### Tier 2: Embedded Graph Database (LadybugDB)

Cached networks are stored in an embedded graph database for persistent, queryable graph operations. This enables:

- **Neighborhood queries**: "What interacts with TRIM25?" — Cypher query without loading the full network into LLM context
- **Path queries**: "How does NS1 connect to RIG-I signaling?" — variable-length path traversal
- **Cross-network queries**: "Which proteins appear in both the TRIM25 paper and the Krogan interactome?" — natural in Cypher across shared node tables
- **Pattern matching**: "Find all edges where protein A increases protein B but another paper says A decreases B" — declarative contradiction detection
- **Topological analysis**: degree, clustering, connected components via built-in algorithm extension

#### Why LadybugDB (not NetworkX)

The initial design proposed NetworkX with a KuzuDB migration path. After evaluation, starting with the embedded graph database is the right call:

**CX2 compatibility**: CX2 networks have integer node/edge IDs and arbitrary per-element properties. NetworkX accepts arbitrary node IDs but has no query language to exploit them. LadybugDB maps CX2 IDs directly to INT64 primary keys and supports `MAP(STRING, STRING)` columns for arbitrary properties.

**Network-level metadata**: CX2 networks carry network-level properties (name, description, ndex-* metadata). NetworkX has no concept of graph-level properties. LadybugDB stores these in a Metadata node table — structured and queryable.

**Query language vs. bespoke code**: Every graph operation in NetworkX requires custom Python traversal code. Cypher handles neighborhood queries, path finding, and pattern matching declaratively. The bespoke code needed for NetworkX would exceed the schema setup for LadybugDB within the first two use cases.

**Persistence**: LadybugDB persists to a single file automatically. NetworkX requires manual serialization/deserialization for every session.

**Migration path**: If advanced graph algorithms (centrality, community detection) are needed beyond what LadybugDB's `algo` extension provides, LadybugDB can export to NetworkX graph objects on demand.

#### About LadybugDB

LadybugDB is the active community fork of KuzuDB, which was archived in October 2025 at v0.11.3. LadybugDB (currently v0.15.1) continues active development under MIT license.

Key characteristics:
- **Truly embedded**: single `pip install`, ~4-8 MB wheel, no server process, no Docker
- **Single-file database**: `db = Database("my_graph.db")` or in-memory with `Database(":memory:")`
- **Cypher query language**: openCypher with near-feature-parity to Neo4j
- **Schema-required**: node/edge tables must be declared, but properties can be NULL and MAP/JSON columns handle arbitrary key-value data
- **Performance**: at our scale (100-10,000 nodes), queries are sub-millisecond. Benchmarked at 100K nodes / 2.4M edges with sub-second queries.

#### Graph Schema for CX2 Data

```python
# Node table — preserves CX2 node IDs as primary keys
conn.execute("""
    CREATE NODE TABLE BioNode(
        id INT64 PRIMARY KEY,
        network_uuid STRING,
        name STRING,
        node_type STRING,
        properties MAP(STRING, STRING)
    )
""")

# Edge table — typed interactions with arbitrary properties
conn.execute("""
    CREATE REL TABLE Interacts(
        FROM BioNode TO BioNode,
        edge_id INT64,
        network_uuid STRING,
        interaction STRING,
        properties MAP(STRING, STRING)
    )
""")

# Network-level metadata
conn.execute("""
    CREATE NODE TABLE Network(
        uuid STRING PRIMARY KEY,
        name STRING,
        description STRING,
        properties MAP(STRING, STRING)
    )
""")

# Which nodes belong to which networks
conn.execute("""
    CREATE REL TABLE InNetwork(FROM BioNode TO Network)
""")
```

#### Example Queries

```cypher
-- Neighborhood: what interacts with TRIM25?
MATCH (n:BioNode {name: 'TRIM25'})-[r:Interacts]-(neighbor:BioNode)
RETURN neighbor.name, r.interaction, r.properties

-- Path: how does NS1 connect to RIG-I signaling?
MATCH path = (a:BioNode {name: 'NS1'})-[:Interacts*1..4]-(b:BioNode {name: 'RIG-I'})
RETURN path

-- Cross-network: proteins in both TRIM25 paper and Krogan interactome
MATCH (n:BioNode)-[:InNetwork]->(net1:Network {name: 'TRIM25_analysis'})
MATCH (n)-[:InNetwork]->(net2:Network {name: 'Krogan_IAV'})
RETURN n.name

-- Contradiction detection: same pair, opposite relations
MATCH (a:BioNode)-[r1:Interacts]->(b:BioNode),
      (a)-[r2:Interacts]->(b)
WHERE r1.network_uuid <> r2.network_uuid
  AND r1.interaction = 'increases' AND r2.interaction = 'decreases'
RETURN a.name, b.name, r1.network_uuid, r2.network_uuid
```

#### Caveats

- **On-disk format not stabilized across versions**: version upgrades may require re-import. Since CX2 JSON files remain the canonical format and NDEx is ground truth, the local DB is always rebuildable.
- **Schema is required**: unlike NetworkX's fully dynamic model, node/edge tables must be declared. MAP columns mitigate this but heterogeneous networks may need multiple node table types.

## Four Categories of Cached Data

### 1. Science Knowledge Graphs

BEL networks extracted from papers. These are the core analytical substrate — the agent merges, queries, and extends them as it reads more literature.

**Typical operations**: neighborhood queries, path finding, cross-network merge, contradiction detection (same edge with opposite relations in different papers).

### 2. Interaction Datasets

PPI networks, co-expression data, interactomes (e.g., Krogan IAV interactome). Dense, less annotated. Used as reference data for validating or extending knowledge graphs.

**Typical operations**: membership queries ("is TRIM25 in the Krogan interactome?"), shared interactor analysis, degree/centrality statistics.

### 3. Tabular Data in Network Form

NDEx can store tabular data as networks, but the graph model adds nothing. Paper triage logs, scan results, scoring tables — these need column filtering, aggregation, sorting.

**Typical operations**: SQL queries — filter by score, sort by date, aggregate by category. Stored as SQLite tables alongside the catalog, not in the graph database.

### 4. Agent Self-Knowledge Networks

Plans, episodic memory, collaborator maps, operational state. These are the agent's own persistent knowledge, published to NDEx for transparency and collaboration but queried locally for speed.

**This is the category that changes the agent's relationship to its own state.** Currently, an agent's working memory is a markdown file (e.g., `agents/rdaneel/working_memory.md`). Self-knowledge networks on NDEx (plans, episodic memory, collaborator maps) are richer and more structured, but the agent can't efficiently query them without downloading the full network each session.

With a local graph store, the agent's self-knowledge networks become a queryable, persistent knowledge base:

- **Plans network**: Query current goals, find actions by status, traverse goal→action hierarchy
- **Episodic memory**: Query past sessions by topic, find when a specific paper was first encountered, trace the evolution of a hypothesis across sessions
- **Collaborator map**: Look up expertise areas, find who to consult for a specific topic, check interaction history

The local store is the working copy. NDEx is the publication venue. The agent reads and writes locally, then syncs to NDEx when ready — analogous to how a scientist maintains working notes locally and publishes papers to a journal.

## Subagent Filtering Pattern

The catalog enables a key optimization: the main agent never loads raw graph data into its own context.

1. Main agent queries the catalog to identify relevant cached networks
2. Spawns a subagent (Haiku or Sonnet) with the specific network loaded
3. Subagent runs the query and returns a filtered subset
4. Main agent receives only the relevant results

This keeps the main agent's context focused on planning and synthesis while subagents handle data retrieval.

## Sync Model: Local-First, NDEx as Publication

| Operation | Flow |
|-----------|------|
| Agent creates a network | Written locally first (is_dirty=true) |
| Agent queries a network | Always local — from cache or catalog |
| Agent publishes | Local → NDEx push, clear is_dirty flag |
| Agent discovers new content | NDEx search → download → add to catalog |
| Staleness check | Compare ndex_modified timestamp on access |

The agent works locally by default. NDEx operations happen at natural boundaries: publishing a completed analysis, checking for new content from other agents, syncing self-knowledge for transparency.

## Staleness and Consistency

NDEx is ground truth for content published by other agents. For the agent's own networks, the local copy is authoritative until published.

- **Other agents' content**: Check NDEx modification timestamp on first access per session. Re-download if stale.
- **Own content**: Local is authoritative. Sync to NDEx explicitly.
- **Conflict resolution**: Not needed in the near term — each agent owns its own networks. Future multi-agent collaboration on shared networks would require a merge strategy.

## Cache Location

`~/.ndex/cache/` — shared across projects and agent repos. Structure:

```
~/.ndex/cache/
  catalog.db              # SQLite catalog (Tier 1)
  graph.db                # LadybugDB graph database (Tier 2)
  networks/
    {uuid}.cx2            # Canonical CX2 JSON files (rebuildable source)
```

## Implementation Phases

### Phase 1: Catalog + Graph Store + CX2 Import
- SQLite catalog with network metadata
- LadybugDB graph schema for CX2 data
- CX2 JSON import/export (preserving node/edge IDs and properties)
- MCP tools: `cache_network`, `query_catalog`, `query_graph`
- Agent self-knowledge networks cached on first access

### Phase 2: Cross-Network Operations + Agent State
- Cross-network queries via shared node tables
- Contradiction detection across BEL networks
- Agent self-knowledge as primary working state
- Working memory migration from markdown to local graph
- Bidirectional sync with NDEx

### Phase 3: Advanced Analysis
- Composite knowledge graphs merged across papers
- NetworkX export for algorithms not covered by LadybugDB
- Subagent filtering pattern for context-efficient queries

## Relationship to Existing Components

- **NDEx MCP server** (`tools/ndex_mcp/`): Remains the interface to the NDEx platform. The local cache sits between the agent and the MCP server, intercepting reads and buffering writes.
- **Agent working memory** (`agents/rdaneel/working_memory.md`): Gradually replaced by queryable self-knowledge networks in the local store. The markdown file becomes a session scratch pad rather than the canonical state.
- **Self-knowledge networks** (`demo_staging/self_knowledge_specs.md`): The CX2 specs for plans, episodic memory, and collaborator maps define the schema for agent state networks. These become the primary format for agent self-knowledge, stored locally and synced to NDEx.
- **Communication design** (`project/architecture/agent_communication_design.md`): Inbox scanning and message discovery still happen via NDEx API. The local cache stores downloaded messages for reference but does not replace NDEx as the communication channel.

## Relationship to Memento

The [memento](https://github.com/dexterpratt/memento) project (2025) explored similar territory: persistent agent memory with episodic, planning, and world-knowledge components stored in a knowledge graph. See `project/architecture/memento_analysis.md` for a detailed evaluation of what carries forward.

Key ideas adopted:
- **Action entity model** for goal tracking (active/state/depends_on pattern)
- **CX2 serialization** of agent knowledge graphs to/from NDEx
- **Entity-relationship-property schema** as a flexible knowledge representation

Key differences from memento's approach:
- **Embedded graph DB** (LadybugDB) replaces PostgreSQL + MCP server — zero infrastructure overhead
- **NDEx as ground truth** for published state, not just a snapshot/backup mechanism
- **Long-context episodes** replace single-query episodes — the agent framework (Claude Code) handles multi-step work within a session, so the episode/task/result machinery is handled by the framework rather than bespoke code
- **CX2 as canonical format** — the graph DB is a queryable cache of CX2 networks, not the primary representation
- **Network-centric** rather than entity-centric — the unit of work is a biological network with graph structure, not an arbitrary entity collection
