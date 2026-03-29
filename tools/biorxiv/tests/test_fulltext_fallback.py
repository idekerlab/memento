"""Test full-text retrieval fallback chain: bioRxiv → Europe PMC → abstract."""

import pytest
from tools.biorxiv.client import BiorxivClient, BiorxivPaper


@pytest.fixture
def client():
    return BiorxivClient()


def _make_paper(doi, published_doi="", abstract="Test abstract", jatsxml=""):
    return BiorxivPaper(
        doi=doi,
        title="Test",
        authors="",
        abstract=abstract,
        category="",
        date="",
        version="1",
        jatsxml=jatsxml,
        published_doi=published_doi,
        biorxiv_url=f"https://www.biorxiv.org/content/{doi}",
    )


class TestFulltextFallback:

    def test_europepmc_fallback_with_published_doi(self, client):
        """Paper with a published version in PMC should get full text."""
        # IFIT3 paper: published in J Virol with PMCID
        paper = _make_paper(
            "10.1101/2025.02.17.638785",
            published_doi="10.1128/jvi.00286-25",
        )
        text = client.fetch_paper_text(paper)
        assert len(text) > 5000, f"Expected substantial text, got {len(text)} chars"
        assert "Europe PMC" in text

    def test_abstract_fallback_for_pure_preprint(self, client):
        """Pure preprint not in PMC should fall back to abstract."""
        paper = _make_paper(
            "10.1101/9999.99.99.000000",  # Fake DOI
            abstract="This is a test abstract about viral mechanisms.",
        )
        text = client.fetch_paper_text(paper)
        assert "abstract only" in text.lower()
        assert "viral mechanisms" in text

    def test_no_abstract_returns_error(self, client):
        """Paper with no abstract and no full text should return error."""
        paper = _make_paper("10.1101/9999.99.99.000001", abstract="")
        text = client.fetch_paper_text(paper)
        assert "unavailable" in text.lower()

    def test_helper_try_fetch_url_rejects_short_response(self, client):
        """_try_fetch_url should reject Cloudflare block pages (short responses)."""
        # A valid URL that returns a short page
        result = client._try_fetch_url("https://httpbin.org/robots.txt")
        # robots.txt is very short, should be rejected
        assert result is None or len(result) > 200
