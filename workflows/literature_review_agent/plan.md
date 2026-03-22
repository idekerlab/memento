# Literature Review Agent — Design & Implementation Plan

## Vision

An agent that monitors bioRxiv for recent preprints on a user-specified topic,
triages them, selects the most interesting one, reads the full PDF, and posts a
structured review to NDEx. The review includes a mechanistic analysis expressed
as a BEL knowledge graph, posted as a CX2 network where:

- The **network description** is the review document (summary, key findings,
  significance, critique).
- The **network nodes and edges** are the BEL knowledge graph extracted from
  the paper's mechanistic claims.

This is the first concrete workflow in the agent communication paradigm defined
in `project/architecture/agent_communication_design.md`. The agent acts as an NDEx
user, posting content that both humans and other agents can discover, read,
and respond to.

---

## Architecture

```
User (via NDEx or CLI)
  ↓  topic query + parameters
Literature Review Agent
  ├── Step 1: Discover — bioRxiv API + optional Semantic Scholar
  ├── Step 2: Triage   — rank by relevance, recency, novelty
  ├── Step 3: Read     — fetch PDF, extract text
  ├── Step 4: Analyze  — write review + extract BEL statements
  ├── Step 5: Build    — convert BEL to CX2 network spec
  └── Step 6: Post     — create network on NDEx with review as description
NDEx (ndexbio.org)
  ↓  discoverable by keyword, author, ndexagent prefix
Human / Other Agents
```

---

## Inputs

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `topic` | Yes | — | Search query (e.g., "TP53 DNA damage response") |
| `category` | No | None | bioRxiv category filter (e.g., "cell_biology", "systems_biology") |
| `days_back` | No | 7 | How far back to scan for preprints |
| `max_triage` | No | 10 | Max papers to consider during triage |
| `visibility` | No | PRIVATE | NDEx visibility for posted review |

---

## Step 1: Discover Recent Preprints

### Data sources

**Primary: bioRxiv API** (`project/apis/biorxiv_api.md`)
- Endpoint: `https://api.biorxiv.org/details/biorxiv/{start_date}/{end_date}`
- Supports category filtering via `?category=` querystring
- Returns: DOI, title, authors, abstract, date, category
- Paginated at 100 results per call

**Secondary (optional): Semantic Scholar**
- Can supplement with citation-aware ranking and related-paper discovery
- Existing client in `tools/robust_literature_search.py` (needs review — see
  Phase 2 notes below)

### Implementation approach

Write a lightweight `biorxiv_client.py` that:
1. Queries the bioRxiv API for the date range and optional category
2. Paginates through results
3. Returns a list of paper metadata dicts
4. Handles rate limiting and transient errors

Do NOT yet integrate `robust_literature_search.py` — it needs review and its
dependencies (corpus_analyzer, citation_extractor) add coupling. Phase 1 uses
bioRxiv directly. Phase 2 can integrate the robust search infrastructure
after auditing it.

### Output

List of candidate paper metadata (title, DOI, authors, abstract, date,
category).

---

## Step 2: Triage and Select

The agent ranks candidate papers by relevance to the topic and selects one
for full review. Triage annotations are persisted to the review log (see
"Review Log" section below) so that previously-triaged but unreviewed papers
remain candidates for future sessions.

### Triage criteria

The agent uses its own judgment (LLM reasoning) to assess:
- **Relevance** (1-5): How closely does the abstract match the topic query?
- **Mechanistic content** (1-5): Does the abstract suggest the paper describes
  molecular/cellular mechanisms (needed for BEL extraction)?
- **Novelty** (1-5): Does it present new findings vs. review/methods-only?
- **Specificity** (1-5): Does the abstract name concrete genes, pathways, or
  biological processes?
- **Overall interest** (1-5): Composite assessment

### Implementation approach

1. Download the current review log from NDEx (or create it on first run)
2. Filter out papers already reviewed (status = "reviewed")
3. Present candidate abstracts to the agent in a single prompt
4. Agent returns scored annotations for each paper
5. All triaged papers are written to the review log with their scores
   and status = "triaged"
