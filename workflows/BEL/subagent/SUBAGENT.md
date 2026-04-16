# Paper-Processor Subagent

A context-isolated subagent that reads a single paper and returns structured BEL statements plus a paper summary. Main agents (rzenith, rgiskard, etc.) invoke it via the `Agent` tool to avoid flooding their own context with full-text reads.

Location-aware: this subagent applies the skill in `../SKILL.md`. If that skill changes, the subagent's behavior changes — the subagent is a thin driver over the skill, not a parallel implementation.

---

## When the caller should use this

Use when a review or analysis step requires reading a paper end-to-end and extracting structured mechanism claims. Typical triggers:

- An rzenith review session is validating an edge and needs to re-check the supporting paper
- An rgiskard analysis step wants BEL tuples from a candidate paper before deciding whether to synthesize
- Any agent encounters a paper not already covered by an existing analysis network

Do **not** use when:

- The paper is already covered by an existing analysis network (reference the UUID instead)
- The caller only needs the abstract — use `get_pubmed_abstract` directly
- The claim is non-mechanistic (epidemiological, narrative, methodological)

---

## Input contract

The caller passes a single JSON object as the subagent's task prompt:

```json
{
  "paper_id": "PMID:38200309",
  "focus_context": "focus on DDR-cGAS-STING mechanism claims",
  "caller_agent": "rzenith"
}
```

Fields:

| Field | Required | Format | Meaning |
|---|---|---|---|
| `paper_id` | yes | `PMID:<digits>`, `DOI:<string>`, or `PMC:<id>` | Paper identifier. PMID preferred when available. |
| `focus_context` | no | free text | Guides extraction — which mechanisms to prioritize. Without it, the subagent extracts all mechanistic claims in the paper. |
| `caller_agent` | no | agent name | Used for attribution in the output's `extracted_by` field. |

The subagent does NOT accept arbitrary free-text prompts beyond this JSON. The calling prompt wraps this JSON and instructs the subagent to follow the protocol below.

---

## Output contract (strict JSON)

```json
{
  "paper_id": "PMID:38200309",
  "extracted_by": "paper-processor-subagent",
  "extracted_on": "2026-04-14",
  "resolution": {
    "title_verified": "MRE11 liberates cGAS from nucleosome sequestration during tumorigenesis.",
    "journal": "Nature",
    "year": "2024",
    "pmid": "38200309",
    "doi": null,
    "pmcid": null,
    "fulltext_status": "abstract_only",
    "fulltext_source": null,
    "verification_warnings": [
      "get_pubmed_abstract returned PMCID PMC7515726 but the PMC title 'Comprehensive nucleosome interactome screen...' does not match the PubMed title; suspected PMID→PMC mapping error. Falling back to abstract-only."
    ]
  },
  "paper_summary": {
    "main_claims": [
      "MRE11-RAD50-NBN (MRN) binding to nucleosome fragments displaces cGAS from acidic-patch sequestration and enables cGAS activation by dsDNA.",
      "MRE11-dependent cGAS activation drives ZBP1-RIPK3-MLKL necroptosis, suppressing breast tumorigenesis."
    ],
    "methods": "Mammary tumorigenesis models (mouse); cell-based cGAS activation assays; biochemical reconstitution of MRN/nucleosome/cGAS; clinical association analysis in human TNBC.",
    "scope": "Mouse mammary tumor models + human breast-cancer association analysis; biochemistry in vitro",
    "limitations": [
      "ZBP1 downregulation association in human TNBC is correlative, not causal",
      "Mapping from mouse model to human tumor behavior is inferred"
    ]
  },
  "bel_statements": [
    {
      "bel": "complex(p(HGNC:MRE11), p(HGNC:RAD50), p(HGNC:NBN)) directlyDecreases complex(p(HGNC:CGAS), a(GO:\"nucleosome\"))",
      "evidence": {
        "evidence_quote": "binding of the MRE11-RAD50-NBN complex to nucleosome fragments is necessary to displace cGAS from acidic-patch-mediated sequestration",
        "pmid": "38200309",
        "doi": null,
        "supporting_analysis_uuid": null,
        "scope": "in vitro biochemistry; mammalian cells",
        "evidence_tier": "supported",
        "last_validated": "2026-04-14"
      },
      "confidence": "high",
      "notes": "`complex()` with an `a(GO:nucleosome)` member is awkward; consider an abstraction node if the representation is extended later."
    }
  ],
  "freeform_claims": [],
  "unresolved_entities": []
}
```

