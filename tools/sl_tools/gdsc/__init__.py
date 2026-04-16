"""
GDSC (Genomics of Drug Sensitivity in Cancer) Tools

Provides access to drug sensitivity data for testing gene-drug synthetic lethality.
"""

from .client import GDSCClient
from .hypothesis_tester import GDSCHypothesisTester, test_gene_drug_sl

__all__ = ["GDSCClient", "GDSCHypothesisTester", "test_gene_drug_sl"]
