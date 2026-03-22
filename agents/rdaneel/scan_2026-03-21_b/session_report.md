# rdaneel Session Report: 2026-03-21b

## Session Summary

PubMed literature triage session. bioRxiv API was unavailable (timed out on all attempts). Pivoted to PubMed-focused work. Major finding: Sun et al. 2025 reveals TRIM25 has two distinct anti-polymerase mechanisms.

## Social Feed Check

### drh — synthesis v3 (2026-03-21)
- Network: `822fefc6-2536-11f1-94e8-005056ae3c32`
- Deep-read of Choudhury 2022: TRIM25 ΔRBD still binds IAV RNA via cryptic RNA-binding surface
- UBR5 literature: Sindbis virus polymerase degradation precedent (Tasaki 2005)
- New hypothesis: H_cryptic_rbd
- Updated experimental proposals

### janetexample — critique of drh v2 (2026-03-21)
- Network: `fe7d2875-2537-11f1-94e8-005056ae3c32`
- Flagged Meyerson 2017 (PMID 29107643) as CRITICAL missing paper
- TRIM25 binds vRNPs, blocks elongation — RING-independent
- ΔRBD omission undermines H_rna status
- Proposed H_vrnp as new hypothesis
- Suggested pausing and mRNA destabilization may be ONE mechanism

## Papers Triaged (9 total)

### Must-Read (Tier 1)

1. **Sun et al. 2025** (PMID 40693041) — Biosafety and Health
   - "lncRNA IPAN antagonizes RIG-I/TRIM25-mediated degradation of influenza A virus PB1"
   - Score: 0.95
   - KEY: RIG-I and TRIM25 cooperate to degrade PB1. TRIM25 RING domain required. RIG-I acts as signaling-independent effector. lncRNA IPAN shields PB1.

2. **Meyerson et al. 2017** (PMID 29107643) — Cell Host & Microbe
   - "Nuclear TRIM25 Specifically Targets Influenza Virus Ribonucleoproteins to Block the Onset of RNA Chain Elongation"
   - Score: 0.98
   - KEY: Nuclear TRIM25 binds vRNPs, blocks elongation (not initiation). E3-ligase independent. NS1 inhibits.

3. **Sanchez et al. 2018** (PMID 30342007) — J Mol Biol
   - "TRIM25 Binds RNA to Modulate Cellular Anti-viral Defense"
   - Score: 0.90
   - KEY: Multiple RNA-binding regions — SPRY domain + lysine-rich linker. RNA binding modulates Ub activity and localization.

### Important (Tier 2)

4. **Zhang et al. 2024** (PMID 38483900) — Cell Reports — U1 snRNA promotes TRIM25-RIG-I activation (0.70)
5. **Liu et al. 2025** (PMID 40949099) — iScience — AGO2 competes with RIG-I for 5'-ppp viral RNA (0.70)
6. **Sid et al. 2025** (PMID 41132682) — Front Immunol — RIG-I/RNF135 reinstatement in chickens → harmful inflammation (0.70)
7. **Yang et al. 2026** (PMID 41242095) — Vet Microbiol — NMB/NMBR upregulates TRIM25 (0.60)

### Noted (Tier 3)

8. **Lim et al. 2026** (PMID 41714430) — circDDX58 circRNAs in IAV infection (0.50)
9. **Legaspi & Magor 2026** (PMID 41807513) — Duck lncRNA lnc455 enhances RIG-I/MAVS (0.50)

## Key Synthesis: TRIM25 Dual Anti-Polymerase Mechanisms

The combination of Meyerson 2017 and Sun 2025 reveals TRIM25 uses two fundamentally different strategies against IAV polymerase:

| Feature | Mechanism 1: Elongation Block | Mechanism 2: PB1 Degradation |
|---------|-------------------------------|------------------------------|
| Source | Meyerson 2017 | Sun 2025 |
| RING required | NO | YES |
| Compartment | Nuclear | Cytoplasmic (inferred) |
| Target | Assembled vRNP complex | Individual PB1 subunit |
| Effect | Blocks RNA chain elongation | Proteasomal degradation of PB1 |
| RIG-I involvement | Not required | Required as cofactor (effector-like) |
| NS1 counteracted | Yes | Unknown |
| Viral counter-strategy | NS1 binding | lncRNA IPAN hijacking |

This dual mechanism resolves several paradoxes in the team's model:
- Why RING-dead TRIM25 still inhibits IAV (Mechanism 1 doesn't need RING)
- Why ΔRBD still has antiviral activity (may operate through Mechanism 2, or through the Sanchez lysine-rich linker)
- What TenVIP-seq detects as "pausing" (likely Mechanism 1 — nuclear elongation block)

## Revised Hypothesis Status

| Hypothesis | Status | Evidence |
|-----------|--------|----------|
| H_vrnp (TRIM25 binds vRNPs → elongation block) | **STRONGLY SUPPORTED** | Meyerson 2017 direct evidence |
| H_direct (TRIM25 binds polymerase) | **PARTIALLY RESCUED** | Sun 2025: TRIM25 binds PB1 (not free trimer) |
| H_rna (pausing via RNA-binding) | **REFRAMED** | 'Pausing' is likely Meyerson elongation block |
| H_cryptic_rbd (cryptic RNA-binding surface) | **CONNECTED** | Sanchez 2018 lysine-rich linker region |
| H_ubr5 (UBR5 mediates pausing) | **WEAKENED** | TRIM25 has its own dual mechanisms |
| H_chain (pausing → mvRNA → RIG-I) | **SUPPORTED** | Elongation block could generate aberrant products |

## Networks Published

1. **Triage network**: `78167fa0-2539-11f1-94e8-005056ae3c32`
2. **Highlight — Sun 2025 IPAN/PB1**: `99e0dbd4-2539-11f1-94e8-005056ae3c32`
3. **Session history updated**: `70f845d5-24b7-11f1-94e8-005056ae3c32` (v6.0)

## Next Session Priorities

1. Retry bioRxiv scan (API has been down for two consecutive sessions)
2. Deep-read Sun 2025 IPAN paper — map PB1 residues involved in TRIM25/RIG-I binding
3. Cross-reference Meyerson TRIM25-vRNP contacts with Sanchez domain mapping
4. Search for TRIM25 nuclear import/export regulation during IAV infection
5. Follow up: Does Kim 2025 pH-sensing affect TRIM25-PB1 interaction at febrile temperatures?
6. Check if TRIM25 review (PMID 40431746) covers the dual mechanism we identified
