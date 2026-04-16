---
name: bel-extraction
description: Extract or author biological mechanism claims in BEL (Biological Expression Language). Use when adding mechanism edges to a knowledge graph based on literature, when converting freeform claims into structured statements, or when authoring curated pathway content. Produces BEL statements with evidence annotations (quote, PMID/DOI, analysis-UUID) that align with NDExBio curation policy. BEL is the authoring representation; a GO-CAM view is produced downstream by a separate tool.
---

# BEL Authoring & Extraction

## When to use this

- You are reading a paper or passage and need to encode its mechanistic claims as edges in an NDEx network.
- You are adding a mechanism edge to an existing knowledge graph and need to author it correctly.
- You are reviewing an existing edge and need to re-express it in BEL to attach proper provenance.

## When NOT to use this

- The claim is narrative / epidemiological / non-mechanistic (e.g. "this drug is widely used in diabetes"). BEL wants causal or structural claims between entities.
- The statement is already in the target graph with equivalent content. Check before authoring.
- You don't have either a specific source quote (for literature-derived edges) or a clearly-identified entity pair (for curation edges). If provenance is missing, don't fabricate — flag for review.

## Core protocol

1. **Identify entities.** For each candidate claim, identify the participating entities. Ground each to a namespace ID from `reference/namespace-policy.md`. If you cannot ground with confidence, use a readable label in a `deferred_lookup` form and tag the edge for review — do not guess an ID.

2. **Pick a BEL function per entity.** Protein → `p()`, gene → `g()`, RNA → `r()`, small molecule → `a()`, complex → `complex()`, process → `bp()`, activity → `act()`, pathology → `path()`. See `reference/bel-grammar.md` for the full list.

3. **Pick a BEL relation.** Prefer `directlyIncreases` / `directlyDecreases` when there is direct molecular evidence (binding, phosphorylation, etc.); `increases` / `decreases` for indirect effects; `positiveCorrelation` / `negativeCorrelation` when causality is not established; `association` when the evidence is weakest. For complexes, use `hasComponent` / `hasComponents`. Full list in `reference/bel-grammar.md`.

4. **Attach evidence annotations** (required for every statement):
   - `quote`: brief verbatim quote from the source supporting the claim (<40 words)
   - `pmid` or `doi`: the source paper
   - `supporting_analysis_uuid`: UUID of any agent-authored analysis network that already analyzed this source, if one exists
   - `scope`: any qualifier the source imposes (cell type, model system, in vitro / in vivo, n, etc.)
   - `evidence_tier`: one of `established` (multi-source, widely-replicated), `supported` (single strong source), `tentative` (weak or single preliminary source), `contested` (conflicting evidence exists)
   - `last_validated`: ISO date of this annotation

5. **Do not duplicate.** Before writing a new BEL statement, check whether an equivalent one already exists in the target graph. Equivalence is by canonical term + relation, not by string match.

6. **Degrade gracefully when BEL can't say it cleanly.** If a claim cannot be expressed in BEL without severe loss, author a plain-language node with `node_type: "claim"` and attach the same evidence annotations. Do not force a bad BEL statement — an honest freeform node is better.

## Example: adding an edge during review

Edge rzenith wants to validate: "ATM activates STING" (currently has no provenance in the KG).

1. Entity grounding: `p(HGNC:ATM)`, `p(HGNC:STING1)` (or `bp(GO:"STING signaling pathway")` if the claim is process-level).
2. After literature check (see the curator's review protocol), decide the mechanism is really ATM-loss leading to cGAS-STING via mtDNA leakage — not a direct ATM-STING interaction. Split into two edges:
   - `p(HGNC:ATM) decreases bp(GO:"response to double-strand break")` — not quite right; better to introduce an intermediate node
   - Use: `act(p(HGNC:ATM)) directlyDecreases a(CHEBI:"mitochondrial DNA", loc(GO:cytosol))` (ATM activity suppresses cytosolic mtDNA)
   - `a(CHEBI:"mitochondrial DNA", loc(GO:cytosol)) directlyIncreases act(p(HGNC:CGAS))` (cytosolic mtDNA activates cGAS)
3. Evidence annotations on each new edge:
   ```
   quote: "ATM deficiency triggers release of mitochondrial DNA into the cytosol..."
   pmid: 33290271
   supporting_analysis_uuid: <rgiskard's analysis of Hu 2021, if it exists>
   scope: "observed in multiple cell lines; generalization to tumor tissue inferential"
   evidence_tier: supported
   last_validated: 2026-04-14
   ```
4. Log the split + provenance addition in the review-log network.

## Output format

When extracting BEL from text, produce JSON-shaped tuples:

```json
{
  "bel": "act(p(HGNC:ATM)) directlyDecreases a(CHEBI:\"mitochondrial DNA\", loc(GO:cytosol))",
  "evidence": {
    "quote": "ATM deficiency triggers release of mitochondrial DNA into the cytosol...",
    "pmid": "33290271",
    "supporting_analysis_uuid": null,
    "scope": "multiple cell lines; in vitro",
    "evidence_tier": "supported",
    "last_validated": "2026-04-14"
  }
}
```

When authoring directly into a network, the same fields become node/edge attributes.

## Reference material (pull as needed)

- `reference/bel-grammar.md` — all BEL functions and relations with examples
- `reference/namespace-policy.md` — entity classes, namespace table, fallback rules when an ID cannot be confidently resolved
- `reference/bel-examples.md` — curated extraction examples (input text → BEL + evidence)
- `reference/bel-to-gocam-mapping.md` — which BEL constructs map cleanly to GO-CAM, which are lossy, which are BEL-only

## Subagent for full-paper extraction

When a mechanism edge review requires reading a paper end-to-end, invoke the paper-processor subagent rather than reading the paper in your main context. It applies this skill over the full text in its own isolated context and returns structured BEL tuples + a paper summary as a single JSON object.

- Spec: `subagent/SUBAGENT.md` (input contract, output contract, verification protocol, failure modes)
- Output schema: `subagent/output_schema.json`
- Reference invocation: `subagent/examples/cho2024_PMID38200309.json`

The subagent is a context-isolation tool, not a new capability. Everything it does is this skill + the PubMed/Europe PMC tools; the value is that the caller's context stays focused on curation decisions while the subagent absorbs full-text reading.

## Common failure modes

- **ID hallucination.** If you aren't confident the HGNC / GO / ChEBI ID is correct, use the label and flag. False IDs pollute the graph and are hard to clean up later.
- **Over-extraction.** If a sentence doesn't assert a mechanistic claim between two grounded entities, skip it. Narrative / motivational / background sentences produce noisy edges.
- **Confusing correlation for causation.** Use `positiveCorrelation` / `negativeCorrelation` when the source reports association without mechanism.
- **Ignoring scope.** An edge labeled `increases` without a `scope` qualifier presents a cell-line result as if it were a general truth. Always capture scope.
- **Forcing BEL on non-BEL claims.** Not every claim belongs in BEL. Use freeform nodes when BEL distorts the meaning.
