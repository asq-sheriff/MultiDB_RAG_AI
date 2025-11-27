"""
Enhanced FastAPI Application with Real AI Services Integration
===============================================================
Location: app/api/main.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import importlib
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Enhanced database connections
from app.database.mongo_connection import (
    init_enhanced_mongo,
    close_enhanced_mongo,
    enhanced_mongo_manager,
)

from app.core.auth_dependencies import get_admin_user
from app.database.postgres_models import User

# Configure logging early
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global startup time for performance tracking
startup_time = time.time()
app_state = {
    "services_initialized": False,
    "startup_errors": [],
    "initialization_time": 0.0,
}


async def _safe_initialize_postgresql() -> bool:
    """Safely initialize PostgreSQL with comprehensive error handling"""
    try:
        logger.info("🐘 Phase 1.5: Initializing PostgreSQL...")

        # Import PostgreSQL components
        from app.database.postgres_connection import postgres_manager
        from app.database.postgres_models import DatabaseBase
        from app.config import config

        if not config.enable_postgresql:
            logger.info("📝 PostgreSQL disabled in configuration")
            return False

        # Initialize PostgreSQL connection
        await postgres_manager.initialize()

        # Test connection
        connection_ok = await postgres_manager.test_connection()
        if not connection_ok:
            logger.error("❌ PostgreSQL connection test failed")
            return False

        # Create tables if they don't exist
        logger.info("📋 Creating PostgreSQL tables...")
        async with postgres_manager.engine.begin() as conn:
            await conn.run_sync(DatabaseBase.metadata.create_all)

        logger.info("✅ PostgreSQL initialized successfully")
        logger.info(f"   Host: {config.postgresql.host}:{config.postgresql.port}")
        logger.info(f"   Database: {config.postgresql.database}")

        return True

    except Exception as e:
        logger.error(f"❌ PostgreSQL initialization failed: {e}")
        app_state["startup_errors"].append(f"PostgreSQL initialization failed: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events."""
    logger.info("🚀 Starting application...")

    # Import managers and services inside the lifespan to ensure deferred initialization
    from app.database.postgres_connection import postgres_manager
    from app.database.redis_connection import redis_manager
    from app.dependencies import get_embedding_service, get_generation_service
    from app.config import config

    # --- Connect to Databases and Caches on STARTUP ---
    await postgres_manager.initialize()
    await init_enhanced_mongo()
    redis_manager.initialize()

    # --- Pre-load AI models to avoid cold starts ---
    if config.use_real_embeddings:
        await get_embedding_service().warmup()
    if config.use_real_generation:
        await get_generation_service().warmup()

    logger.info("🎉 Application startup complete.")
    yield

    # --- Disconnect from Databases and Caches on SHUTDOWN ---
    logger.info("🛑 Shutting down application...")
    await postgres_manager.close()
    await close_enhanced_mongo()
    redis_manager.close()
    logger.info("👋 Application shutdown complete.")


