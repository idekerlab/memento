# BEL Authoring Examples

Worked examples for agent-authored BEL with full evidence annotations per NDExBio curation policy. Unlike `bel_prompt.md` (which was built for a paper-extraction workflow with pre-annotated entities), these examples reflect curator- and researcher-agent authorship: identify entities yourself, ground them, and attach provenance.

---

## Example 1 — Clean direct-effect extraction

**Source** (hypothetical paper excerpt, PMID 33290271):
> "ATM deficiency triggers release of mitochondrial DNA into the cytosol, where it is sensed by cGAS, leading to STING-dependent interferon signaling. We observed this in multiple cell lines using siRNA-mediated ATM depletion."

**Author three statements:**

```json
[
  {
    "bel": "act(p(HGNC:ATM)) directlyDecreases a(CHEBI:\"mitochondrial DNA\", loc(GO:cytosol))",
    "evidence": {
      "quote": "ATM deficiency triggers release of mitochondrial DNA into the cytosol",
      "pmid": "33290271",
      "supporting_analysis_uuid": null,
      "scope": "multiple cell lines; siRNA-mediated ATM depletion",
      "evidence_tier": "supported",
      "last_validated": "2026-04-14"
    }
  },
  {
    "bel": "a(CHEBI:\"mitochondrial DNA\", loc(GO:cytosol)) directlyIncreases act(p(HGNC:CGAS))",
    "evidence": {
      "quote": "mitochondrial DNA into the cytosol, where it is sensed by cGAS",
      "pmid": "33290271",
      "supporting_analysis_uuid": null,
      "scope": "multiple cell lines; siRNA-mediated ATM depletion",
      "evidence_tier": "supported",
      "last_validated": "2026-04-14"
    }
  },
  {
    "bel": "act(p(HGNC:CGAS)) increases act(p(HGNC:STING1))",
    "evidence": {
      "quote": "sensed by cGAS, leading to STING-dependent interferon signaling",
      "pmid": "33290271",
      "supporting_analysis_uuid": null,
      "scope": "multiple cell lines; siRNA-mediated ATM depletion",
      "evidence_tier": "supported",
      "last_validated": "2026-04-14"
    }
  }
]
```

**Notes:**
- The ATM → mtDNA link uses `directlyDecreases` because the mechanism (ATM kinase activity suppressing mtDNA release) is direct. The cGAS → STING link uses `increases` (indirect) because the paper reports a signaling outcome, not direct cGAS-STING binding.
- Each statement gets its own quote — short, verbatim, <40 words.
- `scope` captures what the paper actually did. A reader shouldn't assume in vivo from these statements.

---

## Example 2 — Phosphorylation with site

**Source** (hypothetical, PMID 12345678):
> "TBK1 phosphorylates STING at Serine 366, which is required for IRF3 recruitment and type I interferon induction."

```json
[
  {
    "bel": "act(p(HGNC:TBK1), ma(kin)) directlyIncreases p(HGNC:STING1, pmod(Ph, S, 366))",
    "evidence": {
      "quote": "TBK1 phosphorylates STING at Serine 366",
      "pmid": "12345678",
      "supporting_analysis_uuid": null,
      "scope": "biochemical; site-specific",
      "evidence_tier": "established",
      "last_validated": "2026-04-14"
    }
  },
  {
    "bel": "p(HGNC:STING1, pmod(Ph, S, 366)) directlyIncreases complex(p(HGNC:STING1), p(HGNC:IRF3))",
    "evidence": {
      "quote": "required for IRF3 recruitment",
      "pmid": "12345678",
      "supporting_analysis_uuid": null,
      "scope": "biochemical; site-specific",
      "evidence_tier": "established",
      "last_validated": "2026-04-14"
    }
  }
]
```

**Notes:**
- PTM state is first-class in BEL via `pmod()`. The phospho-STING is a distinct entity from unphosphorylated STING, and the downstream effect is specifically about the phosphorylated form.
- `evidence_tier: established` because this is well-replicated in the field; a single-paper claim should be `supported`.

---

## Example 3 — Correlation without causal mechanism

**Source** (hypothetical, PMID 22334455):
> "Among 312 triple-negative breast cancer patients, BRCA1 germline mutation status was associated with elevated expression of basal cytokeratins (CK5/14/17) and HER1/EGFR."

```json
[
  {
    "bel": "g(HGNC:BRCA1, var(\"germline mutation\")) positiveCorrelation r(HGNC:EGFR)",
    "evidence": {
      "quote": "BRCA1 germline mutation status was associated with elevated expression of ... HER1/EGFR",
      "pmid": "22334455",
      "supporting_analysis_uuid": null,
      "scope": "n=312 triple-negative breast cancer patients; association study, no mechanism",
      "evidence_tier": "supported",
      "last_validated": "2026-04-14"
    }
  }
]
```

