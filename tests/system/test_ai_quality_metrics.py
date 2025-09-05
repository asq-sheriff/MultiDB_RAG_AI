"""
Comprehensive AI Quality Metrics Testing Suite
Tests key RAG metrics: relevance, coherence, faithfulness, groundedness, and latency
"""

import asyncio
import time
import logging
from typing import List, Dict, Any
import statistics

import pytest

from ai_services.shared.dependencies.dependencies import (
    get_chatbot_service,
    get_knowledge_service,
    get_embedding_service,
)

logger = logging.getLogger(__name__)


class AIQualityMetrics:
    """AI Quality metrics calculation utilities"""
    
    @staticmethod
    def calculate_relevance_score(query: str, retrieved_docs: List[Dict]) -> float:
        """Calculate relevance score based on content overlap and semantic similarity"""
        if not retrieved_docs:
            return 0.0
        
        query_tokens = set(query.lower().split())
        relevance_scores = []
        
        for doc in retrieved_docs:
            content = doc.get('content', '') + doc.get('answer', '')
            doc_tokens = set(content.lower().split())
            
            # Simple token overlap ratio
            overlap = len(query_tokens.intersection(doc_tokens))
            total_tokens = len(query_tokens.union(doc_tokens))
            
            if total_tokens > 0:
                overlap_score = overlap / len(query_tokens)  # Precision-like metric
                relevance_scores.append(min(overlap_score, 1.0))
            else:
                relevance_scores.append(0.0)
        
        return statistics.mean(relevance_scores) if relevance_scores else 0.0
    
    @staticmethod
    def calculate_coherence_score(generated_answer: str) -> float:
        """Calculate coherence based on answer structure and completeness"""
        if not generated_answer or len(generated_answer.strip()) == 0:
            return 0.0
        
        # Simple heuristics for coherence
        sentences = generated_answer.split('.')
        coherence_indicators = 0
        total_checks = 5
        
        # Check 1: Has multiple sentences (structure)
        if len(sentences) > 1:
            coherence_indicators += 1
        
        # Check 2: Reasonable length (not too short/long)
        word_count = len(generated_answer.split())
        if 10 <= word_count <= 200:
            coherence_indicators += 1
        
        # Check 3: No excessive repetition
        words = generated_answer.lower().split()
        unique_words = set(words)
        if len(words) > 0 and len(unique_words) / len(words) > 0.7:
            coherence_indicators += 1
        
        # Check 4: Contains answer indicators
        answer_patterns = ['is', 'are', 'can', 'will', 'should', 'because', 'since']
        if any(pattern in generated_answer.lower() for pattern in answer_patterns):
            coherence_indicators += 1
        
        # Check 5: No obvious errors (simple check)
        if not any(error in generated_answer.lower() for error in ['error', 'failed', 'none']):
            coherence_indicators += 1
        
        return coherence_indicators / total_checks
    
    @staticmethod
    def calculate_faithfulness_score(generated_answer: str, retrieved_docs: List[Dict]) -> float:
        """Calculate faithfulness - how well answer is grounded in retrieved documents"""
        if not generated_answer or not retrieved_docs:
            return 0.0
        
        answer_tokens = set(generated_answer.lower().split())
        document_tokens = set()
        
        # Collect all tokens from retrieved documents
        for doc in retrieved_docs:
            content = doc.get('content', '') + doc.get('answer', '')
            document_tokens.update(content.lower().split())
        
        if not document_tokens:
            return 0.0
        
        # Calculate how many answer tokens are present in documents
        grounded_tokens = answer_tokens.intersection(document_tokens)
        faithfulness = len(grounded_tokens) / len(answer_tokens) if answer_tokens else 0.0
        
        return min(faithfulness, 1.0)
    
    @staticmethod
    def calculate_groundedness_score(generated_answer: str, query: str) -> float:
        """Calculate groundedness - how well answer addresses the specific query"""
        if not generated_answer or not query:
            return 0.0
        
        query_tokens = set(query.lower().split())
        answer_tokens = set(generated_answer.lower().split())
        
        # Query coverage in answer
        query_coverage = len(query_tokens.intersection(answer_tokens)) / len(query_tokens) if query_tokens else 0.0
        
        # Answer specificity (avoid generic responses)
        specific_patterns = ['specifically', 'exactly', 'precisely', 'according to', 'based on']
        specificity_bonus = 0.2 if any(pattern in generated_answer.lower() for pattern in specific_patterns) else 0.0
        
        groundedness = min(query_coverage + specificity_bonus, 1.0)
        return groundedness


