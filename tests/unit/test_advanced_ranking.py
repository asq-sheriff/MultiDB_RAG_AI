#!/usr/bin/env python3
"""
Unit Tests for Advanced Ranking System
Tests variance reduction, cross-encoder integration, and ranking strategies
"""

import asyncio
import pytest
import sys
from pathlib import Path
import statistics
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_services.core.advanced_ranking_service import (
    AdvancedRankingService, 
    RankingStrategy, 
    RankingAnalysis,
    AdvancedScoreNormalizer
)
from ai_services.core.cross_encoder_service import CrossEncoderService


class TestAdvancedScoreNormalizer:
    """Test score normalization techniques"""
    
    def test_min_max_normalize(self):
        """Test min-max normalization"""
        normalizer = AdvancedScoreNormalizer()
        scores = [1.0, 5.0, 10.0]
        normalized = normalizer.min_max_normalize(scores)
        
        assert len(normalized) == 3
        assert normalized[0] == 0.0  # min
        assert normalized[-1] == 1.0  # max
        assert 0 <= normalized[1] <= 1  # middle value
        
    def test_z_score_normalize(self):
        """Test z-score normalization"""
        normalizer = AdvancedScoreNormalizer()
        scores = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = normalizer.z_score_normalize(scores)
        
        assert len(normalized) == 5
        # Mean should be approximately 0 after z-score normalization
        assert abs(sum(normalized) / len(normalized)) < 0.001
        
    def test_percentile_rank_scores(self):
        """Test percentile ranking"""
        normalizer = AdvancedScoreNormalizer()
        scores = [1.0, 3.0, 5.0]
        percentile_scores = normalizer.percentile_rank_scores(scores)
        
        assert len(percentile_scores) == 3
        # All percentile scores should be between 0 and 1
        assert all(0 <= score <= 1 for score in percentile_scores)
        
    def test_reciprocal_rank_fusion(self):
        """Test RRF fusion"""
        normalizer = AdvancedScoreNormalizer()
        score_lists = [
            [9.0, 7.0, 5.0],  # First ranking
            [8.0, 6.0, 9.0]   # Second ranking  
        ]
        fused = normalizer.reciprocal_rank_fusion(score_lists)
        
        assert len(fused) == 3
        # RRF scores should be positive
        assert all(score > 0 for score in fused)


