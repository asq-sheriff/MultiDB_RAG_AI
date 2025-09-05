"""
Advanced Ranking Service with Multi-Signal Score Fusion
Implements sophisticated ranking with variance reduction and semantic relevance
"""

import logging
import math
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ai_services.core.cross_encoder_service import CrossEncoderService, AdvancedScoreNormalizer

logger = logging.getLogger(__name__)


class RankingStrategy(Enum):
    """Available ranking strategies"""
    COSINE_ONLY = "cosine_only"
    CROSS_ENCODER_ONLY = "cross_encoder_only"
    HYBRID_WEIGHTED = "hybrid_weighted"
    RRF_FUSION = "rrf_fusion"
    ADAPTIVE = "adaptive"  # Chooses best strategy based on variance


@dataclass
class RankingAnalysis:
    """Analysis of ranking quality and consistency"""
    original_variance: float
    final_variance: float
    variance_reduction: float
    score_distribution: Dict[str, float]
    ranking_strategy_used: str
    quality_improvement: float
    processing_time_ms: int


class AdvancedRankingService:
    """
    Advanced ranking service with multiple scoring techniques
    Addresses high score variance and improves semantic relevance
    """
    
    def __init__(self):
        self.cross_encoder = CrossEncoderService()
        self.normalizer = AdvancedScoreNormalizer()
        self.initialized = False
        
    async def initialize(self):
        """Initialize ranking components"""
        try:
            success = await self.cross_encoder.initialize()
            self.initialized = success
            
            if success:
                logger.info("✅ Advanced ranking service initialized")
            else:
                logger.warning("⚠️ Advanced ranking service running without cross-encoder")
                
            return True  # Service can run without cross-encoder (fallback mode)
            
        except Exception as e:
            logger.error(f"Failed to initialize advanced ranking service: {e}")
            return False
    
    async def rank_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        strategy: RankingStrategy = RankingStrategy.ADAPTIVE,
        top_k: Optional[int] = None,
        **kwargs
    ) -> Tuple[List[Dict[str, Any]], RankingAnalysis]:
        """
        Apply advanced ranking with variance reduction and semantic enhancement
        """
        
        if not results:
            return [], RankingAnalysis(
                original_variance=0.0,
                final_variance=0.0,
                variance_reduction=0.0,
                score_distribution={},
                ranking_strategy_used="empty_results",
                quality_improvement=0.0,
                processing_time_ms=0
            )
        
        start_time = time.time()
        
        # Calculate original score statistics
        original_scores = [r.get('score', 0) for r in results]
        original_variance = self._calculate_variance(original_scores)
        
        # Choose ranking strategy
        chosen_strategy = self._choose_strategy(strategy, original_variance, len(results))
        
        logger.info(f"Applying ranking strategy: {chosen_strategy.value}")
        
        # Apply chosen ranking strategy
        if chosen_strategy == RankingStrategy.COSINE_ONLY:
            ranked_results = await self._cosine_only_ranking(results)
            
        elif chosen_strategy == RankingStrategy.CROSS_ENCODER_ONLY:
            ranked_results = await self._cross_encoder_only_ranking(query, results)
            
        elif chosen_strategy == RankingStrategy.HYBRID_WEIGHTED:
            ranked_results = await self._hybrid_weighted_ranking(query, results)
            
        elif chosen_strategy == RankingStrategy.RRF_FUSION:
            ranked_results = await self._rrf_fusion_ranking(query, results)
            
        else:  # ADAPTIVE
            ranked_results = await self._adaptive_ranking(query, results, original_variance)
        
        # Apply top-k filtering
        if top_k:
            ranked_results = ranked_results[:top_k]
        
        # Calculate final statistics
        final_scores = [r.get('score', 0) for r in ranked_results]
        final_variance = self._calculate_variance(final_scores)
        variance_reduction = max(0, original_variance - final_variance)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        analysis = RankingAnalysis(
            original_variance=original_variance,
            final_variance=final_variance,
            variance_reduction=variance_reduction,
            score_distribution=self._analyze_score_distribution(final_scores),
            ranking_strategy_used=chosen_strategy.value,
            quality_improvement=self._calculate_quality_improvement(original_scores, final_scores),
            processing_time_ms=processing_time
        )
        
        logger.info(
            f"Ranking complete: variance {original_variance:.4f} -> {final_variance:.4f} "
            f"({variance_reduction:.4f} reduction), {processing_time}ms"
        )
        
        return ranked_results, analysis
    
    def _choose_strategy(
        self, 
        requested_strategy: RankingStrategy, 
        variance: float, 
        result_count: int
    ) -> RankingStrategy:
        """Choose optimal ranking strategy based on data characteristics"""
        
        if requested_strategy != RankingStrategy.ADAPTIVE:
            return requested_strategy
        
        # Adaptive strategy selection
        if variance < 0.1:
            return RankingStrategy.COSINE_ONLY  # Low variance, cosine is sufficient
        elif variance > 0.3 and self.initialized and result_count <= 20:
            return RankingStrategy.CROSS_ENCODER_ONLY  # High variance, use cross-encoder
        elif self.initialized:
            return RankingStrategy.HYBRID_WEIGHTED  # Balanced approach
        else:
            return RankingStrategy.COSINE_ONLY  # Fallback if cross-encoder unavailable
    
    async def _cosine_only_ranking(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhanced cosine similarity ranking with normalization"""
        
        # Normalize scores to reduce variance
        scores = [r.get('score', 0) for r in results]
        normalized_scores = self.normalizer.min_max_normalize(scores)
        
        enhanced_results = []
        for i, result in enumerate(results):
            enhanced_result = result.copy()
            enhanced_result['score'] = normalized_scores[i] * 10  # Scale back up
            enhanced_result['ranking_method'] = 'cosine_normalized'
            enhanced_results.append(enhanced_result)
        
        return sorted(enhanced_results, key=lambda x: x['score'], reverse=True)
    
    async def _cross_encoder_only_ranking(
        self, query: str, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Pure cross-encoder ranking"""
        
        rerank_result = await self.cross_encoder.rerank_results(
            query=query,
            results=results,
            score_threshold=0.1  # Lower threshold for cross-encoder only
        )
        
        return rerank_result.reranked_results
    
    async def _hybrid_weighted_ranking(
        self, query: str, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Hybrid ranking combining cosine similarity and cross-encoder"""
        
        # Get cross-encoder scores
        rerank_result = await self.cross_encoder.rerank_results(
            query=query,
            results=results,
            score_threshold=0.0  # Keep all results for hybrid combination
        )
        
        return rerank_result.reranked_results
    
    async def _rrf_fusion_ranking(
        self, query: str, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion of multiple ranking signals"""
        
        if not self.initialized:
            return await self._cosine_only_ranking(results)
        
        # Get different scoring perspectives
        cosine_scores = [r.get('score', 0) for r in results]
        
        # Get cross-encoder scores
        pairs = [(query, r.get('content', '')) for r in results]
        cross_encoder_scores = await self.cross_encoder.batch_score_pairs(pairs)
        
        # Apply RRF fusion
        fused_scores = self.normalizer.reciprocal_rank_fusion([
            cosine_scores,
            cross_encoder_scores
        ])
        
        # Create fused results
        fused_results = []
        for i, result in enumerate(results):
            enhanced_result = result.copy()
            enhanced_result.update({
                'score': fused_scores[i] * 10,  # Scale for consistency
                'cosine_score': cosine_scores[i],
                'cross_encoder_score': cross_encoder_scores[i] if i < len(cross_encoder_scores) else 0,
                'ranking_method': 'rrf_fusion'
            })
            fused_results.append(enhanced_result)
        
        return sorted(fused_results, key=lambda x: x['score'], reverse=True)
    
    async def _adaptive_ranking(
        self, query: str, results: List[Dict[str, Any]], variance: float
    ) -> List[Dict[str, Any]]:
        """Adaptive ranking that chooses best method based on data characteristics"""
        
        if variance < 0.15:
            # Low variance: enhance with normalization only
            return await self._cosine_only_ranking(results)
        elif variance > 0.4 and self.initialized:
            # Very high variance: use cross-encoder to fix
            return await self._cross_encoder_only_ranking(query, results)
        elif self.initialized:
            # Medium variance: hybrid approach
            return await self._hybrid_weighted_ranking(query, results)
        else:
            # Fallback: enhanced cosine
            return await self._cosine_only_ranking(results)
    
    def _calculate_variance(self, scores: List[float]) -> float:
        """Calculate score variance"""
        if len(scores) < 2:
            return 0.0
            
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        return variance
    
    def _analyze_score_distribution(self, scores: List[float]) -> Dict[str, float]:
        """Analyze score distribution for quality assessment"""
        if not scores:
            return {}
        
        return {
            'mean': sum(scores) / len(scores),
            'min': min(scores),
            'max': max(scores),
            'range': max(scores) - min(scores),
            'std_dev': math.sqrt(self._calculate_variance(scores)),
            'count': len(scores)
        }
    
    def _calculate_quality_improvement(self, original_scores: List[float], final_scores: List[float]) -> float:
        """Calculate overall quality improvement"""
        if not original_scores or not final_scores:
            return 0.0
        
        # Quality based on score consistency and magnitude
        original_quality = self._score_quality_metric(original_scores)
        final_quality = self._score_quality_metric(final_scores)
        
        if original_quality == 0:
            return 0.0
            
        return (final_quality - original_quality) / original_quality
    
    def _score_quality_metric(self, scores: List[float]) -> float:
        """Calculate a quality metric for score distribution"""
        if not scores:
            return 0.0
        
        # Quality = high mean scores with low variance
        mean_score = sum(scores) / len(scores)
        variance = self._calculate_variance(scores)
        
        # Quality metric: mean score penalized by variance
        quality = mean_score / (1 + variance)
        return quality


# Global instance for dependency injection
advanced_ranking_service = AdvancedRankingService()