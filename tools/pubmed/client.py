"""PubMed/PMC client for searching published literature and retrieving full text.

Uses NCBI E-utilities for PubMed search and abstract retrieval,
and Europe PMC REST API for open-access full-text retrieval.
"""

from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

import requests


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


@dataclass
class PubMedPaper:
    """Represents a PubMed paper with metadata."""

    pmid: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    first_author: str = ""
    corresponding_author: str = ""
    journal: str = ""
    year: str = ""
    abstract: str = ""
    doi: str = ""
    pmcid: str = ""
    publication_date: str = ""

    def to_dict(self) -> dict:
        return {
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors,
            "first_author": self.first_author,
            "corresponding_author": self.corresponding_author,
            "journal": self.journal,
            "year": self.year,
            "abstract": self.abstract,
            "doi": self.doi,
            "pmcid": self.pmcid,
            "publication_date": self.publication_date,
        }


class PubMedClient:
    """Client for PubMed search and PMC full-text retrieval.

    Combines NCBI E-utilities (search, abstracts) with Europe PMC
    (full-text XML) into a unified interface.
    """

    def __init__(self, rate_limit_delay: float = 0.4):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "ndexbio-agents/0.1 (https://github.com/ndexbio/ndexbio)"
        })
        self._rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

        # NCBI API key raises limit from 3/s to 10/s
        self._api_key = os.environ.get("NCBI_API_KEY", "")
        if self._api_key:
            self._rate_limit_delay = 0.15

    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _request(self, url: str, params: dict | None = None) -> requests.Response:
        """Make a rate-limited GET request with retry on 429."""
        for attempt in range(3):
            self._rate_limit()
            resp = self._session.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 1.0 * (attempt + 1)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()  # raise on final 429
        return resp  # unreachable but satisfies type checker

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        """Make a rate-limited GET request expecting JSON."""
        return self._request(url, params).json()

    def _get_text(self, url: str, params: dict | None = None) -> str:
        """Make a rate-limited GET request expecting text/XML."""
        return self._request(url, params).text

    def _eutils_params(self, **kwargs) -> dict:
        """Add common eutils parameters (api_key if set)."""
        params = dict(kwargs)
        if self._api_key:
            params["api_key"] = self._api_key
        return params

    # ── PubMed Search ────────────────────────────────────────────────

    def search_pubmed(
        self,
        query: str,
        max_results: int = 20,
        sort_by: str = "relevance",
    ) -> list[PubMedPaper]:
        """Search PubMed and return papers with metadata and abstracts.

        Two-step process: esearch to get PMIDs, then efetch to get
        full records including abstracts and author details.

        Args:
            query: PubMed search query (supports MeSH terms, boolean operators).
            max_results: Maximum number of results.
            sort_by: Sort order — "relevance" or "date".
        """
        # Step 1: Search for PMIDs
        search_params = self._eutils_params(
            db="pubmed",
            term=query,
            retmax=max_results,
            retmode="json",
            sort=sort_by,
        )
        search_data = self._get_json(f"{EUTILS_BASE}/esearch.fcgi", search_params)
        pmids = search_data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return []

        # Step 2: Fetch full records via efetch XML
        fetch_params = self._eutils_params(
            db="pubmed",
            id=",".join(pmids),
            rettype="xml",
            retmode="xml",
        )
        xml_text = self._get_text(f"{EUTILS_BASE}/efetch.fcgi", fetch_params)
        return self._parse_pubmed_xml(xml_text)

    def _parse_pubmed_xml(self, xml_text: str) -> list[PubMedPaper]:
        """Parse PubMed efetch XML into PubMedPaper objects."""
        papers = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return papers

        for article in root.findall(".//PubmedArticle"):
            paper = PubMedPaper()

            # PMID
            pmid_el = article.find(".//PMID")
            if pmid_el is not None:
                paper.pmid = pmid_el.text or ""

            # Title
            title_el = article.find(".//ArticleTitle")
            if title_el is not None:
                paper.title = "".join(title_el.itertext()).strip()

            # Authors
            author_list = article.findall(".//Author")
            for i, author in enumerate(author_list):
                last = author.findtext("LastName", "")
                first = author.findtext("ForeName", "")
                initials = author.findtext("Initials", "")
                name = f"{last} {first}".strip() if first else f"{last} {initials}".strip()
                if name:
                    paper.authors.append(name)
                    if i == 0:
                        paper.first_author = name

                    # Corresponding author: look for affiliation with email
                    # or last author as fallback
                    affiliation_el = author.find(".//AffiliationInfo/Affiliation")
                    if affiliation_el is not None and affiliation_el.text:
                        if "@" in affiliation_el.text:
                            paper.corresponding_author = name

            # If no corresponding author found via email, use last author
            if not paper.corresponding_author and paper.authors:
                paper.corresponding_author = paper.authors[-1]

            # Journal
            paper.journal = article.findtext(".//Journal/Title", "")

            # Publication date
            pub_date = article.find(".//PubDate")
            if pub_date is not None:
                year = pub_date.findtext("Year", "")
                month = pub_date.findtext("Month", "")
                day = pub_date.findtext("Day", "")
                paper.year = year
                parts = [p for p in [year, month, day] if p]
                paper.publication_date = "-".join(parts)

            # Abstract — handle structured abstracts
            abstract_parts = []
            for abs_text in article.findall(".//AbstractText"):
                label = abs_text.get("Label", "")
                text = "".join(abs_text.itertext()).strip()
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            paper.abstract = "\n".join(abstract_parts)

            # DOI and PMCID from ArticleIdList
            for aid in article.findall(".//ArticleId"):
                id_type = aid.get("IdType", "")
                if id_type == "doi" and aid.text:
                    paper.doi = aid.text
                elif id_type == "pmc" and aid.text:
                    paper.pmcid = aid.text

            papers.append(paper)

        return papers

    # ── Abstract Retrieval ───────────────────────────────────────────

    def get_abstract(self, pmid: str) -> Optional[PubMedPaper]:
        """Get a single paper's abstract and metadata by PMID.

        Args:
            pmid: PubMed ID (numeric string).

        Returns:
            PubMedPaper with full metadata and abstract, or None if not found.
        """
        fetch_params = self._eutils_params(
            db="pubmed",
            id=pmid,
            rettype="xml",
            retmode="xml",
        )
        xml_text = self._get_text(f"{EUTILS_BASE}/efetch.fcgi", fetch_params)
        papers = self._parse_pubmed_xml(xml_text)
        return papers[0] if papers else None

    # ── PMC Full-Text Retrieval ──────────────────────────────────────

    def get_pmc_fulltext(self, identifier: str) -> Optional[str]:
        """Get full-text from Europe PMC by PMCID, PMID, or DOI.

        Args:
            identifier: PMCID (e.g., "PMC1234567"), PMID, or DOI.

        Returns:
            Full text as plain text (XML tags stripped), or None if unavailable.
        """
        pmcid = self._resolve_to_pmcid(identifier)
        if not pmcid:
            return None

        try:
            xml_text = self._get_text(f"{EPMC_BASE}/{pmcid}/fullTextXML")
            if len(xml_text) < 500:
                return None

            # Strip XML tags for readability
            text = re.sub(r"<[^>]+>", " ", xml_text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 500:
                return None

            return f"[Source: Europe PMC {pmcid}]\n\n{text}"
        except Exception:
            return None

    def _resolve_to_pmcid(self, identifier: str) -> Optional[str]:
        """Resolve a DOI, PMID, or PMCID to a PMCID via Europe PMC search."""
        identifier = identifier.strip()

        # Already a PMCID
        if identifier.upper().startswith("PMC"):
            return identifier

        # Build search query based on identifier type
        if identifier.startswith("10.") or identifier.startswith("doi:"):
            doi = identifier.replace("doi:", "").strip()
            query = f'DOI:"{doi}"'
        elif identifier.isdigit():
            query = f"EXT_ID:{identifier}"
        else:
            query = identifier

        try:
            params = {"query": query, "format": "json", "pageSize": 1}
            data = self._get_json(f"{EPMC_BASE}/search", params)
            if data.get("hitCount", 0) > 0:
                result = data["resultList"]["result"][0]
                return result.get("pmcid")
        except Exception:
            pass
        return None

    # ── PMC Full-Text Search ─────────────────────────────────────────

    def search_pmc_fulltext(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[PubMedPaper]:
        """Search Europe PMC for open-access papers with full text available.

        Args:
            query: Search query.
            max_results: Maximum results to return.

        Returns:
            List of PubMedPaper objects for papers with full text in PMC.
        """
        params = {
            "query": f"({query}) AND HAS_FT:y",
            "format": "json",
            "pageSize": min(max_results, 100),
        }

        try:
            data = self._get_json(f"{EPMC_BASE}/search", params)
        except Exception:
            return []

        papers = []
        for item in data.get("resultList", {}).get("result", []):
            paper = PubMedPaper(
                pmid=item.get("pmid", ""),
                title=item.get("title", "").strip(),
                journal=item.get("journalTitle", ""),
                doi=item.get("doi", ""),
                pmcid=item.get("pmcid", ""),
                publication_date=item.get("firstPublicationDate", ""),
                year=item.get("pubYear", ""),
            )

            # Parse authors
            if "authorList" in item and "author" in item["authorList"]:
                for i, author in enumerate(item["authorList"]["author"]):
                    name = author.get("fullName", "")
                    if not name:
                        last = author.get("lastName", "")
                        first = author.get("firstName", "")
                        name = f"{last} {first}".strip()
                    if name:
                        paper.authors.append(name)
                        if i == 0:
                            paper.first_author = name

            if not paper.corresponding_author and paper.authors:
                paper.corresponding_author = paper.authors[-1]

            # Abstract
            paper.abstract = item.get("abstractText", "").strip()

            papers.append(paper)

        return papers[:max_results]