6. The agent selects the highest-scoring paper for review — this may be
   a paper triaged in a previous session if it scores higher than the
   current batch
7. Triage results are also logged in the session directory

### Output

Selected paper metadata + triage rationale document.

---

## Step 3: Read the Full Paper

### PDF acquisition

bioRxiv preprints are accessible at predictable URLs:
- PDF: `https://www.biorxiv.org/content/{DOI}v{version}.full.pdf`
- The DOI and version are available from Step 1 metadata

### Text extraction

Use the agent's PDF reading capability (Claude Code `Read` tool handles PDFs
natively). If the PDF is too large:
- Read key sections: Abstract, Introduction, Results, Discussion, Methods
  (in that priority order)
- Skip supplementary figures and large data tables

### Output

Extracted text organized by section, ready for analysis.

---

## Step 4: Analyze — Review + BEL Extraction

This is the core intellectual step. The agent performs two parallel analyses:

### 4a. Write the review

Structure:
- **One-paragraph summary**: What the paper does and finds
- **Key findings**: 3-5 bullet points of the main results
- **Mechanistic insights**: What molecular/cellular mechanisms are described
  or proposed
- **Significance**: Why this matters in the field
- **Limitations and open questions**: Critical assessment

This becomes the network description on NDEx.

### 4b. Extract BEL statements

Using the BEL extraction approach from `workflows/BEL/bel_prompt.md` as
guidance, but adapted for raw text (no pre-annotated entities):

1. Agent reads each mechanistically relevant section
2. Identifies molecular entities (genes, proteins, processes, diseases,
   small molecules)
3. Extracts causal/correlative relationships between entities
4. Expresses each relationship as a BEL statement
5. Records the evidence sentence for each statement

**Phase 1 simplification**: Best-effort BEL extraction. The agent extracts
BEL directly from text using its own knowledge for entity resolution. It
should use standard identifiers (HGNC, GO, ChEBI) where confident and plain
names otherwise. No formal validation or grounding pipeline. The goal is a
working POC for collaborator demonstration, not production-grade curation.

**Cap**: Maximum 500 BEL statements per paper in Phase 1. NDEx handles
very large networks (hundreds of thousands of edges), but 500 is a
practical ceiling for a single paper's mechanistic content and keeps
review time bounded.

### BEL output format

```json
[
  {
    "bel": "p(HGNC:TP53) increases bp(GO:\"apoptotic process\")",
    "evidence": "TP53 activation led to increased apoptosis in treated cells.",
    "section": "Results",
    "confidence": "high"
  },
  ...
]
```

### Output

- Review text (markdown)
- List of BEL statements with evidence

---

## Step 5: Build CX2 Network from BEL

Convert the BEL statements into a CX2 network spec.

### Node mapping

Each unique BEL term becomes a node:
- `p(HGNC:TP53)` → node with `name: "TP53"`, `type: "protein"`,
  `namespace: "HGNC"`, `bel_function: "p"`
- `bp(GO:"apoptotic process")` → node with `name: "apoptotic process"`,
  `type: "biological_process"`, `namespace: "GO"`,
  `bel_function: "bp"`

### Edge mapping

Each BEL statement becomes an edge:
- Source and target are the subject and object BEL terms
- Edge attributes: `interaction` (the BEL relation), `bel_statement`
  (the full BEL string), `evidence` (the source sentence),
  `confidence`

### Network metadata

```json
{
  "name": "ndexagent review: <paper title (truncated)>",
  "description": "<full review text from Step 4a>",
  "version": "1.0",
  "properties": {
    "ndex-agent": "claude-code",
    "ndex-workflow": "literature-review",
    "ndex-session": "<timestamp>",
    "ndex-source": "<paper DOI>",
    "ndex-doi": "<paper DOI>",
    "ndex-data-type": "bel-knowledge-graph",
    "ndex-message-type": "analysis"
  }
}
```

### Implementation

Write a `bel_to_cx2.py` module that:
1. Parses BEL statement list from Step 4
2. Deduplicates nodes (same BEL term → same node)
3. Creates edges with full attribution
4. Returns a network spec dict ready for `create_network`

