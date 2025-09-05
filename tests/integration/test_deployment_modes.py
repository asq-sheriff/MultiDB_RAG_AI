"""
End-to-end integration tests for both local and Docker deployment modes.

Tests the unified configuration system across different deployment scenarios:
1. Local development (hybrid: Docker databases + local services)  
2. Full Docker containerization
3. Service-to-service communication in both modes
4. ML model loading and performance in both environments
"""

import asyncio
import pytest
import httpx
import docker
import subprocess
import time
import json
import os
import signal
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Configuration for different deployment modes."""
    mode: str
    api_gateway_url: str
    embedding_service_url: str
    search_service_url: str
    generation_service_url: str
    expected_environment_flags: Dict[str, bool]


class DeploymentTester:
    """Comprehensive deployment testing framework."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.local_processes: List[subprocess.Popen] = []
        self.test_results: Dict[str, Dict] = {}
        
        # Deployment configurations
        self.configs = {
            "local": DeploymentConfig(
                mode="local",
                api_gateway_url="http://localhost:8000",
                embedding_service_url="http://localhost:8002", 
                search_service_url="http://localhost:8001",
                generation_service_url="http://localhost:8003",
                expected_environment_flags={
                    "is_container": False,
                    "is_m1_mac": True  # Assuming M1 Mac for local testing
                }
            ),
            "docker": DeploymentConfig(
                mode="docker",
                api_gateway_url="http://localhost:8000",
                embedding_service_url="http://localhost:8002",
                search_service_url="http://localhost:8001", 
                generation_service_url="http://localhost:8003",
                expected_environment_flags={
                    "is_container": True,
                    "is_m1_mac": False
                }
            )
        }
    
    async def test_service_health(self, config: DeploymentConfig) -> Dict[str, bool]:
        """Test health endpoints for all services."""
        health_results = {}
        services = {
            "api_gateway": f"{config.api_gateway_url}/health",
            "embedding_service": f"{config.embedding_service_url}/health",
            "search_service": f"{config.search_service_url}/health",
            "generation_service": f"{config.generation_service_url}/health"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for service, url in services.items():
                try:
                    logger.info(f"Testing {service} health at {url}")
                    response = await client.get(url)
                    health_results[service] = {
                        "healthy": response.status_code == 200,
                        "response": response.json() if response.status_code == 200 else None,
                        "status_code": response.status_code
                    }
                except Exception as e:
                    logger.error(f"Health check failed for {service}: {e}")
                    health_results[service] = {
                        "healthy": False,
                        "error": str(e),
                        "status_code": None
                    }
        
        return health_results
    
    async def test_environment_detection(self, config: DeploymentConfig) -> Dict[str, Dict]:
        """Test that services correctly detect their deployment environment."""
        env_results = {}
        
        # Test embedding service environment detection
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{config.embedding_service_url}/info")
                if response.status_code == 200:
                    info = response.json()
                    env_results["embedding_service"] = {
                        "detected_correctly": True,
                        "environment": info.get("environment", {}),
                        "configuration": info.get("configuration", {})
                    }
                    
                    # Validate environment flags
                    env_flags = info.get("environment", {})
                    for flag, expected in config.expected_environment_flags.items():
                        actual = env_flags.get(flag)
                        if actual != expected:
                            env_results["embedding_service"]["detected_correctly"] = False
                            env_results["embedding_service"]["flag_mismatch"] = {
                                flag: {"expected": expected, "actual": actual}
                            }
            except Exception as e:
                env_results["embedding_service"] = {"error": str(e), "detected_correctly": False}
        
        return env_results
    
    async def test_embedding_functionality(self, config: DeploymentConfig) -> Dict[str, any]:
        """Test embedding generation in different environments."""
        test_texts = [
            "Healthcare patient management system",
            "Medical record processing workflow", 
            "Clinical decision support tools"
        ]
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Test batch embeddings
                batch_response = await client.post(
                    f"{config.embedding_service_url}/embeddings",
                    json={"texts": test_texts}
                )
                
                # Test single embedding
                single_response = await client.post(
                    f"{config.embedding_service_url}/embedding",
                    json={"text": test_texts[0]}
                )
                
                # Test cache stats
                cache_response = await client.get(f"{config.embedding_service_url}/cache/stats")
                
                return {
                    "batch_embeddings": {
                        "success": batch_response.status_code == 200,
                        "response": batch_response.json() if batch_response.status_code == 200 else None,
                        "embedding_count": len(batch_response.json().get("embeddings", [])) if batch_response.status_code == 200 else 0
                    },
                    "single_embedding": {
                        "success": single_response.status_code == 200,
                        "embedding_dimension": len(single_response.json()) if single_response.status_code == 200 else 0
                    },
                    "cache_stats": {
                        "success": cache_response.status_code == 200,
                        "stats": cache_response.json() if cache_response.status_code == 200 else None
                    }
                }
            except Exception as e:
                return {"error": str(e), "success": False}
    
    async def test_end_to_end_workflow(self, config: DeploymentConfig) -> Dict[str, any]:
        """Test complete end-to-end workflow through API Gateway."""
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                # Test document processing
                doc_response = await client.get(f"{config.api_gateway_url}/dev/test-document-processing")
                
                # Test admin seeding status
                admin_response = await client.get(f"{config.api_gateway_url}/admin/seed-status")
                
                # Test API Gateway health with environment info
                health_response = await client.get(f"{config.api_gateway_url}/health")
                
                return {
                    "document_processing": {
                        "success": doc_response.status_code == 200,
                        "response": doc_response.json() if doc_response.status_code == 200 else None
                    },
                    "admin_endpoints": {
                        "success": admin_response.status_code == 200,
                        "response": admin_response.json() if admin_response.status_code == 200 else None
                    },
                    "api_gateway_health": {
                        "success": health_response.status_code == 200,
                        "response": health_response.json() if health_response.status_code == 200 else None
                    }
                }
            except Exception as e:
                return {"error": str(e), "success": False}
    
    async def test_database_connectivity(self, config: DeploymentConfig) -> Dict[str, bool]:
        """Test database connections through services."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test through admin endpoints which hit databases
                admin_response = await client.get(f"{config.api_gateway_url}/admin/seed-status")
                
                if admin_response.status_code == 200:
                    admin_data = admin_response.json()
                    return {
                        "mongodb_connected": admin_data.get("mongodb", {}).get("connected", False),
                        "overall_status": admin_data.get("overall_status") != "error",
                        "response_received": True
                    }
                else:
                    return {"response_received": False, "status_code": admin_response.status_code}
            except Exception as e:
                return {"error": str(e), "response_received": False}
    
    def start_local_services(self) -> bool:
        """Start services locally for testing."""
        logger.info("🚀 Starting local services...")
        
        # Ensure databases are running
        if not self._ensure_databases_running():
            return False
        
        services = [
            {
                "name": "embedding-service",
                "cmd": ["python", "-m", "uvicorn", "services.embedding_service.main:app", 
                       "--host", "0.0.0.0", "--port", "8002"],
                "port": 8002
            },
            {
                "name": "search-service", 
                "cmd": ["python", "-m", "uvicorn", "services.search_service.main:app",
                       "--host", "0.0.0.0", "--port", "8001"],
                "port": 8001
            },
            {
                "name": "generation-service",
                "cmd": ["python", "-m", "uvicorn", "services.generation_service.main:app",
                       "--host", "0.0.0.0", "--port", "8003"], 
                "port": 8003
            },
            {
                "name": "api-gateway",
                "cmd": ["python", "-m", "uvicorn", "services.api_gateway.main:app",
                       "--host", "0.0.0.0", "--port", "8000"],
                "port": 8000
            }
        ]
        
        for service in services:
            try:
                logger.info(f"Starting {service['name']}...")
                process = subprocess.Popen(
                    service["cmd"],
                    env={**os.environ, "PYTHONPATH": str(Path.cwd())},
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.local_processes.append(process)
                
                # Wait for service to start
                if not self._wait_for_service(service["port"]):
                    logger.error(f"Failed to start {service['name']}")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to start {service['name']}: {e}")
                return False
        
        logger.info("✅ All local services started")
        return True
    
    def start_docker_services(self) -> bool:
        """Start services in Docker containers."""
        logger.info("🐳 Starting Docker services...")
        
        try:
            # Use docker-compose to start all services
            result = subprocess.run([
                "docker-compose", "-f", "docker-compose.all-services.yml", 
                "up", "--build", "-d"
            ], cwd=Path.cwd(), capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"Docker compose failed: {result.stderr}")
                return False
            
            # Wait for services to be healthy
            services_ports = [8000, 8001, 8002, 8003]
            for port in services_ports:
                if not self._wait_for_service(port, timeout=180):
                    logger.error(f"Service on port {port} failed to start")
                    return False
            
            logger.info("✅ All Docker services started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Docker services: {e}")
            return False
    
    def _ensure_databases_running(self) -> bool:
        """Ensure database containers are running."""
        try:
            result = subprocess.run([
                "docker-compose", "up", "-d", 
                "postgres", "redis", "mongodb", "scylla-node1", "scylla-node2", "scylla-node3"
            ], cwd=Path.cwd(), capture_output=True, text=True, timeout=120)
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to ensure databases: {e}")
            return False
    
    def _wait_for_service(self, port: int, timeout: int = 60) -> bool:
        """Wait for a service to be available on given port."""
        import socket
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection(("localhost", port), timeout=1):
                    return True
            except (socket.error, ConnectionRefusedError):
                time.sleep(2)
        return False
    
    def stop_local_services(self):
        """Stop all local service processes."""
        logger.info("🛑 Stopping local services...")
        for process in self.local_processes:
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        self.local_processes.clear()
    
    def stop_docker_services(self):
        """Stop Docker services."""
        logger.info("🛑 Stopping Docker services...")
        try:
            subprocess.run([
                "docker-compose", "-f", "docker-compose.all-services.yml", "down"
            ], cwd=Path.cwd(), timeout=60)
        except Exception as e:
            logger.error(f"Failed to stop Docker services: {e}")
    
    async def run_comprehensive_test(self, deployment_mode: str) -> Dict[str, any]:
        """Run comprehensive tests for a deployment mode."""
        config = self.configs[deployment_mode]
        logger.info(f"🧪 Running comprehensive tests for {deployment_mode} deployment...")
        
        # Start services based on deployment mode
        if deployment_mode == "local":
            if not self.start_local_services():
                return {"success": False, "error": "Failed to start local services"}
        else:
            if not self.start_docker_services():
                return {"success": False, "error": "Failed to start Docker services"}
        
        try:
            # Wait for services to stabilize
            await asyncio.sleep(10)
            
            # Run all tests
            results = {
                "deployment_mode": deployment_mode,
                "health_checks": await self.test_service_health(config),
                "environment_detection": await self.test_environment_detection(config),
                "embedding_functionality": await self.test_embedding_functionality(config),
                "end_to_end_workflow": await self.test_end_to_end_workflow(config),
                "database_connectivity": await self.test_database_connectivity(config)
            }
            
            # Calculate overall success
            results["overall_success"] = self._calculate_overall_success(results)
            
            return results
            
        finally:
            # Cleanup
            if deployment_mode == "local":
                self.stop_local_services()
            else:
                self.stop_docker_services()
    
    def _calculate_overall_success(self, results: Dict) -> bool:
        """Calculate overall success based on test results."""
        # Check health checks
        health_success = all(
            service.get("healthy", False) 
            for service in results.get("health_checks", {}).values()
        )
        
        # Check environment detection
        env_success = all(
            service.get("detected_correctly", False)
            for service in results.get("environment_detection", {}).values()
        )
        
        # Check embedding functionality
        embedding_success = results.get("embedding_functionality", {}).get("batch_embeddings", {}).get("success", False)
        
        # Check end-to-end workflow
        e2e_success = results.get("end_to_end_workflow", {}).get("document_processing", {}).get("success", False)
        
        return health_success and env_success and embedding_success and e2e_success
    
    def generate_test_report(self, results: Dict[str, Dict]) -> str:
        """Generate a comprehensive test report."""
        report = [
            "=" * 80,
            "🧪 MULTIDB CHATBOT - DEPLOYMENT INTEGRATION TEST REPORT",
            "=" * 80,
            "",
        ]
        
        for mode, result in results.items():
            report.extend([
                f"📋 {mode.upper()} DEPLOYMENT TEST RESULTS",
                "-" * 50,
                f"Overall Success: {'✅ PASS' if result.get('overall_success') else '❌ FAIL'}",
                ""
            ])
            
            # Health checks
            health = result.get("health_checks", {})
            report.append("🏥 Health Check Results:")
            for service, status in health.items():
                healthy = status.get("healthy", False)
                report.append(f"  {service}: {'✅' if healthy else '❌'} {status.get('status_code', 'N/A')}")
            report.append("")
            
            # Environment detection
            env = result.get("environment_detection", {})
            report.append("🔍 Environment Detection:")
            for service, detection in env.items():
                detected = detection.get("detected_correctly", False)
                report.append(f"  {service}: {'✅' if detected else '❌'}")
                if not detected and "flag_mismatch" in detection:
                    mismatch = detection["flag_mismatch"]
                    for flag, values in mismatch.items():
                        report.append(f"    {flag}: expected {values['expected']}, got {values['actual']}")
            report.append("")
            
            # Embedding functionality
            embedding = result.get("embedding_functionality", {})
            report.append("🤖 Embedding Functionality:")
            batch_success = embedding.get("batch_embeddings", {}).get("success", False)
            single_success = embedding.get("single_embedding", {}).get("success", False)
            cache_success = embedding.get("cache_stats", {}).get("success", False)
            report.extend([
                f"  Batch Embeddings: {'✅' if batch_success else '❌'}",
                f"  Single Embedding: {'✅' if single_success else '❌'}",
                f"  Cache Integration: {'✅' if cache_success else '❌'}",
                ""
            ])
            
            # End-to-end workflow
            e2e = result.get("end_to_end_workflow", {})
            report.append("🔄 End-to-End Workflow:")
            doc_success = e2e.get("document_processing", {}).get("success", False)
            admin_success = e2e.get("admin_endpoints", {}).get("success", False)
            gateway_success = e2e.get("api_gateway_health", {}).get("success", False)
            report.extend([
                f"  Document Processing: {'✅' if doc_success else '❌'}",
                f"  Admin Endpoints: {'✅' if admin_success else '❌'}",
                f"  API Gateway: {'✅' if gateway_success else '❌'}",
                ""
            ])
            
            # Database connectivity
            db = result.get("database_connectivity", {})
            report.append("🗄️ Database Connectivity:")
            mongo_connected = db.get("mongodb_connected", False)
            overall_status = db.get("overall_status", False)
            report.extend([
                f"  MongoDB: {'✅' if mongo_connected else '❌'}",
                f"  Overall Status: {'✅' if overall_status else '❌'}",
                ""
            ])
        
        report.extend([
            "=" * 80,
            "🎯 SUMMARY",
            "=" * 80,
            ""
        ])
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result.get("overall_success"))
        
        report.extend([
            f"Total Deployment Modes Tested: {total_tests}",
            f"Successful Deployments: {passed_tests}",
            f"Success Rate: {(passed_tests/total_tests)*100:.1f}%",
            "",
            f"Final Result: {'🎉 ALL TESTS PASSED' if passed_tests == total_tests else '⚠️ SOME TESTS FAILED'}",
            ""
        ])
        
        return "\n".join(report)


# Test runner
async def main():
    """Main test runner function."""
    tester = DeploymentTester()
    results = {}
    
    try:
        logger.info("🏁 Starting comprehensive deployment integration tests...")
        
        # Test local deployment
        logger.info("\n" + "="*60)
        logger.info("TESTING LOCAL DEPLOYMENT (Hybrid Mode)")
        logger.info("="*60)
        results["local"] = await tester.run_comprehensive_test("local")
        
        # Wait between tests
        await asyncio.sleep(5)
        
        # Test Docker deployment
        logger.info("\n" + "="*60) 
        logger.info("TESTING DOCKER DEPLOYMENT (Full Container Mode)")
        logger.info("="*60)
        results["docker"] = await tester.run_comprehensive_test("docker")
        
        # Generate and display report
        report = tester.generate_test_report(results)
        print("\n" + report)
        
        # Save report to file
        report_file = Path("test_results_deployment_integration.txt")
        with open(report_file, "w") as f:
            f.write(report)
        
        logger.info(f"📄 Test report saved to: {report_file}")
        
        # Return success status
        overall_success = all(result.get("overall_success", False) for result in results.values())
        return overall_success
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        return False
    finally:
        # Ensure cleanup
        tester.stop_local_services()
        tester.stop_docker_services()


if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)