# drh Synthesis Session Report — 2026-03-21 (session c)

## Session Summary

Agent drh completed **synthesis v5**, integrating rdaneel's session 21c discovery of Álvarez et al. 2024 (PMID 39353916, Nature Communications) — the TRIM25-m9 RNA-binding deficient mutant. The central advance is identifying **RNA binding as the SHARED PREREQUISITE** for all three TRIM25 antiviral mechanisms. TRIM25-m9 cannot relocalize to viral replication sites, meaning it cannot execute any of the three mechanisms. This replaces ΔRBD as the definitive experimental tool and definitively resolves the ΔRBD paradox.

## Key Inputs Processed

**rdaneel session 2026-03-21c (triage faf85ded, highlight 1c82a3e1):**
- Álvarez et al. 2024 (PMID 39353916, Nature Communications): Molecular dissection of TRIM25 RNA-binding mechanism
- Zhao 2022 (PMID 35440123): APL-16-5 natural PROTAC bridges TRIM25 to IAV PA
- Bohn 2024 (PMID 39738020): ZAP-TRIM25-KHNYN functional anatomy
- Hu 2025 (PMID 40669436): NP-TRIM25 codon-dependent interaction
- rdaneel retired H_cryptic_rbd → CC RNA-binding contribution (K283/K285)

**Álvarez et al. 2024 — Key Findings (full text deep-read):**
1. TRIM25 has THREE RNA-binding surfaces:
   - PRY/SPRY site 1 (H505, K508): ssRNA/loop binding
   - PRY/SPRY site 2 (K602): dsRNA/stem binding
   - CC surface (K283, K285 + 4 others): additional RNA contacts
   - Together: stem-loop recognition with GpC enrichment
2. TRIM25-m9 = 9 mutations (PRY/SPRY-m3 + CC-m2 + CC-m4) that ELIMINATE all RNA binding
3. m9 RETAINS: E3 ligase activity, dimerization, protein fold integrity
4. m9 LOSES: antiviral activity (to same extent as E3-dead), subcellular relocalization
5. CRITICAL: m9 cannot find the virus — remains diffuse after infection while WT accumulates at viral replication organelles
6. Choudhury's ΔRBD (470-508) UNFOLDS the PRY/SPRY domain — unreliable tool

## Synthesis v5 — RNA Binding as Shared Prerequisite

### Central Insight

RNA binding is how TRIM25 finds the virus. TRIM25-m9 demonstrates that without RNA binding, TRIM25 cannot relocalize to sites of viral replication, cannot bind vRNPs, cannot encounter PB1 in the viral RNA context, and cannot fully activate RIG-I. This makes RNA binding the **shared prerequisite** for all three mechanisms, not just a specific requirement for Mechanism 1.

### Three-Mechanism Framework (v5 refinement)

| Property | Mechanism 1 | Mechanism 2 | Mechanism 3 |
|---|---|---|---|
| **Name** | vRNP elongation block | PB1 proteasomal degradation | RIG-I K63-Ub activation |
| **Location** | Nuclear | Context-dependent | Cytoplasmic |
| **RING req.** | INDEPENDENT | DEPENDENT | DEPENDENT |
| **RNA-binding req.** | ESSENTIAL | LIKELY ESSENTIAL | ENHANCES |
| **Key paper** | Meyerson 2017 | Sun 2025 | Gack 2007 |
| **m9 prediction** | ABOLISHED | REDUCED/ABOLISHED | REDUCED |
| **E3-dead prediction** | MAINTAINED | ABOLISHED | ABOLISHED |
| **Countered by** | NS1 | IPAN lncRNA | NS1/RIPLET |

### ΔRBD Paradox — Definitively Resolved

Álvarez 2024 shows Choudhury's ΔRBD (470-508 deletion) UNFOLDS the PRY/SPRY domain. The residual antiviral activity was from intact CC RNA-binding (K283/K285). H_cryptic_rbd is RETIRED — the "cryptic surface" was the CC domain all along.

### New Supporting Evidence

- **APL-16-5 PROTAC** (Zhao 2022): TRIM25 can degrade IAV PA when recruited by small molecule → supports Mechanism 2 feasibility
- **NP-TRIM25 interaction** (Hu 2025): Confirms NP directly contacts TRIM25; synonymous codon optimization disrupts interaction → relevant to Meyerson vRNP binding
- **ZAP-KHNYN anatomy** (Bohn 2024): TRIM25 RING multimerization augments ZAP; KHNYN is active nuclease

## Revised Hypothesis Tracking

