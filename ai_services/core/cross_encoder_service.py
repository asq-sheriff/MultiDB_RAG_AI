"""
Cross-Encoder Re-ranking Service
Provides semantic relevance refinement for search results using cross-encoder models
Based on myrag_101.md Layer 2: Query Processing with Adaptive Feedback
"""

import logging
import math
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReRankingResult:
    """Result of cross-encoder re-ranking"""
    original_results: List[Dict[str, Any]]
    reranked_results: List[Dict[str, Any]]
    score_improvement: float
    variance_reduction: float
    processing_time_ms: int
    model_used: str


class CrossEncoderService:
    """
    Cross-encoder service for semantic relevance re-ranking
    
    Addresses the high score variance (0.32) issue by providing dedicated
    query-document pair scoring for better relevance assessment
    """
    
    def __init__(self):
        self.model = None
        self.model_name = "cross-encoder/ms-marco-MiniLM-L-12-v2"  # Fast, accurate
        self.device = "mps" if self._check_mps_available() else "cpu"
        self.batch_size = 8
        
    def _check_mps_available(self) -> bool:
        """Check if MPS (Metal Performance Shaders) is available"""
        try:
            import torch
            return torch.backends.mps.is_available() and torch.backends.mps.is_built()
        except ImportError:
            return False
    
    async def initialize(self):
        """Initialize cross-encoder model"""
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            start_time = time.time()
            
            self.model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=512
            )
            
            load_time = time.time() - start_time
            logger.info(f"✅ Cross-encoder loaded in {load_time:.2f}s on {self.device}")
            
            # Test the model
            test_scores = self.model.predict([
                ("What is the capital of France?", "Paris is the capital city of France.")
            ])
            logger.info(f"✅ Cross-encoder test score: {test_scores[0]:.4f}")
            
            return True
            
        except ImportError as e:
            logger.error(f"❌ sentence-transformers not available: {e}")
            logger.error("Install with: pip install sentence-transformers")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize cross-encoder: {e}")
            return False
    
    async def rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]], 
        top_k: Optional[int] = None,
        score_threshold: float = 0.5,
        variance_threshold: float = 0.2
    ) -> ReRankingResult:
        """
        Re-rank search results using cross-encoder for improved semantic relevance
        
        Args:
            query: User query
            results: List of search results with content and scores
            top_k: Maximum number of results to return
            score_threshold: Minimum cross-encoder score to keep
            variance_threshold: Apply re-ranking if score variance above this
        """
        
        if not self.model:
            logger.warning("Cross-encoder not initialized, skipping re-ranking")
            return ReRankingResult(
                original_results=results,
                reranked_results=results,
                score_improvement=0.0,
                variance_reduction=0.0,
                processing_time_ms=0,
                model_used="none"
            )
        
        if not results:
            return ReRankingResult(
                original_results=[],
                reranked_results=[],
                score_improvement=0.0,
                variance_reduction=0.0,
                processing_time_ms=0,
                model_used=self.model_name
            )
        
        start_time = time.time()
        
        try:
            # Calculate original score statistics
            original_scores = [r.get('score', 0) for r in results]
            original_variance = self._calculate_variance(original_scores)
            
            logger.debug(f"Original scores variance: {original_variance:.4f}")
            
            # Skip re-ranking if variance is already low
            if original_variance < variance_threshold:
                logger.debug("Score variance already low, skipping re-ranking")
                return ReRankingResult(
                    original_results=results,
                    reranked_results=results[:top_k] if top_k else results,
                    score_improvement=0.0,
                    variance_reduction=0.0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    model_used="skipped_low_variance"
                )
            
            # Prepare query-document pairs for cross-encoder
            pairs = []
            for result in results:
                content = result.get('content', '')
                if content:
                    # Truncate long content to fit model context window
                    content = content[:500] + "..." if len(content) > 500 else content
                    pairs.append((query, content))
            
            if not pairs:
                logger.warning("No valid content for re-ranking")
                return ReRankingResult(
                    original_results=results,
                    reranked_results=results,
                    score_improvement=0.0,
                    variance_reduction=0.0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    model_used="no_content"
                )
            
            # Batch process cross-encoder scoring
            cross_encoder_scores = []
            for i in range(0, len(pairs), self.batch_size):
                batch_pairs = pairs[i:i + self.batch_size]
                batch_scores = self.model.predict(batch_pairs)
                cross_encoder_scores.extend(batch_scores)
            
            # Create re-ranked results
            reranked_results = []
            for i, result in enumerate(results):
                if i < len(cross_encoder_scores):
                    cross_score = float(cross_encoder_scores[i])
                    
                    # Skip results below threshold
                    if cross_score < score_threshold:
                        continue
                    
                    # Create enhanced result with cross-encoder score
                    enhanced_result = result.copy()
                    enhanced_result.update({
                        'original_score': result.get('score', 0),
                        'cross_encoder_score': cross_score,
                        'score': self._combine_scores(
                            result.get('score', 0), 
                            cross_score
                        ),
                        'reranked': True,
                        'ranking_model': self.model_name
                    })
                    
                    reranked_results.append(enhanced_result)
            
            # Sort by combined score
            reranked_results.sort(key=lambda x: x['score'], reverse=True)
            
            # Limit results if requested
            if top_k:
                reranked_results = reranked_results[:top_k]
            
            # Calculate improvement metrics
            new_scores = [r['score'] for r in reranked_results]
            new_variance = self._calculate_variance(new_scores)
            
            variance_reduction = max(0, original_variance - new_variance)
            score_improvement = self._calculate_score_improvement(
                original_scores[:len(reranked_results)], new_scores
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Re-ranking complete: {len(results)} -> {len(reranked_results)} results, "
                f"variance: {original_variance:.4f} -> {new_variance:.4f} "
                f"({variance_reduction:.4f} reduction), {processing_time}ms"
            )
            
            return ReRankingResult(
                original_results=results,
                reranked_results=reranked_results,
                score_improvement=score_improvement,
                variance_reduction=variance_reduction,
                processing_time_ms=processing_time,
                model_used=self.model_name
            )
            
        except Exception as e:
            logger.error(f"Cross-encoder re-ranking failed: {e}")
            return ReRankingResult(
                original_results=results,
                reranked_results=results,
                score_improvement=0.0,
                variance_reduction=0.0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_used="error"
            )
    
    def _combine_scores(self, original_score: float, cross_encoder_score: float) -> float:
        """
        Combine original embedding similarity with cross-encoder relevance score
        
        Strategy: Weighted combination favoring cross-encoder for semantic relevance
        """
        # Normalize scores to 0-1 range
        normalized_original = max(0, min(1, original_score / 10))  # Assuming original scores can go up to 10
        normalized_cross = max(0, min(1, cross_encoder_score))
        
        # Weighted combination: 30% embedding similarity, 70% cross-encoder relevance
        combined = (0.3 * normalized_original) + (0.7 * normalized_cross)
        
        # Scale back to match original score range for consistency
        return combined * 10
    
    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate score variance for consistency assessment"""
        if len(scores) < 2:
            return 0.0
            
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        return variance
    
    def _calculate_score_improvement(self, original_scores: List[float], new_scores: List[float]) -> float:
        """Calculate relative improvement in score distribution"""
        if not original_scores or not new_scores:
            return 0.0
        
        # Compare mean scores (higher is better)
        original_mean = sum(original_scores) / len(original_scores)
        new_mean = sum(new_scores) / len(new_scores)
        
        if original_mean == 0:
            return 0.0
            
        improvement = (new_mean - original_mean) / original_mean
        return improvement

    async def batch_score_pairs(
        self, 
        query_document_pairs: List[Tuple[str, str]]
    ) -> List[float]:
        """
        Batch score query-document pairs for efficiency
        Used for large-scale re-ranking operations
        """
        if not self.model:
            logger.warning("Cross-encoder not initialized")
            return [0.0] * len(query_document_pairs)
        
        try:
            all_scores = []
            
            for i in range(0, len(query_document_pairs), self.batch_size):
                batch_pairs = query_document_pairs[i:i + self.batch_size]
                batch_scores = self.model.predict(batch_pairs)
                all_scores.extend(batch_scores)
            
            return [float(score) for score in all_scores]
            
        except Exception as e:
            logger.error(f"Batch scoring failed: {e}")
            return [0.0] * len(query_document_pairs)


class AdvancedScoreNormalizer:
    """
    Advanced score normalization and ranking techniques
    Addresses score variance issues and improves ranking consistency
    """
    
    @staticmethod
    def min_max_normalize(scores: List[float]) -> List[float]:
        """Min-max normalization to [0, 1] range"""
        if not scores:
            return []
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [0.5] * len(scores)  # All equal scores
        
        return [(score - min_score) / (max_score - min_score) for score in scores]
    
    @staticmethod
    def z_score_normalize(scores: List[float]) -> List[float]:
        """Z-score normalization for variance reduction"""
        if len(scores) < 2:
            return scores
        
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = math.sqrt(variance) if variance > 0 else 1.0
        
        return [(score - mean_score) / std_dev for score in scores]
    
    @staticmethod
    def percentile_rank_scores(scores: List[float]) -> List[float]:
        """Convert scores to percentile ranks for consistent distribution"""
        if not scores:
            return []
        
        sorted_scores = sorted(scores)
        
        percentile_scores = []
        for score in scores:
            # Find percentile rank
            rank = sum(1 for s in sorted_scores if s <= score)
            percentile = rank / len(sorted_scores)
            percentile_scores.append(percentile)
        
        return percentile_scores
    
    @staticmethod
    def reciprocal_rank_fusion(score_lists: List[List[float]], k: int = 60) -> List[float]:
        """
        Reciprocal Rank Fusion for combining multiple scoring methods
        Reduces variance by combining different ranking approaches
        """
        if not score_lists or not score_lists[0]:
            return []
        
        num_items = len(score_lists[0])
        fused_scores = [0.0] * num_items
        
        for scores in score_lists:
            # Convert scores to ranks
            sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            
            # Apply RRF formula
            for rank, idx in enumerate(sorted_indices, 1):
                fused_scores[idx] += 1 / (k + rank)
        
        return fused_scores


# Global instance
cross_encoder_service = CrossEncoderService()
score_normalizer = AdvancedScoreNormalizer()