All arrays may be empty. `null` is allowed where indicated. The subagent MUST NOT invent IDs it is not confident about — use `PENDING:` plus `deferred_lookup` annotations and also list the entity under `unresolved_entities`.

**Strict field names** (validated against `output_schema.json`):

- `freeform_claims[]` uses `text` (NOT `claim`) for the claim body, and `reason_not_bel` is required (NOT `notes`).
- `unresolved_entities[]` uses `suggested_namespace` (NOT `attempted_namespace`) and an optional boolean `pending_lookup`; free-form prose belongs in notes OUTSIDE this array, not inline.
- `bel_statements[].notes` is optional and free-text; do not invent other nested keys inside a bel_statement.

The JSON schema is authoritative. If the schema and prose disagree, the schema wins.

### Freeform claims MUST carry the full evidence bundle (common drift point)

This is the single most drift-prone part of the output contract. Observed failure: the subagent emits `freeform_claims` entries with only `text` + `reason_not_bel`, omitting the `evidence` object. Every run to date has hit this; re-reading the schema prose is not sufficient. Before emitting the final JSON, the subagent must run the following mental check:

**For every entry in `freeform_claims`:** the `evidence` object is present and includes `evidence_quote` (verbatim from source, ≤400 chars), `pmid` OR `doi` (at least one — the others may be null), `scope`, `evidence_tier`, and `last_validated`. If any of these are missing, the freeform claim is not ready to emit — either fill in the missing field by re-reading the source, or drop the claim entirely. **A freeform claim without an `evidence` object is malformed output and will be rejected by downstream validation.**

Concretely, a freeform claim must look like this (copy this as a template when authoring):

```json
{
  "text": "MRN displacement of cGAS from the nucleosome acidic patch is quantitatively partial (~50%, consistent with one of two cGAS molecules being ejected per nucleosome).",
  "evidence": {
    "evidence_quote": "MRN titration plateaued at approximately 50% reduction, which indicated the displacement of one out of two bound cGAS molecules per nucleosome",
    "pmid": "38200309",
    "doi": "10.1038/s41586-023-06889-6",
    "supporting_analysis_uuid": null,
    "scope": "in vitro TR-FRET with purified human MRN, cGAS, and recombinant nucleosomal core particles",
    "evidence_tier": "supported",
    "last_validated": "2026-04-14"
  },
  "reason_not_bel": "Stoichiometric quantitative claim does not map cleanly onto a single BEL directlyDecreases edge."
}
```

Do NOT emit a freeform claim shaped like `{"text": "...", "reason_not_bel": "..."}` with no `evidence` object — that form is the recurring drift and is wrong.

### Self-validation before emitting the final JSON

As the last step before returning the output, perform this self-validation pass:

1. Every `bel_statements[]` entry has `bel`, `evidence`, and `confidence`. Its `evidence` has `evidence_quote`, `scope`, `evidence_tier`, `last_validated`.
2. Every `freeform_claims[]` entry has `text`, `evidence` (with the five required sub-fields above), and `reason_not_bel`. Count zero if not. **This is where drift happens — check this list explicitly.**
3. Every `unresolved_entities[]` entry has `label` and `suggested_namespace`.
4. `resolution.fulltext_status` is one of `fulltext`, `abstract_only`, `metadata_only`.
5. `resolution.verification_warnings` is an array (possibly empty) of strings.
6. `paper_summary.main_claims` has ≤ 5 entries.

If any check fails, fix the output before returning it. A final message that is not valid JSON, or is valid JSON that fails any of these checks, forces the caller to re-invoke — wasting the paper-read work already done.

### Field-by-field requirements

- **`resolution.fulltext_status`** ∈ `{"fulltext", "abstract_only", "metadata_only"}`. See "Full-text verification" below.
- **`resolution.verification_warnings`** — list every anomaly encountered: PMCID mismatch, DOI mismatch, truncated text, non-English section, etc. Empty array when clean.
- **`paper_summary.scope`** — always populated. If the paper is a review, say so here.
- **`bel_statements[].evidence.evidence_tier`** — default to `supported` for direct experimental claims in the paper; use `tentative` for claims the paper itself proposes as speculative; use `inferred` when the claim is the author's inference from their data.
- **`bel_statements[].evidence.last_validated`** — ISO-8601 date of this extraction. Not the paper's publication date.
- **`bel_statements[].confidence`** — the subagent's own confidence in the extraction (not the evidence tier). Use `low` when the extraction required heavy interpretation of the source text.

