import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional

class ArxivAPI:
    BASE_URL = "http://export.arxiv.org/api/query?"
    NAMESPACE = {'arxiv': 'http://arxiv.org/schemas/atom'}

    @staticmethod
    def search(query: str, start: int = 0, max_results: int = 10, 
               sort_by: str = 'submittedDate', sort_order: str = 'descending',
               date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict]:
        """
        Search ArXiv papers with given parameters.
        """
        params = {
            'search_query': query,
            'start': start,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': sort_order
        }
        
        if date_from and date_to:
            params['date_from'] = date_from
            params['date_to'] = date_to

        url = ArxivAPI.BASE_URL + urllib.parse.urlencode(params)
        
        try:
            with urllib.request.urlopen(url) as response:
                tree = ET.fromstring(response.read())
                return [ArxivAPI._parse_entry(entry) for entry in tree.findall('atom:entry', ArxivAPI.NAMESPACE)]
        except Exception as e:
            raise Exception(f"Error fetching results: {str(e)}")

    @staticmethod
    def _parse_entry(entry) -> Dict:
        """Parse XML entry into dictionary."""
        return {
            'id': entry.find('atom:id', ArxivAPI.NAMESPACE).text.split('/abs/')[-1],
            'title': entry.find('atom:title', ArxivAPI.NAMESPACE).text.strip(),
            'summary': entry.find('atom:summary', ArxivAPI.NAMESPACE).text.strip(),
            'authors': [author.find('atom:name', ArxivAPI.NAMESPACE).text 
                       for author in entry.findall('atom:author', ArxivAPI.NAMESPACE)],
            'published': entry.find('atom:published', ArxivAPI.NAMESPACE).text,
            'updated': entry.find('atom:updated', ArxivAPI.NAMESPACE).text,
            'pdf_url': next(link.get('href') for link in entry.findall('atom:link', ArxivAPI.NAMESPACE) 
                          if link.get('title') == 'pdf')
        }

    @staticmethod
    def build_query(title: str = '', abstract: str = '', author: str = '', 
                   category: str = '') -> str:
        """Build a formatted query string."""
        parts = []
        if title:
            parts.append(f'ti:"{title}"')
        if abstract:
            parts.append(f'abs:"{abstract}"')
        if author:
            parts.append(f'au:"{author}"')
        if category:
            parts.append(f'cat:{category}')
        return ' AND '.join(parts) if parts else 'all:*'