async def _safe_initialize_ai_services() -> Dict[str, Any]:
    """Safely initialize AI services with comprehensive error handling"""
    status = {
        "embedding_service": False,
        "generation_service": False,
        "knowledge_service": False,
        "chatbot_service": False,
        "any_services_available": False,
        "errors": [],
    }

    # Try to initialize embedding service
    try:
        from app.dependencies import embedding_service

        if embedding_service is not None:
            status["embedding_service"] = True
            logger.info("✅ EmbeddingService available")
        else:
            status["errors"].append("EmbeddingService not initialized")
            logger.warning("⚠️ EmbeddingService not available")
    except Exception as e:
        status["errors"].append(f"EmbeddingService error: {e}")
        logger.warning(f"⚠️ EmbeddingService initialization error: {e}")

    # Try to initialize generation service
    try:
        from app.dependencies import generation_service

        if generation_service is not None:
            status["generation_service"] = True
            logger.info("✅ GenerationService available")
        else:
            status["errors"].append("GenerationService not initialized")
            logger.warning("⚠️ GenerationService not available")
    except Exception as e:
        status["errors"].append(f"GenerationService error: {e}")
        logger.warning(f"⚠️ GenerationService initialization error: {e}")

    # Try to initialize knowledge service
    try:
        from app.dependencies import knowledge_service

        if knowledge_service is not None:
            status["knowledge_service"] = True
            logger.info("✅ KnowledgeService available")
        else:
            status["errors"].append("KnowledgeService not initialized")
            logger.warning("⚠️ KnowledgeService not available")
    except Exception as e:
        status["errors"].append(f"KnowledgeService error: {e}")
        logger.warning(f"⚠️ KnowledgeService initialization error: {e}")

    # Try to initialize chatbot service
    try:
        from app.dependencies import chatbot_service

        if chatbot_service is not None:
            status["chatbot_service"] = True
            logger.info("✅ ChatbotService available")
        else:
            status["errors"].append("ChatbotService not initialized")
            logger.warning("⚠️ ChatbotService not available")
    except Exception as e:
        status["errors"].append(f"ChatbotService error: {e}")
        logger.warning(f"⚠️ ChatbotService initialization error: {e}")

    # Determine if any services are available
    status["any_services_available"] = any(
        [
            status["embedding_service"],
            status["generation_service"],
            status["knowledge_service"],
            status["chatbot_service"],
        ]
    )

    return status


async def _safe_warmup_services() -> bool:
    """Safely warmup AI services with timeout and error handling"""
    try:
        # Import with error handling
        try:
            from app.dependencies import comprehensive_warmup
        except ImportError:
            logger.warning("⚠️ Comprehensive warmup not available")
            return False

        # Run warmup with timeout
        warmup_task = asyncio.create_task(comprehensive_warmup())

        try:
            warmup_results = await asyncio.wait_for(
                warmup_task, timeout=120.0
            )  # 2 minute timeout

            success_rate = warmup_results.get("overall", {}).get("success_rate", 0)
            production_ready = warmup_results.get("overall", {}).get(
                "production_ready", False
            )

            logger.info(
                f"🔥 AI service warmup completed: {success_rate:.1%} success rate"
            )

            # Log telemetry if available
            try:
                from app.dependencies import enhanced_telemetry

                enhanced_telemetry(
                    "app_startup_success",
                    {
                        "startup_time_seconds": time.time() - startup_time,
                        "success_rate": success_rate,
                        "production_ready": production_ready,
                    },
                )
            except Exception:
                pass  # Telemetry is optional

            return success_rate > 0.5  # Consider successful if >50% services work

        except asyncio.TimeoutError:
            logger.warning("⏰ AI service warmup timed out, continuing without warmup")
            warmup_task.cancel()
            return False

    except Exception as e:
        logger.error(f"❌ AI service warmup failed: {e}")
        return False


async def _safe_auto_seed() -> bool:
    """Safely run auto-seeding with error handling"""
    try:
        logger.info("🌱 Starting auto-seeding...")

        # Try enhanced seeding first
        try:
            from app.utils.seed_data import main_advanced_seeding

            # Set conservative settings for startup seeding
            os.environ["SEED_DRY_RUN"] = "0"
            os.environ["SEED_MAX_WORKERS"] = "2"
            os.environ["SEED_BATCH_SIZE"] = "8"

            result = await main_advanced_seeding()

            if result.get("status") == "completed":
                logger.info("✅ Enhanced auto-seeding completed successfully")
                return True
            else:
                logger.warning("⚠️ Enhanced auto-seeding completed with issues")
                return False

        except ImportError:
            logger.info("📄 Enhanced seeding not available, trying standard seeding...")
            try:
                from app.utils import seed_knowledge_base

                seed_knowledge_base(use_enhanced=False)
                logger.info("✅ Standard auto-seeding completed")
                return True
            except Exception as e:
                logger.error(f"❌ Standard seeding failed: {e}")
                return False

    except Exception as e:
        logger.error(f"❌ Auto-seeding failed: {e}")
        return False
    finally:
        # Clean up environment variables
        os.environ.pop("SEED_DRY_RUN", None)
        os.environ.pop("SEED_MAX_WORKERS", None)
        os.environ.pop("SEED_BATCH_SIZE", None)


