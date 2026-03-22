#!/usr/bin/env python3
"""
Citation content extraction utilities for reference validation workflow
Designed to be called by the coding assistant agent
"""

import re
import json
import os
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class ExtractedContent:
    """Structure for extracted citation content"""
    # Basic citation components
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: List[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    
    # Context-enhanced components (when available)
    mechanistic_terms: List[str] = None
    quantitative_claims: List[str] = None
    topic_context: List[str] = None
    research_methods: List[str] = None
    
    # Extraction metadata
    extraction_confidence: float = 0.0
    parsing_issues: List[str] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.mechanistic_terms is None:
            self.mechanistic_terms = []
        if self.quantitative_claims is None:
            self.quantitative_claims = []
        if self.topic_context is None:
            self.topic_context = []
        if self.research_methods is None:
            self.research_methods = []
        if self.parsing_issues is None:
            self.parsing_issues = []

def extract_from_citation_text(citation_text: str) -> ExtractedContent:
    """Extract content from a raw citation string"""
    content = ExtractedContent()
    issues = []
    
    # DOI extraction
    doi_patterns = [
        r'doi:([^\s\]]+)',
        r'DOI:([^\s\]]+)', 
        r'https://doi\.org/([^\s\]]+)',
        r'http://dx\.doi\.org/([^\s\]]+)',
        r'\[doi:([^\]]+)\]'
    ]
    
    for pattern in doi_patterns:
        match = re.search(pattern, citation_text, re.IGNORECASE)
        if match:
            content.doi = match.group(1).strip()
            break
    
    if not content.doi:
        issues.append("no_doi_found")
    
    # Title extraction (look for quoted text)
    title_match = re.search(r'"([^"]+)"', citation_text)
    if title_match:
        content.title = title_match.group(1).strip()
    else:
        issues.append("no_quoted_title_found")
    
    # Author extraction (basic surname detection)
    # Look for patterns like "Smith, J." or "J. Smith"
    author_patterns = [
        r'([A-Z][a-z]+),\s*[A-Z]\.?',  # Smith, J.
        r'[A-Z]\.?\s+([A-Z][a-z]+)',   # J. Smith
    ]
    
    for pattern in author_patterns:
        matches = re.findall(pattern, citation_text)
        content.authors.extend(matches)
    
    # Year extraction
    year_match = re.search(r'\b(19|20)\d{2}\b', citation_text)
    if year_match:
        content.year = int(year_match.group(0))
    
    # Journal extraction (after title, before year typically)
    if content.title:
        post_title = citation_text.split(content.title)[-1]
        journal_match = re.search(r'["\.]?\s*([A-Z][^.]+?)[\.,]?\s*(?:\d{4}|doi)', post_title)
        if journal_match:
            content.journal = journal_match.group(1).strip()
    
    content.parsing_issues = issues
    content.extraction_confidence = max(0.0, 1.0 - len(issues) * 0.2)
    
    return content

def extract_from_hypothesis_file(file_path: str, domain_agnostic: bool = True) -> ExtractedContent:
    """Extract content from hypothesis file with context enhancement"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        content = ExtractedContent()
        content.parsing_issues = [f"file_read_error: {e}"]
        return content
    
    content = ExtractedContent()
    issues = []
    
    # Extract primary citation
    citation_match = re.search(r'\*\*Primary Citation:\*\*\s*\n([^\n]+(?:\n[^\n*]+)*)', text)
    if citation_match:
        citation_text = citation_match.group(1).strip()
        basic_content = extract_from_citation_text(citation_text)
        
        # Copy basic citation fields
        content.doi = basic_content.doi
        content.title = basic_content.title
        content.authors = basic_content.authors
        content.journal = basic_content.journal
        content.year = basic_content.year
        content.parsing_issues.extend(basic_content.parsing_issues)
    else:
        issues.append("no_primary_citation_section")
    
    # Context-enhanced extraction
    # Extract mechanistic terms
    mech_match = re.search(r'\*\*Mechanistic Details:\*\*\s*([^*]+?)(?=\*\*|$)', text, re.DOTALL)
    if mech_match:
        mech_text = mech_match.group(1)
        # Flexible protein/gene pattern matching
        protein_patterns = [
            r'\b[A-Z]+\d+[A-Z]*\b',      # NS1, STAT2, TIM-1
            r'\b[A-Z]{2,}(?:-\d+)?\b',   # RACK1, DC-SIGN
            r'\b[A-Z][a-z]+\d*\b'        # Atg5, Beclin1
        ]
        for pattern in protein_patterns:
            content.mechanistic_terms.extend(re.findall(pattern, mech_text))
    
    # Extract quantitative claims
    quant_match = re.search(r'\*\*Key Quantitative Findings:\*\*\s*([^*]+?)(?=\*\*|$)', text, re.DOTALL)
    if quant_match:
        quant_text = quant_match.group(1)
        number_patterns = [
            r'\d+(?:\.\d+)?(?:-\d+)?%',          # percentages
            r'\d+(?:\.\d+)?-fold',               # fold changes
            r'p\s*[<>=]\s*\d+\.\d+',            # p-values
            r'\d+(?:\.\d+)?\s*(?:μM|nM|mM|mg|μg|hours?|minutes?)',  # measurements
            r'IC50.*?\d+(?:\.\d+)?'              # IC50 values
        ]
        for pattern in number_patterns:
            content.quantitative_claims.extend(re.findall(pattern, quant_text, re.IGNORECASE))
    
    # Extract topic context
    text_lower = text.lower()
    if domain_agnostic:
        # Generic organism detection - configurable per domain
        organisms = ['dengue', 'zika', 'hepatitis', 'influenza', 'hiv', 'malaria', 'plasmodium', 
                    'tuberculosis', 'mycobacterium', 'cancer', 'diabetes', 'alzheimer']
        for org in organisms:
            if org in text_lower:
                content.topic_context.append(org)
        
        # Cell type detection
        cell_types = ['hepatocyte', 'macrophage', 'dendritic', 'endothelial', 'epithelial', 
                     'lymphocyte', 'neuron', 'astrocyte', 'fibroblast']
        for cell in cell_types:
            if cell in text_lower:
                content.topic_context.append(f"{cell}_cells")
    
    # Extract research methods
    method_patterns = [
        r'\b(?:western\s+blot|immunofluorescence|qpcr|elisa|flow\s+cytometry)\b',
        r'\b(?:knockdown|knockout|overexpression|transfection)\b',
        r'\b(?:microscopy|spectroscopy|chromatography)\b'
    ]
    for pattern in method_patterns:
        matches = re.findall(pattern, text_lower)
        content.research_methods.extend(matches)
    
    content.parsing_issues.extend(issues)
    content.extraction_confidence = max(0.0, 1.0 - len(content.parsing_issues) * 0.15)
    
    return content

def batch_extract_from_directory(directory_path: str, pattern: str = "*.md", domain_agnostic: bool = True) -> Dict[str, ExtractedContent]:
    """Extract content from all files matching pattern in directory"""
    import glob
    
    results = {}
    file_pattern = os.path.join(directory_path, pattern)
    files = glob.glob(file_pattern)
    
    for file_path in files:
        filename = os.path.basename(file_path)
        try:
            content = extract_from_hypothesis_file(file_path, domain_agnostic)
            results[filename] = content
        except Exception as e:
            error_content = ExtractedContent()
            error_content.parsing_issues = [f"batch_processing_error: {e}"]
            results[filename] = error_content
    
    return results

def export_results(results: Dict[str, ExtractedContent], output_path: str):
    """Export extraction results to JSON file"""
    json_results = {}
    for filename, content in results.items():
        json_results[filename] = asdict(content)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)

def main():
    """CLI interface for extraction tool"""
    if len(sys.argv) < 2:
        print("Usage: python citation_extractor.py <source> [options]")
        print("  source: citation text, file path, or directory path")
        print("  --domain-specific: Enable domain-specific extraction")
        print("  --batch: Process all .md files in directory")
        print("  --output: Output file path for results")
        sys.exit(1)
    
    source = sys.argv[1]
    domain_agnostic = "--domain-specific" not in sys.argv
    batch_mode = "--batch" in sys.argv
    
    # Get output path if specified
    output_path = None
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_path = sys.argv[output_idx + 1]
    
    if batch_mode and os.path.isdir(source):
        # Batch processing
        results = batch_extract_from_directory(source, domain_agnostic=domain_agnostic)
        
        if output_path:
            export_results(results, output_path)
            print(f"Results exported to {output_path}")
        else:
            print(json.dumps({k: asdict(v) for k, v in results.items()}, indent=2))
    
    elif os.path.isfile(source) and source.endswith('.md'):
        # Single file processing
        content = extract_from_hypothesis_file(source, domain_agnostic)
        result = asdict(content)
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results exported to {output_path}")
        else:
            print(json.dumps(result, indent=2))
    
    else:
        # Citation text processing
        content = extract_from_citation_text(source)
        result = asdict(content)
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results exported to {output_path}")
        else:
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()