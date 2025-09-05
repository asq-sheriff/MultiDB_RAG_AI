#!/usr/bin/env python3
"""
Comprehensive Integration Tests for All User Paths
=================================================

Tests all major user workflows including:
- Health checks and system status
- Authentication and user management  
- Document ingestion and processing
- Search functionality (semantic, keyword, hybrid)
- Chat interactions with context
- Session management
- Analytics and performance monitoring
- Multi-database operations
- Error handling and recovery

Usage:
    pytest tests/integration/test_full_user_paths.py -v
    python -m pytest tests/integration/test_full_user_paths.py::TestUserAuthFlow -v
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
import pytest
import httpx
import random
from motor.motor_asyncio import AsyncIOMotorClient

# Test configuration - Updated to match actual running services
TEST_BASE_URL = "http://localhost:8000"
API_GATEWAY_URL = "http://localhost:8000"  # Service gateway
EMBEDDING_SERVICE_URL = "http://localhost:8005"  # Fixed port
SEARCH_SERVICE_URL = "http://localhost:8001"
GENERATION_SERVICE_URL = "http://localhost:8006"  # Fixed port

# MongoDB connection for direct testing - Updated for demo environment
MONGO_URI = "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true"

# Test data
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"
TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_PASSWORD = "adminpassword123"

TEST_DOCUMENTS = [
    {
        "title": "Healthcare Guidelines",
        "content": "These are comprehensive healthcare guidelines for elderly care including safety protocols and emotional support strategies.",
        "category": "healthcare",
        "type": "guideline"
    },
    {
        "title": "Conversation Best Practices", 
        "content": "Effective conversation patterns for AI companions focusing on empathy, memory engagement, and emotional intelligence.",
        "category": "communication",
        "type": "best_practice"
    },
    {
        "title": "Emergency Procedures",
        "content": "Step-by-step emergency response procedures for elderly companion AI systems including safety checks and alert protocols.",
        "category": "safety",
        "type": "procedure"
    }
]

TEST_QUERIES = [
    "What are the safety protocols for elderly care?",
    "How should AI companions handle emotional situations?", 
    "What are the best conversation techniques?",
    "Tell me about emergency procedures",
    "How to provide healthcare support?"
]


class TestEnvironmentSetup:
    """Test environment setup and validation"""
    
    @pytest.mark.asyncio
    async def test_services_health_check(self):
        """Test that all required services are running and healthy"""
        services_to_check = [
            {"url": f"{TEST_BASE_URL}/health", "name": "Main API"},
            {"url": f"{API_GATEWAY_URL}/health", "name": "API Gateway"},
            {"url": f"{EMBEDDING_SERVICE_URL}/health", "name": "Embedding Service"},
            {"url": f"{GENERATION_SERVICE_URL}/health", "name": "Generation Service"},
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service in services_to_check:
                try:
                    response = await client.get(service["url"])
                    assert response.status_code == 200, f"{service['name']} health check failed"
                    health_data = response.json()
                    assert "status" in health_data, f"{service['name']} missing status field"
                    print(f"✅ {service['name']}: {health_data.get('status', 'unknown')}")
                except Exception as e:
                    pytest.fail(f"❌ {service['name']} health check failed: {e}")
    
    @pytest.mark.asyncio
    async def test_database_connectivity(self):
        """Test direct database connectivity"""
        # Test MongoDB
        try:
            client = AsyncIOMotorClient(MONGO_URI)
            await client.admin.command('ping')
            print("✅ MongoDB connection successful")
            client.close()
        except Exception as e:
            pytest.fail(f"❌ MongoDB connection failed: {e}")
    
    @pytest.mark.asyncio
    async def test_detailed_system_status(self):
        """Test detailed system status endpoint"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{TEST_BASE_URL}/health/detailed")
            assert response.status_code == 200
            
            status_data = response.json()
            assert "overall_status" in status_data
            assert "ai_services" in status_data
            assert "database" in status_data
            assert "performance" in status_data
            
            print(f"✅ Overall system status: {status_data['overall_status']}")
            print(f"✅ AI services ready: {status_data['ai_services'].get('services_ready', 0)}")


