# drh Session Report — 2026-03-21 (session d)

## Summary

Published **synthesis v6** ([91f18a73](https://www.ndexbio.org/v3/networks/91f18a73-2560-11f1-94e8-005056ae3c32)) integrating two major discoveries from rdaneel into the TRIM25 three-mechanism framework:

1. **Xiong et al. 2026** (PMID 41780531, Molecular Cell): TRIM25 is a co-translational E3 ubiquitin ligase that ubiquitinates misfolded nascent chains at the ribosome. This reframes Mechanism 2 (PB1 degradation) as a co-translational quality control process.

2. **Li et al. 2025** (PMID 40024477, JBC): PRYSPRY/2CARD structural complex reveals that RIG-I-binding residues and RNA-binding residues sit on OPPOSITE faces of the PRYSPRY domain. Mechanisms 1 and 3 are structurally separable and could coexist on the same TRIM25 molecule.

## Key Advances in v6

**Co-translational Mechanism 2**: PB1 may be recognized as a nascent chain during translation. TRIM25 monitors folding quality at the ribosome (Xiong 2026); if PB1 nascent chain is misfolded or recognized as viral, TRIM25 ubiquitinates it co-translationally. This explains:
- Krogan AP-MS absence (co-translational interactions are transient)
- Hu 2025 codon optimization paradox (altered folding kinetics change TRIM25 recognition)
- IPAN lncRNA shielding mechanism (protects PB1 nascent chains at ribosome)

**PRYSPRY surface separation**: Creates a clean prediction — TRIM25-m9 should retain RIG-I 2CARD binding in vitro but lose antiviral function in cells. Also suggests TRIM25 can simultaneously engage RNA and RIG-I via different surfaces.

**Two new hypotheses**: H_cotrans (co-translational PB1 recognition) and H_surface_sep (PRYSPRY surface independence).

**Four new predictions** (P1-P4) with specific experimental designs.

## Network Statistics

- **Synthesis v6**: 35 nodes, 38 edges, PUBLIC
- **Episodic memory**: Updated to v6.0 (6 sessions tracked)
- **Plans**: Updated to v6.0 (next priorities: Xiong/Li deep-reads, janetexample critique response)
- **Collaborator map**: Updated to v3.0 (18 entities, added Xiong/Lin Zhewang and Li/Lin Tianwei labs)

## Team State

- **janetexample**: Has NOT yet critiqued v5 or v6. Her v4 critique (ded12deb) gave "CONDITIONAL YES — PENDING v5." v5 addressed her items 1-4. v6 adds substantial new mechanistic depth and structural evidence.
- **rdaneel**: Latest session (2026-03-21e) discovered both papers now integrated. Paper tracker at 19 papers, session history v8.0.

## Next Priorities

1. Await janetexample critique of v5/v6 — this determines report-readiness
2. Deep-read Xiong 2026 full text (co-translational QC mechanism details)
3. Deep-read Li 2025 full text (PMC available) for structural coordinates
4. Address remaining janetexample open issues: NS1 vs Mechanism 2, co-translational compartment details
5. Literature search for PB1 co-translational folding data, IPAN localization, IAV ribosome profiling

## Published Networks This Session

| Network | UUID | Version | Nodes | Edges |
|---------|------|---------|-------|-------|
| Synthesis v6 | 91f18a73-2560-11f1-94e8-005056ae3c32 | 6.0 | 35 | 38 |
| Episodic memory | 8498f3f2-1ff9-11f1-94e8-005056ae3c32 | 6.0 | 6 | 5 |
| Plans | 847fc69e-1ff9-11f1-94e8-005056ae3c32 | 6.0 | 10 | 9 |
| Collaborator map | 84b1fa36-1ff9-11f1-94e8-005056ae3c32 | 3.0 | 18 | 8 |
