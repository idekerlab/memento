# Memento: A Framework for Indefinite-Horizon AI Scientist Agents

## Companion paper to: NDExBio: An Open Platform for AI Agent Scientific Communities

---

## Working Title

"Memento: Persistent Self-Knowledge Graphs and Epistemic Discipline for Indefinite-Horizon AI Scientist Agents"


---

## Abstract

LLM-based agents are increasingly deployed for scientific tasks, but most operate in bounded pipelines — a fixed workflow executed once, with no memory of prior sessions and no capacity for autonomous operation over weeks or months. We present Memento, a framework for building AI agents that operate over indefinite horizons as autonomous researchers and expert consultants. Memento addresses two entangled problems: the architectural problem of maintaining rich self-knowledge across sessions without flooding the context window, and the cognitive problem of equipping agents with the epistemic discipline — evidence evaluation, intellectual independence, provenance tracking — that makes their outputs trustworthy.

The core mechanism is graph-based persistent memory: agents maintain self-knowledge as CX2 property-graph networks persisted in an NDEx database and cached locally in an embedded graph database for efficient access. This two-tier architecture allows agents to accumulate extensive knowledge graphs — session histories, dependency-based plans, collaborator models, literature records, domain models, review logs — while loading only what they need into context via targeted queries.

We describe the framework design, its mandatory protocols for evidence evaluation and knowledge representation, and its deployment in an experimental scientific community on NDExBio. <N> agents with diverse missions — literature discovery, critique, knowledge synthesis, expert curation, hypothesis generation — operated over <period>, producing <metrics>. The NDExBio platform is described in the companion paper [NDExBio paper]; this paper focuses on how they are built and what makes them effective.

---

## 1. Introduction

### 1.1 The problem: AI scientists that forget

Current LLM-based scientific agents operate in bounded contexts  <citations>. They execute a workflow — summarize papers, generate hypotheses, write code — and then stop. Each invocation starts fresh. This is adequate for pipeline tasks but fundamentally inadequate for the kind of sustained, cumulative work that characterizes real research.

A human scientist carries years of context: what they've read, what they found convincing, what they're skeptical of, who they've collaborated with, what they planned to do next. This accumulated context is not incidental — it is the basis for judgment. A scientist who forgot everything between meetings would be capable of processing but not of research.

The problem is not merely technical (how to persist state across sessions) but cognitive (what kind of self-knowledge does an agent need, and how should it use that knowledge to make research decisions?). These are entangled: the architecture constrains what cognitive patterns are possible, and the cognitive requirements drive architectural choices.

> **Rhetorical note**: This section should motivate both the engineering and the epistemology. The reader should understand that "memory for agents" is not just a database problem — it requires a theory of what agents need to remember and why.

### 1.2 The approach: persistent self-knowledge as graphs

Memento's answer is to externalize agent self-knowledge as graph structures — specifically, CX2 property-graph networks stored in an NDEx database. This is not a vector store or a flat log. It is structured, queryable, and semantically rich: agents maintain knowledge graphs of their session history, plans, collaborator models, literature records, and domain knowledge. These graphs are cached locally in an embedded graph database for efficient querying without flooding the context window.

The graph-based approach has several properties that matter for scientific agents specifically:

- **Provenance is native.** Every edge in a knowledge graph can carry evidence metadata — source, evidence tier, scope, validation date. This is not an add-on; it is the representation itself.
- **Cross-network querying enables synthesis.** An agent can query across its own session history, another agent's published analysis, and a curated knowledge graph simultaneously, finding connections that would be invisible in any single document.
- **The agent controls its own memory.** Unlike RAG systems where retrieval is implicit, memento agents explicitly query their knowledge, decide what to load, and choose how to update it. The agent is the active curator of its own knowledge base.

### 1.3 The cognitive model: epistemic discipline

Architecture alone does not make a trustworthy agent. Memento pairs its persistence layer with a cognitive model — a set of mandatory protocols that govern how agents evaluate evidence, represent knowledge, maintain intellectual independence, and track provenance.

These are not optional best practices. They are enforced by the agent's instruction set (its CLAUDE.md) and reinforced by the structure of the knowledge representation:

- **Evidence evaluation protocol**: Every claim incorporated from another source must be assessed for evidence tier, experimental context, and alternative interpretations. Evidence tiers are never silently upgraded.
- **Intellectual independence**: Agents have the right and responsibility to disagree with other agents. Productive disagreement is a success signal, not a failure mode.
- **Formal/freeform duality**: Knowledge is represented in formal vocabularies (BEL) where they fit cleanly, and as freeform claim nodes where formalization would distort the meaning. Both modes are first-class graph content.
- **Edge provenance schema**: Every mechanism edge carries standardized metadata — evidence quote, source identifier, scope, evidence tier, validation date — that other agents can query.

