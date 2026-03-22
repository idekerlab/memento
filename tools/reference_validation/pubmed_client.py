#!/usr/bin/env python3
"""
PubMed E-utilities client for reference validation workflow
Handles title-based paper search and metadata retrieval
"""

import requests
import json
import time
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import quote

@dataclass
class PubMedMetadata:
    """Structure for PubMed search result data"""
    pmid: str
    title: str
    authors: List[str]
    journal: str
    year: Optional[int]
    abstract: str
    doi: str
    search_query: str
    results_found: int
    success: bool
    error_message: Optional[str] = None

class PubMedClient:
    """Client for interacting with PubMed E-utilities API"""
    
    def __init__(self, rate_limit_delay: float = 1.0):
        self.search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ReferenceValidationWorkflow/1.0 (mailto:research@example.com)'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def search_by_title(self, title: str, authors: List[str] = None, max_results: int = 5) -> PubMedMetadata:
        """Search PubMed by title and optionally authors"""
        self._rate_limit()
        
        # Build search query
        search_terms = []
        if title:
            # Use title in quotes for exact phrase search, then fall back to terms
            clean_title = title.strip().replace('"', '')
            search_terms.append(f'"{clean_title}"[Title]')
        
        if authors and len(authors) > 0:
            # Use first author surname
            first_author = authors[0].split()
            if len(first_author) > 0:
                surname = first_author[-1]  # Last word is typically surname
                search_terms.append(f"{surname}[Author]")
        
        query = ' AND '.join(search_terms) if search_terms else title
        
        try:
            # Step 1: Search for PMIDs
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmode': 'json',
                'retmax': max_results
            }
            
            response = self.session.get(self.search_url, params=search_params, timeout=10)
            if response.status_code != 200:
                return PubMedMetadata(
                    pmid='', title='', authors=[], journal='', year=None,
                    abstract='', doi='', search_query=query, results_found=0,
                    success=False, error_message=f"Search API error: {response.status_code}"
                )
            
            search_data = response.json()
            id_list = search_data.get('esearchresult', {}).get('idlist', [])
            total_results = int(search_data.get('esearchresult', {}).get('count', 0))
            
            if not id_list:
                return PubMedMetadata(
                    pmid='', title='', authors=[], journal='', year=None,
                    abstract='', doi='', search_query=query, results_found=total_results,
                    success=False, error_message="No matching papers found"
                )
            
            # Step 2: Fetch details for best match (first result)
            self._rate_limit()
            
            details_params = {
                'db': 'pubmed',
                'id': id_list[0],
                'retmode': 'xml'
            }
            
            details_response = self.session.get(self.fetch_url, params=details_params, timeout=10)
            if details_response.status_code != 200:
                return PubMedMetadata(
                    pmid=id_list[0], title='', authors=[], journal='', year=None,
                    abstract='', doi='', search_query=query, results_found=total_results,
                    success=False, error_message=f"Fetch API error: {details_response.status_code}"
                )
            
            # Step 3: Parse XML response
            try:
                root = ET.fromstring(details_response.content)
                article = root.find('.//Article')
                if article is None:
                    return PubMedMetadata(
                        pmid=id_list[0], title='', authors=[], journal='', year=None,
                        abstract='', doi='', search_query=query, results_found=total_results,
                        success=False, error_message="Could not parse article XML"
                    )
                
                # Extract title
                title_elem = article.find('.//ArticleTitle')
                paper_title = title_elem.text if title_elem is not None else ''
                
                # Extract abstract
                abstract_elem = article.find('.//Abstract/AbstractText')
                abstract = ''
                if abstract_elem is not None:
                    # Handle both simple text and structured abstracts
                    if abstract_elem.text:
                        abstract = abstract_elem.text
                    else:
                        # Structured abstract - combine all sections
                        abstract_parts = []
                        for section in article.findall('.//Abstract/AbstractText'):
                            if section.text:
                                label = section.get('Label', '')
                                text = section.text
                                if label:
                                    abstract_parts.append(f"{label}: {text}")
                                else:
                                    abstract_parts.append(text)
                        abstract = ' '.join(abstract_parts)
                
                # Extract journal
                journal_elem = article.find('.//Journal/Title')
                journal = journal_elem.text if journal_elem is not None else ''
                
                # Extract year
                year = None
                year_elem = article.find('.//PubDate/Year')
                if year_elem is not None and year_elem.text:
                    try:
                        year = int(year_elem.text)
                    except ValueError:
                        pass
                
                # Extract authors
                authors_extracted = []
                for author in article.findall('.//Author'):
                    lastname = author.find('LastName')
                    forename = author.find('ForeName')
                    if lastname is not None:
                        author_name = lastname.text
                        if forename is not None and forename.text:
                            author_name = f"{forename.text} {author_name}"
                        authors_extracted.append(author_name)
                
                # Extract DOI if available
                doi = ''
                for article_id in root.findall('.//ArticleId'):
                    if article_id.get('IdType') == 'doi':
                        doi = article_id.text or ''
                        break
                
                return PubMedMetadata(
                    pmid=id_list[0],
                    title=paper_title,
                    authors=authors_extracted,
                    journal=journal,
                    year=year,
                    abstract=abstract,
                    doi=doi,
                    search_query=query,
                    results_found=total_results,
                    success=True
                )
                
            except ET.ParseError as e:
                return PubMedMetadata(
                    pmid=id_list[0], title='', authors=[], journal='', year=None,
                    abstract='', doi='', search_query=query, results_found=total_results,
                    success=False, error_message=f"XML parsing error: {str(e)}"
                )
        
        except requests.exceptions.Timeout:
            return PubMedMetadata(
                pmid='', title='', authors=[], journal='', year=None,
                abstract='', doi='', search_query=query, results_found=0,
                success=False, error_message="Request timeout"
            )
        
        except requests.exceptions.RequestException as e:
            return PubMedMetadata(
                pmid='', title='', authors=[], journal='', year=None,
                abstract='', doi='', search_query=query, results_found=0,
                success=False, error_message=f"Request error: {str(e)}"
            )
        
        except Exception as e:
            return PubMedMetadata(
                pmid='', title='', authors=[], journal='', year=None,
                abstract='', doi='', search_query=query, results_found=0,
                success=False, error_message=f"Unexpected error: {str(e)}"
            )
    
    def batch_search_titles(self, titles: List[str], authors_list: List[List[str]] = None) -> Dict[str, PubMedMetadata]:
        """Search multiple titles with rate limiting"""
        results = {}
        
        if authors_list is None:
            authors_list = [[] for _ in titles]
        
        for i, (title, authors) in enumerate(zip(titles, authors_list)):
            print(f"Searching title {i+1}/{len(titles)}: {title[:50]}...", file=sys.stderr)
            metadata = self.search_by_title(title, authors)
            results[title] = metadata
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Completed {i+1}/{len(titles)} title searches", file=sys.stderr)
        
        return results
    
    def test_connectivity(self) -> bool:
        """Test connection to PubMed API"""
        test_title = "CRISPR gene editing"
        try:
            result = self.search_by_title(test_title)
            return result.success
        except:
            return False

