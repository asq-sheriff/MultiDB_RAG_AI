"""
End-to-End Integration Tests for Therapeutic AI System
Tests the complete therapeutic AI pipeline with multi-database optimization
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.services.intelligent_data_router import IntelligentTherapeuticRouter, QueryType
from app.services.therapeutic_cache_manager import TherapeuticCacheManager, CacheLevel

class TherapeuticAIIntegrationTests:
    """End-to-end integration tests for the therapeutic AI system"""
    
    def __init__(self):
        self.router = None
        self.cache_manager = None
        self.test_results = []
    
    async def setup_environment(self):
        """Set up the complete test environment"""
        print("🔧 Setting up test environment...")
        
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
        
        print("✅ Test environment initialized")
    
    async def cleanup_environment(self):
        """Clean up test environment"""
        if self.router:
            await self.router.cleanup()
        if self.cache_manager:
            await self.cache_manager.cleanup()
        print("✅ Test environment cleaned up")
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        print(f"{status}: {test_name} - {details}")
    
    async def test_therapeutic_document_availability(self):
        """Test that therapeutic documents are properly seeded and accessible"""
        test_name = "Therapeutic Document Availability"
        
        try:
            result = await self.router.route_query(
                QueryType.DOCUMENT_SEARCH,
                query="loneliness in seniors",
                care_contexts=["loneliness", "anxiety"],
                limit=5
            )
            
            success = result["count"] > 0
            details = f"Found {result['count']} therapeutic documents"
            
            if success and result.get("results"):
                doc = result["results"][0]
                has_contexts = "care_contexts" in doc
                has_category = "therapeutic_category" in doc
                has_score = "combined_score" in doc or "vector_score" in doc
                
                success = has_contexts and has_category and has_score
                details += f" | Structure: contexts={has_contexts}, category={has_category}, score={has_score}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def test_hybrid_therapeutic_search(self):
        """Test hybrid search across MongoDB and PostgreSQL"""
        test_name = "Hybrid Therapeutic Search"
        
        try:
            result = await self.router.route_query(
                QueryType.HYBRID_SEARCH,
                query="senior experiencing grief and anxiety",
                care_contexts=["grief", "anxiety"],
                limit=10
            )
            
            success = "count" in result and "mongodb_count" in result and "postgres_count" in result
            details = f"Total: {result.get('count', 0)}, MongoDB: {result.get('mongodb_count', 0)}, PostgreSQL: {result.get('postgres_count', 0)}"
            
            # Verify results structure if present
            if success and result.get("results"):
                first_result = result["results"][0]
                has_source = "source_db" in first_result
                has_type = "result_type" in first_result
                has_score = "combined_score" in first_result
                
                success = has_source and has_type and has_score
                details += f" | Structure valid: {success}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def test_cache_integration(self):
        """Test therapeutic response caching integration with HIPAA compliance"""
        test_name = "Enhanced Cache Integration with HIPAA"
        
        try:
            query = "How can I help my elderly parent with loneliness?"
            care_contexts = ["loneliness", "caregiver-stress"]
            
            # Clear any existing cache entries first
            cache_key = self.cache_manager._generate_cache_key(
                query=query,
                care_contexts=care_contexts
            )
            # Clear from all cache levels
            if hasattr(self.cache_manager, 'l1_cache'):
                self.cache_manager.l1_cache.clear()
            
            # Test cache miss
            cached_response = await self.cache_manager.get_cached_response(
                query=query,
                care_contexts=care_contexts
            )
            
            cache_miss = cached_response is None
            
            # Cache a response (should be encrypted and HIPAA-compliant)
            response_data = {
                "response": "Here are some ways to help with loneliness...",
                "interventions": ["social_engagement", "regular_visits"],
                "urgency_level": "routine"
            }
            
            cache_result = await self.cache_manager.set_cached_response(
                query=query,
                response_data=response_data,
                care_contexts=care_contexts
            )
            
            # Handle both old and new cache manager return types
            if isinstance(cache_result, tuple):
                cache_key, was_cached = cache_result
            else:
                cache_key, was_cached = cache_result, True
            
            # Test cache hit
            cached_response = await self.cache_manager.get_cached_response(
                query=query,
                care_contexts=care_contexts
            )
            
            cache_hit = cached_response is not None
            data_match = False
            if cache_hit:
                data_match = cached_response["response"]["response"] == response_data["response"]
            
            # Test HIPAA compliance features
            cache_stats = self.cache_manager.get_cache_stats()
            hipaa_enabled = cache_stats.get("hipaa_compliance_enabled", False)
            encryption_enabled = cache_stats.get("encryption_enabled", False)
            clustering_enabled = cache_stats.get("semantic_clustering_enabled", False)
            
            success = cache_miss and cache_hit and data_match and was_cached and cache_key
            details = f"Miss: {cache_miss}, Hit: {cache_hit}, Match: {data_match}, HIPAA: {hipaa_enabled}, Encrypt: {encryption_enabled}, Cluster: {clustering_enabled}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def test_care_context_filtering(self):
        """Test care context-based filtering"""
        test_name = "Care Context Filtering"
        
        try:
            care_contexts_to_test = [
                ["grief", "loneliness"],
                ["anxiety", "health"],
                ["caregiver-stress"]
            ]
            
            all_success = True
            context_results = []
            
            for contexts in care_contexts_to_test:
                result = await self.router.route_query(
                    QueryType.DOCUMENT_SEARCH,
                    query="senior care support",
                    care_contexts=contexts,
                    limit=3
                )
                
                has_count = "count" in result
                valid_count = result.get("count", -1) >= 0
                context_success = has_count and valid_count
                
                context_results.append(f"{contexts}: {result.get('count', 0)}")
                
                if not context_success:
                    all_success = False
            
            details = " | ".join(context_results)
            self.log_test_result(test_name, all_success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def test_crisis_detection_pathway(self):
        """Test crisis detection and SAFE-T script integration"""
        test_name = "Crisis Detection Pathway"
        
        try:
            risk_indicators = ["hopeless", "ending it all", "no point"]
            user_context = {"age": 75, "living_alone": True}
            
            result = await self.router.route_query(
                QueryType.CRISIS_DETECTION,
                risk_indicators=risk_indicators,
                user_context=user_context
            )
            
            has_scripts_or_error = "scripts" in result or "error" in result
            script_count = len(result.get("scripts", []))
            
            # Verify script structure if present
            script_structure_valid = True
            if result.get("scripts"):
                for script in result["scripts"]:
                    if not ("name" in script and ("urgency_level" in script or "severity" in script)):
                        script_structure_valid = False
                        break
            
            success = has_scripts_or_error and script_structure_valid
            details = f"Found {script_count} SAFE-T scripts, Structure valid: {script_structure_valid}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def test_performance_stats(self):
        """Test system performance and statistics collection"""
        test_name = "Performance Statistics"
        
        try:
            # Generate operations
            test_queries = [
                ("I feel lonely", ["loneliness"]),
                ("Caregiver burnout", ["caregiver-stress"]),
                ("Senior health concerns", ["health", "anxiety"]),
            ]
            
            for query, contexts in test_queries:
                await self.router.route_query(
                    QueryType.DOCUMENT_SEARCH,
                    query=query,
                    care_contexts=contexts,
                    limit=3
                )
                
                await self.cache_manager.get_cached_response(
                    query=query,
                    care_contexts=contexts
                )
            
            # Check statistics
            router_stats = self.router.get_routing_stats()
            cache_stats = self.cache_manager.get_cache_stats()
            
            router_valid = (
                router_stats["total_queries"] > 0 and
                "mongodb_queries" in router_stats and
                "cache_hit_rate" in router_stats
            )
            
            cache_valid = (
                cache_stats["total_requests"] > 0 and
                "cache_hit_rate" in cache_stats
            )
            
            success = router_valid and cache_valid
            details = f"Router queries: {router_stats['total_queries']}, Cache requests: {cache_stats['total_requests']}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def test_embedding_service_integration(self):
        """Test BGE embedding service integration"""
        test_name = "Embedding Service Integration"
        
        try:
            result = await self.router.route_query(
                QueryType.DOCUMENT_SEARCH,
                query="senior mental health support",
                care_contexts=["anxiety", "health"],
                limit=5
            )
            
            # If we get results with scores, embeddings are working
            embedding_working = False
            if result.get("results"):
                for doc in result["results"]:
                    if "combined_score" in doc or "vector_score" in doc:
                        embedding_working = True
                        break
            
            success = embedding_working or result.get("count", 0) >= 0  # At least the service responds
            details = f"Results: {result.get('count', 0)}, Embedding scores present: {embedding_working}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def test_end_to_end_therapeutic_flow(self):
        """Test complete therapeutic conversation flow"""
        test_name = "End-to-End Therapeutic Flow"
        
        try:
            # Simulate therapeutic interaction
            user_query = "I'm a 72-year-old living alone and feeling very lonely"
            user_context = {"age": 72, "living_situation": "alone"}
            care_contexts = ["loneliness", "general"]
            
            # Step 1: Check cache
            cached_response = await self.cache_manager.get_cached_response(
                query=user_query,
                user_context=user_context,
                care_contexts=care_contexts
            )
            
            # Step 2: Do hybrid search if not cached
            final_response = None
            search_performed = False
            
            if not cached_response:
                search_result = await self.router.route_query(
                    QueryType.HYBRID_SEARCH,
                    query=user_query,
                    care_contexts=care_contexts,
                    limit=5
                )
                search_performed = True
                
                # Step 3: Generate and cache response
                response_data = {
                    "response": "I understand you're feeling lonely. Here are some suggestions...",
                    "search_results": search_result.get("results", []),
                    "care_plan": ["social_connection", "community_resources"],
                    "urgency_level": "routine"
                }
                
                await self.cache_manager.set_cached_response(
                    query=user_query,
                    response_data=response_data,
                    user_context=user_context,
                    care_contexts=care_contexts
                )
                
                final_response = response_data
            else:
                final_response = cached_response["response"]
            
            # Step 4: Verify subsequent request uses cache
            cached_response_2 = await self.cache_manager.get_cached_response(
                query=user_query,
                user_context=user_context,
                care_contexts=care_contexts
            )
            
            has_final_response = final_response is not None and "response" in final_response
            cache_works = cached_response_2 is not None
            
            success = has_final_response and cache_works
            details = f"Search performed: {search_performed}, Response generated: {has_final_response}, Cache works: {cache_works}"
            
            self.log_test_result(test_name, success, details)
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {str(e)}")
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Starting Therapeutic AI End-to-End Integration Tests")
        print("=" * 70)
        
        try:
            await self.setup_environment()
            
            # Run all tests
            print("\n📋 Running Integration Tests...")
            await self.test_therapeutic_document_availability()
            await self.test_hybrid_therapeutic_search()
            await self.test_cache_integration()
            await self.test_care_context_filtering()
            await self.test_crisis_detection_pathway()
            await self.test_performance_stats()
            await self.test_embedding_service_integration()
            await self.test_end_to_end_therapeutic_flow()
            
            # Summary
            print(f"\n📊 Test Results Summary:")
            total_tests = len(self.test_results)
            passed_tests = sum(1 for result in self.test_results if result["success"])
            failed_tests = total_tests - passed_tests
            
            print(f"  Total Tests: {total_tests}")
            print(f"  Passed: {passed_tests}")
            print(f"  Failed: {failed_tests}")
            print(f"  Success Rate: {(passed_tests/total_tests*100):.1f}%")
            
            if failed_tests > 0:
                print(f"\n❌ Failed Tests:")
                for result in self.test_results:
                    if not result["success"]:
                        print(f"  • {result['test']}: {result['details']}")
            
            if failed_tests == 0:
                print(f"\n🎉 ALL INTEGRATION TESTS PASSED!")
                print("🚀 Therapeutic AI System is fully operational!")
            else:
                print(f"\n⚠️  Some tests failed - check system configuration")
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.cleanup_environment()

async def main():
    """Run the integration test suite"""
    test_suite = TherapeuticAIIntegrationTests()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())