> **Key argument**: The architecture (persistent graphs, efficient querying) enables the cognitive model (evidence evaluation, provenance tracking), and the cognitive model gives the architecture its purpose. Neither is sufficient alone. This integration is Memento's core contribution.

### 1.4 Relationship to NDExBio

Memento is agents. NDExBio is the platform. The companion paper [NDExBio ref] describes the open platform — NDEx as communication substrate, CX2 as exchange format, participation conventions, community dynamics. This paper describes how to build agents that operate effectively on that platform (or any platform that supports persistent structured artifacts).

Critically, memento agents use the *same* NDEx database for both their self-knowledge persistence and their community communication. An agent's session history and plans live alongside its published analyses and critiques. This is a deliberate design choice: it means the agent's operational memory is inspectable by the community, and the community's publications are queryable alongside the agent's own knowledge.

> **Note**: The papers share experimental data — the same agents, the same observation period. NDExBio reports community-level dynamics (interaction graphs, schema diversity, discourse threads). This paper reports agent-level capabilities (how self-knowledge grows, how evidence evaluation works in practice, how plans evolve).

### 1.5 Scope

This paper introduces the Memento framework and reports observations from its deployment in an NDExBio experimental community. We describe:
- The two-tier persistence architecture (NDEx + local graph DB)
- The session lifecycle and self-knowledge schemas
- The evidence evaluation and knowledge representation protocols
- Observations from <N> agents operating over <period>

We do not claim that agent-produced science is high quality — quality evaluation requires human expert validation (deferred to future work). We demonstrate that the framework enables agents to accumulate knowledge, maintain epistemic discipline, and operate autonomously over extended periods.

---

## 2. Background and Related Work

### 2.1 Memory and persistence in LLM agents

- MemGPT / Letta (Packer et al., 2023) — virtual context management, paging memory in/out. Closest architectural relative, but focused on conversation continuity rather than structured scientific knowledge.
- Generative Agents (Park et al., 2023) — memory stream + reflection + planning. Pioneered the idea of agents with persistent memory, but for social simulation, not scientific work. Memory is narrative text, not structured knowledge.
- Voyager (Wang et al., 2023) — skill library as persistent memory for Minecraft agents. Relevant as "agents that learn and accumulate capabilities over time" but in a very different domain.
- RAG-based approaches — retrieve-then-generate pipelines. Memento differs in that the agent *actively curates* its knowledge rather than passively retrieving from a corpus.

> **Key distinction to draw**: Most memory systems treat persistence as a technical problem (how to store and retrieve). Memento treats it as an epistemic problem (what to remember, how to evaluate it, how to structure it for reasoning).

### 2.2 Scientific AI agents

- AI Scientist v2 (Lu et al., 2025) — fully automated paper generation. Impressive pipeline, but single-shot: no memory across runs, no community interaction.
- SciAgents — multi-agent scientific workflows. Internal team structure, not open community.
- ChemCrow, Coscientist — tool-augmented agents for chemistry. Domain-specific pipelines, not indefinite-horizon frameworks.
- The trend: agents are getting better at *doing science once*. The gap is agents that *become better scientists over time*.

### 2.3 Knowledge graphs in agent systems

- Knowledge graphs as memory for agents (survey needed)
- BEL (Biological Expression Language) — compositional vocabulary for mechanism representation
- CX2 — property graph format, no semantic constraints, used by NDEx
- The formal/freeform duality argument (see notes_formal_freeform_duality.md) — why mixed representation is a feature

### 2.4 NDEx and the NDExBio platform

- Brief description of NDEx as infrastructure (defer details to companion paper)
- CX2 format — standardized envelope, unconstrained interior
- NDExBio conventions — minimal participation requirements
- Cross-reference to companion paper for full platform description

---

## 3. Framework Design

### 3.1 Two-tier persistence architecture

**Ground truth tier: NDEx**
- All agent state persisted as CX2 networks in NDEx
- No agent state on disk (beyond cache)
- NDEx provides: stable UUIDs, access control, search, publication with DOIs
- Same database used for self-knowledge AND community communication

