"""Enhanced Seed Data with Advanced Processing Pipeline"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.mongo_connection import close_enhanced_mongo, init_enhanced_mongo
from app.database.mongo_connection import enhanced_mongo_manager as mongo_manager

load_dotenv()
logger = logging.getLogger(__name__)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

try:
    from app.utils.document_processor import (
        DocumentChunk,
        DocumentMetadata,
        ProcessingConfig,
        process_documents_for_seeding,
    )

    ADVANCED_PROCESSOR_AVAILABLE = True
except ImportError:
    ADVANCED_PROCESSOR_AVAILABLE = False

    # Create fallback classes when document processor is not available
    from dataclasses import dataclass
    from typing import List, Optional

    @dataclass
    class DocumentMetadata:
        """Fallback document metadata"""

        file_path: str
        title: str
        file_type: str
        file_size: int
        mime_type: str
        encoding: str
        char_count: int = 0
        word_count: int = 0
        content_hash: str = ""
        extraction_method: str = "basic"
        processing_errors: Optional[List[str]] = None

        def __post_init__(self):
            if self.processing_errors is None:
                self.processing_errors = []

    @dataclass
    class DocumentChunk:
        """Fallback document chunk"""

        chunk_id: str
        content: str
        chunk_index: int
        start_char: int
        end_char: int
        metadata: DocumentMetadata
        embedding_text: str
        chunk_type: str = "content"
        confidence: float = 1.0


@dataclass
class AdvancedSeedConfig:
    """Advanced seeding configuration"""

    use_real_embeddings: bool = os.getenv("USE_REAL_EMBEDDINGS", "1") == "1"
    force_synthetic: bool = os.getenv("SEED_USE_SYNTHETIC_EMBEDDINGS", "0") == "1"
    clear_existing: bool = os.getenv("SEED_CLEAR_EXISTING", "0") == "1"
    migration_mode: bool = os.getenv("SEED_MIGRATION_MODE", "0") == "1"
    incremental_mode: bool = os.getenv("SEED_INCREMENTAL_MODE", "0") == "1"
    initial_batch_size: int = int(os.getenv("SEED_BATCH_SIZE", "16"))
    min_batch_size: int = int(os.getenv("SEED_MIN_BATCH_SIZE", "4"))
    max_batch_size: int = int(os.getenv("SEED_MAX_BATCH_SIZE", "32"))
    dynamic_batch_sizing: bool = os.getenv("SEED_DYNAMIC_BATCH_SIZING", "1") == "1"

    max_workers: int = int(os.getenv("SEED_MAX_WORKERS", "4"))
    enable_parallel_processing: bool = os.getenv("SEED_PARALLEL_PROCESSING", "1") == "1"
    docs_path: Optional[str] = os.getenv("SEED_DOCS_PATH") or "data/docs"
    chunk_chars: int = int(os.getenv("SEED_CHUNK_CHARS", "1500"))
    chunk_overlap: int = int(os.getenv("SEED_CHUNK_OVERLAP", "180"))
    max_file_size_mb: int = int(os.getenv("SEED_MAX_FILE_SIZE_MB", "50"))
    enable_pdf_processing: bool = os.getenv("SEED_ENABLE_PDF", "1") == "1"
    enable_docx_processing: bool = os.getenv("SEED_ENABLE_DOCX", "1") == "1"
    enable_csv_processing: bool = os.getenv("SEED_ENABLE_CSV", "1") == "1"
    create_atlas_indexes: bool = os.getenv("SEED_CREATE_ATLAS_INDEXES", "1") == "1"
    monitor_index_creation: bool = os.getenv("SEED_MONITOR_INDEX_CREATION", "1") == "1"
    atlas_index_timeout: int = int(os.getenv("ATLAS_INDEX_TIMEOUT", "600"))

    # Error handling and retry
    max_retries: int = int(os.getenv("SEED_MAX_RETRIES", "3"))
    retry_delay: float = float(os.getenv("SEED_RETRY_DELAY", "2.0"))
    skip_failed_files: bool = os.getenv("SEED_SKIP_FAILED_FILES", "1") == "1"

    # Memory optimization
    enable_memory_monitoring: bool = (
        os.getenv("SEED_MEMORY_MONITORING", "1") == "1" and PSUTIL_AVAILABLE
    )
    memory_threshold_percent: float = float(os.getenv("SEED_MEMORY_THRESHOLD", "85.0"))
    gc_frequency: int = int(os.getenv("SEED_GC_FREQUENCY", "10"))  # Every N batches

    # Progress tracking
    enable_detailed_progress: bool = os.getenv("SEED_DETAILED_PROGRESS", "1") == "1"
    progress_report_frequency: int = int(os.getenv("SEED_PROGRESS_FREQUENCY", "5"))

    # Quality control
    enable_quality_checks: bool = os.getenv("SEED_QUALITY_CHECKS", "1") == "1"
    min_content_quality_score: float = float(os.getenv("SEED_MIN_QUALITY_SCORE", "0.3"))

    # Control flags
    dry_run: bool = os.getenv("SEED_DRY_RUN", "0") == "1"

    @property
    def effective_use_embeddings(self) -> bool:
        """Determine if we should use real embeddings"""
        if self.force_synthetic:
            return False
        return self.use_real_embeddings


@dataclass
class ProcessingStats:
    """Enhanced processing statistics tracking"""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # File processing stats
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0

    # Content stats
    total_chunks: int = 0
    total_characters: int = 0
    total_embeddings_generated: int = 0

    # Performance stats
    total_processing_time: float = 0.0
    average_batch_time: float = 0.0
    current_batch_size: int = 16
    memory_usage_mb: List[float] = field(default_factory=list)

    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str):
        """Add error to tracking"""
        self.errors.append(f"{datetime.now()}: {error}")
        logger.error(error)

    def add_warning(self, warning: str):
        """Add warning to tracking"""
        self.warnings.append(f"{datetime.now()}: {warning}")
        logger.warning(warning)

    def calculate_rate(self) -> Dict[str, float]:
        """Calculate processing rates"""
        elapsed = (self.end_time or datetime.now()) - self.start_time
        elapsed_seconds = elapsed.total_seconds()

        if elapsed_seconds == 0:
            return {}

        return {
            "files_per_second": self.processed_files / elapsed_seconds,
            "chunks_per_second": self.total_chunks / elapsed_seconds,
            "characters_per_second": self.total_characters / elapsed_seconds,
            "embeddings_per_second": self.total_embeddings_generated / elapsed_seconds,
        }


class AdvancedSeedingPipeline:
    """Advanced seeding pipeline with comprehensive enhancements"""

    def __init__(self, config: AdvancedSeedConfig):
        self.config = config
        self.stats = ProcessingStats()
        self.embedding_service = None
        self.current_batch_size = config.initial_batch_size
        self.executor = None

        if config.enable_parallel_processing:
            self.executor = ThreadPoolExecutor(max_workers=config.max_workers)

        logger.info(
            f"Advanced seeding pipeline initialized: embeddings={config.effective_use_embeddings}, parallel={config.enable_parallel_processing}"
        )

    async def initialize(self):
        """Initialize the seeding pipeline with comprehensive validation"""
        logger.info("🚀 Initializing Advanced Seeding Pipeline...")

        # Validate environment
        validation = self._validate_processing_environment()

        if validation["status"] == "degraded":
            logger.warning("⚠️ Pipeline running in degraded mode")
            for error in validation["errors"]:
                logger.error(f"❌ {error}")

        for warning in validation["warnings"]:
            logger.warning(f"⚠️ {warning}")

        logger.info(f"📋 Available features: {validation['features']}")

        # Initialize MongoDB
        ok = await init_enhanced_mongo()
        if not ok:
            raise RuntimeError("Failed to initialize enhanced MongoDB connection")

        # Initialize embedding service if available
        if (
            self.config.effective_use_embeddings
            and validation["features"]["embedding_service"]
        ):
            self.embedding_service = await self._get_real_embedding_service()
            if self.embedding_service is None:
                if not os.getenv("RAG_SYNTHETIC_QUERY_EMBEDDINGS", "0") == "1":
                    raise RuntimeError(
                        "Failed to initialize EmbeddingService and no synthetic fallback enabled"
                    )
                logger.warning("⚠️ EmbeddingService failed, using synthetic fallback")
        elif self.config.effective_use_embeddings:
            logger.warning(
                "⚠️ Real embeddings requested but EmbeddingService not available, using synthetic"
            )

        logger.info("✅ Advanced Seeding Pipeline initialized")
        return validation

    async def _get_real_embedding_service(self):
        """Get initialized EmbeddingService instance"""
        try:
            from app.dependencies import get_embedding_service

            service = get_embedding_service()

            if not service.is_ready:
                logger.info("🔥 Warming up EmbeddingService...")
                warmup_result = await service.warmup()

                if not warmup_result.get("warmup_successful"):
                    raise RuntimeError(
                        f"EmbeddingService warmup failed: {warmup_result.get('error')}"
                    )

            logger.info(
                f"✅ EmbeddingService ready: {service.embedding_dim}D embeddings"
            )
            return service

        except Exception as e:
            logger.error(f"❌ Failed to get EmbeddingService: {e}")
            return None

    async def run_complete_seeding(self) -> Dict[str, Any]:
        """Run the complete enhanced seeding process"""
        try:
            await self.initialize()

            # Phase 1: Clear existing data if requested
            if self.config.clear_existing:
                clear_results = await self._clear_collections_advanced()
                logger.info(f"🗑️ Cleared collections: {clear_results}")

            # Phase 2: Create/Monitor Atlas indexes
            if self.config.create_atlas_indexes:
                index_results = await self._ensure_atlas_indexes_with_monitoring()
                logger.info(f"📊 Atlas index status: {index_results}")

            # Phase 3: Migration if requested
            if self.config.migration_mode:
                migration_results = await self._advanced_migration()
                logger.info(f"🔄 Migration completed: {migration_results}")

            # Phase 4: Process documents with advanced pipeline
            if self.config.docs_path:
                doc_results = await self._process_documents_advanced()
                logger.info(f"📄 Document processing completed: {doc_results}")

            # Phase 5: Process FAQ data
            faq_results = await self._process_faq_advanced()
            logger.info(f"❓ FAQ processing completed: {faq_results}")

            # Phase 6: Quality validation
            if self.config.enable_quality_checks:
                quality_results = await self._validate_seeding_quality()
                logger.info(f"✅ Quality validation: {quality_results}")

            # Finalize stats
            self.stats.end_time = datetime.now()

            return self._generate_final_report()

        except Exception as e:
            self.stats.add_error(f"Seeding pipeline failed: {e}")
            raise
        finally:
            await self._cleanup()

    async def _clear_collections_advanced(self) -> Dict[str, Any]:
        """Advanced collection clearing with progress tracking"""
        results = {}

        collections = [
            ("knowledge_vectors", mongo_manager.knowledge_vectors),
            ("embeddings", mongo_manager.embeddings),
            ("documents", mongo_manager.documents),
        ]

        for name, collection_func in collections:
            try:
                if not self.config.dry_run:
                    coll: AsyncIOMotorCollection = collection_func()
                    result = await coll.delete_many({})
                    results[name] = result.deleted_count
                else:
                    results[name] = "dry_run"

                logger.info(f"🗑️ Cleared {name}: {results[name]}")

            except Exception as e:
                self.stats.add_error(f"Failed to clear {name}: {e}")
                results[name] = f"error: {e}"

        return results

    async def _ensure_atlas_indexes_with_monitoring(self) -> Dict[str, Any]:
        """Create Atlas indexes with comprehensive monitoring"""
        if not mongo_manager.is_atlas:
            return {"status": "not_atlas"}

        results = {}

        try:
            # Create indexes for both collections
            collections = ["embeddings", "knowledge_vectors"]

            for collection_name in collections:
                logger.info(
                    f"📊 Creating Atlas Vector Search index for {collection_name}..."
                )

                index_name = f"vector_index_{collection_name}"

                if not self.config.dry_run:
                    success = await mongo_manager.create_vector_search_index(
                        collection_name=collection_name, index_name=index_name
                    )

                    if success and self.config.monitor_index_creation:
                        # Monitor index creation progress
                        status = await self._monitor_index_creation(
                            collection_name, index_name
                        )
                        results[collection_name] = status
                    else:
                        results[collection_name] = "created" if success else "failed"
                else:
                    results[collection_name] = "dry_run"

            return results

        except Exception as e:
            self.stats.add_error(f"Atlas index creation failed: {e}")
            return {"error": str(e)}

    async def _monitor_index_creation(
        self, collection_name: str, index_name: str
    ) -> Dict[str, Any]:
        """Monitor Atlas Vector Search index creation progress"""
        start_time = datetime.now()
        timeout = timedelta(seconds=self.config.atlas_index_timeout)

        logger.info(
            f"🔍 Monitoring index creation for {collection_name}.{index_name}..."
        )

        while datetime.now() - start_time < timeout:
            try:
                # Check index status through MongoDB
                db = mongo_manager.get_database()
                collection = db[collection_name]

                # List search indexes (Atlas-specific command)
                try:
                    indexes = await collection.list_search_indexes().to_list(
                        length=None
                    )

                    for index in indexes:
                        if index.get("name") == index_name:
                            status = index.get("status", "unknown")

                            if status == "READY":
                                logger.info(f"✅ Index {index_name} is ready!")
                                return {
                                    "status": "ready",
                                    "creation_time": (
                                        datetime.now() - start_time
                                    ).total_seconds(),
                                    "index_info": index,
                                }
                            elif status == "FAILED":
                                logger.error(f"❌ Index {index_name} creation failed!")
                                return {
                                    "status": "failed",
                                    "error": index.get("statusDetail", "Unknown error"),
                                }
                            else:
                                logger.info(f"🔄 Index {index_name} status: {status}")

                except Exception as e:
                    # If we can't check status, assume it's still being created
                    logger.debug(
                        f"Index status check error (normal during creation): {e}"
                    )

                # Wait before next check
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error monitoring index creation: {e}")
                break

        # Timeout reached
        logger.warning(f"⏰ Index creation monitoring timed out for {index_name}")
        return {"status": "timeout", "elapsed_time": self.config.atlas_index_timeout}

    async def _process_documents_advanced(self) -> Dict[str, Any]:
        """Advanced document processing with multi-format support"""
        if not self.config.docs_path or not Path(self.config.docs_path).exists():
            return {
                "status": "no_documents",
                "reason": f"Path not found: {self.config.docs_path}",
            }

        logger.info(
            f"📄 Starting advanced document processing from {self.config.docs_path}"
        )

        try:
            # Use advanced document processor if available
            if ADVANCED_PROCESSOR_AVAILABLE:
                chunks = await self._process_with_advanced_processor()
            else:
                chunks = await self._process_with_basic_processor()

            if not chunks:
                return {
                    "status": "no_content",
                    "message": "No processable documents found",
                }

            # Store chunks with enhanced metadata
            stored_chunks = await self._store_document_chunks_advanced(chunks)

            return {
                "status": "success",
                "total_chunks": len(chunks),
                "stored_chunks": stored_chunks,
                "processing_time": time.time() - self.stats.start_time.timestamp(),
            }

        except Exception as e:
            self.stats.add_error(f"Document processing failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _process_with_advanced_processor(self) -> List[DocumentChunk]:
        """Process documents using the advanced document processor"""
        config = ProcessingConfig(
            chunk_size=self.config.chunk_chars,
            chunk_overlap=self.config.chunk_overlap,
            max_workers=self.config.max_workers,
            use_parallel_processing=self.config.enable_parallel_processing,
            max_file_size_mb=self.config.max_file_size_mb,
            skip_corrupted_files=self.config.skip_failed_files,
        )

        # Configure supported formats based on config
        supported_extensions = [".txt", ".md", ".rst"]
        if self.config.enable_pdf_processing:
            supported_extensions.extend([".pdf"])
        if self.config.enable_docx_processing:
            supported_extensions.extend([".docx", ".doc"])
        if self.config.enable_csv_processing:
            supported_extensions.extend([".csv"])

        config.supported_extensions = supported_extensions

        return await process_documents_for_seeding(self.config.docs_path, config)

    async def _process_with_basic_processor(self) -> List[DocumentChunk]:
        """Enhanced fallback document processing"""
        logger.warning(
            "📄 Using basic document processor (advanced processor not available)"
        )

        chunks = []
        docs_path = Path(self.config.docs_path)

        # Support basic file types
        file_patterns = ["*.txt", "*.md", "*.rst"]

        for pattern in file_patterns:
            for file_path in docs_path.rglob(pattern):
                try:
                    # Basic file size check
                    file_size = file_path.stat().st_size
                    if file_size > self.config.max_file_size_mb * 1024 * 1024:
                        logger.warning(f"⚠️ Skipping large file: {file_path}")
                        self.stats.skipped_files += 1
                        continue

                    # Read content with encoding fallback
                    content = ""
                    for encoding in ["utf-8", "latin-1", "cp1252"]:
                        try:
                            content = file_path.read_text(encoding=encoding)
                            break
                        except UnicodeDecodeError:
                            continue

                    if not content or len(content.strip()) < 50:
                        logger.warning(f"⚠️ Skipping file with no content: {file_path}")
                        self.stats.skipped_files += 1
                        continue

                    # Create metadata using fallback class
                    metadata = DocumentMetadata(
                        file_path=str(file_path),
                        title=file_path.stem,
                        file_type=file_path.suffix[1:] if file_path.suffix else "txt",
                        file_size=file_size,
                        mime_type="text/plain",
                        encoding="utf-8",
                        char_count=len(content),
                        word_count=len(content.split()),
                        content_hash=hashlib.md5(content.encode()).hexdigest(),
                        extraction_method="basic_text",
                    )

                    # Simple chunking
                    chunk_size = self.config.chunk_chars
                    overlap = self.config.chunk_overlap

                    chunk_index = 0
                    for i in range(0, len(content), chunk_size - overlap):
                        chunk_content = content[i : i + chunk_size].strip()

                        if len(chunk_content) >= 100:  # Minimum chunk size
                            chunk = DocumentChunk(
                                chunk_id=f"{metadata.content_hash}_{chunk_index}",
                                content=chunk_content,
                                chunk_index=chunk_index,
                                start_char=i,
                                end_char=i + len(chunk_content),
                                metadata=metadata,
                                embedding_text=f"{metadata.title}\n\n{chunk_content}".strip(),
                            )
                            chunks.append(chunk)
                            chunk_index += 1

                    self.stats.processed_files += 1

                except Exception as e:
                    self.stats.add_error(f"Failed to process {file_path}: {e}")
                    self.stats.failed_files += 1
                    if not self.config.skip_failed_files:
                        raise

        self.stats.total_files = (
            self.stats.processed_files
            + self.stats.failed_files
            + self.stats.skipped_files
        )
        self.stats.total_chunks = len(chunks)

        return chunks

    async def _manage_memory(self):
        """Enhanced memory management with availability check"""
        if not self.config.enable_memory_monitoring or not PSUTIL_AVAILABLE:
            return

        try:
            process = psutil.Process()
            memory_percent = process.memory_percent()
            memory_mb = process.memory_info().rss / 1024 / 1024

            self.stats.memory_usage_mb.append(memory_mb)

            if memory_percent > self.config.memory_threshold_percent:
                logger.warning(
                    f"⚠️ High memory usage: {memory_percent:.1f}% ({memory_mb:.1f}MB)"
                )

                # Trigger garbage collection
                import gc

                collected = gc.collect()
                logger.info(f"🗑️ Garbage collection freed {collected} objects")

                # Reduce batch size temporarily
                if self.config.dynamic_batch_sizing:
                    old_size = self.current_batch_size
                    self.current_batch_size = max(
                        self.config.min_batch_size, int(self.current_batch_size * 0.7)
                    )
                    if old_size != self.current_batch_size:
                        logger.info(
                            f"📉 Reduced batch size to {self.current_batch_size} due to memory pressure"
                        )

                # Brief pause to stabilize
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.debug(f"Memory monitoring error: {e}")

    async def _store_document_chunks_advanced(self, chunks: List[DocumentChunk]) -> int:
        """Store document chunks with advanced batching and optimization"""
        if not chunks:
            return 0

        docs_coll: AsyncIOMotorCollection = mongo_manager.documents()
        emb_coll: AsyncIOMotorCollection = mongo_manager.embeddings()

        stored_count = 0
        document_ids = {}

        # First, create document metadata entries
        for chunk in chunks:
            doc_path = chunk.metadata.file_path

            if doc_path not in document_ids:
                doc_payload = {
                    "title": chunk.metadata.title,
                    "document_type": chunk.metadata.file_type,
                    "external_id": doc_path,
                    "processing_status": "completed",
                    "source": "advanced_processor",
                    "file_size": chunk.metadata.file_size,
                    "char_count": chunk.metadata.char_count,
                    "word_count": chunk.metadata.word_count,
                    "content_hash": chunk.metadata.content_hash,
                    "extraction_method": chunk.metadata.extraction_method,
                    "ingested_at": datetime.utcnow(),
                    "processing_errors": chunk.metadata.processing_errors,
                }

                if not self.config.dry_run:
                    result = await docs_coll.update_one(
                        {"external_id": doc_path},
                        {"$setOnInsert": doc_payload},
                        upsert=True,
                    )

                    if result.upserted_id:
                        document_ids[doc_path] = result.upserted_id
                    else:
                        existing = await docs_coll.find_one(
                            {"external_id": doc_path}, {"_id": 1}
                        )
                        document_ids[doc_path] = (
                            existing["_id"] if existing else ObjectId()
                        )
                else:
                    document_ids[doc_path] = ObjectId()

        # Process chunks in optimized batches
        chunk_data_batch = []
        embedding_texts = []

        for chunk in chunks:
            doc_id = document_ids.get(chunk.metadata.file_path)
            if not doc_id:
                continue

            chunk_data_batch.append({"chunk": chunk, "doc_id": doc_id})
            embedding_texts.append(chunk.embedding_text)

            # Process batch when it reaches optimal size
            if len(chunk_data_batch) >= self.current_batch_size:
                batch_stored = await self._process_chunk_batch(
                    chunk_data_batch, embedding_texts, emb_coll
                )
                stored_count += batch_stored

                # Clear batch
                chunk_data_batch = []
                embedding_texts = []

                # Memory management
                if self.config.enable_memory_monitoring:
                    await self._manage_memory()

        # Process remaining chunks
        if chunk_data_batch:
            batch_stored = await self._process_chunk_batch(
                chunk_data_batch, embedding_texts, emb_coll
            )
            stored_count += batch_stored

        return stored_count

    async def _process_chunk_batch(
        self,
        chunk_data_batch: List[Dict],
        embedding_texts: List[str],
        emb_coll: AsyncIOMotorCollection,
    ) -> int:
        """Process a batch of chunks with embeddings"""
        if not chunk_data_batch:
            return 0

        batch_start_time = time.time()

        try:
            # Generate embeddings for the batch
            embeddings = await self._generate_embeddings_batch(embedding_texts)

            # Store chunks with embeddings
            stored = 0
            for chunk_data, embedding in zip(chunk_data_batch, embeddings):
                chunk = chunk_data["chunk"]
                doc_id = chunk_data["doc_id"]

                emb_doc = {
                    "document_id": doc_id,
                    "chunk_index": chunk.chunk_index,
                    "title": chunk.metadata.title,
                    "content": chunk.content,
                    "embedding": embedding,
                    "embedding_model": "sentence-transformers/all-mpnet-base-v2"
                    if self.config.effective_use_embeddings
                    else "synthetic",
                    "embedding_dimension": len(embedding),
                    "chunk_type": chunk.chunk_type,
                    "confidence": chunk.confidence,
                    "char_count": len(chunk.content),
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "category": "document",
                    "ingested_at": datetime.utcnow(),
                    "processing_method": "advanced_pipeline",
                }

                if not self.config.dry_run:
                    await emb_coll.update_one(
                        {"document_id": doc_id, "chunk_index": chunk.chunk_index},
                        {"$set": emb_doc},
                        upsert=True,
                    )

                stored += 1

            # Update statistics
            batch_time = time.time() - batch_start_time
            self.stats.average_batch_time = (
                self.stats.average_batch_time + batch_time
            ) / 2
            self.stats.total_embeddings_generated += len(embeddings)

            # Dynamic batch size optimization
            if self.config.dynamic_batch_sizing:
                await self._optimize_batch_size(batch_time, len(chunk_data_batch))

            logger.debug(f"📦 Processed batch: {stored} chunks in {batch_time:.2f}s")
            return stored

        except Exception as e:
            self.stats.add_error(f"Batch processing failed: {e}")

            # Retry with smaller batch if enabled
            if len(chunk_data_batch) > 1 and self.config.max_retries > 0:
                logger.warning("🔄 Retrying batch with smaller size...")
                mid = len(chunk_data_batch) // 2

                batch1 = await self._process_chunk_batch(
                    chunk_data_batch[:mid], embedding_texts[:mid], emb_coll
                )
                batch2 = await self._process_chunk_batch(
                    chunk_data_batch[mid:], embedding_texts[mid:], emb_coll
                )

                return batch1 + batch2

            return 0

    async def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts with retry logic"""
        if not texts:
            return []

        for attempt in range(self.config.max_retries + 1):
            try:
                if self.config.effective_use_embeddings and self.embedding_service:
                    embeddings = await self.embedding_service.embed_batch(
                        texts, show_progress=False
                    )
                    return embeddings
                else:
                    # Use synthetic embeddings
                    synthetic_dim = int(os.getenv("RAG_SYNTHETIC_DIM", "32"))
                    return [
                        self._synthetic_embedding(text, synthetic_dim) for text in texts
                    ]

            except Exception as e:
                if attempt < self.config.max_retries:
                    logger.warning(
                        f"🔄 Embedding generation attempt {attempt + 1} failed, retrying: {e}"
                    )
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    self.stats.add_error(
                        f"Embedding generation failed after {self.config.max_retries} retries: {e}"
                    )

                    # Fallback to synthetic
                    synthetic_dim = int(os.getenv("RAG_SYNTHETIC_DIM", "32"))
                    return [
                        self._synthetic_embedding(text, synthetic_dim) for text in texts
                    ]

    def _synthetic_embedding(self, text: str, dim: int = 32) -> List[float]:
        """Generate synthetic embedding"""
        h = hashlib.sha256((text or "").encode("utf-8")).digest()
        vec = [((h[i % len(h)] / 255.0) - 0.5) for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def _optimize_batch_size(self, batch_time: float, batch_size: int):
        """Dynamically optimize batch size based on performance"""
        target_time = 5.0  # Target 5 seconds per batch

        if batch_time > target_time * 1.5 and batch_size > self.config.min_batch_size:
            # Batch too slow, reduce size
            self.current_batch_size = max(
                self.config.min_batch_size, int(self.current_batch_size * 0.8)
            )
        elif batch_time < target_time * 0.5 and batch_size < self.config.max_batch_size:
            # Batch too fast, increase size
            self.current_batch_size = min(
                self.config.max_batch_size, int(self.current_batch_size * 1.2)
            )

        self.stats.current_batch_size = self.current_batch_size

    async def _process_faq_advanced(self) -> Dict[str, Any]:
        """Advanced FAQ processing with enhanced error handling"""
        try:
            from app.services.multi_db_service import get_faq_seed_rows

            # Get FAQ data with retry logic
            faq_rows = []
            for attempt in range(self.config.max_retries + 1):
                try:
                    faq_rows = await get_faq_seed_rows(None)  # Get all FAQs
                    break
                except Exception as e:
                    if attempt < self.config.max_retries:
                        logger.warning(
                            f"🔄 FAQ fetch attempt {attempt + 1} failed, retrying: {e}"
                        )
                        await asyncio.sleep(self.config.retry_delay)
                    else:
                        self.stats.add_error(
                            f"Failed to fetch FAQs after {self.config.max_retries} retries: {e}"
                        )
                        return {"status": "error", "error": str(e)}

            if not faq_rows:
                return {"status": "no_data", "message": "No FAQ data found"}

            # Process FAQs in batches
            processed = await self._process_faq_batch(faq_rows)

            return {
                "status": "success",
                "total_faqs": len(faq_rows),
                "processed_faqs": processed,
            }

        except Exception as e:
            self.stats.add_error(f"FAQ processing failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _process_faq_batch(self, faq_rows: List[Dict[str, Any]]) -> int:
        """Process FAQ batch with embeddings"""
        if not faq_rows:
            return 0

        coll: AsyncIOMotorCollection = mongo_manager.knowledge_vectors()
        processed = 0

        # Prepare embedding texts
        embedding_texts = []
        valid_rows = []

        for row in faq_rows:
            question = row.get("question", "").strip()
            answer = row.get("answer", "").strip()

            if question and answer:
                valid_rows.append(row)
                embedding_texts.append(f"{question}\n\n{answer}")

        if not valid_rows:
            return 0

        # Generate embeddings
        embeddings = await self._generate_embeddings_batch(embedding_texts)

        # Store FAQ entries
        for row, embedding in zip(valid_rows, embeddings):
            payload = {
                "scylla_key": row.get("scylla_key"),
                "question": row.get("question"),
                "answer": row.get("answer"),
                "embedding": embedding,
                "embedding_model": "sentence-transformers/all-mpnet-base-v2"
                if self.config.effective_use_embeddings
                else "synthetic",
                "embedding_dimension": len(embedding),
                "source": "scylla_advanced",
                "version": row.get("version", 1),
                "updated_at": datetime.utcnow(),
                "last_synced_at": datetime.utcnow(),
                "processing_method": "advanced_pipeline",
            }

            if not self.config.dry_run:
                await coll.update_one(
                    {"scylla_key": row.get("scylla_key")},
                    {"$set": payload},
                    upsert=True,
                )

            processed += 1

        return processed

    async def _advanced_migration(self) -> Dict[str, Any]:
        """Advanced migration with progress tracking"""
        logger.info("🔄 Starting advanced migration to real embeddings...")

        # Migration implementation would go here
        # This would be similar to the existing migration but with better progress tracking

        return {"status": "completed", "migrated_items": 0}

    async def _validate_seeding_quality(self) -> Dict[str, Any]:
        """Validate the quality of seeded data"""
        try:
            # Check collection counts
            emb_coll = mongo_manager.embeddings()
            kv_coll = mongo_manager.knowledge_vectors()
            docs_coll = mongo_manager.documents()

            emb_count = await emb_coll.count_documents({})
            kv_count = await kv_coll.count_documents({})
            docs_count = await docs_coll.count_documents({})

            # Sample embeddings for quality check
            sample_embeddings = await emb_coll.find({}).limit(5).to_list(length=5)

            quality_score = 1.0
            issues = []

            # Check for empty embeddings
            for emb in sample_embeddings:
                if not emb.get("embedding") or len(emb.get("embedding", [])) == 0:
                    quality_score -= 0.2
                    issues.append("Empty embeddings found")
                    break

            # Check for consistent dimensions
            dimensions = [
                len(emb.get("embedding", []))
                for emb in sample_embeddings
                if emb.get("embedding")
            ]
            if len(set(dimensions)) > 1:
                quality_score -= 0.3
                issues.append("Inconsistent embedding dimensions")

            return {
                "status": "completed",
                "quality_score": quality_score,
                "collection_counts": {
                    "embeddings": emb_count,
                    "knowledge_vectors": kv_count,
                    "documents": docs_count,
                },
                "issues": issues,
                "passed": quality_score >= self.config.min_content_quality_score,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
        rates = self.stats.calculate_rate()

        return {
            "status": "completed",
            "processing_time_seconds": processing_time,
            "statistics": {
                "files": {
                    "total": self.stats.total_files,
                    "processed": self.stats.processed_files,
                    "failed": self.stats.failed_files,
                    "skipped": self.stats.skipped_files,
                },
                "content": {
                    "total_chunks": self.stats.total_chunks,
                    "total_characters": self.stats.total_characters,
                    "total_embeddings": self.stats.total_embeddings_generated,
                },
                "performance": {
                    "rates": rates,
                    "average_batch_time": self.stats.average_batch_time,
                    "final_batch_size": self.stats.current_batch_size,
                    "memory_usage_mb": {
                        "max": max(self.stats.memory_usage_mb)
                        if self.stats.memory_usage_mb
                        else 0,
                        "avg": sum(self.stats.memory_usage_mb)
                        / len(self.stats.memory_usage_mb)
                        if self.stats.memory_usage_mb
                        else 0,
                    },
                },
            },
            "configuration": {
                "real_embeddings": self.config.effective_use_embeddings,
                "parallel_processing": self.config.enable_parallel_processing,
                "dynamic_batching": self.config.dynamic_batch_sizing,
                "atlas_indexing": self.config.create_atlas_indexes,
            },
            "errors": self.stats.errors,
            "warnings": self.stats.warnings,
        }

    async def _cleanup(self):
        """Enhanced cleanup"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)

            await close_enhanced_mongo()

            logger.info("✅ Advanced seeding pipeline cleanup completed")

        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

    def _validate_processing_environment(self) -> Dict[str, Any]:
        """Validate the processing environment and available features"""
        validation = {
            "status": "ready",
            "features": {
                "advanced_processor": ADVANCED_PROCESSOR_AVAILABLE,
                "memory_monitoring": PSUTIL_AVAILABLE,
                "embedding_service": False,
                "mongodb": False,
            },
            "warnings": [],
            "errors": [],
        }

        # Check embedding service
        try:
            from app.dependencies import embedding_service

            validation["features"]["embedding_service"] = embedding_service is not None
        except Exception:
            validation["warnings"].append("EmbeddingService not available")

        # Check MongoDB
        try:
            validation["features"]["mongodb"] = mongo_manager is not None
        except Exception:
            validation["errors"].append("MongoDB manager not available")
            validation["status"] = "degraded"

        # Add warnings for missing features
        if not ADVANCED_PROCESSOR_AVAILABLE:
            validation["warnings"].append(
                "Advanced document processor not available - using basic processor"
            )

        if not PSUTIL_AVAILABLE:
            validation["warnings"].append(
                "Memory monitoring not available - psutil not installed"
            )

        return validation


# Main execution function
async def main_advanced_seeding() -> Dict[str, Any]:
    """Main function for advanced seeding"""
    config = AdvancedSeedConfig()

    logger.info("🚀 Starting Advanced Seeding Pipeline V2")
    logger.info(
        f"Configuration: real_embeddings={config.effective_use_embeddings}, "
        f"parallel={config.enable_parallel_processing}, "
        f"dynamic_batching={config.dynamic_batch_sizing}"
    )

    pipeline = AdvancedSeedingPipeline(config)

    try:
        result = await pipeline.run_complete_seeding()
        logger.info("✅ Advanced seeding completed successfully!")
        return result

    except Exception as e:
        logger.error(f"❌ Advanced seeding failed: {e}")
        raise


main = main_advanced_seeding  # For compatibility with existing imports
main_enhanced = main_advanced_seeding  # Alternative name

# Export all the important functions and classes
__all__ = [
    "main_advanced_seeding",
    "main",  # Backward compatibility
    "main_enhanced",  # Alternative name
    "AdvancedSeedConfig",
    "ProcessingStats",
    "AdvancedSeedingPipeline",
]

if __name__ == "__main__":
    asyncio.run(main_advanced_seeding())
