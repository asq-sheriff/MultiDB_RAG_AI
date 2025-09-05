"""Unified Knowledge Service with Atlas Vector Search & Backward Compatibility"""

from __future__ import annotations

import logging
import math
import os
import re  # ADDED: Required for regex search fallback
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable, Iterable

from .confidence_evaluator import ConfidenceEvaluator

# FIXED: Import the getter function instead of the global variable
try:
    from data_layer.connections.mongo_connection import get_mongo_manager

    ENHANCED_MONGO_AVAILABLE = True
except ImportError:
    ENHANCED_MONGO_AVAILABLE = False

    def get_mongo_manager():
        raise RuntimeError("MongoDB manager not available")


from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId

# Optional acceleration
try:
    import numpy as _np

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

logger = logging.getLogger(__name__)

_ENABLE_SYNTHETIC_QUERY_EMBEDS = os.getenv("RAG_SYNTHETIC_QUERY_EMBEDDINGS", "0") == "1"
_SYNTHETIC_DIM = int(os.getenv("RAG_SYNTHETIC_DIM", "32"))

TelemetryFn = Callable[[str, Dict[str, Any]], None]
AsyncQueryEmbedder = Callable[[str], Awaitable[List[float]]]


@dataclass
class SearchConfig:
    """Enhanced search configuration with cascading confidence-based strategy"""

    # Cascading search thresholds
    high_confidence_threshold: float = float(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "0.85"))
    medium_confidence_threshold: float = float(os.getenv("MEDIUM_CONFIDENCE_THRESHOLD", "0.4"))
    
    # Healthcare-specific confidence levels
    medical_term_confidence: float = float(os.getenv("MEDICAL_TERM_CONFIDENCE", "0.9"))
    therapeutic_confidence: float = float(os.getenv("THERAPEUTIC_CONFIDENCE", "0.7"))
    
    # Search strategy control
    enable_confidence_cascading: bool = (
        os.getenv("ENABLE_CONFIDENCE_CASCADING", "true") == "true"
    )
    
    # Fallback configuration
    enable_exact_search_fallback: bool = (
        os.getenv("ENABLE_EXACT_SEARCH_FALLBACK", "true") == "true"
    )
    enable_semantic_search_fallback: bool = (
        os.getenv("ENABLE_SEMANTIC_SEARCH_FALLBACK", "true") == "true"
    )

    # Quality thresholds
    min_exact_results: int = int(os.getenv("MIN_EXACT_RESULTS", "1"))
    min_semantic_score: float = float(os.getenv("MIN_SEMANTIC_SCORE", "0.3"))

    # Performance tuning
    candidate_multiplier_default: int = int(os.getenv("CANDIDATE_MULTIPLIER", "8"))
    candidate_multiplier_fallback: int = int(
        os.getenv("CANDIDATE_MULTIPLIER_FALLBACK", "12")
    )
    max_fallback_attempts: int = int(os.getenv("MAX_FALLBACK_ATTEMPTS", "2"))

    # RAG optimization
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "10"))
    rag_max_snippets: int = int(os.getenv("RAG_MAX_SNIPPETS", "5"))
    rag_diversity_threshold: float = float(os.getenv("RAG_DIVERSITY_THRESHOLD", "0.85"))