**Cache tier: Local graph database (LadybugDB)**
- SQLite catalog for metadata queries (which networks are cached, modification times)
- LadybugDB embedded graph DB for Cypher queries across all cached networks
- Cache is ephemeral — cleared and rebuilt from NDEx at session start
- Enables cross-network queries without downloading everything into context

**Why two tiers?**
- Context window is finite and expensive. A mature agent may have thousands of nodes across its self-knowledge graphs.
- Loading entire graphs into context is wasteful — most sessions need only a fraction.
- Cypher queries let the agent ask targeted questions ("what did I conclude about TRIM25 last week?") and get precise answers.
- NDEx provides durability and discoverability; the local cache provides query speed.

> **Figure 3.1**: Architecture diagram — NDEx as ground truth, local cache as query layer, agent context window as working memory. Show the flow: NDEx → cache at session start, cache → NDEx at session end, targeted Cypher queries during session.

### 3.2 Self-knowledge networks

Every memento agent maintains a set of standard self-knowledge networks. These are the agent's persistent memory — they survive across sessions, are visible to the community, and accumulate over time.

**Mandatory (all agents):**

| Network | Purpose | Key schema elements |
|---|---|---|
| Session history | Chain of sessions: what was done, outcomes, lessons, pointers to produced networks | Linked session nodes with timestamps, actions, outcomes, lessons_learned |
| Plans | Hierarchical tree: mission → goals → actions, each with status and priority | Tree structure with status (active/planned/done/blocked), priority levels |
| Collaborator map | Model of other agents and humans: roles, expertise, interaction patterns | Agent/human nodes with role, expertise, last_interaction |
| Papers read | Literature record: DOIs, triage tiers, key claims, links to analysis networks | Paper nodes with triage_tier, key_claims, analysis_network_uuid |

**Role-specific (additional):**

| Network | Agent type | Purpose |
|---|---|---|
| Review log | Curator agents (e.g., rzenith) | Auditable trail of all curation decisions |
| Domain model / working model | Researcher agents (e.g., rgiskard) | Persistent scratch space for patterns, hypotheses, expectations |
| Curated knowledge graph | Curator agents | The maintained resource itself |
| Synthesis network | Synthesis agents (e.g., drh) | Integrated knowledge across multiple sources |

> **Key point**: Self-knowledge networks are not logs. They are structured graphs that the agent queries, updates, and reasons over. The session history is not "what happened" — it is "what I learned and what I should do next."

### 3.3 Session lifecycle

The session lifecycle is mandatory for all agents and enforces the connection between persistent memory and current reasoning.

**Phase 1 — Initialization (procedural)**
`session_init()` handles mechanical startup: verify connectivity, clear stale cache, download and cache self-knowledge networks, extract active plans and last session. Hard stop if this fails — the agent cannot operate without its memory.

**Phase 2 — Orientation (reasoning)**
Agent reviews its state: What did I do last time? What are my active plans? What's new in the community (social feed check)? Pick 1-2 focus actions.

**Phase 3 — Work (reasoning)**
Execute focus actions. Key disciplines during work:
- Check before duplicating: query the graph before starting analysis that may already exist
- Publish immediately: don't batch outputs, publish each network as completed
- Thread responses: use `ndex-reply-to` to link responses to source networks
- Update self-knowledge incrementally

**Phase 4 — Close (mandatory)**
Add session node to history. Update plans (mark done, add new). Update papers-read, collaborator-map. Publish ALL updated self-knowledge to NDEx. Verify all steps completed.

> **Figure 3.2**: Session lifecycle diagram. Emphasize that phases 1 and 4 are procedural/mandatory, phases 2 and 3 are where agent judgment operates.

### 3.4 MCP tooling layer

Memento agents interact with NDEx and the local store through MCP (Model Context Protocol) servers. This is an implementation detail but an important one: it means the tools are standardized and available to any MCP-compatible agent framework.

| Server | Purpose |
|---|---|
| ndex_mcp | 16 tools: network CRUD, search, sharing, access control |
| local_store | 13 tools: catalog queries, Cypher graph queries, caching, contradiction detection, staleness checks |
| biorxiv | 4 tools: preprint discovery and retrieval |
| pubmed | 4 tools: published literature search and full-text retrieval |
| reference_validation | Citation validation via Crossref + PubMed |

Identity is controlled per-call via profile parameters — multiple agents can share the same tool infrastructure.

### 3.5 Agent definition: CLAUDE.md as behavioral specification

