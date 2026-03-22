#!/usr/bin/env python3
"""
Reference validation classifier implementing decision logic
Classifies references based on dual-track validation results
"""

import json
import sys
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

@dataclass
class ValidationDecision:
    """Structure for validation decision results"""
    reference_id: str
    classification: str  # VERIFIED, DOI_ERROR, WRONG_PAPER, FABRICATION
    confidence_score: float
    primary_evidence: List[str]
    contradictory_evidence: List[str]
    correction_action: str
    correction_details: str
    expert_review_required: bool
    decision_reasoning: str

class ValidationClassifier:
    """Classifier for reference validation decisions"""
    
    def __init__(self, thresholds: Dict[str, float] = None):
        # Default thresholds (can be adjusted based on empirical testing)
        self.thresholds = thresholds or {
            'title_similarity_doi': 0.7,
            'mechanism_overlap': 0.3,
            'title_similarity_search': 0.8,
            'topic_consistency': 0.5,
            'overall_verification': 0.6
        }
    
    def classify_reference(self, 
                          extracted_content: Dict[str, Any],
                          doi_metadata: Optional[Dict[str, Any]],
                          title_metadata: Optional[Dict[str, Any]],
                          doi_analysis: Optional[Dict[str, Any]],
                          title_analysis: Optional[Dict[str, Any]]) -> ValidationDecision:
        """
        Classify reference based on dual-track validation results
        
        Decision Logic:
        1. VERIFIED: DOI consistent (high title similarity + mechanism overlap)
        2. DOI_ERROR: Title search finds correct paper, DOI points elsewhere
        3. WRONG_PAPER: DOI resolves but to unrelated content
        4. FABRICATION: Neither DOI nor title search finds matching paper
        """
        
        reference_id = extracted_content.get('reference_id', 'unknown')
        
        # Check DOI track consistency
        doi_consistent = False
        doi_evidence = []
        doi_contradictions = []
        
        if doi_metadata and doi_metadata.get('success', False) and doi_analysis:
            title_sim = doi_analysis.get('title_similarity', 0.0)
            mechanism_overlap = doi_analysis.get('mechanism_overlap', 0.0)
            topic_consistency = doi_analysis.get('topic_consistency', 0.0)
            
            # DOI consistency criteria
            if (title_sim >= self.thresholds['title_similarity_doi'] and 
                mechanism_overlap >= self.thresholds['mechanism_overlap']):
                doi_consistent = True
                doi_evidence.extend([
                    f"High title similarity: {title_sim:.2f}",
                    f"Good mechanism overlap: {mechanism_overlap:.2f}"
                ])
            else:
                doi_contradictions.extend([
                    f"Low title similarity: {title_sim:.2f}" if title_sim < self.thresholds['title_similarity_doi'] else None,
                    f"Poor mechanism overlap: {mechanism_overlap:.2f}" if mechanism_overlap < self.thresholds['mechanism_overlap'] else None
                ])
                doi_contradictions = [c for c in doi_contradictions if c]
            
            if topic_consistency < self.thresholds['topic_consistency']:
                doi_contradictions.append(f"Topic inconsistency: {topic_consistency:.2f}")
        
        # Check title track results
        title_match_found = False
        title_evidence = []
        title_contradictions = []
        
        if title_metadata and title_metadata.get('success', False) and title_analysis:
            title_sim = title_analysis.get('title_similarity', 0.0)
            mechanism_overlap = title_analysis.get('mechanism_overlap', 0.0)
            
            if (title_sim >= self.thresholds['title_similarity_search'] and
                mechanism_overlap >= self.thresholds['mechanism_overlap']):
                title_match_found = True
                title_evidence.extend([
                    f"High title search similarity: {title_sim:.2f}",
                    f"Good mechanism overlap in search result: {mechanism_overlap:.2f}"
                ])
        
        # Apply decision logic
        if doi_consistent:
            classification = "VERIFIED"
            confidence = self._calculate_confidence(doi_analysis, 'verified')
            primary_evidence = doi_evidence
            contradictory_evidence = []
            correction_action = "NONE"
            correction_details = "Reference is verified as accurate"
            expert_review = False
            reasoning = f"DOI resolves to consistent paper: {doi_metadata.get('title', 'N/A')}"
            
        elif title_match_found and doi_metadata and doi_metadata.get('success', False):
            classification = "DOI_ERROR"
            confidence = self._calculate_confidence(title_analysis, 'doi_error')
            primary_evidence = title_evidence
            contradictory_evidence = doi_contradictions
            correction_action = "UPDATE_DOI"
            correction_details = f"Update DOI from {extracted_content.get('doi', 'N/A')} to {title_metadata.get('doi', 'search_needed')}"
            expert_review = True
            reasoning = f"Correct paper found by title search: {title_metadata.get('title', 'N/A')}"
            
        elif doi_metadata and doi_metadata.get('success', False):
            classification = "WRONG_PAPER"
            confidence = self._calculate_confidence(doi_analysis, 'wrong_paper')
            primary_evidence = [f"DOI resolves to: {doi_metadata.get('title', 'N/A')}"]
            contradictory_evidence = doi_contradictions
            correction_action = "SEARCH_CORRECT_PAPER"
            correction_details = f"DOI points to unrelated paper. Manual literature search needed for claimed research."
            expert_review = True
            reasoning = f"DOI resolves to unrelated paper: {doi_metadata.get('title', 'N/A')}"
            
        else:
            classification = "FABRICATION"
            confidence = 0.1  # Low confidence, needs expert review
            primary_evidence = ["Neither DOI resolution nor title search found matching paper"]
            contradictory_evidence = []
            correction_action = "FLAG_POTENTIAL_FABRICATION"
            correction_details = "Potential AI-generated citation. Expert review and manual literature search required."
            expert_review = True
            reasoning = "No matching paper found through either validation track"
        
        return ValidationDecision(
            reference_id=reference_id,
            classification=classification,
            confidence_score=confidence,
            primary_evidence=primary_evidence,
            contradictory_evidence=contradictory_evidence,
            correction_action=correction_action,
            correction_details=correction_details,
            expert_review_required=expert_review,
            decision_reasoning=reasoning
        )
    
    def _calculate_confidence(self, analysis: Dict[str, Any], classification_type: str) -> float:
        """Calculate confidence score based on analysis results"""
        if not analysis:
            return 0.1
        
        title_sim = analysis.get('title_similarity', 0.0)
        mechanism_overlap = analysis.get('mechanism_overlap', 0.0)
        topic_consistency = analysis.get('topic_consistency', 1.0)  # Default to 1.0 if not available
        
        if classification_type == 'verified':
            # High confidence for strong matches
            base_score = (title_sim + mechanism_overlap + topic_consistency) / 3
            return min(0.95, max(0.7, base_score))
        
        elif classification_type == 'doi_error':
            # Medium confidence for correction cases
            base_score = (title_sim + mechanism_overlap) / 2
            return min(0.8, max(0.5, base_score))
        
        elif classification_type == 'wrong_paper':
            # Lower confidence, indicating clear mismatch
            mismatch_score = 1.0 - ((title_sim + mechanism_overlap) / 2)
            return min(0.7, max(0.2, mismatch_score))
        
        else:  # fabrication
            return 0.1
    
    def batch_classify(self, validation_results: List[Dict[str, Any]]) -> List[ValidationDecision]:
        """Classify multiple validation results"""
        decisions = []
        
        for result in validation_results:
            decision = self.classify_reference(
                result.get('extracted_content', {}),
                result.get('doi_metadata'),
                result.get('title_metadata'),
                result.get('doi_analysis'),
                result.get('title_analysis')
            )
            decisions.append(decision)
        
        return decisions
    
    def generate_summary_statistics(self, decisions: List[ValidationDecision]) -> Dict[str, Any]:
        """Generate summary statistics for classification results"""
        total = len(decisions)
        if total == 0:
            return {}
        
        # Count by classification
        classification_counts = {}
        confidence_scores = []
        expert_review_count = 0
        
        for decision in decisions:
            classification = decision.classification
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
            confidence_scores.append(decision.confidence_score)
            if decision.expert_review_required:
                expert_review_count += 1
        
        # Calculate statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        return {
            'total_references': total,
            'classification_breakdown': {
                cls: {'count': count, 'percentage': (count/total)*100}
                for cls, count in classification_counts.items()
            },
            'average_confidence': avg_confidence,
            'expert_review_required': expert_review_count,
            'expert_review_percentage': (expert_review_count/total)*100
        }

