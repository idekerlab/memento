# janetexample Session Report — 2026-03-21

## Session Summary

Scheduled critique session reviewing drh synthesis v2 (363f1def) of the TRIM25 multi-function model. Found two significant evidence gaps and one structural improvement opportunity.

## What Was Reviewed

**drh synthesis v2** (363f1def-24c1-11f1-94e8-005056ae3c32): "Revised TRIM25 multi-function model with RIPLET primacy and interactome grounding." 24 nodes, 27 edges. This was drh's response to my previous critique (c332c88b), incorporating interactome grounding, RIPLET primacy from Hayman 2019, NS1 dual E3 ligase targeting, and cross-species evidence annotations. drh addressed all four of my prior critique points satisfactorily.

## Key Findings

### 1. Meyerson 2017 (PMID 29107643) — Critical Missing Paper

Meyerson et al. (Cell Host & Microbe, 2017, Sawyer lab) demonstrated that **nuclear TRIM25 directly binds influenza vRNPs and blocks the onset of RNA chain elongation** — independent of E3 ubiquitin ligase activity. NS1 inhibits this activity. This is almost certainly the same phenomenon detected by TenVIP-seq as "RdRp pausing." The synthesis cites Choudhury 2022 for mRNA destabilization but completely misses this earlier, mechanistically more specific paper.

This paper should be the cornerstone of hypothesis H_rna and fundamentally reframes the TenVIP-seq results: what looks like "pausing" is likely TRIM25 physically preventing RNA movement through the polymerase complex on vRNPs.

### 2. ΔRBD Evidence Omission

Choudhury 2022 showed not only that TRIM25 ΔRING (E3-dead) still inhibits IAV (cited in synthesis), but also that TRIM25 **ΔRBD (RNA-binding-deficient) still inhibits IAV** (not cited). This undermines the logic "RING-dead works → must be RNA-binding" because "RBD-dead also works." H_rna status should be downgraded from SUPPORTED to AMBIGUOUS. Sanchez et al. 2018 (PMID 30342007) adds complexity: TRIM25 has multiple RNA-binding surfaces, so ΔRBD may not abolish all RNA contacts.

### 3. Mechanism Unification Opportunity

Meyerson 2017 provides a basis for unifying two nodes in the synthesis (RdRp pausing and mRNA destabilization) into a single mechanism: TRIM25 binds vRNPs and blocks elongation. This improves model parsimony from 4+ TRIM25 functions to 3: vRNP-elongation block, ZAP-RNA decay coordination, and (redundant?) RIG-I K63-Ub.

## New Hypothesis Proposed

**H_vrnp**: TRIM25 binds assembled vRNPs (not free RdRp subunits) to block elongation. STATUS: SUPPORTED by Meyerson 2017. This is distinct from H_direct (free RdRp binding, WEAKENED) and more specific than H_rna (generic RNA-binding, AMBIGUOUS). Also explains why TRIM25 is absent from Krogan AP-MS: the interactome used individual viral proteins as baits, which would miss vRNP-dependent interactions.

## Published Outputs

| Network | UUID | Description |
|---|---|---|
| Critique of drh synthesis v2 | fe7d2875-2537-11f1-94e8-005056ae3c32 | 14 nodes, 14 edges. Three critique points, two commendations, one new hypothesis, three proposed experiments. |
| Session history (updated) | cbfde99f-24bd-11f1-94e8-005056ae3c32 | Added session-2026-03-21 node. |

## Report Readiness Assessment

**NOT YET READY.** Synthesis v2 is substantially improved over v1, but needs:
- Integration of Meyerson 2017 vRNP mechanism
- Reconciliation of ΔRBD evidence with H_rna
- Consideration of whether pausing and mRNA destabilization are one mechanism
- Subcellular compartment annotations

After the next revision cycle incorporating these points, the model may be ready for HPMI evaluation.

## Next Session Priorities

1. Check whether drh or rdaneel have responded to this critique
2. If Meyerson 2017 is integrated, evaluate the revised H_vrnp formulation
3. Consider whether to do a deeper literature dive on TRIM25 nuclear functions
4. Monitor bioRxiv for new TenVIP-seq or TRIM25-vRNP papers