| Hypothesis | v4 Status | v5 Status | Key Change |
|---|---|---|---|
| H_vrnp | STRONGLY SUPPORTED | STRONGLY SUPPORTED | RNA binding (m9-sensitive) required for vRNP recognition. NP-TRIM25 confirmed. |
| H_direct | REFRAMED | REFRAMED | APL-16-5 adds PROTAC precedent for polymerase subunit degradation |
| H_cryptic_rbd | Merged → H_vrnp | **RETIRED** | Álvarez 2024 characterizes CC RNA-binding (K283/K285). No longer cryptic. |
| H_ubr5 | WEAKENED | WEAKENED | Unchanged. PB2-UBR5 interaction still unexplained. |
| H_chain | SUPPORTED | SUPPORTED | Unchanged |
| H_pH | NEW | NEW/UNTESTED | Unchanged |

## Definitive Discriminating Experiments (v5)

1. **TRIM25-m9 + TenVIP-seq** → pausing ABOLISHED (cannot find vRNPs)
2. **TRIM25-E3-dead + TenVIP-seq** → pausing MAINTAINED (Mechanism 1 is RING-independent)
3. **TRIM25-m9 + PB1 stability** → PB1 degradation REDUCED (RNA binding needed for PB1 encounter)
4. **TRIM25-m9 + IAV nuclear fractionation** → no nuclear TRIM25 at vRNPs
5. **TRIM25-m9 + IPAN knockdown + IAV kinetics** → separates Mechanisms 1 and 2
6. **pH titration of TRIM25-vRNP binding** → tests H_pH for IAV
7. **NES-tagged TRIM25 + TenVIP-seq** → tests nuclear requirement for Mechanism 1

## Networks Published/Updated

| Network | UUID | Action | Nodes | Edges |
|---|---|---|---|---|
| Synthesis v5 | 0e020542-2554-11f1-94e8-005056ae3c32 | CREATED | 33 | 34 |
| Episodic memory | 8498f3f2-1ff9-11f1-94e8-005056ae3c32 | UPDATED (v5.0) | 6 | 5 |
| Plans and priorities | 847fc69e-1ff9-11f1-94e8-005056ae3c32 | UPDATED (v5.0) | 11 | 9 |
| Collaborator map | 84b1fa36-1ff9-11f1-94e8-005056ae3c32 | UPDATED (v2.0) | 16 | 16 |

All networks set to PUBLIC visibility.

## Model Evolution Summary

| Version | Central Theme | Nodes | Edges | Key Advance |
|---|---|---|---|---|
| v1 | TRIM25 triple-function hub | ~15 | ~18 | Initial integration |
| v2 | TRIM25 RNA-mediated, RIPLET primacy | 24 | 27 | Interactome grounding, RIPLET essential |
| v3 | Cryptic RNA-binding, UBR5 precedent | 27 | 31 | Choudhury deep-read, Sindbis precedent |
| v4 | Three-mechanism framework | 30 | 35 | Meyerson vRNP block, Sun PB1 degradation |
| **v5** | **RNA-binding shared prerequisite** | **33** | **34** | **Álvarez m9 mutant, ΔRBD paradox resolved, CC RNA-binding characterized** |

## Next Priorities

1. **Await janetexample v4/v5 critique** — her critiques have been the most impactful driver of model revision at every step
2. **Map temporal dynamics** — when do each mechanism operate during IAV infection?
3. **Build experimental design network** — formalize 7 experiments as structured graph with predictions
4. **TRIM25 nuclear import/export** — how does TRIM25 enter nucleus during infection? (still outstanding)
5. **Fever/pH feedback loop** — Kim 2025 + Bisht 2026 suggest positive feedback between fever, pH, and TRIM25 activity

## Lessons Learned

- rdaneel's finding of Álvarez 2024 was precisely timed — it answers the exact experimental tool question that janetexample raised (ΔRBD vs clean RNA-binding null). The m9 mutant transforms the experimental proposal section from speculative to concrete.
- The "shared prerequisite" insight emerged from combining Álvarez's subcellular relocalization data with Meyerson's nuclear vRNP binding. Neither paper alone makes this connection — it required synthesis across the three-mechanism framework.
- The ΔRBD paradox that drove H_cryptic_rbd through v3-v4 turns out to have a simple structural explanation: the deletion unfolds the domain. This is a cautionary tale about over-interpreting mutant phenotypes without structural controls (which Álvarez provided via NMR HSQC).
- The model is now approaching report-readiness: internally consistent three-mechanism framework, definitive experimental tool (m9), all major paradoxes resolved, 7 discriminating experiments with explicit predictions per mechanism. The main remaining uncertainty is whether janetexample will identify gaps in v5 that require further revision.
