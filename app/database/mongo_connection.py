"""
Enhanced MongoDB Atlas Vector Search Integration
=================================================
Location: app/database/mongo_connection.py (COMPLETE REPLACEMENT)
"""

import math
import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import asyncio

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    OperationFailure,
    ConfigurationError
)
from pymongo import ASCENDING, TEXT
from bson import ObjectId

logger = logging.getLogger(__name__)

@dataclass
class MongoConfig:
    """Enhanced MongoDB configuration with Atlas support"""
    host: str = os.getenv("MONGO_HOST", "localhost")
    port: int = int(os.getenv("MONGO_PORT", "27017"))
    username: str = os.getenv("MONGO_USER", "root")
    password: str = os.getenv("MONGO_PASSWORD", "example")
    database: str = os.getenv("MONGO_DB", "chatbot_app")

    # Enhanced connection settings
    max_pool_size: int = int(os.getenv("MONGO_MAX_POOL_SIZE", "20"))
    min_pool_size: int = int(os.getenv("MONGO_MIN_POOL_SIZE", "5"))
    server_selection_timeout_ms: int = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT", "10000"))
    connect_timeout_ms: int = int(os.getenv("MONGO_CONNECT_TIMEOUT", "10000"))
    socket_timeout_ms: int = int(os.getenv("MONGO_SOCKET_TIMEOUT", "20000"))

    # Collections configuration
    conversations_collection: str = "conversations"
    knowledge_base_collection: str = "knowledge_base"
    embeddings_collection: str = "embeddings"
    documents_collection: str = "documents"
    knowledge_vectors_collection: str = "knowledge_vectors"

    # Vector configuration
    embedding_dimension: int = int(os.getenv("MONGO_EMBEDDING_DIM", "768"))
    synthetic_embedding_dimension: int = int(os.getenv("RAG_SYNTHETIC_DIM", "32"))

    # Atlas Vector Search configuration
    vector_index_name: str = os.getenv("MONGO_VECTOR_INDEX_NAME", "vector_index")
    similarity_metric: str = os.getenv("MONGO_SIMILARITY_METRIC", "cosine")

    @property
    def db_name(self) -> str:
        """Database name for compatibility"""
        return self.database

    @property
    def connection_uri(self) -> str:
        """Build MongoDB connection URI for local"""
        return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/"

    @property
    def atlas_uri(self) -> Optional[str]:
        """MongoDB Atlas URI for production"""
        return os.getenv("MONGO_ATLAS_URI")

    def build_uri(self) -> str:
        """Build appropriate MongoDB URI - FIXED to use MONGO_URI environment variable"""
        # FIXED: First check for explicit MONGO_URI (our directConnection fix)
        explicit_uri = os.getenv("MONGO_URI")
        if explicit_uri:
            logger.info("Using explicit MONGO_URI from environment")
            return explicit_uri

        # Fallback to Atlas if configured
        atlas_uri = self.atlas_uri
        if atlas_uri:
            return atlas_uri

        # Finally, build from components
        return self.connection_uri

    def get_connection_settings(self) -> dict:
        """Get Motor connection settings"""
        return {
            "serverSelectionTimeoutMS": self.server_selection_timeout_ms,
            "connectTimeoutMS": self.connect_timeout_ms,
            "socketTimeoutMS": self.socket_timeout_ms,
            "maxPoolSize": self.max_pool_size,
            "minPoolSize": self.min_pool_size,
            "uuidRepresentation": "standard"
        }


@dataclass
class AtlasVectorSearchConfig:
    """Configuration for MongoDB Atlas Vector Search"""

    # Atlas connection
    atlas_uri: Optional[str] = os.getenv("MONGO_ATLAS_URI")
    cluster_name: str = os.getenv("ATLAS_CLUSTER_NAME", "chatbot-vector-search")

    # Vector search index configuration for all-mpnet-base-v2
    vector_index_name: str = os.getenv("ATLAS_VECTOR_INDEX_NAME", "vector_index")
    embedding_field: str = "embedding"
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))  # all-mpnet-base-v2 dimension
    similarity_metric: str = os.getenv("MONGO_SIMILARITY_METRIC", "cosine")

    # Search performance parameters
    num_candidates_multiplier: int = int(os.getenv("ATLAS_CANDIDATES_MULTIPLIER", "10"))
    max_candidates: int = int(os.getenv("ATLAS_MAX_CANDIDATES", "1000"))

    # Fallback configuration
    enable_atlas_search: bool = os.getenv("ENABLE_ATLAS_SEARCH", "auto") != "false"
    enable_manual_fallback: bool = os.getenv("ENABLE_MANUAL_FALLBACK", "true") != "false"
    manual_fallback_threshold: int = int(os.getenv("MANUAL_FALLBACK_THRESHOLD", "10000"))


