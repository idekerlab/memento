"""
GDSC Data Client - Downloads and caches GDSC drug sensitivity data.

Provides access to IC50/AUC drug response data for cancer cell lines.
Data source: https://www.cancerrxgene.org/
"""

import csv
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .. import _config

DEFAULT_CACHE_DIR = _config.get_tool_cache_dir("gdsc")

# GDSC data URLs (release 8.5)
GDSC_URLS = {
    "GDSC1_dose_response": "ftp://ftp.sanger.ac.uk/pub/project/cancerrxgene/releases/current_release/GDSC1_fitted_dose_response_24Jul22.csv",
    "GDSC2_dose_response": "ftp://ftp.sanger.ac.uk/pub/project/cancerrxgene/releases/current_release/GDSC2_fitted_dose_response_24Jul22.csv",
    "compounds": "https://cog.sanger.ac.uk/cancerrxgene/GDSC_release8.5/screened_compounds_rel_8.5.csv",
}

REQUIRED_FILES = [
    "GDSC1_fitted_dose_response.csv",
    "screened_compounds.csv",
]


@dataclass
class DrugInfo:
    drug_id: int
    drug_name: str
    target: str
    pathway: str
    synonyms: str | None = None


@dataclass
class DrugResponse:
    cell_line_name: str
    sanger_model_id: str
    cosmic_id: int
    drug_id: int
    drug_name: str
    ln_ic50: float
    auc: float
    z_score: float
    target: str
    pathway: str


