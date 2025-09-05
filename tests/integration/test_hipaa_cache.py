"""
HIPAA-Compliant Cache Integration Tests
======================================

Consolidated integration tests for HIPAA-compliant caching functionality
including PHI detection, encryption, and semantic clustering.
"""

import pytest
import asyncio
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from app.services.therapeutic_cache_manager import TherapeuticCacheManager, CacheLevel
    from services.content_safety_service.phi_analyzer import PHIAnalyzer
    from services.content_safety_service.healthcare_encryption import HealthcareEncryptionService
    from services.content_safety_service.semantic_clustering import TherapeuticSemanticClustering
    HIPAA_SERVICES_AVAILABLE = True
except ImportError as e:
    HIPAA_SERVICES_AVAILABLE = False
    print(f"HIPAA services not available: {e}")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session") 
async def cache_manager():
    """Create a cache manager instance for testing"""
    if not HIPAA_SERVICES_AVAILABLE:
        pytest.skip("HIPAA services not available")
    
    manager = TherapeuticCacheManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()


@pytest.fixture(scope="session")
async def phi_analyzer():
    """Create PHI analyzer for testing"""
    if not HIPAA_SERVICES_AVAILABLE:
        pytest.skip("HIPAA services not available")
    
    analyzer = PHIAnalyzer()
    await analyzer.initialize()
    yield analyzer
    await analyzer.cleanup()


@pytest.fixture(scope="session") 
async def encryption_service():
    """Create encryption service for testing"""
    if not HIPAA_SERVICES_AVAILABLE:
        pytest.skip("HIPAA services not available")
    
    service = HealthcareEncryptionService()
    yield service


@pytest.mark.hipaa
@pytest.mark.integration
@pytest.mark.asyncio
class TestHIPAACacheIntegration:
    """HIPAA-compliant cache integration tests"""
    
    async def test_phi_detection_and_encryption(self, cache_manager, phi_analyzer, encryption_service):
        """Test PHI detection and encryption in cache"""
        
        # Test data with PHI
        test_data = {
            "user_message": "My name is John Doe and my SSN is 123-45-6789",
            "ai_response": "Hello John, I understand you have concerns about your medical condition.",
            "session_id": "test_session_123",
            "timestamp": datetime.now().isoformat()
        }
        
        # Analyze for PHI
        phi_results = await phi_analyzer.analyze_text(test_data["user_message"])
        
        assert phi_results["has_phi"] == True
        assert "SSN" in [entity["type"] for entity in phi_results["entities"]]
        assert "PERSON" in [entity["type"] for entity in phi_results["entities"]]
        
        # Cache with encryption
        cache_key = "test_phi_cache"
        await cache_manager.set(
            cache_key, 
            test_data,
            cache_level=CacheLevel.ENCRYPTED,
            phi_detected=True
        )
        
        # Retrieve and verify encryption
        cached_data = await cache_manager.get(cache_key)
        
        # Verify data was properly cached and decrypted
        assert cached_data is not None
        assert cached_data["session_id"] == test_data["session_id"]
        
        # Verify PHI was handled appropriately (should be encrypted in storage)
        raw_cached = await cache_manager._get_raw_cached_data(cache_key)
        assert raw_cached != test_data  # Should be different due to encryption
    
    async def test_semantic_clustering_integration(self, cache_manager):
        """Test semantic clustering integration with cache"""
        
        # Test queries with similar semantic meaning
        queries = [
            "What are the symptoms of diabetes?",
            "Can you tell me about diabetic symptoms?", 
            "How do I know if I have diabetes symptoms?",
            "What are signs of high blood sugar?"
        ]
        
        responses = [
            "Diabetes symptoms include increased thirst, frequent urination, and fatigue.",
            "Common diabetic symptoms are excessive thirst, urination, and tiredness.",
            "Signs of diabetes include polydipsia, polyuria, and weakness.",
            "High blood sugar signs include thirst, frequent bathroom visits, and exhaustion."
        ]
        
        # Cache all query-response pairs
        for i, (query, response) in enumerate(zip(queries, responses)):
            cache_key = f"semantic_test_{i}"
            cache_data = {
                "query": query,
                "response": response,
                "similarity_vector": [0.1 * j for j in range(10)]  # Mock vector
            }
            
            await cache_manager.set(
                cache_key,
                cache_data, 
                cache_level=CacheLevel.SEMANTIC_CLUSTER
            )
        
        # Test semantic retrieval - should find similar queries
        similar_query = "What are diabetes warning signs?"
        similar_results = await cache_manager.find_semantically_similar(
            similar_query,
            similarity_threshold=0.7,
            max_results=3
        )
        
        assert len(similar_results) >= 2  # Should find at least 2 similar
        
        # Verify results contain relevant responses
        result_texts = [r["response"] for r in similar_results]
        assert any("diabetes" in text.lower() for text in result_texts)
    
    async def test_cache_level_hierarchy(self, cache_manager):
        """Test different cache levels work properly"""
        
        test_data = {"message": "Test data for cache levels"}
        
        # Test different cache levels
        levels_to_test = [
            CacheLevel.MEMORY_ONLY,
            CacheLevel.REDIS_STANDARD, 
            CacheLevel.ENCRYPTED,
            CacheLevel.SEMANTIC_CLUSTER
        ]
        
        for level in levels_to_test:
            cache_key = f"level_test_{level.value}"
            
            # Set data at specific cache level
            await cache_manager.set(
                cache_key,
                test_data,
                cache_level=level
            )
            
            # Retrieve and verify
            cached_data = await cache_manager.get(cache_key)
            assert cached_data is not None
            assert cached_data["message"] == test_data["message"]
            
            # Verify cache level metadata
            metadata = await cache_manager.get_cache_metadata(cache_key)
            assert metadata["cache_level"] == level.value
    
    async def test_audit_logging_integration(self, cache_manager):
        """Test that cache operations generate proper audit logs"""
        
        test_data = {
            "query": "Sensitive medical query about patient condition",
            "response": "Medical advice response",
            "user_id": "test_user_123", 
            "session_id": "audit_test_session"
        }
        
        cache_key = "audit_test_cache"
        
        # Perform cache operations that should be audited
        await cache_manager.set(
            cache_key,
            test_data,
            cache_level=CacheLevel.ENCRYPTED,
            audit_metadata={
                "operation": "cache_set",
                "user_id": test_data["user_id"],
                "session_id": test_data["session_id"],
                "contains_phi": True
            }
        )
        
        # Retrieve data (should also be audited)
        retrieved_data = await cache_manager.get(
            cache_key,
            audit_metadata={
                "operation": "cache_get", 
                "user_id": test_data["user_id"],
                "session_id": test_data["session_id"]
            }
        )
        
        assert retrieved_data is not None
        
        # Verify audit logs were created
        audit_logs = await cache_manager.get_audit_logs(
            session_id=test_data["session_id"]
        )
        
        assert len(audit_logs) >= 2  # Should have logs for set and get operations
        
        # Verify audit log content
        log_operations = [log["operation"] for log in audit_logs]
        assert "cache_set" in log_operations
        assert "cache_get" in log_operations
    
    async def test_cache_performance_metrics(self, cache_manager):
        """Test cache performance monitoring and metrics"""
        
        # Generate test load
        num_operations = 50
        test_data = {"test": "performance data"}
        
        # Perform multiple cache operations
        for i in range(num_operations):
            cache_key = f"perf_test_{i}"
            await cache_manager.set(cache_key, test_data)
            await cache_manager.get(cache_key)
        
        # Get performance metrics
        metrics = await cache_manager.get_performance_metrics()
        
        assert metrics is not None
        assert "total_operations" in metrics
        assert metrics["total_operations"] >= num_operations * 2  # set + get
        
        assert "cache_hit_rate" in metrics
        assert "average_response_time" in metrics
        assert "memory_usage" in metrics
        
        # Verify metrics are reasonable
        assert 0 <= metrics["cache_hit_rate"] <= 1
        assert metrics["average_response_time"] > 0