---

## Subagent protocol

The subagent executes this sequence in its own isolated context:

### 1. Parse `paper_id`

Split into `{prefix, identifier}`. Prefix must be one of `PMID`, `DOI`, `PMC`. Otherwise return a well-formed output with `fulltext_status: "metadata_only"` and an explanatory warning.

### 2. Resolve metadata

- If `PMID`: call `get_pubmed_abstract(pmid)`. Capture title, journal, authors, year, DOI, PMCID.
- If `DOI`: call `search_pubmed(doi)` to find the PMID, then as above.
- If `PMC`: call `get_pmc_fulltext(PMC_id)` directly; the returned text header contains title and metadata.

### 3. Full-text verification (handles PMID→PMC mismatch)

When a PMCID is available from step 2:

1. Call `get_pmc_fulltext(PMCID)`.
2. Extract the paper title from the first ~500 characters of the returned text.
3. Fuzzy-compare that title to the title from step 2.
4. **If they agree** (substring match or >50% token overlap on major words): proceed with `fulltext_status: "fulltext"`, record `fulltext_source: "europe_pmc_<PMCID>"`.
5. **If they disagree**: add a `verification_warnings` entry naming both titles and the suspected mismapping, then try this recovery chain in order, stopping at the first success:
   - `get_pmc_fulltext(PMID)` — Europe PMC sometimes resolves full text from the PMID directly.
   - `get_pmc_fulltext(DOI)` — DOI-based lookup.
   - `search_pmc_fulltext(<paper title>)` — title-based search of Europe PMC; inspect the top results for a PMCID whose full-text matches the expected title. **This path is the primary recovery for known PMID→PMC mismapping.** (Validated on PMID 38200309: get_pubmed_abstract returned PMC7515726 mismapped to Skrajna 2020, and search_pmc_fulltext on the Cho title recovered the correct PMC10794148.)
6. **If all full-text retrievals fail verification**: set `fulltext_status: "abstract_only"` and proceed using only the abstract from step 2.

After any recovery succeeds, emit the corrected `pmcid`, `doi`, and `fulltext_source` in `resolution`, and log the full trail in `verification_warnings` (both the defective mapping and the recovered one). Downstream consumers rely on this audit trail.

This verification step is load-bearing. The pubmed MCP tool has a known defect where PMID→PMCID mapping can return the wrong PMC record. The subagent must NOT silently accept the wrong paper.

### 4. Apply the BEL skill

Apply `../SKILL.md` to the verified source text (full-text or abstract). Process:

1. Identify mechanism-bearing sentences. Skip narrative / background / motivational sentences.
2. For each mechanism claim: identify entities, ground to namespaces per `../reference/namespace-policy.md`, pick a BEL relation, write a BEL statement.
3. Attach the evidence bundle (quote, pmid/doi, scope, evidence_tier, last_validated).
4. If a claim cannot be expressed cleanly in BEL, emit it as a `freeform_claims` entry rather than forcing bad BEL.
5. List every entity you could not confidently ground under `unresolved_entities`.

Honor `focus_context` when present — prioritize extraction from passages relevant to the focus, and mark statements outside the focus with `confidence: "low"` or omit them entirely.

### 5. Summarize the paper

Populate `paper_summary` with main claims (≤5), methods sketch (<100 words), scope (one sentence), and limitations (from the paper itself, not the subagent's critique).

### 6. Return the JSON

The final message from the subagent must be a single JSON object conforming to the output contract. No prose before or after.

---

## Tool allowlist

The subagent uses only these tools:

- `mcp__pubmed__get_pubmed_abstract`
- `mcp__pubmed__get_pmc_fulltext`
- `mcp__pubmed__search_pubmed`
- `mcp__pubmed__search_pmc_fulltext`

The subagent does **not** write to NDEx, the local store, or the filesystem. The caller is responsible for persisting subagent output as an analysis network and attaching its UUID to the relevant edge's `supporting_analysis_uuid` field.

---

## Caller pattern (main-agent side)

From rzenith's (or any caller's) main context, invoke as:

