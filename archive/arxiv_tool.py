import arxiv

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

        return list(client.results(search))

# Example usage:
if __name__ == "__main__":
    tool = ArxivQueryTool()

    # Example: Search for articles with "machine learning" in title or abstract, sorted by submission date
    results = tool.search("machine learning", max_results=10)

    for result in results:
        print(f"Title: {result.title}")
        print(f"Authors: {', '.join([author.name for author in result.authors])}")
        print(f"Published: {result.published}")
        print(f"URL: {result.entry_id}\n")