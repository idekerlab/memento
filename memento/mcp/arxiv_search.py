from fastmcp import FastMCP
import arxiv
from typing import Optional

class ArxivQueryTool:
    def __init__(self):
        self.default_sort_by = arxiv.SortCriterion.SubmittedDate

    def search(self, search_string, max_results=10, sort_by=None):
        """
        Search arXiv for articles matching the search string in title and abstract.

        Args:
            search_string (str): Keywords to search for.
            max_results (int): Maximum number of results to return.
            sort_by (arxiv.SortCriterion, optional): Criterion to sort results.

        Returns:
            list: List of arXiv result objects.
        """
        # Validate and set the sorting criteria
        sort_by = sort_by or self.default_sort_by

        # Prepare the search query
        query = f"ti:{search_string} OR abs:{search_string}"

        # Create the client
        client = arxiv.Client()

        # Perform the search
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )
        results = list(client.results(search))
        print(f'found {len(results)} articles')
        print(results)
        return results

# Create an MCP server
mcp = FastMCP("arXiv Search")

# Tools

# Arxiv Search tool
@mcp.tool()
async def search_arxiv(search_string: str, max_results: Optional[int] = 10) -> str:
    """
    Search arXiv for articles matching the search string in title and abstract.

    Args:
        search_string (str): Keywords to search for.
        max_results (int): Maximum number of results to return.

    Returns:
        list: List of arXiv result objects.
    """
    tool = ArxivQueryTool()
    try:
        result = tool.search(search_string, max_results=max_results)
    except Exception as e:
        result = e
    return result


if __name__ == "__main__":
    mcp.run()
