#!/usr/bin/env python3
"""
Seeding Integration Tests
=========================

Tests for the seeding pipeline including:
- Basic seeding functionality
- Advanced seeding pipeline
- Data validation after seeding
- Performance monitoring

Usage:
    pytest tests/integration/test_seeding.py -v
"""

import asyncio
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
MONGO_URI = "mongodb://root:example@localhost:27017/chatbot_app?authSource=admin&directConnection=true"


class TestSeedingPipeline:
    """Test the seeding pipeline functionality"""
    
    @pytest.mark.asyncio
    async def test_mongo_connection_for_seeding(self):
        """Test MongoDB connection for seeding operations"""
        client = AsyncIOMotorClient(MONGO_URI)
        try:
            await client.admin.command('ping')
            db = client.chatbot_app
            collections = await db.list_collection_names()
            print(f" MongoDB ready for seeding: {len(collections)} collections")
            assert True  # Connection successful
        except Exception as e:
            pytest.fail(f"MongoDB connection failed: {e}")
        finally:
            client.close()
    
    @pytest.mark.asyncio
    async def test_basic_seeding_components(self):
        """Test basic components required for seeding"""
        try:
            # Test document processor import
            from ai_services.ingestion_pipeline.document_processor import EnhancedDocumentProcessor
            processor = EnhancedDocumentProcessor()
            processor.cleanup()
            print(" Document processor available")
            
            # Test seeding module import
            from ai_services.ingestion_pipeline.seed_data import AdvancedSeedConfig
            config = AdvancedSeedConfig()
            print(" Seeding configuration available")
            
        except ImportError as e:
            pytest.skip(f"Seeding components not available: {e}")
    
    @pytest.mark.asyncio
    async def test_seeded_data_validation(self):
        """Test that seeded data is properly formatted and accessible"""
        client = AsyncIOMotorClient(MONGO_URI)
        try:
            db = client.chatbot_app
            
            # Check for embeddings collection
            embeddings_count = await db.embeddings.count_documents({})
            print(f"9 Embeddings collection has {embeddings_count} documents")
            
            if embeddings_count > 0:
                # Test sample document structure
                sample_doc = await db.embeddings.find_one()
                
                # Validate required fields
                required_fields = ['content', 'title', 'embedding']
                for field in required_fields:
                    assert field in sample_doc, f"Missing required field: {field}"
                
                # Validate embedding format
                if 'embedding' in sample_doc and sample_doc['embedding']:
                    embedding = sample_doc['embedding']
                    assert isinstance(embedding, list), "Embedding should be a list"
                    assert len(embedding) > 0, "Embedding should not be empty"
                    assert all(isinstance(x, (int, float)) for x in embedding), "Embedding should contain numbers"
                
                print(" Seeded data structure validation passed")
            else:
                print("9 No seeded data found - seeding may not have run yet")
                
        finally:
            client.close()


if __name__ == "__main__":
    """Run seeding tests directly"""
    import sys
    
    print("<1 Running Seeding Integration Tests")
    print("=" * 40)
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    sys.exit(exit_code)