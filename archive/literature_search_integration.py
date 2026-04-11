#!/usr/bin/env python3
"""
Literature Search Integration for Critique Agent Workflows

Integrates robust literature search with existing workflow patterns and provides
comprehensive error recovery strategies for the literature claims discovery workflow.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from robust_literature_search import RobustLiteratureSearch
from citation_extractor import extract_paper_metadata, create_author_year_id
from corpus_analyzer import CorpusAnalyzer

logger = logging.getLogger(__name__)

class LiteratureSearchIntegration:
    """Integration layer for robust literature search with existing workflow tools"""
    
    def __init__(self, session_dir: str):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        
        # Initialize robust search
        self.searcher = RobustLiteratureSearch(str(self.session_dir))
        
        # Initialize corpus analyzer for duplicate detection
        self.corpus_analyzer = CorpusAnalyzer()
        
        # Recovery strategies - removed unused methods
        self.recovery_strategies = {
            "query_simplification": self._simplify_query,
            "cached_results": self._load_cached_results,
            "manual_fallback": self._generate_manual_fallback_suggestions
        }
        
        # Session state tracking
        self.session_state = {
            "queries_attempted": [],
            "papers_discovered": [],
            "failures_encountered": [],
            "recovery_actions": []
        }

    def discover_papers_with_recovery(self, query: str, target_count: int = 10) -> Tuple[List[Dict], Dict]:
        """
        Discover papers with comprehensive error recovery
        
        Returns:
            Tuple of (papers_list, recovery_report)
        """
        logger.info(f"🔍 Starting robust paper discovery: {query} (target: {target_count})")
        
        recovery_report = {
            "query": query,
            "target_count": target_count,
            "attempts": [],
            "final_count": 0,
            "recovery_actions": [],
            "success": False
        }
        
        papers = []
        
        # Primary attempt: Multi-source search
        try:
            results = self.searcher.search_multiple_sources(query, limit_per_source=target_count)
            
            # Process results from all available sources
            for source, source_papers in results.items():
                for paper in source_papers:
                    # Add source metadata
                    paper["discovery_source"] = source
                    paper["discovery_query"] = query
                    papers.append(paper)
            
            recovery_report["attempts"].append({
                "strategy": "multi_source_search",
                "sources_used": list(results.keys()),
                "papers_found": len(papers),
                "success": len(papers) > 0
            })
            
            if papers:
                recovery_report["success"] = True
                recovery_report["final_count"] = len(papers)
                logger.info(f"✅ Primary search successful: {len(papers)} papers")
                return self._deduplicate_papers(papers), recovery_report
                
        except Exception as e:
            logger.error(f"❌ Primary search failed: {e}")
            recovery_report["attempts"].append({
                "strategy": "multi_source_search", 
                "error": str(e),
                "success": False
            })
        
        # Recovery Strategy 1: Fallback with simplified query
        if len(papers) < target_count // 2:
            logger.info("🔄 Attempting recovery with simplified query")
            try:
                simplified_query = self._simplify_query(query)
                fallback_results = self.searcher.search_multiple_sources(
                    simplified_query, 
                    limit_per_source=target_count
                )
                
                fallback_papers = []
                for source, source_papers in fallback_results.items():
                    for paper in source_papers:
                        paper["discovery_source"] = f"{source}_fallback"
                        paper["discovery_query"] = simplified_query
                        fallback_papers.append(paper)
                
                papers.extend(fallback_papers)
                
                recovery_report["recovery_actions"].append({
                    "strategy": "simplified_query",
                    "original_query": query,
                    "simplified_query": simplified_query,
                    "additional_papers": len(fallback_papers)
                })
                
                logger.info(f"🔄 Simplified query recovery: +{len(fallback_papers)} papers")
                
            except Exception as e:
                logger.warning(f"⚠️ Simplified query recovery failed: {e}")
        
        # Recovery Strategy 2: Use cached results from previous sessions
        if len(papers) < target_count // 3:
            logger.info("🔄 Attempting recovery with cached results")
            try:
                cached_papers = self._load_cached_results(query)
                if cached_papers:
                    papers.extend(cached_papers)
                    recovery_report["recovery_actions"].append({
                        "strategy": "cached_results",
                        "cached_papers_used": len(cached_papers)
                    })
                    logger.info(f"🔄 Cache recovery: +{len(cached_papers)} papers")
            except Exception as e:
                logger.warning(f"⚠️ Cache recovery failed: {e}")
        
        # Recovery Strategy 3: Manual fallback suggestions
        if len(papers) == 0:
            logger.warning("🚨 All automated recovery failed, generating manual fallback")
            recovery_report["recovery_actions"].append({
                "strategy": "manual_fallback",
                "recommendations": self._generate_manual_fallback_suggestions(query)
            })
        
        # Final processing
        final_papers = self._deduplicate_papers(papers)
        recovery_report["final_count"] = len(final_papers)
        recovery_report["success"] = len(final_papers) > 0
        
        # Save session state
        self._save_recovery_session(query, final_papers, recovery_report)
        
        logger.info(f"📊 Final result: {len(final_papers)} papers after recovery")
        return final_papers, recovery_report

    def _simplify_query(self, query: str) -> str:
        """Simplify complex queries for fallback search"""
        # Remove common modifiers that might be too restrictive
        simplifications = [
            ("experimental", ""),
            ("mechanism", ""),
            ("pathway", ""),
            ("analysis", ""),
            ("proteomics", ""),
            (" AND ", " "),
            (" OR ", " ")
        ]
        
        simplified = query
        for old, new in simplifications:
            simplified = simplified.replace(old, new)
        
        # Keep only the most important terms (first 3-4 words)
        words = simplified.split()
        if len(words) > 4:
            simplified = " ".join(words[:4])
        
        return simplified.strip()

    def _deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers using existing corpus analyzer logic"""
        unique_papers = []
        seen_titles = set()
        seen_dois = set()
        
        for paper in papers:
            # Check DOI first (most reliable)
            doi = paper.get('doi') or paper.get('externalIds', {}).get('DOI')
            if doi and doi in seen_dois:
                continue
            
            # Check title similarity
            title = paper.get('title', '').lower().strip()
            if title and title in seen_titles:
                continue
            
            # Check against existing corpus
            if self.corpus_analyzer.is_duplicate(paper):
                logger.debug(f"Skipping duplicate: {title[:50]}...")
                continue
            
            # Add to unique set
            unique_papers.append(paper)
            if doi:
                seen_dois.add(doi)
            if title:
                seen_titles.add(title)
        
        logger.info(f"🔍 Deduplication: {len(papers)} → {len(unique_papers)} unique papers")
        return unique_papers

    def _load_cached_results(self, query: str) -> List[Dict]:
        """Load cached results from previous search sessions"""
        cache_files = list(self.session_dir.glob("search_session_*.json"))
        cached_papers = []
        
        for cache_file in cache_files[-5:]:  # Check last 5 sessions
            try:
                with open(cache_file, 'r') as f:
                    session_data = json.load(f)
                
                # Look for similar queries
                for log_entry in session_data.get("detailed_log", []):
                    if (log_entry.get("success") and 
                        self._query_similarity(query, log_entry.get("query", "")) > 0.5):
                        # This would need the actual paper data, not just logs
                        # For now, return empty list
                        pass
                        
            except Exception as e:
                logger.debug(f"Could not load cache file {cache_file}: {e}")
        
        return cached_papers

    def _query_similarity(self, query1: str, query2: str) -> float:
        """Calculate simple query similarity"""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def _generate_manual_fallback_suggestions(self, query: str) -> List[str]:
        """Generate suggestions for manual search when all APIs fail"""
        suggestions = [
            f"Try searching Google Scholar manually for: '{query}'",
            f"Check PubMed directly at: https://pubmed.ncbi.nlm.nih.gov/?term={query.replace(' ', '+')}",
            f"Search bioRxiv preprints: https://www.biorxiv.org/search/{query.replace(' ', '%20')}",
            f"Consider using institutional database access for: '{query}'",
            f"Try alternative search terms related to: {', '.join(query.split()[:3])}"
        ]
        return suggestions

    def _save_recovery_session(self, query: str, papers: List[Dict], recovery_report: Dict):
        """Save recovery session data for analysis"""
        session_file = self.session_dir / f"recovery_session_{int(__import__('time').time())}.json"
        
        session_data = {
            "query": query,
            "recovery_report": recovery_report,
            "papers_discovered": len(papers),
            "search_statistics": self.searcher.get_session_statistics(),
            "sample_papers": [
                {
                    "title": paper.get("title", "")[:100],
                    "source": paper.get("discovery_source", "unknown"),
                    "doi": paper.get("doi") or paper.get("externalIds", {}).get("DOI", "")
                }
                for paper in papers[:5]  # Save sample for debugging
            ]
        }
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        logger.info(f"💾 Recovery session saved: {session_file}")

    def process_papers_with_metadata(self, papers: List[Dict]) -> List[Dict]:
        """Process discovered papers with complete metadata extraction"""
        processed_papers = []
        
        for paper in papers:
            try:
                # Extract complete metadata using existing tool
                if paper.get("discovery_source") == "semantic_scholar":
                    metadata = extract_paper_metadata(paper)
                else:
                    # For PubMed or other sources, create compatible format
                    metadata = self._create_compatible_metadata(paper)
                
                # Add discovery context
                metadata["discovery_metadata"] = {
                    "query": paper.get("discovery_query", ""),
                    "source": paper.get("discovery_source", ""),
                    "discovery_timestamp": __import__('time').time()
                }
                
                processed_papers.append(metadata)
                
            except Exception as e:
                logger.warning(f"Failed to process paper metadata: {e}")
                # Continue with incomplete metadata rather than failing
                processed_papers.append({
                    "paper_metadata": {
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", []),
                        "abstract": paper.get("abstract", "")
                    },
                    "processing_error": str(e)
                })
        
        return processed_papers

    def _create_compatible_metadata(self, paper: Dict) -> Dict:
        """Create metadata format compatible with existing tools"""
        return {
            "paper_metadata": {
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "journal": paper.get("journal", paper.get("venue", "")),
                "year": str(paper.get("year", "")),
                "doi": paper.get("doi", ""),
                "pmid": paper.get("pmid", ""),
                "abstract": paper.get("abstract", "")
            },
            "access_metadata": {
                "access_status": "unknown",
                "pdf_available": "unknown",
                "pdf_source": paper.get("discovery_source", ""),
                "retrieval_method": "robust_search_integration"
            }
        }

def test_integration():
    """Test the integration functionality"""
    print("🧪 Testing Literature Search Integration")
    
    # Create test session
    integration = LiteratureSearchIntegration("test_session")
    
    # Test recovery mechanisms
    test_query = "zika virus receptor"
    papers, recovery_report = integration.discover_papers_with_recovery(test_query, target_count=5)
    
    print(f"\n📊 Discovery Results:")
    print(f"  Query: {test_query}")
    print(f"  Papers found: {len(papers)}")
    print(f"  Recovery successful: {recovery_report['success']}")
    print(f"  Attempts made: {len(recovery_report['attempts'])}")
    print(f"  Recovery actions: {len(recovery_report['recovery_actions'])}")
    
    # Show sample papers
    if papers:
        print(f"\n📚 Sample Papers:")
        for i, paper in enumerate(papers[:3], 1):
            title = paper.get("title", "No title")[:60]
            source = paper.get("discovery_source", "unknown")
            print(f"  {i}. [{source}] {title}...")
    
    return papers, recovery_report

if __name__ == "__main__":
    test_integration()