async def _safe_cleanup_services() -> None:
    """Safely cleanup services"""
    try:
        from app.dependencies import cleanup_enhanced_services

        await cleanup_enhanced_services()
    except Exception as e:
        logger.error(f"Service cleanup error: {e}")


async def _log_service_status() -> None:
    """Log final service status with proper async handling"""
    try:
        from app.dependencies import (
            embedding_service,
            generation_service,
            knowledge_service,
            chatbot_service,
            enhanced_mongo_manager,
        )

        ready_services = 0
        total_services = 4

        if embedding_service is not None:
            ready_services += 1
        if generation_service is not None:
            ready_services += 1
        if knowledge_service is not None:
            ready_services += 1
        if chatbot_service is not None:
            ready_services += 1

        logger.info(
            f"📊 Final Service Status: {ready_services}/{total_services} services ready"
        )

        # Check vector search availability with proper async handling
        if enhanced_mongo_manager and enhanced_mongo_manager.is_connected:
            try:
                health = await enhanced_mongo_manager.health_check()
                if health.get("vector_search_available"):
                    logger.info("🔍 Atlas Vector Search available")
                else:
                    logger.info("🔍 Manual vector search available")
            except Exception as e:
                logger.debug(f"Health check failed: {e}")
                logger.info("🔍 Manual vector search available")
        else:
            logger.warning("⚠️ No vector search available")

    except Exception as e:
        logger.debug(f"Service status logging failed: {e}")
        logger.info("📊 Application started successfully")


# Enhanced FastAPI application
app = FastAPI(
    title="Enhanced AI Chatbot API",
    version="2.0.0",
    description="Production-ready AI chatbot with sentence-transformers/all-mpnet-base-v2, qwen3-1.7b, and Atlas Vector Search",
    lifespan=lifespan,
)

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Enhanced Response Models
# -----------------------------


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    mongo: bool
    ai_services: Dict[str, Any]
    uptime_seconds: float
    startup_errors: Optional[List[str]] = None


class ServiceStatusResponse(BaseModel):
    overall_status: str
    ai_services: Dict[str, Any]
    database: Dict[str, Any]
    performance: Dict[str, Any]
    timestamp: str
    startup_info: Optional[Dict[str, Any]] = None


# -----------------------------
# Enhanced Health Endpoints
# -----------------------------


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """Basic health check with AI service status"""
    try:
        # Test enhanced MongoDB
        mongo_ok = enhanced_mongo_manager.is_connected

        # Get AI service status with error handling
        ai_services_status = {"services_ready": 0, "total_services": 4}
        try:
            from app.dependencies import get_comprehensive_service_status

            service_status = get_comprehensive_service_status()
            ai_services_status = service_status.get("services", ai_services_status)
        except Exception as e:
            logger.debug(f"Service status check failed: {e}")

        ai_ready = ai_services_status.get("services_ready", 0) >= 2
        status = "healthy" if mongo_ok and ai_ready else "degraded"

        # Include startup errors if any
        startup_errors = (
            app_state["startup_errors"] if app_state["startup_errors"] else None
        )

        return HealthResponse(
            status=status,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            mongo=mongo_ok,
            ai_services={
                "embedding_ready": ai_services_status.get("embedding_service", False),
                "generation_ready": ai_services_status.get("generation_service", False),
                "total_ready": ai_services_status.get("services_ready", 0),
                "services_initialized": app_state["services_initialized"],
            },
            uptime_seconds=time.time() - startup_time,
            startup_errors=startup_errors,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="error",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            mongo=False,
            ai_services={"error": str(e)},
            uptime_seconds=time.time() - startup_time,
            startup_errors=app_state["startup_errors"],
        )