```
Agent({
  description: "Extract BEL from <paper title abbreviation>",
  subagent_type: "general-purpose",
  prompt: """
You are the paper-processor subagent. Read `workflows/BEL/subagent/SUBAGENT.md` for your full protocol, then process the paper described in the task spec below.

TASK SPEC:
{
  "paper_id": "PMID:38200309",
  "focus_context": "focus on DDR-cGAS-STING mechanism claims",
  "caller_agent": "rzenith"
}

Follow the protocol exactly. Your final message must be a single JSON object conforming to the output contract in SUBAGENT.md — no prose before or after.
"""
})
```

The caller then:

1. Parses the returned JSON.
2. Creates an analysis network in NDEx with:
   - `name`: `ndexagent <caller> analysis PMID-<pmid> YYYY-MM-DD`
   - `ndex-agent: <caller>`, `ndex-message-type: analysis`, `ndex-workflow: paper-processor`
   - Nodes + BEL edges from the subagent output
   - `extracted_by`, `extracted_on`, `fulltext_status`, and any `verification_warnings` as network-level properties
3. Publishes the network PUBLIC and triggers Solr indexing.
4. Adds a papers-read entry with `analysis_network_uuid`.
5. Attaches `supporting_analysis_uuid` to the KG edge that motivated the extraction.

---

## Failure modes and how the subagent handles them

| Failure | Behavior |
|---|---|
| `paper_id` prefix invalid | Return output with `fulltext_status: "metadata_only"`, all arrays empty, one `verification_warnings` entry explaining the problem. |
| PubMed/Europe PMC tools unreachable | Same as above — metadata_only with a warning. Do not invent content. |
| PMID→PMC mismatch (observed defect) | Fallback chain: retry PMC with PMID, then with DOI; if all fail, `abstract_only`. |
| Abstract is a review, not a mechanism paper | Extract the review's synthesis claims at `evidence_tier: "tentative"` and note "review paper" in `paper_summary.methods`. |
| Paper is non-English | Degrade to abstract-only (English abstracts are usually available) and add warning. |
| Paper is clearly out-of-scope for `focus_context` | Return minimal output (2-3 summary claims, empty `bel_statements`), record `verification_warnings: ["paper does not match focus_context"]`. |
| >50 mechanism claims in the paper | Cap at the 20 most central; record `verification_warnings: ["truncated to 20 of N claims"]`. The caller can re-invoke with narrower `focus_context` if it wants the rest. |

---

## Smoke-test reference

An end-to-end example of a real invocation (Cho 2024, PMID 38200309) lives at [`examples/cho2024_PMID38200309.json`](examples/cho2024_PMID38200309.json).

**What the smoke test validated (2026-04-14):**

- End-to-end invocation through the `Agent` tool works; the subagent reads its own spec file and the BEL skill in its isolated context.
- The PMID→PMC verification step catches the real defect: for PMID 38200309, `get_pubmed_abstract` returned the wrong PMCID (PMC7515726 → Skrajna 2020 NAR), and the subagent correctly detected the title mismatch and recovered the real record (PMC10794148 → Cho 2024 Nature) via `search_pmc_fulltext`. The audit trail is preserved in `verification_warnings`.
- Nine well-formed BEL statements extracted across the full mechanistic chain (MRN binding → cGAS activation → STING → ZBP1 → RIPK3 → MLKL necroptosis → tumor suppression). Quotes are verbatim from the full text. Evidence tiers are sensibly mixed (`established` for canonical cGAS-STING-ZBP1-RIPK3-MLKL axis pieces, `supported` for the novel MRN-displacement claims, correctly applied).
- Two genuinely non-BEL claims (partial-displacement stoichiometry, MRE11 domain separation-of-function) were routed to `freeform_claims` rather than forced into BEL.
- Five entities properly surfaced under `unresolved_entities` rather than hallucinated.

**Drift the smoke test revealed (now addressed in this spec):**

- The subagent drifted on a few field names in first invocation (`claim` instead of `text` in freeform_claims; `attempted_namespace` instead of `suggested_namespace`; added non-schema `notes` fields inside freeform_claims and unresolved_entities). The "Strict field names" block above was added in response. Validate output against `output_schema.json` before persisting to an analysis network.

Use the example as a sanity check when iterating on the subagent prompt or the BEL skill — the structure and field population should stay consistent. Expect exact BEL statements to drift as the skill evolves; the contract should not.

---

## Versioning

Changes to this file are changes to the subagent's contract. Breaking changes (field removals, semantic changes to existing fields) require a version bump: add `"subagent_version": "v2"` to the output contract and update callers. Additive changes (new optional fields, new warning types) do not require a version bump.

Current version: **v1** (implicit — no version field emitted).
