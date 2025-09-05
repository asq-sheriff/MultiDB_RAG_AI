"""Database layer dependencies and connection managers"""

import logging
from typing import Optional, TYPE_CHECKING, AsyncGenerator, Any
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from data_layer.connections.scylla_connection import ScyllaDBConnection
    from data_layer.connections.postgres_connection import PostgreSQLConnectionManager
    from data_layer.connections.redis_connection import RedisConnectionManager
    from data_layer.connections.mongo_connection import MongoConnectionManager

scylla_manager: Optional["ScyllaDBConnection"] = None
postgres_manager: Optional["PostgreSQLConnectionManager"] = None
redis_manager: Optional["RedisConnectionManager"] = None
mongo_manager: Optional["MongoConnectionManager"] = None

logger = logging.getLogger(__name__)


def get_scylla_manager() -> "ScyllaDBConnection":
    """Get or create ScyllaDB manager instance"""
    global scylla_manager
    if scylla_manager is None:
        try:
            from data_layer.connections.scylla_connection import ScyllaDBConnection

            scylla_manager = ScyllaDBConnection()
            if not scylla_manager.is_connected():
                scylla_manager.connect()
            logger.info("Created ScyllaDBConnection instance")
        except Exception as e:
            logger.warning(f"ScyllaDB not available, using mock: {e}")
            scylla_manager = MockScyllaManager()
    return scylla_manager


def get_postgres_manager() -> "PostgreSQLConnectionManager":
    """Get PostgreSQL manager instance"""
    global postgres_manager
    if postgres_manager is None:
        try:
            from data_layer.connections.postgres_connection import postgres_manager as pm
            postgres_manager = pm
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL manager: {e}")
            raise
    return postgres_manager


def get_redis_manager() -> "RedisConnectionManager":
    """Get Redis manager instance"""
    global redis_manager
    if redis_manager is None:
        try:
            from data_layer.connections.redis_connection import redis_manager as rm
            redis_manager = rm
        except Exception as e:
            logger.error(f"Failed to get Redis manager: {e}")
            raise
    return redis_manager


def get_mongo_manager() -> "MongoConnectionManager":
    """Get MongoDB manager instance"""
    global mongo_manager
    if mongo_manager is None:
        try:
            from data_layer.connections.mongo_connection import enhanced_mongo_manager
            mongo_manager = enhanced_mongo_manager
        except Exception as e:
            logger.error(f"Failed to get MongoDB manager: {e}")
            raise
    return mongo_manager


async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get PostgreSQL session"""
    pm = get_postgres_manager()
    async with pm.get_session() as session:
        yield session


# Alias for compatibility
get_db_session = get_postgres_session


class MockScyllaManager:
    """Mock ScyllaDB manager for testing"""

    def is_connected(self):
        return False

    def connect(self):
        pass

    def get_session(self):
        return None

    def ensure_keyspace(self, keyspace):
        pass

    def get_connection_info(self):
        return {"connected": False}


def reset_database_managers():
    """Reset all database managers - useful for testing"""
    global scylla_manager, postgres_manager, redis_manager, mongo_manager
    
    scylla_manager = None
    postgres_manager = None
    redis_manager = None
    mongo_manager = None
    
    logger.info("All database managers reset")


def get_database_health_status():
    """Get health status of all database connections"""
    try:
        status = {
            "postgresql": False,
            "mongodb": False, 
            "redis": False,
            "scylladb": False
        }
        
        # Check PostgreSQL
        try:
            pm = get_postgres_manager()
            status["postgresql"] = pm is not None
        except Exception:
            pass
            
        # Check MongoDB
        try:
            mm = get_mongo_manager()
            status["mongodb"] = mm is not None
        except Exception:
            pass
            
        # Check Redis
        try:
            rm = get_redis_manager()
            status["redis"] = rm is not None
        except Exception:
            pass
            
        # Check ScyllaDB
        try:
            sm = get_scylla_manager()
            status["scylladb"] = sm.is_connected() if sm else False
        except Exception:
            pass
            
        return status
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "postgresql": False,
            "mongodb": False,
            "redis": False,
            "scylladb": False,
            "error": str(e)
        }


__all__ = [
    "get_scylla_manager",
    "get_postgres_manager", 
    "get_redis_manager",
    "get_mongo_manager",
    "get_postgres_session",
    "get_db_session",
    "reset_database_managers",
    "get_database_health_status",
    "scylla_manager",
    "postgres_manager",
    "redis_manager", 
    "mongo_manager",
]