@app.get("/health/detailed", response_model=ServiceStatusResponse, tags=["health"])
async def detailed_health() -> ServiceStatusResponse:
    """Comprehensive health check for production monitoring"""
    try:
        # Get comprehensive service status with error handling
        service_status = {}
        try:
            from app.dependencies import get_comprehensive_service_status

            service_status = get_comprehensive_service_status()
        except Exception as e:
            logger.error(f"Service status failed: {e}")
            service_status = {"error": str(e)}

        # Get memory information with error handling
        memory_info = {}
        try:
            from app.dependencies import monitor_ai_service_memory

            memory_info = await monitor_ai_service_memory()
        except Exception as e:
            logger.debug(f"Memory monitoring failed: {e}")
            memory_info = {"error": str(e)}

        # Determine overall status
        services_ready = service_status.get("services", {}).get("services_ready", 0)
        total_services = service_status.get("services", {}).get("total_services", 4)

        if services_ready >= total_services:
            overall_status = "healthy"
        elif services_ready >= total_services // 2:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        # Enhanced MongoDB status
        database_status = service_status.get("database", {})
        database_status["mongo_connected"] = enhanced_mongo_manager.is_connected
        database_status["is_atlas"] = enhanced_mongo_manager.is_atlas

        return ServiceStatusResponse(
            overall_status=overall_status,
            ai_services=service_status.get("services", {}),
            database=database_status,
            performance={
                **service_status.get("performance_metrics", {}),
                "memory_info": memory_info,
                "uptime_seconds": time.time() - startup_time,
            },
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            startup_info={
                "services_initialized": app_state["services_initialized"],
                "initialization_time": app_state["initialization_time"],
                "startup_errors": app_state["startup_errors"],
            },
        )

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@app.get("/health/ai-services", tags=["health"])
async def ai_services_health():
    """Detailed AI service health and performance metrics"""
    try:
        result = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}

        # EmbeddingService status with error handling
        try:
            from app.dependencies import get_embedding_service

            embedding_service = get_embedding_service()
            result["embedding_service"] = {
                "status": "healthy",
                "ready": getattr(embedding_service, "is_ready", False),
                "performance": getattr(embedding_service, "performance_stats", {}),
            }
        except Exception as e:
            result["embedding_service"] = {"status": "unhealthy", "error": str(e)}

        # GenerationService status with error handling
        try:
            from app.dependencies import get_generation_service

            generation_service = get_generation_service()
            result["generation_service"] = {
                "status": "healthy",
                "ready": getattr(generation_service, "is_ready", False),
                "performance": getattr(generation_service, "performance_stats", {}),
            }
        except Exception as e:
            result["generation_service"] = {"status": "unhealthy", "error": str(e)}

        return result

    except Exception as e:
        logger.error(f"AI services health check failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"AI services health check failed: {e}"
        )


@app.get("/health/memory", tags=["health"])
async def memory_health():
    """AI service memory usage monitoring"""
    try:
        try:
            from app.dependencies import monitor_ai_service_memory

            memory_info = await monitor_ai_service_memory()
        except Exception as e:
            memory_info = {"error": str(e), "monitoring_available": False}

        return {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), **memory_info}
    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Memory health check failed: {e}")


@app.get("/health/database", tags=["health"])
async def database_health():
    """Enhanced database health check"""
    try:
        # MongoDB health
        mongo_health = await enhanced_mongo_manager.health_check()

        # ScyllaDB health (basic check)
        scylla_status = "unknown"
        try:
            from app.database.scylla_models import EnhancedConversationHistory

            conv_history = EnhancedConversationHistory()
            scylla_status = (
                "connected"
                if conv_history.connection.is_connected()
                else "disconnected"
            )
        except Exception as e:
            scylla_status = f"error: {e}"

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "mongodb": mongo_health,
            "scylladb": {"status": scylla_status},
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Database health check failed: {e}"
        )


