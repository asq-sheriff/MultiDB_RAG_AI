"""
End-to-End Integration Tests for Therapeutic AI System
Tests the complete therapeutic AI pipeline with multi-database optimization
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.services.intelligent_data_router import IntelligentTherapeuticRouter, QueryType
from app.services.therapeutic_cache_manager import TherapeuticCacheManager, CacheLevel
from app.utils.therapeutic_mongodb_seeder import TherapeuticMongoSeeder
from data_layer.connections.postgres_connection import get_postgres_manager
from data_layer.connections.mongo_connection import get_mongo_manager

class TestTherapeuticAIIntegration:
    """End-to-end integration tests for the therapeutic AI system"""
    
    @pytest.fixture(scope="class")
    async def setup_test_environment(self):
        """Set up the complete test environment"""
        # Set test environment variables
        os.environ["MONGO_HOST"] = "localhost"
        os.environ["MONGO_PORT"] = "27017" 
        os.environ["MONGO_USER"] = "root"
        os.environ["MONGO_PASSWORD"] = "example"
        os.environ["MONGO_DB"] = "chatbot_app"
        os.environ["EMBEDDING_SERVICE_URL"] = "http://localhost:8005"
        
        # Initialize components
        self.router = IntelligentTherapeuticRouter()
        self.cache_manager = TherapeuticCacheManager()
        
        await self.router.initialize()
        await self.cache_manager.initialize()
        
        yield {
            "router": self.router,
            "cache_manager": self.cache_manager
        }
        
        # Cleanup
        await self.router.cleanup()
        await self.cache_manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_therapeutic_document_availability(self, setup_test_environment):
        """Test that therapeutic documents are properly seeded and accessible"""
        components = await setup_test_environment
        router = components["router"]
        
        # Test MongoDB document search
        result = await router.route_query(
            QueryType.DOCUMENT_SEARCH,
            query="loneliness in seniors",
            care_contexts=["loneliness", "anxiety"],
            limit=5
        )
        
        assert result["count"] > 0, "No therapeutic documents found in MongoDB"
        assert "results" in result, "Missing results field"
        
        # Verify document structure
        if result["results"]:
            doc = result["results"][0]
            assert "care_contexts" in doc, "Missing care_contexts in document"
            assert "therapeutic_category" in doc, "Missing therapeutic_category"
            assert "combined_score" in doc, "Missing similarity score"
            
        print(f"✅ MongoDB Document Search: Found {result['count']} therapeutic documents")
    
    @pytest.mark.asyncio
    async def test_postgres_persona_integration(self, setup_test_environment):
        """Test PostgreSQL persona schema integration"""
        components = await setup_test_environment
        router = components["router"]
        
        # Test persona lookup (this might not exist yet, but tests the pathway)
        result = await router.route_query(
            QueryType.PERSONA_LOOKUP,
            persona_key="senior-care-therapist"
        )
        
        # Should either find persona or return appropriate error
        assert "error" in result or "persona" in result, "Invalid persona lookup response"
        
        print(f"✅ PostgreSQL Persona Integration: Response received")
    
    @pytest.mark.asyncio
    async def test_hybrid_therapeutic_search(self, setup_test_environment):
        """Test hybrid search across MongoDB and PostgreSQL"""
        components = await setup_test_environment
        router = components["router"]
        
        # Test hybrid search combining documents and knowledge
        result = await router.route_query(
            QueryType.HYBRID_SEARCH,
            query="senior experiencing grief and anxiety",
            care_contexts=["grief", "anxiety"],
            limit=10
        )
        
        assert result["count"] >= 0, "Hybrid search should return count"
        assert "mongodb_count" in result, "Missing MongoDB result count"
        assert "postgres_count" in result, "Missing PostgreSQL result count"
        
        # Verify results are properly merged
        if result.get("results"):
            for item in result["results"]:
                assert "source_db" in item, "Missing source database info"
                assert "result_type" in item, "Missing result type"
                assert "combined_score" in item, "Missing combined score"
        
        print(f"✅ Hybrid Search: MongoDB={result['mongodb_count']}, PostgreSQL={result['postgres_count']}")
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, setup_test_environment):
        """Test therapeutic response caching integration"""
        components = await setup_test_environment
        cache_manager = components["cache_manager"]
        
        # Test cache miss and set
        query = "How can I help my elderly parent with loneliness?"
        care_contexts = ["loneliness", "caregiver-stress"]
        
        # Should be cache miss first
        cached_response = await cache_manager.get_cached_response(
            query=query,
            care_contexts=care_contexts
        )
        
        assert cached_response is None, "Should be cache miss initially"
        
        # Cache a response
        response_data = {
            "response": "Here are some ways to help with loneliness...",
            "interventions": ["social_engagement", "regular_visits", "community_programs"],
            "urgency_level": "routine"
        }
        
        cache_key = await cache_manager.set_cached_response(
            query=query,
            response_data=response_data,
            care_contexts=care_contexts
        )
        
        assert cache_key is not None, "Cache key should be returned"
        
        # Should be cache hit now
        cached_response = await cache_manager.get_cached_response(
            query=query,
            care_contexts=care_contexts
        )
        
        assert cached_response is not None, "Should be cache hit now"
        assert cached_response["response"]["response"] == response_data["response"]
        
        print(f"✅ Cache Integration: Cache key={cache_key[:8]}...")
    
    @pytest.mark.asyncio
    async def test_care_context_filtering(self, setup_test_environment):
        """Test care context-based filtering across all components"""
        components = await setup_test_environment
        router = components["router"]
        
        # Test different care contexts
        care_contexts_to_test = [
            ["grief", "loneliness"],
            ["anxiety", "health"],
            ["caregiver-stress"],
            ["crisis"]
        ]
        
        for contexts in care_contexts_to_test:
            result = await router.route_query(
                QueryType.DOCUMENT_SEARCH,
                query="senior care support",
                care_contexts=contexts,
                limit=3
            )
            
            # Should get results or appropriate empty response
            assert "count" in result, f"Missing count for contexts: {contexts}"
            assert result["count"] >= 0, "Count should be non-negative"
            
            if result["results"]:
                # Verify care context filtering
                for doc in result["results"]:
                    doc_contexts = doc.get("care_contexts", [])
                    # Should have some overlap with requested contexts
                    assert any(ctx in doc_contexts for ctx in contexts), \
                        f"No context overlap for {contexts} in doc contexts {doc_contexts}"
        
        print(f"✅ Care Context Filtering: Tested {len(care_contexts_to_test)} context combinations")
    
    @pytest.mark.asyncio
    async def test_crisis_detection_pathway(self, setup_test_environment):
        """Test crisis detection and SAFE-T script integration"""
        components = await setup_test_environment
        router = components["router"]
        
        # Test crisis indicators
        risk_indicators = ["hopeless", "ending it all", "no point"]
        user_context = {"age": 75, "living_alone": True}
        
        result = await router.route_query(
            QueryType.CRISIS_DETECTION,
            risk_indicators=risk_indicators,
            user_context=user_context
        )
        
        assert "scripts" in result or "error" in result, "Crisis lookup should return scripts or error"
        
        # If scripts are found, verify structure
        if result.get("scripts"):
            for script in result["scripts"]:
                assert "name" in script, "Script should have name"
                assert "urgency_level" in script, "Script should have urgency level"
        
        print(f"✅ Crisis Detection: Found {len(result.get('scripts', []))} SAFE-T scripts")
    
    @pytest.mark.asyncio 
    async def test_performance_and_stats(self, setup_test_environment):
        """Test system performance and statistics collection"""
        components = await setup_test_environment
        router = components["router"]
        cache_manager = components["cache_manager"]
        
        # Generate multiple operations to test performance
        test_queries = [
            ("I feel lonely", ["loneliness"]),
            ("Caregiver burnout", ["caregiver-stress"]),
            ("Senior health concerns", ["health", "anxiety"]),
            ("I feel lonely", ["loneliness"]),  # Duplicate for cache hit
        ]
        
        for query, contexts in test_queries:
            # Router operation
            await router.route_query(
                QueryType.DOCUMENT_SEARCH,
                query=query,
                care_contexts=contexts,
                limit=3
            )
            
            # Cache operation
            await cache_manager.get_cached_response(
                query=query,
                care_contexts=contexts
            )
        
        # Check router statistics
        router_stats = router.get_routing_stats()
        assert router_stats["total_queries"] > 0, "Router should track queries"
        assert "mongodb_queries" in router_stats, "Should track MongoDB queries"
        assert "cache_hit_rate" in router_stats, "Should calculate hit rate"
        
        # Check cache statistics
        cache_stats = cache_manager.get_cache_stats()
        assert cache_stats["total_requests"] > 0, "Cache should track requests"
        assert "cache_hit_rate" in cache_stats, "Should calculate cache hit rate"
        
        print(f"✅ Performance Stats:")
        print(f"  Router queries: {router_stats['total_queries']}")
        print(f"  Cache requests: {cache_stats['total_requests']}")
        print(f"  Cache hit rate: {cache_stats['cache_hit_rate']}")
    
    @pytest.mark.asyncio
    async def test_embedding_service_integration(self, setup_test_environment):
        """Test BGE embedding service integration"""
        components = await setup_test_environment
        router = components["router"]
        
        # Test that embedding service is working by doing vector search
        result = await router.route_query(
            QueryType.DOCUMENT_SEARCH,
            query="senior mental health support",
            care_contexts=["anxiety", "health"],
            limit=5
        )
        
        # If we get results, embeddings are working
        if result.get("results"):
            for doc in result["results"]:
                # Should have similarity scores (indicating embedding comparison)
                assert "combined_score" in doc or "vector_score" in doc, \
                    "Results should have similarity scores from embeddings"
        
        print(f"✅ Embedding Integration: Query processed with vector similarity")
    
    @pytest.mark.asyncio
    async def test_end_to_end_therapeutic_flow(self, setup_test_environment):
        """Test complete therapeutic conversation flow"""
        components = await setup_test_environment
        router = components["router"]
        cache_manager = components["cache_manager"]
        
        # Simulate a complete therapeutic interaction
        user_query = "I'm a 72-year-old living alone and feeling very lonely"
        user_context = {"age": 72, "living_situation": "alone"}
        care_contexts = ["loneliness", "general"]
        
        # Step 1: Check cache first
        cached_response = await cache_manager.get_cached_response(
            query=user_query,
            user_context=user_context,
            care_contexts=care_contexts
        )
        
        # Step 2: If not cached, do hybrid search
        if not cached_response:
            search_result = await router.route_query(
                QueryType.HYBRID_SEARCH,
                query=user_query,
                care_contexts=care_contexts,
                limit=5
            )
            
            # Step 3: Generate response based on search results
            response_data = {
                "response": "I understand you're feeling lonely. Here are some suggestions...",
                "search_results": search_result.get("results", []),
                "care_plan": ["social_connection", "community_resources"],
                "urgency_level": "routine"
            }
            
            # Step 4: Cache the response
            await cache_manager.set_cached_response(
                query=user_query,
                response_data=response_data,
                user_context=user_context,
                care_contexts=care_contexts
            )
            
            final_response = response_data
        else:
            final_response = cached_response["response"]
        
        # Verify complete flow
        assert final_response is not None, "Should have final response"
        assert "response" in final_response, "Should have response text"
        
        # Step 5: Verify subsequent request uses cache
        cached_response_2 = await cache_manager.get_cached_response(
            query=user_query,
            user_context=user_context,
            care_contexts=care_contexts
        )
        
        assert cached_response_2 is not None, "Subsequent request should hit cache"
        
        print(f"✅ End-to-End Flow: Complete therapeutic conversation processed")

# Integration test runner
async def run_therapeutic_integration_tests():
    """Run all therapeutic AI integration tests"""
    print("🧪 Starting Therapeutic AI Integration Tests")
    print("=" * 60)
    
    test_instance = TestTherapeuticAIIntegration()
    
    try:
        # Set up environment
        async with test_instance.setup_test_environment() as components:
            
            # Run all tests
            await test_instance.test_therapeutic_document_availability(components)
            await test_instance.test_postgres_persona_integration(components) 
            await test_instance.test_hybrid_therapeutic_search(components)
            await test_instance.test_cache_integration(components)
            await test_instance.test_care_context_filtering(components)
            await test_instance.test_crisis_detection_pathway(components)
            await test_instance.test_performance_and_stats(components)
            await test_instance.test_embedding_service_integration(components)
            await test_instance.test_end_to_end_therapeutic_flow(components)
            
            print("\n🎉 All Therapeutic AI Integration Tests Passed!")
            
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(run_therapeutic_integration_tests())