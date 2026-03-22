# bioRxiv Paper Triage Workflow

Three-tier pipeline for discovering, filtering, and analyzing bioRxiv preprints relevant to host-pathogen molecular interactions (HPMI), starting with influenza virus.

## Triage Levels

### Tier 1: Discovery Scan (Fast, High Volume)

**Goal**: Cast a wide net over recent bioRxiv papers and identify potentially interesting ones from abstracts alone.

**Model**: Fast/cheap model (e.g., Haiku) — this is a high-throughput filtering step.

**Process**:
1. Use `search_recent_papers` with HPMI-relevant keywords
2. For each paper, score the abstract on relevance to the current interest group topics
3. Papers scoring above threshold get a brief one-line annotation
4. Output: daily summary of potentially interesting papers, posted as an NDEx network to the HPMI interest group

**Scoring criteria**:
- Molecular mechanism specificity (named proteins, pathways, interactions)
- Host-pathogen context (not just virus alone, not just host alone)
- Novelty signal (new mechanism, unexpected finding, contradiction of prior work)
- Experimental evidence (not purely computational/review)

**Output artifact**: `ndexagent biorxiv-daily-scan YYYY-MM-DD` — a network with one node per paper, annotated with title, DOI, relevance score, and one-line summary.

### Tier 2: Focused Read (Medium Depth)

**Goal**: Read full text of Tier 1 papers that scored highest; produce a brief review.

**Model**: Fast model with full-text context window.

**Process**:
1. Retrieve full text via `get_paper_fulltext`
2. Extract key findings: specific molecular interactions, host factors, viral proteins, mechanisms
3. Assess quality: experimental rigor, controls, statistical support
4. Generate a brief structured review (300-500 words)
5. Post review as an NDEx network artifact to the HPMI interest group

**Review structure**:
- Paper summary (2-3 sentences)
- Key molecular findings (named entities and interactions)
- Experimental approach and strength of evidence
- Relevance to HPMI research community
- Recommendation: skip / worth discussing / must read

**Output artifact**: `ndexagent biorxiv-review <short-title>` — a network encoding the paper's key molecular interactions with the review text as a network description.

### Tier 3: Deep Analysis (High Depth, Low Volume)

**Goal**: Comprehensive analysis of the most significant papers, with literature context, cross-referencing, and possibly data analysis.

**Model**: Most capable model (e.g., Opus) for nuanced scientific reasoning.

**Process**:
1. Full text analysis with careful attention to methods, results, and discussion
2. Literature search: find related work on NDEx and bioRxiv, identify how this paper extends or contradicts existing knowledge
3. Extract a detailed interaction network with provenance
4. Assess reproducibility, identify potential issues or gaps
5. Generate an in-depth review artifact (1000-2000 words)
6. Highlight the paper to collaborators with a notification post

**Analysis structure**:
- Executive summary
- Detailed molecular mechanism analysis
- Network of extracted interactions (nodes=proteins/genes, edges=interactions)
- Comparison with existing knowledge (cite NDEx networks, prior papers)
- Open questions and testable predictions
- Significance assessment for HPMI field

**Output artifacts**:
- `ndexagent biorxiv-analysis <short-title>` — detailed review network with full interaction graph
- `ndexagent biorxiv-highlight <short-title>` — notification post for the interest group

## Interest Group: HPMI (Host-Pathogen Molecular Interactions)

The HPMI interest group is the primary audience for triage outputs. It operates as an NDEx folder-based group where:

- Tier 1 daily scans are posted as routine updates
- Tier 2 reviews are posted for discussion
- Tier 3 analyses are highlighted with notification posts
- Human collaborators and other agents can comment/reply using the NDEx threading conventions

### Initial Focus: Influenza Virus

Keywords for Tier 1 scanning:
- Primary: influenza, flu virus, IAV, IBV, H1N1, H3N2, H5N1, H5N8, H7N9
- Host factors: interferon, innate immunity, ISG, restriction factor, host factor
- Mechanisms: viral replication, polymerase, neuraminidase, hemagglutinin, NS1, NEP, PB2, PA, NP, M1, M2
- Interactions: host-pathogen, viral evasion, immune escape, tropism, pathogenesis
- Broad: virology, respiratory virus, zoonotic

## Scheduling

- **Tier 1**: Daily (or every 2-3 days for less active periods)
- **Tier 2**: Triggered by Tier 1 results (top 3-5 papers per scan)
- **Tier 3**: Triggered by Tier 2 recommendation of "must read" (estimated 1-3 per week)

## Network Conventions

All output networks follow `project/architecture/conventions.md` plus these workflow-specific properties:

| Property | Value | Purpose |
|----------|-------|---------|
| `ndex-workflow` | `biorxiv-triage` | Links to this workflow |
| `ndex-triage-tier` | `1`, `2`, or `3` | Which triage level produced this |
| `ndex-interest-group` | `hpmi` | Target audience |
| `ndex-scan-date` | `YYYY-MM-DD` | Date of the scan/analysis |
| `ndex-paper-doi` | DOI string | Source paper (Tier 2 and 3) |
