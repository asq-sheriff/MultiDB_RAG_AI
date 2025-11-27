"""Database Module Initialization"""

import logging

logger = logging.getLogger(__name__)

try:
    from .mongo_connection import (
        enhanced_mongo_manager,
        mongo_manager,
        init_enhanced_mongo,
        close_enhanced_mongo,
        init_mongo,
        close_mongo,
        MongoConfig,
        AtlasVectorSearchConfig,
    )

    def get_mongo_connection():
        """Get mongo connection"""
        return enhanced_mongo_manager

    mongo_connection = enhanced_mongo_manager
    MONGO_AVAILABLE = True

except ImportError as e:
    logger.warning(f"MongoDB connection not available: {e}")

    class MockMongoManager:
        def __init__(self):
            self.is_connected = False
            self.is_atlas = False
            self.vector_search_available = False

        async def health_check(self):
            return {"status": "unavailable", "error": "MongoDB not configured"}

    enhanced_mongo_manager = MockMongoManager()
    mongo_manager = MockMongoManager()
    mongo_connection = MockMongoManager()
    MONGO_AVAILABLE = False

    async def init_enhanced_mongo():
        return False

    async def close_enhanced_mongo():
        pass

    def get_mongo_connection():
        return enhanced_mongo_manager

    MongoConfig = None
    AtlasVectorSearchConfig = None


try:
    from .postgres_connection import postgres_manager, get_postgres_session
    from .postgres_models import (
        DatabaseBase,
        User,
        Organization,
        Subscription,
        UsageRecord,
        AuditLog,
        FeatureFlag,
        SystemSetting,
    )

    POSTGRES_AVAILABLE = True

except ImportError as e:
    logger.warning(f"PostgreSQL not available: {e}")
    postgres_manager = None
    get_postgres_session = None
    POSTGRES_AVAILABLE = False

try:
    from .scylla_connection import scylla_manager, ScyllaDBConnection
    from .scylla_models import (
        ConversationHistory,
        KnowledgeBase,
        EnhancedConversationHistory,
    )

    SCYLLA_AVAILABLE = True

except ImportError as e:
    logger.warning(f"ScyllaDB not available: {e}")

    class MockScyllaManager:
        def __init__(self):
            self.connected = False

        def is_connected(self):
            return False

        def connect(self):
            pass

        def disconnect(self):
            pass

    scylla_manager = MockScyllaManager()
    ScyllaDBConnection = None
    SCYLLA_AVAILABLE = False

try:
    from .redis_connection import redis_manager, get_redis
    from .redis_models import CacheModel, SessionModel, AnalyticsModel

    REDIS_AVAILABLE = True

except ImportError as e:
    logger.warning(f"Redis not available: {e}")
    redis_manager = None
    get_redis = None
    REDIS_AVAILABLE = False


def get_seed_function():
    """Lazy load seed function to avoid circular imports"""
    try:
        from app.utils.seed_data import main as seed_main

        return seed_main
    except ImportError as e:
        logger.warning(f"Seed data module not available: {e}")
        return None


def seed_knowledge_base():
    """Seed knowledge base with lazy loading"""
    import asyncio

    seed_func = get_seed_function()
    if seed_func:
        try:
            return asyncio.run(seed_func())
        except Exception as e:
            logger.error(f"Seeding failed: {e}")
            return False
    else:
        logger.warning("Seeding not available - seed_data module not found")
        return False


def get_sample_questions():
    """Return sample questions for testing"""
    return [
        "What is Redis?",
        "How does Python work?",
        "What is machine learning?",
        "How do I reset my password?",
        "What is the policy for refunds?",
        "How do I contact support?",
    ]


# Export list - without seed_main
__all__ = [
    # MongoDB
    "enhanced_mongo_manager",
    "mongo_manager",
    "mongo_connection",
    "get_mongo_connection",
    "init_enhanced_mongo",
    "close_enhanced_mongo",
    "init_mongo",
    "close_mongo",
    "MongoConfig",
    "AtlasVectorSearchConfig",
    "MONGO_AVAILABLE",
    # PostgreSQL
    "postgres_manager",
    "get_postgres_session",
    "DatabaseBase",
    "User",
    "Organization",
    "Subscription",
    "UsageRecord",
    "AuditLog",
    "FeatureFlag",
    "SystemSetting",
    "POSTGRES_AVAILABLE",
    # ScyllaDB
    "scylla_manager",
    "ScyllaDBConnection",
    "ConversationHistory",
    "KnowledgeBase",
    "EnhancedConversationHistory",
    "SCYLLA_AVAILABLE",
    # Redis
    "redis_manager",
    "get_redis",
    "CacheModel",
    "SessionModel",
    "AnalyticsModel",
    "REDIS_AVAILABLE",
    # Seed functions (lazy loaded)
    "seed_knowledge_base",
    "get_sample_questions",
    "get_seed_function",
]
