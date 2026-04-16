"""
GDSC Hypothesis Tester - Tests gene-drug synthetic lethality claims.

Tests whether cells with a specific genetic alteration are more sensitive
to drugs targeting a particular gene/pathway.

IMPORTANT: This module never hallucinates data. It reports:
- "data_found": Actual GDSC data supports/contradicts the claim
- "no_data": Drug or cell lines not in GDSC database
- "insufficient_samples": Too few cell lines for statistical test
"""

import statistics
from dataclasses import asdict, dataclass

from .client import GDSCClient


@dataclass
class GDSCTestResult:
    """Result of a GDSC-based gene-drug SL hypothesis test."""

    claim_id: str
    claim_text: str
    test_type: str  # "gene_drug_sl"

    # Data availability
    data_status: str  # "data_found", "no_data", "insufficient_samples"
    data_details: str

    # Test result
    test_executed: bool
    result: str | None  # "supports", "contradicts", "inconclusive", None

    # Sample sizes
    n_mutant: int
    n_wildtype: int

    # Statistical results (for IC50 or AUC comparison)
    effect_size: float | None
    p_value: float | None
    mutant_mean: float | None
    wildtype_mean: float | None

    # Drug info
    drug_name: str
    drug_target: str

    # Data provenance
    dataset: str
    genes_tested: list

    def to_dict(self) -> dict:
        return asdict(self)


def mann_whitney_u(x: list, y: list) -> float:
    """Simple Mann-Whitney U test with normal approximation."""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return 1.0

    combined = [(val, 0) for val in x] + [(val, 1) for val in y]
    combined.sort(key=lambda t: t[0])

    ranks = []
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2
        for k in range(i, j):
            ranks.append((avg_rank, combined[k][1]))
        i = j

    r1 = sum(r for r, g in ranks if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sigma = ((n1 * n2 * (n1 + n2 + 1)) / 12) ** 0.5

    if sigma == 0:
        return 1.0

    z = (u1 - mu) / sigma

    import math

    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / (2**0.5))))
    return p


