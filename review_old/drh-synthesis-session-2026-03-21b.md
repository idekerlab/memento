# drh Synthesis Session Report — 2026-03-21 (session b)

## Session Summary

Agent drh completed a **major synthesis revision (v4)**, adopting janetexample's three-mechanism framework for TRIM25 antiviral activity. This session integrates two critical papers that were missing from v3: Meyerson 2017 (nuclear vRNP elongation block) and Sun 2025 (PB1 proteasomal degradation). The result is the most comprehensive and internally consistent model to date: 30 nodes, 35 edges, 5 tracked hypotheses, subcellular compartment annotations throughout.

## Key Inputs Processed

**janetexample critique of v3 (f583c989-2542-11f1-94e8-005056ae3c32):**
- v3 still missing Meyerson 2017 (highest-priority critique point from first review)
- Sun 2025 transforms the model: TRIM25 has TWO distinct anti-polymerase mechanisms
- Proposed three-mechanism framework: (1) nuclear vRNP elongation block, (2) PB1 degradation, (3) canonical RIG-I K63-Ub
- Report readiness: NOT YET, but approaching after v4

**Meyerson et al. 2017 (PMID 29107643, Cell Host & Microbe, Sawyer lab):**
- Nuclear TRIM25 specifically targets assembled influenza vRNPs
- Blocks onset of RNA chain elongation — prevents RNA movement into polymerase complex
- Does NOT inhibit initiation of capped-RNA-primed mRNA synthesis
- RING-INDEPENDENT (not E3 ligase activity)
- Inhibited by NS1
- This is almost certainly the phenomenon detected by TenVIP-seq as "RdRp pausing"

**Sun et al. 2025 (PMID 40693041, Biosafety and Health, Wang lab):**
- RIG-I and TRIM25 cooperate to degrade IAV PB1 via RING-dependent ubiquitination
- RIG-I serves as COFACTOR — but NOT through its signaling pathway (CARD-dead and ATPase-dead mutants still work)
- Host lncRNA IPAN shields PB1 from RIG-I/TRIM25 access
- IPAN knockdown enhances PB1-TRIM25 and PB1-RIG-I association, restoring degradation

**Kim et al. 2025 (PMID 40179174, Science, Kim VN lab):**
- TRIM25 RNA affinity increases at acidic pH — proton-sensing surveillance
- N4BP1 and KHNYN act redundantly downstream with ZAP
- N1-methylpseudouridine modification reduces TRIM25 RNA binding

**Sanchez et al. 2018 (PMID 30342007, JMB, Pornillos lab):**
- TRIM25 has MULTIPLE RNA-binding surfaces: PRY/SPRY domain AND lysine-rich motif in CC-SPRY linker
- Explains why ΔRBD (PRY/SPRY 470-508 only) doesn't abolish RNA binding

## Synthesis v4 — Three-Mechanism Framework

### Mechanism 1: Nuclear vRNP Elongation Block (Meyerson 2017)
- **Location**: Nuclear
- **RING requirement**: INDEPENDENT
- **Target**: Assembled vRNPs (not free polymerase subunits)
- **Action**: Blocks RNA movement into polymerase complex, preventing elongation onset
- **Countered by**: NS1 (E96/E97 → TRIM25 coiled-coil)
- **= TenVIP-seq "RdRp pausing"** (Zhu 2026)
- **= Choudhury 2022 "mRNA destabilization"** (same mechanism, different resolution)
- **CORNERSTONE** of the revised model

### Mechanism 2: PB1 Proteasomal Degradation (Sun 2025)
- **Location**: Context-dependent (TBD)
- **RING requirement**: DEPENDENT
- **Target**: PB1 protein
- **Cofactor**: RIG-I (signaling-independent — effector-like function)
- **Countered by**: lncRNA IPAN (shields PB1)
- Distinct from Mechanism 1

### Mechanism 3: RIG-I K63-Ub Activation (Canonical)
- **Location**: Cytoplasmic
- **RING requirement**: DEPENDENT
- **Target**: RIG-I CARDs
- **Redundancy**: RIPLET is the essential endogenous activator (Hayman 2019)
- **Countered by**: NS1 (TRIM25) + NS1 (RIPLET, species-specific)

### Plus Ancillary: ZAP-mediated RNA Decay Coordination
- TRIM25 coordinates ZAP-mediated viral RNA decay (Bouton 2026)
- N4BP1 and KHNYN redundant downstream effectors (Kim 2025)
- pH-sensing may regulate this activity (endosomal)

## Paradox Resolutions

**RING-dead paradox (Choudhury 2022):** ΔRING still inhibits IAV because Mechanism 1 is RING-independent. Mechanism 2 (PB1 degradation) would be lost but Mechanism 1 is sufficient.

**ΔRBD paradox (Choudhury 2022):** ΔRBD (PRY/SPRY 470-508 deletion) still inhibits IAV because: (i) Mechanism 2 may not require canonical RBD, and (ii) Sanchez 2018 shows multiple RNA-binding surfaces — ΔRBD removes only one, leaving lysine-rich linker and possible coiled-coil contacts intact for Mechanism 1.

**Krogan AP-MS absence:** Mechanism 1 targets assembled vRNPs, which wouldn't be captured by individual bait protein pull-downs. Mechanism 2 requires RIG-I cofactor — may depend on infection context absent in AP-MS.

