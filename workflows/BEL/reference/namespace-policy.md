# Namespace Policy

Reference material for entity grounding in BEL authoring. Used by `SKILL.md` step 1.

---

## Approved entity classes and namespaces

| Entity class | Namespace | Scope |
|---|---|---|
| Human genes / proteins | `HGNC` | Approved human gene symbols — prefer for everything human |
| Proteins (all species) | `UniProt` | Use when species matters or HGNC doesn't apply |
| Protein families / complexes | `FPLX` | FamPlex — for named families like "AKT Family", "RAS family" |
| Small molecules / metabolites / drugs | `ChEBI` | Chemical Entities of Biological Interest |
| Biological processes / molecular functions / cellular components | `GO` | Gene Ontology — one root namespace; sub-prefixes `GOBP:` / `GOMF:` / `GOCC:` accepted but not required |
| Diseases | `DOID` | Disease Ontology |
| Experimental factors, cell lines, anatomical entities | `EFO` | Experimental Factor Ontology |
| Human phenotypes | `HP` | Human Phenotype Ontology |

Compatible with GO-CAM view: `HGNC`, `UniProt`, `GO`, `ChEBI`. Partially compatible: `DOID`, `HP`. Not directly mapped to GO-CAM: `FPLX`, `EFO`.

## Precedence rules

When a concept could be represented in more than one namespace:

1. **Human genes / proteins** → `HGNC` (symbol), not `UniProt` ID. `p(HGNC:AKT1)` not `p(UniProt:P31749)`. Use UniProt only for non-human species or when the specific UniProt isoform matters.
2. **Protein families** → `FPLX` when the claim is about the family as a whole (e.g. "AKT activity"). Use the individual HGNC symbol when the paper is specific.
3. **Small molecules** → `ChEBI`, always. Do not use `CAS` or other chemistry namespaces.
4. **Processes** → `GO` with the most specific term that fits the claim. If the paper names a process in freeform ("tumor microenvironment remodeling"), prefer the closest GO term over inventing freeform.
5. **Cellular locations inside `loc()` / `tloc()`** → `GO` (cellular component branch).
6. **Diseases** → `DOID` for specific named diseases. Use `bp(GO:"...")` or `path(DOID:...)` depending on whether the claim is about the process or the disease state.

## Fallback rules when an ID cannot be confidently resolved

Do **not** guess an ID. Hallucinated IDs pollute the graph and are hard to clean up later. Three acceptable fallbacks, in order of preference:

### 1. Use the canonical label with a `deferred_lookup` flag

When you know the entity but not a reliable ID:

```
p(PENDING:"serine/threonine-protein kinase ATR", deferred_lookup(HGNC))
```

The `PENDING` namespace is a placeholder. The `deferred_lookup(<target_namespace>)` annotation signals that a later pass (manual or via a namespace-resolution tool, once one exists) should convert this to a proper ID. The edge is still usable — downstream consumers just know the grounding is incomplete.

### 2. Use a parent term from an adjacent namespace

If the specific term doesn't resolve but a broader term does:

```
bp(GO:"DNA repair")
```

when you can't find the specific `GO:"non-homologous end joining"` ID. Mark this in the edge's `scope` annotation: `scope: "broader_than_source"`.

### 3. Use a freeform claim node

When the concept isn't cleanly a named biological entity at all (e.g. "the inflammatory milieu observed in triple-negative breast cancers"), author a claim node rather than forcing BEL:

```
node_type: "claim"
text: "inflammatory milieu in triple-negative breast cancer"
evidence_*: ...
```

This is preferable to forcing a bad BEL statement. See SKILL.md step 6.

## Anti-patterns to avoid

- **Numeric IDs for HGNC.** Use `HGNC:TP53`, never `HGNC:11998`. The symbol is the canonical form and the numeric ID breaks reader parsing.
- **Mixing namespaces for the same concept across different statements in the same session.** If you represented ATM as `p(HGNC:ATM)` once, use `p(HGNC:ATM)` for every subsequent reference in the same work product.
- **Using `a()` for something that has a specific function (gene / RNA / protein / miRNA).** `a()` is for small molecules and general abundances only. A protein is `p()`, always.
- **Using `GO:"apoptosis"` when you mean "apoptosis of hepatocytes" or similar contextualized version.** If the paper's claim is context-dependent, capture the context in the `scope` annotation, not by inventing a compound term.

## When a namespace-lookup MCP exists

This policy assumes agents ground entities from latent knowledge, which is error-prone for less-common terms. When a namespace-resolution MCP is built (deferred task), the policy simplifies to: "for every entity, call the lookup; if it returns no confident match, use fallback 1 (`PENDING` + `deferred_lookup`); otherwise use the returned ID."
