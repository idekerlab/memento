"""Tier 3: Deep analysis of high-significance papers.

This module provides the infrastructure for in-depth paper analysis:
1. Full text analysis with careful attention to methods and results
2. Literature context (search NDEx and bioRxiv for related work)
3. Detailed interaction network extraction
4. Comprehensive review artifact generation
5. Highlight notification for the interest group

The actual analysis is delegated to a capable LLM agent (e.g., Opus).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.biorxiv.client import BiorxivClient, BiorxivPaper


TIER3_ANALYSIS_PROMPT = """You are a senior molecular biology researcher and expert in host-pathogen interactions, particularly influenza virus mechanisms.

Perform an in-depth analysis of the following paper. This paper was flagged as highly significant during triage.

**Paper**: {title}
**DOI**: {doi}
**Authors**: {authors}

**Full Text**:
{fulltext}

**Tier 2 Review Summary**:
{tier2_summary}

**Related Work Found on NDEx/bioRxiv**:
{related_work}

---

Produce your analysis in the following JSON format:

{{
  "executive_summary": "3-5 sentence summary of what makes this paper significant",

  "mechanism_analysis": {{
    "main_finding": "The central molecular mechanism described",
    "pathway_context": "Where this fits in known signaling/regulatory pathways",
    "novelty": "What is genuinely new vs. confirmatory",
    "molecular_details": "Detailed description of the key molecular interactions"
  }},

  "interaction_network": [
    {{
      "source": "protein/gene name",
      "source_type": "host_factor | viral_factor | pathway | complex",
      "target": "protein/gene name",
      "target_type": "host_factor | viral_factor | pathway | complex",
      "interaction": "e.g. phosphorylates, inhibits, activates, binds, recruits",
      "context": "under what conditions, in what cell type",
      "evidence": "brief description of supporting experiment",
      "confidence": "high | medium | low"
    }}
  ],

  "methods_assessment": {{
    "key_techniques": ["list of main experimental approaches"],
    "strengths": "What was done well methodologically",
    "limitations": "Potential issues with methods or interpretation",
    "reproducibility_concerns": "Any red flags for reproducibility"
  }},

  "literature_context": {{
    "confirms": ["List of findings this confirms, with references"],
    "contradicts": ["List of findings this contradicts, with references"],
    "extends": ["List of findings this extends/builds upon, with references"],
    "open_questions": ["Questions raised by this work"]
  }},

  "testable_predictions": [
    "Specific testable predictions that follow from this work"
  ],

  "significance_assessment": {{
    "field_impact": "high | medium | low",
    "impact_justification": "Why this matters for HPMI research",
    "clinical_relevance": "Any therapeutic or diagnostic implications",
    "follow_up_priority": "What experiments should be done next"
  }}
}}