## Revised Hypothesis Tracking

| Hypothesis | v3 Status | v4 Status | Key Change |
|---|---|---|---|
| H_vrnp: TRIM25 binds vRNPs, blocks elongation | — | **STRONGLY SUPPORTED** | NEW. Merges H_rna + H_cryptic_rbd. Cornerstone = Meyerson 2017 |
| H_direct: TRIM25 interacts with polymerase subunit | WEAKENED | **REFRAMED** | Sun 2025: TRIM25 does interact with PB1, but for degradation not pausing |
| H_ubr5: UBR5 mediates RdRp pausing | STRENGTHENED | **WEAKENED** | Two direct TRIM25 mechanisms reduce explanatory need for UBR5 |
| H_chain: Elongation block → mvRNA → RIG-I | PARTIAL | **SUPPORTED** | Mechanism 1 elongation block → truncated products → mvRNA pathway |
| H_cryptic_rbd: Cryptic RNA-binding surface | NEW | **MERGED → H_vrnp** | Explained by Sanchez 2018 multiple surfaces |
| H_pH: TRIM25 pH-sensing regulates mechanisms | — | **NEW** | Kim 2025 Science. Endosomal pH activates RNA affinity |

## Four IAV Evasion Axes (Updated)

1. **NS1 → TRIM25/RIPLET**: Blocks Mechanisms 1 + 3, and RIPLET-dependent RIG-I activation
2. **NP → RIG-I**: Antagonizes Pol III ncRNA self-sensing (Ledwith 2025)
3. **PB1 → TRIM25/MAVS**: Co-opts TRIM25 for MAVS degradation (Luo 2025, H9N2)
4. **IPAN → PB1 shielding**: Host lncRNA co-opted to protect PB1 from Mechanism 2 (Sun 2025)

## Networks Published/Updated

| Network | UUID | Action | Nodes | Edges |
|---|---|---|---|---|
| Synthesis v4 | 7e4db1a1-2548-11f1-94e8-005056ae3c32 | CREATED | 30 | 35 |
| Episodic memory | 8498f3f2-1ff9-11f1-94e8-005056ae3c32 | UPDATED (v4.0) | 8 | 7 |
| Plans and priorities | 847fc69e-1ff9-11f1-94e8-005056ae3c32 | UPDATED (v4.0) | 11 | 9 |

All networks set to PUBLIC visibility.

## Discriminating Experiments Proposed (v4)

1. **TRIM25 ΔRING + vRNP binding assay** — Confirm Mechanism 1 is RING-independent
2. **Nuclear-excluded TRIM25 (NES-tagged) + TenVIP-seq** — Test nuclear requirement for pausing
3. **TRIM25 ΔRING + TenVIP-seq** — Mechanism 1 predicts pausing preserved; Mechanism 2 lost
4. **RIG-I CARD-dead + PB1 stability** — Confirm RIG-I cofactor role is signaling-independent (partially done in Sun 2025)
5. **IPAN knockdown + TenVIP-seq** — Does removing IPAN shield enhance pausing (Mechanism 2 effect) or is it independent (Mechanism 1)?
6. **pH titration of TRIM25-vRNP binding** — Does Kim 2025 pH-sensing apply to Mechanism 1?

## Next Priorities

1. **Await janetexample v4 critique** — all requested elements addressed
2. **Deep-read Sun 2025 full text** — PB1 ubiquitination sites, subcellular location, IPAN kinetics
3. **Test pH-sensing connection** — does fever/pH affect nuclear Mechanism 1?
4. **Map temporal dynamics** — when do each mechanism operate during infection?
5. **Build experimental design network** — formalize 6 experiments as structured graph
6. **Update collaborator map** — add Sawyer, Wang, Kim VN labs

## Model Evolution Summary

| Version | Central Theme | Nodes | Edges | Key Advance |
|---|---|---|---|---|
| v1 | TRIM25 triple-function hub | ~15 | ~18 | Initial integration |
| v2 | TRIM25 RNA-mediated, RIPLET primacy | 24 | 27 | Interactome grounding, RIPLET essential |
| v3 | Cryptic RNA-binding, UBR5 precedent | 27 | 31 | Choudhury deep-read, Sindbis precedent |
| v4 | **Three-mechanism framework** | 30 | 35 | Meyerson vRNP block, Sun PB1 degradation, paradox resolution, subcellular compartments |

## Lessons Learned

- janetexample's critique was again the most impactful input — the three-mechanism framework from her second review (f583c989) became the organizing principle for v4
- Meyerson 2017 was hiding in plain sight — a 2017 Cell Host & Microbe paper that reframes everything we thought about TRIM25 and "RdRp pausing." Deep reading > broad scanning
- The three-mechanism framework resolves paradoxes that seemed contradictory under simpler models. The RING-dead and ΔRBD results that were puzzling in v2-v3 fall naturally out of having RING-independent and RING-dependent mechanisms
- Adding subcellular compartment annotations immediately reveals new questions (where does Mechanism 2 occur? how does TRIM25 enter the nucleus during infection?)
- The model is converging toward report-readiness: the central framework is now internally consistent and explains the major experimental observations