A memento agent is defined by a single markdown file (CLAUDE.md) that specifies its role, mission, and behavioral instructions. No code, no configuration files, no programmatic rules. The agent's behavior emerges from the interaction of these instructions with the LLM's reasoning capabilities.

This is a deliberate design choice:
- **Declarative, not procedural**: Instructions say what the agent should do and why, not how to do it step by step.
- **Shared + specific**: All agents follow SHARED.md protocols (session lifecycle, evidence evaluation). Each agent's CLAUDE.md adds only role-specific behavior.
- **Evolvable**: Updating an agent's behavior means editing a text file, not rewriting code.

> **Discussion point**: This is both a strength and a limitation. The agent's behavior is interpretable and modifiable, but it depends on the LLM's ability to follow complex instructions reliably. We discuss compliance and drift in Section 5.

---

## 4. Epistemic Discipline

> **Framing note**: This section is the cognitive model companion to Section 3's architecture. Together they form Memento's core contribution. This section should feel like "the theory of mind you give an agent."

### 4.1 Evidence evaluation protocol

When an agent encounters a claim — from a paper, from another agent's analysis, from its own prior session — it must evaluate before integrating.

**Five-step evaluation:**
1. Verify against primary sources where possible
2. Assess evidence tier (established → supported → inferred → tentative → contested)
3. Consider alternative interpretations
4. Note experimental context (species, system, cell type, assay)
5. Trace interaction data to underlying assays — never trust edges uncritically

**Evidence tiers are persistent metadata, not transient judgments.** They are written into the graph as edge attributes and carried forward across sessions and agents. An edge that enters the system as "tentative" stays "tentative" until a review session explicitly upgrades it with documented justification.

### 4.2 Intellectual independence

Agents have the right and responsibility to disagree. This is not a platitude — it is an operational requirement with specific expectations:

- Reject inputs that seem overstated or unjustified
- Push back on critiques that miss the point
- Flag unjustified leaps in syntheses
- Treat persistent absence of disagreement as a warning sign

> **Why this matters**: In multi-agent systems, the default failure mode is convergence — agents politely agreeing with each other until the group settles on a shared interpretation that may be wrong. Intellectual independence is the countermeasure.

### 4.3 Knowledge representation: formal/freeform duality

Memento agents represent knowledge in two complementary modes:

**Formal mode (BEL):** Mechanism edges authored in Biological Expression Language. Machine-tractable, dedupable, cross-queryable, exportable to standard views (GO-CAM).

**Freeform mode (claim nodes):** Natural-language claims with full provenance annotations. Used when a formal vocabulary would distort the meaning — stoichiometric qualifications, domain-level separation-of-function, methodological caveats, cross-paper patterns, open puzzles.

Both modes are first-class graph content. Both carry the same provenance metadata. The choice between them is made per-claim, not per-network.

> **Key argument (from notes_formal_freeform_duality.md)**: This reframes the role of formal ontologies — from "pre-agreed schemas required before publication" to "one of several expressive modes the agent chooses per claim." It sidesteps the harmonization bottleneck that has historically slowed multi-group knowledge-graph construction, because freeform claim nodes don't need to be harmonized to be useful — they just need to be readable, which for agent consumers they already are.

### 4.4 Edge provenance schema

Every mechanism edge carries standardized metadata:

| Field | Purpose |
|---|---|
| evidence_quote | Brief verbatim quote from source |
| pmid / doi | Source identifier |
| scope | Study context (species, system, assay) |
| evidence_tier | established / supported / inferred / tentative / contested |
| last_validated | Date of most recent validation |
| evidence_status | current / superseded / retracted / contested |
| supporting_analysis_uuid | Link to agent-authored analysis network |

**Retirement discipline**: Edges are never deleted. Outdated edges are marked `superseded` or `retracted` with explanatory annotations. This preserves referential integrity — other networks may point at retired edges.

---

## 5. Agent Implementations

> **TBD: Which agents to feature as primary examples. Options below; final selection depends on which best illustrate the framework's capabilities and the diversity of agent roles.**

### 5.1 Overview of the experimental community

<N> agents deployed on a local NDEx server, operating as scheduled tasks over <period>. All agents use the Memento framework (SHARED.md + agent-specific CLAUDE.md). They are also members of an NDExBio community described in the companion paper.

Brief table of all agents with: name, role, mission, key self-knowledge networks, distinguishing capability.

### 5.2 Agent profiles (TBD — select 2-3 for detailed treatment)

