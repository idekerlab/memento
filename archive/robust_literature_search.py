#!/usr/bin/env python3
"""
Robust Literature Search Client with Comprehensive Error Handling

Provides reliable API access to Semantic Scholar, PubMed, and arXiv with:
- Exponential backoff and retry mechanisms
- Circuit breaker patterns for API failures
- Graceful fallback between API sources
- Session-based recovery and tracking
"""

import requests
import time
import json
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import random
from pathlib import Path

logger = logging.getLogger(__name__)

class APIStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILED = "failed"
    CIRCUIT_OPEN = "circuit_open"

@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 300.0  # 5 minutes
    half_open_max_calls: int = 3

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = APIStatus.HEALTHY
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        if self.state == APIStatus.HEALTHY:
            return True
        elif self.state == APIStatus.CIRCUIT_OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = APIStatus.DEGRADED
                self.half_open_calls = 0
                return True
            return False
        elif self.state == APIStatus.DEGRADED:
            return self.half_open_calls < self.config.half_open_max_calls
        return False

    def record_success(self):
        if self.state == APIStatus.DEGRADED:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = APIStatus.HEALTHY
                self.failure_count = 0
        else:
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == APIStatus.DEGRADED:
            self.state = APIStatus.CIRCUIT_OPEN
        elif self.failure_count >= self.config.failure_threshold:
            self.state = APIStatus.CIRCUIT_OPEN

