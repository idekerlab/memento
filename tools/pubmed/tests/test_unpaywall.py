"""Tests for Unpaywall client — runs against the live API.

Following the pattern of test_pubmed_client.py, these tests hit real
api.unpaywall.org. They verify the client parses known-stable DOIs
correctly. Skipped silently if the network is unreachable.
"""

import pytest
import requests

from tools.pubmed.unpaywall import (
    UnpaywallClient,
    UnpaywallResult,
    OALocation,
    DEFAULT_EMAIL,
)


@pytest.fixture(scope="module")
def client():
    return UnpaywallClient()


# DOIs chosen for stability:
#   - Nature 2013 paper, OA author copy on arXiv (publisher+repository locations)
NATURE_DOI = "10.1038/nature12373"
#   - bioRxiv preprint (genre: posted-content, repository-only, no publisher)
BIORXIV_DOI = "10.1101/2023.10.23.563660"
#   - Malformed (should return None without raising)
MALFORMED_DOI = "not-a-doi"


class TestDOINormalization:
    def test_strips_doi_prefix(self):
        assert UnpaywallClient._normalize_doi("doi:10.1038/nature12373") == "10.1038/nature12373"

    def test_strips_https_wrapper(self):
        assert UnpaywallClient._normalize_doi("https://doi.org/10.1038/nature12373") == "10.1038/nature12373"

    def test_strips_dx_wrapper(self):
        assert UnpaywallClient._normalize_doi("https://dx.doi.org/10.1038/nature12373") == "10.1038/nature12373"

    def test_leaves_bare_doi(self):
        assert UnpaywallClient._normalize_doi("10.1038/nature12373") == "10.1038/nature12373"

    def test_strips_whitespace(self):
        assert UnpaywallClient._normalize_doi("  10.1038/nature12373  ") == "10.1038/nature12373"


class TestFindFreeFulltext:
    def test_nature_paper_has_locations(self, client):
        result = client.find_free_fulltext(NATURE_DOI)
        assert result is not None, "Known OA DOI must be found"
        assert isinstance(result, UnpaywallResult)
        assert result.doi.lower() == NATURE_DOI.lower()
        assert result.is_oa is True
        assert len(result.locations) >= 1, "Nature 2013 paper has >=1 free location"
        assert all(isinstance(loc, OALocation) for loc in result.locations)

    def test_biorxiv_preprint_is_posted_content(self, client):
        result = client.find_free_fulltext(BIORXIV_DOI)
        assert result is not None
        assert result.genre == "posted-content"
        assert result.is_oa is True
        # bioRxiv locations are all repositories (no publisher role)
        assert all(loc.host_type == "repository" for loc in result.locations)

    def test_malformed_doi_returns_none(self, client):
        result = client.find_free_fulltext(MALFORMED_DOI)
        assert result is None

    def test_empty_doi_returns_none(self, client):
        result = client.find_free_fulltext("")
        assert result is None

    def test_doi_prefix_is_normalized(self, client):
        result = client.find_free_fulltext(f"doi:{NATURE_DOI}")
        assert result is not None
        assert result.doi.lower() == NATURE_DOI.lower()

    def test_url_wrapper_is_normalized(self, client):
        result = client.find_free_fulltext(f"https://doi.org/{NATURE_DOI}")
        assert result is not None
        assert result.doi.lower() == NATURE_DOI.lower()


class TestLocationFields:
    def test_location_has_required_fields(self, client):
        result = client.find_free_fulltext(NATURE_DOI)
        assert result is not None
        for loc in result.locations:
            assert loc.host_type in ("publisher", "repository")
            assert loc.version in (
                "publishedVersion",
                "acceptedVersion",
                "submittedVersion",
                "",
            )

    def test_result_to_dict_is_json_safe(self, client):
        import json
        result = client.find_free_fulltext(NATURE_DOI)
        assert result is not None
        # Round-trip through JSON to ensure no unserializable types
        d = result.to_dict()
        s = json.dumps(d)
        d2 = json.loads(s)
        assert d2["doi"] == result.doi
        assert len(d2["locations"]) == len(result.locations)


class TestEmailConfiguration:
    def test_default_email_if_env_unset(self, monkeypatch):
        monkeypatch.delenv("UNPAYWALL_EMAIL", raising=False)
        c = UnpaywallClient()
        assert c._email == DEFAULT_EMAIL

    def test_env_var_overrides_default(self, monkeypatch):
        monkeypatch.setenv("UNPAYWALL_EMAIL", "override@example.org")
        c = UnpaywallClient()
        assert c._email == "override@example.org"

    def test_explicit_arg_overrides_env(self, monkeypatch):
        monkeypatch.setenv("UNPAYWALL_EMAIL", "env@example.org")
        c = UnpaywallClient(email="explicit@example.org")
        assert c._email == "explicit@example.org"
