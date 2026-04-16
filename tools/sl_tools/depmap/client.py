"""
DepMap Client — extracted from mcp_server.py for use by the unified sl-tools server.

Contains:
- DepMapClient: pandas-based access to DepMap CRISPR dependency, mutation,
  expression, and copy number data
- CellLineInfo dataclass
- mann_whitney_u statistical helper

Usage as Python library:
    from tools.depmap.client import DepMapClient
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .. import _config

# ============================================================================
# Constants
# ============================================================================

DEFAULT_CACHE_DIR = _config.get_tool_cache_dir("depmap")

SUPPORTED_VERSIONS = ["26Q1", "25Q3", "24Q4", "24Q2", "23Q4", "23Q2"]

REQUIRED_FILES = [
    "CRISPRGeneEffect.csv",
    "OmicsSomaticMutations.csv",
    "Model.csv",
]

OPTIONAL_FILES = [
    "OmicsCNGene.csv",
    "OmicsExpressionTPMLogp1HumanProteinCodingGenes.csv",
    "AvanaLogfoldChange.csv",
    "AvanaGuideMap.csv",
]

# Default thresholds for CNV classification
CN_LOSS_THRESHOLD = -1.0
CN_DEEP_LOSS_THRESHOLD = -2.0
CN_GAIN_THRESHOLD = 0.58
CN_AMP_THRESHOLD = 1.0


# ============================================================================
# Data classes
# ============================================================================


@dataclass
class CellLineInfo:
    depmap_id: str
    cell_line_name: str
    lineage: str | None
    primary_disease: str | None
    sanger_model_id: str | None = None


# ============================================================================
# Statistical helpers
# ============================================================================


def mann_whitney_u(x: list, y: list) -> float:
    """
    Mann-Whitney U test using scipy.
    Returns one-tailed p-value (alternative='less').

    Tests whether x has lower values than y (appropriate for synthetic lethality
    where we expect mutants to have more negative dependency scores).

    NaN values are silently dropped before computing the test.
    """
    x = [v for v in x if not math.isnan(v)]
    y = [v for v in y if not math.isnan(v)]

    if len(x) == 0 or len(y) == 0:
        return 1.0

    from scipy.stats import mannwhitneyu

    _, p = mannwhitneyu(x, y, alternative="less")
    return float(p)


# ============================================================================
# DepMapClient
# ============================================================================


class DepMapClient:
    """Pandas-based client for accessing DepMap data with caching."""

    def __init__(
        self,
        version: str = "23Q2",
        cache_dir: Path | None = None,
        datapath: Path | None = None,
    ):
        if version not in SUPPORTED_VERSIONS:
            raise ValueError(f"Unsupported version: {version}. Supported: {SUPPORTED_VERSIONS}")
        self.version = version

        if datapath is not None:
            self.datapath = Path(datapath)
        else:
            base = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
            self.datapath = base / f"depmap_{version.lower()}"

        self.datapath.mkdir(parents=True, exist_ok=True)
        self._index_type = "id"

        # DataFrames (lazy-loaded)
        self.sample_info = None
        self.mutations = None
        self.sq_mutations = None
        self.gene_effect = None
        self.expression = None
        self.copy_number = None
        self.robust_copy_number = None
        self.disrupted = None
        self.logfold_change = None

        # ID maps
        self.id_name_map = {}
        self.name_id_map = {}
        self.lineage = None

        # Sanger ID translation
        self._depmap_to_sanger = {}
        self._sanger_to_depmap = {}

    # =========================================================================
    # Data loading
    # =========================================================================

    def load(
        self,
        mutations=False,
        gene_effect=False,
        expression=False,
        copy_number=False,
        robust_copy_number=False,
        disrupted=False,
    ):
        """Load select data types. sample_info is always loaded."""
        self.load_sample_info()

        if mutations or disrupted:
            self.load_mutations()
        if gene_effect:
            self.load_gene_effect()
        if expression or disrupted:
            self.load_expression()
        if copy_number or disrupted:
            self.load_copy_number()
        if robust_copy_number or disrupted:
            self.load_robust_copy_number()
        if disrupted:
            self.load_disrupted()

        self.use_cell_line_names_as_id()
        return self

    def load_all(self):
        """Load all data types."""
        return self.load(
            mutations=True,
            gene_effect=True,
            expression=True,
            copy_number=True,
            robust_copy_number=True,
            disrupted=True,
        )

    def load_sample_info(self, filename="Model.csv"):
        """Load cell line information."""
        filepath = self.datapath / filename
        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found at {self.datapath}")

        self.sample_info = pd.read_csv(filepath).set_index("ModelID")
        self.id_name_map = self.sample_info["StrippedCellLineName"].to_dict()
        self.name_id_map = {v: k for k, v in self.id_name_map.items()}
        self.lineage = self.sample_info["SampleCollectionSite"].unique()

        # Build Sanger ID translation
        self._depmap_to_sanger = {}
        self._sanger_to_depmap = {}
        if "SangerModelID" in self.sample_info.columns:
            for model_id, row in self.sample_info.iterrows():
                sanger_id = row.get("SangerModelID")
                if pd.notna(sanger_id) and sanger_id:
                    self._depmap_to_sanger[model_id] = sanger_id
                    self._sanger_to_depmap[sanger_id] = model_id

        return self.sample_info

    def load_mutations(self, filename="OmicsSomaticMutations.csv"):
        """Load cell line mutations and build squeezed mutation matrix."""
        filepath = self.datapath / filename
        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found at {self.datapath}")

        self.mutations = pd.read_csv(filepath, low_memory=False)

        # Build squeezed mutation matrix: filter to LikelyLoF mutations, pivot to binary
        lof_col = "LikelyLoF" if "LikelyLoF" in self.mutations.columns else "isDeleterious"
        self.sq_mutations = (
            self.mutations.loc[
                self.mutations[lof_col],
                ["HugoSymbol", "ModelID"],
            ]
            .drop_duplicates()
            .assign(_mutation=1)
            .pivot(index="ModelID", columns="HugoSymbol", values="_mutation")
            .fillna(0)
            .astype(bool)
        )

        return self.mutations

    def load_gene_effect(self, filename="CRISPRGeneEffect.csv"):
        """Load CRISPR gene effect scores."""
        filepath = self.datapath / filename
        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found at {self.datapath}")

        self.gene_effect = pd.read_csv(filepath, index_col=0)
        self.gene_effect.columns = self._fix_depmap_gene_names(self.gene_effect.columns)
        return self.gene_effect

    def load_expression(self, filename="OmicsExpressionTPMLogp1HumanProteinCodingGenes.csv"):
        """Load expression data (log2(TPM+1))."""
        filepath = self.datapath / filename
        if not filepath.exists():
            alt = "OmicsExpressionProteinCodingGenesTPMLogp1.csv"
            alt_path = self.datapath / alt
            if alt_path.exists():
                filepath = alt_path
            else:
                raise FileNotFoundError(
                    f"Expression file not found at {self.datapath} (tried {filename} and {alt})"
                )

        self.expression = pd.read_csv(filepath, index_col=0)
        if "ModelID" in self.expression.columns:
            self.expression = self.expression.set_index("ModelID")
        self.expression.index.name = "DepMap_ID"
        self.expression = self.expression.select_dtypes(include="number")
        self.expression.columns = self._fix_depmap_gene_names(self.expression.columns)
        return self.expression.columns

    def load_copy_number(self, filename="OmicsCNGene.csv"):
        """Load gene-level copy number data (log2 relative CN)."""
        filepath = self.datapath / filename
        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found at {self.datapath}")

        self.copy_number = pd.read_csv(filepath, index_col=0)
        if "ModelID" in self.copy_number.columns:
            self.copy_number = self.copy_number.set_index("ModelID")
        self.copy_number.index.name = "DepMap_ID"
        self.copy_number = self.copy_number.select_dtypes(include="number")
        self.copy_number.columns = self._fix_depmap_gene_names(self.copy_number.columns)
        return self.copy_number.columns

    def load_robust_copy_number(self, underexpression_pct=25):
        """Compute robust copy number: lost only if BOTH under-expressed AND under CN threshold."""
        if self.expression is None:
            raise RuntimeError("Expression data must be loaded first (load with expression=True)")
        if self.copy_number is None:
            raise RuntimeError("Copy number data must be loaded first (load with copy_number=True)")

        under_expression = self.expression < np.percentile(
            self.expression, underexpression_pct, axis=0
        )
        under_copy_number = (self.copy_number < 1).astype(bool)

        self.robust_copy_number = under_expression & under_copy_number
        return self.robust_copy_number

    def load_disrupted(self):
        """Compute disrupted status: LikelyLoF mutation OR (CN loss AND under-expressed)."""
        if self.mutations is None:
            raise RuntimeError("Mutations must be loaded first (load with mutations=True)")
        if self.expression is None:
            raise RuntimeError("Expression must be loaded first (load with expression=True)")
        if self.copy_number is None:
            raise RuntimeError("Copy number must be loaded first (load with copy_number=True)")

        if self.robust_copy_number is None:
            self.load_robust_copy_number()

        if "LikelyLoF" in self.mutations.columns:
            del_col = "LikelyLoF"
        elif "isDeleterious" in self.mutations.columns:
            del_col = "isDeleterious"
        else:
            raise RuntimeError(
                "Cannot find deleterious mutation column. "
                f"Available columns: {list(self.mutations.columns)}"
            )

        deleterious = self.mutations.loc[
            self.mutations[del_col],
            ["HugoSymbol", "ModelID"],
        ].drop_duplicates()

        if len(deleterious) > 0:
            del_mutations = (
                deleterious.assign(_mutation=1)
                .pivot(index="ModelID", columns="HugoSymbol", values="_mutation")
                .fillna(0)
                .astype(bool)
            )
        else:
            del_mutations = pd.DataFrame(dtype=bool)

        rcn = self.robust_copy_number.fillna(False).astype(bool)
        rcn = rcn.loc[~rcn.index.duplicated(keep="first"), ~rcn.columns.duplicated(keep="first")]
        if self._index_type == "name" and len(del_mutations) > 0:
            del_mutations.index = self.convert_id_to_name(del_mutations.index)
        del_mutations = del_mutations.loc[
            ~del_mutations.index.duplicated(keep="first"),
            ~del_mutations.columns.duplicated(keep="first"),
        ]

        if len(del_mutations) > 0:
            common_genes = rcn.columns.intersection(del_mutations.columns)
            common_samples = rcn.index.intersection(del_mutations.index)

            self.disrupted = rcn.copy()

            if len(common_samples) > 0 and len(common_genes) > 0:
                self.disrupted.loc[common_samples, common_genes] = (
                    self.disrupted.loc[common_samples, common_genes].values
                    | del_mutations.loc[common_samples, common_genes].values
                )
        else:
            self.disrupted = rcn

        return self.disrupted

    def load_logfold_change(
        self, filename="AvanaLogfoldChange.csv", guidemap_filename="AvanaGuideMap.csv"
    ):
        """Load sgRNA-level logfold change data."""
        filepath = self.datapath / filename
        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found at {self.datapath}")

        self.logfold_change = pd.read_csv(filepath, index_col=0)

        if guidemap_filename is None:
            return self.logfold_change

        guidemap_path = self.datapath / guidemap_filename
        if not guidemap_path.exists():
            return self.logfold_change

        guidemap = pd.read_csv(guidemap_path, index_col=0)
        guidemap = guidemap.loc[
            guidemap["Gene"].str.endswith(")").fillna(False) & (guidemap["UsedByChronos"]),
            "Gene",
        ].to_dict()
        guidemap = {k: v.split("(")[0].strip() for k, v in guidemap.items()}
        self.logfold_change["Gene"] = self.logfold_change.index.map(guidemap)

        return self.logfold_change

    # =========================================================================
    # Cell line ID management
    # =========================================================================

    def use_cell_line_names_as_id(self):
        """Reindex DataFrames from DepMap IDs to cell line names."""
        attrs = ["expression", "gene_effect", "copy_number", "robust_copy_number", "disrupted"]

        for attr in attrs:
            df = getattr(self, attr, None)
            if df is None:
                continue
            df.index = self.convert_id_to_name(df.index)

        self._index_type = "name"

    def convert_id_to_name(self, ids):
        return np.array([self.id_name_map.get(i, i) for i in ids])

    def convert_name_to_id(self, names):
        return np.array([self.name_id_map.get(i, i) for i in names])

    # =========================================================================
    # Cell line stratification
    # =========================================================================

    def split_samples_by_mutations(
        self,
        mutated_genes,
        gene_column="HugoSymbol",
        deleterious_only=False,
        hotspot_only=False,
    ):
        """Separate cell lines based on mutation status. Returns (mutated, not_mutated)."""
        if self.mutations is None:
            raise RuntimeError("Mutations not loaded. Call load(mutations=True) first.")

        data = self.mutations
        if deleterious_only:
            del_col = "LikelyLoF" if "LikelyLoF" in data.columns else "isDeleterious"
            data = data.loc[data[del_col]]
        if hotspot_only:
            hot_col = "isCOSMIChotspot" if "isCOSMIChotspot" in data.columns else "Hotspot"
            data = data.loc[data[hot_col]]

        try:
            mutated = data[gene_column].isin(mutated_genes)
        except TypeError:
            mutated = data[gene_column].isin([mutated_genes])

        mutated_ids = data.loc[mutated, "ModelID"].unique()
        all_lines = self.mutations["ModelID"].unique()
        not_mutated_ids = np.setdiff1d(all_lines, mutated_ids)

        if self._index_type == "name":
            mutated_ids = self.convert_id_to_name(mutated_ids)
            not_mutated_ids = self.convert_id_to_name(not_mutated_ids)

        return mutated_ids, not_mutated_ids

    def split_samples_by_expression(self, gene, lower_pct=50, upper_pct=50):
        """Separate cell lines based on expression percentile. Returns (under, over)."""
        if self.expression is None:
            raise RuntimeError("Expression not loaded. Call load(expression=True) first.")

        data = self.expression[gene].values
        under_index = np.argwhere(data < np.percentile(data, lower_pct)).ravel()
        over_index = np.argwhere(data > np.percentile(data, upper_pct)).ravel()

        under = np.array(self.expression.index[under_index])
        over = np.array(self.expression.index[over_index])

        if self._index_type == "name":
            under = self.convert_id_to_name(under)
            over = self.convert_id_to_name(over)

        return under, over

    def filter_samples_by_lineage(self, lineage, samples=None, depmap_id=False):
        """Get samples that belong to a lineage."""
        if self.sample_info is None:
            raise RuntimeError("Sample info not loaded. Call load_sample_info() first.")

        column = "DepMap_ID" if depmap_id else "StrippedCellLineName"
        if depmap_id:
            valid_samples = self.sample_info.loc[
                self.sample_info["OncotreeLineage"] == lineage
            ].index.values
        else:
            valid_samples = self.sample_info.loc[
                self.sample_info["OncotreeLineage"] == lineage, column
            ].values

        if samples is not None:
            return np.intersect1d(valid_samples, samples)

        return valid_samples

    # =========================================================================
    # Query methods
    # =========================================================================

    def ensure_data(self, files=None) -> dict:
        """Check that required data files exist locally."""
        if files is None:
            files = REQUIRED_FILES
        results = {}
        missing = []
        for filename in files:
            local_path = self.datapath / filename
            if local_path.exists():
                results[filename] = {"status": "cached", "path": str(local_path)}
            else:
                results[filename] = {"status": "missing"}
                missing.append(filename)
        if missing:
            results["_error"] = (
                f"Missing files: {missing}. "
                f"Download manually from depmap.org/portal/download to {self.datapath}/"
            )
        return results

    def check_gene_coverage(self, genes: list) -> dict:
        """Check which genes have data in DepMap (anti-hallucination check)."""
        if self.gene_effect is None:
            self.load_gene_effect()

        have_mutations = self.sq_mutations is not None
        if not have_mutations:
            try:
                self.load_mutations()
                have_mutations = True
            except FileNotFoundError:
                pass

        have_cnv = self.copy_number is not None
        if not have_cnv:
            try:
                self.load_copy_number()
                have_cnv = True
            except FileNotFoundError:
                pass

        results = {}
        for gene in genes:
            in_crispr = gene in self.gene_effect.columns
            in_mutations = have_mutations and gene in self.sq_mutations.columns
            in_cnv = have_cnv and gene in self.copy_number.columns
            n_cell_lines = self.gene_effect[gene].dropna().shape[0] if in_crispr else 0

            results[gene] = {
                "in_crispr_screen": in_crispr,
                "in_mutation_data": in_mutations,
                "in_cnv_data": in_cnv,
                "n_cell_lines_with_dependency": n_cell_lines,
            }
        return results

    def get_dependency_scores(self, gene: str, cell_lines=None) -> dict:
        """Get dependency scores for a gene across cell lines."""
        if self.gene_effect is None:
            self.load_gene_effect()

        if gene not in self.gene_effect.columns:
            return {"error": f"Gene {gene} not found in CRISPR data"}

        scores = self.gene_effect[gene].dropna()
        if cell_lines is not None:
            valid = scores.index.intersection(cell_lines)
            scores = scores.loc[valid]
        return scores.to_dict()

    def query_gene_effect(self, gene_ko, group):
        """Get single-gene knockout scores for a group of samples."""
        if self.gene_effect is None:
            self.load_gene_effect()

        data = self._safe_index(self.gene_effect, group)
        return data[gene_ko]

    def get_cell_lines_with_mutation(self, gene: str) -> list:
        """Get cell lines with LikelyLoF mutations in a gene."""
        if self.sq_mutations is None:
            self.load_mutations()

        if gene not in self.sq_mutations.columns:
            return []

        return self.sq_mutations.index[self.sq_mutations[gene]].tolist()

    def get_cell_lines_without_mutation(self, gene: str) -> list:
        """Get cell lines without mutations in a gene."""
        if self.sq_mutations is None:
            self.load_mutations()
        if self.gene_effect is None:
            self.load_gene_effect()

        all_lines = set(self.gene_effect.index)
        mutant_lines = set(self.get_cell_lines_with_mutation(gene))
        return list(all_lines - mutant_lines)

    # =========================================================================
    # Copy Number Variation (CNV) Methods
    # =========================================================================

    def has_cnv_data(self) -> bool:
        """Check if CNV data file is available."""
        return (self.datapath / "OmicsCNGene.csv").exists()

    def get_cnv_value(self, gene: str, cell_line: str) -> float | None:
        """Get log2(CN) value for a gene in a cell line."""
        if self.copy_number is None:
            self.load_copy_number()
        if gene not in self.copy_number.columns or cell_line not in self.copy_number.index:
            return None
        val = self.copy_number.loc[cell_line, gene]
        return None if pd.isna(val) else float(val)

    def get_cnv_values(self, gene: str, cell_lines=None) -> dict:
        """Get CN values for a gene across cell lines."""
        if self.copy_number is None:
            self.load_copy_number()
        if gene not in self.copy_number.columns:
            return {"error": f"Gene {gene} not found in CNV data"}

        values = self.copy_number[gene].dropna()
        if cell_lines is not None:
            valid = values.index.intersection(cell_lines)
            values = values.loc[valid]
        return values.to_dict()

    def get_cell_lines_with_cn_loss(
        self, gene: str, threshold: float = CN_LOSS_THRESHOLD, deep_only: bool = False
    ) -> list:
        """Get cell lines with copy number loss for a gene."""
        if self.copy_number is None:
            self.load_copy_number()
        if gene not in self.copy_number.columns:
            return []
        if deep_only:
            threshold = CN_DEEP_LOSS_THRESHOLD
        values = self.copy_number[gene].dropna()
        return values.index[values <= threshold].tolist()

    def get_cell_lines_with_cn_gain(
        self, gene: str, threshold: float = CN_GAIN_THRESHOLD, amplification_only: bool = False
    ) -> list:
        """Get cell lines with copy number gain for a gene."""
        if self.copy_number is None:
            self.load_copy_number()
        if gene not in self.copy_number.columns:
            return []
        if amplification_only:
            threshold = CN_AMP_THRESHOLD
        values = self.copy_number[gene].dropna()
        return values.index[values >= threshold].tolist()

    def get_cell_lines_with_robust_cn_loss(self, gene: str) -> dict:
        """Get cell lines with robust CN loss (CN < 1 AND expression < 25th percentile)."""
        if self.robust_copy_number is None:
            self.load_robust_copy_number()
        self.use_cell_line_names_as_id()

        if gene not in self.robust_copy_number.columns:
            return {
                "error": f"Gene '{gene}' not found in robust copy number matrix",
                "robust_cn_loss": [],
                "no_robust_cn_loss": [],
                "n_robust_cn_loss": 0,
                "n_no_robust_cn_loss": 0,
            }

        mask = self.robust_copy_number[gene].fillna(False).astype(bool)
        if self.gene_effect is not None:
            all_crispr = set(self.gene_effect.index)
        else:
            all_crispr = set(mask.index)
        lost = set(mask[mask].index) & all_crispr
        not_lost = all_crispr - lost

        return {
            "robust_cn_loss": sorted(lost),
            "no_robust_cn_loss": sorted(not_lost),
            "n_robust_cn_loss": len(lost),
            "n_no_robust_cn_loss": len(not_lost),
        }

    def get_cell_lines_with_disruption(
        self,
        gene: str,
        include_mutations: bool = True,
        include_cn_loss: bool = True,
        cn_loss_threshold: float = CN_LOSS_THRESHOLD,
    ) -> list:
        """Get cell lines with gene disruption (mutation OR copy number loss)."""
        disrupted = set()
        if include_mutations:
            try:
                disrupted.update(self.get_cell_lines_with_mutation(gene))
            except FileNotFoundError:
                pass
        if include_cn_loss:
            try:
                disrupted.update(
                    self.get_cell_lines_with_cn_loss(gene, threshold=cn_loss_threshold)
                )
            except FileNotFoundError:
                pass
        return list(disrupted)

    def get_cell_lines_without_disruption(
        self,
        gene: str,
        include_mutations: bool = True,
        include_cn_loss: bool = True,
    ) -> list:
        """Get cell lines without gene disruption."""
        if self.gene_effect is None:
            self.load_gene_effect()
        all_lines = set(self.gene_effect.index)
        disrupted = set(
            self.get_cell_lines_with_disruption(
                gene, include_mutations=include_mutations, include_cn_loss=include_cn_loss
            )
        )
        return list(all_lines - disrupted)

    def get_unique_vulnerabilities(self, sample, cutoff=-1):
        """Get unique vulnerabilities for a sample (genes with effect < cutoff)."""
        if self.gene_effect is None:
            self.load_gene_effect()
        return self.gene_effect.columns[self.gene_effect.loc[sample] < cutoff].values

    # =========================================================================
    # ID translation
    # =========================================================================

    def translate_to_sanger_ids(self, depmap_ids: list) -> list:
        """Translate DepMap IDs to Sanger Model IDs for GDSC integration."""
        if self.sample_info is None:
            self.load_sample_info()
        return [self._depmap_to_sanger[did] for did in depmap_ids if did in self._depmap_to_sanger]

    def translate_from_sanger_ids(self, sanger_ids: list) -> list:
        """Translate Sanger Model IDs to DepMap IDs."""
        if self.sample_info is None:
            self.load_sample_info()
        return [self._sanger_to_depmap[sid] for sid in sanger_ids if sid in self._sanger_to_depmap]

    # =========================================================================
    # Version info
    # =========================================================================

    def get_data_version(self) -> dict:
        """Get version information for reproducibility reporting."""
        return {
            "version": self.version,
            "datapath": str(self.datapath),
            "files_present": [f.name for f in self.datapath.iterdir() if f.suffix == ".csv"],
        }

    def get_version_info(self) -> dict:
        """Get detailed version metadata for methods sections."""
        manifest_path = Path(__file__).parent / "data_manifest.json"
        manifest = {}
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)

        version_info = manifest.get("versions", {}).get(self.version, {})
        files_info = {}

        for filename in REQUIRED_FILES:
            filepath = self.datapath / filename
            file_manifest = version_info.get("files", {}).get(filename, {})
            if filepath.exists():
                sha = file_manifest.get("sha256", "unverified")
                files_info[filename] = sha[:16] + "..." if len(sha) > 16 else sha
            else:
                files_info[filename] = "missing"

        return {
            "tool": "depmap",
            "version": self.version,
            "data_source": "https://depmap.org/portal/",
            "files": files_info,
            "zenodo_doi": version_info.get("files", {})
            .get(REQUIRED_FILES[0], {})
            .get("zenodo_doi"),
        }

    # =========================================================================
    # Safe indexing utilities
    # =========================================================================

    def safe_index(self, attr, index=None, columns=None):
        """Safely index a DataFrame attribute."""
        data = getattr(self, attr)
        if index is not None:
            data = self._safe_index(data, index)
        if columns is not None:
            data = self._safe_columns(data, columns)
        return data

    @staticmethod
    def _fix_depmap_gene_names(columns):
        """Strip parenthetical suffixes: 'GENE (12345)' -> 'GENE'."""
        return np.array([col.split()[0].strip() for col in columns])

    @staticmethod
    def _safe_index(dataframe, index):
        """Index with intersection to avoid KeyErrors."""
        safe = dataframe.index.intersection(index)
        return dataframe.loc[safe]

    @staticmethod
    def _safe_columns(dataframe, columns):
        """Select columns with intersection to avoid KeyErrors."""
        safe = dataframe.columns.intersection(columns)
        return dataframe[safe]
