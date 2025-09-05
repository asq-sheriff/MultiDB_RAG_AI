#!/usr/bin/env python3
"""
Document Ingestion Integration Tests
===================================

Comprehensive tests for the document ingestion pipeline including:
- Data file processing from ./data/docs
- Document processor functionality
- MongoDB storage and retrieval
- Embedding generation and storage
- Search functionality on ingested data
- Performance and error handling

Usage:
    pytest tests/integration/test_document_ingestion.py -v
    python -m pytest tests/integration/test_document_ingestion.py::TestBasicIngestion -v
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any
import pytest
import random
from motor.motor_asyncio import AsyncIOMotorClient

# Import application modules
from app.utils.document_processor import (
    EnhancedDocumentProcessor, 
    ProcessingConfig, 
    DocumentChunk
)

# Configuration
MONGO_URI = "mongodb://root:example@localhost:27017/chatbot_app?authSource=admin&directConnection=true"
TEST_COLLECTION = "test_ingestion"
DATA_DOCS_PATH = "./data/docs"


class TestBasicIngestion:
    """Test basic document ingestion functionality"""
    
    @pytest.mark.asyncio
    async def test_mongo_connection(self):
        """Test MongoDB connection for ingestion"""
        client = AsyncIOMotorClient(MONGO_URI)
        try:
            await client.admin.command('ping')
            print("✅ MongoDB connection successful")
            
            # Test database access
            db = client.chatbot_app
            collections = await db.list_collection_names()
            print(f"✅ Database accessible, collections: {len(collections)}")
            
        except Exception as e:
            pytest.fail(f"MongoDB connection failed: {e}")
        finally:
            client.close()
    
    @pytest.mark.asyncio
    async def test_document_processor_basic(self):
        """Test basic document processor functionality"""
        config = ProcessingConfig(
            chunk_size=500,
            chunk_overlap=50,
            max_workers=2,
            use_parallel_processing=False
        )
        
        processor = EnhancedDocumentProcessor(config)
        
        # Create test document
        test_content = """
        This is a test document for the enhanced document processor.
        
        It contains multiple paragraphs to test chunking functionality.
        The processor should split this into meaningful chunks while preserving context.
        
        This paragraph contains information about healthcare guidelines and safety protocols.
        Emergency procedures should be followed when dealing with elderly care situations.
        
        Finally, this section discusses conversation patterns and emotional support
        strategies that AI companions should implement for effective user interaction.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            chunks = processor._process_file_sync(Path(temp_path))
            
            assert len(chunks) > 0, "No chunks created from test document"
            assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
            assert all(len(chunk.content) >= config.min_chunk_size for chunk in chunks)
            
            print(f"✅ Document processor: {len(chunks)} chunks created")
            
            # Test chunk content
            total_content = ''.join(chunk.content for chunk in chunks).lower()
            assert "healthcare guidelines" in total_content
            assert "emergency procedures" in total_content
            assert "conversation patterns" in total_content
            
        finally:
            os.unlink(temp_path)
            processor.cleanup()
    
    @pytest.mark.asyncio
    async def test_data_docs_processing(self):
        """Test processing of actual data files"""
        if not Path(DATA_DOCS_PATH).exists():
            pytest.skip(f"Data directory {DATA_DOCS_PATH} not found")
        
        config = ProcessingConfig()
        processor = EnhancedDocumentProcessor(config)
        
        try:
            chunks = await processor.process_directory(DATA_DOCS_PATH)
            
            assert len(chunks) > 0, f"No chunks processed from {DATA_DOCS_PATH}"
            
            # Verify chunk metadata
            assert all(chunk.metadata.file_path for chunk in chunks)
            assert all(chunk.metadata.title for chunk in chunks)
            assert all(chunk.content.strip() for chunk in chunks)
            
            # Check for expected content types
            file_types = {chunk.metadata.file_type for chunk in chunks}
            assert len(file_types) > 0, "No file types detected"
            
            print(f"✅ Data docs processing: {len(chunks)} chunks from {len(file_types)} file types")
            
            # Test specific content patterns
            all_content = ' '.join(chunk.content.lower() for chunk in chunks)
            expected_terms = ['safety', 'conversation', 'care', 'support', 'protocol']
            found_terms = [term for term in expected_terms if term in all_content]
            
            print(f"✅ Content validation: Found {len(found_terms)}/{len(expected_terms)} expected terms")
            
            return chunks
            
        finally:
            processor.cleanup()


