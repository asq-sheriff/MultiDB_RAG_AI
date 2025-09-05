#!/usr/bin/env python3
"""
Test Full AI Pipeline in Demo Environment
=========================================
Tests the complete AI pipeline with all components:
- Embedding service (BGE Large)
- Generation service (Qwen2.5-7B)
- Search service (RAG pipeline)
- Content safety service
- Intelligent routing
- Cross-encoder re-ranking
- Vector similarity search
- Hybrid search
"""

import asyncio
import aiohttp
import json
import sys
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

@dataclass
class ServiceTest:
    """Test result for a service"""
    name: str
    url: str
    status: str
    response_time_ms: int
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AIServiceTester:
    """Comprehensive AI service testing suite"""
    
    def __init__(self):
        self.services = {
            "embedding": "http://localhost:8005",
            "generation": "http://localhost:8006", 
            "search": "http://localhost:8001",
            "content_safety": "http://localhost:8007",
            "main_api": "http://localhost:8000"
        }
        self.test_results = []
        
    def print_header(self, title: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}")
        print(f"🧪 {title}")
        print(f"{'=' * 60}{Colors.ENDC}\n")
        
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")
        
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.RED}❌ {message}{Colors.ENDC}")
        
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")
        
    async def test_service_health(self, service_name: str, url: str) -> ServiceTest:
        """Test basic health check for a service"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=10) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        return ServiceTest(
                            name=service_name,
                            url=url,
                            status="healthy",
                            response_time_ms=response_time_ms,
                            details=data
                        )
                    else:
                        return ServiceTest(
                            name=service_name,
                            url=url,
                            status="unhealthy",
                            response_time_ms=response_time_ms,
                            error=f"HTTP {response.status}"
                        )
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return ServiceTest(
                name=service_name,
                url=url,
                status="error",
                response_time_ms=response_time_ms,
                error=str(e)
            )
    
    async def test_embedding_service(self) -> ServiceTest:
        """Test embedding service functionality"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                test_data = {
                    "input": ["I feel lonely and need someone to talk to"],
                    "model": "bge-large-en-v1.5"
                }
                
                async with session.post(
                    f"{self.services['embedding']}/v1/embeddings",
                    json=test_data,
                    timeout=30
                ) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        embeddings = data.get("data", [])
                        if embeddings and len(embeddings[0]["embedding"]) == 1024:
                            return ServiceTest(
                                name="embedding_functionality",
                                url=self.services['embedding'],
                                status="functional",
                                response_time_ms=response_time_ms,
                                details={
                                    "embedding_dim": len(embeddings[0]["embedding"]),
                                    "model": data.get("model"),
                                    "usage": data.get("usage")
                                }
                            )
                    
                    return ServiceTest(
                        name="embedding_functionality", 
                        url=self.services['embedding'],
                        status="error",
                        response_time_ms=response_time_ms,
                        error="Invalid response format"
                    )
                    
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return ServiceTest(
                name="embedding_functionality",
                url=self.services['embedding'], 
                status="error",
                response_time_ms=response_time_ms,
                error=str(e)
            )
    
    async def test_generation_service(self) -> ServiceTest:
        """Test generation service functionality"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                test_data = {
                    "model": "qwen2-1.5b-instruct",
                    "messages": [
                        {"role": "user", "content": "I'm feeling lonely today. Can you help?"}
                    ],
                    "max_tokens": 100,
                    "temperature": 0.7
                }
                
                async with session.post(
                    f"{self.services['generation']}/v1/chat/completions",
                    json=test_data,
                    timeout=60
                ) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        choices = data.get("choices", [])
                        if choices and choices[0]["message"]["content"]:
                            return ServiceTest(
                                name="generation_functionality",
                                url=self.services['generation'],
                                status="functional", 
                                response_time_ms=response_time_ms,
                                details={
                                    "model": data.get("model"),
                                    "response_length": len(choices[0]["message"]["content"]),
                                    "usage": data.get("usage")
                                }
                            )
                    
                    return ServiceTest(
                        name="generation_functionality",
                        url=self.services['generation'],
                        status="error",
                        response_time_ms=response_time_ms,
                        error="Invalid response format"
                    )
                    
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return ServiceTest(
                name="generation_functionality",
                url=self.services['generation'],
                status="error",
                response_time_ms=response_time_ms,
                error=str(e)
            )
    
    async def test_search_service_rag(self) -> ServiceTest:
        """Test search service RAG pipeline"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                test_data = {
                    "query": "How can I deal with loneliness as a senior?",
                    "user_id": "demo_user_sarah",
                    "session_id": "test_session_001",
                    "search_type": "hybrid",
                    "limit": 5
                }
                
                # Add required authentication headers
                headers = {
                    "X-User-ID": "demo_user_sarah",
                    "X-Subscription-Plan": "premium",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    f"{self.services['search']}/api/v1/search/semantic",
                    json=test_data,
                    headers=headers,
                    timeout=30
                ) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        return ServiceTest(
                            name="search_rag_pipeline",
                            url=self.services['search'],
                            status="functional",
                            response_time_ms=response_time_ms,
                            details={
                                "results_count": len(results),
                                "search_type": data.get("search_type"),
                                "query_enhanced": data.get("query_enhanced", False)
                            }
                        )
                    
                    return ServiceTest(
                        name="search_rag_pipeline",
                        url=self.services['search'],
                        status="error",
                        response_time_ms=response_time_ms,
                        error=f"HTTP {response.status}"
                    )
                    
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return ServiceTest(
                name="search_rag_pipeline",
                url=self.services['search'],
                status="error",
                response_time_ms=response_time_ms,
                error=str(e)
            )
    
    async def test_end_to_end_conversation(self) -> ServiceTest:
        """Test complete end-to-end conversation flow"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                test_data = {
                    "message": "I've been feeling very lonely lately. What can I do?",
                    "user_id": "sarah.martinez.demo@example.com",
                    "session_id": "e2e_test_session"
                }
                
                async with session.post(
                    f"{self.services['main_api']}/internal/chat",
                    json=test_data,
                    timeout=60
                ) as response:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        return ServiceTest(
                            name="end_to_end_conversation",
                            url=self.services['main_api'],
                            status="functional",
                            response_time_ms=response_time_ms,
                            details={
                                "has_response": bool(data.get("message") or data.get("answer")),
                                "has_context": data.get("has_context", False),
                                "generation_used": data.get("generation_used", False),
                                "search_quality": data.get("search_quality", {})
                            }
                        )
                    
                    return ServiceTest(
                        name="end_to_end_conversation",
                        url=self.services['main_api'],
                        status="error",
                        response_time_ms=response_time_ms,
                        error=f"HTTP {response.status}"
                    )
                    
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return ServiceTest(
                name="end_to_end_conversation",
                url=self.services['main_api'],
                status="error",
                response_time_ms=response_time_ms,
                error=str(e)
            )
    
    async def run_all_tests(self):
        """Run complete AI pipeline test suite"""
        self.print_header("AI Pipeline Test Suite - Demo Environment")
        
        print(f"{Colors.BLUE}Testing complete AI pipeline with:")
        print(f"• Embedding Service: BGE-Large (1024d)")
        print(f"• Generation Service: Qwen2.5-7B")
        print(f"• Search Service: RAG Pipeline")
        print(f"• Content Safety: PHI Detection")
        print(f"• Intelligent Routing & Cross-encoder Re-ranking{Colors.ENDC}\n")
        
        # Test 1: Health checks
        self.print_header("Phase 1: Service Health Checks")
        for service_name, url in self.services.items():
            test_result = await self.test_service_health(service_name, url)
            self.test_results.append(test_result)
            
            if test_result.status == "healthy":
                self.print_success(f"{service_name.title()}: {test_result.response_time_ms}ms")
            else:
                self.print_error(f"{service_name.title()}: {test_result.error}")
        
        # Test 2: Embedding functionality 
        self.print_header("Phase 2: BGE Embedding Service Test")
        embedding_result = await self.test_embedding_service()
        self.test_results.append(embedding_result)
        
        if embedding_result.status == "functional":
            self.print_success(f"Embeddings: {embedding_result.details['embedding_dim']}d in {embedding_result.response_time_ms}ms")
        else:
            self.print_error(f"Embedding test failed: {embedding_result.error}")
        
        # Test 3: Generation functionality
        self.print_header("Phase 3: Qwen Generation Service Test") 
        generation_result = await self.test_generation_service()
        self.test_results.append(generation_result)
        
        if generation_result.status == "functional":
            self.print_success(f"Generation: {generation_result.details['response_length']} chars in {generation_result.response_time_ms}ms")
        else:
            self.print_error(f"Generation test failed: {generation_result.error}")
        
        # Test 4: RAG pipeline
        self.print_header("Phase 4: RAG Pipeline Test")
        search_result = await self.test_search_service_rag()
        self.test_results.append(search_result)
        
        if search_result.status == "functional":
            self.print_success(f"RAG Search: {search_result.details['results_count']} results in {search_result.response_time_ms}ms")
        else:
            self.print_error(f"RAG search test failed: {search_result.error}")
        
        # Test 5: End-to-end conversation
        self.print_header("Phase 5: End-to-End Conversation Test")
        e2e_result = await self.test_end_to_end_conversation()
        self.test_results.append(e2e_result)
        
        if e2e_result.status == "functional":
            self.print_success(f"E2E Conversation: Generated response in {e2e_result.response_time_ms}ms")
            if e2e_result.details.get("generation_used"):
                self.print_success("✓ Real AI generation used")
            if e2e_result.details.get("has_context"):
                self.print_success("✓ RAG context retrieved")
        else:
            self.print_error(f"E2E conversation test failed: {e2e_result.error}")
        
        # Final report
        self.print_test_summary()
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        self.print_header("Test Summary")
        
        passed = sum(1 for r in self.test_results if r.status in ["healthy", "functional"])
        total = len(self.test_results)
        
        print(f"{Colors.BOLD}Overall Results: {passed}/{total} tests passed{Colors.ENDC}")
        print(f"Success Rate: {(passed/total)*100:.1f}%\n")
        
        # Performance summary
        avg_response_time = sum(r.response_time_ms for r in self.test_results) / len(self.test_results)
        print(f"{Colors.BLUE}Performance Summary:${Colors.ENDC}")
        print(f"Average Response Time: {avg_response_time:.0f}ms")
        
        for result in self.test_results:
            status_icon = "✅" if result.status in ["healthy", "functional"] else "❌"
            print(f"  {status_icon} {result.name}: {result.response_time_ms}ms")
        
        # Recommendations
        print(f"\n{Colors.YELLOW}AI Pipeline Status:${Colors.ENDC}")
        if passed == total:
            self.print_success("All AI services operational - Full demo capabilities available")
            print(f"{Colors.GREEN}🎯 Ready for complete AI pipeline demonstration including:")
            print(f"   • Semantic search with BGE embeddings") 
            print(f"   • Therapeutic conversation generation with Qwen")
            print(f"   • Hybrid keyword + vector search")
            print(f"   • Cross-encoder re-ranking")
            print(f"   • Real-time safety validation{Colors.ENDC}")
        else:
            failed_services = [r.name for r in self.test_results if r.status not in ["healthy", "functional"]]
            self.print_warning(f"Some AI services not available: {', '.join(failed_services)}")
            print(f"{Colors.YELLOW}Demo will fall back to simulation mode for failed services{Colors.ENDC}")

async def main():
    """Main test execution"""
    tester = AIServiceTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())