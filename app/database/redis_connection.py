import redis
import logging
from typing import Optional
from contextlib import asynccontextmanager

try:
    import redis.asyncio as aioredis

    ASYNC_REDIS_AVAILABLE = True
except ImportError:
    try:
        import aioredis

        ASYNC_REDIS_AVAILABLE = True
    except ImportError:
        ASYNC_REDIS_AVAILABLE = False
        aioredis = None

from app.config import config

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """Redis connection management with connection pooling"""

    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._async_pool: Optional = None
        self._client: Optional[redis.Redis] = None
        self._async_client: Optional = None
        self._connected: bool = False

    def initialize(self) -> None:
        """Initialize Redis connection pools"""
        try:
            self._pool = redis.ConnectionPool(
                host=config.redis.host,
                port=config.redis.port,
                db=config.redis.db,
                password=config.redis.password if config.redis.password else None,
                max_connections=config.redis.max_connections,
                socket_timeout=config.redis.socket_timeout,
                socket_connect_timeout=config.redis.socket_connect_timeout,
                decode_responses=True,
                health_check_interval=30,
            )

            self._client = redis.Redis(connection_pool=self._pool)

            if ASYNC_REDIS_AVAILABLE and aioredis:
                try:
                    self._async_pool = aioredis.ConnectionPool(
                        host=config.redis.host,
                        port=config.redis.port,
                        db=config.redis.db,
                        password=config.redis.password
                        if config.redis.password
                        else None,
                        max_connections=config.redis.max_connections,
                        socket_timeout=config.redis.socket_timeout,
                        socket_connect_timeout=config.redis.socket_connect_timeout,
                        decode_responses=True,
                    )
                    self._async_client = aioredis.Redis(
                        connection_pool=self._async_pool
                    )
                except Exception as e:
                    logger.warning(
                        f"Async Redis setup failed: {e}, continuing with sync only"
                    )

            self._client.ping()
            self._connected = True
            logger.info(
                f"Redis {redis.__version__} connected successfully to {config.redis.host}:{config.redis.port}"
            )

        except Exception as e:
            self._connected = False
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise ConnectionError(f"Cannot connect to Redis: {e}")

    @property
    def client(self) -> redis.Redis:
        """Get synchronous Redis client"""
        if not self._client:
            self.initialize()
        return self._client

    @property
    def async_client(self):
        """Get asynchronous Redis client"""
        if not self._async_client:
            if ASYNC_REDIS_AVAILABLE:
                self.initialize()
            else:
                raise RuntimeError("Async Redis not available")
        return self._async_client

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self._connected or not self._client:
            return False

        try:
            self._client.ping()
            return True
        except Exception as e:
            logger.debug(f"Redis connection check failed: {e}")
            self._connected = False
            return False

    @asynccontextmanager
    async def get_async_client(self):
        """Context manager for async Redis operations"""
        if not ASYNC_REDIS_AVAILABLE:
            raise RuntimeError("Async Redis not available, use synchronous client")

        try:
            yield self.async_client
        except Exception as e:
            logger.error(f"Redis async operation failed: {e}")
            raise

    def close(self) -> None:
        """Close Redis connections"""
        try:
            if self._pool:
                self._pool.disconnect()

            if self._async_pool and hasattr(self._async_pool, "disconnect"):
                try:
                    import asyncio

                    if asyncio.get_event_loop().is_running():
                        asyncio.create_task(self._async_pool.disconnect())
                    else:
                        asyncio.run(self._async_pool.disconnect())
                except Exception:
                    pass

            self._connected = False
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")

    def test_connection(self) -> bool:
        """Test Redis connection"""
        try:
            self.client.ping()
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            self._connected = False
            return False


redis_manager: Optional[RedisConnectionManager] = None


def get_redis_manager() -> "RedisConnectionManager":
    global redis_manager
    if redis_manager is None:
        redis_manager = RedisConnectionManager()
    return redis_manager


def get_redis() -> redis.Redis:
    manager = get_redis_manager()
    if not manager.is_connected:
        manager.initialize()
    return manager.client