### Output

CX2 network spec (JSON).

---

## Step 6: Post to NDEx

Using the existing NDEx MCP tools:

1. `create_network(network_spec)` — post the review network
2. `set_network_properties(network_id, properties)` — set ndex- metadata
3. `set_network_visibility(network_id, visibility)` — default PRIVATE
4. Log the network UUID in the session directory

### NDEx conventions compliance

Per `project/architecture/conventions.md`:
- Name prefixed with `ndexagent`
- All custom properties use `ndex-` prefix
- Network created as PRIVATE by default
- Searchable via `ndexagent review` or `ndexagent <topic>`

---

## Review Log (NDEx-hosted)

The agent maintains a persistent review log as a CX2 network on its NDEx
account. This serves as memory across sessions: which papers have been seen,
triaged, or reviewed.

### Why a network?

- Stored on NDEx alongside the agent's other content — no local state to lose
- Discoverable and inspectable by humans and other agents
- Can be downloaded and queried programmatically (JSON, not token-expensive)
- Follows the paradigm: everything the agent knows is on NDEx

### Network structure

**Name**: `ndexagent review log <topic>`

**Each node is a paper** with these attributes:
- `doi`: paper DOI
- `title`: paper title
- `authors`: first author et al.
- `date`: publication/posting date
- `category`: bioRxiv category
- `status`: one of `"triaged"`, `"reviewed"`, `"skipped"`
- `relevance_score`: 1-5 from triage
- `mechanistic_score`: 1-5 from triage
- `novelty_score`: 1-5 from triage
- `specificity_score`: 1-5 from triage
- `overall_interest`: 1-5 composite score
- `triage_rationale`: brief text justification
- `review_network_id`: UUID of posted review (if status = "reviewed")
- `triaged_date`: when the agent first assessed this paper
- `reviewed_date`: when the agent completed the review (if applicable)

**No edges** in Phase 1 — the log is a flat list of papers. Phase 2 could
add edges for paper-to-paper relationships (cites, related-to, supersedes).

### Network metadata

```json
{
  "name": "ndexagent review log <topic>",
  "description": "Persistent log of papers triaged and reviewed by the literature review agent for topic: <topic>",
  "properties": {
    "ndex-agent": "claude-code",
    "ndex-workflow": "literature-review",
    "ndex-data-type": "review-log",
    "ndex-topic": "<topic>"
  }
}
```

### Operations

**Startup**: Search NDEx for `ndexagent review log <topic>` owned by the
agent's account. If found, download it. If not, create it.

**After triage**: Add new paper nodes (status = "triaged") with scores.
Update the network on NDEx via `update_network`.

**After review**: Update the selected paper's node: set status = "reviewed",
add `review_network_id` and `reviewed_date`. Update on NDEx.

**Selection logic**: When choosing a paper to review, the agent considers:
1. All papers with status = "triaged" (including from previous sessions)
2. Papers from the current batch not yet in the log
3. Selects the highest `overall_interest` score among unreviewed papers
4. A previously-triaged paper with a high score beats a mediocre new paper

### Programmatic access

The log is a CX2 network. To check for duplicates or query scores without
using LLM tokens:

```python
# Download log, check if DOI already exists
log_cx2 = wrapper.download_network(log_network_id)
# Parse nodes, filter by doi attribute
# This is pure Python dict traversal — no LLM needed
```

This keeps duplicate detection and log queries efficient (code, not tokens).

---

## Session Directory Structure

Per CLAUDE.md workflow requirements:

```
$AGENT_OUTPUT_DIR/literature_review/YYYYMMDD_HHMMSS/
├── workflow_metadata.json     # Inputs, parameters, timestamps
├── log.json                   # Step-by-step execution log
├── candidates.json            # Step 1 output: all discovered papers
├── triage.json                # Step 2 output: ranked papers + rationale
├── selected_paper.json        # Step 2 output: chosen paper metadata
├── paper_text.md              # Step 3 output: extracted text
├── review.md                  # Step 4a output: review document
├── bel_statements.json        # Step 4b output: extracted BEL
├── network_spec.json          # Step 5 output: CX2 spec
└── post_result.json           # Step 6 output: NDEx UUID + URL
```

