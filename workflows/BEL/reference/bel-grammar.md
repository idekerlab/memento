# BEL Grammar Reference

Reference material for agents authoring BEL statements. Use with `SKILL.md` (the protocol) and `bel-examples.md` (worked examples).

Source: condensed and corrected from `../bel_prompt.md`. Cleanups applied:
- Removed `challenges` as a relation (not in BEL spec)
- Normalized `GO:` as the canonical GO namespace (sub-namespaces `GOBP:` / `GOMF:` / `GOCC:` are accepted but not required)
- Fixed example using numeric HGNC ID to use symbol

---

## Functions (entity constructors)

| Function | Short | Purpose | Example |
|---|---|---|---|
| `abundance` | `a()` | General / small molecule / metabolite | `a(CHEBI:thapsigargin)` |
| `geneAbundance` | `g()` | Gene (DNA) | `g(HGNC:TP53)` |
| `rnaAbundance` | `r()` | RNA | `r(HGNC:AKT1)` |
| `microRNAAbundance` | `m()` | Processed microRNA | `m(HGNC:MIR21)` |
| `proteinAbundance` | `p()` | Protein | `p(HGNC:AKT1)` |
| `complexAbundance` | `complex()` | Named complex or list of components | `complex(p(HGNC:FOS), p(HGNC:JUN))` |
| `compositeAbundance` | `composite()` | Multiple abundances synergizing; subject-only | `composite(p(HGNC:IL6), complex(GO:"IL-23 complex"))` |
| `biologicalProcess` | `bp()` | Process or event population | `bp(GO:apoptosis)` |
| `pathology` | `path()` | Disease or pathological process | `path(DOID:cancer)` |
| `activity` | `act()` | Molecular activity of an abundance | `act(p(HGNC:AKT1))` |
| `molecularActivity` | `ma()` | Activity-type argument for `act()` | `act(p(HGNC:AKT1), ma(kin))` |
| `reaction` | `rxn()` | Reactants → products | `rxn(reactants(a(CHEBI:superoxide)), products(a(CHEBI:"hydrogen peroxide")))` |
| `translocation` | `tloc()` | Movement between cellular locations | `tloc(p(HGNC:EGFR), fromLoc(GO:"cell surface"), toLoc(GO:endosome))` |
| `cellSecretion` | `sec()` | Shorthand for translocation to extracellular space | `sec(p(HGNC:RETN))` |
| `cellSurfaceExpression` | `surf()` | Shorthand for translocation to cell surface | `surf(p(HGNC:GPER1))` |
| `degradation` | `deg()` | Destruction of an abundance (e.g. proteasomal) | `deg(p(HGNC:MYC))` |
| `location` | `loc()` | Location subset within an abundance | `a(CHEBI:"calcium(2+)", loc(GO:"endoplasmic reticulum"))` |

## Modifiers (inner constructors)

Used inside the abundance functions above.

| Modifier | Short | Purpose | Example |
|---|---|---|---|
| `proteinModification` | `pmod()` | PTM on a protein | `p(HGNC:AKT1, pmod(Ph, S, 473))` |
| `variant` | `var()` | Sequence variant (within `g()` / `r()` / `p()` / `m()`) | `p(HGNC:TP53, var("p.Arg175His"))` |
| `fragment` | `frag()` | Protein fragment (within `p()`) | `p(HGNC:AKT1, frag("1-100"))` |
| `fusion` | `fus()` | Fusion gene/transcript/protein (replaces namespace:value) | `r(fus(HGNC:TMPRSS2, "r.1_79", HGNC:ERG, "r.312_5034"))` |

## Protein modification labels (default BEL namespace)

Used as the `type` argument of `pmod()`.

| Label | Modification |
|---|---|
| `Ac` | acetylation |
| `ADPRib` | ADP-ribosylation |
| `Farn` | farnesylation |
| `Gerger` | geranylgeranylation |
| `Glyco` / `NGlyco` / `OGlyco` | glycosylation (general / N-linked / O-linked) |
| `Hy` | hydroxylation |
| `ISG` | ISGylation |
| `Me` / `Me1` / `Me2` / `Me3` | methylation (general / mono / di / tri) |
| `Myr` | myristoylation |
| `Nedd` | neddylation |
| `NO` | nitrosylation |
| `Palm` | palmitoylation |
| `Ph` | phosphorylation |
| `Sulf` | sulfation |
| `Sumo` | SUMOylation |
| `Ub` / `UbK48` / `UbK63` / `UbMono` / `UbPoly` | ubiquitination (general / K48 / K63 / mono / poly) |

Form: `pmod(type, residue, position)` — residue and position are optional. Residue may be 1-letter (`S`) or 3-letter (`Ser`) amino acid code.

Examples:
- `p(HGNC:AKT1, pmod(Ph, S, 473))` — phosphorylated at Ser473
- `p(HGNC:MAPK1, pmod(Ph, Thr, 185), pmod(Ph, Tyr, 187))` — doubly phosphorylated
- `p(HGNC:HRAS, pmod(Palm))` — palmitoylated at an unspecified residue

## Relations

Causal (between abundances / activities / processes):

| Relation | Long form | Meaning |
|---|---|---|
| `=>` | `directlyIncreases` | A directly increases B (e.g. direct binding, phosphorylation) |
| `=\|` | `directlyDecreases` | A directly decreases B |
| `->` | `increases` | A indirectly increases B |
| `-\|` | `decreases` | A indirectly decreases B |
| `pos` | `positiveCorrelation` | A is positively correlated with B (causality not established) |
| `neg` | `negativeCorrelation` | A is negatively correlated with B |
| `cnc` | `causesNoChange` | A does not affect B |
| (none) | `association` | A is associated with B — weakest causal claim |
| `reg` | `regulates` | A regulates B somehow (direction unspecified) |
| (none) | `rateLimitingStepOf` | A is a rate-limiting step of B |

Structural:

| Relation | Meaning |
|---|---|
| `hasComponent` | A has component B (complexes) |
| `hasComponents` | A has components list(B, C, D, ...) |
| `hasMember` | A has member B |
| `hasMembers` | A has members list(B, C, D, ...) |
| `hasActivity` | A has activity B |
| `isA` | A is a subset of B |
| `subProcessOf` | A is a subprocess of B |
| `orthologous` | A is orthologous to B |
| `transcribedTo` / `:>` | gene → RNA |
| `translatedTo` / `>>` | RNA → protein |

## Notes on usage by agents

- Prefer short forms (`p()`, `a()`, `=>`) in authored statements — they're canonical and more compact in network storage.
- A statement's canonical form uses identical arguments throughout — `p(HGNC:AKT1)` always refers to the same entity regardless of where it appears. Dedupe on canonical form, not string match.
- When direct-vs-indirect evidence is unclear, use `increases` / `decreases` (indirect) rather than `directlyIncreases` / `directlyDecreases`. Under-claiming is the safer default.
- `association` is the weakest causal claim and acceptable when a paper reports co-occurrence without mechanism.
- For correlation claims without established causal direction, use `positiveCorrelation` / `negativeCorrelation` rather than forcing a direction with `increases` / `decreases`.