def main():
    """CLI interface for PubMed client"""
    if len(sys.argv) < 2:
        print("Usage: python pubmed_client.py <title> [options]")
        print("  title: Paper title to search for")
        print("  --authors <author1,author2>: Authors to include in search")
        print("  --batch <file>: Process titles from file (one per line)")
        print("  --output <file>: Output file path for results")
        print("  --test: Test API connectivity")
        sys.exit(1)
    
    client = PubMedClient()
    
    if "--test" in sys.argv:
        if client.test_connectivity():
            print("✅ PubMed API connectivity successful")
        else:
            print("❌ PubMed API connectivity failed")
        sys.exit(0)
    
    output_path = None
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_path = sys.argv[output_idx + 1]
    
    authors = []
    if "--authors" in sys.argv:
        authors_idx = sys.argv.index("--authors")
        if authors_idx + 1 < len(sys.argv):
            authors = [a.strip() for a in sys.argv[authors_idx + 1].split(',')]
    
    if "--batch" in sys.argv:
        batch_idx = sys.argv.index("--batch")
        if batch_idx + 1 < len(sys.argv):
            file_path = sys.argv[batch_idx + 1]
            try:
                with open(file_path, 'r') as f:
                    titles = [line.strip() for line in f if line.strip()]
                
                results = client.batch_search_titles(titles)
                
                if output_path:
                    with open(output_path, 'w') as f:
                        json.dump({k: asdict(v) for k, v in results.items()}, f, indent=2)
                    print(f"Results exported to {output_path}")
                else:
                    print(json.dumps({k: asdict(v) for k, v in results.items()}, indent=2))
                    
            except FileNotFoundError:
                print(f"Error: File {file_path} not found")
                sys.exit(1)
    
    else:
        # Single title search
        title = sys.argv[1]
        result = client.search_by_title(title, authors)
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(asdict(result), f, indent=2)
            print(f"Results exported to {output_path}")
        else:
            print(json.dumps(asdict(result), indent=2))

if __name__ == "__main__":
    main()