class RobustLiteratureSearch:
    """Robust literature search with comprehensive error handling"""
    
    def __init__(self, session_dir: Optional[str] = None):
        self.session_dir = Path(session_dir) if session_dir else Path.cwd() / "search_session"
        self.session_dir.mkdir(exist_ok=True)
        
        # Initialize circuit breakers for each API
        circuit_config = CircuitBreakerConfig()
        self.circuit_breakers = {
            "semantic_scholar": CircuitBreaker(circuit_config),
            "pubmed": CircuitBreaker(circuit_config),
            "arxiv": CircuitBreaker(circuit_config)
        }
        
        # Rate limiting state
        self.last_api_calls = {}
        self.api_delays = {
            "semantic_scholar": 1.0,
            "pubmed": 0.5,
            "arxiv": 0.5
        }
        
        # Retry configuration
        self.retry_config = RetryConfig()
        
        # Session tracking
        self.session_log = []
        
        # Request session with connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CritiqueAgent/1.0 (Research; mailto:research@example.com)'
        })

    def _calculate_backoff_delay(self, attempt: int, base_delay: float = 1.0) -> float:
        """Calculate exponential backoff delay with jitter"""
        delay = min(
            base_delay * (self.retry_config.exponential_base ** attempt),
            self.retry_config.max_delay
        )
        
        if self.retry_config.jitter:
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
            
        return delay

    def _apply_rate_limit(self, api_name: str):
        """Apply rate limiting with exponential backoff awareness"""
        current_time = time.time()
        
        if api_name in self.last_api_calls:
            elapsed = current_time - self.last_api_calls[api_name]
            required_delay = self.api_delays.get(api_name, 1.0)
            
            if elapsed < required_delay:
                sleep_time = required_delay - elapsed
                logger.debug(f"Rate limiting {api_name}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_api_calls[api_name] = time.time()

    def _log_api_attempt(self, api_name: str, query: str, attempt: int, success: bool, error: str = None):
        """Log API attempt for session tracking"""
        log_entry = {
            "timestamp": time.time(),
            "api": api_name,
            "query": query,
            "attempt": attempt,
            "success": success,
            "error": error,
            "circuit_state": self.circuit_breakers[api_name].state.value
        }
        self.session_log.append(log_entry)

    def _robust_api_call(self, api_name: str, url: str, params: Dict, query: str) -> Optional[Dict]:
        """Execute API call with comprehensive error handling"""
        circuit_breaker = self.circuit_breakers[api_name]
        
        if not circuit_breaker.can_execute():
            logger.warning(f"{api_name} circuit breaker is open, skipping")
            self._log_api_attempt(api_name, query, 0, False, "circuit_breaker_open")
            return None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Apply rate limiting
                self._apply_rate_limit(api_name)
                
                # Make request with timeout
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=(10, 30)  # (connect, read) timeouts
                )
                
                if response.status_code == 200:
                    circuit_breaker.record_success()
                    self._log_api_attempt(api_name, query, attempt, True)
                    return response.json()
                    
                elif response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('retry-after', 60))
                    backoff_delay = self._calculate_backoff_delay(attempt, retry_after)
                    logger.warning(f"{api_name} rate limited (429), waiting {backoff_delay:.1f}s")
                    time.sleep(backoff_delay)
                    continue
                    
                elif response.status_code in [503, 502, 500]:  # Server errors
                    backoff_delay = self._calculate_backoff_delay(attempt)
                    logger.warning(f"{api_name} server error ({response.status_code}), retrying in {backoff_delay:.1f}s")
                    time.sleep(backoff_delay)
                    continue
                    
                else:  # Other errors
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.error(f"{api_name} API error: {error_msg}")
                    circuit_breaker.record_failure()
                    self._log_api_attempt(api_name, query, attempt, False, error_msg)
                    return None
                    
            except requests.exceptions.Timeout:
                backoff_delay = self._calculate_backoff_delay(attempt)
                logger.warning(f"{api_name} timeout, retrying in {backoff_delay:.1f}s")
                time.sleep(backoff_delay)
                continue
                
            except requests.exceptions.ConnectionError as e:
                backoff_delay = self._calculate_backoff_delay(attempt)
                logger.warning(f"{api_name} connection error: {e}, retrying in {backoff_delay:.1f}s")
                time.sleep(backoff_delay)
                continue
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"{api_name} unexpected error: {error_msg}")
                circuit_breaker.record_failure()
                self._log_api_attempt(api_name, query, attempt, False, error_msg)
                return None
        
        # All retries failed
        circuit_breaker.record_failure()
        self._log_api_attempt(api_name, query, self.retry_config.max_retries, False, "max_retries_exceeded")
        logger.error(f"{api_name} failed after {self.retry_config.max_retries} retries")
        return None

    def search_semantic_scholar(self, query: str, limit: int = 10, fields: List[str] = None) -> Optional[List[Dict]]:
        """Search Semantic Scholar with robust error handling"""
        if fields is None:
            fields = ["title", "authors", "venue", "year", "abstract", "citationCount", "openAccessPdf", "externalIds"]
        
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": ",".join(fields),
            "fieldsOfStudy": "Biology,Medicine",
            "publicationTypes": "JournalArticle"
        }
        
        logger.info(f"🔍 Searching Semantic Scholar: {query} (limit: {limit})")
        
        response_data = self._robust_api_call("semantic_scholar", url, params, query)
        if response_data:
            papers = response_data.get('data', [])
            total = response_data.get('total', len(papers))
            logger.info(f"✅ Semantic Scholar returned {len(papers)} papers (total: {total})")
            return papers
        
        logger.warning("❌ Semantic Scholar search failed")
        return None

    def search_pubmed(self, query: str, limit: int = 10) -> Optional[List[Dict]]:
        """Search PubMed with robust error handling"""
        # First, get PMIDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
            "sort": "relevance"
        }
        
        logger.info(f"🔍 Searching PubMed: {query} (limit: {limit})")
        
        search_response = self._robust_api_call("pubmed", search_url, search_params, query)
        if not search_response:
            logger.warning("❌ PubMed search failed")
            return None
        
        pmids = search_response.get('esearchresult', {}).get('idlist', [])
        if not pmids:
            logger.warning("❌ PubMed returned no results")
            return []
        
        # Get paper details
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json"
        }
        
        fetch_response = self._robust_api_call("pubmed", fetch_url, fetch_params, query)
        if not fetch_response:
            logger.warning("❌ PubMed fetch failed")
            return None
        
        # Process results
        papers = []
        result_data = fetch_response.get('result', {})
        for pmid in pmids:
            if pmid in result_data:
                paper_data = result_data[pmid]
                paper = {
                    "source": "pubmed",
                    "pmid": pmid,
                    "title": paper_data.get('title', ''),
                    "authors": [author.get('name', '') for author in paper_data.get('authors', [])],
                    "journal": paper_data.get('source', ''),
                    "year": paper_data.get('pubdate', '').split()[0] if paper_data.get('pubdate') else None,
                    "abstract": "",  # Abstract requires separate API call
                    "doi": paper_data.get('doi', '')
                }
                papers.append(paper)
        
        logger.info(f"✅ PubMed returned {len(papers)} papers")
        return papers

    def search_multiple_sources(self, query: str, limit_per_source: int = 10) -> Dict[str, List[Dict]]:
        """Search multiple sources with graceful degradation"""
        results = {}
        
        # Try Semantic Scholar first (most comprehensive)
        ss_results = self.search_semantic_scholar(query, limit_per_source)
        if ss_results is not None:
            results["semantic_scholar"] = ss_results
        
        # Try PubMed as backup (medical focus)
        pubmed_results = self.search_pubmed(query, limit_per_source)
        if pubmed_results is not None:
            results["pubmed"] = pubmed_results
        
        # Log source availability
        available_sources = list(results.keys())
        logger.info(f"📊 Search completed using sources: {', '.join(available_sources)}")
        
        return results

    def get_session_statistics(self) -> Dict:
        """Get comprehensive session statistics"""
        total_calls = len(self.session_log)
        successful_calls = sum(1 for call in self.session_log if call["success"])
        
        api_stats = {}
        for api_name in self.circuit_breakers.keys():
            api_calls = [call for call in self.session_log if call["api"] == api_name]
            api_successful = sum(1 for call in api_calls if call["success"])
            
            api_stats[api_name] = {
                "total_calls": len(api_calls),
                "successful_calls": api_successful,
                "success_rate": api_successful / len(api_calls) if api_calls else 0,
                "circuit_state": self.circuit_breakers[api_name].state.value,
                "failure_count": self.circuit_breakers[api_name].failure_count
            }
        
        return {
            "session_summary": {
                "total_api_calls": total_calls,
                "successful_calls": successful_calls,
                "overall_success_rate": successful_calls / total_calls if total_calls else 0,
                "session_duration": time.time() - self.session_log[0]["timestamp"] if self.session_log else 0
            },
            "api_statistics": api_stats,
            "recent_errors": [
                call for call in self.session_log[-10:] 
                if not call["success"] and call["error"]
            ]
        }

    def save_session_log(self) -> Path:
        """Save session log for debugging and analysis"""
        log_file = self.session_dir / f"search_session_{int(time.time())}.json"
        
        session_data = {
            "session_statistics": self.get_session_statistics(),
            "detailed_log": self.session_log,
            "configuration": {
                "retry_config": {
                    "max_retries": self.retry_config.max_retries,
                    "base_delay": self.retry_config.base_delay,
                    "max_delay": self.retry_config.max_delay
                },
                "rate_limits": self.api_delays
            }
        }
        
        with open(log_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"💾 Session log saved: {log_file}")
        return log_file

def test_robust_search():
    """Test the robust search functionality"""
    print("🧪 Testing Robust Literature Search")
    
    searcher = RobustLiteratureSearch()
    
    # Test query
    test_query = "zika virus receptor interaction"
    
    # Test multi-source search
    results = searcher.search_multiple_sources(test_query, limit_per_source=5)
    
    # Print results
    for source, papers in results.items():
        print(f"\n📚 {source.upper()} Results ({len(papers)} papers):")
        for i, paper in enumerate(papers[:3], 1):
            title = paper.get('title', 'No title')[:80]
            print(f"  {i}. {title}...")
    
    # Print statistics
    stats = searcher.get_session_statistics()
    print(f"\n📊 Session Statistics:")
    print(f"  Total API calls: {stats['session_summary']['total_api_calls']}")
    print(f"  Success rate: {stats['session_summary']['overall_success_rate']:.2%}")
    
    for api, api_stats in stats['api_statistics'].items():
        print(f"  {api}: {api_stats['success_rate']:.2%} ({api_stats['circuit_state']})")
    
    # Save session log
    log_file = searcher.save_session_log()
    print(f"\n💾 Session saved: {log_file}")
    
    return results, stats

if __name__ == "__main__":
    test_robust_search()