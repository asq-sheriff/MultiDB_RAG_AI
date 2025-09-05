"""
Confidence-based search result evaluator for cascading search strategy
Optimizes RAG pipeline performance by evaluating text search confidence
"""

import re
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ConfidenceScore:
    """Confidence score with breakdown metrics"""
    overall: float
    text_match: float
    medical_terms: float
    therapeutic_context: float
    result_count: int
    top_score: float


class ConfidenceEvaluator:
    """Evaluates confidence in text search results for cascading strategy"""
    
    def __init__(self):
        # Medical/healthcare term patterns
        self.medical_terms = {
            'medications': r'\b(medication|medicine|drug|pill|dose|dosage|prescription)\b',
            'symptoms': r'\b(pain|anxiety|depression|nausea|fatigue|dizzy|shortness|breathing)\b',
            'procedures': r'\b(surgery|treatment|therapy|procedure|examination|test|scan)\b',
            'conditions': r'\b(diabetes|hypertension|arthritis|dementia|alzheimer|heart|kidney)\b',
            'care_terms': r'\b(care|nursing|assistance|help|support|monitor|assess)\b'
        }
        
        # Therapeutic conversation patterns
        self.therapeutic_patterns = {
            'emotions': r'\b(feel|feeling|sad|happy|worried|scared|angry|lonely|upset)\b',
            'social': r'\b(family|friend|visit|talk|conversation|lonely|isolated)\b',
            'activities': r'\b(exercise|walk|hobby|activity|garden|read|music|game)\b',
            'daily_living': r'\b(eat|sleep|bath|dress|meal|breakfast|lunch|dinner)\b'
        }

    def evaluate_text_results(
        self, 
        query: str, 
        results: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> ConfidenceScore:
        """
        Evaluate confidence in text search results
        
        Returns confidence score indicating if vector search is needed
        """
        if not results:
            return ConfidenceScore(
                overall=0.0, text_match=0.0, medical_terms=0.0,
                therapeutic_context=0.0, result_count=0, top_score=0.0
            )
        
        # Base metrics
        result_count = len(results)
        top_score = results[0].get('score', 0.0) if results else 0.0
        
        # Text match quality assessment
        text_match_score = self._evaluate_text_match_quality(query, results)
        
        # Medical terminology coverage
        medical_score = self._evaluate_medical_coverage(query, results)
        
        # Therapeutic context relevance
        therapeutic_score = self._evaluate_therapeutic_context(query, results)
        
        # Compute overall confidence
        overall_confidence = self._compute_overall_confidence(
            text_match_score, medical_score, therapeutic_score,
            result_count, top_score, top_k
        )
        
        return ConfidenceScore(
            overall=overall_confidence,
            text_match=text_match_score,
            medical_terms=medical_score,
            therapeutic_context=therapeutic_score,
            result_count=result_count,
            top_score=top_score
        )

    def _evaluate_text_match_quality(self, query: str, results: List[Dict]) -> float:
        """Evaluate quality of text search matches"""
        if not results:
            return 0.0
            
        query_words = set(query.lower().split())
        if not query_words:
            return 0.0
        
        match_scores = []
        
        for result in results[:3]:  # Focus on top 3 results
            content = (result.get('content', '') + ' ' + result.get('title', '')).lower()
            content_words = set(content.split())
            
            # Exact word matches
            exact_matches = len(query_words.intersection(content_words))
            exact_ratio = exact_matches / len(query_words)
            
            # Partial word matches (fuzzy)
            partial_matches = 0
            for q_word in query_words:
                if any(q_word in c_word or c_word in q_word for c_word in content_words):
                    partial_matches += 1
            partial_ratio = partial_matches / len(query_words)
            
            # Score with text search score if available
            text_score = result.get('score', 0.0)
            normalized_text_score = min(text_score / 10.0, 1.0) if text_score else 0.0
            
            # Combine metrics
            match_quality = (exact_ratio * 0.6 + partial_ratio * 0.3 + normalized_text_score * 0.1)
            match_scores.append(match_quality)
        
        return sum(match_scores) / len(match_scores) if match_scores else 0.0

    def _evaluate_medical_coverage(self, query: str, results: List[Dict]) -> float:
        """Evaluate medical/healthcare terminology coverage"""
        query_lower = query.lower()
        
        # Check if query contains medical terms
        query_medical_score = 0.0
        for category, pattern in self.medical_terms.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                query_medical_score += 0.2  # Each category adds 20%
        
        if query_medical_score == 0.0:
            return 0.5  # Neutral score for non-medical queries
        
        # Check if results contain relevant medical terms
        result_medical_scores = []
        
        for result in results[:3]:
            content = (result.get('content', '') + ' ' + result.get('title', '')).lower()
            result_score = 0.0
            
            for category, pattern in self.medical_terms.items():
                if re.search(pattern, content, re.IGNORECASE):
                    result_score += 0.2
            
            result_medical_scores.append(min(result_score, 1.0))
        
        avg_result_score = sum(result_medical_scores) / len(result_medical_scores) if result_medical_scores else 0.0
        
        # Higher confidence if both query and results are medical
        return min(query_medical_score * avg_result_score * 1.5, 1.0)

    def _evaluate_therapeutic_context(self, query: str, results: List[Dict]) -> float:
        """Evaluate therapeutic conversation context relevance"""
        query_lower = query.lower()
        
        # Check therapeutic patterns in query
        query_therapeutic_score = 0.0
        for category, pattern in self.therapeutic_patterns.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                query_therapeutic_score += 0.25  # Each category adds 25%
        
        if query_therapeutic_score == 0.0:
            return 0.5  # Neutral for non-therapeutic queries
        
        # Check therapeutic context in results
        result_therapeutic_scores = []
        
        for result in results[:3]:
            content = (result.get('content', '') + ' ' + result.get('title', '')).lower()
            result_score = 0.0
            
            for category, pattern in self.therapeutic_patterns.items():
                if re.search(pattern, content, re.IGNORECASE):
                    result_score += 0.25
            
            result_therapeutic_scores.append(min(result_score, 1.0))
        
        avg_result_score = sum(result_therapeutic_scores) / len(result_therapeutic_scores) if result_therapeutic_scores else 0.0
        
        # Balance query and result therapeutic relevance
        return (query_therapeutic_score * 0.4 + avg_result_score * 0.6)

    def _compute_overall_confidence(
        self, 
        text_match: float,
        medical: float, 
        therapeutic: float,
        result_count: int,
        top_score: float,
        expected_results: int
    ) -> float:
        """Compute overall confidence score with healthcare-specific weights"""
        
        # Base confidence from text matching
        base_confidence = text_match * 0.5
        
        # Healthcare domain boost
        domain_confidence = (medical * 0.3 + therapeutic * 0.2)
        
        # Result quantity penalty
        quantity_factor = min(result_count / max(expected_results, 1), 1.0)
        
        # Top result score boost (if available)
        score_boost = min(top_score / 20.0, 0.1) if top_score else 0.0
        
        # Combine all factors
        overall = base_confidence + domain_confidence + score_boost
        overall *= quantity_factor
        
        return min(max(overall, 0.0), 1.0)  # Clamp to [0, 1]

    def should_cascade_to_vector(self, confidence: ConfidenceScore, config: 'SearchConfig') -> str:
        """
        Determine search strategy based on confidence
        
        Returns: 'text_only', 'hybrid', or 'vector_only'
        """
        if not config.enable_confidence_cascading:
            return 'hybrid'  # Default behavior
        
        # Special handling for medical queries
        if confidence.medical_terms > config.medical_term_confidence:
            if confidence.overall >= config.high_confidence_threshold:
                return 'text_only'  # High confidence medical terms
            else:
                return 'hybrid'  # Medium confidence medical - enhance with vector
        
        # Special handling for therapeutic queries
        if confidence.therapeutic_context > config.therapeutic_confidence:
            return 'hybrid'  # Therapeutic queries always benefit from semantic search
        
        # General confidence-based routing
        if confidence.overall >= config.high_confidence_threshold:
            return 'text_only'
        elif confidence.overall >= config.medium_confidence_threshold:
            return 'hybrid'
        else:
            return 'vector_only'