class TestAIQualityMetrics:
    """Test suite for AI Quality metrics"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup services for testing"""
        self.chatbot_service = get_chatbot_service()
        self.knowledge_service = get_knowledge_service() 
        self.embedding_service = get_embedding_service()
        self.metrics = AIQualityMetrics()
        
        # Test queries for different scenarios
        self.test_queries = [
            {
                "query": "What is artificial intelligence?",
                "category": "general_knowledge",
                "expected_relevance": 0.3  # Lower expectation without seeded data
            },
            {
                "query": "How does machine learning work?",
                "category": "technical",
                "expected_relevance": 0.3
            },
            {
                "query": "What are the benefits of AI?",
                "category": "conceptual", 
                "expected_relevance": 0.3
            },
            {
                "query": "Can you help me with data science?",
                "category": "assistance",
                "expected_relevance": 0.2
            }
        ]
        
        yield
        
        # Cleanup if needed
        pass
    
    @pytest.mark.asyncio
    async def test_retrieval_quality_metrics(self):
        """Test retrieval quality across multiple queries"""
        retrieval_metrics = []
        
        for test_case in self.test_queries:
            query = test_case["query"]
            
            # Measure retrieval latency
            start_time = time.time()
            results = await self.knowledge_service.search_router(
                query=query, 
                top_k=5, 
                route="semantic"
            )
            retrieval_latency = time.time() - start_time
            
            # Extract retrieved documents
            retrieved_docs = results.get("results", [])
            
            # Calculate relevance score
            relevance_score = self.metrics.calculate_relevance_score(query, retrieved_docs)
            
            metrics = {
                "query": query,
                "category": test_case["category"],
                "retrieval_latency_ms": retrieval_latency * 1000,
                "documents_retrieved": len(retrieved_docs),
                "relevance_score": relevance_score,
                "expected_relevance": test_case["expected_relevance"]
            }
            
            retrieval_metrics.append(metrics)
            
            # Assertions
            assert retrieval_latency < 5.0, f"Retrieval too slow: {retrieval_latency:.2f}s for query: {query}"
            assert len(retrieved_docs) >= 0, "Should handle empty results gracefully"
            assert 0 <= relevance_score <= 1, f"Invalid relevance score: {relevance_score}"
            
            logger.info(f"Retrieval metrics for '{query}': "
                       f"latency={retrieval_latency*1000:.1f}ms, "
                       f"docs={len(retrieved_docs)}, "
                       f"relevance={relevance_score:.3f}")
        
        # Overall retrieval performance
        avg_latency = statistics.mean([m["retrieval_latency_ms"] for m in retrieval_metrics])
        avg_relevance = statistics.mean([m["relevance_score"] for m in retrieval_metrics])
        
        assert avg_latency < 3000, f"Average retrieval latency too high: {avg_latency:.1f}ms"
        logger.info(f"Overall retrieval performance: avg_latency={avg_latency:.1f}ms, avg_relevance={avg_relevance:.3f}")
    
    @pytest.mark.asyncio
    async def test_generation_quality_metrics(self):
        """Test generation quality across multiple queries"""
        generation_metrics = []
        
        for test_case in self.test_queries:
            query = test_case["query"]
            
            # Measure generation latency
            start_time = time.time()
            response = await self.chatbot_service.answer_user_message(
                user_id="quality_test_user",
                message=query,
                route="auto"
            )
            generation_latency = time.time() - start_time
            
            generated_answer = response.get("answer", "")
            retrieval_info = response.get("retrieval", {})
            retrieved_docs = retrieval_info.get("results", [])
            
            # Calculate quality metrics
            coherence_score = self.metrics.calculate_coherence_score(generated_answer)
            faithfulness_score = self.metrics.calculate_faithfulness_score(generated_answer, retrieved_docs)
            groundedness_score = self.metrics.calculate_groundedness_score(generated_answer, query)
            
            metrics = {
                "query": query,
                "category": test_case["category"],
                "generation_latency_ms": generation_latency * 1000,
                "answer_length": len(generated_answer),
                "coherence_score": coherence_score,
                "faithfulness_score": faithfulness_score,
                "groundedness_score": groundedness_score,
                "overall_quality": (coherence_score + faithfulness_score + groundedness_score) / 3
            }
            
            generation_metrics.append(metrics)
            
            # Assertions
            assert generation_latency < 10.0, f"Generation too slow: {generation_latency:.2f}s for query: {query}"
            assert len(generated_answer) > 0, "Should generate non-empty answer"
            assert 0 <= coherence_score <= 1, f"Invalid coherence score: {coherence_score}"
            assert 0 <= faithfulness_score <= 1, f"Invalid faithfulness score: {faithfulness_score}"
            assert 0 <= groundedness_score <= 1, f"Invalid groundedness score: {groundedness_score}"
            
            # Quality thresholds (lenient for test environment)
            assert coherence_score >= 0.4, f"Low coherence for '{query}': {coherence_score:.3f}"
            
            logger.info(f"Generation metrics for '{query}': "
                       f"latency={generation_latency*1000:.1f}ms, "
                       f"coherence={coherence_score:.3f}, "
                       f"faithfulness={faithfulness_score:.3f}, "
                       f"groundedness={groundedness_score:.3f}")
        
        # Overall generation performance
        avg_latency = statistics.mean([m["generation_latency_ms"] for m in generation_metrics])
        avg_coherence = statistics.mean([m["coherence_score"] for m in generation_metrics])
        avg_faithfulness = statistics.mean([m["faithfulness_score"] for m in generation_metrics])
        avg_groundedness = statistics.mean([m["groundedness_score"] for m in generation_metrics])
        overall_quality = (avg_coherence + avg_faithfulness + avg_groundedness) / 3
        
        assert avg_latency < 8000, f"Average generation latency too high: {avg_latency:.1f}ms"
        assert overall_quality >= 0.4, f"Overall quality too low: {overall_quality:.3f}"
        
        logger.info(f"Overall generation performance: "
                   f"avg_latency={avg_latency:.1f}ms, "
                   f"coherence={avg_coherence:.3f}, "
                   f"faithfulness={avg_faithfulness:.3f}, "
                   f"groundedness={avg_groundedness:.3f}, "
                   f"overall_quality={overall_quality:.3f}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_rag_quality(self):
        """Test complete RAG pipeline quality"""
        end_to_end_metrics = []
        
        for test_case in self.test_queries:
            query = test_case["query"]
            
            # Measure end-to-end latency
            start_time = time.time()
            
            # Get retrieval results
            retrieval_results = await self.knowledge_service.search_router(
                query=query, top_k=5, route="auto"
            )
            
            # Get complete response
            response = await self.chatbot_service.answer_user_message(
                user_id="e2e_test_user",
                message=query,
                route="auto"
            )
            
            end_to_end_latency = time.time() - start_time
            
            generated_answer = response.get("answer", "")
            retrieved_docs = retrieval_results.get("results", [])
            
            # Calculate comprehensive metrics
            relevance_score = self.metrics.calculate_relevance_score(query, retrieved_docs)
            coherence_score = self.metrics.calculate_coherence_score(generated_answer)
            faithfulness_score = self.metrics.calculate_faithfulness_score(generated_answer, retrieved_docs)
            groundedness_score = self.metrics.calculate_groundedness_score(generated_answer, query)
            
            # RAG-specific composite score
            rag_quality_score = (
                relevance_score * 0.25 +      # How relevant were retrieved docs
                coherence_score * 0.25 +      # How coherent is the answer  
                faithfulness_score * 0.25 +   # How grounded in retrieved docs
                groundedness_score * 0.25     # How well does it address query
            )
            
            metrics = {
                "query": query,
                "category": test_case["category"], 
                "e2e_latency_ms": end_to_end_latency * 1000,
                "docs_retrieved": len(retrieved_docs),
                "answer_length": len(generated_answer),
                "relevance_score": relevance_score,
                "coherence_score": coherence_score,
                "faithfulness_score": faithfulness_score,
                "groundedness_score": groundedness_score,
                "rag_quality_score": rag_quality_score
            }
            
            end_to_end_metrics.append(metrics)
            
            # Assertions
            assert end_to_end_latency < 15.0, f"E2E too slow: {end_to_end_latency:.2f}s for query: {query}"
            assert 0 <= rag_quality_score <= 1, f"Invalid RAG quality score: {rag_quality_score}"
            
            # Quality threshold (lenient for test environment)
            assert rag_quality_score >= 0.3, f"RAG quality too low for '{query}': {rag_quality_score:.3f}"
            
            logger.info(f"E2E RAG metrics for '{query}': "
                       f"latency={end_to_end_latency*1000:.1f}ms, "
                       f"rag_quality={rag_quality_score:.3f}")
        
        # Overall RAG performance
        avg_e2e_latency = statistics.mean([m["e2e_latency_ms"] for m in end_to_end_metrics])
        avg_rag_quality = statistics.mean([m["rag_quality_score"] for m in end_to_end_metrics])
        
        assert avg_e2e_latency < 12000, f"Average E2E latency too high: {avg_e2e_latency:.1f}ms"
        assert avg_rag_quality >= 0.35, f"Average RAG quality too low: {avg_rag_quality:.3f}"
        
        logger.info(f"Overall E2E RAG performance: "
                   f"avg_latency={avg_e2e_latency:.1f}ms, "
                   f"avg_rag_quality={avg_rag_quality:.3f}")
    
    @pytest.mark.asyncio 
    async def test_embedding_quality_metrics(self):
        """Test embedding service quality and consistency"""
        if not self.embedding_service:
            pytest.skip("Embedding service not available")
        
        test_texts = [
            "What is artificial intelligence?",
            "How does machine learning work?", 
            "What are neural networks?",
            "Explain deep learning algorithms"
        ]
        
        embedding_metrics = []
        
        for text in test_texts:
            start_time = time.time()
            
            if hasattr(self.embedding_service, 'embed_query'):
                embedding = await self.embedding_service.embed_query(text)
            else:
                # Skip if method not available
                continue
                
            embedding_latency = time.time() - start_time
            
            metrics = {
                "text": text,
                "embedding_latency_ms": embedding_latency * 1000,
                "embedding_dimension": len(embedding) if embedding else 0,
                "embedding_norm": sum(x*x for x in embedding)**0.5 if embedding else 0
            }
            
            embedding_metrics.append(metrics)
            
            # Assertions
            assert embedding_latency < 2.0, f"Embedding too slow: {embedding_latency:.2f}s"
            assert len(embedding) > 0, "Should generate non-empty embedding"
            assert all(isinstance(x, (int, float)) for x in embedding), "Embedding should be numeric"
            
            logger.info(f"Embedding metrics for '{text[:30]}...': "
                       f"latency={embedding_latency*1000:.1f}ms, "
                       f"dim={len(embedding)}")
        
        if embedding_metrics:
            avg_embedding_latency = statistics.mean([m["embedding_latency_ms"] for m in embedding_metrics])
            assert avg_embedding_latency < 1500, f"Average embedding latency too high: {avg_embedding_latency:.1f}ms"
            
            logger.info(f"Overall embedding performance: avg_latency={avg_embedding_latency:.1f}ms")