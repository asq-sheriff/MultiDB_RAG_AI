#!/usr/bin/env python3
"""
AI Quality Benchmarking Script
Runs comprehensive quality assessments and generates reports
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
import argparse
import logging
import statistics
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIQualityBenchmark:
    """Comprehensive AI Quality Benchmarking Suite"""
    
    def __init__(self):
        self.results = {
            "benchmark_info": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "description": "Lilo_EmotionalAI_Backend AI Quality Benchmark"
            },
            "retrieval_metrics": [],
            "generation_metrics": [],
            "end_to_end_metrics": [],
            "embedding_metrics": [],
            "overall_performance": {}
        }
    
    def calculate_metrics(self, query: str, retrieved_docs: List[Dict], 
                         generated_answer: str, latencies: Dict[str, float]) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics"""
        
        # Relevance Score
        if retrieved_docs:
            query_tokens = set(query.lower().split())
            relevance_scores = []
            
            for doc in retrieved_docs:
                content = doc.get('content', '') + doc.get('answer', '')
                doc_tokens = set(content.lower().split())
                
                if query_tokens:
                    overlap = len(query_tokens.intersection(doc_tokens))
                    relevance = overlap / len(query_tokens)
                    relevance_scores.append(min(relevance, 1.0))
            
            relevance_score = statistics.mean(relevance_scores) if relevance_scores else 0.0
        else:
            relevance_score = 0.0
        
        # Coherence Score
        if generated_answer:
            sentences = generated_answer.split('.')
            word_count = len(generated_answer.split())
            words = generated_answer.lower().split()
            unique_words = set(words)
            
            coherence_factors = 0
            total_factors = 4
            
            if len(sentences) > 1: coherence_factors += 1
            if 10 <= word_count <= 200: coherence_factors += 1
            if len(words) > 0 and len(unique_words) / len(words) > 0.7: coherence_factors += 1
            if any(p in generated_answer.lower() for p in ['is', 'are', 'can', 'will']): coherence_factors += 1
            
            coherence_score = coherence_factors / total_factors
        else:
            coherence_score = 0.0
        
        # Faithfulness Score
        if generated_answer and retrieved_docs:
            answer_tokens = set(generated_answer.lower().split())
            doc_tokens = set()
            
            for doc in retrieved_docs:
                content = doc.get('content', '') + doc.get('answer', '')
                doc_tokens.update(content.lower().split())
            
            if answer_tokens and doc_tokens:
                grounded_tokens = answer_tokens.intersection(doc_tokens)
                faithfulness_score = len(grounded_tokens) / len(answer_tokens)
            else:
                faithfulness_score = 0.0
        else:
            faithfulness_score = 0.0
        
        # Groundedness Score
        if generated_answer and query:
            query_tokens = set(query.lower().split())
            answer_tokens = set(generated_answer.lower().split())
            
            if query_tokens:
                coverage = len(query_tokens.intersection(answer_tokens)) / len(query_tokens)
            else:
                coverage = 0.0
            
            # Specificity bonus
            specific_patterns = ['specifically', 'exactly', 'according to', 'based on']
            specificity = 0.1 if any(p in generated_answer.lower() for p in specific_patterns) else 0.0
            
            groundedness_score = min(coverage + specificity, 1.0)
        else:
            groundedness_score = 0.0
        
        return {
            "query": query,
            "documents_retrieved": len(retrieved_docs),
            "answer_length": len(generated_answer) if generated_answer else 0,
            "relevance_score": round(relevance_score, 3),
            "coherence_score": round(coherence_score, 3),
            "faithfulness_score": round(faithfulness_score, 3),
            "groundedness_score": round(groundedness_score, 3),
            "composite_quality_score": round((relevance_score + coherence_score + 
                                           faithfulness_score + groundedness_score) / 4, 3),
            "retrieval_latency_ms": round(latencies.get("retrieval", 0) * 1000, 1),
            "generation_latency_ms": round(latencies.get("generation", 0) * 1000, 1),
            "total_latency_ms": round(latencies.get("total", 0) * 1000, 1)
        }
    
    async def run_retrieval_benchmark(self, knowledge_service) -> List[Dict[str, Any]]:
        """Run retrieval quality benchmark"""
        logger.info("🔍 Running retrieval quality benchmark...")
        
        test_queries = [
            {"query": "What is artificial intelligence?", "category": "definition"},
            {"query": "How does machine learning work?", "category": "process"},
            {"query": "What are neural networks?", "category": "concept"},
            {"query": "Explain deep learning algorithms", "category": "technical"},
            {"query": "What are the benefits of AI?", "category": "analysis"},
            {"query": "Can you help me understand data science?", "category": "assistance"},
            {"query": "What is natural language processing?", "category": "field"},
            {"query": "How do recommendation systems work?", "category": "application"}
        ]
        
        benchmark_results = []
        
        for test_case in test_queries:
            query = test_case["query"]
            
            start_time = time.time()
            try:
                results = await knowledge_service.search_router(
                    query=query, top_k=5, route="auto"
                )
                retrieval_latency = time.time() - start_time
                
                retrieved_docs = results.get("results", [])
                
                metrics = self.calculate_metrics(
                    query=query,
                    retrieved_docs=retrieved_docs,
                    generated_answer="",  # Just retrieval test
                    latencies={"retrieval": retrieval_latency}
                )
                
                metrics.update({
                    "category": test_case["category"],
                    "route_used": results.get("route", "unknown"),
                    "search_strategy": results.get("search_type", "unknown")
                })
                
                benchmark_results.append(metrics)
                logger.info(f"  Query: '{query[:40]}...' - Relevance: {metrics['relevance_score']:.3f}")
                
            except Exception as e:
                logger.error(f"Retrieval benchmark failed for '{query}': {e}")
                benchmark_results.append({
                    "query": query,
                    "category": test_case["category"],
                    "error": str(e),
                    "relevance_score": 0.0
                })
        
        return benchmark_results
    
    async def run_generation_benchmark(self, chatbot_service) -> List[Dict[str, Any]]:
        """Run generation quality benchmark"""
        logger.info("🤖 Running generation quality benchmark...")
        
        test_queries = [
            {"query": "What is the difference between AI and machine learning?", "category": "comparison"},
            {"query": "How can AI help in healthcare?", "category": "application"},
            {"query": "What are the ethical concerns with AI?", "category": "ethics"},
            {"query": "Explain how neural networks learn", "category": "explanation"},
            {"query": "What is the future of artificial intelligence?", "category": "prediction"},
            {"query": "How do I get started with machine learning?", "category": "guidance"},
        ]
        
        benchmark_results = []
        
        for test_case in test_queries:
            query = test_case["query"]
            
            start_time = time.time()
            try:
                response = await chatbot_service.answer_user_message(
                    user_id="benchmark_user",
                    message=query,
                    route="auto"
                )
                total_latency = time.time() - start_time
                
                generated_answer = response.get("answer", "")
                retrieval_info = response.get("retrieval", {})
                retrieved_docs = retrieval_info.get("results", [])
                
                metrics = self.calculate_metrics(
                    query=query,
                    retrieved_docs=retrieved_docs,
                    generated_answer=generated_answer,
                    latencies={"total": total_latency}
                )
                
                metrics.update({
                    "category": test_case["category"],
                    "route_used": response.get("route", "unknown"),
                    "generation_strategy": response.get("generation_strategy", "unknown")
                })
                
                benchmark_results.append(metrics)
                logger.info(f"  Query: '{query[:40]}...' - Quality: {metrics['composite_quality_score']:.3f}")
                
            except Exception as e:
                logger.error(f"Generation benchmark failed for '{query}': {e}")
                benchmark_results.append({
                    "query": query,
                    "category": test_case["category"], 
                    "error": str(e),
                    "composite_quality_score": 0.0
                })
        
        return benchmark_results
    
    async def run_embedding_benchmark(self, embedding_service) -> List[Dict[str, Any]]:
        """Run embedding quality benchmark"""
        logger.info("🧠 Running embedding quality benchmark...")
        
        if not embedding_service or not hasattr(embedding_service, 'embed_query'):
            logger.warning("Embedding service not available, skipping embedding benchmark")
            return []
        
        test_texts = [
            "What is artificial intelligence?",
            "Machine learning algorithms",
            "Deep neural networks",
            "Natural language processing",
            "Computer vision applications",
            "Reinforcement learning systems"
        ]
        
        benchmark_results = []
        
        for text in test_texts:
            start_time = time.time()
            try:
                embedding = await embedding_service.embed_query(text)
                embedding_latency = time.time() - start_time
                
                metrics = {
                    "text": text,
                    "embedding_latency_ms": round(embedding_latency * 1000, 1),
                    "embedding_dimension": len(embedding) if embedding else 0,
                    "embedding_norm": round(sum(x*x for x in embedding)**0.5, 3) if embedding else 0,
                    "non_zero_components": sum(1 for x in embedding if abs(x) > 1e-6) if embedding else 0
                }
                
                benchmark_results.append(metrics)
                logger.info(f"  Text: '{text[:30]}...' - Latency: {metrics['embedding_latency_ms']:.1f}ms")
                
            except Exception as e:
                logger.error(f"Embedding benchmark failed for '{text}': {e}")
                benchmark_results.append({
                    "text": text,
                    "error": str(e),
                    "embedding_latency_ms": 0,
                    "embedding_dimension": 0
                })
        
        return benchmark_results
    
    def calculate_overall_performance(self) -> Dict[str, Any]:
        """Calculate overall performance summary"""
        logger.info("📊 Calculating overall performance metrics...")
        
        # Retrieval Performance
        retrieval_data = [r for r in self.results["retrieval_metrics"] if "error" not in r]
        if retrieval_data:
            avg_relevance = statistics.mean([r["relevance_score"] for r in retrieval_data])
            avg_retrieval_latency = statistics.mean([r["retrieval_latency_ms"] for r in retrieval_data])
        else:
            avg_relevance = 0.0
            avg_retrieval_latency = 0.0
        
        # Generation Performance  
        generation_data = [r for r in self.results["generation_metrics"] if "error" not in r]
        if generation_data:
            avg_coherence = statistics.mean([r["coherence_score"] for r in generation_data])
            avg_faithfulness = statistics.mean([r["faithfulness_score"] for r in generation_data])
            avg_groundedness = statistics.mean([r["groundedness_score"] for r in generation_data])
            avg_composite_quality = statistics.mean([r["composite_quality_score"] for r in generation_data])
            avg_generation_latency = statistics.mean([r["total_latency_ms"] for r in generation_data])
        else:
            avg_coherence = avg_faithfulness = avg_groundedness = avg_composite_quality = 0.0
            avg_generation_latency = 0.0
        
        # Embedding Performance
        embedding_data = [r for r in self.results["embedding_metrics"] if "error" not in r]
        if embedding_data:
            avg_embedding_latency = statistics.mean([r["embedding_latency_ms"] for r in embedding_data])
            avg_embedding_dimension = statistics.mean([r["embedding_dimension"] for r in embedding_data])
        else:
            avg_embedding_latency = avg_embedding_dimension = 0.0
        
        return {
            "retrieval_performance": {
                "avg_relevance_score": round(avg_relevance, 3),
                "avg_latency_ms": round(avg_retrieval_latency, 1),
                "queries_processed": len(retrieval_data)
            },
            "generation_performance": {
                "avg_coherence_score": round(avg_coherence, 3),
                "avg_faithfulness_score": round(avg_faithfulness, 3),
                "avg_groundedness_score": round(avg_groundedness, 3),
                "avg_composite_quality": round(avg_composite_quality, 3),
                "avg_latency_ms": round(avg_generation_latency, 1),
                "queries_processed": len(generation_data)
            },
            "embedding_performance": {
                "avg_latency_ms": round(avg_embedding_latency, 1),
                "avg_dimension": round(avg_embedding_dimension, 1),
                "texts_processed": len(embedding_data)
            },
            "overall_quality_score": round((avg_relevance + avg_composite_quality) / 2, 3),
            "performance_grade": self._calculate_performance_grade(
                avg_relevance, avg_composite_quality, avg_generation_latency
            )
        }
    
    def _calculate_performance_grade(self, relevance: float, quality: float, latency: float) -> str:
        """Calculate overall performance grade"""
        # Normalize latency (assume 5000ms is poor, 1000ms is excellent)
        latency_score = max(0, min(1, (5000 - latency) / 4000)) if latency > 0 else 0
        
        overall_score = (relevance * 0.3 + quality * 0.5 + latency_score * 0.2)
        
        if overall_score >= 0.9: return "A+ (Excellent)"
        elif overall_score >= 0.8: return "A (Very Good)"
        elif overall_score >= 0.7: return "B+ (Good)"
        elif overall_score >= 0.6: return "B (Acceptable)"
        elif overall_score >= 0.5: return "C+ (Below Average)"
        elif overall_score >= 0.4: return "C (Poor)"
        else: return "D (Needs Improvement)"
    
    async def run_full_benchmark(self):
        """Run complete AI quality benchmark"""
        logger.info("🚀 Starting comprehensive AI Quality Benchmark...")
        
        try:
            # Import dependencies
            import sys
            sys.path.append('/')
            
            from ai_services.shared.dependencies.dependencies import (
                get_chatbot_service,
                get_knowledge_service, 
                get_embedding_service
            )
            
            # Get services
            knowledge_service = get_knowledge_service()
            chatbot_service = get_chatbot_service()
            embedding_service = get_embedding_service()
            
            # Run benchmarks
            if knowledge_service:
                self.results["retrieval_metrics"] = await self.run_retrieval_benchmark(knowledge_service)
            
            if chatbot_service:
                self.results["generation_metrics"] = await self.run_generation_benchmark(chatbot_service)
            
            if embedding_service:
                self.results["embedding_metrics"] = await self.run_embedding_benchmark(embedding_service)
            
            # Calculate overall performance
            self.results["overall_performance"] = self.calculate_overall_performance()
            
            logger.info("✅ Benchmark completed successfully")
            return self.results
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            raise
    
    def save_report(self, output_path: str):
        """Save benchmark report to file"""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"📄 Benchmark report saved to: {output_path}")
    
    def print_summary(self):
        """Print benchmark summary to console"""
        overall = self.results["overall_performance"]
        
        print("\n" + "="*60)
        print("🎯 AI QUALITY BENCHMARK SUMMARY")
        print("="*60)
        
        print(f"\n📊 Overall Performance Grade: {overall['performance_grade']}")
        print(f"🏆 Overall Quality Score: {overall['overall_quality_score']:.3f}")
        
        print(f"\n🔍 Retrieval Performance:")
        retrieval = overall["retrieval_performance"]
        print(f"   • Average Relevance: {retrieval['avg_relevance_score']:.3f}")
        print(f"   • Average Latency: {retrieval['avg_latency_ms']:.1f}ms")
        print(f"   • Queries Processed: {retrieval['queries_processed']}")
        
        print(f"\n🤖 Generation Performance:")
        generation = overall["generation_performance"]
        print(f"   • Average Coherence: {generation['avg_coherence_score']:.3f}")
        print(f"   • Average Faithfulness: {generation['avg_faithfulness_score']:.3f}")
        print(f"   • Average Groundedness: {generation['avg_groundedness_score']:.3f}")
        print(f"   • Composite Quality: {generation['avg_composite_quality']:.3f}")
        print(f"   • Average Latency: {generation['avg_latency_ms']:.1f}ms")
        
        print(f"\n🧠 Embedding Performance:")
        embedding = overall["embedding_performance"]
        print(f"   • Average Latency: {embedding['avg_latency_ms']:.1f}ms")
        print(f"   • Vector Dimension: {embedding['avg_dimension']:.0f}")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description="AI Quality Benchmark")
    parser.add_argument("--output", "-o", default="benchmark_report.json", 
                       help="Output file path for benchmark report")
    parser.add_argument("--quiet", "-q", action="store_true", 
                       help="Minimal output")
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    async def run_benchmark():
        benchmark = AIQualityBenchmark()
        await benchmark.run_full_benchmark()
        
        if not args.quiet:
            benchmark.print_summary()
        
        benchmark.save_report(args.output)
        
        return benchmark.results["overall_performance"]["performance_grade"]
    
    # Run the benchmark
    try:
        grade = asyncio.run(run_benchmark())
        print(f"\n🎯 Final Grade: {grade}")
        return 0
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())