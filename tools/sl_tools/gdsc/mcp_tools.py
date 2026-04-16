"""GDSC drug sensitivity MCP tool definitions for the sl-tools unified server."""

from dataclasses import asdict

from .._json_utils import sanitize_floats
from ..registry import register_plugin
from .client import GDSCClient

_client: GDSCClient | None = None


def _get_client() -> GDSCClient:
    global _client
    if _client is None:
        _client = GDSCClient()
    return _client


def register(mcp_app):
    """Register all GDSC tools on the MCP app."""

    register_plugin(
        "gdsc",
        check_coverage_fn=None,  # GDSC indexes by drug, not gene
        ensure_data_fn=lambda: _get_client().ensure_data(),
    )

    @mcp_app.tool()
    def mcp_gdsc_ensure_data() -> dict:
        """Ensure GDSC drug sensitivity data files are downloaded and available."""
        return _get_client().ensure_data()

    @mcp_app.tool()
    def mcp_gdsc_get_drugs_targeting_gene(gene: str) -> list[dict]:
        """
        Get drugs that target a specific gene from GDSC.
        Returns list of drug info dicts with drug_id, name, target, pathway.
        """
        drugs = _get_client().get_drugs_targeting_gene(gene)
        return [sanitize_floats(asdict(d)) for d in drugs]

    @mcp_app.tool()
    def mcp_gdsc_get_drug_by_name(drug_name: str) -> dict | None:
        """Get drug info by name from GDSC. Returns drug_id, name, target, pathway or None."""
        drug = _get_client().get_drug_by_name(drug_name)
        if drug is None:
            return None
        return sanitize_floats(asdict(drug))

    @mcp_app.tool()
    def mcp_gdsc_get_ic50_scores(drug_id: int, cell_lines: list[str] | None = None) -> dict:
        """
        Get LN_IC50 scores for a drug across cell lines from GDSC.
        Returns {sanger_model_id: ln_ic50}. Lower = more sensitive.
        """
        return sanitize_floats(_get_client().get_ic50_scores(drug_id, cell_lines=cell_lines))

    @mcp_app.tool()
    def mcp_gdsc_get_auc_scores(drug_id: int, cell_lines: list[str] | None = None) -> dict:
        """
        Get AUC scores for a drug across cell lines from GDSC.
        Returns {sanger_model_id: auc}. Lower AUC = more sensitive to drug.
        """
        return sanitize_floats(_get_client().get_auc_scores(drug_id, cell_lines=cell_lines))

    @mcp_app.tool()
    def mcp_gdsc_get_auc_by_target(target_gene: str, cell_lines: list[str] | None = None) -> dict:
        """
        Get AUC scores pooled across ALL drugs targeting a gene.

        Use this when testing gene-level drug sensitivity (e.g., "are EGFR-disrupted
        cells more sensitive to AURKA-targeting drugs?"). Pools data from every drug
        whose target includes the gene. For cell lines screened against multiple
        drugs, the minimum AUC (most sensitive) is kept.

        For claims about a specific drug (e.g., "cells are sensitive to Alisertib"),
        use mcp_gdsc_get_auc_scores with a drug_id instead.

        Returns {sanger_model_id: auc}. Lower AUC = more sensitive.
        """
        return sanitize_floats(
            _get_client().get_auc_scores_by_target(target_gene, cell_lines=cell_lines)
        )

    @mcp_app.tool()
    def mcp_gdsc_test_target_sensitivity(
        target_gene: str,
        stratification_gene: str,
        metric: str = "auc",
    ) -> dict:
        """
        Test whether cell lines with a disrupted gene are more sensitive to
        drugs targeting another gene. This is the primary tool for testing
        gene-drug synthetic lethality via GDSC.

        Unlike mcp_gdsc_test_drug_sensitivity (single drug), this pools AUC
        across ALL drugs targeting the target_gene, matching standard
        pharmacogenomic analysis methodology.

        Uses disruption (somatic mutation OR robust copy number loss) to
        stratify cell lines, and restricts the universe to cell lines with
        both genomic AND drug response data.

        Args:
            target_gene: Gene whose targeting drugs to test (e.g., "AURKA")
            stratification_gene: Gene to stratify by disruption (e.g., "EGFR")
            metric: "auc" (default, lower = more sensitive) or "ic50"

        Returns:
            p_value: one-tailed p-value (Mann-Whitney U, alternative='less')
            effect_size: median(disrupted) - median(intact)
            median_disrupted, median_intact: group medians
            n_disrupted, n_intact: sample sizes (after universe filtering)
            n_disrupted_premapping: disrupted count before ID translation
            n_drugs_pooled: number of drugs pooled for target_gene
            drugs_used: list of drug names pooled
        """
        import statistics as stats_mod

        from ..depmap.client import mann_whitney_u
        from ..depmap.mcp_tools import _ensure_loaded

        # 1. Get disrupted vs intact cell lines using disruption matrix
        depmap = _ensure_loaded(mutations=True, gene_effect=True, expression=True, copy_number=True)
        if depmap.disrupted is None:
            depmap.load_disrupted()
        depmap.use_cell_line_names_as_id()

        if stratification_gene not in depmap.disrupted.columns:
            return {
                "error": f"Gene '{stratification_gene}' not found in disruption matrix",
                "p_value": None,
                "effect_size": None,
            }

        disrupted_mask = depmap.disrupted[stratification_gene].fillna(False).astype(bool)

        # Build universe: cell lines with disruption data AND mutation data.
        # Mutation universe = all cell lines with ANY somatic mutation record
        # (not just LikelyLoF), so we know their mutation status was assessed.
        # disrupted.index uses cell line names (after use_cell_line_names_as_id),
        # but mutations.ModelID uses ACH-* IDs. Convert to names.
        id_name_map = {v: k for k, v in depmap.name_id_map.items()}
        mutation_universe_names = set(
            id_name_map.get(ach, ach) for ach in depmap.mutations["ModelID"].unique()
        )
        all_genomic = set(depmap.disrupted.index) & mutation_universe_names
        disrupted_names = sorted(set(disrupted_mask[disrupted_mask].index) & all_genomic)
        intact_names = sorted(all_genomic - set(disrupted_names))

        n_disrupted_pre = len(disrupted_names)
        n_intact_pre = len(intact_names)

        if n_disrupted_pre == 0:
            return {
                "error": f"No disrupted cell lines found for {stratification_gene}",
                "p_value": None,
                "effect_size": None,
                "n_disrupted_premapping": 0,
                "n_intact_premapping": n_intact_pre,
            }

        # 2. Convert names → ACH-* IDs → SIDM* IDs
        disrupted_ach = [depmap.name_id_map.get(n, n) for n in disrupted_names]
        intact_ach = [depmap.name_id_map.get(n, n) for n in intact_names]

        disrupted_sanger = set(depmap.translate_to_sanger_ids(disrupted_ach))
        intact_sanger = set(depmap.translate_to_sanger_ids(intact_ach))

        # 3. Get ALL drug response data for target gene (pooled across drugs)
        gdsc = _get_client()
        drugs = gdsc.get_drugs_targeting_gene(target_gene)
        if not drugs:
            return {
                "error": f"No GDSC drugs found targeting '{target_gene}'",
                "p_value": None,
                "effect_size": None,
            }

        drug_names_used = sorted(set(d.drug_name for d in drugs))

        # Get all individual AUC measurements across all drugs targeting this gene
        all_measurements = gdsc.get_all_auc_scores_by_target(target_gene)

        # Build universe: Sanger IDs that have ANY drug response data for this target
        sanger_ids_with_data = set(m["sanger_model_id"] for m in all_measurements)

        # 4. Intersect with universe (cell lines that have both genomic + drug data)
        disrupted_in_universe = disrupted_sanger & sanger_ids_with_data
        intact_in_universe = intact_sanger & sanger_ids_with_data

        # Collect all AUC values per group (pooled across drugs, like the notebook)
        group_a = [
            m["auc"] for m in all_measurements if m["sanger_model_id"] in disrupted_in_universe
        ]
        group_b = [m["auc"] for m in all_measurements if m["sanger_model_id"] in intact_in_universe]

        if len(group_a) < 3:
            return {
                "error": f"Insufficient disrupted cell lines with GDSC data ({len(group_a)} measurements)",
                "p_value": None,
                "effect_size": None,
                "n_disrupted": len(group_a),
                "n_intact": len(group_b),
                "n_disrupted_cell_lines": len(disrupted_in_universe),
                "n_intact_cell_lines": len(intact_in_universe),
                "n_disrupted_premapping": n_disrupted_pre,
                "n_intact_premapping": n_intact_pre,
                "n_drugs_pooled": len(drug_names_used),
            }

        if len(group_b) < 3:
            return {
                "error": f"Insufficient intact cell lines with GDSC data ({len(group_b)} measurements)",
                "p_value": None,
                "effect_size": None,
                "n_disrupted": len(group_a),
                "n_intact": len(group_b),
                "n_disrupted_cell_lines": len(disrupted_in_universe),
                "n_intact_cell_lines": len(intact_in_universe),
                "n_disrupted_premapping": n_disrupted_pre,
                "n_intact_premapping": n_intact_pre,
                "n_drugs_pooled": len(drug_names_used),
            }

        # 5. Mann-Whitney U (one-tailed: disrupted more sensitive = lower scores)
        p_value = mann_whitney_u(group_a, group_b)
        median_a = stats_mod.median(group_a)
        median_b = stats_mod.median(group_b)
        effect_size = median_a - median_b

        return sanitize_floats(
            {
                "p_value": p_value,
                "effect_size": effect_size,
                "median_disrupted": median_a,
                "median_intact": median_b,
                "n_disrupted": len(group_a),
                "n_intact": len(group_b),
                "n_disrupted_cell_lines": len(disrupted_in_universe),
                "n_intact_cell_lines": len(intact_in_universe),
                "n_disrupted_premapping": n_disrupted_pre,
                "n_intact_premapping": n_intact_pre,
                "n_drugs_pooled": len(drug_names_used),
                "drugs_used": drug_names_used,
                "target_gene": target_gene,
                "stratification_gene": stratification_gene,
                "metric": metric,
            }
        )

    @mcp_app.tool()
    def mcp_gdsc_check_drug_coverage(drug_names: list[str]) -> dict:
        """Check which drugs have data in GDSC. Returns per-drug availability and cell line counts."""
        return _get_client().check_drug_coverage(drug_names)

    @mcp_app.tool()
    def mcp_gdsc_get_all_cell_lines() -> list[str]:
        """Get all cell line IDs (Sanger Model IDs) with drug response data in GDSC."""
        return sorted(list(_get_client().get_all_cell_lines()))

    @mcp_app.tool()
    def mcp_gdsc_test_drug_sensitivity(
        drug_id: int,
        stratification_gene: str,
        metric: str = "auc",
    ) -> dict:
        """
        Test whether cell lines with a disrupted gene are more sensitive to a drug.
        Performs the full workflow server-side: stratify cell lines by gene disruption
        (DepMap), get drug response scores (GDSC), translate cell line IDs internally,
        and run a one-tailed Mann-Whitney U test.

        Use this instead of manually chaining mcp_get_disrupted_cell_lines →
        mcp_translate_to_sanger_ids → mcp_gdsc_get_auc_scores → mcp_mann_whitney_u,
        which fails due to cell line name vs ID mismatches.

        Args:
            drug_id: GDSC drug ID (from mcp_gdsc_get_drugs_targeting_gene)
            stratification_gene: Gene to stratify by (disrupted vs intact)
            metric: "auc" (default, lower = more sensitive) or "ic50" (lower = more sensitive)

        Returns:
            p_value: one-tailed p-value (alternative='less', testing if disrupted are more sensitive)
            effect_size: median(disrupted) - median(intact), negative means disrupted more sensitive
            median_disrupted, median_intact: group medians
            n_disrupted, n_intact: sample sizes after ID mapping
            n_disrupted_premapping, n_intact_premapping: sample sizes before ID mapping
        """
        import math
        import statistics as stats_mod

        from ..depmap.client import mann_whitney_u
        from ..depmap.mcp_tools import _ensure_loaded

        # 1. Get disrupted vs intact cell lines (as names)
        depmap = _ensure_loaded(mutations=True, gene_effect=True, expression=True, copy_number=True)
        if depmap.disrupted is None:
            depmap.load_disrupted()
        depmap.use_cell_line_names_as_id()

        if stratification_gene not in depmap.disrupted.columns:
            return {
                "error": f"Gene '{stratification_gene}' not found in disruption matrix",
                "p_value": None,
                "effect_size": None,
            }

        disrupted_mask = depmap.disrupted[stratification_gene].fillna(False).astype(bool)
        all_crispr = set(depmap.gene_effect.index)
        disrupted_names = sorted(set(disrupted_mask[disrupted_mask].index) & all_crispr)
        intact_names = sorted(all_crispr - set(disrupted_names))

        n_disrupted_pre = len(disrupted_names)
        n_intact_pre = len(intact_names)

        if n_disrupted_pre == 0:
            return {
                "error": f"No disrupted cell lines found for {stratification_gene}",
                "p_value": None,
                "effect_size": None,
                "n_disrupted_premapping": 0,
                "n_intact_premapping": n_intact_pre,
            }

        # 2. Convert names → ACH-* IDs → SIDM* IDs
        disrupted_ach = [depmap.name_id_map.get(n, n) for n in disrupted_names]
        intact_ach = [depmap.name_id_map.get(n, n) for n in intact_names]

        disrupted_sanger = set(depmap.translate_to_sanger_ids(disrupted_ach))
        intact_sanger = set(depmap.translate_to_sanger_ids(intact_ach))

        # 3. Get drug response scores
        gdsc = _get_client()
        if metric == "ic50":
            all_scores = gdsc.get_ic50_scores(drug_id)
        else:
            all_scores = gdsc.get_auc_scores(drug_id)

        # 4. Split scores by group (intersect with available GDSC data)
        group_a = [
            all_scores[sid]
            for sid in disrupted_sanger
            if sid in all_scores and not math.isnan(all_scores[sid])
        ]
        group_b = [
            all_scores[sid]
            for sid in intact_sanger
            if sid in all_scores and not math.isnan(all_scores[sid])
        ]

        if len(group_a) < 3:
            return {
                "error": f"Insufficient disrupted cell lines with GDSC data ({len(group_a)})",
                "p_value": None,
                "effect_size": None,
                "n_disrupted": len(group_a),
                "n_intact": len(group_b),
                "n_disrupted_premapping": n_disrupted_pre,
                "n_intact_premapping": n_intact_pre,
            }

        if len(group_b) < 3:
            return {
                "error": f"Insufficient intact cell lines with GDSC data ({len(group_b)})",
                "p_value": None,
                "effect_size": None,
                "n_disrupted": len(group_a),
                "n_intact": len(group_b),
                "n_disrupted_premapping": n_disrupted_pre,
                "n_intact_premapping": n_intact_pre,
            }

        # 5. Mann-Whitney U (one-tailed: disrupted more sensitive = lower scores)
        p_value = mann_whitney_u(group_a, group_b)
        median_a = stats_mod.median(group_a)
        median_b = stats_mod.median(group_b)
        effect_size = median_a - median_b

        return sanitize_floats(
            {
                "p_value": p_value,
                "effect_size": effect_size,
                "median_disrupted": median_a,
                "median_intact": median_b,
                "n_disrupted": len(group_a),
                "n_intact": len(group_b),
                "n_disrupted_premapping": n_disrupted_pre,
                "n_intact_premapping": n_intact_pre,
                "drug_id": drug_id,
                "stratification_gene": stratification_gene,
                "metric": metric,
            }
        )

    @mcp_app.tool()
    def mcp_gdsc_get_data_version() -> dict:
        """Get GDSC data version info and list of cached files."""
        return _get_client().get_data_version()

    @mcp_app.tool()
    def mcp_gdsc_get_version_info() -> dict:
        """Get GDSC version metadata for methods sections and reproducibility."""
        return _get_client().get_version_info()
