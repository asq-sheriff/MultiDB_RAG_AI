"""
PostgreSQL Hybrid Seeding with BGE Embeddings
Seeds document chunks and knowledge base with hybrid BGE service embeddings
"""

import asyncio
import logging
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from data_layer.models.postgres.postgres_models import DatabaseBase, Document, DocumentChunk
from data_layer.connections.postgres_connection import get_postgres_manager
from ai_services.shared.config.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8005")
DOCS_PATH = os.getenv("SEED_DOCS_PATH", "data/docs")
CHUNK_SIZE = int(os.getenv("SEED_CHUNK_CHARS", "1500"))
CHUNK_OVERLAP = int(os.getenv("SEED_CHUNK_OVERLAP", "200"))
BATCH_SIZE = int(os.getenv("SEED_BATCH_SIZE", "8"))


class PostgreSQLHybridSeeder:
    """PostgreSQL seeding with hybrid BGE embeddings"""

    def __init__(self):
        self.embedding_service_url = EMBEDDING_SERVICE_URL
        self.embedder_id = "hybrid-bge-large-en-v1.5"
        self.embedding_model = "bge-large-en-v1.5"
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database connection and verify embedding service"""
        # Initialize database using postgres manager
        postgres_manager = get_postgres_manager()
        await postgres_manager.initialize()
        self.session_factory = postgres_manager._session_factory

        # Verify embedding service
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.embedding_service_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f"✅ Connected to hybrid embedding service")
                        logger.info(f"📊 Model: {health_data.get('model')}, Dimensions: {health_data.get('dimension')}")
                        return True
                    else:
                        raise RuntimeError(f"Embedding service unhealthy: {response.status}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to embedding service: {e}")
                return False

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using hybrid service"""
        async with aiohttp.ClientSession() as session:
            payload = {"texts": texts}
            async with session.post(f"{self.embedding_service_url}/embeddings", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    embeddings = result["embeddings"]
                    logger.debug(f"📊 Generated {len(embeddings)} embeddings with {len(embeddings[0])} dimensions")
                    return embeddings
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"Embedding generation failed: {response.status} - {error_text}")

    async def process_documents(self) -> Dict[str, Any]:
        """Process documents from the docs directory"""
        docs_path = Path(DOCS_PATH)
        if not docs_path.exists():
            logger.warning(f"⚠️ Documents path not found: {DOCS_PATH}")
            return {"status": "no_documents", "path": DOCS_PATH}

        # Find all text files
        text_files = []
        for pattern in ["*.txt", "*.md", "*.rst"]:
            text_files.extend(docs_path.rglob(pattern))

        if not text_files:
            logger.warning(f"⚠️ No text files found in {DOCS_PATH}")
            return {"status": "no_files", "path": DOCS_PATH}

        logger.info(f"📄 Found {len(text_files)} documents to process")

        processed_docs = 0
        total_chunks = 0

        async with self.session_factory() as db:
            for file_path in text_files:
                try:
                    # Read file content
                    content = file_path.read_text(encoding='utf-8')
                    if len(content.strip()) < 100:
                        logger.warning(f"⚠️ Skipping short file: {file_path}")
                        continue

                    # Create document record
                    doc_id = uuid.uuid4()
                    checksum = hashlib.md5(content.encode()).hexdigest()

                    # Check if document already exists
                    existing_doc = await db.get(Document, doc_id)
                    if existing_doc and existing_doc.checksum == checksum:
                        logger.info(f"⏭️ Document unchanged, skipping: {file_path.name}")
                        continue

                    document = Document(
                        doc_id=doc_id,
                        source_type="file",
                        title=file_path.stem,
                        url_or_path=str(file_path),
                        checksum=checksum,
                        modality="text"
                    )

                    db.add(document)
                    await db.flush()

                    # Process chunks
                    chunks = await self.create_chunks(content, file_path.stem)
                    chunk_records = await self.store_chunks(db, doc_id, chunks)

                    total_chunks += len(chunk_records)
                    processed_docs += 1

                    logger.info(f"✅ Processed {file_path.name}: {len(chunk_records)} chunks")

                except Exception as e:
                    logger.error(f"❌ Failed to process {file_path}: {e}")
                    await db.rollback()
                    continue

            await db.commit()

        return {
            "status": "completed",
            "documents_processed": processed_docs,
            "total_chunks": total_chunks,
            "embedder_id": self.embedder_id,
            "embedding_model": self.embedding_model
        }

    async def create_chunks(self, content: str, title: str) -> List[Dict[str, Any]]:
        """Create text chunks from document content"""
        chunks = []
        chunk_size = CHUNK_SIZE
        overlap = CHUNK_OVERLAP

        for i in range(0, len(content), chunk_size - overlap):
            chunk_text = content[i:i + chunk_size].strip()
            if len(chunk_text) < 50:  # Skip very short chunks
                continue

            # Create embedding text with title context
            embedding_text = f"{title}\\n\\n{chunk_text}" if title else chunk_text

            chunks.append({
                "text": chunk_text,
                "embedding_text": embedding_text,
                "start_char": i,
                "end_char": i + len(chunk_text),
                "order": len(chunks)
            })

        return chunks

    async def store_chunks(self, db: AsyncSession, doc_id: uuid.UUID, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Store chunks with embeddings in batches"""
        chunk_records = []

        # Process in batches
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            embedding_texts = [chunk["embedding_text"] for chunk in batch]

            # Generate embeddings for batch
            try:
                embeddings = await self.generate_embeddings(embedding_texts)
            except Exception as e:
                logger.error(f"❌ Failed to generate embeddings for batch: {e}")
                continue

            # Create chunk records
            for j, (chunk_data, embedding) in enumerate(zip(batch, embeddings)):
                chunk_record = DocumentChunk(
                    chunk_id=uuid.uuid4(),
                    doc_id=doc_id,
                    index_type="content",
                    section_path=[],
                    order_in_doc=chunk_data["order"],
                    text=chunk_data["text"],
                    embedding=embedding,
                    embedder_id=self.embedder_id,
                    embedding_model=self.embedding_model,
                    chunk_metadata={
                        "start_char": chunk_data["start_char"],
                        "end_char": chunk_data["end_char"],
                        "embedding_dimensions": len(embedding),
                        "generation_method": "hybrid_bge_service"
                    }
                )

                db.add(chunk_record)
                chunk_records.append(chunk_record)

            await db.flush()
            logger.debug(f"📦 Stored batch {i//BATCH_SIZE + 1}: {len(batch)} chunks")

        return chunk_records

    async def cleanup(self):
        """Cleanup database connections"""
        # Database cleanup is handled by postgres manager
        pass

    async def run_seeding(self) -> Dict[str, Any]:
        """Run the complete seeding process"""
        try:
            logger.info("🌱 Starting PostgreSQL hybrid seeding with BGE embeddings...")

            # Initialize
            if not await self.initialize():
                return {"status": "failed", "error": "Initialization failed"}

            # Process documents
            result = await self.process_documents()

            logger.info("✅ PostgreSQL hybrid seeding completed successfully!")
            return result

        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            await self.cleanup()


async def main():
    """Main seeding function"""
    seeder = PostgreSQLHybridSeeder()
    result = await seeder.run_seeding()
    
    print("\\n📊 Seeding Results:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    return result


if __name__ == "__main__":
    asyncio.run(main())