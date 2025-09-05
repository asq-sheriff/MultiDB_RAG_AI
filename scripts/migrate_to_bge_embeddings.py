#!/usr/bin/env python3
"""
Migration script to update existing embeddings to BGE 1024-dimensional vectors
"""
import asyncio
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def migrate_embeddings_to_bge():
    """
    Migrate existing 384-dimensional embeddings to BGE 1024-dimensional embeddings
    """
    try:
        # Initialize services  
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from ai_services.shared.utils.env_loader import load_environment, detect_environment
        from data_layer.connections.mongo_connection import EnhancedMongoManager
        from ai_services.shared.dependencies.dependencies import get_embedding_service
        
        # Load appropriate environment
        detected_env = detect_environment()
        load_environment(detected_env)
        logger.info(f"🌍 Using {detected_env} environment")
        
        logger.info("🚀 Starting BGE embedding migration...")
        
        # Connect to MongoDB
        mongo = EnhancedMongoManager()
        await mongo.connect()
        db = mongo.database
        
        # Get collections
        therapeutic_collection = db.therapeutic_content
        embeddings_collection = db.embeddings if hasattr(db, 'embeddings') else None
        
        # Get embedding service
        embedding_service = get_embedding_service()
        if not embedding_service:
            logger.error("❌ Embedding service not available")
            return False
        
        # Check current state in therapeutic_content collection
        total_docs = await therapeutic_collection.count_documents({})
        embedded_docs = await therapeutic_collection.count_documents({"embedding": {"$ne": None}})
        missing_embeddings = total_docs - embedded_docs
        
        logger.info(f"📊 Current state: {total_docs} total documents, {embedded_docs} with embeddings, {missing_embeddings} missing embeddings")
        
        if missing_embeddings == 0:
            logger.info("✅ No migration needed - all documents have embeddings")
            return True
            
        # Generate embeddings for therapeutic_content documents
        if missing_embeddings > 0:
            logger.info(f"🔧 Generating BGE embeddings for {missing_embeddings} therapeutic documents...")
            cursor = therapeutic_collection.find({"embedding": {"$in": [None, []]}})
            
            migrated_count = 0
            async for doc in cursor:
                try:
                    content = doc.get('content', '')
                    if not content:
                        logger.warning(f"Skipping document {doc['_id']} - no content")
                        continue
                    
                    # Generate new BGE embedding via embedding service
                    new_embedding = await embedding_service.embed_query(content)
                    
                    if new_embedding and len(new_embedding) == 1024:
                        # Update document with new BGE embedding
                        await therapeutic_collection.update_one(
                            {"_id": doc["_id"]},
                            {
                                "$set": {
                                    "embedding": new_embedding,
                                    "embedding_dimension": 1024,
                                    "embedding_model": "BAAI/bge-large-en-v1.5",
                                    "embedder_id": "bge-large-en-v1.5",
                                    "migrated_to_bge": datetime.utcnow()
                                }
                            }
                        )
                        migrated_count += 1
                        
                        if migrated_count % 10 == 0:
                            logger.info(f"✅ Generated embeddings for {migrated_count}/{missing_embeddings} documents")
                    else:
                        logger.warning(f"❌ BGE returned invalid embedding for doc {doc['_id']}: length={len(new_embedding) if new_embedding else 0}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to generate embedding for {doc['_id']}: {e}")
                    continue
            
            logger.info(f"✅ Completed embedding generation: {migrated_count} documents updated")
        
        # Final verification
        final_embedded_docs = await therapeutic_collection.count_documents({"embedding": {"$ne": None}})
        final_missing = total_docs - final_embedded_docs
        
        logger.info(f"🎯 Migration complete!")
        logger.info(f"   📊 Total documents: {total_docs}")
        logger.info(f"   ✅ Documents with BGE embeddings: {final_embedded_docs}")
        logger.info(f"   ❌ Documents still missing embeddings: {final_missing}")
        
        if final_missing == 0:
            logger.info("   🎉 All therapeutic documents now have BGE 1024-dimensional embeddings!")
        
        await mongo.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(migrate_embeddings_to_bge())
    if success:
        print("🎉 BGE migration completed successfully!")
        exit(0)
    else:
        print("💥 BGE migration failed!")
        exit(1)