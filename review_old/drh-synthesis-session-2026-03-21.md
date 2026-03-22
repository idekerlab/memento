# drh Synthesis Session Report — 2026-03-21

## Session Summary

Agent drh completed a focused literature investigation session, extending synthesis v2 with two deep-dives: (1) full-text analysis of Choudhury et al. 2022, and (2) comprehensive UBR5 literature survey. These produced synthesis v3 (27 nodes, 31 edges, 5 tracked hypotheses) and a new hypothesis (H_cryptic_rbd).

## Key Inputs Processed

**Choudhury et al. 2022 (PMID 35736141) — Deep-Read:**
- TRIM25 ΔRBD mutant (lacking RNA-binding residues 470-508 in PRY/SPRY domain) STILL binds IAV positive-sense RNAs by CLIP-seq
- TRIM25 ΔRBD and ΔRING mutants both STILL inhibit IAV replication
- TRIM25 preferentially binds positive-sense IAV RNAs; binding correlates with GpC dinucleotide frequency
- Direct tethering of TRIM25 to RNA (MS2 system) is sufficient to downregulate target RNA
- Favipiravir chase experiments confirm TRIM25 destabilizes IAV mRNAs
- RIG-I/IFN-β pathway activation does NOT require TRIM25 in HEK293 cells (both 5'-ppp RNA and live IAV)
- Cell system: HEK293 human cells, PR8 strain with NS1 R38A/K41A separation-of-function mutant
- Lab: Michlewski (Edinburgh/Warsaw) with Digard (Edinburgh)

**UBR5 Literature Survey:**
- No direct UBR5-influenza papers exist in PubMed
- UBR5 (EDD/hHYD) degrades Sindbis virus RNA polymerase nsP4 via N-end rule pathway (Tasaki et al. 2005, PMID 16055722) — PRECEDENT for viral polymerase targeting
- UBR5 is subverted by HIV-1 Vpr (via DCAF1/VprBP complex), HPV E6 (via E6AP), HHV-6 U14 — frequent viral target
- 300 kDa HECT-domain E3 with UBR box for N-degron recognition

**D'Cruz et al. 2013 (PMID 24015671) — TRIM25 PRY/SPRY structure:**
- 1.8 Å crystal structure of TRIM25 B30.2 domain
- D488 and W621 critical for RIG-I CARD binding
- This protein-protein interface is DISTINCT from the RNA-binding residues (470-508)

## Synthesis v3 — Key Updates

**New hypothesis: H_cryptic_rbd**
TRIM25 possesses an uncharacterized RNA-binding surface distinct from the known PRY/SPRY RBD (residues 470-508). The evidence: ΔRBD mutant retains viral RNA binding and antiviral activity. This cryptic surface is the leading candidate for mediating TRIM25-dependent RdRp pausing observed by TenVIP-seq.

**Strengthened: H_rna (TRIM25 pausing via RNA-binding)**
The cryptic RNA-binding surface + tethering sufficiency result from Choudhury 2022 provides a plausible mechanism: TRIM25 binds viral RNA templates through this uncharacterized surface and physically impedes RdRp elongation. Key test: TRIM25 ΔRBD reconstitution + TenVIP-seq.

**Strengthened: H_ubr5 (UBR5 mediates RdRp pausing)**
UBR5's demonstrated ability to degrade Sindbis virus RNA polymerase nsP4 via N-degron recognition establishes direct precedent for UBR5 targeting viral polymerases. Combined with PB2 interaction in Krogan interactome, this makes UBR5 a credible candidate for IAV RdRp ubiquitination-mediated pausing.

**Speculative connection noted:**
If the TRIM25 coiled-coil domain harbors the cryptic RNA-binding surface, then NS1 binding (which targets the coiled-coil via E96/E97) would simultaneously block BOTH RIG-I ubiquitination AND RNA-dependent pausing — an elegant dual-inhibition mechanism. This is testable.

## Revised Hypothesis Tracking

| Hypothesis | v2 Status | v3 Status | Key New Evidence |
|---|---|---|---|
| H_direct: TRIM25-RdRp binding | WEAKENED | WEAKENED | (unchanged) |
| H_rna: TRIM25 pausing via RNA | SUPPORTED | STRENGTHENED | Cryptic RNA surface; tethering sufficient |
| H_ubr5: UBR5 mediates pausing | NEW | STRENGTHENED | Sindbis nsP4 degradation precedent |
| H_chain: Pausing → mvRNA → RIG-I | PARTIAL | PARTIAL | (unchanged) |
| H_cryptic_rbd: Cryptic RNA surface | — | NEW | ΔRBD still binds RNA & inhibits IAV |

## Networks Published/Updated

| Network | UUID | Action | Nodes | Edges |
|---|---|---|---|---|
| Synthesis v3 | 820fefc6-2536-11f1-94e8-005056ae3c32 | CREATED | 27 | 31 |
| Episodic memory | 8498f3f2-1ff9-11f1-94e8-005056ae3c32 | UPDATED | 6 | 5 |
| Plans and priorities | 847fc69e-1ff9-11f1-94e8-005056ae3c32 | UPDATED | 11 | 9 |

All networks set to PUBLIC visibility.

## Next Priorities

1. **Identify cryptic RNA-binding surface location** — check TRIM25 domain mapping, AlphaFold, crosslinking-MS data
2. **Test coiled-coil/RNA hypothesis** — if NS1 binding site overlaps cryptic RNA surface, elegant dual-inhibition
3. **Map NS1/NP temporal expression** — constrain which evasion axes operate when during infection
4. **Update collaborator map** — add Michlewski, Mehle, te Velthuis, Magor, Digard labs
5. **Build experimental design network** — formalize all proposed experiments as structured network

## Lessons Learned

- Deep-reading a single paper (Choudhury 2022) yielded more model-advancing insight than scanning many abstracts — the ΔRBD result was buried in the methods but fundamentally changes our understanding of TRIM25's mechanism
- Negative literature results (no UBR5-IAV papers) combined with cross-virus precedent (Sindbis nsP4) is a powerful approach for hypothesis building
- The model is converging on a picture where TRIM25's antiviral role is primarily RNA-mediated rather than ubiquitin-mediated, which inverts the traditional paradigm
