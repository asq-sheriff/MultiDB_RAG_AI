"""
Performance Benchmark Tests for MultiDB Chatbot Services

These tests measure and validate performance characteristics of key services,
ensuring they meet SLA requirements and detecting performance regressions.
"""

import asyncio
import statistics
import time
from typing import Dict, List, Any
import pytest
import httpx
from dataclasses import dataclass
import concurrent.futures
import numpy as np

# Test Configuration
API_GATEWAY_URL = "http://localhost:8000"
CONTENT_SAFETY_URL = "http://localhost:8007" 
EMBEDDING_SERVICE_URL = "http://localhost:8005"
GENERATION_SERVICE_URL = "http://localhost:8006"

@dataclass
class PerformanceMetrics:
    """Performance metrics for a test run."""
    min_time: float
    max_time: float  
    mean_time: float
    median_time: float
    p95_time: float
    p99_time: float
    throughput_per_sec: float
    success_rate: float
    total_requests: int
    failed_requests: int

@dataclass
class ServiceBenchmark:
    """Benchmark configuration for a service."""
    name: str
    url: str
    payload: Dict[str, Any]
    expected_max_response_time: float  # SLA target in seconds
    expected_min_throughput: float    # Minimum requests/sec
    concurrency_levels: List[int]     # Concurrency to test


