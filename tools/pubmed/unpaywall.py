"""Unpaywall client — find legal free-fulltext URLs for a DOI.

Unpaywall (https://unpaywall.org) indexes ~30M scholarly works with
author-deposited preprints, institutional-repository copies, and
publisher OA versions. Its canonical use in this project: before
escalating a paywalled paper to a human courier (dexter), ask Unpaywall
whether a free version exists that the existing pubmed/biorxiv tools
don't already know about (typically author manuscripts on arXiv,
bioRxiv, or institutional repositories).

API reference: https://unpaywall.org/products/api

Rate limit: 100,000 requests/day per email. An email address is
required on every request as a politeness signal — Unpaywall uses
it to reach out if the caller misbehaves, not for authentication.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


UNPAYWALL_BASE = "https://api.unpaywall.org/v2"

# Default contact email if UNPAYWALL_EMAIL env var is not set. Unpaywall
# does not validate this; it's a politeness hint so they can reach the
# operator if a caller starts misbehaving. Override with UNPAYWALL_EMAIL
# in ~/.claude/settings.json or the MCP server's environment if you want
# Unpaywall contact to reach you directly.
DEFAULT_EMAIL = "ndexbio-agents@users.noreply.github.com"


@dataclass
class OALocation:
    """One free-fulltext location reported by Unpaywall for a DOI.

    host_type: "publisher" (the journal itself hosts a free copy, e.g.
        an OA journal or a paper under an open-access policy) vs.
        "repository" (author-deposited: arXiv, bioRxiv, institutional
        repositories, PMC).

    version: "publishedVersion" (final typeset PDF) > "acceptedVersion"
        (post-peer-review, pre-typesetting, a.k.a. postprint) >
        "submittedVersion" (preprint, pre-peer-review). Agents should
        prefer publishedVersion when present and note the version when
        citing.
    """

    url: str
    url_for_pdf: str | None
    url_for_landing_page: str | None
    host_type: str  # "publisher" or "repository"
    version: str  # publishedVersion | acceptedVersion | submittedVersion
    license: str | None
    repository_institution: str | None
    is_best: bool

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> "OALocation":
        return cls(
            url=d.get("url", ""),
            url_for_pdf=d.get("url_for_pdf"),
            url_for_landing_page=d.get("url_for_landing_page"),
            host_type=d.get("host_type", ""),
            version=d.get("version", ""),
            license=d.get("license"),
            repository_institution=d.get("repository_institution"),
            is_best=bool(d.get("is_best", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "url_for_pdf": self.url_for_pdf,
            "url_for_landing_page": self.url_for_landing_page,
            "host_type": self.host_type,
            "version": self.version,
            "license": self.license,
            "repository_institution": self.repository_institution,
            "is_best": self.is_best,
        }


@dataclass
class UnpaywallResult:
    """Parsed Unpaywall response for a single DOI."""

    doi: str
    is_oa: bool
    genre: str  # "journal-article", "posted-content" (preprints), etc.
    title: str
    journal_name: str
    locations: list[OALocation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "doi": self.doi,
            "is_oa": self.is_oa,
            "genre": self.genre,
            "title": self.title,
            "journal_name": self.journal_name,
            "locations": [loc.to_dict() for loc in self.locations],
        }


class UnpaywallClient:
    """Client for Unpaywall single-DOI lookups.

    This client does NOT fetch the fulltext itself — it only returns
    URLs where free versions exist. Fetching those URLs and extracting
    text is a separate concern (one URL may be a PDF, another an HTML
    landing page, a third a preprint-server API endpoint).
    """

    def __init__(self, email: str | None = None, rate_limit_delay: float = 0.1):
        self._email = email or os.environ.get("UNPAYWALL_EMAIL") or DEFAULT_EMAIL
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "ndexbio-agents/0.1 (https://github.com/ndexbio/ndexbio)"
        })
        self._rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Strip 'doi:' prefix, whitespace, and any URL wrapping."""
        doi = doi.strip()
        if doi.lower().startswith("doi:"):
            doi = doi[4:].strip()
        for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
            if doi.lower().startswith(prefix):
                doi = doi[len(prefix):]
                break
        return doi

    def find_free_fulltext(self, doi: str) -> UnpaywallResult | None:
        """Look up free-fulltext locations for a DOI.

        Returns:
            UnpaywallResult with is_oa and all known free locations if
            the DOI is in Unpaywall's index (roughly any paper with a
            Crossref record since ~2010). Returns None if the DOI is
            not found (HTTP 404 — either not a real DOI or not yet
            indexed). Raises on other errors (network, 5xx, rate limit).
        """
        doi_normalized = self._normalize_doi(doi)
        if not doi_normalized:
            return None

        self._rate_limit()
        url = f"{UNPAYWALL_BASE}/{doi_normalized}"
        params = {"email": self._email}
        resp = self._session.get(url, params=params, timeout=30)
        self._last_request_time = time.time()

        if resp.status_code == 404:
            return None
        if resp.status_code == 422:
            # Malformed DOI per Unpaywall — treat like "not found" rather
            # than raising, since a validation-style failure is actionable
            # by the caller (wrong identifier) not the operator.
            return None
        resp.raise_for_status()

        data = resp.json()
        locations_raw = data.get("oa_locations") or []
        locations = [OALocation.from_api(loc) for loc in locations_raw]

        return UnpaywallResult(
            doi=data.get("doi", doi_normalized),
            is_oa=bool(data.get("is_oa", False)),
            genre=data.get("genre", ""),
            title=(data.get("title") or "").strip(),
            journal_name=data.get("journal_name") or "",
            locations=locations,
        )
