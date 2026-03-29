"""PubMed/PMC MCP Server — exposes PubMed search and PMC full-text as MCP tools.

Run with:  python -m tools.pubmed.server
"""

from mcp.server.fastmcp import FastMCP
from .client import PubMedClient

mcp = FastMCP("pubmed", log_level="INFO")

_client: PubMedClient | None = None


def _get_client() -> PubMedClient:
    global _client
    if _client is None:
        _client = PubMedClient()
    return _client


# ── PubMed Search ────────────────────────────────────────────────────


@mcp.tool()
def search_pubmed(
    query: str,
    max_results: int = 20,
    sort_by: str = "relevance",
) -> dict:
    """Search PubMed for papers matching a query. Returns metadata, authors, and abstracts.

    Args:
        query: PubMed search query. Supports MeSH terms, boolean operators,
               field tags (e.g. "RIG-I[Title] AND TRIM25 AND influenza").
        max_results: Maximum papers to return (default 20).
        sort_by: "relevance" or "date".
    """
    try:
        client = _get_client()
        papers = client.search_pubmed(query, max_results=max_results, sort_by=sort_by)
        return {
            "status": "success",
            "data": {
                "total": len(papers),
                "papers": [p.to_dict() for p in papers],
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "error_type": type(e).__name__}


@mcp.tool()
def get_pubmed_abstract(pmid: str) -> dict:
    """Get the abstract and full metadata for a specific PubMed paper by PMID.

    Args:
        pmid: PubMed ID (e.g. "35123456").
    """
    try:
        client = _get_client()
        paper = client.get_abstract(pmid)
        if paper is None:
            return {"status": "error", "message": f"Paper with PMID {pmid} not found"}
        return {"status": "success", "data": paper.to_dict()}
    except Exception as e:
        return {"status": "error", "message": str(e), "error_type": type(e).__name__}


# ── PMC Full Text ────────────────────────────────────────────────────


@mcp.tool()
def get_pmc_fulltext(identifier: str) -> dict:
    """Retrieve full text of a paper from PubMed Central via Europe PMC.

    Accepts PMCID, PMID, or DOI. Returns plain text (XML tags stripped).
    Only works for open-access papers deposited in PMC.

    Args:
        identifier: PMCID (e.g. "PMC1234567"), PMID, or DOI.
    """
    try:
        client = _get_client()
        text = client.get_pmc_fulltext(identifier)
        if text is None:
            return {
                "status": "error",
                "message": f"Full text not available for {identifier}. "
                "Paper may not be open-access or not in PMC.",
            }
        return {
            "status": "success",
            "data": {
                "identifier": identifier,
                "source": "Europe PMC",
                "text_length": len(text),
                "text": text[:50000],  # Cap at 50k chars
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "error_type": type(e).__name__}


@mcp.tool()
def search_pmc_fulltext(
    query: str,
    max_results: int = 20,
) -> dict:
    """Search Europe PMC for open-access papers with full text available.

    Similar to search_pubmed but filters for papers that have full text
    in PubMed Central, so you can immediately retrieve the full text.

    Args:
        query: Search query (e.g. "RIG-I TRIM25 influenza ubiquitination").
        max_results: Maximum papers to return (default 20).
    """
    try:
        client = _get_client()
        papers = client.search_pmc_fulltext(query, max_results=max_results)
        return {
            "status": "success",
            "data": {
                "total": len(papers),
                "papers": [p.to_dict() for p in papers],
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "error_type": type(e).__name__}


# ── Entry point ──────────────────────────────────────────────────────


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
