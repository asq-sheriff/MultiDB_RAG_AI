"""Shared test fixtures and configuration"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
import httpx
from httpx import ASGITransport
import sys
from pathlib import Path
import logging
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment configuration FIRST
from ai_services.shared.utils.env_loader import load_environment, detect_environment, get_demo_database_urls

# Load appropriate environment for tests
detected_env = detect_environment()
load_environment(detected_env)
logging.getLogger(__name__).info(f"Test environment: {detected_env}")

# Set test environment variables BEFORE importing anything else
os.environ["TESTING"] = "true"
os.environ["USE_REAL_EMBEDDINGS"] = "1"  # Use real embeddings for AI quality tests
os.environ["USE_REAL_GENERATION"] = "0"  # Use mock generation for tests
os.environ["RAG_SYNTHETIC_QUERY_EMBEDDINGS"] = (
    "0"  # Disable synthetic embeddings for AI quality tests
)

# Override with demo database URLs if in demo environment
if detected_env == "demo":
    demo_urls = get_demo_database_urls()
    if demo_urls.get("postgres"):
        os.environ["DATABASE_URL"] = demo_urls["postgres"]
    if demo_urls.get("mongodb"):
        os.environ["MONGODB_URL"] = demo_urls["mongodb"]
    if demo_urls.get("redis"):
        os.environ["REDIS_URL"] = demo_urls["redis"]
    logging.getLogger(__name__).info(f"Using demo database URLs for testing")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from data_layer.models.postgres.postgres_models import DatabaseBase
from ai_services.main import app

# Import MongoDB functions
from data_layer.connections.mongo_connection import init_enhanced_mongo, close_enhanced_mongo

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def initialize_services(event_loop):
    """
    Initialize all application services once for the test session.
    """
    from ai_services.shared.dependencies.dependencies import reset_services

    reset_services()

    # Initialize MongoDB connection
    try:
        await init_enhanced_mongo()
        logger.info("MongoDB initialized for tests")
    except Exception as e:
        logger.warning(
            f"MongoDB initialization failed (non-critical for some tests): {e}"
        )

    # Initialize PostgreSQL
    try:
        from data_layer.connections.postgres_connection import postgres_manager

        await postgres_manager.initialize()
        logger.info("PostgreSQL initialized for tests")
    except Exception as e:
        logger.warning(f"PostgreSQL initialization failed: {e}")

    # Initialize Redis (optional)
    try:
        from data_layer.connections.redis_connection import redis_manager

        redis_manager.initialize()
        logger.info("Redis initialized for tests")
    except Exception as e:
        logger.warning(f"Redis initialization failed (non-critical): {e}")

    from ai_services.shared.dependencies import dependencies
    from data_layer.dependencies import get_scylla_manager

    services_status = {
        "embedding": False,
        "generation": False,
        "knowledge": False,
        "chatbot": False,
        "billing": False,
        "auth": False,
        "user": False,
        "multi_db": False,
        "scylla": False,
    }

    # Initialize core services
    try:
        embedding_service = dependencies.get_embedding_service()
        services_status["embedding"] = embedding_service is not None
        logger.info(f"Embedding service initialized: {services_status['embedding']}")
    except Exception as e:
        logger.warning(f"Embedding service initialization failed: {e}")

    try:
        generation_service = dependencies.get_generation_service()
        services_status["generation"] = generation_service is not None
        logger.info(f"Generation service initialized: {services_status['generation']}")
    except Exception as e:
        logger.warning(f"Generation service initialization failed: {e}")

    try:
        knowledge_service = dependencies.get_knowledge_service()
        services_status["knowledge"] = knowledge_service is not None
        logger.info(f"Knowledge service initialized: {services_status['knowledge']}")
    except Exception as e:
        logger.error(f"Knowledge service initialization failed: {e}")

    try:
        chatbot_service = dependencies.get_chatbot_service()
        services_status["chatbot"] = chatbot_service is not None
        logger.info(f"Chatbot service initialized: {services_status['chatbot']}")
    except Exception as e:
        logger.error(f"Chatbot service initialization failed: {e}")

    # Note: auth/billing/user services now handled by Go microservices
    # These services are no longer available in Python
    services_status["billing"] = True  # Handled by billing-service-go
    services_status["auth"] = True     # Handled by auth-rbac-service-go  
    services_status["user"] = True     # Handled by Go services
    logger.info("Auth/billing/user services handled by Go microservices")

    try:
        multi_db_service = dependencies.get_multi_db_service()
        services_status["multi_db"] = multi_db_service is not None
        logger.info(f"Multi-DB service initialized: {services_status['multi_db']}")
    except Exception as e:
        logger.warning(f"Multi-DB service initialization failed: {e}")

    # ScyllaDB is optional
    try:
        scylla_manager = get_scylla_manager()
        services_status["scylla"] = (
            scylla_manager is not None and scylla_manager.is_connected()
        )
        logger.info(f"ScyllaDB manager initialized: {services_status['scylla']}")
    except Exception as e:
        logger.warning(f"ScyllaDB initialization failed (non-critical): {e}")

    # Log summary
    initialized_count = sum(1 for v in services_status.values() if v)
    total_count = len(services_status)
    logger.info(
        f"Service initialization summary: {initialized_count}/{total_count} services ready"
    )

    # Check critical services
    critical_services = ["billing", "auth", "knowledge", "chatbot"]
    critical_ok = all(services_status.get(s, False) for s in critical_services)

    if not critical_ok:
        failed_critical = [
            s for s in critical_services if not services_status.get(s, False)
        ]
        logger.error(f"Critical services failed to initialize: {failed_critical}")
        # Don't raise - let tests handle missing services

    yield

    # Cleanup after all tests
    try:
        await close_enhanced_mongo()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.warning(f"MongoDB cleanup failed: {e}")

    try:
        from data_layer.connections.postgres_connection import postgres_manager

        await postgres_manager.close()
        logger.info("PostgreSQL connection closed")
    except Exception as e:
        logger.warning(f"PostgreSQL cleanup failed: {e}")

    try:
        from data_layer.connections.redis_connection import redis_manager

        redis_manager.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis cleanup failed: {e}")

    # Reset services
    reset_services()
    logger.info("All services reset")


@pytest.fixture(scope="function")
async def mongo_connection():
    """
    Ensure MongoDB connection is available for each test.
    This fixture can be used by tests that need MongoDB.
    """
    from data_layer.connections.mongo_connection import get_mongo_manager

    try:
        manager = get_mongo_manager()
        # Skip health check in tests to avoid connection issues
        yield manager
    except Exception as e:
        logger.warning(f"MongoDB connection issue (non-critical): {e}")
        yield None


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine using environment-aware configuration."""
    from ai_services.shared.config.config import config
    
    # Use a test database
    test_db_name = f"{config.postgresql.database}_test"

    # First, create the test database if it doesn't exist
    default_db_url = config.postgresql.url.replace(
        f"/{config.postgresql.database}", "/postgres"
    )
    temp_engine = create_async_engine(
        default_db_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )

    async with temp_engine.connect() as conn:
        # Check if test database exists
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": test_db_name},
        )
        exists = result.scalar()

        if not exists:
            await conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            logger.info(f"Created test database: {test_db_name}")

    await temp_engine.dispose()

    # Now create the actual test engine
    test_db_url = config.postgresql.url.replace(
        f"/{config.postgresql.database}", f"/{test_db_name}"
    )
    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=NullPool,  # Important for testing
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(DatabaseBase.metadata.create_all)
        logger.info("Created test database tables")

    yield engine

    # Cleanup
    await engine.dispose()
    logger.info("Test database engine disposed")


@pytest.fixture(scope="function")
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    async_session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Rollback any changes made during the test


@pytest.fixture
async def test_client():
    """Create a test client for API testing."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def suppress_scylla_warnings(monkeypatch):
    """Suppress ScyllaDB/Cassandra shutdown warnings in tests."""
    import warnings

    warnings.filterwarnings(
        "ignore", message=".*cannot schedule new futures after shutdown.*"
    )
    warnings.filterwarnings("ignore", category=ResourceWarning)

    # Also suppress through environment
    monkeypatch.setenv("CASSANDRA_SKIP_SHUTDOWN_ERRORS", "1")
    monkeypatch.setenv("PYTHONWARNINGS", "ignore::ResourceWarning")
