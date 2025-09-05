"""
Test Script for Advanced Therapeutic Response Caching System
Tests Priority 3: Multi-tier caching with intelligent cache warming
"""

import asyncio
import logging
from datetime import datetime
import json

import sys
import os
sys.path.append('/')

from ai_services.core.therapeutic_cache_manager import TherapeuticCacheManager, CacheLevel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TherapeuticCacheTester:
    """Tests the advanced therapeutic caching system"""
    
    def __init__(self):
        self.cache_manager = None
    
    async def initialize(self):
        """Initialize the cache manager"""
        self.cache_manager = TherapeuticCacheManager()
        await self.cache_manager.initialize()
        print("✅ Therapeutic cache manager initialized")
    
    async def test_cache_key_generation(self):
        """Test cache key generation with different parameters"""
        print("\n🔑 Testing Cache Key Generation...")
        
        # Test same query with different contexts
        query1 = "I feel lonely and isolated"
        key1 = self.cache_manager._generate_cache_key(
            query1, 
            care_contexts=["loneliness", "anxiety"]
        )
        
        key2 = self.cache_manager._generate_cache_key(
            query1,
            care_contexts=["anxiety", "loneliness"]  # Different order
        )
        
        print(f"Query: {query1}")
        print(f"Key 1 (loneliness, anxiety): {key1[:16]}...")
        print(f"Key 2 (anxiety, loneliness): {key2[:16]}...")
        print(f"Keys are identical: {key1 == key2}")  # Should be True (sorted)
        
        # Test with user context
        user_context = {"age_group": "seniors-65+", "living_situation": "alone"}
        key3 = self.cache_manager._generate_cache_key(
            query1,
            care_contexts=["loneliness"],
            user_context=user_context
        )
        
        print(f"Key with user context: {key3[:16]}...")
        print(f"Different from base key: {key1 != key3}")  # Should be True
    
    async def test_l1_memory_cache(self):
        """Test L1 in-memory caching"""
        print("\n💾 Testing L1 Memory Cache...")
        
        query = "How can I help someone with grief?"
        care_contexts = ["grief", "loneliness"]
        
        # Test cache miss
        cached_response = await self.cache_manager.get_cached_response(
            query=query,
            care_contexts=care_contexts,
            cache_levels=[CacheLevel.L1_MEMORY]
        )
        
        print(f"Cache miss result: {cached_response is None}")
        
        # Store response
        response_data = {
            "response": "Here are some ways to help with grief...",
            "care_recommendations": ["active_listening", "empathy", "patience"],
            "urgency_level": "routine"
        }
        
        cache_key = await self.cache_manager.set_cached_response(
            query=query,
            response_data=response_data,
            care_contexts=care_contexts,
            ttl_hours=12
        )
        
        print(f"Cached response with key: {cache_key[:8]}...")
        
        # Test cache hit
        cached_response = await self.cache_manager.get_cached_response(
            query=query,
            care_contexts=care_contexts,
            cache_levels=[CacheLevel.L1_MEMORY]
        )
        
        print(f"Cache hit successful: {cached_response is not None}")
        if cached_response:
            print(f"Cached response type: {cached_response['response']['response'][:30]}...")
            print(f"Access count: {cached_response.get('access_count', 0)}")
    
    async def test_multi_tier_caching(self):
        """Test multi-tier cache cascade"""
        print("\n🏗️  Testing Multi-Tier Cache Cascade...")
        
        query = "Senior experiencing caregiver burnout"
        care_contexts = ["caregiver-stress", "anxiety"]
        user_context = {"age_group": "seniors-65+", "care_level": "assisted"}
        
        # Clear L1 cache first
        cache_key = self.cache_manager._generate_cache_key(query, user_context, care_contexts)
        if cache_key in self.cache_manager.l1_cache:
            del self.cache_manager.l1_cache[cache_key]
        
        # Store in all tiers
        response_data = {
            "response": "Caregiver burnout is common among seniors...",
            "interventions": ["respite_care", "support_groups", "stress_management"],
            "urgency_level": "concerning"
        }
        
        await self.cache_manager.set_cached_response(
            query=query,
            response_data=response_data,
            user_context=user_context,
            care_contexts=care_contexts,
            ttl_hours=6
        )
        
        print("✅ Response cached in all tiers")
        
        # Clear L1 to test L2 fallback
        if cache_key in self.cache_manager.l1_cache:
            del self.cache_manager.l1_cache[cache_key]
        
        # Test L2 fallback
        cached_response = await self.cache_manager.get_cached_response(
            query=query,
            user_context=user_context,
            care_contexts=care_contexts,
            cache_levels=[CacheLevel.L1_MEMORY, CacheLevel.L2_MONGODB]
        )
        
        print(f"L2 MongoDB fallback successful: {cached_response is not None}")
        if cached_response:
            print(f"Response promoted back to L1: {cache_key in self.cache_manager.l1_cache}")
    
    async def test_cache_warming(self):
        """Test intelligent cache warming"""
        print("\n🔥 Testing Cache Warming...")
        
        # Define common therapeutic queries for warming
        common_queries = [
            {
                "query": "I feel sad and hopeless",
                "care_contexts": ["grief", "anxiety"]
            },
            {
                "query": "How do I cope with loneliness?",
                "care_contexts": ["loneliness", "general"]
            },
            {
                "query": "My caregiver is stressed",
                "care_contexts": ["caregiver-stress", "health"]
            },
            {
                "query": "I'm worried about my health",
                "care_contexts": ["health", "anxiety"]
            }
        ]
        
        # Warm the cache
        await self.cache_manager.warm_cache(common_queries)
        
        # Test that warmed queries are cached
        warmed_hits = 0
        for query_config in common_queries:
            cached = await self.cache_manager.get_cached_response(
                query=query_config["query"],
                care_contexts=query_config["care_contexts"]
            )
            if cached:
                warmed_hits += 1
        
        print(f"Cache warming success rate: {warmed_hits}/{len(common_queries)}")
    
    async def test_cache_invalidation(self):
        """Test cache invalidation by care context"""
        print("\n🗑️  Testing Cache Invalidation...")
        
        # Cache responses for different care contexts
        test_queries = [
            ("I need help with grief", ["grief"]),
            ("Feeling anxious today", ["anxiety"]),
            ("Caregiver needs support", ["caregiver-stress"])
        ]
        
        cached_keys = []
        for query, contexts in test_queries:
            response_data = {"response": f"Response for {query}"}
            key = await self.cache_manager.set_cached_response(
                query=query,
                response_data=response_data,
                care_contexts=contexts
            )
            cached_keys.append((key, contexts))
        
        print(f"Cached {len(cached_keys)} responses")
        
        # Invalidate grief-related cache entries
        invalidated_count = await self.cache_manager.invalidate_cache(
            care_contexts=["grief"]
        )
        
        print(f"Invalidated {invalidated_count} grief-related entries")
        
        # Check what remains
        remaining = 0
        for key, contexts in cached_keys:
            cached = await self.cache_manager.get_cached_response(
                query="test",  # Won't matter for L1 check
                cache_levels=[CacheLevel.L1_MEMORY]
            )
            if key in self.cache_manager.l1_cache:
                remaining += 1
        
        print(f"Remaining L1 cache entries: {remaining}")
    
    async def test_cache_performance(self):
        """Test cache performance and statistics"""
        print("\n📊 Testing Cache Performance...")
        
        # Generate multiple cache operations
        test_operations = [
            ("How to handle depression?", ["grief", "anxiety"]),
            ("Senior living alone", ["loneliness", "health"]),
            ("Caregiver burnout signs", ["caregiver-stress"]),
            ("Managing chronic pain", ["health", "anxiety"]),
            ("How to handle depression?", ["grief", "anxiety"]),  # Duplicate for hit test
            ("Senior living alone", ["loneliness", "health"])     # Duplicate for hit test
        ]
        
        for query, contexts in test_operations:
            # Try to get (will miss first time)
            cached = await self.cache_manager.get_cached_response(
                query=query,
                care_contexts=contexts
            )
            
            if not cached:
                # Cache a response
                response_data = {"response": f"Generated response for: {query}"}
                await self.cache_manager.set_cached_response(
                    query=query,
                    response_data=response_data,
                    care_contexts=contexts
                )
                
                # Get again (should hit now)
                await self.cache_manager.get_cached_response(
                    query=query,
                    care_contexts=contexts
                )
        
        # Get performance statistics
        stats = self.cache_manager.get_cache_stats()
        
        print("Cache Performance Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    async def run_all_tests(self):
        """Run all therapeutic cache tests"""
        print("🧪 Starting Advanced Therapeutic Cache Tests")
        print("=" * 60)
        
        try:
            await self.initialize()
            
            # Run individual tests
            await self.test_cache_key_generation()
            await self.test_l1_memory_cache()
            await self.test_multi_tier_caching()
            await self.test_cache_warming()
            await self.test_cache_invalidation()
            await self.test_cache_performance()
            
            print("\n✅ All therapeutic cache tests completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.cache_manager:
                await self.cache_manager.cleanup()
                print("✅ Cache manager cleanup completed")

async def main():
    """Run therapeutic cache tests"""
    tester = TherapeuticCacheTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())