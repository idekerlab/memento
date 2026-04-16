# BEL → GO-CAM Mapping (stub)

**Status: stub.** Full mapping work is Phase C of the rzenith curator evolution plan (`ndexbio/project/rzenith_curation_and_bel_plan.md`). This file exists so SKILL.md can point agents at it and so agents have initial expectations about which of their authored BEL will survive in a GO-CAM export.

When the real translator is built (`tools/bel_gocam/`), this document becomes the human-readable specification backing it.

---

## Premise

BEL is the authoring representation. GO-CAM is a downstream view for ecosystem interop (Chris Mungall / GO / Noctua consumers). The mapping is lossy in a controlled, documented way — some BEL constructs map cleanly, some map with loss, some don't map at all.

Goal of this document: tell an authoring agent *which BEL patterns will render faithfully in the GO-CAM view and which will not*, so the agent can make informed representation choices at authoring time.

---

## Clean mappings (render without loss)

These BEL patterns have direct GO-CAM equivalents.

| BEL pattern | GO-CAM pattern |
|---|---|
| `act(p(HGNC:X)) directlyIncreases act(p(HGNC:Y))` | Activity enabled by X → `directly positively regulates` → activity enabled by Y |
| `act(p(HGNC:X)) directlyDecreases act(p(HGNC:Y))` | Activity enabled by X → `directly negatively regulates` → activity enabled by Y |
| `act(p(HGNC:X)) increases bp(GO:"P")` | Activity enabled by X → `positively regulates` → process P |
| `bp(GO:"A") subProcessOf bp(GO:"B")` | A `part of` B (BP hierarchy) |
| `p(HGNC:X) isA p(FPLX:"Family")` | X `in taxon` / family membership (via separate annotation) |
| `complex(p(HGNC:X), p(HGNC:Y))` | GO-CAM complex node with `has part` → X, `has part` → Y |
| `act(p(HGNC:X), ma(GO:"kinase activity"))` | Activity enabled by X with explicit MF term |
| Cellular location via `loc(GO:...)` | GO-CAM `occurs in` annotation |

## Lossy mappings (render with flag)

These are representable in GO-CAM but lose detail.

| BEL pattern | GO-CAM handling | What's lost |
|---|---|---|
| `p(HGNC:X, pmod(Ph, S, n)) directlyIncreases ...` | Activity enabled by X, with separate annotation noting "regulated by phosphorylation" | Site specificity (S, n) collapsed; GO-CAM doesn't natively carry residue/position |
| `deg(p(HGNC:X))` | Process `protein catabolic process` with X as input | The BEL causal chain (`deg() directlyDecreases abundance`) is implied but not explicit |
| `tloc(X, fromLoc(A), toLoc(B))` | Activity with `occurs in` annotations but transport direction is awkward | The from/to pair becomes two separate location annotations |
| `p(HGNC:X) isA act(GO:"kinase activity")` when the paper only claims activity type | Activity enabled by X with MF = kinase activity | The underlying relation (`isA` vs `hasActivity`) is flattened |

Flag in translator output: `{gocam: ..., lossy: true, lost_info: ["modification_site"]}`.

## Constructs that do not map

These BEL patterns are marked BEL-only in the GO-CAM view and omitted from the export.

| BEL pattern | Why no GO-CAM equivalent |
|---|---|
| `positiveCorrelation`, `negativeCorrelation` | GO-CAM is causal; correlation is explicitly out of scope |
| `causesNoChange` | Negative findings are not represented in GO-CAM |
| `association` | Too weak — GO-CAM requires causal direction |
| `a(CHEBI:"...") abundance claims` when the claim is about levels, not activity | GO-CAM does not model abundances as first-class |
| `composite(X, Y, Z) increases ...` | GO-CAM does not model synergistic composites |
| `var(...)` variants | GO-CAM models wild-type activities; variant-specific claims are out of scope |
| `frag(...)`, `fus(...)` | Same |
| `pathology()` claims in isolation | Diseases are represented differently in GO-CAM ecosystem (not as causal nodes) |
| Freeform claim nodes (from namespace-policy.md fallback 3) | Not BEL, not GO-CAM — inherently outside scope |

## Authoring implications

If you are authoring an edge and care about GO-CAM renderability:

- **Prefer `act()` on both sides of causal relations.** `act(p(HGNC:X)) directlyIncreases act(p(HGNC:Y))` is the cleanest GO-CAM pattern.
- **Use `bp(GO:...)` for process-level claims.** Direct GO-CAM equivalent.
- **Accept that PTM-specific edges will be lossy** in GO-CAM. Don't avoid authoring them — just know the export will collapse them.
- **Do not avoid `positiveCorrelation` / `association` when they're honest.** These won't make it into the GO-CAM view, and that's correct — GO-CAM shouldn't contain claims weaker than its vocabulary supports.

## Translator output contract (draft)

For a given BEL statement, the translator will return one of:

```
{ status: "mapped",   gocam: <structured output>, lossy: false }
{ status: "mapped",   gocam: <structured output>, lossy: true,  lost_info: [...] }
{ status: "unmapped", reason: <short string> }
```

Translator will NOT guess or partially render when the mapping is not defined. Better to report unmapped and let the curator decide than to silently distort.

## Open design items (Phase C)

- Decide: BEL evidence annotations (quote, PMID, analysis UUID, scope, tier) — how do these map to GO-CAM's evidence code + reference system? GO-CAM natively supports PMID references and evidence codes; quote and analysis_uuid are extensions.
- Decide: how to handle multi-statement BEL inputs where a single biological event is decomposed into multiple BEL edges. GO-CAM may represent this as a single activity edge.
- Decide: whether the GO-CAM view includes retired (`evidence_status: superseded`) edges — probably not.
- Validate mappings against actual Noctua-consumable GO-CAM models with Chris Mungall's input before committing.