class EnhancedMongoConnectionManager:
    """
    Enhanced MongoDB connection manager with Atlas Vector Search support.
    Production-ready with comprehensive error handling and fallback mechanisms.
    """

    def __init__(self, config: Optional[MongoConfig] = None, atlas_config: Optional[AtlasVectorSearchConfig] = None):
        self._config = config or MongoConfig()
        self.atlas_config = atlas_config or AtlasVectorSearchConfig()

        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connected: bool = False
        self._is_atlas: bool = False
        self._vector_search_available: bool = False
        self._connection_errors: List[str] = []

        logger.info(f"MongoDB manager initialized for database: {self._config.db_name}")

    async def connect(self) -> bool:
        """Enhanced connection with Atlas detection and fallback"""
        self._connection_errors.clear()

        # Try Atlas connection first if configured
        if self.atlas_config.atlas_uri and self.atlas_config.enable_atlas_search:
            logger.info("Attempting MongoDB Atlas connection...")
            if await self._connect_atlas():
                return True

        # Fallback to local connection
        logger.info("Attempting local MongoDB connection...")
        return await self._connect_local()

    async def _connect_atlas(self) -> bool:
        """Connect to MongoDB Atlas with vector search capabilities"""
        try:
            logger.info("🌐 Connecting to MongoDB Atlas...")

            connection_settings = {
                **self._config.get_connection_settings(),
                "retryWrites": True,
                "w": "majority"
            }

            self.client = AsyncIOMotorClient(
                self.atlas_config.atlas_uri,
                **connection_settings
            )

            # Test connection with ping
            await asyncio.wait_for(
                self.client.admin.command("ping"),
                timeout=10.0
            )

            self.database = self.client.get_database(self._config.db_name)

            # Check for vector search capabilities
            self._vector_search_available = await self._check_vector_search_support()

            self._connected = True
            self._is_atlas = True

            logger.info(f"✅ MongoDB Atlas connected successfully")
            logger.info(f"   Database: {self._config.db_name}")
            logger.info(f"   Vector Search: {'Available' if self._vector_search_available else 'Not Available'}")
            return True

        except asyncio.TimeoutError:
            error = "Atlas connection timeout"
            self._connection_errors.append(error)
            logger.warning(f"⏰ {error}")
            return False
        except Exception as e:
            error = f"Atlas connection failed: {e}"
            self._connection_errors.append(error)
            logger.warning(f"⚠️ {error}")
            return False

    # Location: app/database/mongo_connection.py
    # REPLACE the _connect_local method with this version

    async def _connect_local(self) -> bool:
        """Connect to local MongoDB (with Atlas Local detection)"""
        try:
            # Build URI
            uri = self._config.build_uri()
            logger.info(f"🏠 Connecting to local MongoDB: {self._config.host}:{self._config.port}")
            logger.debug(f"Using URI: {uri.replace(self._config.password, '***')}")

            connection_settings = self._config.get_connection_settings()

            # Override timeouts for local connection
            connection_settings.update({
                "serverSelectionTimeoutMS": 3000,
                "connectTimeoutMS": 3000,
                "socketTimeoutMS": 5000,
            })

            if "directConnection=true" in uri:
                logger.info("🔗 Using direct connection (bypasses replica set discovery)")

            self.client = AsyncIOMotorClient(
                uri,
                **connection_settings
            )

            try:
                # Test connection
                await asyncio.wait_for(
                    self.client.admin.command("ping"),
                    timeout=5.0
                )

                # Get database
                self.database = self.client.get_database(self._config.db_name)

                # Verify database is accessible
                await asyncio.wait_for(
                    self.database.command("ping"),
                    timeout=3.0
                )

            except asyncio.TimeoutError:
                raise ConnectionFailure("MongoDB ping command timed out")
            except Exception as e:
                raise ConnectionFailure(f"MongoDB connection test failed: {e}")

            # Connection successful
            self._connected = True

            # DON'T hardcode these to False! Check for vector search support instead
            # self._is_atlas = False  # ← REMOVE THIS LINE
            # self._vector_search_available = False  # ← REMOVE THIS LINE

            # INSTEAD, check for vector search capabilities!
            logger.info("🔍 Checking for vector search capabilities...")
            self._vector_search_available = await self._check_vector_search_support()

            # If vector search is available, we're on Atlas Local
            if self._vector_search_available:
                self._is_atlas = True
                logger.info("🌟 MongoDB Atlas Local detected with vector search!")
            else:
                self._is_atlas = False
                logger.info("📦 Standard MongoDB detected (no vector search)")

            logger.info(f"✅ Local MongoDB connected successfully")
            logger.info(f"   Database: {self._config.db_name}")
            logger.info(f"   Host: {self._config.host}:{self._config.port}")
            logger.info(f"   Direct connection: {'directConnection=true' in uri}")
            logger.info(f"   Atlas Local: {self._is_atlas}")  # Now will be True!
            logger.info(f"   Vector Search: {self._vector_search_available}")  # Now will be True!

            return True

        except ConnectionFailure as e:
            error = f"Local MongoDB connection failed: {e}"
            self._connection_errors.append(error)
            logger.error(f"❌ {error}")

            # Provide helpful troubleshooting info
            if "nodename nor servname provided" in str(e) or "mongodb-atlas-local" in str(e):
                logger.info("💡 Replica set discovery issue detected")
                logger.info("   Ensure MONGO_URI includes directConnection=true")
                logger.info(
                    "   Example: mongodb://root:example@localhost:27017/chatbot_app?authSource=admin&directConnection=true")
            else:
                logger.info("💡 Try: docker-compose up mongodb")

            return False
        except Exception as e:
            error = f"Local MongoDB connection failed: {e}"
            self._connection_errors.append(error)
            logger.error(f"❌ {error}")
            return False

    async def _check_vector_search_support(self) -> bool:
        """Check if the current MongoDB instance supports vector search"""
        try:
            # Method 1: Try to use $vectorSearch directly (most reliable test)
            collection = self.database.get_collection(self._config.embeddings_collection)

            # Your actual index name from .env
            index_name = 'vector_idx_embeddings_embedding'

            try:
                # Test $vectorSearch aggregation with your actual index
                test_pipeline = [
                    {
                        '$vectorSearch': {
                            'index': index_name,
                            'path': 'embedding',
                            'queryVector': [0.1] * self.atlas_config.embedding_dimension,
                            'numCandidates': 10,
                            'limit': 1
                        }
                    }
                ]

                # Execute the pipeline
                cursor = collection.aggregate(test_pipeline, maxTimeMS=5000)
                results = await cursor.to_list(1)

                # If we get here without error, vector search is working!
                logger.info(f"✅ Vector search is WORKING with index '{index_name}'!")

                # Mark as Atlas since vector search is working
                self._is_atlas = True  # Important: Set this!

                return True

            except OperationFailure as e:
                error_msg = str(e).lower()

                if "$vectorsearch is not supported" in error_msg:
                    logger.info("❌ $vectorSearch not supported - not Atlas Local")
                    return False

                elif "index not found" in error_msg or "no index found" in error_msg:
                    # This is actually GOOD - means vector search IS supported
                    logger.info("✅ Vector search IS supported (just need to create index)")

                    # Method 2: Check if our specific indexes exist
                    try:
                        cursor = collection.list_search_indexes()
                        indexes = await cursor.to_list(None)

                        # Check for our specific index names
                        our_indexes = [
                            'vector_idx_embeddings_embedding',
                            'vector_idx_knowledge_vectors_embedding'
                        ]

                        for idx in indexes:
                            idx_name = idx.get('name', '')
                            if idx_name in our_indexes:
                                status = idx.get('status', 'unknown')
                                queryable = idx.get('queryable', False)

                                logger.info(f"🔍 Found index '{idx_name}': {status} (queryable: {queryable})")

                                if status == 'READY' and queryable:
                                    logger.info("✅ Vector search index is READY and queryable!")
                                    self._is_atlas = True  # Mark as Atlas
                                    return True

                        # If we can list search indexes, we have Atlas Local
                        if len(indexes) > 0:
                            logger.info(f"✅ Found {len(indexes)} search indexes - Atlas Local confirmed")
                            self._is_atlas = True
                            return True

                    except Exception as list_error:
                        logger.debug(f"Could not list search indexes: {list_error}")

                    # Even if index doesn't exist, vector search is supported
                    self._is_atlas = True  # Mark as Atlas since $vectorSearch is recognized
                    return True

                else:
                    # Some other error but $vectorSearch is recognized
                    logger.info(f"⚠️ Vector search test had issues but is supported: {str(e)[:100]}")
                    self._is_atlas = True
                    return True

        except Exception as e:
            logger.debug(f"Vector search check failed (may be normal for standard MongoDB): {e}")

            # Final fallback: Check build info for Atlas indicators
            try:
                build_info = await self.client.admin.command('buildInfo')
                version = build_info.get('version', '')

                # Check for Atlas Local indicators
                if any([
                    'atlas' in version.lower(),
                    self.client.options.replica_set_name == 'mongodb-atlas-local' if hasattr(self.client.options,
                                                                                             'replica_set_name') else False
                ]):
                    logger.info("🌟 MongoDB Atlas Local detected via build info")
                    self._is_atlas = True
                    return True

            except:
                pass

            return False

    async def create_vector_search_index(
            self,
            collection_name: str = "embeddings",
            index_name: Optional[str] = None
    ) -> bool:
        """
        Create vector search index on Atlas using the correct motor 3.7.1 API.
        """
        if not self._is_atlas or not self._connected:
            logger.warning("⚠️ Vector search index creation requires Atlas connection")
            return False

        try:
            from pymongo.operations import SearchIndexModel

            index_name = index_name or self.atlas_config.vector_index_name
            collection = self.database.get_collection(collection_name)

            # Define the index configuration with correct types for MongoDB Atlas Local
            index_definition = {
                "mappings": {
                    "dynamic": True,  # Allows indexing of fields not explicitly defined
                    "fields": {
                        "embedding": {
                            "type": "knnVector",  # For vector search
                            "dimensions": self.atlas_config.embedding_dimension,
                            "similarity": self.atlas_config.similarity_metric.lower()
                        },
                        "category": {
                            "type": "string"  # CHANGED from "filter" to "string"
                        },
                        "source": {
                            "type": "string"  # CHANGED from "filter" to "string"
                        }
                    }
                }
            }

            # Check if the index already exists to avoid errors
            try:
                existing_indexes = await collection.list_search_indexes().to_list(length=10)
                if any(idx['name'] == index_name for idx in existing_indexes):
                    logger.info(f"📊 Vector search index '{index_name}' already exists for {collection_name}")
                    return True
            except Exception as e:
                logger.debug(f"Could not list existing indexes (may be normal): {e}")

            # Create the SearchIndexModel object (required for motor 3.7.1)
            index_model = SearchIndexModel(
                definition=index_definition,
                name=index_name
            )

            # Create the search index using the model
            await collection.create_search_index(model=index_model)

            logger.info(f"📊 Vector search index '{index_name}' creation initiated for {collection_name}")
            return True

        except ImportError as e:
            logger.error(f"❌ SearchIndexModel not available - motor/pymongo version issue: {e}")
            return False
        except Exception as e:
            # Don't log the full error if it's just that the index exists
            if "already exists" in str(e).lower():
                logger.info(f"📊 Vector search index '{index_name}' already exists.")
                return True
            logger.error(f"❌ Failed to create vector search index: {e}")
            return False

    async def vector_search(
            self,
            collection_name: str,
            query_vector: List[float],
            limit: int = 10,
            num_candidates: Optional[int] = None,
            filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search using Atlas $vectorSearch or manual fallback.

        Args:
            collection_name: Collection to search
            query_vector: Query embedding vector
            limit: Number of results to return
            num_candidates: Number of candidates for ANN search
            filters: Optional metadata filters

        Returns:
            List of search results with scores
        """
        if not self._connected:
            logger.warning("⚠️ MongoDB not connected, cannot perform vector search")
            return []

        collection = self.database.get_collection(collection_name)

        # Use Atlas vector search if available
        if self._is_atlas and self._vector_search_available:
            logger.debug(f"🔍 Using Atlas vector search for {collection_name}")
            return await self._atlas_vector_search(
                collection, query_vector, limit, num_candidates, filters
            )

        # Fallback to manual similarity calculation
        if self.atlas_config.enable_manual_fallback:
            logger.debug(f"🔍 Using manual vector search for {collection_name}")
            return await self._manual_vector_search(
                collection, query_vector, limit, filters
            )

        logger.warning("❌ No vector search method available")
        return []

    async def _atlas_vector_search(
            self,
            collection: AsyncIOMotorCollection,
            query_vector: List[float],
            limit: int,
            num_candidates: Optional[int],
            filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform Atlas vector search using $vectorSearch aggregation"""
        try:
            # Calculate num_candidates with optimization
            if num_candidates is None:
                num_candidates = min(
                    max(limit * self.atlas_config.num_candidates_multiplier, 100),
                    self.atlas_config.max_candidates
                )

            # Build vector search stage
            vector_search_stage = {
                "$vectorSearch": {
                    "index": self.atlas_config.vector_index_name,
                    "path": self.atlas_config.embedding_field,
                    "queryVector": query_vector,
                    "numCandidates": num_candidates,
                    "limit": limit
                }
            }

            # Add filters if provided
            if filters:
                vector_search_stage["$vectorSearch"]["filter"] = filters

            # Build comprehensive aggregation pipeline
            pipeline = [
                vector_search_stage,
                {
                    "$project": {
                        "title": 1,
                        "content": 1,
                        "document_id": 1,
                        "chunk_index": 1,
                        "category": 1,
                        "source": 1,
                        "embedding_model": 1,
                        "ingested_at": 1,
                        "metadata": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            # Execute search with timeout
            cursor = collection.aggregate(pipeline, maxTimeMS=5000)
            results = await cursor.to_list(length=limit)

            logger.debug(f"✅ Atlas vector search returned {len(results)} results")
            logger.debug(f"   Query vector dim: {len(query_vector)}")
            logger.debug(f"   Candidates: {num_candidates}")
            logger.debug(f"   Filters: {filters}")

            return results

        except OperationFailure as e:
            logger.error(f"❌ Atlas vector search operation failed: {e}")

            # Check if it's an index issue
            if "index not found" in str(e).lower():
                logger.warning("📊 Vector search index not found, falling back to manual search")
                self._vector_search_available = False

            # Fallback to manual search if Atlas fails
            if self.atlas_config.enable_manual_fallback:
                logger.info("🔄 Falling back to manual vector search")
                return await self._manual_vector_search(collection, query_vector, limit, filters)

            return []

        except Exception as e:
            logger.error(f"❌ Unexpected Atlas vector search error: {e}")

            # Fallback to manual search if Atlas fails
            if self.atlas_config.enable_manual_fallback:
                logger.info("🔄 Falling back to manual vector search due to error")
                return await self._manual_vector_search(collection, query_vector, limit, filters)

            return []

    async def _manual_vector_search(
            self,
            collection: AsyncIOMotorCollection,
            query_vector: List[float],
            limit: int,
            filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Manual vector search using cosine similarity (fallback)"""
        try:
            # Build query with filters
            query = filters or {}

            # Ensure we have embeddings
            query[self.atlas_config.embedding_field] = {"$exists": True, "$ne": None}

            # Limit document retrieval for performance
            max_docs = min(self.atlas_config.manual_fallback_threshold, 10000)

            # Get documents with projection to include necessary fields
            projection = {
                "title": 1,
                "content": 1,
                "document_id": 1,
                "chunk_index": 1,
                "category": 1,
                "source": 1,
                "embedding_model": 1,
                "ingested_at": 1,
                "metadata": 1,
                self.atlas_config.embedding_field: 1
            }

            cursor = collection.find(query, projection).limit(max_docs)
            documents = await cursor.to_list(length=max_docs)

            if not documents:
                logger.debug("🔍 No documents found for manual vector search")
                return []

            # Calculate similarities
            similarities = []

            for doc in documents:
                embedding = doc.get(self.atlas_config.embedding_field)
                if not embedding or not isinstance(embedding, list):
                    continue

                # Validate embedding dimension
                if len(embedding) != len(query_vector):
                    logger.debug(f"⚠️ Embedding dimension mismatch: {len(embedding)} vs {len(query_vector)}")
                    continue

                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_vector, embedding)

                # Add score to document (Atlas-compatible format)
                doc["score"] = float(similarity)
                similarities.append((similarity, doc))

            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[0], reverse=True)
            results = [doc for _, doc in similarities[:limit]]

            logger.debug(f"✅ Manual vector search returned {len(results)} results from {len(documents)} documents")
            logger.debug(f"   Top score: {results[0]['score']:.4f}" if results else "   No results")

            return results

        except Exception as e:
            logger.error(f"❌ Manual vector search failed: {e}")
            return []

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if len(a) != len(b):
                logger.warning(f"⚠️ Vector dimension mismatch: {len(a)} vs {len(b)}")
                return 0.0

            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))

            if norm_a == 0 or norm_b == 0:
                return 0.0

            similarity = dot_product / (norm_a * norm_b)

            # Clamp to [-1, 1] to handle floating point precision issues
            return max(-1.0, min(1.0, similarity))

        except Exception as e:
            logger.error(f"❌ Cosine similarity calculation failed: {e}")
            return 0.0

    # Core Properties and Methods
    @property
    def is_atlas(self) -> bool:
        """Check if connected to Atlas"""
        return self._is_atlas

    @property
    def vector_search_available(self) -> bool:
        """Check if vector search is available"""
        return self._vector_search_available

    @property
    def is_connected(self) -> bool:
        """Check if MongoDB connection is active"""
        return self._connected and self.client is not None

    def _require_db(self) -> AsyncIOMotorDatabase:
        """Require database connection (internal method)"""
        if not self._connected or self.database is None:
            raise RuntimeError("MongoDB is not connected. Call connect() first.")
        return self.database

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get the database instance (public method)"""
        return self._require_db()

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Get a collection by name"""
        db = self._require_db()
        return db.get_collection(name)

    # Collection Accessors
    def documents(self) -> AsyncIOMotorCollection:
        """Get documents collection"""
        return self.get_collection(self._config.documents_collection)

    def embeddings(self) -> AsyncIOMotorCollection:
        """Get embeddings collection"""
        return self.get_collection(self._config.embeddings_collection)

    def knowledge_vectors(self) -> AsyncIOMotorCollection:
        """Get knowledge_vectors collection"""
        return self.get_collection(self._config.knowledge_vectors_collection)

    def conversations(self) -> AsyncIOMotorCollection:
        """Get conversations collection"""
        return self.get_collection(self._config.conversations_collection)

    def knowledge_base(self) -> AsyncIOMotorCollection:
        """Get knowledge_base collection"""
        return self.get_collection(self._config.knowledge_base_collection)

    async def ensure_indexes(self) -> None:
        """Enhanced index creation with vector search support"""
        if not self._connected:
            logger.warning("⚠️ Cannot create indexes - not connected")
            return

        logger.info("📊 Creating MongoDB indexes...")

        try:
            # Create traditional indexes first
            await self._create_traditional_indexes()

            # Create vector search indexes if on Atlas
            if self._is_atlas:
                await self._create_vector_search_indexes()

            logger.info("✅ MongoDB indexes created successfully")

        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
            raise

    async def _create_traditional_indexes(self):
        """Create traditional MongoDB indexes"""
        db = self._require_db()

        try:
            # Documents collection indexes
            docs = db.get_collection(self._config.documents_collection)
            await docs.create_index([("document_type", ASCENDING)], name="ix_document_type", background=True)
            await docs.create_index([("processing_status", ASCENDING)], name="ix_processing_status", background=True)
            await docs.create_index([("external_id", ASCENDING)], name="ix_external_id", sparse=True, background=True)
            await docs.create_index([("ingested_at", ASCENDING)], name="ix_ingested_at", background=True)

            # Embeddings collection indexes
            emb = db.get_collection(self._config.embeddings_collection)

            # Text search index for hybrid search
            try:
                await emb.create_index(
                    [("title", TEXT), ("content", TEXT)],
                    name="emb_text_title_content",
                    default_language="english",
                    weights={"title": 3, "content": 1},
                    background=True
                )
                logger.info("📝 Text search index created for embeddings")
            except Exception as e:
                logger.warning(f"⚠️ Text index creation failed (may already exist): {e}")

            await emb.create_index([("document_id", ASCENDING), ("chunk_index", ASCENDING)],
                                 name="ix_doc_chunk", unique=True, background=True)
            await emb.create_index([("category", ASCENDING)], name="ix_category", sparse=True, background=True)
            await emb.create_index([("source", ASCENDING)], name="ix_source", sparse=True, background=True)
            await emb.create_index([("embedding_model", ASCENDING)], name="ix_embedding_model", sparse=True, background=True)
            await emb.create_index([("ingested_at", ASCENDING)], name="ix_emb_ingested_at", background=True)

            # Knowledge vectors collection indexes
            kv = db.get_collection(self._config.knowledge_vectors_collection)
            await kv.create_index([("scylla_key", ASCENDING)], name="ix_scylla_key", unique=True, background=True)
            await kv.create_index([("source", ASCENDING)], name="ix_kv_source", sparse=True, background=True)
            await kv.create_index([("last_synced_at", ASCENDING)], name="ix_last_synced_at", background=True)

            # Text search for knowledge vectors
            try:
                await kv.create_index(
                    [("question", TEXT), ("answer", TEXT)],
                    name="kv_text_q_a",
                    default_language="english",
                    weights={"question": 4, "answer": 1},
                    background=True
                )
                logger.info("📝 Text search index created for knowledge vectors")
            except Exception as e:
                logger.warning(f"⚠️ Knowledge vectors text index creation failed: {e}")

            # Conversations collection indexes (if needed)
            conv = db.get_collection(self._config.conversations_collection)
            await conv.create_index([("user_id", ASCENDING), ("timestamp", ASCENDING)],
                                  name="ix_user_timestamp", background=True)

            logger.info("✅ Traditional indexes created successfully")

        except Exception as e:
            logger.error(f"❌ Failed to create traditional indexes: {e}")
            raise

    async def _create_vector_search_indexes(self):
        """Create vector search indexes for Atlas"""
        collections_to_index = [
            self._config.embeddings_collection,
            self._config.knowledge_vectors_collection
        ]

        for collection_name in collections_to_index:
            try:
                index_name = f"vector_index_{collection_name}"
                success = await self.create_vector_search_index(collection_name, index_name)

                if success:
                    logger.info(f"📊 Vector search index created for {collection_name}")
                else:
                    logger.warning(f"⚠️ Vector search index creation failed for {collection_name}")

            except Exception as e:
                logger.error(f"❌ Failed to create vector search index for {collection_name}: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with detailed diagnostics"""
        health_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "connected": self._connected,
            "database": self._config.db_name,
            "connection_type": "atlas" if self._is_atlas else "local",
            "is_atlas": self._is_atlas,
            "vector_search_available": self._vector_search_available,
            "connection_errors": self._connection_errors,
            "atlas_config": {
                "vector_index_name": self.atlas_config.vector_index_name,
                "embedding_dimension": self.atlas_config.embedding_dimension,
                "similarity_metric": self.atlas_config.similarity_metric,
                "enable_manual_fallback": self.atlas_config.enable_manual_fallback
            },
            "collections": {},
            "indexes": {},
            "vector_search": {},
            "performance": {},
            "errors": []
        }

        if not self._connected:
            health_info["status"] = "disconnected"
            health_info["errors"].append("Not connected to MongoDB")
            return health_info

        try:
            # Test basic connection
            ping_start = datetime.utcnow()
            await asyncio.wait_for(self.client.admin.command("ping"), timeout=5.0)
            ping_time = (datetime.utcnow() - ping_start).total_seconds()

            health_info["ping"] = {
                "status": "success",
                "response_time_ms": ping_time * 1000
            }

            # Check collections
            db = self.database
            collection_names = await db.list_collection_names()
            health_info["collections"]["available"] = collection_names

            # Check collection counts
            for collection_name in [self._config.embeddings_collection,
                                  self._config.knowledge_vectors_collection,
                                  self._config.documents_collection]:
                if collection_name in collection_names:
                    try:
                        collection = db.get_collection(collection_name)
                        count = await collection.count_documents({})
                        health_info["collections"][collection_name] = {
                            "document_count": count,
                            "exists": True
                        }
                    except Exception as e:
                        health_info["collections"][collection_name] = {
                            "error": str(e),
                            "exists": True
                        }

            # Check indexes
            try:
                emb_collection = db.get_collection(self._config.embeddings_collection)
                indexes = await emb_collection.list_indexes().to_list(length=None)
                health_info["indexes"]["embeddings"] = [idx["name"] for idx in indexes]
            except Exception as e:
                health_info["indexes"]["embeddings"] = {"error": str(e)}

            # Check vector search capabilities (Atlas only)
            if self._is_atlas:
                try:
                    embeddings_collection = db.get_collection(self._config.embeddings_collection)
                    search_indexes = await embeddings_collection.list_search_indexes().to_list(length=None)

                    vector_indexes = [idx for idx in search_indexes
                                    if idx.get("name") == self.atlas_config.vector_index_name]

                    health_info["vector_search"] = {
                        "index_exists": len(vector_indexes) > 0,
                        "index_status": vector_indexes[0].get("status") if vector_indexes else "not_found",
                        "index_definition": vector_indexes[0].get("latestDefinition") if vector_indexes else None,
                        "total_search_indexes": len(search_indexes),
                        "all_search_indexes": [idx.get("name") for idx in search_indexes]
                    }

                    # Update vector search availability based on index status
                    if vector_indexes:
                        status = vector_indexes[0].get("status")
                        self._vector_search_available = status in ["READY", "BUILDING"]

                except Exception as e:
                    health_info["vector_search"] = {"error": str(e)}

            # Performance check - test a simple query
            try:
                perf_start = datetime.utcnow()
                test_collection = db.get_collection(self._config.embeddings_collection)
                await test_collection.find_one({})
                query_time = (datetime.utcnow() - perf_start).total_seconds()

                health_info["performance"] = {
                    "simple_query_ms": query_time * 1000,
                    "connection_pool_size": getattr(self.client, 'max_pool_size', 'unknown')
                }
            except Exception as e:
                health_info["performance"] = {"error": str(e)}

            # Determine overall status
            if not health_info["errors"]:
                if self._is_atlas and self._vector_search_available:
                    health_info["status"] = "healthy_with_vector_search"
                elif self._is_atlas and not self._vector_search_available:
                    health_info["status"] = "healthy_no_vector_search"
                else:
                    health_info["status"] = "healthy_local"
            else:
                health_info["status"] = "degraded"

        except asyncio.TimeoutError:
            health_info["status"] = "unhealthy"
            health_info["errors"].append("Health check timeout")
        except Exception as e:
            health_info["status"] = "unhealthy"
            health_info["errors"].append(f"Health check failed: {e}")

        return health_info

    async def disconnect(self) -> None:
        """Close connection with cleanup"""
        try:
            if self.client:
                self.client.close()
                logger.info("🔌 MongoDB connection closed")
        except Exception as e:
            logger.error(f"❌ Error during MongoDB disconnect: {e}")
        finally:
            self.client = None
            self.database = None
            self._connected = False
            self._is_atlas = False
            self._vector_search_available = False

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (f"EnhancedMongoConnectionManager("
                f"connected={self._connected}, "
                f"atlas={self._is_atlas}, "
                f"vector_search={self._vector_search_available}, "
                f"db={self._config.db_name})")


# Compatibility layer for existing code
class MongoConnectionManager(EnhancedMongoConnectionManager):
    """
    Legacy compatibility class.
    Inherits all enhanced functionality while maintaining backward compatibility.
    """

    def __init__(self):
        config = MongoConfig()
        atlas_config = AtlasVectorSearchConfig()
        super().__init__(config, atlas_config)
        logger.info("MongoDB connection manager initialized (legacy compatibility mode)")


# Global instances - Enhanced and Legacy
enhanced_mongo_manager: Optional[EnhancedMongoConnectionManager] = None
mongo_manager: Optional[EnhancedMongoConnectionManager] = None

# Legacy instance for backward compatibility
legacy_mongo_manager: Optional[MongoConnectionManager] = None


async def init_enhanced_mongo() -> bool:
    """Initialize enhanced MongoDB connection with comprehensive setup"""
    global enhanced_mongo_manager, mongo_manager, legacy_mongo_manager
    logger.info("🚀 Initializing Enhanced MongoDB Connection...")

    if enhanced_mongo_manager is None:
        enhanced_mongo_manager = EnhancedMongoConnectionManager()
        mongo_manager = enhanced_mongo_manager
        legacy_mongo_manager = MongoConnectionManager()

    try:
        # Connect to MongoDB
        success = await enhanced_mongo_manager.connect()

        if success:
            # Create indexes
            await enhanced_mongo_manager.ensure_indexes()
            logger.info("✅ Enhanced MongoDB initialized successfully")
            return True
        else:
            logger.error("❌ Failed to connect to MongoDB")
            return False

    except Exception as e:
        logger.error(f"❌ Enhanced MongoDB initialization failed: {e}")
        return False


async def close_enhanced_mongo() -> None:
    """Close enhanced MongoDB connection"""
    await enhanced_mongo_manager.disconnect()


# Legacy initialization functions for backward compatibility
async def init_mongo() -> bool:
    """Legacy initialization function"""
    return await init_enhanced_mongo()


async def close_mongo() -> None:
    """Legacy close function"""
    await close_enhanced_mongo()


def get_mongo_manager() -> "EnhancedMongoConnectionManager":
    """
    Returns the singleton instance of the EnhancedMongoConnectionManager.
    Raises a RuntimeError if it has not been initialized.
    """
    # The 'enhanced_mongo_manager' global is set by 'init_enhanced_mongo'
    if enhanced_mongo_manager is None:
        raise RuntimeError(
            "MongoConnectionManager has not been initialized. "
            "Ensure init_enhanced_mongo() is called at application startup."
        )
    return enhanced_mongo_manager


# Export all public components
__all__ = [
    'MongoConfig',
    'AtlasVectorSearchConfig',
    'EnhancedMongoConnectionManager',
    'MongoConnectionManager',
    'enhanced_mongo_manager',
    'mongo_manager',
    'legacy_mongo_manager',
    'init_enhanced_mongo',
    'close_enhanced_mongo',
    'init_mongo',
    'close_mongo',
    'get_mongo_manager'
]