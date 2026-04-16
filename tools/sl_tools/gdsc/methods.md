# GDSC Drug Sensitivity Data - Methods and Usage

## Overview

The Genomics of Drug Sensitivity in Cancer (GDSC) project measures drug response across hundreds of cancer cell lines. This tool provides access to drug sensitivity data (IC50, AUC) for testing gene-drug synthetic lethality hypotheses.

**Data Source**: https://www.cancerrxgene.org/
**Data Version**: GDSC1 release 8.5
**Citation**: Yang et al., Nucleic Acids Research 2013

## Data Description

### Coverage
- **Cell Lines**: 932 cancer cell lines
- **Drugs**: ~500 compounds
- **Datasets**: GDSC1 (primary), GDSC2 (available but not cached)

### Data Types

#### GDSC1_fitted_dose_response.csv
Drug response measurements for each cell line × drug combination.
- **LN_IC50**: Natural log of IC50 (lower = more sensitive)
- **AUC**: Area under dose-response curve (lower = more sensitive)
- **Z_SCORE**: Normalized sensitivity score

#### screened_compounds.csv
Drug metadata and target annotations.
- **DRUG_ID**: Unique identifier
- **DRUG_NAME**: Compound name
- **TARGET**: Target gene(s)
- **TARGET_PATHWAY**: Pathway classification

### Metric Interpretation

**AUC (Area Under Curve)**:
- Range: 0-1
- **Lower AUC = more sensitive** to drug
- Preferred metric for binary sensitive/resistant classification

**LN_IC50 (Log IC50)**:
- Natural log of concentration for 50% inhibition
- **Lower LN_IC50 = more sensitive**
- Better for dose-response modeling

## Client API

### Initialization

```python
from tools.gdsc.client import GDSCClient

# Auto-downloads data on first use
client = GDSCClient(auto_download=True)

# Verify data is available
status = client.ensure_data()
```

### Core Methods

#### `get_drug_by_name(drug_name: str, dataset: str = "GDSC1") -> DrugInfo`
**Purpose**: Look up drug by name and verify it exists
```python
drug = client.get_drug_by_name("Olaparib")
# Returns: DrugInfo(drug_id=1017, drug_name="Olaparib", target="PARP1, PARP2", pathway="DNA replication")
```

**Note**: Some drugs have multiple entries with different IDs. This method returns the one with response data in the specified dataset.

#### `get_drugs_targeting_gene(gene: str) -> list[DrugInfo]`
**Purpose**: Find all drugs targeting a specific gene
```python
atr_drugs = client.get_drugs_targeting_gene("ATR")
# Returns: [DrugInfo(drug_name="AZD6738", ...), DrugInfo(drug_name="AZ20", ...), ...]
```

#### `get_auc_scores(drug_id: int, cell_lines: list = None, dataset: str = "GDSC1") -> dict`
**Purpose**: Get AUC scores for a drug across cell lines
```python
scores = client.get_auc_scores(1017)  # Olaparib
# Returns: {"SIDM00001": 0.85, "SIDM00023": 0.72, ...}
```

#### `get_ic50_scores(drug_id: int, cell_lines: list = None, dataset: str = "GDSC1") -> dict`
**Purpose**: Get LN_IC50 scores for a drug across cell lines
```python
scores = client.get_ic50_scores(1017)
# Returns: {"SIDM00001": 2.3, "SIDM00023": 1.1, ...}
```

## Hypothesis Testing Patterns

### Pattern 1: Gene-Drug Synthetic Lethality

**Question**: Does loss of gene_a sensitize cells to drug?

**Method**:
1. Get mutation status from DepMap (GDSC lacks mutation data)
2. Translate cell line IDs from DepMap to GDSC format
3. Compare drug AUC between mutant and wildtype groups
4. Use Mann-Whitney U test for statistical significance