def main():
    """CLI interface for validation classifier"""
    if len(sys.argv) < 2:
        print("Usage: python validation_classifier.py <validation_results_file> [options]")
        print("  validation_results_file: JSON file with dual-track validation results")
        print("  --output <file>: Output file path for classification results")
        print("  --thresholds <file>: JSON file with custom thresholds")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    output_path = None
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_path = sys.argv[output_idx + 1]
    
    # Load custom thresholds if provided
    thresholds = None
    if "--thresholds" in sys.argv:
        thresholds_idx = sys.argv.index("--thresholds")
        if thresholds_idx + 1 < len(sys.argv):
            with open(sys.argv[thresholds_idx + 1], 'r') as f:
                thresholds = json.load(f)
    
    try:
        with open(results_file, 'r') as f:
            validation_results = json.load(f)
        
        classifier = ValidationClassifier(thresholds)
        
        # Handle both single result and batch results
        if isinstance(validation_results, list):
            decisions = classifier.batch_classify(validation_results)
        else:
            # Single result
            decision = classifier.classify_reference(
                validation_results.get('extracted_content', {}),
                validation_results.get('doi_metadata'),
                validation_results.get('title_metadata'),
                validation_results.get('doi_analysis'),
                validation_results.get('title_analysis')
            )
            decisions = [decision]
        
        # Generate summary
        summary = classifier.generate_summary_statistics(decisions)
        
        results = {
            'classification_decisions': [asdict(d) for d in decisions],
            'summary_statistics': summary,
            'thresholds_used': classifier.thresholds
        }
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Classification results exported to {output_path}")
        else:
            print(json.dumps(results, indent=2))
            
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()