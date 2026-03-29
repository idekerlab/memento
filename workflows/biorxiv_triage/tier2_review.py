"""Tier 2: Focused read and brief review of selected papers.

This module provides the infrastructure for Tier 2 paper analysis:
1. Retrieve full text of a paper
2. Structure a review template for LLM completion
3. Build an NDEx network spec encoding key molecular interactions

The actual review generation is delegated to an LLM agent that uses this
module's prompts and output formatting.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.biorxiv.client import BiorxivClient, BiorxivPaper


# Prompt template for LLM-based review generation
TIER2_REVIEW_PROMPT = """You are a molecular biology researcher specializing in host-pathogen interactions.

Read the following bioRxiv paper and produce a structured brief review.

**Paper**: {title}
**DOI**: {doi}
**Authors**: {authors}

**Full Text**:
{fulltext}

---

Produce your review in the following JSON format:

{{
  "summary": "2-3 sentence summary of the paper's main findings",
  "key_molecular_findings": [
    {{
      "host_factor": "protein/gene name or null",
      "viral_factor": "protein/gene name or null",
      "interaction_type": "e.g. inhibits, activates, binds, phosphorylates",
      "mechanism": "brief description of the mechanism",
      "evidence_strength": "strong/moderate/weak"
    }}
  ],
  "experimental_approach": "Brief description of main experimental methods",
  "evidence_quality": "strong/moderate/weak — with brief justification",
  "hpmi_relevance": "How this relates to host-pathogen molecular interactions research",
  "recommendation": "skip | worth_discussing | must_read",
  "recommendation_reason": "1-2 sentences explaining the recommendation"
}}

Focus on:
- Specific molecular interactions between host and pathogen
- Named proteins, genes, pathways
- Novel mechanisms or unexpected findings
- Strength of experimental evidence
"""


def prepare_review_input(paper_doi: str) -> dict:
    """Fetch paper full text and prepare the review prompt.

    Args:
        paper_doi: DOI of the paper to review.

    Returns:
        Dict with 'prompt' (the filled template) and 'paper_metadata'.
    """
    client = BiorxivClient()

    # Get paper details
    paper = _lookup_paper(client, paper_doi)
    if paper is None:
        return {"status": "error", "message": f"Paper not found: {paper_doi}"}

    # Fetch full text
    fulltext = client.fetch_paper_text(paper)
    if fulltext.startswith("Error"):
        return {"status": "error", "message": fulltext}

    # Truncate to reasonable length for LLM context
    max_chars = 40000
    if len(fulltext) > max_chars:
        fulltext = fulltext[:max_chars] + "\n\n[... text truncated for length ...]"

    prompt = TIER2_REVIEW_PROMPT.format(
        title=paper.title,
        doi=paper.doi,
        authors=paper.authors,
        fulltext=fulltext,
    )

    return {
        "status": "success",
        "prompt": prompt,
        "paper_metadata": paper.to_dict(),
        "fulltext_length": len(fulltext),
    }


def review_to_ndex_network(paper_metadata: dict, review: dict) -> dict:
    """Convert a Tier 2 review into an NDEx network spec.

    The network encodes molecular interactions as nodes and edges,
    with the review text as the network description.

    Args:
        paper_metadata: Paper metadata dict from BiorxivPaper.to_dict().
        review: Parsed review JSON from the LLM.
    """
    nodes = []
    edges = []
    node_map = {}  # name -> node_id
    next_id = 0

    def get_or_create_node(name: str, node_type: str) -> int:
        nonlocal next_id
        if name in node_map:
            return node_map[name]
        node_id = next_id
        next_id += 1
        nodes.append({
            "id": node_id,
            "v": {"name": name, "type": node_type},
        })
        node_map[name] = node_id
        return node_id

    # Build interaction network from findings
    for finding in review.get("key_molecular_findings", []):
        host = finding.get("host_factor")
        viral = finding.get("viral_factor")
        if host and viral:
            host_id = get_or_create_node(host, "host_factor")
            viral_id = get_or_create_node(viral, "viral_factor")
            edges.append({
                "s": viral_id,
                "t": host_id,
                "v": {
                    "interaction": finding.get("interaction_type", "interacts_with"),
                    "mechanism": finding.get("mechanism", ""),
                    "evidence_strength": finding.get("evidence_strength", ""),
                },
            })
        elif host:
            get_or_create_node(host, "host_factor")
        elif viral:
            get_or_create_node(viral, "viral_factor")

    short_title = paper_metadata.get("title", "untitled")[:60].rstrip()
    recommendation = review.get("recommendation", "unknown")

    description = (
        f"**Recommendation: {recommendation}**\n\n"
        f"{review.get('summary', '')}\n\n"
        f"**Experimental approach**: {review.get('experimental_approach', 'N/A')}\n\n"
        f"**Evidence quality**: {review.get('evidence_quality', 'N/A')}\n\n"
        f"**HPMI relevance**: {review.get('hpmi_relevance', 'N/A')}\n\n"
        f"**Recommendation reason**: {review.get('recommendation_reason', 'N/A')}"
    )

    return {
        "name": f"ndexagent biorxiv-review {short_title}",
        "description": description,
        "version": "1.0",
        "properties": {
            "ndex-agent": "rdaneel",
            "ndex-workflow": "biorxiv-triage",
            "ndex-triage-tier": "2",
            "ndex-interest-group": "hpmi",
            "ndex-scan-date": date.today().isoformat(),
            "ndex-paper-doi": paper_metadata.get("doi", ""),
            "ndex-message-type": "analysis",
            "ndex-recommendation": recommendation,
        },
        "nodes": nodes,
        "edges": edges,
    }


def _lookup_paper(client: BiorxivClient, doi: str) -> Optional[BiorxivPaper]:
    """Look up a paper by DOI."""
    from tools.biorxiv.client import BIORXIV_CONTENT_URL

    url = f"https://api.biorxiv.org/details/biorxiv/{doi}"
    try:
        data = client._get(url)
        collection = data.get("collection", [])
        if collection:
            item = collection[-1]
            return BiorxivPaper(
                doi=item.get("doi", doi),
                title=item.get("title", ""),
                authors=item.get("authors", ""),
                abstract=item.get("abstract", ""),
                category=item.get("category", ""),
                date=item.get("date", ""),
                version=str(item.get("version", "1")),
                jatsxml=item.get("jatsxml", ""),
                published_doi=item.get("published", ""),
                biorxiv_url=f"{BIORXIV_CONTENT_URL}/{doi}",
            )
    except Exception:
        pass
    return None
