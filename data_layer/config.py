"""Database layer configuration - separated from AI services"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import secrets

# Load demo environment first if available
try:
    from ai_services.shared.utils.env_loader import load_demo_environment
    load_demo_environment()
except ImportError:
    pass

load_dotenv()


@dataclass
class PostgreSQLConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "demo_v1_chatbot_app")
    username: str = os.getenv("POSTGRES_USER", "demo_v1_user")
    password: str = os.getenv("POSTGRES_PASSWORD", "demo_secure_password_v1")
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    secret_key: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class MongoConfig:
    host: str = os.getenv("MONGO_HOST", "localhost")
    port: int = int(os.getenv("MONGO_PORT", "27018"))
    username: str = os.getenv("MONGO_USER", "root")
    password: str = os.getenv("MONGO_PASSWORD", "demo_example_v1")
    database: str = os.getenv("MONGO_DB", "demo_v1_chatbot_app")
    max_pool_size: int = 20
    min_pool_size: int = 5
    server_selection_timeout_ms: int = 5000
    connect_timeout_ms: int = 5000
    socket_timeout_ms: int = 10000
    conversations_collection: str = "conversations"
    knowledge_base_collection: str = "knowledge_base"
    embeddings_collection: str = "embeddings"
    documents_collection: str = "documents"
    knowledge_vectors_collection: str = "knowledge_vectors"
    embedding_dimension: int = int(os.getenv("MONGO_EMBEDDING_DIM", "768"))
    synthetic_embedding_dimension: int = int(os.getenv("RAG_SYNTHETIC_DIM", "32"))
    vector_index_name: str = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")
    similarity_metric: str = os.getenv("MONGO_SIMILARITY_METRIC", "cosine")

    @property
    def db_name(self) -> str:
        return self.database

    @property
    def connection_uri(self) -> str:
        return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?authSource=admin&directConnection=true"

    @property
    def atlas_uri(self) -> Optional[str]:
        return os.getenv("MONGO_ATLAS_URI")

    def build_uri(self) -> str:
        atlas_uri = self.atlas_uri
        if atlas_uri:
            return atlas_uri
        return self.connection_uri

    def get_connection_settings(self) -> dict:
        return {
            "serverSelectionTimeoutMS": self.server_selection_timeout_ms,
            "connectTimeoutMS": self.connect_timeout_ms,
            "socketTimeoutMS": self.socket_timeout_ms,
            "maxPoolSize": self.max_pool_size,
            "minPoolSize": self.min_pool_size,
        }


@dataclass
class RedisConfig:
    host: str = os.getenv("REDIS_HOST", "localhost")
    port: int = int(os.getenv("REDIS_PORT", "6380"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: Optional[str] = os.getenv("REDIS_PASSWORD")
    max_connections: int = 20
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    default_cache_ttl: int = 3600
    session_ttl: int = 86400
    analytics_ttl: int = 604800
    ai_cache_ttl: int = 1800


@dataclass
class ScyllaConfig:
    hosts: list = None
    port: int = int(os.getenv("SCYLLA_PORT", "9045"))
    keyspace: str = "chatbot_ks"
    datacenter: str = "datacenter1"
    connect_timeout: int = 15
    control_connection_timeout: int = 15
    protocol_version: int = 4
    max_retries: int = 3
    retry_delay: float = 2.0

    def __post_init__(self):
        if self.hosts is None:
            self.hosts = ["127.0.0.1"]

    @classmethod
    def get_scylla_config(cls) -> dict:
        instance = cls()
        return {
            "hosts": instance.hosts,
            "port": instance.port,
            "keyspace": instance.keyspace,
            "datacenter": instance.datacenter,
            "connect_timeout": instance.connect_timeout,
            "control_connection_timeout": instance.control_connection_timeout,
            "protocol_version": instance.protocol_version,
            "max_retries": instance.max_retries,
            "retry_delay": instance.retry_delay,
        }


@dataclass
class DatabaseConfig:
    postgresql: PostgreSQLConfig
    mongo: MongoConfig
    redis: RedisConfig
    scylla: ScyllaConfig
    
    enable_postgresql: bool = os.getenv("ENABLE_POSTGRESQL", "true").lower() == "true"
    enable_mongodb: bool = os.getenv("ENABLE_MONGODB", "true").lower() == "true"


# Database layer configuration instance
database_config = DatabaseConfig(
    postgresql=PostgreSQLConfig(),
    mongo=MongoConfig(),
    redis=RedisConfig(),
    scylla=ScyllaConfig(),
)