**Code**:
```python
from tools.depmap.client import DepMapClient
from tools.gdsc.hypothesis_tester import GDSCHypothesisTester

# Get mutation status from DepMap
depmap = DepMapClient(version="25Q3")
mutants_depmap = depmap.get_cell_lines_with_mutation("BRCA2")
wildtype_depmap = depmap.get_cell_lines_without_mutation("BRCA2")

# Translate to Sanger IDs
mutants_sanger = depmap.translate_to_sanger_ids(mutants_depmap)
wildtype_sanger = depmap.translate_to_sanger_ids(wildtype_depmap)

# Test drug sensitivity
tester = GDSCHypothesisTester()
result = tester.test_gene_drug_sl(
    claim_id="BRCA2_Olaparib",
    claim_text="Loss of BRCA2 sensitizes to Olaparib",
    gene_a="BRCA2",
    drug_name="Olaparib",
    mutant_cell_lines=mutants_sanger,
    wildtype_cell_lines=wildtype_sanger,
    metric="auc"
)
```

**Result interpretation**:
- `effect_size < 0`: Mutant cells have lower AUC (more sensitive) → supports hypothesis
- `effect_size > 0`: Mutant cells have higher AUC (less sensitive) → contradicts hypothesis
- Threshold: `|effect_size| > 0.05` with `p_value < 0.05` for significance

### Pattern 2: Drug Target Validation

**Question**: Which drugs target ATR and have good data coverage?

```python
# Find ATR-targeting drugs
atr_drugs = client.get_drugs_targeting_gene("ATR")

# Check data availability for each
for drug in atr_drugs:
    scores = client.get_auc_scores(drug.drug_id)
    print(f"{drug.drug_name}: {len(scores)} cell lines with data")
```

## Integration with DepMap

### Cell Line ID Translation

GDSC uses Sanger Model IDs (SIDM*), while DepMap uses ACH-* format. Translation is required for integration:

```python
from tools.depmap.client import DepMapClient

depmap = DepMapClient(version="25Q3")

# Get mutants from DepMap
mutants_depmap = depmap.get_cell_lines_with_mutation("ARID1A")
# ["ACH-000001", "ACH-000023", ...]

# Translate to Sanger IDs
mutants_sanger = depmap.translate_to_sanger_ids(mutants_depmap)
# ["SIDM00001", "SIDM00023", ...]

# Use Sanger IDs in GDSC queries
```

**Coverage note**: Not all DepMap cell lines are in GDSC. Translation may reduce sample size.

### Integration Workflow

```
DepMap                      GDSC
-------                     ----
get_cell_lines_with_mutation()
        |
        v
translate_to_sanger_ids()
        |
        +-----------------> get_auc_scores(cell_lines=sanger_ids)
        |                            |
        v                            v
Statistical comparison (Mann-Whitney U test)
```

## Drug Lookup Considerations

### Duplicate Drug Names

Some drugs have multiple entries in the compounds file:
```
AZD6738 (ID: 1394) - has response data
AZD6738 (ID: 1917) - no response data in GDSC1
```

The `get_drug_by_name()` method automatically returns the entry with response data.

### Target Annotations

Target field may contain multiple genes:
- `"ATR"` - single target
- `"MTOR, ATR"` - dual target
- `"PARP1, PARP2"` - family targets

Search by gene finds all drugs where gene appears in target list.

## Limitations

### Data Limitations
- **No mutation data**: GDSC doesn't provide mutation calls; must use DepMap
- **Cell line panel**: Different from DepMap; ~60-70% overlap after ID translation
- **Dataset versions**: GDSC1 cached; GDSC2 available but not pre-downloaded

### ID Translation
- **Incomplete mapping**: Some DepMap lines lack Sanger IDs
- **Sample size reduction**: Typically lose 30-40% of cell lines in translation

### Drug Response Interpretation
- **Context-dependent**: Drug sensitivity varies by cancer type
- **Technical variation**: Plate effects, batch effects possible
- **No single-agent essentiality**: Measures drug effect, not basal dependency

## Anti-Hallucination Protocol

**Always verify before querying**:
```python
# 1. Check data availability
status = client.ensure_data()
if any(s.get("status") == "missing" for s in status.values() if isinstance(s, dict)):
    raise RuntimeError("Data not available")

# 2. Verify drug exists
drug = client.get_drug_by_name("MyDrug")
if drug is None:
    return {"error": "Drug not found in GDSC"}

# 3. Check response data exists
scores = client.get_auc_scores(drug.drug_id)
if len(scores) < 50:
    return {"warning": f"Limited data: only {len(scores)} cell lines"}

# 4. Only then proceed with analysis
```
