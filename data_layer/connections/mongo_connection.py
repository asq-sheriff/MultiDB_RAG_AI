"""MongoDB Connection Manager with Atlas Vector Search Support"""

import logging
from typing import Optional, List, Dict, Any
import os
from pathlib import Path

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    AsyncIOMotorClient = None

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None

logger = logging.getLogger(__name__)

# Load environment variables from .env file to ensure correct MongoDB credentials
if DOTENV_AVAILABLE:
    # Look for .env file in the project root
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)  # Don't override existing env vars
        logger.debug(f"Loaded environment from {env_file}")
    else:
        logger.debug(f"No .env file found at {env_file}")


class MongoConfig:
    """Enhanced MongoDB configuration with robust hybrid setup support"""

    def __init__(self):
        self.host = os.getenv("MONGO_HOST", "localhost")
        self.port = int(os.getenv("MONGO_PORT", "27017"))
        self.username = os.getenv("MONGO_USER", "root")
        
        # Use password from env, default to 'example' for current containers
        password = os.getenv("MONGO_PASSWORD", "example")
        
        # If we detect demo password but current containers, use current password
        if password == "demo_example_v1" and self.port == 27017:
            logger.warning("Using current container password for port 27017")
            password = "example"
        
        self.password = password
        self.database = os.getenv("MONGO_DB", "chatbot_app")
        self.atlas_uri = os.getenv("MONGO_ATLAS_URI")
        self.embedding_dimension = int(os.getenv("MONGO_EMBEDDING_DIM", "768"))
        self.vector_index_name = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")
        self.similarity_metric = os.getenv("MONGO_SIMILARITY_METRIC", "cosine")
        
        # Additional connection settings for hybrid setup
        self.auth_source = os.getenv("MONGO_AUTH_SOURCE", "admin")
        self.max_pool_size = int(os.getenv("MONGO_MAX_POOL_SIZE", "20"))
        self.min_pool_size = int(os.getenv("MONGO_MIN_POOL_SIZE", "5"))
        self.server_selection_timeout = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT", "5000"))
        self.connect_timeout = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000"))
        self.socket_timeout = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "20000"))
        
        # Log the configuration for debugging (without exposing the password)
        logger.debug(f"MongoDB config: host={self.host}:{self.port}, user={self.username}, db={self.database}")

    def get_connection_string(self) -> str:
        """Get MongoDB connection string with hybrid setup optimizations"""
        if self.atlas_uri:
            return self.atlas_uri
            
        # For MongoDB Atlas Local containers, use the container hostname
        # Check if we're connecting to port 27017 (current containers vs 27018 for demo)
        actual_host = self.host
        if self.host == "localhost" and self.port == 27017:
            # Try connecting to container hostname for replica set
            actual_host = "mongodb-atlas-local"
            
        # Enhanced connection string for hybrid Docker/localhost setup
        # For external connections to MongoDB Atlas Local, use directConnection
        connection_params = [
            f"authSource={self.auth_source}",
            "directConnection=true",  # Required for external connections to single-node replica sets
            f"maxPoolSize={self.max_pool_size}",
            f"minPoolSize={self.min_pool_size}",
            f"serverSelectionTimeoutMS={self.server_selection_timeout}",
            f"connectTimeoutMS={self.connect_timeout}",
            f"socketTimeoutMS={self.socket_timeout}",
            "retryWrites=false"  # Disable retryWrites for direct connections
        ]
        
        params_str = "&".join(connection_params)
        return f"mongodb://{self.username}:{self.password}@{actual_host}:{self.port}/?{params_str}"

    def is_atlas(self) -> bool:
        """Check if using Atlas"""
        return bool(self.atlas_uri)
        
    def get_connection_info(self) -> dict:
        """Get connection information for debugging"""
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "database": self.database,
            "auth_source": self.auth_source,
            "is_atlas": self.is_atlas(),
            "connection_string_masked": f"mongodb://{self.username}:***@{self.host}:{self.port}/..."
        }


class AtlasVectorSearchConfig:
    """Atlas Vector Search configuration"""

    def __init__(self):
        self.index_name = os.getenv("ATLAS_VECTOR_INDEX_NAME", "vector_index")
        self.collection_name = os.getenv("ATLAS_COLLECTION_NAME", "documents")
        self.embedding_field = os.getenv("ATLAS_EMBEDDING_FIELD", "embedding")
        self.text_field = os.getenv("ATLAS_TEXT_FIELD", "content")
        self.metadata_field = os.getenv("ATLAS_METADATA_FIELD", "metadata")


