#!/usr/bin/env python3
"""Test AI services (embedding and generation)"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()


async def test_embedding_service():
    """Test embedding service"""
    try:
        from ai_services.shared.dependencies.dependencies import embedding_service

        if not embedding_service:
            print("❌ Embedding: Service not initialized")
            return False

        # Test single embedding
        start = time.time()
        embedding = await embedding_service.embed_query("Test query for embedding")
        elapsed = time.time() - start

        if len(embedding) == 768:
            print(f"✅ Embedding: Working (768D, {elapsed:.2f}s)")
            return True
        else:
            print(f"❌ Embedding: Wrong dimension ({len(embedding)})")
            return False

    except Exception as e:
        print(f"❌ Embedding: {str(e)[:100]}")
        return False


async def test_generation_service():
    """Test generation service"""
    try:
        from ai_services.shared.dependencies.dependencies import generation_service

        if not generation_service:
            print("❌ Generation: Service not initialized")
            return False

        # Test generation
        start = time.time()
        response = await generation_service.generate(
            "Hello, how are you?", max_tokens=20
        )
        elapsed = time.time() - start

        if response and len(response) > 0:
            print(f"✅ Generation: Working ({elapsed:.2f}s)")
            return True
        else:
            print("❌ Generation: No response")
            return False

    except Exception as e:
        print(f"❌ Generation: {str(e)[:100]}")
        return False


async def test_knowledge_service():
    """Test knowledge/RAG service with advanced ranking"""
    try:
        from ai_services.shared.dependencies.dependencies import knowledge_service

        if not knowledge_service:
            print("❌ Knowledge: Service not initialized")
            return False

        # Test search with ranking analysis
        result = await knowledge_service.search_router(
            query="test query", top_k=3, route="auto"
        )

        if result and "results" in result:
            # Check if advanced ranking metadata is present
            ranking_meta = result.get('meta', {}).get('ranking_analysis')
            if ranking_meta:
                print(f"✅ Knowledge: Working with advanced ranking ({len(result['results'])} results, variance: {ranking_meta.final_variance:.4f})")
            else:
                print(f"✅ Knowledge: Working ({len(result['results'])} results)")
            return True
        else:
            print("❌ Knowledge: No results")
            return False

    except Exception as e:
        print(f"❌ Knowledge: {str(e)[:100]}")
        return False


async def test_advanced_ranking_service():
    """Test advanced ranking service functionality"""
    try:
        from ai_services.core.advanced_ranking_service import advanced_ranking_service, RankingStrategy
        
        # Test initialization
        await advanced_ranking_service.initialize()
        
        if not advanced_ranking_service.initialized:
            print("⚠️ Advanced Ranking: Running without cross-encoder")
        
        # Test with mock data
        mock_results = [
            {'content': 'test content 1', 'score': 8.5, 'id': '1'},
            {'content': 'test content 2', 'score': 3.2, 'id': '2'},  
            {'content': 'test content 3', 'score': 7.1, 'id': '3'}
        ]
        
        ranked_results, analysis = await advanced_ranking_service.rank_results(
            query="test query",
            results=mock_results,
            strategy=RankingStrategy.ADAPTIVE,
            top_k=3
        )
        
        if ranked_results and analysis:
            print(f"✅ Advanced Ranking: Working (strategy: {analysis.ranking_strategy_used}, variance: {analysis.final_variance:.4f})")
            return True
        else:
            print("❌ Advanced Ranking: No results")
            return False
            
    except Exception as e:
        print(f"❌ Advanced Ranking: {str(e)[:100]}")
        return False


async def test_cross_encoder_service():
    """Test cross-encoder re-ranking service"""
    try:
        from ai_services.core.cross_encoder_service import cross_encoder_service
        
        # Test initialization (may take time for model loading)
        success = await cross_encoder_service.initialize()
        
        if success:
            # Test scoring
            pairs = [("What is diabetes?", "Diabetes is a chronic condition affecting blood sugar levels")]
            scores = await cross_encoder_service.batch_score_pairs(pairs)
            
            if scores and len(scores) > 0:
                print(f"✅ Cross-Encoder: Working (score: {scores[0]:.4f})")
                return True
            else:
                print("❌ Cross-Encoder: No scores returned")
                return False
        else:
            print("⚠️ Cross-Encoder: Failed to load model")
            return False
            
    except Exception as e:
        print(f"❌ Cross-Encoder: {str(e)[:100]}")
        return False


async def test_chatbot_service():
    """Test chatbot service"""
    try:
        from ai_services.shared.dependencies.dependencies import chatbot_service

        if not chatbot_service:
            print("❌ Chatbot: Service not initialized")
            return False

        # Test chat
        response = await chatbot_service.answer_user_message(
            user_id="test_user", message="Hello"
        )

        if response and "answer" in response:
            print("✅ Chatbot: Working")
            return True
        else:
            print("❌ Chatbot: No response")
            return False

    except Exception as e:
        print(f"❌ Chatbot: {str(e)[:100]}")
        return False


async def main():
    print("\n🤖 AI SERVICE TESTS")
    print("=" * 50)

    results = []
    results.append(await test_embedding_service())
    results.append(await test_generation_service())
    results.append(await test_knowledge_service())
    results.append(await test_advanced_ranking_service())
    results.append(await test_cross_encoder_service())
    results.append(await test_chatbot_service())

    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} services working")
        return 0
    else:
        print(f"⚠️ {passed}/{total} services working")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