@pytest.mark.hipaa 
@pytest.mark.integration
@pytest.mark.asyncio 
async def test_end_to_end_hipaa_workflow():
    """Test complete end-to-end HIPAA workflow"""
    
    if not HIPAA_SERVICES_AVAILABLE:
        pytest.skip("HIPAA services not available")
    
    # Initialize all services
    cache_manager = TherapeuticCacheManager()
    phi_analyzer = PHIAnalyzer()
    encryption_service = HealthcareEncryptionService()
    
    await cache_manager.initialize()
    await phi_analyzer.initialize()
    
    try:
        # Simulate a complete therapeutic conversation with PHI
        conversation_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "Hi, I'm Mary Smith. I've been having chest pain and shortness of breath. My DOB is 01/15/1975.",
                    "timestamp": datetime.now().isoformat()
                },
                {
                    "role": "assistant", 
                    "content": "Hello Mary. I understand you're experiencing chest pain and shortness of breath. These can be concerning symptoms. Can you describe when these symptoms occur?",
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "user_id": "test_user_mary",
            "session_id": "e2e_test_session"
        }
        
        # Step 1: Analyze for PHI
        user_message = conversation_data["messages"][0]["content"]
        phi_analysis = await phi_analyzer.analyze_text(user_message)
        
        assert phi_analysis["has_phi"] == True
        
        # Step 2: Cache conversation with appropriate security
        cache_key = f"conversation_{conversation_data['session_id']}"
        await cache_manager.set(
            cache_key,
            conversation_data,
            cache_level=CacheLevel.ENCRYPTED,
            phi_detected=phi_analysis["has_phi"],
            audit_metadata={
                "user_id": conversation_data["user_id"],
                "session_id": conversation_data["session_id"],
                "phi_entities": len(phi_analysis["entities"])
            }
        )
        
        # Step 3: Retrieve conversation data
        retrieved_conversation = await cache_manager.get(cache_key)
        
        assert retrieved_conversation is not None
        assert retrieved_conversation["user_id"] == conversation_data["user_id"]
        assert len(retrieved_conversation["messages"]) == 2
        
        # Step 4: Verify audit trail was created
        audit_logs = await cache_manager.get_audit_logs(
            session_id=conversation_data["session_id"]
        )
        
        assert len(audit_logs) >= 1
        assert audit_logs[0]["session_id"] == conversation_data["session_id"]
        
        # Step 5: Test conversation continuation (semantic similarity)
        follow_up_query = "The chest pain is getting worse, especially when I exercise"
        similar_conversations = await cache_manager.find_semantically_similar(
            follow_up_query,
            user_id=conversation_data["user_id"],
            similarity_threshold=0.6
        )
        
        # Should find the previous conversation about chest pain
        assert len(similar_conversations) >= 1
        
    finally:
        # Cleanup
        await cache_manager.cleanup()
        await phi_analyzer.cleanup()


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v"])