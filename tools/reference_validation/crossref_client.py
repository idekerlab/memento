#!/usr/bin/env python3
"""
CrossRef API client for reference validation workflow
Handles DOI resolution and metadata retrieval
"""

import requests
import json
import time
import sys
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class CrossRefMetadata:
    """Structure for CrossRef API response data"""
    doi: str
    title: str
    authors: list
    journal: str
    year: Optional[int]
    abstract: str
    publisher: str
    type: str
    url: str
    success: bool
    error_message: Optional[str] = None

class CrossRefClient:
    """Client for interacting with CrossRef API"""
    
    def __init__(self, rate_limit_delay: float = 1.0):
        self.base_url = "https://api.crossref.org/works"
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ReferenceValidationWorkflow/1.0 (mailto:research@example.com)',
            'Accept': 'application/json'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def resolve_doi(self, doi: str) -> CrossRefMetadata:
        """Resolve DOI to paper metadata via CrossRef API"""
        self._rate_limit()
        
        # Clean DOI string
        clean_doi = doi.strip()
        if clean_doi.startswith('http'):
            # Extract DOI from URL
            clean_doi = clean_doi.split('/')[-2] + '/' + clean_doi.split('/')[-1]
        
        try:
            url = f"{self.base_url}/{clean_doi}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                work = data.get('message', {})
                
                # Extract authors
                authors = []
                for author in work.get('author', []):
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                
                # Extract year from date-parts
                year = None
                pub_date = (work.get('published-print') or 
                           work.get('published-online') or 
                           work.get('created'))
                if pub_date and 'date-parts' in pub_date:
                    try:
                        year = pub_date['date-parts'][0][0]
                    except (IndexError, TypeError):
                        pass
                
                return CrossRefMetadata(
                    doi=work.get('DOI', clean_doi),
                    title=work.get('title', [''])[0] if work.get('title') else '',
                    authors=authors,
                    journal=work.get('container-title', [''])[0] if work.get('container-title') else '',
                    year=year,
                    abstract=work.get('abstract', ''),
                    publisher=work.get('publisher', ''),
                    type=work.get('type', ''),
                    url=work.get('URL', ''),
                    success=True
                )
            
            elif response.status_code == 404:
                return CrossRefMetadata(
                    doi=clean_doi,
                    title='', authors=[], journal='', year=None,
                    abstract='', publisher='', type='', url='',
                    success=False,
                    error_message="DOI not found in CrossRef database"
                )
            
            else:
                return CrossRefMetadata(
                    doi=clean_doi,
                    title='', authors=[], journal='', year=None,
                    abstract='', publisher='', type='', url='',
                    success=False,
                    error_message=f"CrossRef API error: {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            return CrossRefMetadata(
                doi=clean_doi,
                title='', authors=[], journal='', year=None,
                abstract='', publisher='', type='', url='',
                success=False,
                error_message="Request timeout"
            )
        
        except requests.exceptions.RequestException as e:
            return CrossRefMetadata(
                doi=clean_doi,
                title='', authors=[], journal='', year=None,
                abstract='', publisher='', type='', url='',
                success=False,
                error_message=f"Request error: {str(e)}"
            )
        
        except Exception as e:
            return CrossRefMetadata(
                doi=clean_doi,
                title='', authors=[], journal='', year=None,
                abstract='', publisher='', type='', url='',
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def batch_resolve_dois(self, dois: list) -> Dict[str, CrossRefMetadata]:
        """Resolve multiple DOIs with rate limiting"""
        results = {}
        
        for i, doi in enumerate(dois):
            print(f"Resolving DOI {i+1}/{len(dois)}: {doi}", file=sys.stderr)
            metadata = self.resolve_doi(doi)
            results[doi] = metadata
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"Completed {i+1}/{len(dois)} DOI resolutions", file=sys.stderr)
        
        return results
    
    def test_connectivity(self) -> bool:
        """Test connection to CrossRef API"""
        test_doi = "10.1038/nature12373"  # Well-known DOI for testing
        try:
            result = self.resolve_doi(test_doi)
            return result.success
        except:
            return False

def main():
    """CLI interface for CrossRef client"""
    if len(sys.argv) < 2:
        print("Usage: python crossref_client.py <doi> [options]")
        print("  doi: Single DOI to resolve")
        print("  --batch <file>: Process DOIs from file (one per line)")
        print("  --output <file>: Output file path for results")
        print("  --test: Test API connectivity")
        sys.exit(1)
    
    client = CrossRefClient()
    
    if "--test" in sys.argv:
        if client.test_connectivity():
            print("✅ CrossRef API connectivity successful")
        else:
            print("❌ CrossRef API connectivity failed")
        sys.exit(0)
    
    output_path = None
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_path = sys.argv[output_idx + 1]
    
    if "--batch" in sys.argv:
        batch_idx = sys.argv.index("--batch")
        if batch_idx + 1 < len(sys.argv):
            file_path = sys.argv[batch_idx + 1]
            try:
                with open(file_path, 'r') as f:
                    dois = [line.strip() for line in f if line.strip()]
                
                results = client.batch_resolve_dois(dois)
                
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
        # Single DOI resolution
        doi = sys.argv[1]
        result = client.resolve_doi(doi)
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(asdict(result), f, indent=2)
            print(f"Results exported to {output_path}")
        else:
            print(json.dumps(asdict(result), indent=2))

if __name__ == "__main__":
    main()