Be rigorous, specific, and cite evidence from the paper. Name specific proteins, genes, and cell types. Identify logical gaps.
"""


def prepare_analysis_input(
    paper_doi: str,
    tier2_summary: str = "",
    related_work: str = "",
) -> dict:
    """Fetch paper and prepare the Tier 3 analysis prompt.

    Args:
        paper_doi: DOI of the paper.
        tier2_summary: Summary from Tier 2 review (if available).
        related_work: Text describing related work found on NDEx/bioRxiv.
    """
    client = BiorxivClient()
    paper = _lookup_paper(client, paper_doi)
    if paper is None:
        return {"status": "error", "message": f"Paper not found: {paper_doi}"}

    fulltext = client.fetch_paper_text(paper)
    if fulltext.startswith("Error"):
        return {"status": "error", "message": fulltext}

    # For Tier 3, allow more text
    max_chars = 80000
    if len(fulltext) > max_chars:
        fulltext = fulltext[:max_chars] + "\n\n[... text truncated ...]"

    prompt = TIER3_ANALYSIS_PROMPT.format(
        title=paper.title,
        doi=paper.doi,
        authors=paper.authors,
        fulltext=fulltext,
        tier2_summary=tier2_summary or "Not available",
        related_work=related_work or "Not yet searched",
    )

    return {
        "status": "success",
        "prompt": prompt,
        "paper_metadata": paper.to_dict(),
        "fulltext_length": len(fulltext),
    }


def analysis_to_ndex_networks(paper_metadata: dict, analysis: dict) -> dict:
    """Convert a Tier 3 analysis into NDEx network specs.

    Returns two network specs:
    1. The detailed analysis network (with interaction graph)
    2. A highlight/notification post for the interest group
    """
    nodes = []
    edges = []
    node_map = {}
    next_id = 0

    def get_or_create_node(name: str, node_type: str) -> int:
        nonlocal next_id
        key = f"{name}:{node_type}"
        if key in node_map:
            return node_map[key]
        node_id = next_id
        next_id += 1
        nodes.append({
            "id": node_id,
            "v": {"name": name, "type": node_type},
        })
        node_map[key] = node_id
        return node_id

    # Build detailed interaction network
    for interaction in analysis.get("interaction_network", []):
        src_id = get_or_create_node(
            interaction["source"], interaction.get("source_type", "unknown")
        )
        tgt_id = get_or_create_node(
            interaction["target"], interaction.get("target_type", "unknown")
        )
        edges.append({
            "s": src_id,
            "t": tgt_id,
            "v": {
                "interaction": interaction.get("interaction", "interacts_with"),
                "context": interaction.get("context", ""),
                "evidence": interaction.get("evidence", ""),
                "confidence": interaction.get("confidence", ""),
            },
        })

    short_title = paper_metadata.get("title", "untitled")[:50].rstrip()
    doi = paper_metadata.get("doi", "")
    scan_date = date.today().isoformat()

    mechanism = analysis.get("mechanism_analysis", {})
    significance = analysis.get("significance_assessment", {})
    methods = analysis.get("methods_assessment", {})
    lit_context = analysis.get("literature_context", {})

    # Build rich description
    description_parts = [
        f"## Executive Summary\n{analysis.get('executive_summary', 'N/A')}",
        f"\n## Mechanism Analysis\n"
        f"**Main finding**: {mechanism.get('main_finding', 'N/A')}\n"
        f"**Novelty**: {mechanism.get('novelty', 'N/A')}\n"
        f"**Pathway context**: {mechanism.get('pathway_context', 'N/A')}\n"
        f"**Molecular details**: {mechanism.get('molecular_details', 'N/A')}",
        f"\n## Methods Assessment\n"
        f"**Strengths**: {methods.get('strengths', 'N/A')}\n"
        f"**Limitations**: {methods.get('limitations', 'N/A')}",
        f"\n## Significance\n"
        f"**Field impact**: {significance.get('field_impact', 'N/A')}\n"
        f"**Justification**: {significance.get('impact_justification', 'N/A')}\n"
        f"**Clinical relevance**: {significance.get('clinical_relevance', 'N/A')}",
    ]

    # Predictions
    predictions = analysis.get("testable_predictions", [])
    if predictions:
        description_parts.append(
            "\n## Testable Predictions\n" +
            "\n".join(f"- {p}" for p in predictions)
        )

    description = "\n".join(description_parts)

    # Analysis network
    analysis_network = {
        "name": f"ndexagent biorxiv-analysis {short_title}",
        "description": description,
        "version": "1.0",
        "properties": {
            "ndex-agent": "rdaneel",
            "ndex-workflow": "biorxiv-triage",
            "ndex-triage-tier": "3",
            "ndex-interest-group": "hpmi",
            "ndex-scan-date": scan_date,
            "ndex-paper-doi": doi,
            "ndex-message-type": "analysis",
            "ndex-data-type": "interaction",
        },
        "nodes": nodes,
        "edges": edges,
    }

    # Highlight/notification post
    highlight_network = {
        "name": f"ndexagent biorxiv-highlight {short_title}",
        "description": (
            f"Highlighted paper for HPMI interest group: {paper_metadata.get('title', '')}\n\n"
            f"DOI: {doi}\n\n"
            f"{analysis.get('executive_summary', '')}\n\n"
            f"**Impact**: {significance.get('field_impact', 'N/A')} — "
            f"{significance.get('impact_justification', '')}\n\n"
            f"Full analysis posted as a separate network."
        ),
        "version": "1.0",
        "properties": {
            "ndex-agent": "rdaneel",
            "ndex-workflow": "biorxiv-triage",
            "ndex-triage-tier": "3",
            "ndex-interest-group": "hpmi",
            "ndex-scan-date": scan_date,
            "ndex-paper-doi": doi,
            "ndex-message-type": "announcement",
        },
        "nodes": [],
        "edges": [],
    }

    return {
        "analysis_network": analysis_network,
        "highlight_network": highlight_network,
    }


def _lookup_paper(client, doi):
    """Look up paper by DOI."""
    from tools.biorxiv.client import BiorxivPaper, BIORXIV_CONTENT_URL

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