---

## Human Communication Interface (Phase 1)

Per the user's requirement for a human-facing interface to agent-posted
content on NDEx:

### Reading agent content

1. **Keyword search**: `search_networks("ndexagent review TP53")` finds
   reviews mentioning TP53
2. **Author browse**: `get_user_networks("rdaneel")` lists all networks
   posted by the agent's account
3. **Prebuilt "feed" queries**: Search for `ndexagent` with date filters
   to see recent agent activity

### Viewing a review network

When a human opens a review network in the NDEx web UI:
- **Description tab**: Shows the full review text (summary, findings,
  significance, critique)
- **Network view**: Shows the BEL knowledge graph as an interactive
  node-edge diagram
- Nodes colored/shaped by type (protein, process, disease, etc.)
- Edges labeled with BEL relations

### Authoring and replies

Phase 1 supports one-way posting (agent → NDEx). Human interaction is
read-only via the NDEx web UI. Phase 2 will add:
- Human posting requests as networks (per agent_communication_design.md)
- Agent reading and responding to human-posted requests
- Reply threading via `ndex-reply-to` property

---

## File Structure

```
workflows/literature_review_agent/
├── plan.md                    # This document
├── literature_review.md       # The workflow prompt (agent instructions)
├── bel_to_cx2.py              # BEL statement list → CX2 network spec
├── biorxiv_client.py          # bioRxiv API client
└── review_log.py              # Review log CX2 network read/write utilities
```

---

## Implementation Phases

### Phase 1: Core Pipeline (current)

Implement the 6-step workflow end to end:
1. `biorxiv_client.py` — bioRxiv date-range search with category filter
2. `review_log.py` — review log CX2 network CRUD (create, read, update,
   DOI lookup, score-based selection)
3. `bel_to_cx2.py` — BEL statement list to CX2 network spec conversion
4. `literature_review.md` — workflow prompt with all 6 steps
5. Test with a real topic, verify the full pipeline from bioRxiv search
   through triage/logging to NDEx posting

### Phase 2: Search Infrastructure

- Audit `tools/robust_literature_search.py` for current compatibility
- Integrate Semantic Scholar for citation-aware ranking during triage
- Add bioRxiv full-text JATS XML parsing as alternative to PDF
- Formal entity grounding for BEL terms (HGNC, GO, ChEBI lookups)

### Phase 3: Human Interface & Agent Communication

- Build lightweight web viewer for agent-posted review networks
  (or extend NDEx viewer with review-specific display)
- Human request posting: user creates a network with topic + parameters,
  agent picks it up from inbox
- Reply threading: agent posts follow-up analyses in response to human
  feedback
- Multi-agent journal club: multiple agents review the same paper,
  post competing analyses

---

## Dependencies

| Component | Status | Notes |
|-----------|--------|-------|
| NDEx MCP tools | Ready | 15 tools, tested, bugs fixed |
| bioRxiv API | Available | REST API, no auth needed |
| BEL prompt | Available | `workflows/BEL/bel_prompt.md` — reference for extraction |
| PDF reading | Available | Claude Code Read tool handles PDFs |
| robust_literature_search.py | Needs review | Imports corpus_analyzer, citation_extractor — verify these still work |
| Semantic Scholar API | Available | Used by robust_literature_search; optional for Phase 1 |

---

## Resolved Design Questions

1. **Network size limits**: NDEx handles hundreds of thousands of edges.
   Cap at 500 BEL statements per paper for Phase 1 — practical ceiling
   for single-paper content.

2. **BEL validation**: Best-effort for Phase 1. No formal validation
   dependency. The goal is a working POC for collaborator demonstration.

3. **Duplicate detection**: Resolved — the review log network on NDEx
   tracks all triaged and reviewed papers by DOI. Duplicate check is
   a programmatic CX2 node lookup (no LLM tokens). Previously-triaged
   papers with high scores remain candidates across sessions.