def _cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    """Cosine similarity calculation with NumPy acceleration"""
    if _HAS_NUMPY:
        try:
            va = _np.asarray(a, dtype=_np.float32)
            vb = _np.asarray(b, dtype=_np.float32)
            denom = _np.linalg.norm(va) * _np.linalg.norm(vb)
            if denom == 0:
                return 0.0
            return float(_np.dot(va, vb) / denom)
        except Exception:
            pass

    # Pure Python fallback
    dot = sum(xa * xb for xa, xb in zip(a, b))
    norm_a = math.sqrt(sum(xa * xa for xa in a))
    norm_b = math.sqrt(sum(xb * xb for xb in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# Alias for backward compatibility
_cosine = _cosine_similarity


def _classify_query(query: str) -> str:
    """Enhanced query classification with improved heuristics"""
    q = (query or "").strip().lower()
    if not q:
        return "hybrid"

    tokens = q.split()

    # Force semantic search for schedule/routine queries
    schedule_keywords = ["schedule", "routine", "today", "tomorrow", "activity", "activities", "appointment", "appointments", "plan", "plans"]
    if any(keyword in q for keyword in schedule_keywords):
        return "semantic"

    # Exact search indicators
    exact_indicators = [
        len(tokens) <= 3,  # Short queries
        q.startswith('"') and q.endswith('"'),  # Quoted
        any(keyword in q for keyword in ["exact:", "id:", "code:", "key:", "faq"]),
        any(char in q for char in ["#", "_", "-"] if len(q) < 20),  # ID-like patterns
    ]

    if any(exact_indicators):
        return "exact"

    # Semantic search indicators
    semantic_indicators = [
        len(tokens) > 8,  # Long descriptive queries
        any(
            word in q
            for word in ["how", "what", "why", "explain", "describe", "tell me"]
        ),
        any(word in q for word in ["similar", "like", "related", "about", "regarding"]),
    ]

    if any(semantic_indicators):
        return "semantic"

    return "hybrid"


# Backward compatibility alias
classify_query = _classify_query


def _assess_search_quality(results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Assess search result quality with enhanced metrics"""
    if not results:
        return {
            "quality_assessment": "no_results",
            "confidence": 0.0,
            "recommendations": ["try_broader_terms", "check_spelling"],
        }

    # Calculate quality metrics
    scores = [r.get("score", 0.0) for r in results]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores) if scores else 0.0
    score_variance = (
        sum((s - avg_score) ** 2 for s in scores) / len(scores)
        if len(scores) > 1
        else 0.0
    )

    # Diversity assessment
    unique_sources = len(set(r.get("source", "") for r in results))
    unique_types = len(set(r.get("type", "") for r in results))

    # Content quality assessment
    content_lengths = [len(r.get("content", r.get("text_content", r.get("answer", "")))) for r in results if r.get("content") or r.get("text_content") or r.get("answer")]
    avg_content_length = (
        sum(content_lengths) / len(content_lengths) if content_lengths else 0
    )

    # Overall quality assessment
    if max_score > 0.9 and avg_score > 0.7:
        quality = "excellent"
        confidence = 0.95
    elif max_score > 0.7 and avg_score > 0.5:
        quality = "good"
        confidence = 0.8
    elif max_score > 0.5 and avg_score > 0.3:
        quality = "fair"
        confidence = 0.6
    else:
        quality = "poor"
        confidence = 0.3

    recommendations = []
    if avg_score < 0.5:
        recommendations.append("consider_fallback_search")
    if unique_sources < 2:
        recommendations.append("diversify_sources")
    if avg_content_length < 50:
        recommendations.append("expand_content")

    return {
        "quality_assessment": quality,
        "confidence": confidence,
        "avg_score": avg_score,
        "max_score": max_score,
        "score_variance": score_variance,
        "result_count": len(results),
        "unique_sources": unique_sources,
        "unique_types": unique_types,
        "avg_content_length": avg_content_length,
        "recommendations": recommendations,
    }


def _synthetic_embedding(text: str, dim: int = 32) -> List[float]:
    """Deterministic synthetic embedding for testing (backward compatibility)"""
    h = hashlib.sha256((text or "").encode("utf-8")).digest()
    vec = [((h[i % len(h)] / 255.0) - 0.5) for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _now_iso() -> str:
    """ISO timestamp helper"""
    return datetime.utcnow().isoformat() + "Z"


def _normalize_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize MongoDB ObjectId to string"""
    d = dict(doc)
    if "_id" in d and isinstance(d["_id"], ObjectId):
        d["_id"] = str(d["_id"])
    return d


def _apply_filters(
    base_query: Dict[str, Any], filters: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Apply additional filters to MongoDB query"""
    if not filters:
        return base_query
    
    # Skip user_context as it's used for post-processing, not direct MongoDB filtering
    for k, v in filters.items():
        if k != "user_context":
            base_query[k] = v
    return base_query


# -----------------------------------------------------------------------------
# Unified Knowledge Service
# -----------------------------------------------------------------------------


class KnowledgeService:
    """Unified Knowledge Service with Atlas Vector Search and backward compatibility."""

    def __init__(
        self,
        scylla_exact_search_fn: Optional[
            Callable[[str, int], Awaitable[List[Dict[str, Any]]]]
        ] = None,
        telemetry_cb: Optional[TelemetryFn] = None,
        query_embedder: Optional[AsyncQueryEmbedder] = None,
        search_config: Optional[SearchConfig] = None,
    ) -> None:
        """
        Initialize Unified KnowledgeService.

        Args:
            scylla_exact_search_fn: async function(query, top_k) -> List[Dict]
            telemetry_cb: function(kind, fields) -> None
            query_embedder: async function(query) -> List[float]
            search_config: Enhanced search configuration
        """
        self.scylla_search = scylla_exact_search_fn
        self.telemetry = telemetry_cb or (lambda kind, fields: None)
        self.query_embedder = query_embedder
        self.config = search_config or SearchConfig()
        self.confidence_evaluator = ConfidenceEvaluator()

        # Legacy property names for backward compatibility
        self._scylla_search = scylla_exact_search_fn
        self._telemetry = self.telemetry
        self._query_embedder = query_embedder

        logger.info("Unified KnowledgeService initialized")
        logger.info(f"  Enhanced MongoDB available: {ENHANCED_MONGO_AVAILABLE}")

        # FIXED: Check vector search availability at runtime, not init time
        # We'll check this when we actually need it
        logger.info("  Atlas Vector Search available: Will check at runtime")

    def _get_mongo_manager(self):
        """Get the MongoDB manager instance - FIXED to use the getter function"""
        try:
            return get_mongo_manager()
        except RuntimeError as e:
            logger.error(f"MongoDB manager not initialized: {e}")
            raise

    async def search_router(
        self,
        query: str,
        top_k: int = 5,
        route: str = "auto",
        filters: Optional[Dict[str, Any]] = None,
        search_kb: bool = True,
        search_docs: bool = True,
        candidate_multiplier: int = 8,
    ) -> Dict[str, Any]:
        """
        Unified search router with Atlas Vector Search and fallback mechanisms.

        Returns:
            {
                "route": "exact|semantic|hybrid|auto->chosen",
                "query": "...",
                "results": [...],
                "meta": {...},
                "search_quality": {...},  # Enhanced feature
                "fallback_applied": bool  # Enhanced feature
            }
        """
        start_time = time.time()
        start_ts = _now_iso()
        decided_route = route

        # Handle "vector" route as "semantic" for backward compatibility
        if route == "vector":
            decided_route = "semantic"
        elif route == "auto":
            decided_route = _classify_query(query)

        logger.info(
            f"Search router: query='{query}', route={route}->{decided_route}, filters={filters}"
        )

        self.telemetry(
            "unified_search_begin",
            {
                "route": route,
                "decided_route": decided_route,
                "query_length": len(query),
                "top_k": top_k,
                "enhanced_features": ENHANCED_MONGO_AVAILABLE,
            },
        )

        results: List[Dict[str, Any]] = []
        fallback_applied = False
        meta = {
            "start": start_ts,
            "start_time": start_time,
            "decided_route": decided_route,
            "atlas_used": False,
            "fallback_attempts": 0,
        }

        # Store query embedding for semantic conversation memory
        query_embedding = None
        stored_query_id = None
        
        try:
            if self.query_embedder and decided_route in ("semantic", "hybrid"):
                query_embedding = await self.query_embedder(query)
                
                # Store query embedding if user context is available
                user_id = filters.get('user_id') if filters else None
                session_id = filters.get('session_id') if filters else None
                
                if user_id and session_id and query_embedding:
                    try:
                        from ai_services.core.semantic_conversation_search import semantic_conversation_search
                        stored_query_id = await semantic_conversation_search.store_query_embedding(
                            user_id=user_id,
                            session_id=session_id,
                            query_text=query,
                            query_embedding=query_embedding,
                            conversation_turn=filters.get('conversation_turn'),
                            followup_to_query_id=filters.get('followup_to_query_id')
                        )
                        logger.debug(f"Stored query embedding: {stored_query_id}")
                    except Exception as e:
                        logger.warning(f"Failed to store query embedding: {e}")
        
        except Exception as e:
            logger.warning(f"Query embedding generation failed: {e}")

        try:
            # Confidence-based cascading search strategy
            if self.config.enable_confidence_cascading and decided_route in ("auto", "hybrid"):
                results, search_strategy_used = await self._execute_cascading_search(
                    query, top_k, search_docs, search_kb, candidate_multiplier, filters
                )
                meta["search_strategy"] = search_strategy_used
            else:
                # Legacy routing for backward compatibility
                if decided_route == "exact":
                    results = await self._execute_exact_search(
                        query, top_k, search_kb, filters
                    )

                    # Apply exact search fallback if enabled and results are poor
                    if (
                        self.config.enable_exact_search_fallback
                        and len(results) < self.config.min_exact_results
                    ):
                        logger.info(f"Applying exact search fallback for query: {query}")
                        fallback_results = await self._execute_semantic_search(
                            query,
                            top_k,
                            search_docs,
                            search_kb,
                            candidate_multiplier,
                            filters,
                        )
                        results.extend(fallback_results)
                        fallback_applied = True
                        meta["fallback_attempts"] += 1

                elif decided_route in ("semantic", "hybrid"):
                    results = await self._execute_semantic_search(
                        query, top_k, search_docs, search_kb, candidate_multiplier, filters
                    )

                    # Apply semantic search fallback if enabled and results are poor
                    if (
                        self.config.enable_semantic_search_fallback
                        and self._should_apply_semantic_fallback(results)
                    ):
                        logger.info(f"Applying semantic search fallback for query: {query}")
                        fallback_results = await self._execute_exact_search(
                            query, top_k, search_kb, filters
                        )
                        results.extend(fallback_results)
                        fallback_applied = True
                        meta["fallback_attempts"] += 1

                else:
                    # Default fallback
                    results = await self._execute_semantic_search(
                        query, top_k, search_docs, search_kb, candidate_multiplier, filters
                    )

            # Advanced re-ranking with variance reduction and semantic enhancement
            results, ranking_analysis = await self._advanced_rerank_results(query, results, top_k)

            logger.debug(f"Search router returning {len(results)} results after advanced ranking")
            logger.debug(f"Ranking analysis: variance reduction {ranking_analysis.variance_reduction:.4f}")

            # Enhanced search quality assessment with ranking insights
            search_quality = _assess_search_quality(results, query)
            search_quality.update({
                'ranking_analysis': {
                    'original_variance': ranking_analysis.original_variance,
                    'final_variance': ranking_analysis.final_variance,
                    'variance_reduction': ranking_analysis.variance_reduction,
                    'strategy_used': ranking_analysis.ranking_strategy_used,
                    'quality_improvement': ranking_analysis.quality_improvement
                }
            })

        except Exception as e:
            logger.exception(f"Unified search failed: {e}")
            meta["error"] = str(e)
            search_quality = {"quality_assessment": "error", "confidence": 0.0}

        # Final metadata
        meta.update(
            {
                "end": _now_iso(),
                "end_time": time.time(),
                "total_time_seconds": time.time() - start_time,
                "result_count": len(results),
            }
        )

        self.telemetry(
            "unified_search_complete",
            {
                "route": f"{route}->{decided_route}",
                "result_count": len(results),
                "fallback_applied": fallback_applied,
                "search_quality": search_quality.get("quality_assessment"),
                "total_time": meta["total_time_seconds"],
            },
        )

        # Update stored query embedding with search metrics
        if stored_query_id and query_embedding:
            try:
                # Calculate average similarity score
                avg_score = None
                if results:
                    scores = [r.get('score', 0) for r in results if 'score' in r]
                    avg_score = sum(scores) / len(scores) if scores else None
                
                search_metrics = {
                    'results_count': len(results),
                    'avg_score': avg_score,
                    'route': f"{route}->{decided_route}",
                    'quality_score': search_quality.get("confidence", 0.0),
                    'processing_time_ms': int(meta["total_time_seconds"] * 1000)
                }
                
                # Update the stored query embedding with search results
                from ai_services.core.semantic_conversation_search import semantic_conversation_search
                await semantic_conversation_search._update_query_metrics(
                    stored_query_id, search_metrics
                )
                
            except Exception as e:
                logger.warning(f"Failed to update query embedding metrics: {e}")

        # Apply user-specific filtering for personalized queries
        if filters and "user_context" in filters:
            user_context = filters["user_context"]
            user_name = user_context.get("user_name")
            user_role = user_context.get("user_role")
            
            logger.info(f"Applying user-specific filtering for {user_name} ({user_role})")
            
            # For personal queries, filter results to match the specific user
            personal_keywords = ["schedule", "my", "today", "routine", "activities", "tasks", "responsibilities"]
            is_personal_query = any(keyword in query.lower() for keyword in personal_keywords)
            
            logger.info(f"Personal query check: '{query}' -> {is_personal_query}")
            
            if is_personal_query and user_name:
                logger.info(f"Starting filtering for {user_name}: {len(results)} initial results")
                filtered_results = []
                for i, result in enumerate(results):
                    content = result.get("content", "").lower()
                    # Create comprehensive user indicators for matching
                    user_indicators = [user_name.lower()]
                    
                    # Add name variations based on role
                    if user_role == "care_physician":
                        # Handle "Dr. James Chen" variations
                        name_parts = user_name.lower().split()
                        if len(name_parts) >= 2:
                            first_name, last_name = name_parts[0], name_parts[-1]
                            user_indicators.extend([
                                f"dr. {first_name} {last_name}",
                                f"dr {first_name} {last_name}",
                                f"dr. {last_name}",
                                f"dr {last_name}",
                                f"{first_name} {last_name}, md",
                                "care physician"
                            ])
                    elif user_role == "care_staff":
                        # Handle "Maria Rodriguez, RN" variations
                        name_parts = user_name.lower().split()
                        if len(name_parts) >= 2:
                            first_name, last_name = name_parts[0], name_parts[-1]
                            user_indicators.extend([
                                f"{first_name} {last_name}, rn",
                                f"{last_name}, rn",
                                "care staff"
                            ])
                    elif user_role == "administrator":
                        user_indicators.extend(["administrator", "administrative"])
                    elif user_role == "resident":
                        # Add room number indicators
                        user_indicators.extend(["room 215", "resident"])
                        
                    # Check if content matches any user indicator
                    matches = [indicator for indicator in user_indicators if indicator.strip() and indicator in content]
                    matches_user = bool(matches)
                    
                    if i < 3:  # Only log first 3 for debugging
                        logger.info(f"  Result {i+1} ({result.get('document_id', 'no-id')[:8]}...): matches={matches}")
                    
                    if matches_user:
                        filtered_results.append(result)
                
                if filtered_results:
                    # Boost scores for user-specific documents to prioritize them
                    for result in filtered_results:
                        original_score = result.get("score", 0.0)
                        result["score"] = original_score + 100  # Significant boost for user-specific content
                        result["user_specific"] = True
                    
                    logger.info(f"User-specific filtering: {len(results)} -> {len(filtered_results)} results for {user_name}")
                    results = filtered_results
                else:
                    logger.warning(f"User-specific filtering found no relevant results for {user_name}, keeping original results")

        return {
            "route": f"{route}->{decided_route}",
            "query": query,
            "results": results,
            "meta": meta,
            "search_quality": search_quality,
            "fallback_applied": fallback_applied,
            "stored_query_id": stored_query_id,  # Include for conversation linking
        }

    # Enhanced search execution methods
    async def _execute_exact_search(
        self,
        query: str,
        top_k: int,
        search_kb: bool,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute exact search via ScyllaDB or text search fallback"""

        if self.scylla_search and search_kb:
            try:
                self.telemetry("search_begin", {"backend": "scylla", "route": "exact"})
                results = await self.scylla_search(query, top_k)
                self.telemetry(
                    "search_end", {"backend": "scylla", "count": len(results)}
                )
                return results
            except Exception as e:
                logger.warning(f"ScyllaDB exact search failed: {e}")

        # Fallback to MongoDB text search
        self.telemetry("search_begin", {"backend": "mongo.kv_text", "route": "exact"})
        results = await self.mongo_text_search_kv(query, top_k=top_k, filters=filters)
        self.telemetry(
            "search_end", {"backend": "mongo.kv_text", "count": len(results)}
        )
        return results

    async def _execute_semantic_search(
        self,
        query: str,
        top_k: int,
        search_docs: bool,
        search_kb: bool,
        candidate_multiplier: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute semantic search with Atlas Vector Search or hybrid fallback"""

        results = []

        # FIXED: Get mongo manager at runtime
        mongo_manager = self._get_mongo_manager()

        # Try Atlas Vector Search first if available
        if ENHANCED_MONGO_AVAILABLE and mongo_manager.vector_search_available:
            try:
                if search_docs:
                    doc_results = await self._atlas_vector_search_embeddings(
                        query, top_k, candidate_multiplier
                    )
                    results.extend(doc_results)

                if search_kb:
                    kb_results = await self._atlas_vector_search_knowledge_vectors(
                        query, top_k, candidate_multiplier
                    )
                    results.extend(kb_results)

                if results:
                    return sorted(
                        results, key=lambda r: r.get("score", 0.0), reverse=True
                    )[:top_k]

            except Exception as e:
                logger.warning(
                    f"Atlas Vector Search failed, falling back to hybrid: {e}"
                )

        # Fallback to hybrid search (original implementation)
        if search_docs:
            self.telemetry("search_begin", {"backend": "mongo.emb.hybrid"})
            doc_results = await self.mongo_hybrid_search_embeddings(
                query,
                top_k=top_k,
                filters=filters,
                candidate_multiplier=candidate_multiplier,
            )
            self.telemetry(
                "search_end", {"backend": "mongo.emb.hybrid", "count": len(doc_results)}
            )
            results.extend(doc_results)

        if search_kb:
            self.telemetry("search_begin", {"backend": "mongo.kv.hybrid"})
            kb_results = await self.mongo_hybrid_search_kv(
                query,
                top_k=top_k,
                filters=filters,
                candidate_multiplier=candidate_multiplier,
            )
            self.telemetry(
                "search_end", {"backend": "mongo.kv.hybrid", "count": len(kb_results)}
            )
            results.extend(kb_results)

        return sorted(results, key=lambda r: r.get("score", 0.0), reverse=True)[:top_k]

    # Atlas Vector Search methods (enhanced features)
    async def _atlas_vector_search_embeddings(
        self, query: str, top_k: int, candidate_multiplier: int
    ) -> List[Dict[str, Any]]:
        """Execute Atlas Vector Search on embeddings collection"""

        if not self.query_embedder:
            raise RuntimeError("Query embedder required for Atlas Vector Search")

        query_vector = await self.query_embedder(query)

        # FIXED: Get mongo manager and then get collection
        mongo_manager = self._get_mongo_manager()
        collection = mongo_manager.embeddings()

        # Atlas Vector Search pipeline - FIXED: Added "path" field
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_idx_embeddings_embedding",
                    "path": "embedding",  # FIXED: Added required path field
                    "queryVector": query_vector,
                    "numCandidates": min(top_k * candidate_multiplier, 1000),
                    "limit": top_k,
                }
            },
            {
                "$project": {
                    "title": 1,
                    "text_content": 1,
                    "content": 1,
                    "document_id": 1,
                    "chunk_index": 1,
                    "category": 1,
                    "tags": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        cursor = collection.aggregate(pipeline)
        docs = await cursor.to_list(length=top_k)

        results = []
        for doc in docs:
            results.append(
                {
                    "type": "document",
                    "source": "atlas_vector_search",
                    "id": str(doc["_id"]),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                    "document_id": str(doc.get("document_id", "")),
                    "chunk_index": doc.get("chunk_index", 0),
                    "category": doc.get("category", ""),
                    "tags": doc.get("tags", []),
                    "score": float(doc.get("score", 0.0)),
                    "metric": "atlas_vector_score",
                }
            )

        return results

    async def _atlas_vector_search_knowledge_vectors(
        self, query: str, top_k: int, candidate_multiplier: int
    ) -> List[Dict[str, Any]]:
        """Execute Atlas Vector Search on knowledge_vectors collection"""

        if not self.query_embedder:
            raise RuntimeError("Query embedder required for Atlas Vector Search")

        query_vector = await self.query_embedder(query)

        # FIXED: Get mongo manager and then get collection
        mongo_manager = self._get_mongo_manager()
        collection = mongo_manager.knowledge_vectors()

        # Atlas Vector Search pipeline - FIXED: Added "path" field
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_idx_knowledge_vectors_embedding",
                    "path": "embedding",  # FIXED: Added required path field
                    "queryVector": query_vector,
                    "numCandidates": min(top_k * candidate_multiplier, 1000),
                    "limit": top_k,
                }
            },
            {
                "$project": {
                    "question": 1,
                    "answer": 1,
                    "scylla_key": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        cursor = collection.aggregate(pipeline)
        docs = await cursor.to_list(length=top_k)

        results = []
        for doc in docs:
            results.append(
                {
                    "type": "faq",
                    "source": "atlas_vector_search",
                    "id": str(doc["_id"]),
                    "scylla_key": doc.get("scylla_key", ""),
                    "question": doc.get("question", ""),
                    "answer": doc.get("answer", ""),
                    "score": float(doc.get("score", 0.0)),
                    "metric": "atlas_vector_score",
                }
            )

        return results

    # Original MongoDB methods (backward compatibility) - FIXED versions
    async def mongo_text_search_embeddings(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """$text search on `embeddings` with textScore sort (backward compatibility) - FIXED"""
        # FIXED: Get mongo manager and then get collection
        mongo_manager = self._get_mongo_manager()
        coll: AsyncIOMotorCollection = mongo_manager.embeddings()

        out: List[Dict[str, Any]] = []

        try:
            # First, check if ANY documents exist in the collection
            doc_count = await coll.count_documents({})
            logger.info(f"Total documents in embeddings collection: {doc_count}")

            if doc_count == 0:
                logger.warning("No documents in embeddings collection!")
                return []

            # Try text search first
            q = _apply_filters({"$text": {"$search": query}}, filters)
            proj = projection or {
                "title": 1,
                "text_content": 1,  # MongoDB stores content in text_content field
                "content": 1,       # Keep for backward compatibility
                "embedding": 1,
                "document_id": 1,
                "chunk_index": 1,
                "category": 1,
                "tags": 1,
                "source": 1,
                "score": {"$meta": "textScore"},
            }
            cursor = (
                coll.find(q, proj)
                .sort([("score", {"$meta": "textScore"})])
                .limit(top_k)
            )
            docs = await cursor.to_list(length=top_k)

            if docs:
                logger.info(f"Text search found {len(docs)} documents")

            for d in docs:
                d = _normalize_id(d)
                out.append(
                    {
                        "type": "document",
                        "source": "mongo.embeddings",
                        "id": d["_id"],
                        "title": d.get("title"),
                        "content": d.get("text_content") or d.get("content"),
                        "document_id": str(d.get("document_id"))
                        if d.get("document_id")
                        else None,
                        "chunk_index": d.get("chunk_index"),
                        "category": d.get("category"),
                        "tags": d.get("tags", []),
                        "score": float(d.get("score", 0.0)),
                        "metric": "textScore",
                    }
                )

        except Exception as e:
            # If text search fails (e.g., no text index), fall back to regular query
            logger.warning(f"Text search failed, falling back to regular query: {e}")

            # Build a fallback query
            fallback_query = {}
            if filters:
                fallback_query.update(filters)

            # Create a more permissive regex search
            if query:
                # Split query into words and search for any of them
                query_words = query.lower().split()
                or_conditions = []

                for word in query_words:
                    # Escape special regex characters
                    escaped_word = re.escape(word)
                    or_conditions.extend(
                        [
                            {"content": {"$regex": escaped_word, "$options": "i"}},
                            {"title": {"$regex": escaped_word, "$options": "i"}},
                        ]
                    )

                if or_conditions:
                    fallback_query["$or"] = or_conditions

            # If no query provided, just get any documents
            if not fallback_query:
                fallback_query = {"content": {"$exists": True}}

            proj = projection or {
                "title": 1,
                "text_content": 1,
                "content": 1,
                "embedding": 1,
                "document_id": 1,
                "chunk_index": 1,
                "category": 1,
                "tags": 1,
                "source": 1,
            }

            logger.info(f"Fallback query: {fallback_query}")
            cursor = coll.find(fallback_query, proj).limit(top_k)
            docs = await cursor.to_list(length=top_k)

            logger.info(f"Fallback search found {len(docs)} documents")

            for d in docs:
                d = _normalize_id(d)
                # Calculate a simple relevance score based on keyword matches
                content = (d.get("content", "") + " " + d.get("title", "")).lower()
                query_lower = query.lower() if query else ""

                # Count matches for all query words
                score = 0.0
                if query_lower:
                    query_words = query_lower.split()
                    for word in query_words:
                        score += content.count(word) / max(len(content.split()), 1)
                    score = score / max(
                        len(query_words), 1
                    )  # Normalize by number of query words
                else:
                    score = 0.5  # Default score when no query

                out.append(
                    {
                        "type": "document",
                        "source": "mongo.embeddings",
                        "id": d["_id"],
                        "title": d.get("title"),
                        "content": d.get("text_content") or d.get("content"),
                        "document_id": str(d.get("document_id"))
                        if d.get("document_id")
                        else None,
                        "chunk_index": d.get("chunk_index"),
                        "category": d.get("category"),
                        "tags": d.get("tags", []),
                        "score": float(score),
                        "metric": "regex_match",
                    }
                )

        return out

    async def mongo_text_search_kv(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """$text search on `knowledge_vectors` (backward compatibility)"""
        # FIXED: Get mongo manager and then get collection
        mongo_manager = self._get_mongo_manager()
        coll: AsyncIOMotorCollection = mongo_manager.knowledge_vectors()

        q = _apply_filters({"$text": {"$search": query}}, filters)
        proj = projection or {
            "question": 1,
            "answer": 1,
            "embedding": 1,
            "scylla_key": 1,
            "score": {"$meta": "textScore"},
        }
        cursor = (
            coll.find(q, proj).sort([("score", {"$meta": "textScore"})]).limit(top_k)
        )
        docs = await cursor.to_list(length=top_k)

        out: List[Dict[str, Any]] = []
        for d in docs:
            d = _normalize_id(d)
            out.append(
                {
                    "type": "faq",
                    "source": "mongo.knowledge_vectors",
                    "id": d["_id"],
                    "scylla_key": d.get("scylla_key"),
                    "question": d.get("question"),
                    "answer": d.get("answer"),
                    "score": float(d.get("score", 0.0)),
                    "metric": "textScore",
                }
            )
        return out

    async def mongo_hybrid_search_embeddings(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        candidate_multiplier: int = 8,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Hybrid search: text candidates + cosine re-ranking (backward compatibility) - FIXED"""

        # First try text search
        candidates = await self.mongo_text_search_embeddings(
            query,
            top_k=max(top_k * max(1, candidate_multiplier), top_k),
            filters=filters,
            projection={
                "title": 1,
                "text_content": 1,
                "content": 1,
                "embedding": 1,
                "document_id": 1,
                "chunk_index": 1,
                "category": 1,
                "tags": 1,
                "source": 1,
                "score": {"$meta": "textScore"},
            },
        )

        # If no text search results, try a broader approach
        if not candidates:
            logger.info(
                f"No text search results for query '{query}', trying broader retrieval"
            )
            mongo_manager = self._get_mongo_manager()
            coll = mongo_manager.embeddings()

            # Get ANY documents that have embeddings
            simple_query = filters or {}
            simple_query["embedding"] = {
                "$exists": True,
                "$ne": None,
                "$not": {"$size": 0},
            }

            # Also ensure content exists
            simple_query["content"] = {"$exists": True, "$nin": [None, ""]}

            # Log the query for debugging
            logger.info(f"Broader retrieval query: {simple_query}")

            # Get more documents for broader search
            broader_limit = min(top_k * candidate_multiplier * 2, 100)
            cursor = coll.find(simple_query).limit(broader_limit)
            docs = await cursor.to_list(length=broader_limit)

            logger.info(
                f"Broader retrieval found {len(docs)} documents with embeddings"
            )

            candidates = []
            for d in docs:
                d = _normalize_id(d)

                # Do a simple keyword match to pre-filter
                content = (d.get("content", "") + " " + d.get("title", "")).lower()
                query_lower = query.lower() if query else ""

                # Check if any query word appears in content
                has_match = False
                if query_lower:
                    for word in query_lower.split():
                        if word in content:
                            has_match = True
                            break
                else:
                    has_match = True  # Include all if no query

                # Only include documents that have some relevance
                if has_match or len(candidates) < top_k:
                    candidates.append(
                        {
                            "type": "document",
                            "source": "mongo.embeddings",
                            "id": d["_id"],
                            "title": d.get("title"),
                            "content": d.get("text_content") or d.get("content"),
                            "document_id": str(d.get("document_id"))
                            if d.get("document_id")
                            else None,
                            "chunk_index": d.get("chunk_index"),
                            "category": d.get("category"),
                            "tags": d.get("tags", []),
                            "embedding": d.get("embedding"),
                            "score": 0.0,
                            "metric": "fallback",
                        }
                    )

            if not candidates:
                logger.warning("No documents found even with broader retrieval")
                return []

            logger.info(f"Using {len(candidates)} candidates for re-ranking")

        # Generate query embedding if not provided
        if query_embedding is None:
            query_embedding = await self._embed_query(query)

        # Re-rank candidates by cosine similarity
        re_ranked: List[Tuple[float, Dict[str, Any]]] = []

        for c in candidates:
            emb = c.get("embedding")
            if not emb or not isinstance(emb, list) or len(emb) == 0:
                logger.warning(f"Skipping document {c.get('id')} - no valid embedding (emb={type(emb)}, len={len(emb) if emb else 0})")
                continue

            # Ensure embedding dimensions match
            if len(emb) != len(query_embedding):
                logger.warning(
                    f"Skipping document {c.get('id')} - dimension mismatch: doc={len(emb)} vs query={len(query_embedding)}"
                )
                continue

            cos = _cosine_similarity(query_embedding, emb)
            item = dict(c)
            item["score"] = float(cos)
            item["metric"] = "cosine"
            # Remove embedding from final result to save space
            item.pop("embedding", None)
            re_ranked.append((cos, item))

        if not re_ranked:
            logger.warning("No documents could be re-ranked (no valid embeddings)")
            # Return the text search results without re-ranking
            for c in candidates[:top_k]:
                c.pop("embedding", None)
            return candidates[:top_k]

        re_ranked.sort(key=lambda x: x[0], reverse=True)
        results = [it for _, it in re_ranked[:top_k]]

        logger.info(f"Returning {len(results)} re-ranked results")
        return results

    async def mongo_hybrid_search_kv(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        candidate_multiplier: int = 8,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Hybrid search on knowledge_vectors (backward compatibility)"""
        # FIXED: Get mongo manager and then get collection
        mongo_manager = self._get_mongo_manager()
        coll: AsyncIOMotorCollection = mongo_manager.knowledge_vectors()

        q = _apply_filters({"$text": {"$search": query}}, filters)
        proj = {
            "question": 1,
            "answer": 1,
            "embedding": 1,
            "scylla_key": 1,
            "score": {"$meta": "textScore"},
        }

        candidate_n = max(top_k * max(1, candidate_multiplier), top_k)
        docs = (
            await coll.find(q, proj)
            .sort([("score", {"$meta": "textScore"})])
            .limit(candidate_n)
            .to_list(length=candidate_n)
        )
        if not docs:
            return []

        if query_embedding is None:
            query_embedding = await self._embed_query(query)

        re_ranked: List[Tuple[float, Dict[str, Any]]] = []
        for d in docs:
            d = _normalize_id(d)
            emb = d.get("embedding")
            if not emb:
                continue
            cos = _cosine_similarity(query_embedding, emb)
            re_ranked.append(
                (
                    cos,
                    {
                        "type": "faq",
                        "source": "mongo.knowledge_vectors",
                        "id": d["_id"],
                        "scylla_key": d.get("scylla_key"),
                        "question": d.get("question"),
                        "answer": d.get("answer"),
                        "score": float(cos),
                        "metric": "cosine",
                    },
                )
            )

        re_ranked.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in re_ranked[:top_k]]

    # Enhanced helper methods
    def _should_apply_semantic_fallback(self, results: List[Dict[str, Any]]) -> bool:
        """Determine if semantic search fallback should be applied"""
        if not results:
            return True

        scores = [r.get("score", 0.0) for r in results]
        avg_score = sum(scores) / len(scores)
        return avg_score < self.config.min_semantic_score

    def _deduplicate_and_rerank(
        self, results: List[Dict[str, Any]], top_k: int
    ) -> List[Dict[str, Any]]:
        """Remove duplicates and re-rank results"""
        seen_ids = set()
        seen_content = set()
        unique_results = []

        for result in sorted(results, key=lambda r: r.get("score", 0.0), reverse=True):
            # Check for ID duplicates
            result_id = result.get("id") or result.get("scylla_key", "")
            if result_id and result_id in seen_ids:
                continue

            # Check for content duplicates
            content = result.get("content", result.get("answer", ""))[:100]
            if content and content in seen_content:
                continue

            seen_ids.add(result_id)
            seen_content.add(content)
            unique_results.append(result)

            if len(unique_results) >= top_k:
                break

        return unique_results

    async def _advanced_rerank_results(
        self, query: str, results: List[Dict[str, Any]], top_k: int
    ) -> Tuple[List[Dict[str, Any]], Any]:
        """
        Advanced re-ranking with variance reduction and cross-encoder enhancement
        Replaces simple deduplication with sophisticated ranking
        """
        from ai_services.core.advanced_ranking_service import advanced_ranking_service, RankingStrategy
        
        try:
            # Initialize ranking service if needed
            if not advanced_ranking_service.initialized:
                await advanced_ranking_service.initialize()
            
            # First deduplicate to avoid ranking duplicates
            deduplicated_results = self._simple_deduplicate(results)
            
            # Apply advanced ranking
            ranked_results, ranking_analysis = await advanced_ranking_service.rank_results(
                query=query,
                results=deduplicated_results,
                strategy=RankingStrategy.ADAPTIVE,
                top_k=top_k
            )
            
            return ranked_results, ranking_analysis
            
        except Exception as e:
            logger.warning(f"Advanced re-ranking failed, using simple deduplication: {e}")
            
            # Fallback to simple deduplication
            simple_results = self._deduplicate_and_rerank(results, top_k)
            
            # Create minimal analysis for fallback
            from ai_services.core.advanced_ranking_service import RankingAnalysis
            fallback_analysis = RankingAnalysis(
                original_variance=0.0,
                final_variance=0.0,
                variance_reduction=0.0,
                score_distribution={},
                ranking_strategy_used="fallback_simple",
                quality_improvement=0.0,
                processing_time_ms=0
            )
            
            return simple_results, fallback_analysis

    def _simple_deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple deduplication without limiting results for ranking input"""
        seen_ids = set()
        seen_content = set()
        unique_results = []

        for result in results:
            result_id = result.get("id") or result.get("_id") or result.get("document_id")
            content = result.get("content", "")

            if result_id and result_id in seen_ids:
                continue
            if content and content in seen_content:
                continue

            seen_ids.add(result_id)
            seen_content.add(content)
            unique_results.append(result)

        return unique_results

    # Embedding hook (consolidated)
    async def _embed_query(self, query: str) -> List[float]:
        """
        Unified query embedding with fallback chain:
        1) Custom async query_embedder if provided
        2) Synthetic embeddings if enabled via env flag
        3) RuntimeError to force explicit configuration
        """
        # Custom hook provided?
        if self.query_embedder:
            vec = await self.query_embedder(query)
            if not isinstance(vec, list) or not all(
                isinstance(x, (int, float)) for x in vec
            ):
                raise TypeError("query_embedder must return List[float]")
            return [float(x) for x in vec]

        # Synthetic fallback for testing
        if _ENABLE_SYNTHETIC_QUERY_EMBEDS:
            return _synthetic_embedding(query, dim=_SYNTHETIC_DIM)

        raise RuntimeError(
            "No query embedding configured. Either:\n"
            "- Set RAG_SYNTHETIC_QUERY_EMBEDDINGS=1 (for temporary local testing), or\n"
            "- Inject a real async query embedder into KnowledgeService(query_embedder=...)."
        )

    async def _execute_cascading_search(
        self,
        query: str,
        top_k: int = 10,
        search_docs: bool = True,
        search_kb: bool = True,
        candidate_multiplier: int = 8,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Execute confidence-based cascading search strategy
        
        Returns: (results, strategy_used)
        """
        start_time = time.time()
        
        # Step 1: Fast text search
        logger.info(f"🔍 Starting cascading search for: '{query}'")
        text_start = time.time()
        
        text_results = []
        if search_docs:
            text_results.extend(
                await self.mongo_hybrid_search_embeddings(
                    query, top_k * 2, filters, candidate_multiplier=2
                )
            )
        if search_kb:
            text_results.extend(
                await self.mongo_hybrid_search_kv(
                    query, top_k * 2, filters=filters
                )
            )
        
        text_time = time.time() - text_start
        logger.info(f"⚡ Text search completed in {text_time*1000:.0f}ms, found {len(text_results)} results")
        
        # Step 2: Evaluate confidence
        confidence = self.confidence_evaluator.evaluate_text_results(query, text_results, top_k)
        search_strategy = self.confidence_evaluator.should_cascade_to_vector(confidence, self.config)
        
        logger.info(
            f"📊 Confidence analysis: overall={confidence.overall:.2f}, "
            f"text_match={confidence.text_match:.2f}, medical={confidence.medical_terms:.2f}, "
            f"therapeutic={confidence.therapeutic_context:.2f} → strategy={search_strategy}"
        )
        
        # Step 3: Execute strategy
        if search_strategy == "text_only":
            # High confidence - return text results immediately
            logger.info("✅ High confidence - using text search only")
            final_results = text_results[:top_k]
            total_time = time.time() - start_time
            logger.info(f"🚀 Cascading search completed in {total_time*1000:.0f}ms (text-only)")
            
        elif search_strategy == "hybrid":
            # Medium confidence - enhance with vector search
            logger.info("🔄 Medium confidence - enhancing with vector search")
            vector_start = time.time()
            
            # Get query embedding for semantic search
            query_embedding = await self._embed_query(query) if self.query_embedder else None
            
            # Perform vector search on documents with embeddings
            vector_results = await self._execute_semantic_search_with_embedding(
                query, query_embedding, top_k, search_docs, search_kb, 
                candidate_multiplier, filters
            )
            
            vector_time = time.time() - vector_start
            logger.info(f"🎯 Vector search completed in {vector_time*1000:.0f}ms, found {len(vector_results)} results")
            
            # Merge and deduplicate results
            final_results = self._merge_search_results(text_results, vector_results, top_k)
            total_time = time.time() - start_time
            logger.info(f"🚀 Cascading search completed in {total_time*1000:.0f}ms (hybrid)")
            
        else:  # vector_only
            # Low confidence - vector search only
            logger.info("🎯 Low confidence - using vector search only")
            query_embedding = await self._embed_query(query) if self.query_embedder else None
            
            final_results = await self._execute_semantic_search_with_embedding(
                query, query_embedding, top_k, search_docs, search_kb,
                candidate_multiplier, filters
            )
            total_time = time.time() - start_time
            logger.info(f"🚀 Cascading search completed in {total_time*1000:.0f}ms (vector-only)")
        
        # Add confidence metadata to results
        for result in final_results:
            result["confidence_score"] = confidence.overall
            result["search_strategy"] = search_strategy
        
        return final_results, search_strategy

    async def _execute_semantic_search_with_embedding(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        top_k: int,
        search_docs: bool,
        search_kb: bool,
        candidate_multiplier: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute semantic search with pre-computed query embedding"""
        results = []
        
        if search_docs:
            doc_results = await self.mongo_hybrid_search_embeddings(
                query, top_k * candidate_multiplier, filters, candidate_multiplier, query_embedding
            )
            results.extend(doc_results)
            
        if search_kb:
            kb_results = await self.mongo_hybrid_search_kv(
                query, top_k * candidate_multiplier, filters, candidate_multiplier, query_embedding
            )
            results.extend(kb_results)
        
        return results[:top_k]

    def _merge_search_results(
        self, 
        text_results: List[Dict[str, Any]], 
        vector_results: List[Dict[str, Any]], 
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate text and vector search results"""
        seen_ids = set()
        merged_results = []
        
        # Prioritize vector results (higher quality) but include high-scoring text results
        all_results = vector_results + text_results
        
        for result in all_results:
            result_id = result.get('id') or result.get('_id')
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                merged_results.append(result)
                
                if len(merged_results) >= top_k:
                    break
        
        # Sort by score if available
        if merged_results and 'score' in merged_results[0]:
            merged_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return merged_results[:top_k]


# Backward compatibility aliases
EnhancedKnowledgeService = KnowledgeService
