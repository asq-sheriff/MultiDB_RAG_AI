"""
Therapeutic MongoDB Seeder - Optimized for Senior Care AI
Implements Priority 1 from MongoDB-PostgreSQL Integration Analysis
"""

import asyncio
import os
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - Use API Gateway for embedding service
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8090/api/v1/embedding")
DOCS_PATH = os.getenv("SEED_DOCS_PATH", "data/docs")
CHUNK_SIZE = int(os.getenv("SEED_CHUNK_CHARS", "1500"))
CHUNK_OVERLAP = int(os.getenv("SEED_CHUNK_OVERLAP", "180"))

class TherapeuticMongoSeeder:
    """Optimized MongoDB seeder for therapeutic content with intelligent indexing"""
    
    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.embedding_session = None
        
        # MongoDB connection parameters
        self.mongo_host = os.getenv("MONGO_HOST", "localhost")
        self.mongo_port = int(os.getenv("MONGO_PORT", "27017"))
        self.mongo_user = os.getenv("MONGO_USER", "root")
        self.mongo_password = os.getenv("MONGO_PASSWORD", "example")
        self.mongo_db = os.getenv("MONGO_DB", "chatbot_app")
        
    async def initialize(self):
        """Initialize MongoDB connection and HTTP session"""
        # MongoDB connection with auth
        mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/?authSource=admin&directConnection=true"
        
        self.mongo_client = AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client[self.mongo_db]
        
        # Test connection
        await self.mongo_client.admin.command('ismaster')
        logger.info(f"✅ Connected to MongoDB: {self.mongo_host}:{self.mongo_port}")
        
        # HTTP session for embeddings
        self.embedding_session = aiohttp.ClientSession()
        
        # Test embedding service via API Gateway
        try:
            async with self.embedding_session.get(f"{EMBEDDING_SERVICE_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ Connected to embedding service via API Gateway: {health_data.get('model', 'unknown')}")
                else:
                    raise Exception(f"Embedding service unhealthy: {response.status}")
        except Exception as e:
            logger.error(f"❌ Embedding service connection failed: {e}")
            raise
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using BGE service via API Gateway"""
        try:
            async with self.embedding_session.post(
                f"{EMBEDDING_SERVICE_URL}/v1/embeddings",
                json={
                    "model": "bge-large",
                    "input": texts
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return [item.get("embedding", []) for item in data.get("data", [])]
                else:
                    error_text = await response.text()
                    raise Exception(f"Embedding service error {response.status}: {error_text}")
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            raise
    
    def categorize_therapeutic_content(self, title: str, content: str) -> Dict[str, Any]:
        """Intelligently categorize therapeutic content based on analysis"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Determine care context
        care_contexts = []
        if any(term in title_lower or term in content_lower for term in ['grief', 'loss', 'bereav', 'mourn']):
            care_contexts.append('grief')
        if any(term in title_lower or term in content_lower for term in ['lonely', 'isolat', 'alone', 'companion']):
            care_contexts.append('loneliness') 
        if any(term in title_lower or term in content_lower for term in ['anxious', 'anxiety', 'worry', 'stress']):
            care_contexts.append('anxiety')
        if any(term in title_lower or term in content_lower for term in ['caregiver', 'caring', 'burnout']):
            care_contexts.append('caregiver-stress')
        if any(term in title_lower or term in content_lower for term in ['crisis', 'safe-t', 'emergency', 'suicide']):
            care_contexts.append('crisis')
        if any(term in title_lower or term in content_lower for term in ['medication', 'health', 'medical']):
            care_contexts.append('health')
        
        # Determine therapeutic category
        therapeutic_category = 'general'
        if 'empathic' in title_lower or 'companion' in title_lower:
            therapeutic_category = 'empathy'
        elif 'crisis' in title_lower or 'safe-t' in title_lower:
            therapeutic_category = 'crisis'
        elif 'enhancement' in title_lower or 'care' in title_lower:
            therapeutic_category = 'care-enhancement'
        
        # Determine urgency level
        urgency_level = 'routine'
        if any(term in content_lower for term in ['emergency', 'crisis', 'immediate', 'urgent']):
            urgency_level = 'urgent'
        elif any(term in content_lower for term in ['concern', 'watch', 'monitor']):
            urgency_level = 'concerning'
        
        # Extract keywords
        keywords = []
        for context in care_contexts:
            keywords.append(context)
        keywords.extend(['senior-care', 'therapeutic', 'mental-health'])
        
        return {
            'care_contexts': care_contexts or ['general'],
            'therapeutic_category': therapeutic_category,
            'urgency_level': urgency_level,
            'keywords': keywords,
            'applicable_demographics': ['seniors-65+', 'caregivers'],
            'document_type': 'therapeutic-guide' if 'guide' in title_lower else 'knowledge-cards' if 'card' in title_lower else 'therapeutic-content'
        }
    
    async def process_therapeutic_documents(self) -> Dict[str, Any]:
        """Process and migrate therapeutic documents to optimized MongoDB"""
        docs_dir = Path(DOCS_PATH)
        if not docs_dir.exists():
            raise FileNotFoundError(f"Documents directory not found: {docs_dir}")
        
        processed_docs = 0
        processed_chunks = 0
        results = []
        
        # Process each document (both .md and .txt files)
        import itertools
        md_files = docs_dir.glob("*.md")
        txt_files = docs_dir.glob("*.txt")
        for doc_path in itertools.chain(md_files, txt_files):
            if doc_path.name.startswith('.'):
                continue
                
            logger.info(f"📄 Processing therapeutic document: {doc_path.name}")
            
            try:
                # Read document content
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not content.strip():
                    logger.warning(f"⚠️  Empty document skipped: {doc_path.name}")
                    continue
                
                # Calculate checksum for duplicate detection
                checksum = hashlib.sha256(content.encode()).hexdigest()
                
                # Check if document already exists
                existing_doc = await self.db.therapeutic_documents.find_one({
                    "source_file": doc_path.name,
                    "checksum": checksum
                })
                
                if existing_doc:
                    logger.info(f"📋 Document already processed: {doc_path.name}")
                    continue
                
                # Categorize therapeutic content
                metadata = self.categorize_therapeutic_content(doc_path.stem, content)
                
                # Create document record
                doc_id = str(uuid.uuid4())
                doc_record = {
                    "_id": doc_id,
                    "source_file": doc_path.name,
                    "title": doc_path.stem.replace('_', ' ').replace('-', ' ').title(),
                    "checksum": checksum,
                    "file_size": len(content),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    **metadata
                }
                
                # Insert document record
                await self.db.therapeutic_documents.insert_one(doc_record)
                logger.info(f"✅ Document record created: {doc_id}")
                
                # Create therapeutic content chunks
                chunks = self.create_therapeutic_chunks(content, doc_path.stem, metadata)
                chunk_data = []
                
                for idx, chunk in enumerate(chunks):
                    chunk_record = {
                        "_id": str(uuid.uuid4()),
                        "document_id": doc_id,
                        "chunk_order": idx,
                        "text_content": chunk["text"],
                        "title": chunk.get("heading", doc_path.stem),
                        "char_count": len(chunk["text"]),
                        "created_at": datetime.now(timezone.utc),
                        **metadata  # Inherit document metadata
                    }
                    chunk_data.append(chunk_record)
                
                # Generate embeddings in batches
                texts_for_embedding = [chunk["text_content"] for chunk in chunk_data]
                embeddings = await self.generate_embeddings(texts_for_embedding)
                
                # Add embeddings to chunk data
                for i, chunk_record in enumerate(chunk_data):
                    chunk_record["embedding"] = embeddings[i]
                    chunk_record["embedder_id"] = "hybrid-bge-large-en-v1.5"
                    chunk_record["embedding_model"] = "bge-large-en-v1.5"
                    chunk_record["embedding_dimensions"] = len(embeddings[i])
                
                # Insert therapeutic content chunks
                if chunk_data:
                    await self.db.therapeutic_content.insert_many(chunk_data)
                    logger.info(f"✅ Created {len(chunk_data)} therapeutic content chunks")
                
                processed_docs += 1
                processed_chunks += len(chunk_data)
                
                results.append({
                    "document": doc_path.name,
                    "doc_id": doc_id,
                    "chunks": len(chunk_data),
                    "care_contexts": metadata["care_contexts"],
                    "therapeutic_category": metadata["therapeutic_category"]
                })
                
            except Exception as e:
                logger.error(f"❌ Failed to process {doc_path.name}: {e}")
                continue
        
        return {
            "status": "completed",
            "documents_processed": processed_docs,
            "total_chunks": processed_chunks,
            "embedder_id": "hybrid-bge-large-en-v1.5",
            "embedding_model": "bge-large-en-v1.5",
            "results": results
        }
    
    def create_therapeutic_chunks(self, content: str, title: str, metadata: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create intelligently chunked therapeutic content"""
        chunks = []
        lines = content.split('\n')
        current_chunk = ""
        current_heading = None
        
        for line in lines:
            line = line.strip()
            
            # Detect headings
            if line.startswith('#'):
                # If we have a current chunk, save it
                if current_chunk.strip():
                    chunks.append({
                        "text": current_chunk.strip(),
                        "heading": current_heading,
                        "metadata": metadata
                    })
                    current_chunk = ""
                
                current_heading = line.lstrip('#').strip()
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"
                
                # Check chunk size
                if len(current_chunk) >= CHUNK_SIZE:
                    # Find a good break point
                    break_point = self.find_sentence_break(current_chunk, CHUNK_SIZE - CHUNK_OVERLAP)
                    if break_point > 0:
                        chunk_text = current_chunk[:break_point].strip()
                        chunks.append({
                            "text": chunk_text,
                            "heading": current_heading,
                            "metadata": metadata
                        })
                        current_chunk = current_chunk[break_point - CHUNK_OVERLAP:] if break_point > CHUNK_OVERLAP else current_chunk[break_point:]
        
        # Add final chunk if exists
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "heading": current_heading,
                "metadata": metadata
            })
        
        return chunks
    
    def find_sentence_break(self, text: str, target_position: int) -> int:
        """Find the best sentence break near target position"""
        if target_position >= len(text):
            return len(text)
        
        # Look for sentence endings near target position
        search_window = 100
        start_pos = max(0, target_position - search_window)
        end_pos = min(len(text), target_position + search_window)
        
        # Find sentence endings
        for i in range(target_position, start_pos, -1):
            if text[i] in '.!?' and i < len(text) - 1 and text[i + 1] in ' \n':
                return i + 1
        
        # Fallback to space break
        for i in range(target_position, start_pos, -1):
            if text[i] == ' ':
                return i
        
        return target_position
    
    async def cleanup(self):
        """Clean up connections"""
        if self.embedding_session:
            await self.embedding_session.close()
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("✅ Cleanup completed")

async def main():
    """Run therapeutic MongoDB seeding"""
    seeder = TherapeuticMongoSeeder()
    
    try:
        await seeder.initialize()
        results = await seeder.process_therapeutic_documents()
        
        print("\n📊 Therapeutic MongoDB Seeding Results:")
        print(f"  Status: {results['status']}")
        print(f"  Documents Processed: {results['documents_processed']}")
        print(f"  Total Chunks: {results['total_chunks']}")
        print(f"  Embedder: {results['embedder_id']}")
        print(f"  Model: {results['embedding_model']}")
        
        print("\n📋 Document Details:")
        for result in results['results']:
            print(f"  • {result['document']}: {result['chunks']} chunks")
            print(f"    Care contexts: {', '.join(result['care_contexts'])}")
            print(f"    Category: {result['therapeutic_category']}")
        
        return results
        
    finally:
        await seeder.cleanup()

if __name__ == "__main__":
    asyncio.run(main())