# -----------------------------
# Enhanced Admin Endpoints with Authentication
# -----------------------------


@app.post("/admin/seed-enhanced", tags=["admin"])
async def trigger_enhanced_seeding(
    clear_existing: bool = False,
    migration_mode: bool = False,
    monitor_indexes: bool = True,
    enable_pdf: bool = True,
    enable_docx: bool = True,
    enable_csv: bool = True,
    dry_run: bool = False,
    admin_user: User = Depends(get_admin_user),
):
    """Trigger enhanced seeding pipeline with configurable options"""
    try:
        # Validate that seeding is available
        try:
            from app.utils.seed_data import main_advanced_seeding
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Enhanced seeding not available - missing dependencies",
            )

        # Set environment variables for this request
        env_backup = {}
        env_vars = {
            "SEED_CLEAR_EXISTING": "1" if clear_existing else "0",
            "SEED_MIGRATION_MODE": "1" if migration_mode else "0",
            "SEED_MONITOR_INDEX_CREATION": "1" if monitor_indexes else "0",
            "SEED_ENABLE_PDF": "1" if enable_pdf else "0",
            "SEED_ENABLE_DOCX": "1" if enable_docx else "0",
            "SEED_ENABLE_CSV": "1" if enable_csv else "0",
            "SEED_DRY_RUN": "1" if dry_run else "0",
        }

        # Backup and set environment variables
        for key, value in env_vars.items():
            env_backup[key] = os.environ.get(key)
            os.environ[key] = value

        logger.info(f"Admin {admin_user.email} triggered enhanced seeding")
        logger.info(f"🚀 Starting enhanced seeding via API (dry_run={dry_run})...")
        start_time = time.time()

        result = await main_advanced_seeding()
        elapsed = time.time() - start_time

        logger.info(f"✅ Enhanced seeding completed in {elapsed:.2f}s")

        return {
            "status": "success",
            "message": "Enhanced seeding completed successfully",
            "execution_time_seconds": elapsed,
            "dry_run": dry_run,
            "details": result,
        }

    except Exception as e:
        logger.error(f"❌ Enhanced seeding failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Enhanced seeding failed: {str(e)}"
        )
    finally:
        # Restore environment variables
        for key, backup_value in env_backup.items():
            if backup_value is not None:
                os.environ[key] = backup_value
            else:
                os.environ.pop(key, None)


@app.get("/admin/seed-status", tags=["admin"])
async def get_seeding_status(admin_user: User = Depends(get_admin_user)):
    """Get enhanced seeding system status and configuration"""
    try:
        # Check if enhanced seeding is available
        enhanced_available = False
        import_error = None
        try:
            _mod = importlib.import_module("app.utils.seed_data")
            enhanced_available = hasattr(_mod, "main_advanced_seeding")
        except Exception as exc:
            enhanced_available = False
            import_error = exc

        # Get configuration if available
        seeding_config = {}
        validation = {"valid": False, "issues": ["Enhanced seeding not available"]}

        if enhanced_available:
            try:
                from app.config import config

                seeding_config = config.get_enhanced_seeding_config()
                validation = config.validate_seeding_configuration()
            except Exception as e:
                validation = {"valid": False, "issues": [f"Configuration error: {e}"]}

        # Get AI service status
        ai_status = {}
        try:
            from app.dependencies import get_comprehensive_service_status

            ai_status = get_comprehensive_service_status()
        except Exception as e:
            ai_status = {"error": str(e)}

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "enhanced_seeding_available": enhanced_available,
            "import_error": import_error,
            "configuration": seeding_config,
            "validation": validation,
            "ai_services": {
                "embedding_ready": ai_status.get("services", {}).get(
                    "embedding_service", False
                ),
                "generation_ready": ai_status.get("services", {}).get(
                    "generation_service", False
                ),
                "atlas_available": ai_status.get("database", {}).get(
                    "atlas_search_available", False
                ),
            },
            "capabilities": {
                "real_embeddings": ai_status.get("configuration", {}).get(
                    "use_real_embeddings", False
                ),
                "atlas_search": ai_status.get("configuration", {}).get(
                    "enable_atlas_search", False
                ),
                "parallel_processing": seeding_config.get("performance", {}).get(
                    "parallel_processing", False
                ),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get seeding status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get seeding status: {str(e)}"
        )


