#!/usr/bin/env python3
"""
Fix MongoDB Embeddings for AI Quality Tests
============================================

This script connects to the demo MongoDB database and fixes embedding issues:
1. Examines documents in therapeutic_content collection
2. Identifies documents with None/null embeddings 
3. Generates proper BGE embeddings using the embedding service
4. Updates documents with valid 1024-dimensional embeddings

Specifically focuses on documents containing 'secret code' or 'blue rocket' 
text since that's what the AI quality tests are looking for.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from motor.motor_asyncio import AsyncIOMotorClient
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmbeddingFixer:
    def __init__(self):
        # Demo MongoDB configuration
        self.mongo_host = "localhost"
        self.mongo_port = 27018  # Demo MongoDB port
        self.mongo_user = "root"
        self.mongo_password = "demo_example_v1"
        self.mongo_db = "demo_v1_chatbot_app"
        
        # BGE Embedding service configuration
        self.embedding_service_url = "http://localhost:8005"
        self.embedding_dimension = 1024  # BGE-large-en-v1.5 produces 1024-dim embeddings
        
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        
    async def connect_to_mongo(self) -> bool:
        """Connect to demo MongoDB database"""
        try:
            # Build connection string
            connection_string = (
                f"mongodb://{self.mongo_user}:{self.mongo_password}@"
                f"{self.mongo_host}:{self.mongo_port}/?authSource=admin&directConnection=true"
            )
            
            logger.info(f"Connecting to demo MongoDB at {self.mongo_host}:{self.mongo_port}")
            
            self.client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000
            )
            
            # Test connection
            await self.client.admin.command("ping")
            self.db = self.client[self.mongo_db]
            
            # List available databases and collections for verification
            db_list = await self.client.list_database_names()
            logger.info(f"Available databases: {db_list}")
            
            if self.mongo_db in db_list:
                collections = await self.db.list_collection_names()
                logger.info(f"Collections in {self.mongo_db}: {collections}")
            else:
                logger.warning(f"Database {self.mongo_db} not found!")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def check_embedding_service(self) -> bool:
        """Check if BGE embedding service is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.embedding_service_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"Embedding service health: {health_data}")
                        return True
                    else:
                        logger.error(f"Embedding service unhealthy: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Cannot reach embedding service: {e}")
            return False
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using BGE service"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"text": text}
                async with session.post(
                    f"{self.embedding_service_url}/embed", 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        embedding = result.get("embedding")
                        if embedding and len(embedding) == self.embedding_dimension:
                            return embedding
                        else:
                            logger.error(f"Invalid embedding dimension: {len(embedding) if embedding else 'None'}")
                            return None
                    else:
                        logger.error(f"Embedding service error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def examine_collection(self, collection_name: str = "therapeutic_content") -> Dict[str, Any]:
        """Examine the therapeutic_content collection structure and embedding status"""
        collection = self.db[collection_name]
        
        # Get total document count
        total_docs = await collection.count_documents({})
        logger.info(f"Total documents in {collection_name}: {total_docs}")
        
        # Check for documents with None/null embeddings
        null_embedding_count = await collection.count_documents({
            "$or": [
                {"embedding": None},
                {"embedding": {"$exists": False}},
                {"embedding": []},
                {"embedding": {"$size": 0}}
            ]
        })
        
        logger.info(f"Documents with null/missing embeddings: {null_embedding_count}")
        
        # Check for test content (secret code, blue rocket)
        test_queries = ["secret code", "blue rocket"]
        test_docs = []
        
        for query in test_queries:
            docs = await collection.find({
                "$text": {"$search": query}
            }).limit(5).to_list(length=5)
            
            if not docs:  # Try regex search if text search fails
                docs = await collection.find({
                    "content": {"$regex": query, "$options": "i"}
                }).limit(5).to_list(length=5)
                
            logger.info(f"Found {len(docs)} documents containing '{query}'")
            test_docs.extend(docs)
        
        # Sample a few documents to examine structure
        sample_docs = await collection.find().limit(3).to_list(length=3)
        
        logger.info("Sample document structure:")
        for i, doc in enumerate(sample_docs):
            logger.info(f"Document {i+1}:")
            logger.info(f"  _id: {doc.get('_id')}")
            logger.info(f"  title: {doc.get('title', 'N/A')[:100]}...")
            logger.info(f"  content preview: {doc.get('content', 'N/A')[:100]}...")
            
            embedding = doc.get('embedding')
            if embedding is None:
                logger.info(f"  embedding: None")
            elif isinstance(embedding, list):
                logger.info(f"  embedding: List of {len(embedding)} elements")
                if len(embedding) > 0:
                    logger.info(f"  embedding sample: {embedding[:3]}...")
            else:
                logger.info(f"  embedding: {type(embedding)}")
        
        return {
            "total_docs": total_docs,
            "null_embeddings": null_embedding_count,
            "test_docs": test_docs,
            "sample_docs": sample_docs
        }
    
    async def fix_embeddings(self, collection_name: str = "therapeutic_content", batch_size: int = 10) -> int:
        """Fix documents with missing embeddings"""
        collection = self.db[collection_name]
        
        # Find documents with missing embeddings
        cursor = collection.find({
            "$or": [
                {"embedding": None},
                {"embedding": {"$exists": False}},
                {"embedding": []},
                {"embedding": {"$size": 0}}
            ]
        })
        
        docs_to_fix = await cursor.to_list(length=None)
        logger.info(f"Found {len(docs_to_fix)} documents needing embedding fixes")
        
        if not docs_to_fix:
            logger.info("No documents need embedding fixes")
            return 0
        
        fixed_count = 0
        
        # Process in batches
        for i in range(0, len(docs_to_fix), batch_size):
            batch = docs_to_fix[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(docs_to_fix) + batch_size - 1)//batch_size}")
            
            for doc in batch:
                doc_id = doc["_id"]
                
                # Get text content for embedding
                content = doc.get("content", "")
                title = doc.get("title", "")
                text_to_embed = f"{title}\n\n{content}".strip()
                
                if not text_to_embed:
                    logger.warning(f"Document {doc_id} has no content to embed")
                    continue
                
                # Generate embedding
                logger.info(f"Generating embedding for document {doc_id}")
                embedding = await self.generate_embedding(text_to_embed)
                
                if embedding:
                    # Update document with new embedding
                    try:
                        await collection.update_one(
                            {"_id": doc_id},
                            {
                                "$set": {
                                    "embedding": embedding,
                                    "embedding_model": "BAAI/bge-large-en-v1.5",
                                    "embedding_dimension": self.embedding_dimension,
                                    "embedding_updated_at": datetime.utcnow()
                                }
                            }
                        )
                        fixed_count += 1
                        logger.info(f"✅ Fixed embedding for document {doc_id}")
                        
                        # Check if this document contains test content
                        if any(term in content.lower() for term in ["secret code", "blue rocket"]):
                            logger.info(f"🎯 Fixed TEST DOCUMENT containing search terms: {doc_id}")
                            
                    except Exception as e:
                        logger.error(f"Failed to update document {doc_id}: {e}")
                else:
                    logger.error(f"Failed to generate embedding for document {doc_id}")
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        logger.info(f"✅ Fixed embeddings for {fixed_count} documents")
        return fixed_count
    
    async def verify_embeddings(self, collection_name: str = "therapeutic_content") -> Dict[str, Any]:
        """Verify that embeddings are properly set"""
        collection = self.db[collection_name]
        
        # Count documents with valid embeddings
        valid_embeddings = await collection.count_documents({
            "embedding": {"$exists": True, "$ne": None, "$not": {"$size": 0}}
        })
        
        # Count total documents
        total_docs = await collection.count_documents({})
        
        # Test search for documents with our test terms
        test_results = {}
        test_queries = ["secret code", "blue rocket"]
        
        for query in test_queries:
            # Find documents with the query terms that have embeddings
            docs_with_embeddings = await collection.find({
                "content": {"$regex": query, "$options": "i"},
                "embedding": {"$exists": True, "$ne": None, "$not": {"$size": 0}}
            }).to_list(length=5)
            
            test_results[query] = {
                "found_docs": len(docs_with_embeddings),
                "sample_ids": [str(doc["_id"]) for doc in docs_with_embeddings[:3]]
            }
            
            logger.info(f"Found {len(docs_with_embeddings)} documents with '{query}' that have embeddings")
        
        # Sample check embedding dimensions
        sample_doc = await collection.find_one({
            "embedding": {"$exists": True, "$ne": None, "$not": {"$size": 0}}
        })
        
        embedding_dim = None
        if sample_doc and "embedding" in sample_doc:
            embedding_dim = len(sample_doc["embedding"])
        
        result = {
            "total_documents": total_docs,
            "documents_with_embeddings": valid_embeddings,
            "coverage_percentage": (valid_embeddings / total_docs * 100) if total_docs > 0 else 0,
            "embedding_dimension": embedding_dim,
            "test_queries": test_results
        }
        
        logger.info(f"Verification results: {result}")
        return result
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

async def main():
    """Main function to fix MongoDB embeddings"""
    logger.info("🚀 Starting MongoDB Embedding Fix for AI Quality Tests")
    
    fixer = EmbeddingFixer()
    
    try:
        # Connect to MongoDB
        if not await fixer.connect_to_mongo():
            logger.error("Failed to connect to MongoDB")
            return False
        
        # Check embedding service
        if not await fixer.check_embedding_service():
            logger.error("Embedding service is not available")
            return False
        
        # Examine current state
        logger.info("📊 Examining collection state...")
        collection_info = await fixer.examine_collection()
        
        # Fix embeddings if needed
        if collection_info["null_embeddings"] > 0:
            logger.info("🔧 Fixing embeddings...")
            fixed_count = await fixer.fix_embeddings()
            logger.info(f"Fixed {fixed_count} documents")
        else:
            logger.info("✅ No embeddings need fixing")
        
        # Verify the fix
        logger.info("🔍 Verifying embeddings...")
        verification = await fixer.verify_embeddings()
        
        # Summary
        logger.info("=" * 50)
        logger.info("SUMMARY:")
        logger.info(f"Total documents: {verification['total_documents']}")
        logger.info(f"Documents with embeddings: {verification['documents_with_embeddings']}")
        logger.info(f"Coverage: {verification['coverage_percentage']:.1f}%")
        logger.info(f"Embedding dimension: {verification['embedding_dimension']}")
        
        for query, results in verification['test_queries'].items():
            logger.info(f"Documents with '{query}' having embeddings: {results['found_docs']}")
            
        logger.info("=" * 50)
        
        if verification['coverage_percentage'] >= 95:
            logger.info("✅ Embedding fix successful!")
            return True
        else:
            logger.warning("⚠️ Some documents still missing embeddings")
            return False
        
    except Exception as e:
        logger.error(f"Error during embedding fix: {e}")
        return False
    finally:
        await fixer.close()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)