"""Enhanced EmbeddingService with sentence-transformers/all-mpnet-base-v2 Optimization"""

from __future__ import annotations

import asyncio
import gc
import logging
import os
import psutil
import time
import threading
import torch
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Embedding model dependencies
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    EMBEDDING_DEPS_AVAILABLE = True
except ImportError as e:
    EMBEDDING_DEPS_AVAILABLE = False
    _import_error = e

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """sentence-transformers/all-mpnet-base-v2 optimized configuration for MacBook Pro"""

    # sentence-transformers/all-mpnet-base-v2 model configuration
    model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2"
    )
    fallback_model: str = os.getenv(
        "EMBEDDING_FALLBACK_MODEL", "sentence-transformers/all-mpnet-base-v2"
    )

    # Performance settings optimized for all-mpnet-base-v2
    batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "8"))  # Smaller for MacBook
    max_sequence_length: int = int(os.getenv("EMBEDDING_MAX_LENGTH", "8192"))
    normalize_embeddings: bool = (
        os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true"
    )

    # fp16 acceleration
    use_fp16: bool = os.getenv("EMBEDDING_USE_FP16", "true").lower() == "true"

    # Device configuration
    device: Optional[str] = os.getenv("EMBEDDING_DEVICE")  # Auto-detect
    enable_mps: bool = os.getenv("EMBEDDING_ENABLE_MPS", "true").lower() == "true"

    # MacBook-specific memory management
    max_cache_size_mb: int = int(
        os.getenv("EMBEDDING_CACHE_MB", "1024")
    )  # Reduced for MacBook
    thread_pool_workers: int = int(
        os.getenv("EMBEDDING_THREADS", "1")
    )  # Single thread for stability
    memory_cleanup_threshold: float = float(
        os.getenv("MEMORY_CLEANUP_THRESHOLD", "0.80")
    )  # 80% RAM usage

    # Timeout settings
    query_timeout_seconds: float = float(os.getenv("EMBEDDING_QUERY_TIMEOUT", "10.0"))
    batch_timeout_seconds: float = float(os.getenv("EMBEDDING_BATCH_TIMEOUT", "120.0"))

    enable_postgresql: bool = (
        os.getenv("EMBEDDING_ENABLE_POSTGRESQL", "false").lower() == "true"
    )

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """Create config from environment variables"""
        return cls()


