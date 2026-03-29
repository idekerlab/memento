"""Tests for PubMed/PMC client — runs against live APIs.

These tests make real API calls to NCBI and Europe PMC.
They verify the client works end-to-end with actual data.
"""

import pytest
from tools.pubmed.client import PubMedClient, PubMedPaper


@pytest.fixture(scope="module")
def client():
    return PubMedClient()


# ── PubMed Search ────────────────────────────────────────────────────


class TestSearchPubMed:
    def test_search_returns_papers(self, client):
        papers = client.search_pubmed("RIG-I TRIM25 influenza", max_results=5)
        assert len(papers) > 0
        assert all(isinstance(p, PubMedPaper) for p in papers)

    def test_papers_have_metadata(self, client):
        papers = client.search_pubmed("RIG-I TRIM25 influenza", max_results=3)
        for paper in papers:
            assert paper.pmid, "Paper should have a PMID"
            assert paper.title, "Paper should have a title"
            assert len(paper.authors) > 0, "Paper should have authors"
            assert paper.first_author, "Paper should have a first author"

    def test_papers_have_abstracts(self, client):
        papers = client.search_pubmed("RIG-I ubiquitination innate immunity", max_results=3)
        papers_with_abstracts = [p for p in papers if p.abstract]
        assert len(papers_with_abstracts) > 0, "At least some papers should have abstracts"

    def test_empty_query_returns_empty(self, client):
        papers = client.search_pubmed("xyznonexistentquery12345678", max_results=5)
        assert papers == []

    def test_sort_by_date(self, client):
        papers = client.search_pubmed("influenza RIG-I", max_results=3, sort_by="date")
        assert len(papers) > 0


# ── Abstract Retrieval ───────────────────────────────────────────────


class TestGetAbstract:
    def test_get_known_paper(self, client):
        # PMID 17392790: Gack et al. 2007, "TRIM25 RING-finger E3 ubiquitin
        # ligase is essential for RIG-I-mediated antiviral activity"
        paper = client.get_abstract("17392790")
        assert paper is not None
        assert paper.pmid == "17392790"
        assert "TRIM25" in paper.title or "RIG-I" in paper.title
        assert paper.abstract, "Should have an abstract"
        assert len(paper.authors) > 0

    def test_nonexistent_pmid(self, client):
        paper = client.get_abstract("99999999999")
        assert paper is None


# ── PMC Full-Text Retrieval ──────────────────────────────────────────


class TestGetPMCFulltext:
    def test_by_pmcid(self, client):
        # PMC1865070: Gack et al. 2007 (same paper, known to be in PMC)
        text = client.get_pmc_fulltext("PMC1865070")
        if text is not None:
            assert len(text) > 1000, "Full text should be substantial"
            assert "Europe PMC" in text

    def test_by_doi(self, client):
        # DOI for a well-known open-access paper
        text = client.get_pmc_fulltext("10.1038/nature05858")
        # May or may not resolve — test that it doesn't crash
        if text is not None:
            assert len(text) > 500

    def test_nonexistent_returns_none(self, client):
        text = client.get_pmc_fulltext("PMC0000000")
        assert text is None


# ── PMC Full-Text Search ─────────────────────────────────────────────


class TestSearchPMCFulltext:
    def test_search_returns_papers(self, client):
        papers = client.search_pmc_fulltext("RIG-I TRIM25 influenza", max_results=5)
        assert len(papers) > 0
        assert all(isinstance(p, PubMedPaper) for p in papers)

    def test_papers_have_pmcid(self, client):
        papers = client.search_pmc_fulltext("TRIM25 ubiquitination", max_results=3)
        papers_with_pmcid = [p for p in papers if p.pmcid]
        assert len(papers_with_pmcid) > 0, "PMC search results should have PMCIDs"


# ── Identifier Resolution ────────────────────────────────────────────


class TestIdentifierResolution:
    def test_pmcid_passthrough(self, client):
        result = client._resolve_to_pmcid("PMC1865070")
        assert result == "PMC1865070"

    def test_doi_resolution(self, client):
        # This DOI should resolve to a PMCID
        result = client._resolve_to_pmcid("10.1038/nature05858")
        # May or may not resolve depending on Europe PMC coverage
        # Just verify it doesn't crash
        assert result is None or result.startswith("PMC")

    def test_pmid_resolution(self, client):
        result = client._resolve_to_pmcid("17392790")
        # Should resolve to PMC1865070 or similar
        assert result is None or result.startswith("PMC")


# ── Data Model ────────────────────────────────────────────────────────


class TestPubMedPaper:
    def test_to_dict(self):
        paper = PubMedPaper(pmid="12345", title="Test Paper", authors=["Smith J"])
        d = paper.to_dict()
        assert d["pmid"] == "12345"
        assert d["title"] == "Test Paper"
        assert d["authors"] == ["Smith J"]
        assert "first_author" in d
        assert "corresponding_author" in d
