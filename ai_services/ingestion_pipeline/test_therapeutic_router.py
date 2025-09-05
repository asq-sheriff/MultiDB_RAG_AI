"""
Test Script for Intelligent Therapeutic Data Router
Tests Priority 2: Multi-database query routing and hybrid search
"""

import asyncio
import logging
from typing import Dict, Any
import json

from ..services.intelligent_data_router import (
    IntelligentTherapeuticRouter,
    QueryType,
    TherapeuticContext
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TherapeuticRouterTester:
    """Tests the intelligent therapeutic data router functionality"""
    
    def __init__(self):
        self.router = None
    
    async def initialize(self):
        """Initialize the therapeutic router"""
        self.router = IntelligentTherapeuticRouter()
        await self.router.initialize()
        print("✅ Therapeutic router initialized")
    
    async def test_mongodb_therapeutic_search(self):
        """Test MongoDB therapeutic document search"""
        print("\n🧠 Testing MongoDB Therapeutic Search...")
        
        query = "I feel lonely and isolated"
        care_contexts = ["loneliness", "anxiety"]
        
        result = await self.router.route_query(
            QueryType.DOCUMENT_SEARCH,
            query=query,
            care_contexts=care_contexts,
            limit=5
        )
        
        print(f"Query: {query}")
        print(f"Care contexts: {care_contexts}")
        print(f"Results: {result.get('count', 0)} therapeutic documents found")
        
        if result.get('results'):
            for i, doc in enumerate(result['results'][:2]):
                print(f"  {i+1}. {doc.get('title', 'Untitled')}")
                print(f"     Care contexts: {doc.get('care_contexts', [])}")
                print(f"     Score: {doc.get('combined_score', 0):.3f}")
        
        return result
    
    async def test_postgres_knowledge_search(self):
        """Test PostgreSQL knowledge card search"""
        print("\n🎯 Testing PostgreSQL Knowledge Search...")
        
        query = "How to help someone with grief"
        
        result = await self.router.route_query(
            QueryType.KNOWLEDGE_SEARCH,
            query=query,
            limit=3
        )
        
        print(f"Query: {query}")
        print(f"Results: {result.get('count', 0)} knowledge cards found")
        
        if result.get('results'):
            for i, card in enumerate(result['results']):
                print(f"  {i+1}. {card.get('topic', 'Untitled')}")
                print(f"     Do list: {len(card.get('do_list', []))} items")
                print(f"     Don't list: {len(card.get('dont_list', []))} items")
                print(f"     Similarity: {card.get('similarity', 0):.3f}")
        
        return result
    
    async def test_hybrid_therapeutic_search(self):
        """Test hybrid search across MongoDB and PostgreSQL"""
        print("\n🔗 Testing Hybrid Therapeutic Search...")
        
        query = "Senior experiencing caregiver stress and anxiety"
        care_contexts = ["caregiver-stress", "anxiety"]
        
        result = await self.router.route_query(
            QueryType.HYBRID_SEARCH,
            query=query,
            care_contexts=care_contexts,
            limit=10
        )
        
        print(f"Query: {query}")
        print(f"Care contexts: {care_contexts}")
        print(f"Total results: {result.get('count', 0)}")
        print(f"MongoDB results: {result.get('mongodb_count', 0)}")
        print(f"PostgreSQL results: {result.get('postgres_count', 0)}")
        
        if result.get('results'):
            print("\nTop hybrid results:")
            for i, item in enumerate(result['results'][:3]):
                print(f"  {i+1}. [{item.get('source_db', 'unknown')}] {item.get('title', item.get('topic', 'Untitled'))}")
                print(f"     Type: {item.get('result_type', 'unknown')}")
                print(f"     Score: {item.get('combined_score', 0):.3f}")
        
        return result
    
    async def test_postgres_crisis_lookup(self):
        """Test PostgreSQL crisis detection and SAFE-T script lookup"""
        print("\n🚨 Testing Crisis Detection and SAFE-T Lookup...")
        
        risk_indicators = ["suicide", "hopeless", "ending it all"]
        user_context = {"age": 72, "living_alone": True}
        
        result = await self.router.route_query(
            QueryType.CRISIS_DETECTION,
            risk_indicators=risk_indicators,
            user_context=user_context
        )
        
        print(f"Risk indicators: {risk_indicators}")
        print(f"User context: {user_context}")
        print(f"SAFE-T scripts found: {result.get('count', 0)}")
        
        if result.get('scripts'):
            for i, script in enumerate(result['scripts']):
                print(f"  {i+1}. {script.get('name', 'Unnamed script')}")
                print(f"     Urgency: {script.get('urgency_level', 'unknown')}")
                print(f"     Risk level: {script.get('risk_level', 'unknown')}")
        
        return result
    
    async def test_postgres_persona_lookup(self):
        """Test PostgreSQL persona configuration lookup"""
        print("\n👤 Testing Persona Configuration Lookup...")
        
        persona_key = "senior-care-therapist"
        
        result = await self.router.route_query(
            QueryType.PERSONA_LOOKUP,
            persona_key=persona_key
        )
        
        print(f"Persona key: {persona_key}")
        
        if result.get('persona'):
            persona = result['persona']
            print(f"Persona found: {persona.get('display_name', 'Unknown')}")
            print(f"Version: {persona.get('version_number', 'Unknown')}")
            print(f"Prompt blocks: {len(persona.get('prompt_blocks', []))}")
            print(f"Style parameters: {len(persona.get('style_parameters', {}))}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        return result
    
    async def test_routing_performance(self):
        """Test routing performance and statistics"""
        print("\n📊 Testing Routing Performance...")
        
        # Run multiple queries to test performance
        test_queries = [
            ("loneliness in seniors", ["loneliness"]),
            ("grief support", ["grief"]),
            ("caregiver burnout", ["caregiver-stress"]),
            ("anxiety management", ["anxiety"]),
            ("health concerns", ["health"])
        ]
        
        for query, contexts in test_queries:
            await self.router.route_query(
                QueryType.HYBRID_SEARCH,
                query=query,
                care_contexts=contexts,
                limit=5
            )
        
        stats = self.router.get_routing_stats()
        print(f"Total queries processed: {stats['total_queries']}")
        print(f"MongoDB queries: {stats['mongodb_queries']}")
        print(f"PostgreSQL queries: {stats['postgres_queries']}")
        print(f"Hybrid queries: {stats['hybrid_queries']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
        print(f"Hybrid query rate: {stats['hybrid_query_rate']:.2%}")
        
        return stats
    
    async def run_all_tests(self):
        """Run all therapeutic router tests"""
        print("🧪 Starting Therapeutic Data Router Tests")
        print("=" * 60)
        
        try:
            await self.initialize()
            
            # Test individual database searches
            await self.test_mongodb_therapeutic_search()
            await self.test_postgres_knowledge_search()
            
            # Test hybrid search
            await self.test_hybrid_therapeutic_search()
            
            # Test specialized lookups
            await self.test_postgres_crisis_lookup()
            await self.test_postgres_persona_lookup()
            
            # Test performance
            await self.test_routing_performance()
            
            print("\n✅ All therapeutic router tests completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise
        finally:
            if self.router:
                await self.router.cleanup()
                print("✅ Router cleanup completed")

async def main():
    """Run therapeutic router tests"""
    tester = TherapeuticRouterTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())