**Notes:**
- Use `positiveCorrelation` — the paper reports association, not a causal mechanism. Upgrading to `increases` without mechanistic evidence is over-claiming.
- The `var("germline mutation")` qualifier preserves the paper's specificity without pretending to a specific sequence variant.
- `scope` captures cohort size and study type, which will matter to anyone interpreting this edge later.

---

## Example 4 — Curation review: adding provenance to an existing edge

Not an extraction task — a review task. rzenith is reviewing edge `MRE11 → PD-L1` in the DDR KB v1.1, which currently lacks provenance.

**Current edge in graph:**
```
source: p(HGNC:MRE11)
target: p(HGNC:CD274)      [PD-L1]
relation: increases
evidence_tier: assumed
```

**After literature check** (rzenith finds and reads the key paper, or invokes the paper-processor subagent):

```json
{
  "bel": "act(p(HGNC:MRE11A)) increases p(HGNC:CD274, loc(GO:nucleus))",
  "evidence": {
    "quote": "MRE11-dependent resection is required for nuclear PD-L1 accumulation following DNA damage",
    "pmid": "XXXXXXXX",
    "supporting_analysis_uuid": "<uuid of rgiskard's analysis of the paper, if one exists>",
    "scope": "breast cancer cell lines; following ionizing radiation",
    "evidence_tier": "tentative",
    "last_validated": "2026-04-14"
  }
}
```

**Notes:**
- The original edge was imprecise. The paper's claim is specifically about *nuclear* PD-L1, not total PD-L1. The updated BEL uses `loc(GO:nucleus)` to capture this.
- `MRE11` is actually `MRE11A` in current HGNC — the review caught a minor naming drift.
- `evidence_tier: tentative` because this is single-paper at review time. Would upgrade to `supported` or `established` if multiple independent sources were found.
- A second edge could be authored for the upstream step (DNA damage → MRE11 activation), but only if the paper makes that claim explicitly.

---

## Example 5 — When to degrade to a freeform claim node

**Source:**
> "The inflammatory tumor microenvironment characteristic of BRCA-deficient tumors may contribute to their sensitivity to PARP inhibitors."

This is narrative and speculative. "Inflammatory tumor microenvironment" is not a clean BEL entity — it's a context, and the paper marks the claim as speculation ("may contribute").

**Do not force BEL.** Instead:

```json
{
  "node_type": "claim",
  "text": "Inflammatory tumor microenvironment in BRCA-deficient tumors may contribute to PARP inhibitor sensitivity",
  "evidence": {
    "quote": "The inflammatory tumor microenvironment characteristic of BRCA-deficient tumors may contribute to their sensitivity to PARP inhibitors",
    "pmid": "XXXXXXXX",
    "supporting_analysis_uuid": null,
    "scope": "narrative / speculative",
    "evidence_tier": "tentative",
    "last_validated": "2026-04-14"
  }
}
```

**Notes:**
- Claim nodes won't render in the GO-CAM view — that's OK. They're honest placeholders for things BEL can't cleanly say.
- When (or if) the field produces specific mechanistic evidence for this claim, the claim node can be replaced with proper BEL statements during review.

---

## Common patterns quick reference

| Claim shape | BEL form |
|---|---|
| X binds Y (forming complex) | `complex(p(HGNC:X), p(HGNC:Y))` |
| X directly phosphorylates Y at site | `act(p(HGNC:X), ma(kin)) directlyIncreases p(HGNC:Y, pmod(Ph, S, n))` |
| X activates process P | `act(p(HGNC:X)) increases bp(GO:"P")` (or `directlyIncreases` if direct) |
| X inhibits Y's activity | `p(HGNC:X) directlyDecreases act(p(HGNC:Y))` |
| X degrades Y | `act(p(HGNC:X)) directlyIncreases deg(p(HGNC:Y))` |
| X correlates with disease D | `p(HGNC:X) positiveCorrelation path(DOID:"D")` |
| Drug D inhibits protein P | `a(CHEBI:"D") directlyDecreases act(p(HGNC:P))` |
| X is required for (but not sufficient for) process | `rateLimitingStepOf` or `bp(GO:"X") subProcessOf bp(GO:"P")` |
| A, B, C together produce effect (but not alone) | `composite(p(HGNC:A), p(HGNC:B), p(HGNC:C)) increases ...` |
