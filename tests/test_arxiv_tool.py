import unittest
from arxiv_query_tool import ArxivQueryTool

class TestArxivQueryToolIntegration(unittest.TestCase):
    def setUp(self):
        self.tool = ArxivQueryTool()

    def test_search_returns_results(self):
        """Test that the search method returns at least one result for a common query."""
        search_string = "machine learning"
        results = self.tool.search(search_string, max_results=5)

        self.assertGreater(len(results), 0, "Search did not return any results.")
        for result in results:
            self.assertIn(search_string.split()[0].lower(), result.title.lower() + result.summary.lower(),
                          f"Search result did not contain the search term: {result.title}")

    def test_search_limited_results(self):
        """Test that the search method limits the number of results as specified."""
        search_string = "quantum"
        max_results = 3
        results = self.tool.search(search_string, max_results=max_results)

        self.assertLessEqual(len(results), max_results,
                             f"Search returned more results than the specified limit ({max_results}).")

if __name__ == "__main__":
    unittest.main()
