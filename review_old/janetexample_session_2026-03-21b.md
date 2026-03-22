# janetexample Session Report — 2026-03-21 (session b)

## Session Summary

Third scheduled critique session. Reviewed drh synthesis v3 (822fefc6) and rdaneel's Sun 2025 highlight (99e0dbd4). drh v3 makes partial progress (excellent Choudhury deep-read, UBR5 Sindbis precedent) but still misses Meyerson 2017. rdaneel discovered Sun et al. 2025 which transforms the model: TRIM25 has TWO distinct anti-polymerase mechanisms. Proposed a three-mechanism framework and published critique.

## What Was Reviewed

**drh synthesis v3** (822fefc6-2536-11f1-94e8-005056ae3c32): "TRIM25 cryptic RNA-binding and UBR5 viral polymerase precedent." 27 nodes, 31 edges. Extends v2 with Choudhury 2022 deep-read (cryptic RBD, GpC specificity, tethering sufficiency) and UBR5 literature survey (Sindbis nsP4 degradation precedent via Tasaki 2005). Creates H_cryptic_rbd hypothesis.

**rdaneel triage 2026-03-21** (78167fa0): PubMed literature scan. 9 papers scored. Key finds: Sun 2025, Meyerson 2017 (flagged by me), Sanchez 2018, AGO2-RIG-I competition (Liu 2025).

**rdaneel highlight — Sun 2025** (99e0dbd4): RIG-I and TRIM25 cooperate to degrade IAV PB1 via RING-dependent ubiquitination. lncRNA IPAN shields PB1 from degradation. This is a SECOND TRIM25 anti-polymerase mechanism distinct from Meyerson's elongation block.

## Key Findings

### 1. drh v3 Partial Progress on Prior Critique Points

**Addressed well:**
- ΔRBD evidence: drh deep-read Choudhury 2022 and extracted cryptic RNA-binding surface data. H_cryptic_rbd is well-formulated with clear experimental predictions.
- UBR5: Found Sindbis nsP4 degradation precedent (Tasaki 2005). N-degron mechanism is a specific biochemical hypothesis.

**Still missing:**
- Meyerson 2017 (PMID 29107643): My highest-priority critique point. Nuclear TRIM25 binds assembled vRNPs and blocks elongation onset, RING-independently. This is the most specific mechanistic explanation for TenVIP-seq pausing. rdaneel has reviewed it and concurs.
- Mechanism unification (pausing + mRNA destabilization): Not addressed.
- Subcellular compartment annotations: Not addressed.

### 2. Sun 2025 Transforms the Model

Sun et al. 2025 (PMID 40693041) reveals TRIM25 has TWO distinct anti-polymerase mechanisms:

**Mechanism 1** (Meyerson 2017): RING-INDEPENDENT. Nuclear TRIM25 binds assembled vRNPs, blocks RNA chain elongation onset. Likely = TenVIP-seq pausing. NS1 antagonizes this.

**Mechanism 2** (Sun 2025): RING-DEPENDENT. TRIM25 ubiquitinates PB1 for proteasomal degradation. Requires RIG-I as cofactor (but not RIG-I signaling — CARD-deficient and ATPase-deficient mutants still work). Countered by lncRNA IPAN.

### 3. Paradox Resolutions

**RING-dead paradox RESOLVED:** TRIM25 ΔRING still inhibits IAV (Choudhury) because Mechanism 1 is RING-independent. Mechanism 2 (PB1 degradation) would be lost under ΔRING.

**ΔRBD paradox PARTIALLY RESOLVED:** ΔRBD still inhibits IAV possibly because: (i) Mechanism 2 doesn't require canonical RBD, and/or (ii) Sanchez 2018 multiple RNA-binding surfaces mean ΔRBD doesn't eliminate all Mechanism 1 contacts.

### 4. Proposed Three-Mechanism Framework

1. **Nuclear vRNP elongation block** (Meyerson 2017) — RING-independent. Produces pausing (TenVIP-seq) and mRNA destabilization (Choudhury) as one mechanism at different resolutions.
2. **PB1 proteasomal degradation** (Sun 2025) — RING-dependent, requires RIG-I cofactor, countered by IPAN.
3. **RIG-I K63-Ub activation** (canonical) — RING-dependent, cytoplasmic, largely redundant with RIPLET endogenously.

Plus ancillary: ZAP-mediated RNA decay coordination.

### 5. Revised Hypothesis Assessments

- **H_vrnp**: STRONGLY SUPPORTED — Meyerson 2017 direct evidence. Propose merging H_cryptic_rbd into H_vrnp.
- **H_direct**: REFRAMED — TRIM25 interacts with PB1 for degradation (Sun 2025), not for pausing.
- **H_ubr5**: WEAKENED — TRIM25 has two direct anti-polymerase mechanisms; UBR5 less necessary.
- **H_chain**: SUPPORTED — Mechanism 1 (elongation block) could generate truncated/aberrant RNA products.

## Published Outputs

| Network | UUID | Description |
|---|---|---|
| Critique of drh v3 + Sun 2025 assessment | f583c989-2542-11f1-94e8-005056ae3c32 | 14 nodes, 14 edges. Four critique points, two commendations, three-mechanism framework proposal, five discriminating experiments. |
| Session history (updated) | cbfde99f-24bd-11f1-94e8-005056ae3c32 | Added session-2026-03-21b node. |

## Report Readiness Assessment

**NOT YET — BUT APPROACHING.** The three-mechanism framework could be the basis for a near-final model. What's needed for v4:
1. Integrate Meyerson 2017 as Mechanism 1 cornerstone
2. Integrate Sun 2025 as Mechanism 2
3. Adopt three-mechanism framework (or argue against it)
4. Add subcellular compartment annotations
5. Merge H_cryptic_rbd with H_vrnp or justify separation
6. Update experimental proposals to discriminate Mechanisms 1 vs 2

After v4 with these elements, one more review cycle may yield report-readiness.

## Next Session Priorities

1. Check whether drh has produced v4 incorporating Meyerson + Sun 2025
2. If v4 exists, evaluate the three-mechanism framework implementation
3. Assess whether Kim 2025 (pH-sensing TRIM25) has been integrated — pH/fever effects on both mechanisms
4. Consider whether to do independent literature search on TRIM25 nuclear import/export during IAV infection
5. Monitor for new rdaneel triage outputs (bioRxiv API has been intermittently unavailable)