@app.post("/admin/cleanup", tags=["admin"])
async def force_cleanup(admin_user: User = Depends(get_admin_user)):
    """Force cleanup of AI services (admin only)"""
    logger.info(f"Admin {admin_user.email} triggered force cleanup")
    try:
        await _safe_cleanup_services()
        return {"status": "success", "message": "Enhanced AI services cleaned up"}
    except Exception as e:
        logger.error(f"Force cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")


@app.post("/admin/warmup", tags=["admin"])
async def force_warmup(admin_user: User = Depends(get_admin_user)):
    """Force warmup of AI services (admin only)"""
    logger.info(f"Admin {admin_user.email} triggered force warmup")
    try:
        warmup_success = await _safe_warmup_services()
        return {
            "status": "success" if warmup_success else "partial",
            "message": "AI service warmup completed",
            "success": warmup_success,
        }
    except Exception as e:
        logger.error(f"Force warmup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Warmup failed: {e}")


# -----------------------------
# Development/Testing Endpoints
# -----------------------------


@app.get("/dev/test-embedding", tags=["development"])
async def test_embedding_endpoint():
    """Test endpoint for embedding service (development only)"""
    try:
        from app.dependencies import get_embedding_service

        service = get_embedding_service()

        test_text = "This is a test query for the sentence-transformers/all-mpnet-base-v2 embedding service."

        start_time = time.time()
        embedding = await service.embed_query(test_text)
        elapsed = time.time() - start_time

        return {
            "status": "success",
            "test_text": test_text,
            "embedding_dimension": len(embedding),
            "time_seconds": elapsed,
            "embedding_preview": embedding[:5],
            "service_stats": getattr(service, "performance_stats", {}),
        }

    except Exception as e:
        logger.error(f"Embedding test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding test failed: {e}")


@app.get("/dev/test-generation", tags=["development"])
async def test_generation_endpoint():
    """Test endpoint for generation service (development only)"""
    try:
        from app.dependencies import get_generation_service

        service = get_generation_service()

        test_prompt = "Explain what artificial intelligence is in simple terms."

        start_time = time.time()
        response = await service.generate(prompt=test_prompt, max_tokens=100)
        elapsed = time.time() - start_time

        return {
            "status": "success",
            "test_prompt": test_prompt,
            "generated_response": response,
            "time_seconds": elapsed,
            "response_length": len(response),
            "service_stats": getattr(service, "performance_stats", {}),
        }

    except Exception as e:
        logger.error(f"Generation test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation test failed: {e}")


@app.get("/dev/test-document-processing", tags=["development"])
async def test_document_processing():
    """Test document processing capabilities"""
    try:
        from app.utils.document_processor import (
            EnhancedDocumentProcessor,
            ProcessingConfig,
        )
        from pathlib import Path
        import tempfile

        # Create test configuration
        config = ProcessingConfig(
            chunk_size=500,
            chunk_overlap=50,
            max_workers=2,
            use_parallel_processing=False,
            supported_extensions=[".txt", ".md"],
        )

        processor = EnhancedDocumentProcessor(config)

        # Test with a simple text
        test_text = """
        This is a test document for the enhanced document processor.

        It contains multiple paragraphs to test the chunking functionality.
        The processor should split this into meaningful chunks while preserving context.

        This is another paragraph to provide more content for testing
        the document processing capabilities of the enhanced system.
        """

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(test_text)
            temp_path = f.name

        try:
            # Process the test file
            chunks = processor._process_file_sync(Path(temp_path))

            return {
                "status": "success",
                "test_file_size": len(test_text),
                "chunks_created": len(chunks),
                "chunk_details": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "content_length": len(chunk.content),
                        "chunk_index": chunk.chunk_index,
                    }
                    for chunk in chunks[:3]  # First 3 chunks only
                ],
                "processor_config": {
                    "chunk_size": config.chunk_size,
                    "chunk_overlap": config.chunk_overlap,
                    "supported_extensions": config.supported_extensions,
                },
            }

        finally:
            # Clean up
            os.unlink(temp_path)
            processor.cleanup()

    except Exception as e:
        logger.error(f"Document processing test failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Document processing test failed: {e}"
        )


