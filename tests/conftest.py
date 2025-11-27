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

# Set test environment variables BEFORE importing anything else
os.environ["TESTING"] = "true"
os.environ["USE_REAL_EMBEDDINGS"] = "0"  # Use mock embeddings for tests
os.environ["USE_REAL_GENERATION"] = "0"  # Use mock generation for tests
os.environ["RAG_SYNTHETIC_QUERY_EMBEDDINGS"] = (
    "1"  # Enable synthetic embeddings for tests
)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.database.postgres_models import DatabaseBase
from app.api.main import app
from app.config import config

# Import MongoDB functions
from app.database.mongo_connection import init_enhanced_mongo, close_enhanced_mongo

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
    from app.dependencies import reset_services

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
        from app.database.postgres_connection import postgres_manager

        await postgres_manager.initialize()
        logger.info("PostgreSQL initialized for tests")
    except Exception as e:
        logger.warning(f"PostgreSQL initialization failed: {e}")

    # Initialize Redis (optional)
    try:
        from app.database.redis_connection import redis_manager

        redis_manager.initialize()
        logger.info("Redis initialized for tests")
    except Exception as e:
        logger.warning(f"Redis initialization failed (non-critical): {e}")

    from app import dependencies

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

    # Initialize auth/billing services
    try:
        billing_service = dependencies.get_billing_service()
        services_status["billing"] = billing_service is not None
        logger.info(f"Billing service initialized: {services_status['billing']}")
    except Exception as e:
        logger.error(f"Billing service initialization failed: {e}")

    try:
        auth_service = dependencies.get_auth_service()
        services_status["auth"] = auth_service is not None
        logger.info(f"Auth service initialized: {services_status['auth']}")
    except Exception as e:
        logger.error(f"Auth service initialization failed: {e}")

    try:
        user_service = dependencies.get_user_service()
        services_status["user"] = user_service is not None
        logger.info(f"User service initialized: {services_status['user']}")
    except Exception as e:
        logger.error(f"User service initialization failed: {e}")

    try:
        multi_db_service = dependencies.get_multi_db_service()
        services_status["multi_db"] = multi_db_service is not None
        logger.info(f"Multi-DB service initialized: {services_status['multi_db']}")
    except Exception as e:
        logger.warning(f"Multi-DB service initialization failed: {e}")

    # ScyllaDB is optional
    try:
        scylla_manager = dependencies.get_scylla_manager()
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
        from app.database.postgres_connection import postgres_manager

        await postgres_manager.close()
        logger.info("PostgreSQL connection closed")
    except Exception as e:
        logger.warning(f"PostgreSQL cleanup failed: {e}")

    try:
        from app.database.redis_connection import redis_manager

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
    from app.database.mongo_connection import get_mongo_manager

    try:
        manager = get_mongo_manager()
        # Skip health check in tests to avoid connection issues
        yield manager
    except Exception as e:
        logger.warning(f"MongoDB connection issue (non-critical): {e}")
        yield None


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
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