class EnhancedMongoManager:
    """Enhanced MongoDB Manager with Atlas Vector Search support"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        self.config = MongoConfig()
        self.vector_config = AtlasVectorSearchConfig()
        self.is_connected = False
        self.is_atlas = self.config.is_atlas()
        self.vector_search_available = False

    async def connect(self) -> bool:
        """Connect to MongoDB with enhanced error handling"""
        if not MOTOR_AVAILABLE:
            logger.warning("Motor (async MongoDB driver) not available")
            return False

        try:
            connection_string = self.config.get_connection_string()
            conn_info = self.config.get_connection_info()
            
            logger.info(f"Connecting to MongoDB: {conn_info['host']}:{conn_info['port']} (database: {conn_info['database']})")
            
            # Use enhanced connection settings from config
            self.client = AsyncIOMotorClient(
                connection_string, 
                serverSelectionTimeoutMS=self.config.server_selection_timeout,
                connectTimeoutMS=self.config.connect_timeout,
                socketTimeoutMS=self.config.socket_timeout,
                maxPoolSize=self.config.max_pool_size,
                minPoolSize=self.config.min_pool_size,
                retryWrites=True
            )

            # Test connection with detailed error info
            await self.client.admin.command("ping")
            
            # Verify authentication by listing databases
            db_list = await self.client.list_database_names()
            logger.debug(f"Available databases: {db_list}")

            self.database = self.client[self.config.database]
            self.is_connected = True

            # Check if Atlas Vector Search is available
            if self.is_atlas:
                self.vector_search_available = await self._check_vector_search()

            logger.info(
                f"✅ MongoDB connected successfully to {conn_info['host']}:{conn_info['port']} "
                f"(Atlas: {self.is_atlas}, Vector Search: {self.vector_search_available})"
            )
            return True

        except Exception as e:
            conn_info = self.config.get_connection_info()
            logger.error(
                f"❌ Failed to connect to MongoDB at {conn_info['host']}:{conn_info['port']}: {e}"
            )
            logger.error(f"Connection details: {conn_info}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            self.is_connected = False
            self.vector_search_available = False
            logger.info("MongoDB disconnected")

    async def _check_vector_search(self) -> bool:
        """Check if Atlas Vector Search is available"""
        try:
            # Try to list search indexes to verify vector search capability
            collection = self.database[self.vector_config.collection_name]
            search_indexes = await collection.list_search_indexes().to_list(length=None)
            return len(search_indexes) > 0
        except Exception as e:
            logger.debug(f"Vector search not available: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """MongoDB health check"""
        if not self.is_connected:
            return {"status": "disconnected", "error": "Not connected to MongoDB"}

        try:
            # Ping the database
            await self.client.admin.command("ping")

            # Get server info
            server_info = await self.client.admin.command("buildinfo")

            return {
                "status": "healthy",
                "is_atlas": self.is_atlas,
                "vector_search_available": self.vector_search_available,
                "server_version": server_info.get("version", "unknown"),
                "database": self.config.database,
            }

        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def create_collection(self, collection_name: str) -> bool:
        """Create a collection"""
        if not self.is_connected:
            return False

        try:
            await self.database.create_collection(collection_name)
            logger.info(f"Collection '{collection_name}' created")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            return False

    async def insert_document(
        self, collection_name: str, document: Dict[str, Any]
    ) -> Optional[str]:
        """Insert a document"""
        if not self.is_connected:
            return None

        try:
            collection = self.database[collection_name]
            result = await collection.insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to insert document: {e}")
            return None

    async def vector_search(
        self,
        query_vector: List[float],
        collection_name: str = None,
        limit: int = 5,
        filters: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """Perform Atlas Vector Search"""
        if not self.vector_search_available:
            logger.warning("Vector search not available")
            return []

        collection_name = collection_name or self.vector_config.collection_name

        try:
            collection = self.database[collection_name]

            # Build vector search pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_config.index_name,
                        "path": self.vector_config.embedding_field,
                        "queryVector": query_vector,
                        "numCandidates": limit * 2,
                        "limit": limit,
                    }
                }
            ]

            # Add filters if provided
            if filters:
                pipeline.append({"$match": filters})

            # Add score calculation
            pipeline.append({"$addFields": {"score": {"$meta": "vectorSearchScore"}}})

            # Execute search
            results = await collection.aggregate(pipeline).to_list(length=limit)

            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def documents(self):
        """Get documents collection for seeding compatibility"""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database.documents

    def embeddings(self):
        """Get embeddings collection for seeding compatibility"""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database.therapeutic_content

    def knowledge_vectors(self):
        """Get knowledge_vectors collection for seeding compatibility"""
        if self.database is None:
            raise RuntimeError("Database not connected")
        return self.database.therapeutic_content


# Global manager instances
enhanced_mongo_manager = EnhancedMongoManager()
mongo_manager = enhanced_mongo_manager  # Alias for backward compatibility


async def init_enhanced_mongo() -> bool:
    """Initialize enhanced MongoDB connection"""
    return await enhanced_mongo_manager.connect()


async def close_enhanced_mongo():
    """Close enhanced MongoDB connection"""
    await enhanced_mongo_manager.disconnect()


# Backward compatibility aliases
async def init_mongo() -> bool:
    """Initialize MongoDB connection (alias)"""
    return await init_enhanced_mongo()


async def close_mongo():
    """Close MongoDB connection (alias)"""
    await close_enhanced_mongo()


def get_mongo_client():
    """Get MongoDB client"""
    return enhanced_mongo_manager.client


def get_mongo_database():
    """Get MongoDB database"""
    return enhanced_mongo_manager.database


def get_mongo_manager():
    """Get MongoDB manager"""
    return enhanced_mongo_manager


# Export all classes and functions
__all__ = [
    "EnhancedMongoManager",
    "MongoConfig",
    "AtlasVectorSearchConfig",
    "enhanced_mongo_manager",
    "mongo_manager",
    "init_enhanced_mongo",
    "close_enhanced_mongo",
    "init_mongo",
    "close_mongo",
    "get_mongo_client",
    "get_mongo_database",
    "get_mongo_manager",
]
