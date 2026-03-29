#!/usr/bin/env python3
"""
Europe PMC Fetcher for Literature Dataset Extraction

This module provides comprehensive access to Europe PMC's API for automated
retrieval of biomedical literature, supplementary files, and metadata.

Features:
- RESTful API integration with Europe PMC
- Automated supplementary file discovery and download
- Bulk metadata retrieval and validation
- Integration with literature dataset extraction workflow

Author: Data Agent
Created: 2025-01-12
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import quote
import requests
from dataclasses import dataclass, asdict
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PaperMetadata:
    """Structure for Europe PMC paper metadata."""
    pmcid: Optional[str] = None
    pmid: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: List[str] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = None
    open_access: bool = False
    has_pdf: bool = False
    has_supplementary: bool = False
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []


@dataclass
class SupplementaryFile:
    """Structure for supplementary file information."""
    filename: str
    url: str
    file_type: str
    size_bytes: Optional[int] = None
    description: Optional[str] = None


@dataclass
class FetchResult:
    """Structure for fetch operation results."""
    success: bool
    paper_metadata: PaperMetadata
    pdf_path: Optional[Path] = None
    xml_path: Optional[Path] = None
    supplementary_files: List[Path] = None
    download_report: Dict = None
    limitations: List[str] = None
    
    def __post_init__(self):
        if self.supplementary_files is None:
            self.supplementary_files = []
        if self.download_report is None:
            self.download_report = {}
        if self.limitations is None:
            self.limitations = []


class EuropePMCFetcher:
    """
    Fetcher for Europe PMC content with comprehensive API integration.
    
    Provides methods for searching, retrieving, and downloading biomedical
    literature content from Europe PMC's database.
    """
    
    def __init__(self, base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"):
        """
        Initialize Europe PMC fetcher.
        
        Args:
            base_url: Base URL for Europe PMC REST API
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EuropePMC-Fetcher/1.0 (Literature Dataset Extraction)',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self.request_delay = 0.5  # seconds between requests
        self.last_request_time = 0
        
        logger.info("Europe PMC fetcher initialized")
    
    def _rate_limit(self):
        """Implement respectful rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make rate-limited request to Europe PMC API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.RequestException: On API request failure
        """
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Europe PMC API request failed: {e}")
            raise
    
    def search_paper(self, identifier: str) -> Optional[PaperMetadata]:
        """
        Search for paper in Europe PMC using DOI, PMCID, or PMID.
        
        Args:
            identifier: DOI, PMCID, or PMID
            
        Returns:
            PaperMetadata if found, None otherwise
        """
        logger.info(f"Searching Europe PMC for: {identifier}")
        
        # Determine search query based on identifier format
        query = self._format_search_query(identifier)
        
        try:
            params = {
                'query': query,
                'format': 'json',
                'pageSize': 1
            }
            
            response = self._make_request('search', params)
            
            if response.get('hitCount', 0) == 0:
                logger.warning(f"Paper not found in Europe PMC: {identifier}")
                return None
            
            # Extract paper information from first result
            paper_data = response['resultList']['result'][0]
            return self._parse_paper_metadata(paper_data)
        
        except Exception as e:
            logger.error(f"Error searching for paper {identifier}: {e}")
            return None
    
    def _format_search_query(self, identifier: str) -> str:
        """Format search query based on identifier type."""
        identifier = identifier.strip()
        
        # DOI pattern
        if identifier.startswith('10.') or identifier.startswith('doi:'):
            doi = identifier.replace('doi:', '').strip()
            return f'DOI:"{doi}"'
        
        # PMCID pattern
        elif identifier.startswith('PMC') or identifier.isdigit():
            pmcid = identifier if identifier.startswith('PMC') else f'PMC{identifier}'
            return f'PMCID:{pmcid}'
        
        # PMID pattern
        elif identifier.startswith('PMID:') or (identifier.isdigit() and len(identifier) >= 7):
            pmid = identifier.replace('PMID:', '').strip()
            return f'EXT_ID:{pmid}'
        
        # Default to text search
        else:
            return quote(identifier)
    
    def _parse_paper_metadata(self, paper_data: Dict) -> PaperMetadata:
        """Parse Europe PMC paper data into structured metadata."""
        
        # Extract basic identifiers
        pmcid = paper_data.get('pmcid')
        pmid = paper_data.get('pmid')
        doi = paper_data.get('doi')
        
        # Extract bibliographic information
        title = paper_data.get('title', '').strip()
        journal = paper_data.get('journalTitle', '').strip()
        
        # Extract authors
        authors = []
        if 'authorList' in paper_data and 'author' in paper_data['authorList']:
            for author in paper_data['authorList']['author']:
                if 'fullName' in author:
                    authors.append(author['fullName'])
                elif 'lastName' in author:
                    first = author.get('firstName', '')
                    last = author['lastName']
                    authors.append(f"{first} {last}".strip())
        
        # Extract publication date
        pub_date = paper_data.get('firstPublicationDate', '')
        
        # Extract abstract
        abstract = paper_data.get('abstractText', '').strip()
        
        # Extract keywords
        keywords = []
        if 'keywordList' in paper_data:
            for keyword_group in paper_data['keywordList']:
                if 'keyword' in keyword_group:
                    keywords.extend(keyword_group['keyword'])
        
        # Determine content availability
        open_access = paper_data.get('isOpenAccess', 'N') == 'Y'
        has_pdf = paper_data.get('hasPDF', 'N') == 'Y'
        has_supplementary = paper_data.get('hasSuppl', 'N') == 'Y'
        
        return PaperMetadata(
            pmcid=pmcid,
            pmid=pmid,
            doi=doi,
            title=title,
            authors=authors,
            journal=journal,
            publication_date=pub_date,
            abstract=abstract,
            keywords=keywords,
            open_access=open_access,
            has_pdf=has_pdf,
            has_supplementary=has_supplementary
        )
    
    def get_supplementary_files(self, pmcid: str) -> List[SupplementaryFile]:
        """
        Get list of supplementary files for a paper.
        
        Args:
            pmcid: PMC identifier
            
        Returns:
            List of SupplementaryFile objects
        """
        logger.info(f"Retrieving supplementary files for {pmcid}")
        
        try:
            params = {
                'pmcid': pmcid,
                'format': 'json'
            }
            
            response = self._make_request(f'{pmcid}/supplementaryFiles', params)
            
            supplementary_files = []
            
            if 'supplementaryFiles' in response:
                for file_data in response['supplementaryFiles']:
                    supp_file = SupplementaryFile(
                        filename=file_data.get('fileName', ''),
                        url=file_data.get('url', ''),
                        file_type=file_data.get('fileType', ''),
                        size_bytes=file_data.get('fileSize'),
                        description=file_data.get('description', '')
                    )
                    supplementary_files.append(supp_file)
            
            logger.info(f"Found {len(supplementary_files)} supplementary files")
            return supplementary_files
        
        except Exception as e:
            logger.error(f"Error retrieving supplementary files: {e}")
            return []
    
    def download_pdf(self, pmcid: str, output_dir: Path) -> Optional[Path]:
        """
        Download PDF for a paper.
        
        Args:
            pmcid: PMC identifier
            output_dir: Directory to save PDF
            
        Returns:
            Path to downloaded PDF or None if failed
        """
        logger.info(f"Downloading PDF for {pmcid}")
        
        try:
            pdf_url = f"{self.base_url}/{pmcid}/fullTextXML"
            
            self._rate_limit()
            response = self.session.get(pdf_url, timeout=60)
            
            if response.status_code == 200:
                pdf_path = output_dir / f"{pmcid}.pdf"
                
                with open(pdf_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"PDF downloaded: {pdf_path}")
                return pdf_path
            else:
                logger.warning(f"PDF not available for {pmcid}: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return None
    
    def download_xml(self, pmcid: str, output_dir: Path) -> Optional[Path]:
        """
        Download full-text XML for a paper.
        
        Args:
            pmcid: PMC identifier
            output_dir: Directory to save XML
            
        Returns:
            Path to downloaded XML or None if failed
        """
        logger.info(f"Downloading XML for {pmcid}")
        
        try:
            xml_url = f"{self.base_url}/{pmcid}/fullTextXML"
            
            self._rate_limit()
            response = self.session.get(xml_url, timeout=60)
            
            if response.status_code == 200:
                xml_path = output_dir / f"{pmcid}.xml"
                
                with open(xml_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"XML downloaded: {xml_path}")
                return xml_path
            else:
                logger.warning(f"XML not available for {pmcid}: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Error downloading XML: {e}")
            return None
    
    def download_supplementary_file(self, supp_file: SupplementaryFile, 
                                  output_dir: Path) -> Optional[Path]:
        """
        Download a supplementary file.
        
        Args:
            supp_file: SupplementaryFile object with download information
            output_dir: Directory to save file
            
        Returns:
            Path to downloaded file or None if failed
        """
        logger.info(f"Downloading supplementary file: {supp_file.filename}")
        
        try:
            self._rate_limit()
            response = self.session.get(supp_file.url, timeout=120)
            
            if response.status_code == 200:
                file_path = output_dir / supp_file.filename
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Supplementary file downloaded: {file_path}")
                return file_path
            else:
                logger.warning(f"Failed to download {supp_file.filename}: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Error downloading supplementary file {supp_file.filename}: {e}")
            return None
    
    def fetch_paper_complete(self, identifier: str, output_dir: Union[str, Path],
                           include_supplementary: bool = True) -> FetchResult:
        """
        Complete paper fetch including PDF, XML, and supplementary files.
        
        Args:
            identifier: DOI, PMCID, or PMID
            output_dir: Directory to save all files
            include_supplementary: Whether to download supplementary files
            
        Returns:
            FetchResult with complete download information
        """
        logger.info(f"Starting complete fetch for: {identifier}")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize result structure
        result = FetchResult(
            success=False,
            paper_metadata=PaperMetadata(),
            download_report={
                'identifier': identifier,
                'start_time': time.time(),
                'files_downloaded': [],
                'files_failed': [],
                'total_size_bytes': 0
            }
        )
        
        try:
            # Step 1: Search for paper
            metadata = self.search_paper(identifier)
            if not metadata:
                result.limitations.append("Paper not found in Europe PMC database")
                return result
            
            result.paper_metadata = metadata
            
            # Step 2: Download PDF if available
            if metadata.has_pdf and metadata.pmcid:
                pdf_path = self.download_pdf(metadata.pmcid, output_dir)
                if pdf_path:
                    result.pdf_path = pdf_path
                    result.download_report['files_downloaded'].append(str(pdf_path))
                else:
                    result.download_report['files_failed'].append('PDF')
                    result.limitations.append("PDF download failed")
            else:
                result.limitations.append("PDF not available")
            
            # Step 3: Download XML if available
            if metadata.pmcid:
                xml_path = self.download_xml(metadata.pmcid, output_dir)
                if xml_path:
                    result.xml_path = xml_path
                    result.download_report['files_downloaded'].append(str(xml_path))
                else:
                    result.download_report['files_failed'].append('XML')
            
            # Step 4: Download supplementary files if requested
            if include_supplementary and metadata.has_supplementary and metadata.pmcid:
                supp_files = self.get_supplementary_files(metadata.pmcid)
                
                supp_dir = output_dir / 'supplementary_files'
                supp_dir.mkdir(exist_ok=True)
                
                for supp_file in supp_files:
                    downloaded_path = self.download_supplementary_file(supp_file, supp_dir)
                    if downloaded_path:
                        result.supplementary_files.append(downloaded_path)
                        result.download_report['files_downloaded'].append(str(downloaded_path))
                    else:
                        result.download_report['files_failed'].append(supp_file.filename)
            
            # Step 5: Generate metadata file
            metadata_path = output_dir / 'paper_metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2)
            
            result.download_report['files_downloaded'].append(str(metadata_path))
            
            # Calculate total size and completion status
            total_size = 0
            for file_path in result.download_report['files_downloaded']:
                if Path(file_path).exists():
                    total_size += Path(file_path).stat().st_size
            
            result.download_report['total_size_bytes'] = total_size
            result.download_report['end_time'] = time.time()
            result.download_report['duration_seconds'] = (
                result.download_report['end_time'] - result.download_report['start_time']
            )
            
            # Determine overall success
            files_downloaded = len(result.download_report['files_downloaded'])
            files_failed = len(result.download_report['files_failed'])
            
            if files_downloaded > 0:
                result.success = True
                logger.info(f"Fetch completed: {files_downloaded} files downloaded, {files_failed} failed")
            else:
                result.limitations.append("No files successfully downloaded")
                logger.warning("Fetch failed: no files downloaded")
        
        except Exception as e:
            logger.error(f"Error during complete fetch: {e}")
            result.limitations.append(f"Fetch error: {str(e)}")
        
        return result


def quick_paper_lookup(identifier: str) -> Optional[Dict]:
    """
    Quick utility function for paper lookup without downloading.
    
    Args:
        identifier: DOI, PMCID, or PMID
        
    Returns:
        Dictionary with paper information or None
    """
    try:
        fetcher = EuropePMCFetcher()
        metadata = fetcher.search_paper(identifier)
        
        if metadata:
            return {
                'found': True,
                'pmcid': metadata.pmcid,
                'title': metadata.title,
                'authors': metadata.authors,
                'journal': metadata.journal,
                'open_access': metadata.open_access,
                'has_pdf': metadata.has_pdf,
                'has_supplementary': metadata.has_supplementary
            }
        else:
            return {'found': False}
    
    except Exception as e:
        logger.error(f"Quick lookup failed: {e}")
        return {'found': False, 'error': str(e)}


if __name__ == "__main__":
    # Example usage and testing
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python europepmc_fetcher.py <DOI|PMCID|PMID> [output_dir]")
        sys.exit(1)
    
    identifier = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "downloads"
    
    print(f"Europe PMC Fetcher - Retrieving: {identifier}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)
    
    fetcher = EuropePMCFetcher()
    result = fetcher.fetch_paper_complete(identifier, output_dir)
    
    print(f"Success: {result.success}")
    print(f"Title: {result.paper_metadata.title}")
    print(f"Files downloaded: {len(result.download_report['files_downloaded'])}")
    print(f"Files failed: {len(result.download_report['files_failed'])}")
    
    if result.limitations:
        print("Limitations:")
        for limitation in result.limitations:
            print(f"  - {limitation}")
    
    print(f"\nTotal size: {result.download_report['total_size_bytes']:,} bytes")
    print(f"Duration: {result.download_report['duration_seconds']:.1f} seconds")