**Candidate A: The literature discovery pipeline (rdaneel)**
- Three-tier triage: scan → review → deep analysis
- Papers-read graph as cumulative literature memory
- Researcher network tracking the human field
- Disconfirmation mandate: 1 in 5 deep reads chosen to challenge the model

**Candidate B: The expert curator (rzenith)**
- Curated knowledge graph as primary deliverable
- Review protocol: 3-5 edges per session with decision tree
- BEL migration: every touched edge must be in BEL
- Versioned KG with delta tracking
- Review log as auditable trail

**Candidate C: The hypothesis-generating researcher (rgiskard)**
- Working model as persistent scratch space (lower provenance bar than curated KGs)
- Pattern detection across accumulated analyses
- Hypothesis graduation: from working model to publishable output
- Subagent invocation for deep paper analysis

**Candidate D: The constructive critic (janetexample)**
- Social feed-driven: activates when new content appears
- Structured critique with verdicts (approved / conditional / rejected)
- Hypothesis development from identified gaps
- Report authority: decides when findings are ready for human researchers

**Candidate E: The knowledge synthesizer (drh)**
- Integrates across multiple agents' outputs
- Confidence scale for synthesis claims (strong / moderate / preliminary / speculative)
- Researcher network construction (mapping the human field)

### 5.3 Operational patterns observed

[To be populated with data from the observation period]

- Self-knowledge growth over time (nodes/edges in session history, plans, papers-read)
- Plan evolution: how goals and actions change across sessions
- Evidence evaluation in practice: examples of tier assignment, alternative consideration
- Intellectual independence events: documented disagreements between agents

---

## 6. Results

> **Note**: This section reports agent-level results. Community-level results (interaction graphs, discourse threads, schema diversity) are reported in the companion NDExBio paper.

### 6.1 Self-knowledge accumulation

**Metrics:**
- Growth curves for each self-knowledge network (nodes, edges) over observation period
- Session count per agent
- Plan evolution: actions created, completed, blocked, new goals added

**Expected narrative:** Agents accumulate increasingly rich self-knowledge over time. Session histories grow linearly. Plans evolve — initial goals are completed or revised, new goals emerge from discoveries. Papers-read graphs grow as the agent's coverage of the literature expands.

> **Figure 6.1**: Growth curves for self-knowledge networks, by agent. Show that this is cumulative, not reset.

### 6.2 Evidence evaluation in practice

**Metrics:**
- Distribution of evidence tiers across all agent-authored edges
- Examples of tier assignment with justification
- Cases where agents noted alternative interpretations
- Cases where experimental context was flagged as limiting

**Expected narrative:** Agents are exercising judgment, not just labeling. The tier distribution should not be uniform — most edges should be "supported" or "inferred," with fewer "established" and "tentative." Examples should show that agents are reading sources carefully, not just copying abstracts.

> **Figure 6.2**: Evidence tier distribution across agents. Possibly a stacked bar chart per agent.

### 6.3 Knowledge representation patterns

**Metrics:**
- BEL vs. freeform claim node ratio across agents
- Examples of claims that were appropriately formalized vs. appropriately left freeform
- Schema diversity within and across agents

**Expected narrative:** The formal/freeform duality is being exercised — agents are making per-claim decisions about representation mode. The ratio should vary by agent role (curators may be more formal; hypothesis generators may use more freeform).

### 6.4 Operational reliability

**Metrics:**
- Session completion rate (did the agent complete all mandatory lifecycle steps?)
- Self-knowledge integrity: are networks consistently updated and published?
- Tool failure rates and recovery patterns

**Expected narrative:** The framework is reliable enough for sustained operation. Session lifecycle compliance should be high. Failure modes should be documented honestly.

### 6.5 [Potential] Plan-driven behavior

**Metrics:**
- Correlation between plan priorities and session focus
- Examples of plan evolution over time
- Cases where agents adjusted plans based on new information

---

## 7. Discussion

### 7.1 Architecture enables epistemology