class EmbeddingService:
    """sentence-transformers/all-mpnet-base-v2 optimized embedding service."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig.from_env()
        self._model: Optional[SentenceTransformer] = None
        self._model_lock = threading.Lock()
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self.config.thread_pool_workers
        )
        self._device = None
        self._embedding_dim = None

        # Performance tracking
        self._load_time: Optional[float] = None
        self._query_count = 0
        self._total_query_time = 0.0
        self._memory_cleanup_count = 0

        # Memory monitoring
        self._process = psutil.Process()

        logger.info(
            "sentence-transformers/all-mpnet-base-v2 EmbeddingService initialized"
        )

    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text using sentence-transformers/all-mpnet-base-v2.
        Optimized for MacBook Pro with memory monitoring.

        Args:
            text: Query text to embed

        Returns:
            List[float]: 1024-dimensional embedding vector

        Raises:
            TimeoutError: If embedding takes longer than configured timeout
            RuntimeError: If model loading fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Memory check before processing
        await self._check_and_cleanup_memory()

        start_time = time.time()

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._thread_pool, self._embed_single, text.strip()
                ),
                timeout=self.config.query_timeout_seconds,
            )

            # Performance tracking
            elapsed = time.time() - start_time
            self._query_count += 1
            self._total_query_time += elapsed

            if elapsed > 1.0:  # Log slow queries
                logger.warning(
                    f"Slow all-mpnet-base-v2 query: {elapsed:.2f}s for {len(text)} chars"
                )

            return result

        except asyncio.TimeoutError:
            logger.error(
                f"all-mpnet-base-v2 embedding timeout after {self.config.query_timeout_seconds}s"
            )
            raise TimeoutError(
                f"Embedding timeout: {self.config.query_timeout_seconds}s"
            )
        except Exception as e:
            logger.error(f"all-mpnet-base-v2 embedding failed: {e}")
            raise RuntimeError(f"Embedding failed: {e}")

    async def embed_batch(
        self, texts: List[str], show_progress: bool = True
    ) -> List[List[float]]:
        """
        Embed multiple texts efficiently using sentence-transformers/all-mpnet-base-v2 batch processing.
        Includes memory management for long-running operations.

        Args:
            texts: List of texts to embed
            show_progress: Whether to log progress updates

        Returns:
            List[List[float]]: List of 1024-dimensional embedding vectors
        """
        if not texts:
            return []

        # Clean and validate inputs
        clean_texts = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                logger.warning(f"Skipping empty text at index {i}")
                clean_texts.append("")  # Placeholder for consistent indexing
            else:
                clean_texts.append(text.strip())

        if not any(clean_texts):
            raise ValueError("No valid texts to embed")

        # Memory check before batch processing
        await self._check_and_cleanup_memory()

        start_time = time.time()

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._thread_pool,
                    self._embed_batch_sync,
                    clean_texts,
                    show_progress,
                ),
                timeout=self.config.batch_timeout_seconds,
            )

            elapsed = time.time() - start_time
            rate = len(clean_texts) / elapsed if elapsed > 0 else 0

            if show_progress:
                logger.info(
                    f"all-mpnet-base-v2 batch embedding: {len(clean_texts)} texts in {elapsed:.1f}s ({rate:.1f} texts/sec)"
                )

            return result

        except asyncio.TimeoutError:
            logger.error(
                f"all-mpnet-base-v2 batch timeout after {self.config.batch_timeout_seconds}s"
            )
            raise TimeoutError(
                f"Batch embedding timeout: {self.config.batch_timeout_seconds}s"
            )
        except Exception as e:
            logger.error(f"all-mpnet-base-v2 batch embedding failed: {e}")
            raise RuntimeError(f"Batch embedding failed: {e}")

    def _embed_single(self, text: str) -> List[float]:
        """Synchronous single text embedding using sentence-transformers/all-mpnet-base-v2"""
        model = self._get_model()

        try:
            # all-mpnet-base-v2 optimized encoding with fp16
            with torch.no_grad():
                embedding = model.encode(
                    text,
                    normalize_embeddings=self.config.normalize_embeddings,
                    convert_to_numpy=True,
                    batch_size=1,
                    show_progress_bar=False,
                )

            # Ensure we have a proper embedding
            if isinstance(embedding, np.ndarray):
                if embedding.ndim > 1:
                    embedding = embedding.flatten()
                return embedding.tolist()
            else:
                return list(embedding)

        except Exception as e:
            logger.error(f"all-mpnet-base-v2 encoding failed: {e}")
            raise RuntimeError(f"all-mpnet-base-v2 encoding failed: {e}")

    def _embed_batch_sync(
        self, texts: List[str], show_progress: bool
    ) -> List[List[float]]:
        """Synchronous batch embedding using sentence-transformers/all-mpnet-base-v2 with memory management"""
        model = self._get_model()

        # Filter out empty texts but maintain indices
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text:  # Non-empty after cleaning
                valid_indices.append(i)
                valid_texts.append(text)

        if not valid_texts:
            return [[0.0] * self.embedding_dim] * len(texts)

        # Process in smaller batches for memory management
        all_embeddings = []
        effective_batch_size = min(self.config.batch_size, len(valid_texts))

        try:
            with torch.no_grad():  # Prevent gradient computation
                for i in range(0, len(valid_texts), effective_batch_size):
                    batch = valid_texts[i : i + effective_batch_size]

                    if show_progress and len(valid_texts) > effective_batch_size:
                        batch_num = i // effective_batch_size + 1
                        total_batches = (
                            len(valid_texts) - 1
                        ) // effective_batch_size + 1
                        logger.info(
                            f"all-mpnet-base-v2 processing batch {batch_num}/{total_batches}"
                        )

                    # Memory cleanup between batches
                    if i > 0 and i % (effective_batch_size * 3) == 0:
                        self._cleanup_memory()

                    batch_embeddings = model.encode(
                        batch,
                        batch_size=len(batch),
                        normalize_embeddings=self.config.normalize_embeddings,
                        convert_to_numpy=True,
                        show_progress_bar=False,
                    )

                    # Convert to list format
                    if isinstance(batch_embeddings, np.ndarray):
                        if batch_embeddings.ndim == 1:
                            # Single embedding
                            all_embeddings.append(batch_embeddings.tolist())
                        else:
                            # Multiple embeddings
                            all_embeddings.extend(
                                [emb.tolist() for emb in batch_embeddings]
                            )
                    else:
                        all_embeddings.extend(batch_embeddings)

        except Exception as e:
            logger.error(f"all-mpnet-base-v2 batch processing failed: {e}")
            raise RuntimeError(f"all-mpnet-base-v2 batch processing failed: {e}")

        # Final memory cleanup
        self._cleanup_memory()

        # Reconstruct full results array with placeholders for empty texts
        results = []
        valid_iter = iter(all_embeddings)

        for i, text in enumerate(texts):
            if text:  # Non-empty
                results.append(next(valid_iter))
            else:  # Empty text placeholder
                results.append([0.0] * self.embedding_dim)

        return results

    def _get_model(self) -> SentenceTransformer:
        """Load and cache sentence-transformers/all-mpnet-base-v2 model (thread-safe with memory optimization)"""
        if self._model is not None:
            return self._model

        with self._model_lock:
            # Double-check pattern
            if self._model is not None:
                return self._model

            if not EMBEDDING_DEPS_AVAILABLE:
                raise RuntimeError(
                    f"Embedding dependencies not available: {_import_error}. "
                    "Install with: pip install torch sentence-transformers"
                )

            logger.info(
                f"Loading sentence-transformers/all-mpnet-base-v2 model: {self.config.model_name}"
            )
            load_start = time.time()

            try:
                # Auto-detect optimal device for MacBook
                if self.config.device is None or self.config.device == "auto":
                    if torch.backends.mps.is_available() and self.config.enable_mps:
                        self._device = "mps"  # Metal Performance Shaders for MacBook
                        logger.info(
                            "Using Metal Performance Shaders (MPS) for all-mpnet-base-v2"
                        )
                    elif torch.cuda.is_available():
                        self._device = "cuda"
                        logger.info("Using CUDA acceleration")
                    else:
                        self._device = "cpu"
                        logger.info("Using CPU (no hardware acceleration)")
                else:
                    # Validate the provided device
                    valid_devices = ["cpu", "cuda", "mps"]
                    if self.config.device in valid_devices:
                        self._device = self.config.device
                    else:
                        logger.warning(
                            f"Invalid device '{self.config.device}', falling back to CPU"
                        )
                        self._device = "cpu"

                # Load sentence-transformers/all-mpnet-base-v2 with optimizations
                model_kwargs = {
                    "device": self._device,  # This should now be a valid device string
                    "cache_folder": os.path.expanduser(
                        "~/.cache/sentence_transformers"
                    ),
                    "trust_remote_code": True,  # Required for all-mpnet-base-v2
                }

                self._model = SentenceTransformer(
                    self.config.model_name, **model_kwargs
                )

                # Configure all-mpnet-base-v2 settings
                if hasattr(self._model, "max_seq_length"):
                    self._model.max_seq_length = self.config.max_sequence_length

                # Enable fp16 for speed if supported and requested
                if self.config.use_fp16 and self._device in ["cuda", "mps"]:
                    try:
                        if hasattr(self._model, "half"):
                            self._model.half()
                            logger.info(
                                "fp16 acceleration enabled for all-mpnet-base-v2"
                            )
                    except Exception as e:
                        logger.warning(f"Could not enable fp16: {e}")

                # Get embedding dimension
                self._embedding_dim = self._model.get_sentence_embedding_dimension()

                self._load_time = time.time() - load_start
                logger.info(
                    f"all-mpnet-base-v2 loaded successfully in {self._load_time:.1f}s (device: {self._device}, dim: {self._embedding_dim})"
                )

                return self._model

            except Exception as e:
                logger.warning(
                    f"Failed to load all-mpnet-base-v2 {self.config.model_name}: {e}"
                )

                # Try fallback model
                if self.config.fallback_model != self.config.model_name:
                    logger.info(
                        f"Attempting fallback model: {self.config.fallback_model}"
                    )
                    try:
                        self._model = SentenceTransformer(
                            self.config.fallback_model,
                            device=self._device,
                            cache_folder=os.path.expanduser(
                                "~/.cache/sentence_transformers"
                            ),
                        )

                        if hasattr(self._model, "max_seq_length"):
                            self._model.max_seq_length = self.config.max_sequence_length

                        self._embedding_dim = (
                            self._model.get_sentence_embedding_dimension()
                        )
                        self._load_time = time.time() - load_start

                        logger.info(
                            f"Fallback model loaded in {self._load_time:.1f}s (dim: {self._embedding_dim})"
                        )
                        return self._model

                    except Exception as fallback_error:
                        logger.error(f"Fallback model also failed: {fallback_error}")

                raise RuntimeError(f"Could not load any embedding model: {e}")

    async def _check_and_cleanup_memory(self) -> None:
        """Check memory usage and cleanup if necessary"""
        try:
            memory_percent = self._process.memory_percent()
            if memory_percent > self.config.memory_cleanup_threshold * 100:
                logger.warning(f"High memory usage detected: {memory_percent:.1f}%")
                self._cleanup_memory()
                self._memory_cleanup_count += 1
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")

    def _cleanup_memory(self) -> None:
        """Aggressive memory cleanup for MacBook"""
        try:
            # Clear PyTorch cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                try:
                    torch.mps.empty_cache()
                except Exception:
                    pass

            # Force garbage collection
            for _ in range(3):
                gc.collect()()

        except Exception as e:
            logger.debug(f"Memory cleanup warning: {e}")

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension"""
        if self._embedding_dim is None:
            # all-mpnet-base-v2 produces 1024-dimensional embeddings
            if "all-mpnet-base-v2" in self.config.model_name.lower():
                return 768
            else:
                # Trigger model loading to get actual dimension
                self._get_model()
        return self._embedding_dim or 768

    @property
    def is_ready(self) -> bool:
        """Check if the model is loaded and ready"""
        return self._model is not None

    @property
    def performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_query_time = (
            (self._total_query_time / self._query_count) if self._query_count > 0 else 0
        )
        memory_mb = self._process.memory_info().rss / 1024 / 1024

        return {
            "model_name": self.config.model_name,
            "device": self._device,
            "embedding_dimension": self._embedding_dim,
            "model_load_time_seconds": self._load_time,
            "total_queries": self._query_count,
            "average_query_time_seconds": avg_query_time,
            "memory_usage_mb": memory_mb,
            "memory_cleanups": self._memory_cleanup_count,
            "fp16_enabled": self.config.use_fp16,
            "is_ready": self.is_ready,
        }

    async def warmup(self) -> Dict[str, Any]:
        """
        Warm up all-mpnet-base-v2 model with a test embedding.
        Call this during application startup.
        """
        logger.info("Warming up sentence-transformers/all-mpnet-base-v2 model...")
        start_time = time.time()

        try:
            # Test embedding
            test_embedding = await self.embed_query(
                "all-mpnet-base-v2 warmup test query for semantic search"
            )
            warmup_time = time.time() - start_time

            stats = {
                "warmup_successful": True,
                "warmup_time_seconds": warmup_time,
                "test_embedding_dim": len(test_embedding),
                **self.performance_stats,
            }

            logger.info(f"all-mpnet-base-v2 warmup complete in {warmup_time:.2f}s")
            return stats

        except Exception as e:
            logger.error(f"all-mpnet-base-v2 warmup failed: {e}")
            return {
                "warmup_successful": False,
                "error": str(e),
                "warmup_time_seconds": time.time() - start_time,
            }

    def __del__(self):
        """Cleanup thread pool on deletion"""
        if hasattr(self, "_thread_pool"):
            self._thread_pool.shutdown(wait=False)


# Global instance (initialized in dependencies.py)
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the global all-mpnet-base-v2 embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def embed_query_async(text: str) -> List[float]:
    """Convenience function for async query embedding"""
    service = get_embedding_service()
    return await service.embed_query(text)


async def embed_batch_async(texts: List[str]) -> List[List[float]]:
    """Convenience function for async batch embedding"""
    service = get_embedding_service()
    return await service.embed_batch(texts)