4. **Review quality threshold**: Post regardless. A text-only review
   with few or no BEL statements is still valuable as a triage output.
   The review text in the network description carries value independently
   of the graph.

## Resolved: Log Scope and Growth

**One log per topic** — simpler for Phase 1, avoids unbounded growth,
and keeps each log focused and manageable.

**Log growth** is not a Phase 1 concern. For later phases, two mitigations
are planned:
- **Local graph database caching**: avoid repeated large downloads by
  maintaining a local cache with filtering/query capabilities.
- **NDEx server-side network queries**: the NDEx API supports some
  network query operations that could filter the log server-side,
  reducing download size.

---

## Local Network Cache — Design (Future)

### Motivation

The agent downloads networks from NDEx for querying and analysis. Without
caching, every session re-downloads the same data. As the agent works with
more networks (review logs, merged knowledge graphs, interaction data,
agent state), this becomes wasteful and slow. A local cache also enables
graph queries without loading entire networks into LLM context.

### Use Cases

The cache must support four distinct categories of cached data:

1. **Science knowledge graphs** — causal molecular networks (BEL graphs)
   merged from multiple papers. Need neighborhood queries ("what regulates
   TP53?"), path queries ("how does X connect to Y?"), and cross-network
   merge operations. Can grow to thousands of edges across reviews.

2. **Interaction datasets** — PPI networks, co-expression data. Dense,
   less annotated. Queries are topological (degree, shared interactors,
   clustering). Similar storage needs to (1).

3. **Tabular data embedded in networks** — NDEx can store tabular data as
   networks but the graph model adds nothing. These need column filtering,
   aggregation, sorting — SQL/dataframe operations, not graph traversal.

4. **Agent state** — plans, status tracking, episodic memory, operational
   knowledge (collaborators, topics, meta-knowledge of available networks).
   Mostly key-value and document retrieval. Graph structure matters only
   for relational queries across pieces of knowledge.

### Architecture: Two-Tier Design

**Tier 1: SQLite metadata catalog.** Every cached network gets a row
tracking UUID, name, type classification (graph/tabular/state), size,
download timestamp, NDEx modification timestamp, local file path, and
`ndex-*` properties. The agent queries this catalog first to decide which
networks to load. Fast, zero-dependency, trivially queryable.

**Tier 2: Backend per data type.**
- *Graph data* (use cases 1, 2): CX2 JSON files on disk, loaded into
  NetworkX on demand for graph queries. NetworkX handles subgraph
  extraction, neighbor queries, and path finding for networks under ~50K
  edges.
- *Tabular data* (use case 3): SQLite tables with JSON columns, queryable
  without loading into LLM context.
- *Agent state* (use case 4): SQLite tables for structured state; JSON
  documents for unstructured knowledge.

### Subagent Filtering Pattern

The catalog (Tier 1) enables a key optimization: the main agent never
loads raw graph data into its own context. Instead:
1. Main agent queries the catalog to identify relevant cached networks
2. Spawns a cheaper/faster subagent (Haiku or Sonnet) with the network
   loaded
3. Subagent runs a specific query and returns a filtered subset
4. Main agent receives only the relevant results

### Staleness and Consistency

NDEx is the ground truth. Design questions for implementation:
- TTL-based expiry vs. checking NDEx modification timestamp on access
- Whether to re-download on every session start or lazily on first query
- How to handle NDEx updates to networks the agent has cached

### Migration Path

Start with NetworkX-on-demand for graph queries. If cross-network queries
or persistence overhead becomes painful, swap Tier 2 graph backend for
KùzuDB (embedded graph DB, Cypher queries, Python-native, no server
process). The cache file format (CX2 JSON on disk) and catalog layer
remain unchanged regardless of backend.

### Cache Location

TBD — options are `$AGENT_OUTPUT_DIR/cache/` (project-scoped) or
`~/.ndex/cache/` (shared across projects). The former is simpler; the
latter enables reuse across different agent repos.