class GDSCHypothesisTester:
    """
    Test gene-drug synthetic lethality claims against GDSC data.

    Requires integration with DepMap for mutation status of cell lines.
    """

    def __init__(self, auto_download: bool = False):
        self.client = GDSCClient(auto_download=auto_download)

    def ensure_data(self) -> dict:
        """Ensure required data is available."""
        return self.client.ensure_data()

    def test_gene_drug_sl(
        self,
        claim_id: str,
        claim_text: str,
        gene_a: str,
        drug_name: str,
        mutant_cell_lines: list,
        wildtype_cell_lines: list,
        metric: str = "auc",  # "auc" or "ic50"
        min_samples: int = 5,
        dataset: str = "GDSC1",
    ) -> GDSCTestResult:
        """
        Test claim: "Loss of gene_a sensitizes cells to drug".

        Args:
            claim_id: Identifier for this claim
            claim_text: Human-readable claim text
            gene_a: Gene whose loss creates drug sensitivity
            drug_name: Drug to test sensitivity to
            mutant_cell_lines: List of cell line IDs with gene_a mutation
            wildtype_cell_lines: List of cell line IDs without gene_a mutation
            metric: "auc" (lower=more sensitive) or "ic50" (lower=more sensitive)
            min_samples: Minimum samples per group
            dataset: "GDSC1" or "GDSC2"

        Returns:
            GDSCTestResult with test outcome
        """
        genes_tested = [gene_a, drug_name]

        # Get drug info
        drug = self.client.get_drug_by_name(drug_name)
        if drug is None:
            return GDSCTestResult(
                claim_id=claim_id,
                claim_text=claim_text,
                test_type="gene_drug_sl",
                data_status="no_data",
                data_details=f"Drug '{drug_name}' not found in GDSC",
                test_executed=False,
                result=None,
                n_mutant=0,
                n_wildtype=0,
                effect_size=None,
                p_value=None,
                mutant_mean=None,
                wildtype_mean=None,
                drug_name=drug_name,
                drug_target="",
                dataset=dataset,
                genes_tested=genes_tested,
            )

        # Get drug response scores
        if metric == "auc":
            all_scores = self.client.get_auc_scores(drug.drug_id, dataset=dataset)
        else:
            all_scores = self.client.get_ic50_scores(drug.drug_id, dataset=dataset)

        if not all_scores:
            return GDSCTestResult(
                claim_id=claim_id,
                claim_text=claim_text,
                test_type="gene_drug_sl",
                data_status="no_data",
                data_details=f"No response data for drug '{drug_name}' in {dataset}",
                test_executed=False,
                result=None,
                n_mutant=0,
                n_wildtype=0,
                effect_size=None,
                p_value=None,
                mutant_mean=None,
                wildtype_mean=None,
                drug_name=drug_name,
                drug_target=drug.target,
                dataset=dataset,
                genes_tested=genes_tested,
            )

        # Filter to cell lines with drug response data
        mutant_scores = [all_scores[cl] for cl in mutant_cell_lines if cl in all_scores]
        wildtype_scores = [all_scores[cl] for cl in wildtype_cell_lines if cl in all_scores]

        # Remove NaN values
        import math

        mutant_scores = [s for s in mutant_scores if not math.isnan(s)]
        wildtype_scores = [s for s in wildtype_scores if not math.isnan(s)]

        n_mutant = len(mutant_scores)
        n_wildtype = len(wildtype_scores)

        if n_mutant < min_samples or n_wildtype < min_samples:
            return GDSCTestResult(
                claim_id=claim_id,
                claim_text=claim_text,
                test_type="gene_drug_sl",
                data_status="insufficient_samples",
                data_details=f"Mutant: {n_mutant}, Wildtype: {n_wildtype}. Need >= {min_samples} each.",
                test_executed=False,
                result=None,
                n_mutant=n_mutant,
                n_wildtype=n_wildtype,
                effect_size=None,
                p_value=None,
                mutant_mean=None,
                wildtype_mean=None,
                drug_name=drug_name,
                drug_target=drug.target,
                dataset=dataset,
                genes_tested=genes_tested,
            )

        # Calculate statistics
        mutant_mean = statistics.mean(mutant_scores)
        wildtype_mean = statistics.mean(wildtype_scores)
        effect_size = mutant_mean - wildtype_mean
        p_value = mann_whitney_u(mutant_scores, wildtype_scores)

        # Interpret result
        # For AUC: Lower = more sensitive. If mutant_mean < wildtype_mean, mutants are more sensitive
        # For IC50: Lower = more sensitive. Same interpretation
        if p_value < 0.05:
            if effect_size < -0.1:  # Mutant more sensitive (lower score)
                result = "supports"
            elif effect_size > 0.1:  # Mutant less sensitive
                result = "contradicts"
            else:
                result = "inconclusive"
        else:
            result = "inconclusive"

        return GDSCTestResult(
            claim_id=claim_id,
            claim_text=claim_text,
            test_type="gene_drug_sl",
            data_status="data_found",
            data_details=f"Compared {drug_name} {metric.upper()} in {gene_a}-mutant vs wildtype",
            test_executed=True,
            result=result,
            n_mutant=n_mutant,
            n_wildtype=n_wildtype,
            effect_size=effect_size,
            p_value=p_value,
            mutant_mean=mutant_mean,
            wildtype_mean=wildtype_mean,
            drug_name=drug_name,
            drug_target=drug.target,
            dataset=dataset,
            genes_tested=genes_tested,
        )


def test_gene_drug_sl(
    gene_a: str,
    drug_name: str,
    mutant_cell_lines: list,
    wildtype_cell_lines: list,
    auto_download: bool = False,
) -> dict:
    """
    Convenience function to test gene-drug synthetic lethality.

    Note: Requires pre-computed lists of mutant/wildtype cell lines.
    Use DepMapClient to get these lists based on mutation status.
    """
    tester = GDSCHypothesisTester(auto_download=auto_download)
    result = tester.test_gene_drug_sl(
        claim_id=f"{gene_a}_{drug_name}_sl",
        claim_text=f"Loss of {gene_a} sensitizes to {drug_name}",
        gene_a=gene_a,
        drug_name=drug_name,
        mutant_cell_lines=mutant_cell_lines,
        wildtype_cell_lines=wildtype_cell_lines,
    )
    return result.to_dict()