# -----------------------------
# Enhanced Router Loading with Better Error Handling
# -----------------------------


def _include_optional_router(module_path: str, router_attr: str = "router") -> None:
    """Enhanced router loading with comprehensive error handling"""
    logger.info(f"Loading router from {module_path}")
    try:
        module = __import__(module_path, fromlist=[router_attr])
        router = getattr(module, router_attr)
        app.include_router(router)
        logger.info(f"✅ Successfully loaded router from {module_path}")
    except ImportError as e:
        logger.warning(f"⚠️ Router {module_path} not found: {e}")
    except AttributeError as e:
        logger.warning(
            f"⚠️ Router attribute '{router_attr}' not found in {module_path}: {e}"
        )
    except Exception as e:
        logger.error(f"❌ Failed to load router {module_path}: {e}")


# Load all API routers with enhanced error handling
logger.info("📡 Loading API routers...")

# Load routers in order of importance
routers_to_load = [
    ("app.api.endpoints.auth", "router"),
    ("app.api.endpoints.users", "router"),
    ("app.api.endpoints.search", "router"),  # Enhanced search with Atlas Vector Search
    ("app.api.endpoints.chat", "router"),  # Enhanced chat with real LLM generation
    ("app.api.endpoints.billing", "router"),
]

for module_path, router_attr in routers_to_load:
    _include_optional_router(module_path, router_attr)

logger.info("✅ Router loading completed")


# -----------------------------
# Global Error Handler
# -----------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with enhanced logging"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Try to log telemetry but don't fail if it's not available
    try:
        from app.dependencies import enhanced_telemetry

        enhanced_telemetry(
            "app_error",
            {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "endpoint": str(request.url.path),
            },
        )
    except Exception:
        pass  # Telemetry is optional

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please check the logs.",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    )


# -----------------------------
# Root Endpoint
# -----------------------------


@app.get("/", tags=["root"])
async def root():
    """Enhanced root endpoint with comprehensive service information"""
    try:
        from app.dependencies import get_comprehensive_service_status

        service_status = get_comprehensive_service_status()
    except Exception:
        service_status = {"services": {"services_ready": 0}, "database": {}}

    return {
        "message": "Enhanced AI Chatbot API",
        "version": "2.0.0",
        "description": "Production-ready AI chatbot with sentence-transformers/all-mpnet-base-v2 and qwen3-1.7b",
        "uptime_seconds": time.time() - startup_time,
        "startup_info": {
            "services_initialized": app_state["services_initialized"],
            "initialization_time": app_state["initialization_time"],
            "startup_errors_count": len(app_state["startup_errors"]),
        },
        "ai_services": {
            "embedding_model": "sentence-transformers/all-mpnet-base-v2",
            "generation_model": "qwen/qwen3-1.7b",
            "services_ready": service_status.get("services", {}).get(
                "services_ready", 0
            ),
            "atlas_search": service_status.get("database", {}).get(
                "atlas_search_available", False
            ),
        },
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "chat": "/chat",
            "search": "/search",
            "docs": "/docs",
            "admin": "/admin/seed-status",
        },
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting Enhanced AI Chatbot Application in development mode...")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
