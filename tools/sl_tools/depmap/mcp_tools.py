"""DepMap MCP tool definitions for the sl-tools unified server."""

import math

from .. import _config
from ..registry import register_plugin
from .client import CN_GAIN_THRESHOLD, CN_LOSS_THRESHOLD, DepMapClient, mann_whitney_u

_client: DepMapClient | None = None


def _get_client() -> DepMapClient:
    global _client
    if _client is None:
        _client = DepMapClient(version=_config.depmap_version)
        _client.load_sample_info()
    return _client


def _ensure_loaded(
    mutations=False,
    gene_effect=False,
    expression=False,
    copy_number=False,
):
    """Ensure required data is loaded on the client."""
    c = _get_client()
    if mutations and c.mutations is None:
        c.load_mutations()
    if gene_effect and c.gene_effect is None:
        c.load_gene_effect()
    if expression and c.expression is None:
        c.load_expression()
    if copy_number and c.copy_number is None:
        c.load_copy_number()
    return c


def register(mcp_app):
    """Register all DepMap tools on the MCP app."""

    register_plugin(
        "depmap",
        check_coverage_fn=lambda genes: _get_client().check_gene_coverage(genes),
        ensure_data_fn=lambda: _get_client().ensure_data(),
    )

    # --- Data management ---

    @mcp_app.tool()
    def mcp_ensure_data() -> dict:
        """Check that required DepMap data files exist locally. Returns status per file."""
        return _get_client().ensure_data()

    @mcp_app.tool()
    def mcp_check_gene_coverage(genes: list[str]) -> dict:
        """
        Check which genes have data in DepMap (anti-hallucination check).
        Returns per-gene availability in CRISPR, mutation, and CNV datasets.
        """
        return _get_client().check_gene_coverage(genes)

    @mcp_app.tool()
    def mcp_get_data_version() -> dict:
        """Get DepMap version and list of data files present locally."""
        return _get_client().get_data_version()

    @mcp_app.tool()
    def mcp_get_version_info() -> dict:
        """Get detailed version metadata for methods sections and reproducibility."""
        return _get_client().get_version_info()

    # --- Dependency scores ---

    @mcp_app.tool()
    def mcp_get_dependency_scores(gene: str, cell_lines: list[str] | None = None) -> dict:
        """
        Get CRISPR dependency scores for a gene across cell lines.
        More negative = more dependent. Returns {cell_line: score}.
        """
        c = _ensure_loaded(gene_effect=True)
        return c.get_dependency_scores(gene, cell_lines=cell_lines)

    @mcp_app.tool()
    def mcp_get_unique_vulnerabilities(sample: str, cutoff: float = -1.0) -> list[str]:
        """
        Get genes that a specific cell line is uniquely dependent on
        (gene effect < cutoff, default -1.0).
        """
        c = _ensure_loaded(gene_effect=True)
        return c.get_unique_vulnerabilities(sample, cutoff=cutoff).tolist()

    # --- Mutations ---

    @mcp_app.tool()
    def mcp_get_cell_lines_with_mutation(gene: str) -> list[str]:
        """Get cell lines with LikelyLoF somatic mutations in a gene."""
        c = _ensure_loaded(mutations=True)
        return c.get_cell_lines_with_mutation(gene)

    @mcp_app.tool()
    def mcp_get_cell_lines_without_mutation(gene: str) -> list[str]:
        """Get cell lines without mutations in a gene."""
        c = _ensure_loaded(mutations=True, gene_effect=True)
        return c.get_cell_lines_without_mutation(gene)

    # --- Copy number ---

    @mcp_app.tool()
    def mcp_has_cnv_data() -> bool:
        """Check if CNV data file (OmicsCNGene.csv) is available."""
        return _get_client().has_cnv_data()

    @mcp_app.tool()
    def mcp_get_cnv_value(gene: str, cell_line: str) -> float | None:
        """Get log2(relative copy number) for a gene in a specific cell line."""
        c = _ensure_loaded(copy_number=True)
        return c.get_cnv_value(gene, cell_line)

    @mcp_app.tool()
    def mcp_get_cnv_values(gene: str, cell_lines: list[str] | None = None) -> dict:
        """Get log2(CN) values for a gene across cell lines. Returns {cell_line: value}."""
        c = _ensure_loaded(copy_number=True)
        return c.get_cnv_values(gene, cell_lines=cell_lines)

    @mcp_app.tool()
    def mcp_get_cell_lines_with_cn_loss(
        gene: str, threshold: float = CN_LOSS_THRESHOLD, deep_only: bool = False
    ) -> list[str]:
        """
        Get cell lines with copy number loss for a gene.
        Default threshold: -1.0 (log2 scale). Set deep_only=True for threshold -2.0.
        """
        c = _ensure_loaded(copy_number=True)
        return c.get_cell_lines_with_cn_loss(gene, threshold=threshold, deep_only=deep_only)

    @mcp_app.tool()
    def mcp_get_cell_lines_with_cn_gain(
        gene: str, threshold: float = CN_GAIN_THRESHOLD, amplification_only: bool = False
    ) -> list[str]:
        """
        Get cell lines with copy number gain for a gene.
        Default threshold: 0.58. Set amplification_only=True for threshold 1.0.
        """
        c = _ensure_loaded(copy_number=True)
        return c.get_cell_lines_with_cn_gain(
            gene, threshold=threshold, amplification_only=amplification_only
        )

    @mcp_app.tool()
    def mcp_get_cell_lines_with_robust_cn_loss(gene: str) -> dict:
        """
        Get cell lines with robust copy number loss for a gene.
        Robust CN loss requires BOTH: CN < 1 (normalized) AND expression below
        the 25th percentile. This avoids counting CN losses not reflected in
        expression, matching the reference implementation.

        Returns:
            robust_cn_loss: list of cell line names with robust CN loss
            no_robust_cn_loss: list of cell line names without robust CN loss
            n_robust_cn_loss: count
            n_no_robust_cn_loss: count
        """
        c = _ensure_loaded(gene_effect=True, expression=True, copy_number=True)
        return c.get_cell_lines_with_robust_cn_loss(gene)

    @mcp_app.tool()
    def mcp_get_cell_lines_with_disruption(
        gene: str,
        include_mutations: bool = True,
        include_cn_loss: bool = True,
        cn_loss_threshold: float = CN_LOSS_THRESHOLD,
    ) -> list[str]:
        """Get cell lines with gene disruption (mutation OR copy number loss)."""
        c = _get_client()
        return c.get_cell_lines_with_disruption(
            gene,
            include_mutations=include_mutations,
            include_cn_loss=include_cn_loss,
            cn_loss_threshold=cn_loss_threshold,
        )

    @mcp_app.tool()
    def mcp_get_cell_lines_without_disruption(
        gene: str,
        include_mutations: bool = True,
        include_cn_loss: bool = True,
    ) -> list[str]:
        """Get cell lines without gene disruption (no mutation AND no CN loss)."""
        c = _get_client()
        return c.get_cell_lines_without_disruption(
            gene,
            include_mutations=include_mutations,
            include_cn_loss=include_cn_loss,
        )

    @mcp_app.tool()
    def mcp_get_disrupted_cell_lines(gene: str) -> dict:
        """
        Get cell lines where a gene is disrupted using the rigorous definition:
        LikelyLoF point mutation/indel OR (copy number loss AND under-expressed
        relative to population median).

        This matches the methodology: deleterious mutations are identified via
        LikelyLoF annotations. Robust copy number loss requires BOTH CN < 1
        (normalized) AND expression below the 25th percentile.

        Requires mutation, expression, and copy number data to all be available.

        Returns:
            disrupted: list of cell line names where gene is disrupted
            not_disrupted: list of cell line names where gene is intact
            n_disrupted: count of disrupted cell lines
            n_not_disrupted: count of intact cell lines
        """
        c = _ensure_loaded(mutations=True, gene_effect=True, expression=True, copy_number=True)
        if c.disrupted is None:
            c.load_disrupted()
        c.use_cell_line_names_as_id()

        if gene not in c.disrupted.columns:
            return {
                "error": f"Gene '{gene}' not found in disruption matrix",
                "disrupted": [],
                "not_disrupted": [],
                "n_disrupted": 0,
                "n_not_disrupted": 0,
            }

        disrupted_mask = c.disrupted[gene].fillna(False).astype(bool)
        all_crispr = set(c.gene_effect.index)
        disrupted_lines = set(disrupted_mask[disrupted_mask].index) & all_crispr
        not_disrupted_lines = all_crispr - disrupted_lines

        return {
            "disrupted": sorted(disrupted_lines),
            "not_disrupted": sorted(not_disrupted_lines),
            "n_disrupted": len(disrupted_lines),
            "n_not_disrupted": len(not_disrupted_lines),
        }

    # --- Stratification ---

    @mcp_app.tool()
    def mcp_split_samples_by_mutations(
        mutated_genes: list[str],
        deleterious_only: bool = False,
        hotspot_only: bool = False,
    ) -> dict:
        """
        Split cell lines by mutation status from full mutations file.
        Returns {"mutated": [...], "not_mutated": [...]}.
        """
        c = _ensure_loaded(mutations=True)
        c.use_cell_line_names_as_id()
        mutated, not_mutated = c.split_samples_by_mutations(
            mutated_genes, deleterious_only=deleterious_only, hotspot_only=hotspot_only
        )
        return {"mutated": mutated.tolist(), "not_mutated": not_mutated.tolist()}

    @mcp_app.tool()
    def mcp_split_samples_by_expression(
        gene: str, lower_pct: int = 50, upper_pct: int = 50
    ) -> dict:
        """
        Split cell lines by expression percentile.
        Returns {"under_expressing": [...], "over_expressing": [...]}.
        """
        c = _ensure_loaded(expression=True)
        c.use_cell_line_names_as_id()
        under, over = c.split_samples_by_expression(gene, lower_pct=lower_pct, upper_pct=upper_pct)
        return {"under_expressing": under.tolist(), "over_expressing": over.tolist()}

    @mcp_app.tool()
    def mcp_filter_samples_by_lineage(lineage: str, samples: list[str] | None = None) -> list[str]:
        """
        Get cell lines belonging to a cancer lineage (e.g. "Breast", "Lung").
        Optionally intersect with a provided sample list.
        """
        c = _get_client()
        result = c.filter_samples_by_lineage(lineage, samples=samples)
        return result.tolist()

    # --- ID translation ---

    @mcp_app.tool()
    def mcp_translate_to_sanger_ids(depmap_ids: list[str]) -> list[str]:
        """Translate DepMap IDs (ACH-*) to Sanger Model IDs (SIDM*) for GDSC integration."""
        return _get_client().translate_to_sanger_ids(depmap_ids)

    @mcp_app.tool()
    def mcp_translate_from_sanger_ids(sanger_ids: list[str]) -> list[str]:
        """Translate Sanger Model IDs (SIDM*) to DepMap IDs (ACH-*)."""
        return _get_client().translate_from_sanger_ids(sanger_ids)

    # --- Statistical tests ---

    @mcp_app.tool()
    def mcp_mann_whitney_u(
        group_a: list[float],
        group_b: list[float],
    ) -> dict:
        """
        One-tailed Mann-Whitney U test: is group_a lower than group_b?

        Use for synthetic lethality testing: pass mutant dependency scores as
        group_a and wildtype scores as group_b. A significant result (p < 0.05)
        with negative effect_size means mutants are more dependent.

        Returns:
            p_value: one-tailed p-value (alternative='less')
            effect_size: median(group_a) - median(group_b)
            median_a: median of group_a
            median_b: median of group_b
            n_a: sample size of group_a
            n_b: sample size of group_b
        """
        import statistics as stats_mod

        group_a = [v for v in group_a if not math.isnan(v)]
        group_b = [v for v in group_b if not math.isnan(v)]

        p_value = mann_whitney_u(group_a, group_b)
        median_a = stats_mod.median(group_a) if group_a else None
        median_b = stats_mod.median(group_b) if group_b else None
        effect_size = (
            (median_a - median_b) if (median_a is not None and median_b is not None) else None
        )

        return {
            "p_value": p_value,
            "effect_size": effect_size,
            "median_a": median_a,
            "median_b": median_b,
            "n_a": len(group_a),
            "n_b": len(group_b),
        }

    @mcp_app.tool()
    def mcp_spearman_correlation(
        values_a: list[float],
        values_b: list[float],
    ) -> dict:
        """
        Spearman rank correlation between two paired numeric vectors.

        Use for testing dosage-sensitive relationships, e.g. whether copy number
        of gene_a correlates with dependency on gene_b across cell lines.

        Both lists must be the same length and represent matched observations
        (same cell lines in the same order).

        Returns:
            spearman_r: Spearman correlation coefficient (-1 to 1)
            p_value: two-tailed p-value for testing H0: no monotonic association
            n_samples: number of paired observations
        """
        if len(values_a) != len(values_b):
            return {
                "error": f"Length mismatch: values_a has {len(values_a)}, values_b has {len(values_b)}"
            }

        paired = [
            (a, b) for a, b in zip(values_a, values_b) if not math.isnan(a) and not math.isnan(b)
        ]
        if len(paired) < 3:
            return {
                "error": f"Need at least 3 paired observations after dropping NaNs, got {len(paired)}"
            }
        values_a, values_b = zip(*paired)

        from scipy.stats import spearmanr

        r, p = spearmanr(values_a, values_b)

        if math.isnan(r):
            return {
                "spearman_r": None,
                "p_value": None,
                "n_samples": len(values_a),
                "error": "Correlation undefined — one or both arrays are constant",
            }

        return {
            "spearman_r": float(r),
            "p_value": float(p),
            "n_samples": len(values_a),
        }

    # --- Composite tools ---

    @mcp_app.tool()
    def mcp_test_sl_pair(
        gene_a: str,
        gene_b: str,
        method: str = "disruption",
        lineage: str | None = None,
    ) -> dict:
        """
        Test a synthetic lethality pair end-to-end, server-side.

        Stratifies cell lines by gene_a status, gets gene_b CRISPR dependency
        scores for each group, and runs a one-tailed Mann-Whitney U test.
        Returns only summary statistics — no raw scores or cell line lists
        are serialized.

        Use this instead of manually chaining mcp_get_disrupted_cell_lines →
        mcp_get_dependency_scores → mcp_mann_whitney_u, which floods context
        with thousands of intermediate values.

        Args:
            gene_a: The partner gene (stratified by loss/alteration)
            gene_b: The target gene (tested for CRISPR dependency)
            method: How to stratify cell lines by gene_a:
                "disruption" - deleterious mutation OR robust CN loss (default)
                "mutation" - any somatic mutation (LikelyLoF)
                "cn_loss" - robust CN loss (CN < 1 AND under-expressed)
                "expression" - low vs high expression (median split)
                "cn_gain" - copy number gain (threshold 0.58)
                "mutation_hotspot" - hotspot mutations only
                "mutation_deleterious" - deleterious mutations only
            lineage: Optional cancer lineage filter (e.g. "Breast", "Lung")

        Returns:
            gene_a, gene_b, method, lineage: echo inputs
            p_value: one-tailed p-value (alternative='less')
            effect_size: median(altered) - median(intact), negative = more dependent
            median_altered, median_intact: group medians
            n_altered, n_intact: sample sizes
            warning: present if n_altered < 25 (low statistical power)
        """
        import statistics as stats_mod

        from .._json_utils import sanitize_floats

        # --- Stratify by method ---
        if method == "disruption":
            c = _ensure_loaded(mutations=True, gene_effect=True, expression=True, copy_number=True)
            if c.disrupted is None:
                c.load_disrupted()
            c.use_cell_line_names_as_id()
            if gene_a not in c.disrupted.columns:
                return {"error": f"Gene '{gene_a}' not found in disruption matrix", "p_value": None}
            mask = c.disrupted[gene_a].fillna(False).astype(bool)
            all_crispr = set(c.gene_effect.index)
            altered = sorted(set(mask[mask].index) & all_crispr)
            intact = sorted(all_crispr - set(altered))

        elif method == "mutation":
            c = _ensure_loaded(mutations=True, gene_effect=True)
            c.use_cell_line_names_as_id()
            altered = c.get_cell_lines_with_mutation(gene_a)
            intact = c.get_cell_lines_without_mutation(gene_a)

        elif method in ("mutation_hotspot", "mutation_deleterious"):
            c = _ensure_loaded(mutations=True, gene_effect=True)
            c.use_cell_line_names_as_id()
            hotspot = method == "mutation_hotspot"
            deleterious = method == "mutation_deleterious"
            mutated, not_mutated = c.split_samples_by_mutations(
                [gene_a],
                hotspot_only=hotspot,
                deleterious_only=deleterious,
            )
            altered = mutated.tolist()
            intact = not_mutated.tolist()

        elif method == "cn_loss":
            c = _ensure_loaded(gene_effect=True, expression=True, copy_number=True)
            c.use_cell_line_names_as_id()
            result = c.get_cell_lines_with_robust_cn_loss(gene_a)
            altered = result["robust_cn_loss"]
            intact = result["no_robust_cn_loss"]

        elif method == "expression":
            c = _ensure_loaded(gene_effect=True, expression=True)
            c.use_cell_line_names_as_id()
            under, over = c.split_samples_by_expression(gene_a)
            altered = under.tolist()
            intact = over.tolist()

        elif method == "cn_gain":
            c = _ensure_loaded(gene_effect=True, copy_number=True)
            c.use_cell_line_names_as_id()
            altered = c.get_cell_lines_with_cn_gain(gene_a)
            all_crispr = set(c.gene_effect.index)
            intact = sorted(all_crispr - set(altered))

        else:
            return {
                "error": f"Unknown method '{method}'. Valid: disruption, mutation, "
                "cn_loss, expression, cn_gain, mutation_hotspot, mutation_deleterious",
                "p_value": None,
            }

        # --- Optional lineage filter ---
        if lineage:
            altered = c.filter_samples_by_lineage(lineage, samples=altered).tolist()
            intact = c.filter_samples_by_lineage(lineage, samples=intact).tolist()

        # --- Check sample sizes ---
        base_result = {
            "gene_a": gene_a,
            "gene_b": gene_b,
            "method": method,
            "lineage": lineage,
            "n_altered": len(altered),
            "n_intact": len(intact),
        }

        if len(altered) == 0:
            return {
                **base_result,
                "error": f"No altered cell lines found for {gene_a}",
                "p_value": None,
            }

        # --- Get dependency scores ---
        scores_altered = c.get_dependency_scores(gene_b, cell_lines=altered)
        scores_intact = c.get_dependency_scores(gene_b, cell_lines=intact)

        if "error" in scores_altered:
            return {**base_result, "error": scores_altered["error"], "p_value": None}

        group_a = [v for v in scores_altered.values() if not math.isnan(v)]
        group_b = [v for v in scores_intact.values() if not math.isnan(v)]

        base_result["n_altered"] = len(group_a)
        base_result["n_intact"] = len(group_b)

        if len(group_a) < 5 or len(group_b) < 5:
            return {
                **base_result,
                "error": f"Insufficient samples (n_altered={len(group_a)}, n_intact={len(group_b)})",
                "p_value": None,
            }

        # --- Statistical test ---
        p_value = mann_whitney_u(group_a, group_b)
        median_a = stats_mod.median(group_a)
        median_b = stats_mod.median(group_b)

        result = {
            **base_result,
            "p_value": p_value,
            "effect_size": median_a - median_b,
            "median_altered": median_a,
            "median_intact": median_b,
        }

        if len(group_a) < 25:
            result["warning"] = "low_power"

        return sanitize_floats(result)

    @mcp_app.tool()
    def mcp_test_cn_correlation(
        gene_a: str,
        gene_b: str,
        lineage: str | None = None,
    ) -> dict:
        """
        Test if copy number of gene_a correlates with CRISPR dependency on
        gene_b, server-side. Computes Spearman correlation without serializing
        raw vectors to context.

        Use this instead of manually chaining mcp_get_cnv_values →
        mcp_get_dependency_scores → mcp_spearman_correlation.

        Args:
            gene_a: Gene whose copy number is measured
            gene_b: Gene whose CRISPR dependency is measured
            lineage: Optional cancer lineage filter (e.g. "Breast")

        Returns:
            gene_a, gene_b, lineage: echo inputs
            spearman_r: correlation coefficient (-1 to 1)
            p_value: two-tailed p-value
            n_samples: number of matched cell lines
        """
        from scipy.stats import spearmanr

        from .._json_utils import sanitize_floats

        c = _ensure_loaded(gene_effect=True, copy_number=True)
        c.use_cell_line_names_as_id()

        if not c.has_cnv_data():
            return {"error": "CNV data not available", "p_value": None}

        cnv_values = c.get_cnv_values(gene_a)
        dep_scores = c.get_dependency_scores(gene_b)

        if "error" in cnv_values:
            return {"error": cnv_values["error"], "p_value": None}
        if "error" in dep_scores:
            return {"error": dep_scores["error"], "p_value": None}

        # Match cell lines present in both datasets
        common = set(cnv_values.keys()) & set(dep_scores.keys())

        # Optional lineage filter
        if lineage:
            lineage_lines = set(c.filter_samples_by_lineage(lineage, samples=list(common)).tolist())
            common = common & lineage_lines

        # Build paired lists, dropping NaNs
        paired = [
            (cnv_values[cl], dep_scores[cl])
            for cl in common
            if not math.isnan(cnv_values[cl]) and not math.isnan(dep_scores[cl])
        ]

        if len(paired) < 3:
            return {
                "error": f"Need at least 3 paired observations, got {len(paired)}",
                "gene_a": gene_a,
                "gene_b": gene_b,
                "lineage": lineage,
                "p_value": None,
            }

        cn_vals, dep_vals = zip(*paired)
        r, p = spearmanr(cn_vals, dep_vals)

        if math.isnan(r):
            return sanitize_floats(
                {
                    "gene_a": gene_a,
                    "gene_b": gene_b,
                    "lineage": lineage,
                    "spearman_r": None,
                    "p_value": None,
                    "n_samples": len(paired),
                    "error": "Correlation undefined — one or both arrays are constant",
                }
            )

        return sanitize_floats(
            {
                "gene_a": gene_a,
                "gene_b": gene_b,
                "lineage": lineage,
                "spearman_r": float(r),
                "p_value": float(p),
                "n_samples": len(paired),
            }
        )