[Core argument of the paper: you can't have evidence evaluation without persistent memory, and persistent memory without epistemic discipline produces unreliable agents. The integration is the point.]

### 7.2 What indefinite operation reveals

[Observations that only emerge over many sessions: knowledge accumulation, plan evolution, growing sophistication of evidence evaluation, drift and its correction.]

### 7.3 The CLAUDE.md approach: strengths and limits

[Declarative behavioral specification via natural language instructions. Strengths: interpretable, evolvable, no code to maintain. Limits: depends on LLM instruction-following, potential drift over long sessions, no formal verification of compliance.]

### 7.4 Limitations and honest accounting

- **Single LLM dependency**: Current agents all use Claude. Framework-agnosticism is a design principle but not yet demonstrated.
- **No quality ground truth**: We report that agents produce structured, provenanced knowledge — not that the knowledge is correct.
- **Small community**: <N> agents from a single research group. Diversity of deploying organizations is needed.
- **Scheduled task constraints**: Agents operate in discrete sessions, not continuous operation. Session boundaries create discontinuities.
- **BEL coverage**: Formal vocabulary covers molecular mechanisms well but not all scientific claims. The freeform fallback is necessary but its prevalence may indicate vocabulary gaps.

### 7.5 Relationship to companion paper

[How the two papers complement each other. NDExBio provides the platform; Memento provides the agents. The same experimental community is reported from two perspectives. Readers interested in community dynamics should read NDExBio; readers interested in agent capabilities should read this paper.]

### 7.6 Future directions

- Quality evaluation with expert ground truth
- Multi-model deployment (agents using different LLMs)
- Cross-organization deployment
- Automated compliance monitoring (did the agent follow its protocols?)
- Benchmarks for indefinite-horizon agent capability

---

## 8. Conclusion

Memento demonstrates that LLM-based agents can operate as autonomous researchers over indefinite horizons when equipped with persistent, structured self-knowledge and explicit epistemic discipline. The framework's core contribution is the integration of architecture (graph-based persistent memory with efficient local querying) and cognitive model (evidence evaluation, intellectual independence, formal/freeform knowledge representation, provenance tracking).

The agents described here are not finished products — they are early demonstrations of a capability model. The important result is not what they produced, but that the framework enables a kind of agent behavior that bounded pipelines cannot: cumulative learning, plan-driven autonomy, and epistemically disciplined reasoning that improves with sustained operation.

Memento is open source. We invite the agent-building community to use it, extend it, and deploy agents that are not just capable but trustworthy.

---

## Methods

### Agent implementation
- All agents implemented as CLAUDE.md behavioral specifications
- Underlying model: Claude (version) via Claude API / Claude Code
- Scheduled operation via [cowork scheduled tasks / cron]
- MCP servers for tool access

### Data collection
- NDEx API for network metadata and content
- Local store catalog for session-level data
- CX2 parsing for schema and provenance analysis

### Metric definitions
[Precise definitions once analysis approach is finalized]

---

## Open Items

**Before drafting:**
- [ ] Decide which agents to feature as primary examples (Section 5.2)
- [ ] Define observation period dates
- [ ] Determine whether to include the "expert agent" framing from NDExBio intro here too, or leave it to the companion paper

**Data collection needed:**
- [ ] Self-knowledge network growth data per agent
- [ ] Evidence tier distribution across all agent-authored edges
- [ ] BEL vs. freeform claim node ratios
- [ ] Session lifecycle compliance rates
- [ ] Plan evolution data (goals created, completed, revised)

**Writing:**
- [ ] Related work section needs thorough literature search (MemGPT, Generative Agents, Voyager, AI Scientist, etc.)
- [ ] Methods section needs precise definitions once data is available
- [ ] Abstract needs concrete numbers

**Coordination with NDExBio paper:**
- [ ] Agree on shared experimental description (same agents, same period)
- [ ] Cross-reference consistently (this paper = agent capabilities, that paper = community dynamics)
- [ ] Ensure no contradictions in how agents are described
- [ ] Coordinate submission timing

---

## Figures Summary (Planned)

| # | Description | Status |
|---|---|---|
| 1 | Two-tier architecture diagram (NDEx → local cache → context) | To create |
| 2 | Session lifecycle (init → orient → work → close) | To create |
| 3 | Self-knowledge network schemas (visual) | To create |
| 4 | Self-knowledge growth curves over time | Generate from data |
| 5 | Evidence tier distribution across agents | Generate from data |
| 6 | BEL vs. freeform representation ratios | Generate from data |
| 7 | Plan evolution example (one agent over multiple sessions) | Generate from data |
| 8 | Example knowledge graph fragment with provenance | Extract from agent output |

---

## Candidate Venues

- **arXiv cs.AI** — primary target, establish priority, companion to NDExBio preprint
- **arXiv cs.MA** — multi-agent systems audience
- **arXiv q-bio.QM** — quantitative methods in biology
- Cross-post to multiple arXiv categories as appropriate

> **Strategic note**: Simultaneous arXiv posting with the NDExBio companion paper. Each paper references the other. The combination — platform + agent framework — is stronger than either alone.
