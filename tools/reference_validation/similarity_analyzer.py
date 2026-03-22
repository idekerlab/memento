#!/usr/bin/env python3
"""
Text similarity and content analysis utilities for reference validation
Provides similarity scoring and content overlap analysis
"""

import json
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
import re

@dataclass
class SimilarityAnalysis:
    """Structure for similarity analysis results"""
    title_similarity: float
    author_match: str  # 'exact', 'partial', 'none'
    journal_similarity: float
    mechanism_overlap: float
    quantitative_match: bool
    topic_consistency: float
    overall_score: float
    analysis_details: Dict[str, Any]

class SimilarityAnalyzer:
    """Analyzer for content similarity and consistency"""
    
    def __init__(self):
        pass
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings using SequenceMatcher"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        clean1 = text1.lower().strip()
        clean2 = text2.lower().strip()
        
        return SequenceMatcher(None, clean1, clean2).ratio()
    
    def calculate_fuzzy_similarity(self, text1: str, text2: str) -> float:
        """Calculate fuzzy similarity handling common variations"""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts more aggressively
        def normalize(text):
            # Convert to lowercase
            text = text.lower()
            # Remove common punctuation and formatting
            text = re.sub(r'[^\w\s]', ' ', text)
            # Normalize whitespace
            text = ' '.join(text.split())
            # Remove common article words
            articles = ['the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by']
            words = text.split()
            words = [w for w in words if w not in articles]
            return ' '.join(words)
        
        norm1 = normalize(text1)
        norm2 = normalize(text2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def analyze_author_overlap(self, authors1: List[str], authors2: List[str]) -> Tuple[str, Dict[str, Any]]:
        """Analyze overlap between author lists"""
        if not authors1 or not authors2:
            return 'none', {'reason': 'missing_author_data'}
        
        # Extract surnames for comparison
        def extract_surnames(authors):
            surnames = []
            for author in authors:
                # Split on comma first (Last, First format)
                if ',' in author:
                    surnames.append(author.split(',')[0].strip().lower())
                else:
                    # Take last word as surname
                    words = author.strip().split()
                    if words:
                        surnames.append(words[-1].lower())
            return surnames
        
        surnames1 = extract_surnames(authors1)
        surnames2 = extract_surnames(authors2)
        
        # Calculate overlap
        overlap = set(surnames1) & set(surnames2)
        total_unique = set(surnames1) | set(surnames2)
        
        if not total_unique:
            return 'none', {'reason': 'no_valid_surnames'}
        
        overlap_ratio = len(overlap) / len(total_unique)
        
        details = {
            'surnames1': surnames1,
            'surnames2': surnames2,
            'overlap': list(overlap),
            'overlap_ratio': overlap_ratio
        }
        
        if overlap_ratio >= 0.8:
            return 'exact', details
        elif overlap_ratio >= 0.3:
            return 'partial', details
        else:
            return 'none', details
    
    def analyze_mechanism_overlap(self, extracted_terms: List[str], abstract_text: str) -> Tuple[float, Dict[str, Any]]:
        """Analyze overlap between mechanistic terms and abstract"""
        if not extracted_terms or not abstract_text:
            return 0.0, {'reason': 'missing_data'}
        
        abstract_lower = abstract_text.lower()
        
        # Direct term matching
        direct_matches = []
        for term in extracted_terms:
            if term.lower() in abstract_lower:
                direct_matches.append(term)
        
        # Fuzzy term matching for protein variants
        fuzzy_matches = []
        for term in extracted_terms:
            if term not in direct_matches:
                # Check for variants (e.g., NS1 vs NS-1, TIM1 vs TIM-1)
                variants = [
                    term.replace('-', ''),
                    term.replace('-', ' '),
                    re.sub(r'(\d)', r'-\1', term),
                    re.sub(r'(\d)', r' \1', term)
                ]
                for variant in variants:
                    if variant.lower() in abstract_lower and variant != term:
                        fuzzy_matches.append((term, variant))
                        break
        
        total_terms = len(extracted_terms)
        total_matches = len(direct_matches) + len(fuzzy_matches)
        
        overlap_score = total_matches / total_terms if total_terms > 0 else 0.0
        
        details = {
            'extracted_terms': extracted_terms,
            'direct_matches': direct_matches,
            'fuzzy_matches': fuzzy_matches,
            'total_terms': total_terms,
            'total_matches': total_matches
        }
        
        return overlap_score, details
    
    def analyze_quantitative_claims(self, extracted_claims: List[str], abstract_text: str) -> Tuple[bool, Dict[str, Any]]:
        """Analyze if quantitative claims are supported by abstract"""
        if not extracted_claims or not abstract_text:
            return False, {'reason': 'missing_data'}
        
        abstract_lower = abstract_text.lower()
        
        # Look for exact matches
        exact_matches = []
        for claim in extracted_claims:
            if claim.lower() in abstract_lower:
                exact_matches.append(claim)
        
        # Look for pattern matches (e.g., similar percentages, fold changes)
        pattern_matches = []
        for claim in extracted_claims:
            if claim not in exact_matches:
                # Extract numeric components
                numbers = re.findall(r'\d+(?:\.\d+)?', claim)
                for number in numbers:
                    if number in abstract_text:
                        pattern_matches.append((claim, number))
                        break
        
        any_matches = len(exact_matches) > 0 or len(pattern_matches) > 0
        
        details = {
            'extracted_claims': extracted_claims,
            'exact_matches': exact_matches,
            'pattern_matches': pattern_matches,
            'total_claims': len(extracted_claims)
        }
        
        return any_matches, details
    
    def analyze_topic_consistency(self, extracted_context: List[str], title: str, abstract: str) -> Tuple[float, Dict[str, Any]]:
        """Analyze consistency of topic context"""
        if not extracted_context:
            return 1.0, {'reason': 'no_context_to_check'}  # Assume consistent if no context specified
        
        combined_text = (title + ' ' + abstract).lower()
        
        # Direct context matching
        direct_matches = []
        for context in extracted_context:
            if context.lower() in combined_text:
                direct_matches.append(context)
        
        # Related term matching (e.g., dengue -> flavivirus)
        related_matches = []
        context_relations = {
            'dengue': ['flavivirus', 'arbovirus', 'aedes'],
            'zika': ['flavivirus', 'arbovirus', 'aedes'],
            'hepatitis': ['liver', 'hepatocyte', 'hbv', 'hcv'],
            'hiv': ['retrovirus', 'cd4', 't-cell'],
            'malaria': ['plasmodium', 'mosquito', 'anopheles'],
            'cancer': ['tumor', 'oncology', 'malignant', 'carcinoma'],
        }
        
        for context in extracted_context:
            if context not in direct_matches:
                context_lower = context.lower()
                if context_lower in context_relations:
                    for related_term in context_relations[context_lower]:
                        if related_term in combined_text:
                            related_matches.append((context, related_term))
                            break
        
        total_context = len(extracted_context)
        total_matches = len(direct_matches) + len(related_matches)
        
        consistency_score = total_matches / total_context if total_context > 0 else 1.0
        
        details = {
            'extracted_context': extracted_context,
            'direct_matches': direct_matches,
            'related_matches': related_matches,
            'total_context': total_context,
            'total_matches': total_matches
        }
        
        return consistency_score, details
    
    def comprehensive_analysis(self, extracted_content: Dict[str, Any], paper_metadata: Dict[str, Any]) -> SimilarityAnalysis:
        """Perform comprehensive similarity analysis"""
        
        # Title similarity
        title_sim = self.calculate_fuzzy_similarity(
            extracted_content.get('title', ''),
            paper_metadata.get('title', '')
        )
        
        # Author analysis
        author_match, author_details = self.analyze_author_overlap(
            extracted_content.get('authors', []),
            paper_metadata.get('authors', [])
        )
        
        # Journal similarity
        journal_sim = self.calculate_text_similarity(
            extracted_content.get('journal', ''),
            paper_metadata.get('journal', '')
        )
        
        # Mechanism overlap
        mechanism_score, mechanism_details = self.analyze_mechanism_overlap(
            extracted_content.get('mechanistic_terms', []),
            paper_metadata.get('abstract', '')
        )
        
        # Quantitative claims
        quant_match, quant_details = self.analyze_quantitative_claims(
            extracted_content.get('quantitative_claims', []),
            paper_metadata.get('abstract', '')
        )
        
        # Topic consistency
        topic_score, topic_details = self.analyze_topic_consistency(
            extracted_content.get('topic_context', []),
            paper_metadata.get('title', ''),
            paper_metadata.get('abstract', '')
        )
        
        # Calculate overall score (weighted average)
        weights = {
            'title': 0.4,
            'mechanism': 0.3,
            'topic': 0.2,
            'author': 0.1
        }
        
        overall_score = (
            title_sim * weights['title'] +
            mechanism_score * weights['mechanism'] +
            topic_score * weights['topic'] +
            (1.0 if author_match == 'exact' else 0.5 if author_match == 'partial' else 0.0) * weights['author']
        )
        
        analysis_details = {
            'author_analysis': author_details,
            'mechanism_analysis': mechanism_details,
            'quantitative_analysis': quant_details,
            'topic_analysis': topic_details,
            'weights_used': weights
        }
        
        return SimilarityAnalysis(
            title_similarity=title_sim,
            author_match=author_match,
            journal_similarity=journal_sim,
            mechanism_overlap=mechanism_score,
            quantitative_match=quant_match,
            topic_consistency=topic_score,
            overall_score=overall_score,
            analysis_details=analysis_details
        )

def main():
    """CLI interface for similarity analyzer"""
    if len(sys.argv) < 3:
        print("Usage: python similarity_analyzer.py <extracted_file> <metadata_file> [options]")
        print("  extracted_file: JSON file with extracted content")
        print("  metadata_file: JSON file with paper metadata")
        print("  --output <file>: Output file path for results")
        sys.exit(1)
    
    extracted_file = sys.argv[1]
    metadata_file = sys.argv[2]
    
    output_path = None
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_path = sys.argv[output_idx + 1]
    
    try:
        with open(extracted_file, 'r') as f:
            extracted_content = json.load(f)
        
        with open(metadata_file, 'r') as f:
            paper_metadata = json.load(f)
        
        analyzer = SimilarityAnalyzer()
        analysis = analyzer.comprehensive_analysis(extracted_content, paper_metadata)
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(asdict(analysis), f, indent=2)
            print(f"Analysis results exported to {output_path}")
        else:
            print(json.dumps(asdict(analysis), indent=2))
            
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()