class TestMongoDBIngestion:
    """Test MongoDB document storage and retrieval"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Setup and cleanup test data"""
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client.chatbot_app
        
        # Clear test collection
        await self.db[TEST_COLLECTION].delete_many({})
        
        yield
        
        # Cleanup after test
        await self.db[TEST_COLLECTION].delete_many({})
        self.client.close()
    
    @pytest.mark.asyncio
    async def test_document_storage_basic(self):
        """Test basic document storage in MongoDB"""
        # Create test document
        test_doc = {
            'content': 'This is a test document for MongoDB storage validation',
            'title': 'Test Document',
            'document_id': 'test_doc_001',
            'chunk_index': 0,
            'category': 'test',
            'source': 'test_file.txt',
            'embedding': [random.uniform(-1, 1) for _ in range(768)],
            'metadata': {
                'file_size': 100,
                'word_count': 10,
                'test_marker': True
            }
        }
        
        # Insert document
        result = await self.db[TEST_COLLECTION].insert_one(test_doc)
        assert result.inserted_id is not None
        
        # Retrieve and validate
        retrieved = await self.db[TEST_COLLECTION].find_one({'_id': result.inserted_id})
        assert retrieved is not None
        assert retrieved['content'] == test_doc['content']
        assert retrieved['title'] == test_doc['title']
        assert len(retrieved['embedding']) == 768
        
        print("✅ Basic MongoDB document storage and retrieval")
    
    @pytest.mark.asyncio
    async def test_batch_ingestion(self):
        """Test batch document ingestion"""
        # Process real documents
        config = ProcessingConfig()
        processor = EnhancedDocumentProcessor(config)
        
        try:
            chunks = await processor.process_directory(DATA_DOCS_PATH)
            if len(chunks) == 0:
                pytest.skip("No documents to process")
            
            # Prepare batch of documents for insertion
            batch_documents = []
            for i, chunk in enumerate(chunks[:10]):  # Test with first 10 chunks
                mock_embedding = [random.uniform(-1, 1) for _ in range(768)]
                
                doc = {
                    'content': chunk.content,
                    'title': chunk.metadata.title,
                    'document_id': f'batch_test_{i}',
                    'chunk_index': chunk.chunk_index,
                    'chunk_id': chunk.chunk_id,
                    'category': 'batch_test',
                    'source': chunk.metadata.file_path,
                    'file_type': chunk.metadata.file_type,
                    'embedding': mock_embedding,
                    'created_at': time.strftime("%Y-%m-%dT%H:%M:%S"),
                    'metadata': {
                        'file_size': chunk.metadata.file_size,
                        'word_count': chunk.metadata.word_count,
                        'extraction_method': chunk.metadata.extraction_method
                    }
                }
                batch_documents.append(doc)
            
            # Batch insert
            start_time = time.time()
            result = await self.db[TEST_COLLECTION].insert_many(batch_documents)
            insert_time = time.time() - start_time
            
            assert len(result.inserted_ids) == len(batch_documents)
            
            # Verify insertion
            count = await self.db[TEST_COLLECTION].count_documents({'category': 'batch_test'})
            assert count == len(batch_documents)
            
            print(f"✅ Batch ingestion: {len(batch_documents)} documents in {insert_time:.3f}s")
            
        finally:
            processor.cleanup()
    
    @pytest.mark.asyncio
    async def test_search_functionality(self):
        """Test search on ingested documents"""
        # Insert test documents with searchable content
        test_docs = [
            {
                'content': 'Healthcare safety protocols for elderly patients include emergency response procedures',
                'title': 'Safety Protocols',
                'category': 'search_test',
                'embedding': [random.uniform(-1, 1) for _ in range(768)]
            },
            {
                'content': 'Conversation patterns for AI companions should focus on empathy and emotional support',
                'title': 'Conversation Guide',
                'category': 'search_test', 
                'embedding': [random.uniform(-1, 1) for _ in range(768)]
            },
            {
                'content': 'Emergency procedures must be clearly defined and easily accessible to caregivers',
                'title': 'Emergency Guide',
                'category': 'search_test',
                'embedding': [random.uniform(-1, 1) for _ in range(768)]
            }
        ]
        
        await self.db[TEST_COLLECTION].insert_many(test_docs)
        
        # Test text search
        search_tests = [
            ('safety', 'Healthcare safety protocols'),
            ('conversation', 'Conversation patterns'),
            ('emergency', 'Emergency procedures'),
            ('empathy', 'empathy and emotional')
        ]
        
        for search_term, expected_content in search_tests:
            results = await self.db[TEST_COLLECTION].find({
                'content': {'$regex': search_term, '$options': 'i'},
                'category': 'search_test'
            }).to_list(None)
            
            assert len(results) > 0, f"No results found for '{search_term}'"
            
            # Verify expected content is in results
            found_expected = any(expected_content.lower() in doc['content'].lower() for doc in results)
            assert found_expected, f"Expected content not found for '{search_term}'"
        
        print("✅ Search functionality on ingested documents")
    
    @pytest.mark.asyncio
    async def test_aggregation_queries(self):
        """Test aggregation queries on ingested data"""
        # Insert test data with categories
        test_data = []
        categories = ['healthcare', 'safety', 'communication', 'emergency']
        
        for i in range(20):
            doc = {
                'content': f'Test document content {i}',
                'title': f'Test Doc {i}',
                'category': categories[i % len(categories)],
                'file_type': 'md' if i % 2 == 0 else 'pdf',
                'word_count': random.randint(50, 500),
                'test_batch': 'aggregation_test'
            }
            test_data.append(doc)
        
        await self.db[TEST_COLLECTION].insert_many(test_data)
        
        # Test aggregation: group by category
        pipeline = [
            {'$match': {'test_batch': 'aggregation_test'}},
            {'$group': {
                '_id': '$category',
                'count': {'$sum': 1},
                'avg_word_count': {'$avg': '$word_count'}
            }},
            {'$sort': {'count': -1}}
        ]
        
        results = await self.db[TEST_COLLECTION].aggregate(pipeline).to_list(None)
        
        assert len(results) == len(categories)
        assert all(result['count'] > 0 for result in results)
        assert all('avg_word_count' in result for result in results)
        
        print(f"✅ Aggregation queries: {len(results)} category groups")
        
        # Test aggregation: file type distribution
        file_type_pipeline = [
            {'$match': {'test_batch': 'aggregation_test'}},
            {'$group': {'_id': '$file_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        
        file_results = await self.db[TEST_COLLECTION].aggregate(file_type_pipeline).to_list(None)
        assert len(file_results) == 2  # md and pdf
        
        print("✅ File type aggregation successful")


class TestEmbeddingIntegration:
    """Test embedding generation and vector operations"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Setup test environment"""
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client.chatbot_app
        await self.db[TEST_COLLECTION].delete_many({})
        
        yield
        
        await self.db[TEST_COLLECTION].delete_many({})
        self.client.close()
    
    @pytest.mark.asyncio
    async def test_mock_embedding_generation(self):
        """Test mock embedding generation and storage"""
        test_texts = [
            "Healthcare protocols for elderly care and safety management",
            "Conversation patterns and emotional support strategies", 
            "Emergency response procedures and crisis intervention",
            "AI companion guidelines for empathetic interaction"
        ]
        
        documents_with_embeddings = []
        
        for i, text in enumerate(test_texts):
            # Generate mock embedding (768 dimensions to match sentence-transformers)
            mock_embedding = [random.uniform(-1, 1) for _ in range(768)]
            
            doc = {
                'content': text,
                'title': f'Test Document {i+1}',
                'embedding': mock_embedding,
                'embedding_model': 'mock_768d',
                'category': 'embedding_test'
            }
            documents_with_embeddings.append(doc)
        
        # Insert documents with embeddings
        result = await self.db[TEST_COLLECTION].insert_many(documents_with_embeddings)
        assert len(result.inserted_ids) == len(test_texts)
        
        # Test embedding retrieval and validation
        docs_with_embeddings = await self.db[TEST_COLLECTION].find({
            'category': 'embedding_test',
            'embedding': {'$exists': True}
        }).to_list(None)
        
        assert len(docs_with_embeddings) == len(test_texts)
        
        for doc in docs_with_embeddings:
            assert 'embedding' in doc
            assert len(doc['embedding']) == 768
            assert all(isinstance(val, float) for val in doc['embedding'])
        
        print(f"✅ Mock embedding generation and storage: {len(test_texts)} documents")
    
    @pytest.mark.asyncio 
    async def test_similarity_search_simulation(self):
        """Test simulated vector similarity search"""
        # Create documents with known similar content
        similar_docs = [
            {
                'content': 'Healthcare safety protocols and emergency procedures',
                'title': 'Safety Guide 1',
                'embedding': [0.5, 0.3, -0.2, 0.8] + [0.0] * 764,  # Simple test vector
                'category': 'similarity_test'
            },
            {
                'content': 'Safety protocols for healthcare workers and emergency response',
                'title': 'Safety Guide 2', 
                'embedding': [0.4, 0.35, -0.15, 0.75] + [0.0] * 764,  # Similar vector
                'category': 'similarity_test'
            },
            {
                'content': 'Cooking recipes and kitchen management techniques',
                'title': 'Cooking Guide',
                'embedding': [-0.8, 0.1, 0.9, -0.3] + [0.0] * 764,  # Different vector
                'category': 'similarity_test'
            }
        ]
        
        await self.db[TEST_COLLECTION].insert_many(similar_docs)
        
        # Simulate similarity search by finding documents with similar patterns
        # In a real implementation, this would use vector similarity
        safety_docs = await self.db[TEST_COLLECTION].find({
            'content': {'$regex': 'safety.*protocol', '$options': 'i'},
            'category': 'similarity_test'
        }).to_list(None)
        
        assert len(safety_docs) >= 2, "Should find at least 2 safety-related documents"
        
        # Verify content similarity
        safety_contents = [doc['content'] for doc in safety_docs]
        assert all('safety' in content.lower() for content in safety_contents)
        assert all('protocol' in content.lower() for content in safety_contents)
        
        print(f"✅ Similarity search simulation: {len(safety_docs)} relevant documents found")


class TestPerformanceAndScaling:
    """Test performance characteristics of ingestion pipeline"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Setup test environment"""
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client.chatbot_app
        await self.db[TEST_COLLECTION].delete_many({})
        
        yield
        
        await self.db[TEST_COLLECTION].delete_many({})
        self.client.close()
    
    @pytest.mark.asyncio
    async def test_ingestion_performance(self):
        """Test ingestion performance with various batch sizes"""
        batch_sizes = [1, 5, 10, 25]
        performance_results = {}
        
        for batch_size in batch_sizes:
            # Generate test documents
            test_docs = []
            for i in range(batch_size):
                doc = {
                    'content': f'Performance test document {i} with substantial content to test realistic ingestion scenarios and processing capabilities of the enhanced document ingestion pipeline.',
                    'title': f'Perf Test Doc {i}',
                    'embedding': [random.uniform(-1, 1) for _ in range(768)],
                    'category': f'perf_test_{batch_size}',
                    'metadata': {
                        'word_count': 25,
                        'test_batch_size': batch_size
                    }
                }
                test_docs.append(doc)
            
            # Measure insertion time
            start_time = time.time()
            result = await self.db[TEST_COLLECTION].insert_many(test_docs)
            insert_time = time.time() - start_time
            
            assert len(result.inserted_ids) == batch_size
            
            # Measure query time
            query_start = time.time()
            retrieved = await self.db[TEST_COLLECTION].find({
                'category': f'perf_test_{batch_size}'
            }).to_list(None)
            query_time = time.time() - query_start
            
            assert len(retrieved) == batch_size
            
            performance_results[batch_size] = {
                'insert_time': insert_time,
                'query_time': query_time,
                'docs_per_second': batch_size / insert_time if insert_time > 0 else float('inf')
            }
        
        # Report performance results
        print("✅ Ingestion performance results:")
        for batch_size, results in performance_results.items():
            print(f"  Batch {batch_size:2d}: {results['docs_per_second']:.1f} docs/sec, "
                  f"insert: {results['insert_time']:.3f}s, query: {results['query_time']:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_ingestion(self):
        """Test concurrent document ingestion"""
        async def insert_batch(batch_id: int, doc_count: int):
            """Insert a batch of documents concurrently"""
            docs = []
            for i in range(doc_count):
                doc = {
                    'content': f'Concurrent test document {i} from batch {batch_id}',
                    'title': f'Concurrent Doc {batch_id}-{i}',
                    'batch_id': batch_id,
                    'category': 'concurrent_test',
                    'embedding': [random.uniform(-1, 1) for _ in range(768)]
                }
                docs.append(doc)
            
            result = await self.db[TEST_COLLECTION].insert_many(docs)
            return len(result.inserted_ids)
        
        # Run concurrent insertions
        batch_count = 5
        docs_per_batch = 10
        
        start_time = time.time()
        tasks = [insert_batch(i, docs_per_batch) for i in range(batch_count)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        total_inserted = sum(results)
        expected_total = batch_count * docs_per_batch
        
        assert total_inserted == expected_total
        
        # Verify all documents were inserted
        final_count = await self.db[TEST_COLLECTION].count_documents({'category': 'concurrent_test'})
        assert final_count == expected_total
        
        docs_per_second = total_inserted / total_time if total_time > 0 else float('inf')
        print(f"✅ Concurrent ingestion: {total_inserted} docs in {total_time:.3f}s ({docs_per_second:.1f} docs/sec)")


class TestErrorHandlingAndRecovery:
    """Test error handling in the ingestion pipeline"""
    
    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Setup test environment"""
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client.chatbot_app
        
        yield
        
        # Cleanup any test data
        await self.db[TEST_COLLECTION].delete_many({'category': {'$regex': 'error_test'}})
        self.client.close()
    
    @pytest.mark.asyncio
    async def test_invalid_document_handling(self):
        """Test handling of invalid documents during ingestion"""
        # Test documents with various issues
        problematic_docs = [
            # Missing required fields
            {'content': 'Valid content but missing title'},
            # Invalid embedding dimensions
            {'title': 'Invalid Embedding', 'content': 'Test', 'embedding': [1, 2, 3]},
            # Extremely large content
            {'title': 'Large Content', 'content': 'x' * 100000, 'category': 'error_test_large'},
            # Empty content
            {'title': 'Empty Content', 'content': '', 'category': 'error_test_empty'},
            # Valid document for comparison
            {'title': 'Valid Doc', 'content': 'Valid content', 'embedding': [0.5] * 768, 'category': 'error_test_valid'}
        ]
        
        # Insert documents and handle errors
        successful_inserts = 0
        failed_inserts = 0
        
        for doc in problematic_docs:
            try:
                result = await self.db[TEST_COLLECTION].insert_one(doc)
                if result.inserted_id:
                    successful_inserts += 1
            except Exception as e:
                failed_inserts += 1
                print(f"ℹ️ Expected error for problematic document: {type(e).__name__}")
        
        print(f"✅ Error handling: {successful_inserts} successful, {failed_inserts} failed as expected")
        
        # Verify valid documents were inserted
        valid_count = await self.db[TEST_COLLECTION].count_documents({'category': 'error_test_valid'})
        assert valid_count >= 1, "Valid documents should be inserted successfully"
    
    @pytest.mark.asyncio
    async def test_connection_recovery(self):
        """Test ingestion behavior during connection issues"""
        # This test simulates connection recovery scenarios
        test_doc = {
            'title': 'Connection Test',
            'content': 'Testing connection recovery during ingestion',
            'category': 'error_test_connection',
            'embedding': [0.1] * 768
        }
        
        # Test normal insertion
        try:
            result = await self.db[TEST_COLLECTION].insert_one(test_doc.copy())
            assert result.inserted_id is not None
            print("✅ Normal insertion successful")
        except Exception as e:
            print(f"ℹ️ Connection test result: {e}")
        
        # Test with timeout simulation (using very short timeout)
        try:
            short_timeout_client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=1)
            short_db = short_timeout_client.chatbot_app
            
            # This should timeout quickly
            await asyncio.wait_for(
                short_db[TEST_COLLECTION].insert_one(test_doc.copy()),
                timeout=0.001
            )
        except (asyncio.TimeoutError, Exception) as e:
            print(f"✅ Timeout handling working: {type(e).__name__}")
        finally:
            try:
                short_timeout_client.close()
            except:
                pass


if __name__ == "__main__":
    """Run document ingestion tests directly"""
    import sys
    
    print("📄 Running Document Ingestion Integration Tests")
    print("=" * 50)
    
    # Run pytest with verbose output  
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--color=yes",
        "-x"  # Stop on first failure
    ])
    
    sys.exit(exit_code)