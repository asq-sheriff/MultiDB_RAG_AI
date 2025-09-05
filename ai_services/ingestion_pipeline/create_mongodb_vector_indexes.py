"""
Create MongoDB Vector Search Indexes for Therapeutic Content
Sets up Atlas Vector Search indexes for the intelligent data router
"""

import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class MongoVectorIndexManager:
    """Manages MongoDB Atlas Vector Search indexes"""
    
    def __init__(self):
        self.mongo_client = None
        self.db = None
        
        # MongoDB connection parameters
        self.mongo_host = os.getenv("MONGO_HOST", "localhost")
        self.mongo_port = int(os.getenv("MONGO_PORT", "27017"))
        self.mongo_user = os.getenv("MONGO_USER", "root")
        self.mongo_password = os.getenv("MONGO_PASSWORD", "example")
        self.mongo_db = os.getenv("MONGO_DB", "chatbot_app")
    
    async def initialize(self):
        """Initialize MongoDB connection"""
        mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/?authSource=admin&directConnection=true"
        
        self.mongo_client = AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client[self.mongo_db]
        
        # Test connection
        await self.mongo_client.admin.command('ismaster')
        logger.info(f"✅ Connected to MongoDB: {self.mongo_host}:{self.mongo_port}")
    
    async def create_therapeutic_vector_indexes(self):
        """Create vector search indexes for therapeutic content"""
        
        # For local MongoDB (not Atlas), we'll create regular indexes
        # Atlas Vector Search is only available in MongoDB Atlas cloud
        
        try:
            print("🔍 Creating therapeutic content search indexes...")
            
            # 1. Compound index for care context and therapeutic category
            await self.db.therapeutic_content.create_index([
                ("care_contexts", 1),
                ("therapeutic_category", 1),
                ("urgency_level", 1)
            ], name="idx_therapeutic_context")
            print("✅ Created therapeutic context index")
            
            # 2. Text search index for fallback search (skip if exists)
            try:
                await self.db.therapeutic_content.create_index([
                    ("title", "text"),
                    ("text_content", "text")
                ], name="idx_therapeutic_text_search")
                print("✅ Created therapeutic text search index")
            except Exception as e:
                if "IndexOptionsConflict" in str(e) or "equivalent index already exists" in str(e):
                    print("⚠️  Text search index already exists, skipping")
                else:
                    raise
            
            # 3. Document relationship index
            await self.db.therapeutic_content.create_index([
                ("document_id", 1),
                ("chunk_order", 1)
            ], name="idx_document_chunks")
            print("✅ Created document chunks index")
            
            # 4. Embedder tracking index
            await self.db.therapeutic_content.create_index([
                ("embedder_id", 1),
                ("embedding_model", 1)
            ], name="idx_embedder_tracking")
            print("✅ Created embedder tracking index")
            
            # 5. For documents collection
            await self.db.therapeutic_documents.create_index([
                ("care_contexts", 1),
                ("therapeutic_category", 1)
            ], name="idx_document_therapeutic_context")
            print("✅ Created document therapeutic context index")
            
            await self.db.therapeutic_documents.create_index([
                ("source_file", 1),
                ("checksum", 1)
            ], unique=True, name="idx_document_uniqueness")
            print("✅ Created document uniqueness index")
            
            print("\n🎯 MongoDB therapeutic indexes created successfully!")
            print("Note: For production, consider using MongoDB Atlas Vector Search")
            print("for high-performance vector similarity search.")
            
        except Exception as e:
            logger.error(f"❌ Failed to create therapeutic indexes: {e}")
            raise
    
    async def create_atlas_vector_search_definition(self):
        """Generate Atlas Vector Search index definition"""
        
        atlas_index_definition = {
            "name": "vector_idx_therapeutic_content",
            "type": "vectorSearch",
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
                        "path": "care_contexts"
                    },
                    {
                        "type": "filter", 
                        "path": "therapeutic_category"
                    },
                    {
                        "type": "filter",
                        "path": "urgency_level"
                    }
                ]
            }
        }
        
        print("\n📋 Atlas Vector Search Index Definition:")
        print("Use this definition in MongoDB Atlas to create vector search:")
        print("Database: chatbot_app")
        print("Collection: therapeutic_content")
        print(f"Definition: {atlas_index_definition}")
        
        return atlas_index_definition
    
    async def list_current_indexes(self):
        """List current indexes on therapeutic collections"""
        print("\n📊 Current Therapeutic Content Indexes:")
        therapeutic_indexes = await self.db.therapeutic_content.list_indexes().to_list(None)
        for idx in therapeutic_indexes:
            print(f"  • {idx.get('name', 'unnamed')}: {idx.get('key', {})}")
        
        print("\n📊 Current Therapeutic Documents Indexes:")
        document_indexes = await self.db.therapeutic_documents.list_indexes().to_list(None)
        for idx in document_indexes:
            print(f"  • {idx.get('name', 'unnamed')}: {idx.get('key', {})}")
    
    async def cleanup(self):
        """Clean up connection"""
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("✅ Cleanup completed")

async def main():
    """Create MongoDB therapeutic indexes"""
    manager = MongoVectorIndexManager()
    
    try:
        await manager.initialize()
        await manager.create_therapeutic_vector_indexes()
        await manager.create_atlas_vector_search_definition()
        await manager.list_current_indexes()
        
    finally:
        await manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())