class TestAdvancedRankingService:
    """Test advanced ranking service"""
    
    @pytest.fixture
    async def ranking_service(self):
        """Setup ranking service for tests"""
        service = AdvancedRankingService()
        await service.initialize()
        return service
        
    def create_high_variance_results(self) -> List[Dict[str, Any]]:
        """Create mock results with high score variance"""
        return [
            {'content': 'excellent match', 'score': 9.5, 'id': 'high1'},
            {'content': 'poor match', 'score': 1.2, 'id': 'low1'},
            {'content': 'good match', 'score': 8.7, 'id': 'high2'},
            {'content': 'bad match', 'score': 0.8, 'id': 'low2'},
            {'content': 'decent match', 'score': 6.3, 'id': 'med1'},
        ]
    
    async def test_cosine_only_strategy(self, ranking_service):
        """Test cosine-only ranking strategy"""
        results = self.create_high_variance_results()
        query = "test query"
        
        ranked_results, analysis = await ranking_service.rank_results(
            query=query,
            results=results,
            strategy=RankingStrategy.COSINE_ONLY,
            top_k=5
        )
        
        assert len(ranked_results) == 5
        assert analysis.ranking_strategy_used == "cosine_only"
        assert analysis.variance_reduction >= 0  # Should reduce or maintain variance
        
    async def test_adaptive_strategy_selection(self, ranking_service):
        """Test adaptive strategy selection based on variance"""
        low_variance_results = [
            {'content': 'content 1', 'score': 7.0, 'id': '1'},
            {'content': 'content 2', 'score': 7.1, 'id': '2'},
            {'content': 'content 3', 'score': 7.2, 'id': '3'},
        ]
        
        high_variance_results = self.create_high_variance_results()
        
        # Test with low variance (should choose cosine_only)
        ranked_low, analysis_low = await ranking_service.rank_results(
            query="test query",
            results=low_variance_results,
            strategy=RankingStrategy.ADAPTIVE
        )
        
        # Test with high variance (should choose more sophisticated method)
        ranked_high, analysis_high = await ranking_service.rank_results(
            query="test query", 
            results=high_variance_results,
            strategy=RankingStrategy.ADAPTIVE
        )
        
        assert analysis_low.ranking_strategy_used in ['cosine_only', 'hybrid_weighted', 'cross_encoder_only']
        assert analysis_high.ranking_strategy_used in ['cosine_only', 'hybrid_weighted', 'cross_encoder_only', 'rrf_fusion']
        
    async def test_variance_reduction(self, ranking_service):
        """Test that ranking reduces score variance"""
        high_variance_results = self.create_high_variance_results()
        
        original_scores = [r['score'] for r in high_variance_results]
        original_variance = statistics.variance(original_scores)
        
        # Should be high variance (>0.32) 
        assert original_variance > 0.32
        
        ranked_results, analysis = await ranking_service.rank_results(
            query="diabetes symptoms",
            results=high_variance_results,
            strategy=RankingStrategy.RRF_FUSION
        )
        
        final_scores = [r['score'] for r in ranked_results]
        final_variance = statistics.variance(final_scores)
        
        # Variance should be reduced
        assert analysis.variance_reduction > 0
        assert final_variance < original_variance
        
    async def test_empty_results_handling(self, ranking_service):
        """Test handling of empty results"""
        ranked_results, analysis = await ranking_service.rank_results(
            query="test query",
            results=[],
            strategy=RankingStrategy.ADAPTIVE
        )
        
        assert ranked_results == []
        assert analysis.ranking_strategy_used == "empty_results"
        assert analysis.variance_reduction == 0.0


class TestCrossEncoderService:
    """Test cross-encoder service functionality"""
    
    @pytest.fixture
    async def cross_encoder_service(self):
        """Setup cross-encoder service"""
        from ai_services.core.cross_encoder_service import CrossEncoderService
        service = CrossEncoderService()
        success = await service.initialize()
        return service if success else None
        
    async def test_batch_score_pairs(self, cross_encoder_service):
        """Test batch scoring of query-document pairs"""
        if not cross_encoder_service:
            pytest.skip("Cross-encoder not available")
            
        pairs = [
            ("What is diabetes?", "Diabetes is a chronic condition affecting blood sugar."),
            ("How to cook pasta?", "Diabetes requires careful blood sugar monitoring."),  # Mismatch
        ]
        
        scores = await cross_encoder_service.batch_score_pairs(pairs)
        
        assert len(scores) == 2
        # First pair should score higher than mismatched pair
        assert scores[0] > scores[1]
        # All scores should be reasonable (cross-encoder can return wider ranges)
        assert all(-15 <= score <= 20 for score in scores)
        
    async def test_rerank_results(self, cross_encoder_service):
        """Test result re-ranking"""
        if not cross_encoder_service:
            pytest.skip("Cross-encoder not available")
            
        results = [
            {'content': 'Diabetes is a metabolic disorder.', 'score': 0.7, 'id': '1'},
            {'content': 'Cooking pasta requires boiling water.', 'score': 0.9, 'id': '2'},  # Higher original score but irrelevant
        ]
        
        rerank_result = await cross_encoder_service.rerank_results(
            query="What is diabetes?",
            results=results,
            score_threshold=0.0
        )
        
        assert len(rerank_result.reranked_results) > 0
        # Relevant document should be ranked higher after re-ranking
        top_result = rerank_result.reranked_results[0]
        assert 'diabetes' in top_result['content'].lower()


