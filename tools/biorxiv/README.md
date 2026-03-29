# bioRxiv MCP Server

MCP server for discovering and retrieving bioRxiv preprints. Provides keyword search, category filtering, and full-text retrieval.

## Tools (4 total)

| Tool | Description |
|------|-------------|
| `search_recent_papers` | Search recent preprints by keywords in title/abstract |
| `get_recent_papers_by_category` | Filter recent papers by bioRxiv subject category |
| `get_paper_fulltext` | Retrieve full text of a paper by DOI |
| `get_paper_abstract` | Get abstract and metadata by DOI |

## Running

```bash
python -m tools.biorxiv.server
```

No credentials required — the bioRxiv API is public.

## Rate Limiting

The client enforces a 1-second delay between API calls to respect bioRxiv's usage policies.
