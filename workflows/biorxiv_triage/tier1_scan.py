"""Tier 1: Daily bioRxiv scan for HPMI-relevant papers.

This script implements the high-volume discovery scan. It:
1. Fetches recent papers from bioRxiv
2. Filters by HPMI keywords (configurable per interest group)
3. Scores abstracts for relevance
4. Produces a daily summary suitable for posting to NDEx

Designed to be called by an agent or scheduler. The scoring/annotation
step should be delegated to an LLM (fast model) for natural language
assessment; this module provides the retrieval and filtering infrastructure.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.biorxiv.client import BiorxivClient, BiorxivPaper


# Default keyword groups for influenza HPMI scanning
INFLUENZA_HPMI_KEYWORDS = {
    "virus": [
        "influenza", "flu virus", "IAV", "IBV",
        "H1N1", "H3N2", "H5N1", "H5N8", "H7N9",
    ],
    "host_factors": [
        "interferon", "innate immunity", "ISG", "restriction factor",
        "host factor", "host-pathogen",
    ],
    "mechanisms": [
        "viral replication", "polymerase", "neuraminidase", "hemagglutinin",
        "NS1", "NEP", "PB2", "NP",
        "viral evasion", "immune escape", "pathogenesis",
    ],
}


def get_all_keywords() -> list[str]:
    """Flatten keyword groups into a single list."""
    keywords = []
    for group in INFLUENZA_HPMI_KEYWORDS.values():
        keywords.extend(group)
    return keywords


def scan_biorxiv(
    interval_days: int = 3,
    max_papers: int = 500,
    extra_keywords: Optional[list[str]] = None,
) -> dict:
    """Run a Tier 1 scan of recent bioRxiv papers.

    Args:
        interval_days: How many days back to scan.
        max_papers: Maximum papers to retrieve from bioRxiv.
        extra_keywords: Additional keywords beyond the defaults.

    Returns:
        Dict with scan metadata and list of matched papers.
    """
    client = BiorxivClient()

    # Fetch recent papers
    all_papers = client.get_all_recent_papers(
        interval_days=interval_days,
        max_papers=max_papers,
    )

    # Build keyword list
    keywords = get_all_keywords()
    if extra_keywords:
        keywords.extend(extra_keywords)

    # Filter by keywords (any match)
    matched = client.search_by_keywords(all_papers, keywords, match_mode="any")

    return {
        "scan_date": date.today().isoformat(),
        "interval_days": interval_days,
        "total_scanned": len(all_papers),
        "total_matched": len(matched),
        "keywords_used": keywords,
        "papers": [p.to_dict() for p in matched],
    }


def format_for_ndex_network(scan_result: dict) -> dict:
    """Convert scan results into an NDEx network spec for posting.

    Creates a network where each node is a paper with metadata attributes.
    This can be posted to NDEx as a daily scan summary.
    """
    papers = scan_result["papers"]
    scan_date = scan_result["scan_date"]

    nodes = []
    for i, paper in enumerate(papers):
        nodes.append({
            "id": i,
            "v": {
                "name": paper["title"][:100],
                "doi": paper["doi"],
                "authors": paper["authors"][:200],
                "date": paper["date"],
                "category": paper["category"],
                "abstract_snippet": paper["abstract"][:300],
                "type": "preprint",
            }
        })

    network_spec = {
        "name": f"ndexagent biorxiv-daily-scan {scan_date}",
        "description": (
            f"Daily bioRxiv scan for HPMI-relevant papers. "
            f"Scanned {scan_result['total_scanned']} papers from the last "
            f"{scan_result['interval_days']} days, found {scan_result['total_matched']} "
            f"potentially relevant papers."
        ),
        "version": "1.0",
        "properties": {
            "ndex-agent": "rdaneel",
            "ndex-workflow": "biorxiv-triage",
            "ndex-triage-tier": "1",
            "ndex-interest-group": "hpmi",
            "ndex-scan-date": scan_date,
            "ndex-message-type": "analysis",
        },
        "nodes": nodes,
        "edges": [],  # Tier 1 has no edges — just a list of papers
    }

    return network_spec


def main():
    """Run scan and output results as JSON."""
    import argparse

    parser = argparse.ArgumentParser(description="Tier 1 bioRxiv scan")
    parser.add_argument("--days", type=int, default=3, help="Days back to scan")
    parser.add_argument("--max", type=int, default=500, help="Max papers to fetch")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    result = scan_biorxiv(interval_days=args.days, max_papers=args.max)

    print(f"Scanned {result['total_scanned']} papers, found {result['total_matched']} matches")

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
        print(f"Results written to {args.output}")
    else:
        # Also generate the NDEx network spec
        network_spec = format_for_ndex_network(result)
        print(f"\nNDEx network spec: {network_spec['name']}")
        print(f"Nodes: {len(network_spec['nodes'])}")


if __name__ == "__main__":
    main()