class GDSCClient:
    """Client for accessing GDSC drug sensitivity data."""

    def __init__(self, cache_dir: Path | None = None, auto_download: bool = True):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_download = auto_download

        self._dose_response_data = None
        self._compounds_data = None
        self._drug_index = {}  # drug_name -> DrugInfo
        self._target_to_drugs = {}  # target_gene -> [drug_ids]
        self._cell_line_index = set()

    def ensure_data(self, files: list | None = None) -> dict:
        """Ensure required data files are downloaded."""
        if files is None:
            files = REQUIRED_FILES

        results = {}
        for filename in files:
            local_path = self.cache_dir / filename

            if local_path.exists():
                results[filename] = {"status": "cached", "path": str(local_path)}
                continue

            # Map filename to URL
            if "GDSC1" in filename:
                url = GDSC_URLS["GDSC1_dose_response"]
            elif "GDSC2" in filename:
                url = GDSC_URLS["GDSC2_dose_response"]
            elif "compound" in filename.lower():
                url = GDSC_URLS["compounds"]
            else:
                results[filename] = {"status": "unknown_file"}
                continue

            if not self.auto_download:
                results[filename] = {"status": "needs_download", "url": url}
                continue

            try:
                self._download_file(url, local_path)
                results[filename] = {"status": "downloaded", "path": str(local_path)}
            except Exception as e:
                results[filename] = {"status": "download_failed", "error": str(e)}

        return results

    def _download_file(self, url: str, dest: Path) -> None:
        """Download a file from URL to destination."""
        temp_path = dest.with_suffix(".tmp")
        try:
            urllib.request.urlretrieve(url, temp_path)
            temp_path.rename(dest)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _load_compounds(self) -> None:
        """Load compound/drug metadata."""
        if self._compounds_data is not None:
            return

        filepath = self.cache_dir / "screened_compounds.csv"
        if not filepath.exists():
            # Try alternative name
            filepath = self.cache_dir / "screened_compounds_rel_8.5.csv"
        if not filepath.exists():
            raise FileNotFoundError("Compounds file not found. Run ensure_data() first.")

        self._compounds_data = {}
        self._target_to_drugs = {}

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                drug_id = int(row.get("DRUG_ID", 0))
                drug_name = row.get("DRUG_NAME", "")
                target = row.get("TARGET", "")
                pathway = row.get("TARGET_PATHWAY", "")
                synonyms = row.get("SYNONYMS", "")

                drug_info = DrugInfo(
                    drug_id=drug_id,
                    drug_name=drug_name,
                    target=target,
                    pathway=pathway,
                    synonyms=synonyms,
                )
                self._compounds_data[drug_id] = drug_info
                # Handle duplicates: store as list if multiple drugs share the same name
                name_key = drug_name.upper()
                if name_key not in self._drug_index:
                    self._drug_index[name_key] = []
                self._drug_index[name_key].append(drug_info)

                # Index by target genes
                for gene in target.split(", "):
                    gene = gene.strip().upper()
                    if gene:
                        if gene not in self._target_to_drugs:
                            self._target_to_drugs[gene] = []
                        self._target_to_drugs[gene].append(drug_id)

    def _load_dose_response(self, dataset: str = "GDSC1") -> None:
        """Load dose-response data."""
        if self._dose_response_data is not None:
            return

        filename = f"{dataset}_fitted_dose_response.csv"
        filepath = self.cache_dir / filename
        if not filepath.exists():
            # Try dated version
            for f in self.cache_dir.glob(f"{dataset}_fitted_dose_response*.csv"):
                filepath = f
                break
        if not filepath.exists():
            raise FileNotFoundError(f"{filename} not found. Run ensure_data() first.")

        self._dose_response_data = {}
        self._cell_line_index = set()

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cosmic_id = int(row.get("COSMIC_ID", 0))
                    drug_id = int(row.get("DRUG_ID", 0))
                    ln_ic50 = float(row.get("LN_IC50", "nan"))
                    auc = float(row.get("AUC", "nan"))
                    z_score = float(row.get("Z_SCORE", "nan"))

                    cell_name = row.get("CELL_LINE_NAME", "")
                    sanger_id = row.get("SANGER_MODEL_ID", "")
                    drug_name = row.get("DRUG_NAME", "")
                    target = row.get("PUTATIVE_TARGET", "")
                    pathway = row.get("PATHWAY_NAME", "")

                    response = DrugResponse(
                        cell_line_name=cell_name,
                        sanger_model_id=sanger_id,
                        cosmic_id=cosmic_id,
                        drug_id=drug_id,
                        drug_name=drug_name,
                        ln_ic50=ln_ic50,
                        auc=auc,
                        z_score=z_score,
                        target=target,
                        pathway=pathway,
                    )

                    # Index by (drug_id, sanger_model_id)
                    key = (drug_id, sanger_id)
                    self._dose_response_data[key] = response
                    self._cell_line_index.add(sanger_id)

                except (ValueError, KeyError):
                    continue

    def get_drugs_targeting_gene(self, gene: str) -> list:
        """Get drugs that target a specific gene."""
        self._load_compounds()
        gene = gene.upper()
        drug_ids = self._target_to_drugs.get(gene, [])
        return [self._compounds_data[did] for did in drug_ids if did in self._compounds_data]

    def get_drug_by_name(self, drug_name: str, dataset: str = "GDSC1") -> DrugInfo | None:
        """Get drug info by name. If multiple drugs share the name, returns one with response data."""
        self._load_compounds()
        drugs = self._drug_index.get(drug_name.upper(), [])
        if not drugs:
            return None
        if len(drugs) == 1:
            return drugs[0]
        # Multiple drugs with same name - prefer one with response data
        self._load_dose_response(dataset)
        for drug in drugs:
            has_data = any(did == drug.drug_id for did, _ in self._dose_response_data.keys())
            if has_data:
                return drug
        return drugs[0]  # Fallback to first if none have data

    def get_drug_response(
        self, drug_id: int, cell_lines: list | None = None, dataset: str = "GDSC1"
    ) -> dict:
        """
        Get drug response data for a drug across cell lines.

        Returns dict: {sanger_model_id: DrugResponse}
        """
        self._load_dose_response(dataset)

        responses = {}
        for (did, sanger_id), response in self._dose_response_data.items():
            if did == drug_id:
                if cell_lines is None or sanger_id in cell_lines:
                    responses[sanger_id] = response
        return responses

    def get_ic50_scores(
        self, drug_id: int, cell_lines: list | None = None, dataset: str = "GDSC1"
    ) -> dict:
        """
        Get LN_IC50 scores for a drug across cell lines.

        Returns dict: {sanger_model_id: ln_ic50}
        """
        responses = self.get_drug_response(drug_id, cell_lines, dataset)
        return {sid: r.ln_ic50 for sid, r in responses.items()}

    def get_auc_scores(
        self, drug_id: int, cell_lines: list | None = None, dataset: str = "GDSC1"
    ) -> dict:
        """
        Get AUC scores for a drug across cell lines.

        Returns dict: {sanger_model_id: auc}
        Lower AUC = more sensitive to drug
        """
        responses = self.get_drug_response(drug_id, cell_lines, dataset)
        return {sid: r.auc for sid, r in responses.items()}

    def get_auc_scores_by_target(
        self, target_gene: str, cell_lines: list | None = None, dataset: str = "GDSC1"
    ) -> dict:
        """
        Get AUC scores pooled across ALL drugs targeting a gene.

        Unlike get_auc_scores (single drug), this pools data from every drug
        whose PUTATIVE_TARGET includes the gene. For cell lines screened against
        multiple drugs targeting the same gene, the minimum AUC (most sensitive)
        is kept.

        Returns dict: {sanger_model_id: auc}
        Lower AUC = more sensitive to drugs targeting this gene.
        """
        self._load_compounds()
        self._load_dose_response(dataset)

        target_gene = target_gene.upper()
        drug_ids = self._target_to_drugs.get(target_gene, [])
        if not drug_ids:
            return {}

        import math

        # Collect AUC per cell line across all drugs targeting this gene
        # For each cell line, keep the minimum AUC (most sensitive response)
        pooled = {}
        for drug_id in drug_ids:
            for (did, sanger_id), response in self._dose_response_data.items():
                if did != drug_id:
                    continue
                if cell_lines is not None and sanger_id not in cell_lines:
                    continue
                if math.isnan(response.auc):
                    continue
                if sanger_id not in pooled or response.auc < pooled[sanger_id]:
                    pooled[sanger_id] = response.auc

        return pooled

    def get_all_auc_scores_by_target(
        self, target_gene: str, cell_lines: list | None = None, dataset: str = "GDSC1"
    ) -> list:
        """
        Get all individual AUC scores across all drugs targeting a gene.

        Unlike get_auc_scores_by_target (which keeps min per cell line), this
        returns every drug×cell_line AUC measurement. Useful for pooled
        statistical tests matching the notebook methodology.

        Returns list of dicts: [{sanger_model_id, drug_id, drug_name, auc}, ...]
        """
        self._load_compounds()
        self._load_dose_response(dataset)

        target_gene = target_gene.upper()
        drug_ids = self._target_to_drugs.get(target_gene, [])
        if not drug_ids:
            return []

        import math

        results = []
        for drug_id in drug_ids:
            drug_info = self._compounds_data.get(drug_id)
            for (did, sanger_id), response in self._dose_response_data.items():
                if did != drug_id:
                    continue
                if cell_lines is not None and sanger_id not in cell_lines:
                    continue
                if math.isnan(response.auc):
                    continue
                results.append(
                    {
                        "sanger_model_id": sanger_id,
                        "drug_id": drug_id,
                        "drug_name": drug_info.drug_name if drug_info else "",
                        "auc": response.auc,
                    }
                )

        return results

    def check_drug_coverage(self, drug_names: list) -> dict:
        """Check which drugs have data in GDSC."""
        self._load_compounds()
        self._load_dose_response()

        results = {}
        for name in drug_names:
            drug = self.get_drug_by_name(name)
            if drug:
                n_responses = sum(
                    1 for (did, _) in self._dose_response_data.keys() if did == drug.drug_id
                )
                results[name] = {
                    "found": True,
                    "drug_id": drug.drug_id,
                    "target": drug.target,
                    "pathway": drug.pathway,
                    "n_cell_lines": n_responses,
                }
            else:
                results[name] = {"found": False}
        return results

    def get_all_cell_lines(self) -> set:
        """Get set of all cell line IDs with drug response data."""
        self._load_dose_response()
        return self._cell_line_index.copy()

    def get_data_version(self) -> dict:
        """Get information about cached data."""
        return {
            "cache_dir": str(self.cache_dir),
            "files_present": [f.name for f in self.cache_dir.iterdir() if f.suffix == ".csv"],
        }

    def get_version_info(self) -> dict:
        """
        Get detailed version metadata for methods sections and reproducibility.

        Returns dict with tool name, version, and file checksums.
        Use this when documenting data versions in papers/reports.
        """
        import json

        manifest_path = Path(__file__).parent / "data_manifest.json"
        manifest = {}
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)

        # Find current version from manifest
        versions = manifest.get("versions", {})
        current_version = None
        version_info = {}
        for v, info in versions.items():
            if info.get("status") == "current":
                current_version = v
                version_info = info
                break

        if not current_version and versions:
            current_version = list(versions.keys())[0]
            version_info = versions[current_version]

        files_info = {}
        for filename in REQUIRED_FILES:
            filepath = self.cache_dir / filename
            file_manifest = version_info.get("files", {}).get(filename, {})

            if filepath.exists():
                sha = file_manifest.get("sha256", "unverified")
                files_info[filename] = sha[:16] + "..." if len(sha) > 16 else sha
            else:
                files_info[filename] = "missing"

        return {
            "tool": "gdsc",
            "version": current_version or "unknown",
            "dataset": version_info.get("dataset", "GDSC1"),
            "data_source": "https://www.cancerrxgene.org/",
            "files": files_info,
            "zenodo_doi": version_info.get("files", {})
            .get(REQUIRED_FILES[0], {})
            .get("zenodo_doi"),
        }
