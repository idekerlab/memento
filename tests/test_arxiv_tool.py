import unittest
from datetime import datetime, timedelta
from arxiv_api import ArxivAPI

class TestArxivAPI(unittest.TestCase):
    def setUp(self):
        self.api = ArxivAPI()
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    def test_author_search(self):
        query = self.api.build_query(author="dexter pratt")
        results = self.api.search(query, max_results=5)
        
        self.assertTrue(len(results) > 0)
        for paper in results:
            self.assertTrue(any('Pratt, Dexter' in author for author in paper['authors']))

    def test_title_search(self):
        query = self.api.build_query(title="network biology")
        results = self.api.search(query, max_results=3)
        
        self.assertTrue(len(results) > 0)
        for paper in results:
            self.assertTrue('network'.lower() in paper['title'].lower() or 
                          'biology'.lower() in paper['title'].lower())

    def test_date_range_search(self):
        query = self.api.build_query(title="machine learning")
        results = self.api.search(query, max_results=5, 
                                date_from=self.yesterday, 
                                date_to=self.today)
        
        self.assertTrue(len(results) >= 0)  # May be 0 if no papers published
        for paper in results:
            paper_date = datetime.strptime(paper['published'][:10], '%Y-%m-%d')
            self.assertTrue(paper_date >= datetime.strptime(self.yesterday, '%Y-%m-%d'))
            self.assertTrue(paper_date <= datetime.now())

    def test_pdf_url(self):
        query = self.api.build_query(title="deep learning")
        results = self.api.search(query, max_results=1)
        
        self.assertTrue(len(results) > 0)
        self.assertTrue(results[0]['pdf_url'].startswith('http'))
        self.assertTrue(results[0]['pdf_url'].endswith('pdf'))

if __name__ == '__main__':
    unittest.main()