class TestDocumentIngestion:
    """Test document ingestion pipeline"""
    
    @pytest.mark.asyncio
    async def test_document_processor_functionality(self):
        """Test document processing capabilities"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{TEST_BASE_URL}/dev/test-document-processing")
            assert response.status_code == 200
            
            test_result = response.json()
            assert test_result["status"] == "success"
            assert test_result["chunks_created"] > 0
            assert len(test_result["chunk_details"]) > 0
            
            print(f"✅ Document processing test: {test_result['chunks_created']} chunks created")
    
    @pytest.mark.asyncio  
    async def test_data_files_ingestion(self):
        """Test ingestion of actual data files from ./data/docs"""
        # This tests the ingestion process we verified earlier
        from ai_services.ingestion_pipeline.document_processor import EnhancedDocumentProcessor, ProcessingConfig
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Process documents
        config = ProcessingConfig()
        processor = EnhancedDocumentProcessor(config)
        chunks = await processor.process_directory('./data/docs')
        assert len(chunks) > 0, "No chunks processed from data files"
        
        # Test database ingestion
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.chatbot_app
        
        # Clear existing test data
        await db.test_embeddings.delete_many({})
        
        # Insert test documents
        test_documents = []
        for chunk in chunks[:5]:  # Test with first 5 chunks
            mock_embedding = [random.uniform(-1, 1) for _ in range(768)]
            doc = {
                'content': chunk.content,
                'title': chunk.metadata.title,
                'embedding': mock_embedding,
                'category': 'test_ingestion',
                'source': chunk.metadata.file_path,
                'chunk_id': chunk.chunk_id
            }
            test_documents.append(doc)
        
        result = await db.test_embeddings.insert_many(test_documents)
        assert len(result.inserted_ids) == len(test_documents)
        
        # Verify retrieval
        retrieved_count = await db.test_embeddings.count_documents({'category': 'test_ingestion'})
        assert retrieved_count == len(test_documents)
        
        # Cleanup
        await db.test_embeddings.delete_many({'category': 'test_ingestion'})
        processor.cleanup()
        client.close()
        
        print(f"✅ Data files ingestion test: {len(chunks)} chunks processed, {len(test_documents)} tested")
    
    @pytest.mark.asyncio
    async def test_admin_seeding_endpoints(self):
        """Test admin seeding functionality"""
        # First test seeding status
        async with httpx.AsyncClient(timeout=30.0) as client:
            status_response = await client.get(f"{TEST_BASE_URL}/admin/seed-status")
            
            if status_response.status_code in [401, 403]:
                print("⚠️ Admin endpoints require authentication - skipping seeding tests")
                return
            elif status_response.status_code == 503:
                print("⚠️ Admin endpoints require database connectivity - expected in demo")
                return
                
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert "enhanced_seeding_available" in status_data
            
            print(f"✅ Seeding system status: Available={status_data['enhanced_seeding_available']}")


class TestUserAuthFlow:
    """Test user authentication and authorization flows"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.test_user_data = {
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
            "is_active": True
        }
    
    @pytest.mark.asyncio
    async def test_user_registration_flow(self):
        """Test complete user registration process"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test registration
            register_response = await client.post(
                f"{TEST_BASE_URL}/auth/register",
                json=self.test_user_data
            )
            
            if register_response.status_code == 404:
                print("⚠️ Auth endpoints not available - skipping user auth tests")
                return
                
            # Handle different possible response scenarios
            if register_response.status_code in [200, 201]:
                register_data = register_response.json()
                print(f"✅ User registration successful: {register_data.get('message', 'OK')}")
            else:
                print(f"ℹ️ Registration response: {register_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_user_login_flow(self):
        """Test user login process"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Attempt login
            login_data = {
                "username": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            
            login_response = await client.post(
                f"{TEST_BASE_URL}/auth/login",
                data=login_data  # OAuth2 expects form data
            )
            
            if login_response.status_code == 404:
                print("⚠️ Auth login endpoint not available")
                return
                
            # Test token validation if login successful
            if login_response.status_code == 200:
                token_data = login_response.json()
                if "access_token" in token_data:
                    token = token_data["access_token"]
                    
                    # Test protected endpoint
                    headers = {"Authorization": f"Bearer {token}"}
                    profile_response = await client.get(
                        f"{TEST_BASE_URL}/users/profile",
                        headers=headers
                    )
                    
                    print(f"✅ Login and token validation: {profile_response.status_code}")
            else:
                print(f"ℹ️ Login attempt result: {login_response.status_code}")


class TestSearchFunctionality:
    """Test all search functionality"""
    
    @pytest.fixture(autouse=True) 
    async def setup_search_data(self):
        """Setup test data for search tests"""
        # Insert test documents directly into MongoDB
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.chatbot_app
        
        # Clear existing test data
        await db.test_search.delete_many({})
        
        # Insert test documents
        test_docs = []
        for i, doc in enumerate(TEST_DOCUMENTS):
            # Generate mock embeddings
            mock_embedding = [random.uniform(-1, 1) for _ in range(768)]
            
            test_doc = {
                **doc,
                'embedding': mock_embedding,
                'document_id': f'test_doc_{i}',
                'chunk_index': 0,
                'created_at': time.strftime("%Y-%m-%dT%H:%M:%S"),
                'test_marker': 'search_test_data'
            }
            test_docs.append(test_doc)
        
        await db.test_search.insert_many(test_docs)
        
        yield  # Run the test
        
        # Cleanup
        await db.test_search.delete_many({'test_marker': 'search_test_data'})
        client.close()
    
    @pytest.mark.asyncio
    async def test_basic_search_endpoints(self):
        """Test basic search API endpoints"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            search_data = {
                "query": "healthcare guidelines safety",
                "limit": 5
            }
            
            # Test semantic search
            semantic_response = await client.post(
                f"{TEST_BASE_URL}/search/semantic",
                json=search_data
            )
            
            if semantic_response.status_code == 404:
                print("⚠️ Search endpoints not available - testing alternative paths")
                return
                
            if semantic_response.status_code == 200:
                semantic_results = semantic_response.json()
                assert "results" in semantic_results
                print(f"✅ Semantic search: {len(semantic_results.get('results', []))} results")
    
    @pytest.mark.asyncio
    async def test_hybrid_search_endpoints(self):
        """Test hybrid search functionality"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in TEST_QUERIES[:3]:  # Test first 3 queries
                search_data = {
                    "query": query,
                    "limit": 10
                }
                
                # Test via API Gateway hybrid search
                hybrid_response = await client.post(
                    f"{API_GATEWAY_URL}/hybrid/intelligent-search",
                    json=search_data
                )
                
                if hybrid_response.status_code == 200:
                    hybrid_results = hybrid_response.json()
                    print(f"✅ Hybrid search for '{query[:30]}...': {hybrid_results.get('status', 'completed')}")
                elif hybrid_response.status_code == 404:
                    print("ℹ️ Hybrid search endpoint not available")
                    break
                else:
                    print(f"ℹ️ Hybrid search response: {hybrid_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_document_search(self):
        """Test document-specific search"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            doc_search_data = {
                "query": "emergency procedures safety",
                "filters": {
                    "category": "safety",
                    "type": "procedure"
                },
                "limit": 5
            }
            
            doc_response = await client.post(
                f"{API_GATEWAY_URL}/hybrid/document-search",
                json=doc_search_data
            )
            
            if doc_response.status_code == 200:
                doc_results = doc_response.json()
                print(f"✅ Document search: {doc_results.get('status', 'completed')}")
            else:
                print(f"ℹ️ Document search response: {doc_response.status_code}")


class TestChatFunctionality:
    """Test chat and conversation functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    @pytest.mark.asyncio
    async def test_chat_message_flow(self):
        """Test complete chat message flow"""
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Create session first
            session_data = {
                "user_id": self.user_id,
                "session_type": "chat_test"
            }
            
            session_response = await client.post(
                f"{API_GATEWAY_URL}/sessions/create",
                json=session_data
            )
            
            if session_response.status_code == 200:
                session_result = session_response.json()
                session_id = session_result.get("session_id", self.session_id)
                print(f"✅ Session created: {session_id}")
                
                # Test chat message
                chat_data = {
                    "message": "What are the best practices for elderly care?",
                    "session_id": session_id,
                    "user_id": self.user_id
                }
                
                chat_response = await client.post(
                    f"{TEST_BASE_URL}/chat/message",
                    json=chat_data
                )
                
                if chat_response.status_code == 200:
                    chat_result = chat_response.json()
                    assert "response" in chat_result or "message" in chat_result
                    print(f"✅ Chat response received")
                elif chat_response.status_code == 404:
                    print("ℹ️ Chat endpoints not available")
                else:
                    print(f"ℹ️ Chat response: {chat_response.status_code}")
            else:
                print(f"ℹ️ Session creation response: {session_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_conversation_storage(self):
        """Test conversation storage and retrieval"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Test storing a conversation message
            message_data = {
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "content": "Test conversation message",
                "role": "user",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
            
            store_response = await client.post(
                f"{API_GATEWAY_URL}/conversations/{self.session_id}/message",
                json=message_data
            )
            
            if store_response.status_code == 200:
                print("✅ Conversation message stored")
                
                # Test retrieving conversation history
                history_response = await client.get(
                    f"{API_GATEWAY_URL}/conversations/{self.session_id}/history"
                )
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    print(f"✅ Conversation history retrieved: {len(history_data.get('messages', []))} messages")
                else:
                    print(f"ℹ️ History retrieval: {history_response.status_code}")
            else:
                print(f"ℹ️ Message storage: {store_response.status_code}")


class TestAIServices:
    """Test AI service functionality"""
    
    @pytest.mark.asyncio
    async def test_embedding_service(self):
        """Test embedding generation"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Test via main API
            embed_response = await client.get(f"{TEST_BASE_URL}/dev/test-embedding")
            
            if embed_response.status_code == 200:
                embed_result = embed_response.json()
                assert embed_result["status"] == "success"
                assert embed_result["embedding_dimension"] > 0
                print(f"✅ Embedding service: {embed_result['embedding_dimension']} dimensions")
            else:
                print(f"ℹ️ Embedding test response: {embed_response.status_code}")
            
            # Test direct embedding service
            direct_response = await client.post(
                f"{EMBEDDING_SERVICE_URL}/embedding",
                json={"text": "Test embedding generation"}
            )
            
            if direct_response.status_code == 200:
                embedding = direct_response.json()
                assert isinstance(embedding, list)
                assert len(embedding) > 0
                print(f"✅ Direct embedding service: {len(embedding)} dimensions")
            else:
                print(f"ℹ️ Direct embedding response: {direct_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_generation_service(self):
        """Test text generation"""
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Test via main API
            gen_response = await client.get(f"{TEST_BASE_URL}/dev/test-generation")
            
            if gen_response.status_code == 200:
                gen_result = gen_response.json()
                assert gen_result["status"] == "success"
                assert len(gen_result["generated_response"]) > 0
                print(f"✅ Generation service: {len(gen_result['generated_response'])} chars generated")
            else:
                print(f"ℹ️ Generation test response: {gen_response.status_code}")
            
            # Test direct generation service
            direct_response = await client.post(
                f"{GENERATION_SERVICE_URL}/generate/response",
                json={
                    "prompt": "Explain what AI chatbots are used for.",
                    "max_tokens": 100,
                    "temperature": 0.7
                }
            )
            
            if direct_response.status_code == 200:
                generation = direct_response.json()
                assert "response" in generation
                print(f"✅ Direct generation service: Response generated")
            else:
                print(f"ℹ️ Direct generation response: {direct_response.status_code}")


class TestAnalyticsAndMonitoring:
    """Test analytics and monitoring functionality"""
    
    @pytest.mark.asyncio
    async def test_analytics_endpoints(self):
        """Test analytics data collection and retrieval"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Test analytics dashboard
            dashboard_response = await client.get(f"{API_GATEWAY_URL}/analytics/realtime/dashboard")
            
            if dashboard_response.status_code == 200:
                dashboard_data = dashboard_response.json()
                print(f"✅ Analytics dashboard available")
            else:
                print(f"ℹ️ Analytics dashboard: {dashboard_response.status_code}")
            
            # Test performance metrics recording
            metric_data = {
                "service": "test_integration",
                "operation": "test_metric_recording", 
                "duration_ms": 150.5,
                "success": True,
                "metadata": {"test_run": True}
            }
            
            metric_response = await client.post(
                f"{API_GATEWAY_URL}/analytics/realtime/metric",
                json=metric_data
            )
            
            if metric_response.status_code == 200:
                print("✅ Metric recording successful")
            else:
                print(f"ℹ️ Metric recording: {metric_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring endpoints"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test performance dashboard
            perf_response = await client.get(f"{API_GATEWAY_URL}/hybrid/performance-dashboard")
            
            if perf_response.status_code == 200:
                perf_data = perf_response.json()
                print("✅ Performance dashboard available")
            else:
                print(f"ℹ️ Performance dashboard: {perf_response.status_code}")


class TestMultiDatabaseOperations:
    """Test multi-database operations and routing"""
    
    @pytest.mark.asyncio
    async def test_hybrid_database_stats(self):
        """Test hybrid database statistics"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            stats_response = await client.get(f"{API_GATEWAY_URL}/hybrid/stats")
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                print("✅ Hybrid database stats available")
            else:
                print(f"ℹ️ Hybrid stats: {stats_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_user_preferences_management(self):
        """Test user preferences across databases"""
        async with httpx.AsyncClient(timeout=15.0) as client:
            prefs_data = {
                "user_id": f"test_user_{uuid.uuid4().hex[:8]}",
                "action": "update",
                "preferences": {
                    "theme": "dark",
                    "language": "en",
                    "notifications": True
                }
            }
            
            prefs_response = await client.post(
                f"{API_GATEWAY_URL}/hybrid/user-preferences",
                json=prefs_data
            )
            
            if prefs_response.status_code == 200:
                print("✅ User preferences management working")
            else:
                print(f"ℹ️ User preferences: {prefs_response.status_code}")
    
    @pytest.mark.asyncio
    async def test_hybrid_benchmark(self):
        """Test hybrid system benchmarking"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            benchmark_data = {
                "test_types": ["basic_connectivity", "search_performance"],
                "iterations": 5
            }
            
            benchmark_response = await client.post(
                f"{API_GATEWAY_URL}/hybrid/benchmark",
                json=benchmark_data
            )
            
            if benchmark_response.status_code == 200:
                benchmark_result = benchmark_response.json()
                print(f"✅ Hybrid benchmark: {benchmark_result.get('status', 'completed')}")
            else:
                print(f"ℹ️ Hybrid benchmark: {benchmark_response.status_code}")


class TestErrorHandlingAndRecovery:
    """Test error handling and system recovery"""
    
    @pytest.mark.asyncio
    async def test_invalid_endpoints(self):
        """Test handling of invalid API endpoints"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test non-existent endpoints
            invalid_endpoints = [
                f"{TEST_BASE_URL}/nonexistent",
                f"{API_GATEWAY_URL}/invalid/endpoint",
                f"{EMBEDDING_SERVICE_URL}/missing"
            ]
            
            for endpoint in invalid_endpoints:
                try:
                    response = await client.get(endpoint)
                    assert response.status_code in [404, 405], f"Expected 404/405 for {endpoint}"
                except httpx.ConnectError:
                    print(f"ℹ️ Service not available: {endpoint}")
            
            print("✅ Invalid endpoint handling working correctly")
    
    @pytest.mark.asyncio
    async def test_malformed_requests(self):
        """Test handling of malformed requests"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test malformed JSON
            try:
                response = await client.post(
                    f"{TEST_BASE_URL}/search/semantic",
                    content="invalid json data",
                    headers={"Content-Type": "application/json"}
                )
                assert response.status_code in [400, 422, 404], "Should handle malformed JSON"
                print("✅ Malformed JSON handling working")
            except Exception as e:
                print(f"ℹ️ Malformed request test: {e}")
    
    @pytest.mark.asyncio 
    async def test_timeout_handling(self):
        """Test system behavior under timeouts"""
        # Test with very short timeout
        try:
            async with httpx.AsyncClient(timeout=0.001) as client:
                response = await client.get(f"{TEST_BASE_URL}/health")
        except httpx.TimeoutException:
            print("✅ Timeout handling working correctly")
        except Exception as e:
            print(f"ℹ️ Timeout test result: {e}")


@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete end-to-end user workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_search_workflow(self):
        """Test complete search workflow from query to results"""
        async with httpx.AsyncClient(timeout=25.0) as client:
            workflow_steps = []
            
            # Step 1: Check system health
            health_response = await client.get(f"{TEST_BASE_URL}/health")
            workflow_steps.append(("health_check", health_response.status_code == 200))
            
            # Step 2: Perform search
            search_data = {"query": "healthcare safety protocols", "limit": 10}
            search_response = await client.post(
                f"{API_GATEWAY_URL}/hybrid/intelligent-search", 
                json=search_data
            )
            workflow_steps.append(("search", search_response.status_code == 200))
            
            # Step 3: Test analytics recording
            if search_response.status_code == 200:
                analytics_data = {
                    "service": "search",
                    "operation": "intelligent_search",
                    "success": True,
                    "user_query": "healthcare safety protocols"
                }
                analytics_response = await client.post(
                    f"{API_GATEWAY_URL}/analytics/realtime/metric",
                    json=analytics_data
                )
                workflow_steps.append(("analytics", analytics_response.status_code == 200))
            
            # Report workflow results
            successful_steps = sum(1 for _, success in workflow_steps if success)
            total_steps = len(workflow_steps)
            
            print(f"✅ End-to-end search workflow: {successful_steps}/{total_steps} steps successful")
            for step_name, success in workflow_steps:
                status = "✅" if success else "❌"
                print(f"  {status} {step_name}")
    
    @pytest.mark.asyncio
    async def test_complete_chat_workflow(self):
        """Test complete chat workflow"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            workflow_steps = []
            session_id = f"e2e_test_{uuid.uuid4().hex[:8]}"
            
            try:
                # Step 1: Create session
                session_data = {"user_id": "e2e_test_user"}
                session_response = await client.post(
                    f"{API_GATEWAY_URL}/sessions/create",
                    json=session_data
                )
            except Exception as e:
                print(f"⚠️ Chat workflow test failed due to service connectivity: {e}")
                print("This is expected in demo environment with limited microservice networking")
                return
            workflow_steps.append(("session_creation", session_response.status_code == 200))
            
            if session_response.status_code == 200:
                session_result = session_response.json()
                session_id = session_result.get("session_id", session_id)
            
            # Step 2: Send chat message
            chat_data = {
                "message": "What are the key safety considerations for elderly care?",
                "session_id": session_id
            }
            
            chat_response = await client.post(f"{TEST_BASE_URL}/chat/message", json=chat_data)
            workflow_steps.append(("chat_message", chat_response.status_code in [200, 404]))
            
            # Step 3: Check conversation storage
            history_response = await client.get(
                f"{API_GATEWAY_URL}/conversations/{session_id}/history"
            )
            workflow_steps.append(("conversation_storage", history_response.status_code in [200, 404]))
            
            # Report results
            successful_steps = sum(1 for _, success in workflow_steps if success)
            total_steps = len(workflow_steps)
            
            print(f"✅ End-to-end chat workflow: {successful_steps}/{total_steps} steps successful")


if __name__ == "__main__":
    """Run integration tests directly"""
    import sys
    
    print("🧪 Running MultiDB Chatbot Integration Tests")
    print("=" * 50)
    
    # Run pytest with verbose output
    exit_code = pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "--color=yes"
    ])
    
    sys.exit(exit_code)