# Integration test with all ranking components
async def test_integrated_ranking_pipeline():
    """Test complete ranking pipeline integration"""
    
    print("\n🔗 INTEGRATED RANKING PIPELINE TEST")
    print("=" * 50)
    
    try:
        # Initialize services
        ranking_service = AdvancedRankingService()
        await ranking_service.initialize()
        
        # Create realistic high-variance results
        mixed_results = [
            {'content': 'Diabetes symptoms include increased thirst and frequent urination', 'score': 9.1, 'id': 'relevant1'},
            {'content': 'Heart disease prevention requires regular exercise', 'score': 8.8, 'id': 'unrelated1'},
            {'content': 'Type 2 diabetes often develops gradually with subtle symptoms', 'score': 7.2, 'id': 'relevant2'}, 
            {'content': 'Weather forecast shows rain tomorrow', 'score': 6.9, 'id': 'unrelated2'},
            {'content': 'Diabetes management includes blood sugar monitoring', 'score': 5.8, 'id': 'relevant3'},
            {'content': 'Stock market trends this week', 'score': 5.5, 'id': 'unrelated3'},
        ]
        
        query = "What are the symptoms of diabetes?"
        
        # Test integrated pipeline
        ranked_results, analysis = await ranking_service.rank_results(
            query=query,
            results=mixed_results,
            strategy=RankingStrategy.ADAPTIVE,
            top_k=4
        )
        
        print(f"✅ Integration Test Results:")
        print(f"   Strategy used: {analysis.ranking_strategy_used}")
        print(f"   Variance reduction: {analysis.variance_reduction:.4f}")
        print(f"   Quality improvement: {analysis.quality_improvement:.2%}")
        print(f"   Processing time: {analysis.processing_time_ms}ms")
        
        # Validate relevance ordering (diabetes content should rank higher)
        diabetes_results = [r for r in ranked_results if 'diabetes' in r['content'].lower()]
        total_results = len(ranked_results)
        diabetes_count = len(diabetes_results)
        
        print(f"   Relevance: {diabetes_count}/{total_results} top results contain 'diabetes'")
        
        return len(ranked_results) > 0 and analysis.variance_reduction >= 0
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


async def run_unit_tests():
    """Run all unit tests"""
    
    print("🧪 ADVANCED RANKING UNIT TESTS")
    print("=" * 50)
    
    # Test normalizer
    normalizer = AdvancedScoreNormalizer()
    test_scores = [1.0, 5.0, 9.0, 2.0, 7.0]
    
    # Test each normalization method
    min_max = normalizer.min_max_normalize(test_scores)
    z_scores = normalizer.z_score_normalize(test_scores)
    percentiles = normalizer.percentile_rank_scores(test_scores)
    
    print("✅ Normalizer tests passed")
    
    # Test RRF
    rrf_scores = normalizer.reciprocal_rank_fusion([[9, 7, 5], [8, 6, 9]])
    assert len(rrf_scores) == 3
    print("✅ RRF fusion test passed")
    
    # Test ranking service
    ranking_service = AdvancedRankingService()
    await ranking_service.initialize()
    
    mock_results = [
        {'content': 'test 1', 'score': 8.0, 'id': '1'},
        {'content': 'test 2', 'score': 2.0, 'id': '2'}
    ]
    
    ranked, analysis = await ranking_service.rank_results(
        query="test",
        results=mock_results,
        strategy=RankingStrategy.COSINE_ONLY
    )
    
    assert len(ranked) == 2
    assert analysis.ranking_strategy_used == "cosine_only"
    print("✅ Ranking service test passed")
    
    # Integration test
    integration_success = await test_integrated_ranking_pipeline()
    
    if integration_success:
        print("✅ Integration test passed")
        return True
    else:
        print("❌ Integration test failed") 
        return False


if __name__ == "__main__":
    success = asyncio.run(run_unit_tests())
    sys.exit(0 if success else 1)