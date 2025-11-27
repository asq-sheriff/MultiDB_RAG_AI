"""MongoDB Connection Manager with Atlas Vector Search Support"""

import logging
from typing import Optional, List, Dict, Any
import os

try:
    from motor.motor_asyncio import AsyncIOMotorClient

    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    AsyncIOMotorClient = None

logger = logging.getLogger(__name__)


class MongoConfig:
    """MongoDB configuration"""

    def __init__(self):
        self.host = os.getenv("MONGO_HOST", "localhost")
        self.port = int(os.getenv("MONGO_PORT", "27017"))
        self.username = os.getenv("MONGO_USER", "root")
        self.password = os.getenv("MONGO_PASSWORD", "example")
        self.database = os.getenv("MONGO_DB", "chatbot_app")
        self.atlas_uri = os.getenv("MONGO_ATLAS_URI")
        self.embedding_dimension = int(os.getenv("MONGO_EMBEDDING_DIM", "768"))
        self.vector_index_name = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")
        self.similarity_metric = os.getenv("MONGO_SIMILARITY_METRIC", "cosine")

    def get_connection_string(self) -> str:
        """Get MongoDB connection string"""
        if self.atlas_uri:
            return self.atlas_uri
        return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/"

    def is_atlas(self) -> bool:
        """Check if using Atlas"""
        return bool(self.atlas_uri)


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
        """Connect to MongoDB"""
        if not MOTOR_AVAILABLE:
            logger.warning("Motor (async MongoDB driver) not available")
            return False

        try:
            connection_string = self.config.get_connection_string()
            self.client = AsyncIOMotorClient(
                connection_string, serverSelectionTimeoutMS=5000
            )

            # Test connection
            await self.client.admin.command("ping")

            self.database = self.client[self.config.database]
            self.is_connected = True

            # Check if Atlas Vector Search is available
            if self.is_atlas:
                self.vector_search_available = await self._check_vector_search()

            logger.info(
                f"MongoDB connected successfully (Atlas: {self.is_atlas}, Vector Search: {self.vector_search_available})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
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