class TestServiceBenchmarks:
    """Comprehensive service performance benchmarks."""

    # Service benchmark configurations
    BENCHMARKS = [
        ServiceBenchmark(
            name="Safety Analysis (Simple Content)",
            url=f"{CONTENT_SAFETY_URL}/safety/analyze",
            payload={
                "content": "Hello, how are you today?",
                "user_id": "perf-test-user",
                "session_id": "perf-session"
            },
            expected_max_response_time=1.0,  # Should be fast with caching
            expected_min_throughput=5.0,    # 5 requests/second minimum
            concurrency_levels=[1, 5, 10]
        ),
        ServiceBenchmark(
            name="Safety Analysis (Complex Content)",
            url=f"{CONTENT_SAFETY_URL}/safety/analyze",
            payload={
                "content": "I'm having severe chest pain and trouble breathing, this feels like an emergency",
                "user_id": "perf-test-user-complex",
                "session_id": "perf-session-complex"
            },
            expected_max_response_time=2.0,  # Complex analysis
            expected_min_throughput=2.0,    # 2 requests/second minimum
            concurrency_levels=[1, 3, 5]
        ),
        ServiceBenchmark(
            name="Emotion Analysis",
            url=f"{CONTENT_SAFETY_URL}/emotion/analyze",
            payload={
                "content": "I'm feeling quite anxious about my upcoming medical appointment",
                "user_id": "perf-emotion-user",
                "session_id": "perf-emotion-session"
            },
            expected_max_response_time=1.5,
            expected_min_throughput=3.0,
            concurrency_levels=[1, 5, 10]
        ),
        ServiceBenchmark(
            name="Embedding Generation",
            url=f"{EMBEDDING_SERVICE_URL}/embeddings",
            payload={
                "texts": ["This is a performance test for embedding generation"]
            },
            expected_max_response_time=0.8,
            expected_min_throughput=8.0,
            concurrency_levels=[1, 10, 20]
        ),
        ServiceBenchmark(
            name="Combined Safety+Emotion Analysis",
            url=f"{CONTENT_SAFETY_URL}/combined/analyze",
            payload={
                "content": "I'm worried about my health and feeling stressed about everything",
                "user_id": "perf-combined-user",
                "session_id": "perf-combined-session"
            },
            expected_max_response_time=3.0,  # Both analyses combined
            expected_min_throughput=1.5,
            concurrency_levels=[1, 3, 5]
        )
    ]

    @pytest.mark.asyncio
    async def test_service_health_before_benchmarks(self):
        """Ensure all services are healthy before running performance tests."""
        services = [
            (CONTENT_SAFETY_URL, "Content Safety Service"),
            (EMBEDDING_SERVICE_URL, "Embedding Service"), 
            (GENERATION_SERVICE_URL, "Generation Service"),
            (API_GATEWAY_URL, "API Gateway")
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for url, name in services:
                try:
                    response = await client.get(f"{url}/health")
                    assert response.status_code == 200, f"{name} health check failed"
                    print(f"✅ {name} is healthy")
                except Exception as e:
                    pytest.fail(f"❌ {name} health check failed: {e}")

    @pytest.mark.asyncio
    async def test_single_request_latency_benchmarks(self):
        """Test single request latency for each service."""
        print("\n" + "="*60)
        print("🚀 SINGLE REQUEST LATENCY BENCHMARKS")
        print("="*60)
        
        for benchmark in self.BENCHMARKS:
            print(f"\n📊 Testing: {benchmark.name}")
            
            # Perform 10 single requests to measure latency distribution
            latencies = []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i in range(10):
                    start_time = time.time()
                    try:
                        response = await client.post(benchmark.url, json=benchmark.payload)
                        end_time = time.time()
                        
                        assert response.status_code == 200, f"Request failed with {response.status_code}"
                        latency = end_time - start_time
                        latencies.append(latency)
                        
                    except Exception as e:
                        print(f"❌ Request {i+1} failed: {e}")
                        pytest.fail(f"Single request test failed for {benchmark.name}")
            
            # Calculate metrics
            metrics = self._calculate_metrics(latencies, len(latencies), 0)
            
            # Print results
            print(f"   Min: {metrics.min_time:.3f}s")
            print(f"   Max: {metrics.max_time:.3f}s") 
            print(f"   Mean: {metrics.mean_time:.3f}s")
            print(f"   Median: {metrics.median_time:.3f}s")
            print(f"   P95: {metrics.p95_time:.3f}s")
            print(f"   P99: {metrics.p99_time:.3f}s")
            
            # Validate SLA
            if metrics.p95_time <= benchmark.expected_max_response_time:
                print(f"   ✅ SLA Met: P95 {metrics.p95_time:.3f}s <= {benchmark.expected_max_response_time}s")
            else:
                print(f"   ❌ SLA Violation: P95 {metrics.p95_time:.3f}s > {benchmark.expected_max_response_time}s")
                pytest.fail(f"SLA violation for {benchmark.name}: P95 latency too high")

    @pytest.mark.asyncio
    async def test_throughput_benchmarks(self):
        """Test throughput at different concurrency levels."""
        print("\n" + "="*60)
        print("🔥 THROUGHPUT BENCHMARKS")
        print("="*60)
        
        for benchmark in self.BENCHMARKS:
            print(f"\n📈 Testing: {benchmark.name}")
            
            for concurrency in benchmark.concurrency_levels:
                print(f"   Concurrency: {concurrency}")
                
                # Run concurrent requests
                start_time = time.time()
                results = await self._run_concurrent_requests(
                    benchmark.url, benchmark.payload, concurrency, 30  # 30 requests total
                )
                total_time = time.time() - start_time
                
                successful_requests = len([r for r in results if r['success']])
                failed_requests = len(results) - successful_requests
                
                if successful_requests > 0:
                    latencies = [r['latency'] for r in results if r['success']]
                    metrics = self._calculate_metrics(latencies, successful_requests, failed_requests)
                    metrics.throughput_per_sec = successful_requests / total_time
                    
                    print(f"     Throughput: {metrics.throughput_per_sec:.2f} req/s")
                    print(f"     Success Rate: {metrics.success_rate:.1%}")
                    print(f"     Mean Latency: {metrics.mean_time:.3f}s")
                    print(f"     P95 Latency: {metrics.p95_time:.3f}s")
                    
                    # Validate throughput SLA
                    if metrics.throughput_per_sec >= benchmark.expected_min_throughput:
                        print(f"     ✅ Throughput SLA Met: {metrics.throughput_per_sec:.2f} >= {benchmark.expected_min_throughput} req/s")
                    else:
                        print(f"     ⚠️ Throughput Below Target: {metrics.throughput_per_sec:.2f} < {benchmark.expected_min_throughput} req/s")
                else:
                    print(f"     ❌ All requests failed at concurrency {concurrency}")

    @pytest.mark.asyncio
    async def test_cache_performance_validation(self):
        """Validate caching performance improvements."""
        print("\n" + "="*60)
        print("💾 CACHE PERFORMANCE VALIDATION")
        print("="*60)
        
        cache_test_content = "This is a cache performance test message for validation"
        payload = {
            "content": cache_test_content,
            "user_id": "cache-perf-user",
            "session_id": "cache-perf-session"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First request (cache miss)
            print("🔥 First request (cache miss):")
            start_time = time.time()
            response1 = await client.post(f"{CONTENT_SAFETY_URL}/safety/analyze", json=payload)
            first_request_time = time.time() - start_time
            
            assert response1.status_code == 200
            print(f"   Time: {first_request_time:.3f}s")
            
            # Second request (cache hit)
            print("⚡ Second request (cache hit):")
            start_time = time.time()
            response2 = await client.post(f"{CONTENT_SAFETY_URL}/safety/analyze", json=payload)
            second_request_time = time.time() - start_time
            
            assert response2.status_code == 200
            print(f"   Time: {second_request_time:.3f}s")
            
            # Calculate speedup
            speedup = first_request_time / second_request_time if second_request_time > 0 else 0
            print(f"🚀 Cache Speedup: {speedup:.1f}x faster")
            
            # Validate significant speedup (should be at least 10x faster)
            assert speedup >= 10.0, f"Cache speedup insufficient: {speedup:.1f}x < 10x"
            print("   ✅ Cache performance validation passed!")

    @pytest.mark.asyncio  
    async def test_load_stress_test(self):
        """Stress test with sustained load."""
        print("\n" + "="*60)
        print("🔥 LOAD STRESS TEST")
        print("="*60)
        
        # Use the simplest endpoint for stress testing
        stress_payload = {
            "content": "Stress test message",
            "user_id": "stress-user",
            "session_id": "stress-session"
        }
        
        print("Running 2-minute stress test with 5 concurrent requests...")
        
        start_time = time.time()
        total_requests = 0
        successful_requests = 0
        error_count = 0
        
        # Run for 2 minutes
        while time.time() - start_time < 120:  # 2 minutes
            batch_results = await self._run_concurrent_requests(
                f"{CONTENT_SAFETY_URL}/safety/analyze", 
                stress_payload, 
                concurrency=5, 
                total_requests=20
            )
            
            batch_successful = len([r for r in batch_results if r['success']])
            batch_failed = len(batch_results) - batch_successful
            
            total_requests += len(batch_results)
            successful_requests += batch_successful
            error_count += batch_failed
            
            # Brief pause between batches
            await asyncio.sleep(1)
        
        total_time = time.time() - start_time
        
        print(f"📊 Stress Test Results:")
        print(f"   Duration: {total_time:.1f}s")
        print(f"   Total Requests: {total_requests}")
        print(f"   Successful: {successful_requests}")
        print(f"   Failed: {error_count}")
        print(f"   Success Rate: {successful_requests/total_requests*100:.1f}%")
        print(f"   Average Throughput: {successful_requests/total_time:.2f} req/s")
        
        # Validate stress test results
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        assert success_rate >= 0.95, f"Stress test success rate too low: {success_rate:.1%} < 95%"
        print("   ✅ Stress test passed!")

    async def _run_concurrent_requests(self, url: str, payload: Dict[str, Any], concurrency: int, total_requests: int) -> List[Dict[str, Any]]:
        """Run concurrent requests and return results."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def make_request(client: httpx.AsyncClient) -> Dict[str, Any]:
            async with semaphore:
                start_time = time.time()
                try:
                    response = await client.post(url, json=payload)
                    end_time = time.time()
                    return {
                        'success': response.status_code == 200,
                        'latency': end_time - start_time,
                        'status_code': response.status_code
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'latency': 0,
                        'error': str(e)
                    }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [make_request(client) for _ in range(total_requests)]
            results = await asyncio.gather(*tasks)
            
        return results

    def _calculate_metrics(self, latencies: List[float], successful_requests: int, failed_requests: int) -> PerformanceMetrics:
        """Calculate performance metrics from latency data."""
        if not latencies:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, failed_requests)
        
        return PerformanceMetrics(
            min_time=min(latencies),
            max_time=max(latencies),
            mean_time=statistics.mean(latencies),
            median_time=statistics.median(latencies),
            p95_time=np.percentile(latencies, 95),
            p99_time=np.percentile(latencies, 99),
            throughput_per_sec=0,  # Will be calculated separately
            success_rate=successful_requests / (successful_requests + failed_requests) if (successful_requests + failed_requests) > 0 else 0,
            total_requests=successful_requests + failed_requests,
            failed_requests=failed_requests
        )

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self):
        """Detect performance regressions by comparing to baseline."""
        print("\n" + "="*60)
        print("🔍 PERFORMANCE REGRESSION DETECTION")
        print("="*60)
        
        # Simple baseline test - should be very fast with caching
        baseline_content = "Simple baseline performance test"
        payload = {
            "content": baseline_content,
            "user_id": "regression-user", 
            "session_id": "regression-session"
        }
        
        # Prime the cache
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(f"{CONTENT_SAFETY_URL}/safety/analyze", json=payload)
            
            # Measure cached performance
            latencies = []
            for _ in range(20):
                start_time = time.time()
                response = await client.post(f"{CONTENT_SAFETY_URL}/safety/analyze", json=payload)
                latency = time.time() - start_time
                assert response.status_code == 200
                latencies.append(latency)
        
        mean_latency = statistics.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        
        print(f"📊 Baseline Performance (Cached):")
        print(f"   Mean Latency: {mean_latency:.3f}s")
        print(f"   P95 Latency: {p95_latency:.3f}s")
        
        # Regression thresholds (should be very fast with caching)
        assert mean_latency < 0.1, f"Regression detected: Mean latency {mean_latency:.3f}s > 0.1s"
        assert p95_latency < 0.2, f"Regression detected: P95 latency {p95_latency:.3f}s > 0.2s"
        
        print("   ✅ No performance regression detected!")


if __name__ == "__main__":
    # Run specific benchmark manually
    import asyncio
    
    async def run_quick_benchmark():
        test_instance = TestServiceBenchmarks()
        await test_instance.test_service_health_before_benchmarks()
        await test_instance.test_cache_performance_validation()
    
    asyncio.run(run_quick_benchmark())