# Local Store Testing Plan

Testing plan for the two-tier local store (SQLite catalog + LadybugDB graph database). Structured so that all required permissions and directory access can be granted up front.

## Permissions and Access Required

Grant all of these at session start:

### File System
- **Read/write**: `~/.ndex/cache/` (catalog.db, graph.db, networks/*.cx2)
- **Read/write**: project working directory for test fixtures and output
- **Read**: `demo_staging/self_knowledge_specs.md` (CX2 test fixtures)
- **Read**: `agents/rdaneel/working_memory.md` (episodic data reference)

### Python Packages
- `pip install ladybugdb` (embedded graph database)
- `pip install ndex2` (CX2 format handling — already installed)
- `pip install pytest pytest-asyncio` (if not already installed)

### NDEx API (for round-trip tests)
- **Read**: public networks (no auth needed)
- **Read/write**: agent account networks (via `~/.ndex/config.json` profile)

### Shell Commands
- `mkdir -p ~/.ndex/cache/networks`
- `rm -rf ~/.ndex/cache/test_*` (cleanup between test runs)
- `python -m pytest` (test execution)

---

## Test Tiers

### T0: Environment and Dependencies

Verify the stack works before testing any logic.

| # | Test | What It Proves |
|---|------|----------------|
| T0.1 | `import ladybugdb` succeeds | Package installed correctly |
| T0.2 | Create in-memory database, execute `RETURN 1` | Engine runs, Cypher works |
| T0.3 | Create on-disk database at `~/.ndex/cache/test_t0.db`, close, reopen, query | Persistence works |
| T0.4 | Create SQLite catalog at `~/.ndex/cache/test_catalog.db` with schema | SQLite works |
| T0.5 | `from ndex2.cx2 import CX2Network` succeeds | CX2 library available |
| T0.6 | Cleanup: remove test_t0.db, test_catalog.db | Cleanup path works |

### T1: SQLite Catalog Operations

Test the metadata catalog independently of the graph database.

| # | Test | What It Proves |
|---|------|----------------|
| T1.1 | Create catalog with full schema (all columns from design doc) | Schema is valid |
| T1.2 | Insert a network record, query by uuid | Basic CRUD |
| T1.3 | Insert 5 records with different categories, query by category | Filtering works |
| T1.4 | Update `is_dirty`, `local_modified`; verify old values replaced | Updates work |
| T1.5 | Query by `agent` column | Multi-agent catalog support |
| T1.6 | Insert record with JSON `properties` column, query and parse | JSON column works |
| T1.7 | Insert duplicate uuid — verify constraint violation | PK enforcement |
| T1.8 | Delete a record by uuid, verify gone | Deletion works |

### T2: LadybugDB Schema and Basic Operations

Test graph database operations with our CX2-oriented schema.

| # | Test | What It Proves |
|---|------|----------------|
| T2.1 | Create BioNode, Network, Interacts, InNetwork tables per design schema | Schema creation works |
| T2.2 | Insert a single BioNode with id, name, node_type, MAP properties | Node creation with MAP works |
| T2.3 | Insert two BioNodes, create Interacts edge between them | Edge creation works |
| T2.4 | Insert a Network node, create InNetwork edges for BioNodes | Network membership works |
| T2.5 | Query: `MATCH (n:BioNode) RETURN n.name` — verify all nodes returned | Basic query |
| T2.6 | Query: `MATCH (n:BioNode {name: 'X'})-[r:Interacts]-(m) RETURN m.name` | Neighborhood query |
| T2.7 | Query: `MATCH (n:BioNode)-[:InNetwork]->(net:Network) WHERE net.uuid = 'X' RETURN n` | Network membership query |
| T2.8 | Update a node's properties MAP via SET | Property update |
| T2.9 | Delete a node, verify edges cascade or handle correctly | Deletion behavior |
| T2.10 | Insert nodes with NULL name or empty MAP — verify handling | Edge cases |

### T3: CX2 Import/Export Round-Trip

The critical tests. Verify that CX2 networks survive import into LadybugDB and export back without data loss.

#### T3.1: Minimal Network
- Create a CX2 network with 2 nodes, 1 edge, basic properties
- Import into LadybugDB
- Export back to CX2
- **Verify**: node IDs preserved, edge source/target correct, all properties present, network-level attributes intact

#### T3.2: Self-Knowledge Networks (from demo specs)
- Load each of the three self-knowledge CX2 specs from `demo_staging/self_knowledge_specs.md`:
  - Plans network (11 nodes, 10 edges, hierarchical)
  - Episodic memory (5 nodes, 4 edges, temporal chain)
  - Collaborator map (7 nodes, 12 edges, heterogeneous)
- Import each into LadybugDB
- Export back to CX2
- **Verify**: node count, edge count, all node/edge properties, interaction types

#### T3.3: BEL Knowledge Graph
- Construct or download a Tier 3 BEL analysis network (e.g., TRIM25/RdRp, ~14 nodes, 14 edges)
- Import into LadybugDB
- Export back to CX2
- **Verify**: BEL-specific properties (function, modification, evidence, citation), edge interaction types (increases, directlyIncreases, etc.)

#### T3.4: Larger Network
- Download a real network from NDEx (e.g., Krogan IAV interactome, ~500+ nodes)
- Import into LadybugDB
- Export back to CX2
- **Verify**: node/edge counts match, spot-check 10 random nodes for property preservation

#### T3.5: Properties Edge Cases
- Network with:
  - Nodes with no properties (empty MAP)
  - Nodes with many properties (10+ key-value pairs)
  - Properties with special characters in values (quotes, newlines, unicode)
  - Edges with properties vs. edges with no properties
- Round-trip and verify all preserved

#### T3.6: Multiple Networks in One Database
- Import 3 different networks into the same LadybugDB instance
- Verify each network's nodes are tagged with correct `network_uuid`
- Verify InNetwork edges correctly associate nodes to networks
- Query nodes belonging to a specific network — verify no cross-contamination

### T4: Graph Queries on Real Data

Test Cypher queries against imported biological networks.

| # | Test | What It Proves |
|---|------|----------------|
| T4.1 | Neighborhood: find all neighbors of a known protein | Basic traversal works on real data |
| T4.2 | 2-hop neighborhood: `*1..2` variable-length path | Multi-hop works |
| T4.3 | Path finding: find path between two known-connected proteins | Variable-length path query |
| T4.4 | Cross-network: find proteins present in two imported networks | Cross-network join |
| T4.5 | Filter by edge type: find all `increases` relationships | Edge type filtering |
| T4.6 | Filter by node property: find all nodes where type = 'protein' | MAP property filtering |
| T4.7 | Aggregation: count nodes per network | GROUP BY / aggregation |
| T4.8 | Contradiction detection: find same node pair with opposite edge types across networks | The key analytical query |

### T5: Agent Self-Knowledge Operations

Test the specific patterns agents use to manage their own state.

#### T5.1: Plans Network Operations
- Import drh plans network
- Query: find all actions with state = 'planned'
- Query: traverse mission → goal → action hierarchy
- Update: change an action's state from 'planned' to 'in_progress'
- Create: add a new action node, link with `has_action` edge
- Export to CX2 — verify new action present

#### T5.2: Episodic Memory Operations
- Import drh episodic memory
- Query: find most recent session (latest timestamp)
- Query: find session where a specific paper was first mentioned (text search in `actions_taken` property)
- Create: add a new session node, link with `followed_by` edge to previous
- Export to CX2 — verify temporal chain intact

#### T5.3: Collaborator Map Operations
- Import drh collaborator map
- Query: find all agents with role = 'literature_reviewer'
- Query: find all collaborators with expertise containing 'ubiquitin'
- Create: add a new agent node with expertise properties
- Create: add `collaborates_with` edge
- Export to CX2 — verify new relationships present

### T6: Catalog + Graph Integration

Test the two tiers working together.

| # | Test | What It Proves |
|---|------|----------------|
| T6.1 | Import a CX2 network: creates catalog entry AND graph data | Full import pipeline |
| T6.2 | Query catalog for network by category, then query graph for its nodes | Tier 1 → Tier 2 flow |
| T6.3 | Mark network as dirty in catalog, export from graph, verify is_dirty cleared | Dirty flag lifecycle |
| T6.4 | Import network, delete from graph, verify catalog entry updated or removed | Deletion consistency |
| T6.5 | Import same network twice — verify update rather than duplicate | Idempotent import |

### T7: NDEx Round-Trip (Integration)

End-to-end tests requiring NDEx API access. These can be skipped in offline testing.

| # | Test | What It Proves |
|---|------|----------------|
| T7.1 | Download public network from NDEx → import to local store → query → verify | Full NDEx-to-local pipeline |
| T7.2 | Create network locally → export to CX2 → upload to NDEx → download → compare | Full round-trip through NDEx |
| T7.3 | Download agent's own network → modify locally → re-upload → verify changes on NDEx | Local-first edit + sync |
| T7.4 | Check staleness: import network, wait, check NDEx modification timestamp | Staleness detection works |

### T8: Error Handling and Edge Cases

| # | Test | What It Proves |
|---|------|----------------|
| T8.1 | Import malformed CX2 (missing nodes array) — verify graceful error | Bad input handling |
| T8.2 | Query non-existent network UUID in catalog — verify empty result | Missing data handling |
| T8.3 | Import network with node ID collisions across networks — verify isolation | Multi-network safety |
| T8.4 | Open database while another process has it open — verify behavior | Concurrent access |
| T8.5 | Import network, corrupt database file, rebuild from CX2 files | Recovery from CX2 source |
| T8.6 | Database at `~/.ndex/cache/` doesn't exist on first run — verify auto-creation | First-run experience |

### T9: Performance Baselines

Not pass/fail — establish baseline measurements for future comparison.

| # | Test | Measurement |
|---|------|-------------|
| T9.1 | Import 100-node network | Time to import |
| T9.2 | Import 1000-node network | Time to import |
| T9.3 | Neighborhood query on 1000-node network | Query latency |
| T9.4 | Cross-network query across 5 imported networks | Query latency |
| T9.5 | Export 1000-node network to CX2 | Time to export |
| T9.6 | Catalog query with 100 entries | Query latency |

---

## Test Fixtures

### Pre-built CX2 networks needed:
1. **Minimal**: 2 nodes, 1 edge (inline in test code)
2. **Self-knowledge**: parsed from `demo_staging/self_knowledge_specs.md`
3. **BEL network**: constructed from a Tier 3 analysis or downloaded from NDEx
4. **Large network**: downloaded from NDEx (Krogan IAV interactome or similar public network)

### Test database locations:
All test databases use `~/.ndex/cache/test_*` prefix for easy cleanup:
- `~/.ndex/cache/test_catalog.db`
- `~/.ndex/cache/test_graph.db`
- `~/.ndex/cache/test_networks/`

### Cleanup:
`rm -rf ~/.ndex/cache/test_*` between full test runs.

---

## Implementation Notes

- Tests should be implementable as a standard pytest suite under `tests/local_store/`
- T0–T6 run offline (no network access required)
- T7 requires NDEx API access and valid credentials
- T8–T9 can run offline
- Consider `@pytest.fixture` for database setup/teardown with test-prefixed paths
- Use `conftest.py` for shared fixtures (catalog schema, graph schema, sample CX2 networks)
