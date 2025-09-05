#!/usr/bin/env python3
"""
MongoDB Optimization Script - Create optimal indexes and performance configurations.
Run this script to optimize MongoDB collections for the MultiDB Chatbot application.
"""

import asyncio
import logging
import sys
import os
from typing import List, Dict, Any
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.connections.mongo_connection import get_mongo_manager
from motor.motor_asyncio import AsyncIOMotorCollection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MongoDBOptimizer:
    """MongoDB performance optimizer with advanced indexing strategies."""
    
    def __init__(self):
        self.mongo_manager = None
        self.database = None
        self.optimization_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indexes_created": [],
            "indexes_existing": [],
            "optimizations_applied": [],
            "errors": []
        }
    
    async def initialize(self):
        """Initialize MongoDB connection."""
        try:
            self.mongo_manager = get_mongo_manager()
            if not self.mongo_manager.is_connected:
                success = await self.mongo_manager.connect()
                if not success:
                    raise RuntimeError("Failed to connect to MongoDB")
            
            self.database = self.mongo_manager.database
            logger.info(f"Connected to MongoDB database: {self.database.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise
    
    async def optimize_embeddings_collection(self):
        """Optimize the embeddings collection with advanced indexes."""
        logger.info("Optimizing embeddings collection...")
        
        collection = self.database.embeddings
        indexes_to_create = [
            # Primary vector search index (Atlas Vector Search)
            # Note: This needs to be created through MongoDB Atlas UI or API
            
            # Compound index for category-time-based queries
            {
                "index": [("category", 1), ("created_at", -1), ("score", -1)],
                "name": "idx_category_time_score",
                "options": {"background": True}
            },
            
            # Document and chunk lookup
            {
                "index": [("document_id", 1), ("chunk_index", 1)],
                "name": "idx_document_chunk",
                "options": {"background": True, "unique": True}
            },
            
            # User-specific content
            {
                "index": [("user_id", 1), ("category", 1), ("created_at", -1)],
                "name": "idx_user_category_time",
                "options": {"background": True}
            },
            
            # Content length for filtering
            {
                "index": [("content_length", 1)],
                "name": "idx_content_length",
                "options": {"background": True, "sparse": True}
            },
            
            # Tags array index
            {
                "index": [("tags", 1)],
                "name": "idx_tags",
                "options": {"background": True, "sparse": True}
            },
            
            # Source and type filtering
            {
                "index": [("source", 1), ("document_type", 1)],
                "name": "idx_source_type",
                "options": {"background": True, "sparse": True}
            },
            
            # Text search index for fallback
            {
                "index": [("title", "text"), ("content", "text")],
                "name": "idx_text_search",
                "options": {
                    "background": True,
                    "weights": {"title": 3, "content": 1},
                    "default_language": "english"
                }
            }
        ]
        
        await self._create_indexes(collection, indexes_to_create)
        
        # Set collection-level options for performance
        await self._optimize_collection_settings(collection, {
            "comment": "Optimized for vector search and document retrieval"
        })
        
        logger.info("Embeddings collection optimization completed")
    
    async def optimize_knowledge_vectors_collection(self):
        """Optimize the knowledge_vectors collection."""
        logger.info("Optimizing knowledge_vectors collection...")
        
        collection = self.database.knowledge_vectors
        indexes_to_create = [
            # Primary vector search index (Atlas Vector Search)
            # Note: This needs to be created through MongoDB Atlas UI or API
            
            # ScyllaDB key for cross-database lookups
            {
                "index": [("scylla_key", 1)],
                "name": "idx_scylla_key",
                "options": {"background": True, "unique": True}
            },
            
            # Category and update time
            {
                "index": [("category", 1), ("updated_at", -1)],
                "name": "idx_category_updated",
                "options": {"background": True}
            },
            
            # FAQ confidence scoring
            {
                "index": [("confidence", -1), ("category", 1)],
                "name": "idx_confidence_category",
                "options": {"background": True}
            },
            
            # Version and lifecycle management
            {
                "index": [("version", 1), ("is_active", 1)],
                "name": "idx_version_active",
                "options": {"background": True, "sparse": True}
            },
            
            # Text search for knowledge base
            {
                "index": [("question", "text"), ("answer", "text")],
                "name": "idx_knowledge_text_search",
                "options": {
                    "background": True,
                    "weights": {"question": 5, "answer": 1},
                    "default_language": "english"
                }
            }
        ]
        
        await self._create_indexes(collection, indexes_to_create)
        logger.info("Knowledge vectors collection optimization completed")
    
    async def create_performance_collections(self):
        """Create and optimize performance monitoring collections."""
        logger.info("Creating performance monitoring collections...")
        
        # Query cache collection with TTL
        cache_collection = self.database.query_cache
        cache_indexes = [
            {
                "index": [("query_key", 1)],
                "name": "idx_query_key",
                "options": {"background": True, "unique": True}
            },
            {
                "index": [("created_at", 1)],
                "name": "idx_ttl_cache",
                "options": {"background": True, "expireAfterSeconds": 3600}
            },
            {
                "index": [("cache_category", 1), ("created_at", -1)],
                "name": "idx_cache_category_time",
                "options": {"background": True, "sparse": True}
            }
        ]
        await self._create_indexes(cache_collection, cache_indexes)
        
        # Performance metrics collection
        metrics_collection = self.database.performance_metrics
        metrics_indexes = [
            {
                "index": [("timestamp", -1), ("service", 1)],
                "name": "idx_metrics_time_service",
                "options": {"background": True}
            },
            {
                "index": [("service", 1), ("operation", 1), ("timestamp", -1)],
                "name": "idx_service_operation_time",
                "options": {"background": True}
            },
            {
                "index": [("success", 1), ("timestamp", -1)],
                "name": "idx_success_time",
                "options": {"background": True}
            },
            {
                "index": [("timestamp", 1)],
                "name": "idx_metrics_ttl",
                "options": {"background": True, "expireAfterSeconds": 2592000}  # 30 days
            }
        ]
        await self._create_indexes(metrics_collection, metrics_indexes)
        
        # User preferences collection
        prefs_collection = self.database.user_preferences
        prefs_indexes = [
            {
                "index": [("user_id", 1)],
                "name": "idx_user_preferences",
                "options": {"background": True, "unique": True}
            },
            {
                "index": [("updated_at", -1)],
                "name": "idx_prefs_updated",
                "options": {"background": True}
            },
            {
                "index": [("preferences.theme", 1)],
                "name": "idx_theme_preference",
                "options": {"background": True, "sparse": True}
            }
        ]
        await self._create_indexes(prefs_collection, prefs_indexes)
        
        logger.info("Performance collections created and optimized")
    
    async def create_analytics_collections(self):
        """Create collections for advanced analytics."""
        logger.info("Creating analytics collections...")
        
        # Document analytics collection
        doc_analytics = self.database.document_analytics
        analytics_indexes = [
            {
                "index": [("date", -1), ("category", 1)],
                "name": "idx_date_category",
                "options": {"background": True}
            },
            {
                "index": [("document_id", 1), ("date", -1)],
                "name": "idx_doc_date",
                "options": {"background": True}
            },
            {
                "index": [("date", 1)],
                "name": "idx_analytics_ttl",
                "options": {"background": True, "expireAfterSeconds": 7776000}  # 90 days
            }
        ]
        await self._create_indexes(doc_analytics, analytics_indexes)
        
        # Search analytics collection
        search_analytics = self.database.search_analytics
        search_indexes = [
            {
                "index": [("query_hash", 1), ("timestamp", -1)],
                "name": "idx_query_hash_time",
                "options": {"background": True}
            },
            {
                "index": [("user_id", 1), ("timestamp", -1)],
                "name": "idx_user_search_time",
                "options": {"background": True}
            },
            {
                "index": [("timestamp", 1)],
                "name": "idx_search_analytics_ttl",
                "options": {"background": True, "expireAfterSeconds": 7776000}  # 90 days
            }
        ]
        await self._create_indexes(search_analytics, search_indexes)
        
        logger.info("Analytics collections created")
    
    async def _create_indexes(self, collection: AsyncIOMotorCollection, indexes: List[Dict]):
        """Create indexes for a collection."""
        collection_name = collection.name
        
        try:
            # Get existing indexes
            existing_indexes = await collection.list_indexes().to_list(None)
            existing_names = {idx.get('name') for idx in existing_indexes}
            
            for index_def in indexes:
                index_spec = index_def["index"]
                index_name = index_def["name"]
                index_options = index_def.get("options", {})
                
                if index_name in existing_names:
                    self.optimization_results["indexes_existing"].append({
                        "collection": collection_name,
                        "index": index_name
                    })
                    logger.info(f"Index {index_name} already exists on {collection_name}")
                else:
                    try:
                        await collection.create_index(index_spec, name=index_name, **index_options)
                        self.optimization_results["indexes_created"].append({
                            "collection": collection_name,
                            "index": index_name,
                            "spec": index_spec
                        })
                        logger.info(f"Created index {index_name} on {collection_name}")
                    except Exception as e:
                        error_msg = f"Failed to create index {index_name} on {collection_name}: {e}"
                        logger.error(error_msg)
                        self.optimization_results["errors"].append(error_msg)
                        
        except Exception as e:
            error_msg = f"Failed to process indexes for {collection_name}: {e}"
            logger.error(error_msg)
            self.optimization_results["errors"].append(error_msg)
    
    async def _optimize_collection_settings(self, collection: AsyncIOMotorCollection, settings: Dict):
        """Apply collection-level optimization settings."""
        try:
            # MongoDB doesn't have direct collection settings via motor
            # These would typically be set during collection creation or via MongoDB shell
            self.optimization_results["optimizations_applied"].append({
                "collection": collection.name,
                "settings": settings
            })
            logger.info(f"Collection settings noted for {collection.name}")
        except Exception as e:
            logger.error(f"Failed to apply settings to {collection.name}: {e}")
    
    async def create_atlas_vector_search_indexes(self):
        """Instructions for creating Atlas Vector Search indexes."""
        logger.info("Atlas Vector Search Index Instructions:")
        logger.info("=" * 60)
        
        atlas_instructions = [
            {
                "collection": "embeddings",
                "index_name": "vector_idx_embeddings_embedding",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 1024,
                            "similarity": "cosine"
                        },
                        {
                            "type": "filter",
                            "path": "category"
                        },
                        {
                            "type": "filter", 
                            "path": "user_id"
                        },
                        {
                            "type": "filter",
                            "path": "document_id"
                        }
                    ]
                }
            },
            {
                "collection": "knowledge_vectors",
                "index_name": "vector_idx_knowledge_vectors_embedding",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 1024,
                            "similarity": "cosine"
                        },
                        {
                            "type": "filter",
                            "path": "category"
                        },
                        {
                            "type": "filter",
                            "path": "scylla_key"
                        }
                    ]
                }
            }
        ]
        
        for instruction in atlas_instructions:
            logger.info(f"\nCollection: {instruction['collection']}")
            logger.info(f"Index Name: {instruction['index_name']}")
            logger.info(f"Definition: {instruction['definition']}")
        
        logger.info("\nTo create these indexes:")
        logger.info("1. Go to MongoDB Atlas Dashboard")
        logger.info("2. Navigate to Database → Search")
        logger.info("3. Create Search Index with the above definitions")
        logger.info("4. Wait for indexes to build (this may take several minutes)")
        
        self.optimization_results["atlas_instructions"] = atlas_instructions
    
    async def analyze_collection_stats(self):
        """Analyze collection statistics for optimization insights."""
        logger.info("Analyzing collection statistics...")
        
        collections_to_analyze = ["embeddings", "knowledge_vectors", "query_cache", "performance_metrics"]
        stats = {}
        
        for coll_name in collections_to_analyze:
            try:
                collection = self.database[coll_name]
                
                # Get basic stats
                doc_count = await collection.count_documents({})
                
                # Get collection stats via database command
                coll_stats = await self.database.command("collStats", coll_name)
                
                # Get index stats
                indexes = await collection.list_indexes().to_list(None)
                
                stats[coll_name] = {
                    "document_count": doc_count,
                    "size_bytes": coll_stats.get("size", 0),
                    "avg_obj_size": coll_stats.get("avgObjSize", 0),
                    "storage_size": coll_stats.get("storageSize", 0),
                    "total_indexes": len(indexes),
                    "index_sizes": coll_stats.get("totalIndexSize", 0)
                }
                
                logger.info(f"{coll_name}: {doc_count} docs, {stats[coll_name]['size_bytes']} bytes")
                
            except Exception as e:
                logger.warning(f"Could not get stats for {coll_name}: {e}")
                stats[coll_name] = {"error": str(e)}
        
        self.optimization_results["collection_stats"] = stats
        return stats
    
    async def run_optimization(self):
        """Run complete MongoDB optimization."""
        logger.info("Starting MongoDB optimization process...")
        
        try:
            await self.initialize()
            
            # Core collection optimizations
            await self.optimize_embeddings_collection()
            await self.optimize_knowledge_vectors_collection()
            
            # Performance and analytics collections
            await self.create_performance_collections()
            await self.create_analytics_collections()
            
            # Atlas Vector Search instructions
            await self.create_atlas_vector_search_indexes()
            
            # Collection analysis
            await self.analyze_collection_stats()
            
            logger.info("MongoDB optimization completed successfully!")
            
            # Print summary
            self._print_optimization_summary()
            
        except Exception as e:
            logger.error(f"MongoDB optimization failed: {e}")
            self.optimization_results["fatal_error"] = str(e)
            raise
        
        finally:
            if self.mongo_manager:
                await self.mongo_manager.disconnect()
    
    def _print_optimization_summary(self):
        """Print optimization summary."""
        results = self.optimization_results
        
        print("\n" + "=" * 60)
        print("MONGODB OPTIMIZATION SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Indexes Created: {len(results['indexes_created'])}")
        print(f"Indexes Already Existing: {len(results['indexes_existing'])}")
        print(f"Optimizations Applied: {len(results['optimizations_applied'])}")
        print(f"Errors: {len(results['errors'])}")
        
        if results["indexes_created"]:
            print("\nNew Indexes Created:")
            for idx in results["indexes_created"]:
                print(f"  - {idx['collection']}.{idx['index']}")
        
        if results["errors"]:
            print("\nErrors Encountered:")
            for error in results["errors"]:
                print(f"  - {error}")
        
        if "collection_stats" in results:
            print("\nCollection Statistics:")
            for coll, stats in results["collection_stats"].items():
                if "error" not in stats:
                    print(f"  {coll}: {stats['document_count']} docs, {stats['total_indexes']} indexes")
        
        print("\nNext Steps:")
        print("1. Create Atlas Vector Search indexes (see instructions above)")
        print("2. Monitor query performance in MongoDB Atlas")
        print("3. Consider sharding for large collections")
        print("4. Set up monitoring alerts for slow queries")
        print("=" * 60)


async def main():
    """Main optimization function."""
    optimizer = MongoDBOptimizer()
    await optimizer.run_optimization()


if __name__ == "__main__":
    asyncio.run(main())