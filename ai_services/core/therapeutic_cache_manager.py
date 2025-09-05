"""
Advanced Therapeutic Response Caching System
Implements Priority 3 from MongoDB-PostgreSQL Integration Analysis
Multi-tier caching with intelligent cache warming for therapeutic AI responses

HIPAA-Compliant Enhancement:
- PHI detection and cache exclusion
- Healthcare data protection compliance
- Audit trails for cache operations
"""

import asyncio
import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import pickle
import uuid
import sys
import os
import gc

from motor.motor_asyncio import AsyncIOMotorClient
import aiohttp

# Import HIPAA compliance components and semantic clustering
sys.path.append(os.path.join(os.path.dirname(__file__), '../../ai_services/content-safety'))
from phi_analyzer import PHIAnalyzer, PHIAnalysisResult
from healthcare_encryption import HealthcareEncryptionService
from semantic_clustering import TherapeuticSemanticClustering

logger = logging.getLogger(__name__)

class CacheLevel(Enum):
    """Cache tier levels for therapeutic responses"""
    L1_MEMORY = "l1_memory"        # In-memory Python dict cache
    L2_MONGODB = "l2_mongodb"      # MongoDB therapeutic_response_cache collection
    L3_PERSISTENT = "l3_persistent" # Long-term MongoDB storage
    SOURCE = "source"              # Original computation/query

class TherapeuticCacheManager:
    """Multi-tier caching system optimized for therapeutic AI responses with HIPAA compliance"""
    
    def __init__(self):
        # L1 Cache: In-memory dictionary
        self.l1_cache: Dict[str, Dict[str, Any]] = {}
        self.l1_max_size = 1000  # Maximum L1 cache entries
        self.l1_hit_count = 0
        
        # L2 Cache: MongoDB collection
        self.mongo_client = None
        self.db = None
        self.l2_hit_count = 0
        
        # L3 Cache: Persistent storage
        self.l3_hit_count = 0
        
        # HIPAA Compliance Components
        self.phi_analyzer = PHIAnalyzer()
        self.encryption_service = HealthcareEncryptionService()
        self.semantic_clustering = TherapeuticSemanticClustering()
        self.hipaa_compliance_enabled = True
        self.encryption_enabled = os.getenv("HEALTHCARE_ENCRYPTION_ENABLED", "true").lower() == "true"
        self.semantic_clustering_enabled = os.getenv("SEMANTIC_CLUSTERING_ENABLED", "true").lower() == "true"
        
        # Cache statistics (enhanced with PHI exclusion tracking)
        self.cache_stats = {
            "total_requests": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "evictions": 0,
            "phi_exclusions": 0,
            "phi_detections": 0,
            "hipaa_violations_prevented": 0,
            "semantic_clusters_created": 0,
            "cluster_cache_hits": 0,
            "cluster_preloads": 0,
            "rate_limit_blocks": 0,
            "active_rate_limit_buckets": 0
        }
        
        # HTTP session for external calls
        self.http_session = None
        
        # Rate limiting components (token bucket per user/IP)
        self.rate_limit_enabled = os.getenv("CACHE_RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.rate_limit_requests_per_minute = int(os.getenv("CACHE_RATE_LIMIT_RPM", "60"))  # 60 requests per minute
        self.rate_limit_burst_size = int(os.getenv("CACHE_RATE_LIMIT_BURST", "10"))  # Allow 10 burst requests
        self.rate_limit_buckets: Dict[str, Dict[str, Any]] = {}  # user_id -> bucket state
        self.rate_limit_cleanup_interval = 300  # Clean up old buckets every 5 minutes
        self.last_rate_limit_cleanup = datetime.now(timezone.utc)
        
        # Access logging components for HIPAA audit trail
        self.access_logging_enabled = os.getenv("CACHE_ACCESS_LOGGING_ENABLED", "true").lower() == "true"
        self.access_log_level = os.getenv("CACHE_ACCESS_LOG_LEVEL", "INFO").upper()
        self.audit_logger = logging.getLogger(f"{__name__}.audit")
        
        # MongoDB connection parameters
        self.mongo_host = os.getenv("MONGO_HOST", "localhost")
        self.mongo_port = int(os.getenv("MONGO_PORT", "27017"))
        self.mongo_user = os.getenv("MONGO_USER", "root")
        self.mongo_password = os.getenv("MONGO_PASSWORD", "example")
        self.mongo_db = os.getenv("MONGO_DB", "chatbot_app")
    
    async def initialize(self):
        """Initialize cache system and MongoDB connection"""
        # MongoDB connection
        mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/?authSource=admin&directConnection=true"
        
        self.mongo_client = AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client[self.mongo_db]
        
        # Test connection
        try:
            await self.mongo_client.admin.command('ismaster')
            logger.info(f"✅ Cache manager connected to MongoDB: {self.mongo_host}:{self.mongo_port}")
        except Exception as e:
            logger.warning(f"⚠️  MongoDB connection failed, L2/L3 cache disabled: {e}")
            self.db = None
        
        # HTTP session
        self.http_session = aiohttp.ClientSession()
        
        # Create indexes for cache collections
        await self._create_cache_indexes()
        
        logger.info("✅ Therapeutic cache manager initialized with HIPAA compliance")
    
    async def _create_cache_indexes(self):
        """Create optimized indexes for cache collections"""
        if self.db is None:
            return
            
        try:
            # L2 Cache indexes
            await self.db.therapeutic_response_cache.create_index([
                ("cache_key", 1)
            ], unique=True, name="idx_cache_key")
            
            await self.db.therapeutic_response_cache.create_index([
                ("expires_at", 1)
            ], expireAfterSeconds=0, name="idx_ttl_cache")
            
            await self.db.therapeutic_response_cache.create_index([
                ("user_segment", 1),
                ("care_context", 1),
                ("created_at", -1)
            ], name="idx_user_segment_context")
            
            # L3 Persistent cache indexes
            await self.db.therapeutic_persistent_cache.create_index([
                ("content_hash", 1)
            ], name="idx_content_hash")
            
            await self.db.therapeutic_persistent_cache.create_index([
                ("access_count", -1),
                ("last_accessed", -1)
            ], name="idx_popularity")
            
            logger.info("✅ Cache indexes created")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to create cache indexes: {e}")
    
    async def _analyze_phi_compliance(self, query: str, response_data: Dict[str, Any] = None) -> tuple[bool, PHIAnalysisResult, PHIAnalysisResult]:
        """
        Analyze query and response for PHI content and HIPAA compliance
        
        Returns:
            tuple[cache_allowed, query_analysis, response_analysis]
        """
        if not self.hipaa_compliance_enabled:
            return True, None, None
        
        # Analyze query for PHI
        query_analysis = await self.phi_analyzer.analyze_text(
            query, 
            context={"source": "user_query", "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        
        self.cache_stats["phi_detections"] += len(query_analysis.phi_detections) if query_analysis.phi_detections else 0
        
        # Analyze response for PHI if provided
        response_analysis = None
        if response_data:
            response_text = self._extract_text_from_response(response_data)
            if response_text:
                response_analysis = await self.phi_analyzer.analyze_text(
                    response_text,
                    context={"source": "ai_response", "timestamp": datetime.now(timezone.utc).isoformat()}
                )
                self.cache_stats["phi_detections"] += len(response_analysis.phi_detections) if response_analysis.phi_detections else 0
        
        # Determine cache eligibility
        cache_allowed = True
        exclusion_reason = None
        
        # Check query PHI
        if query_analysis and not query_analysis.cache_safe:
            cache_allowed = False
            exclusion_reason = f"Query contains PHI: {query_analysis.risk_level} risk"
        
        # Check response PHI
        if response_analysis and not response_analysis.cache_safe:
            cache_allowed = False
            if exclusion_reason:
                exclusion_reason += f" | Response contains PHI: {response_analysis.risk_level} risk"
            else:
                exclusion_reason = f"Response contains PHI: {response_analysis.risk_level} risk"
        
        # Log PHI exclusion
        if not cache_allowed:
            self.cache_stats["phi_exclusions"] += 1
            self.cache_stats["hipaa_violations_prevented"] += 1
            logger.warning(f"🚫 HIPAA cache exclusion: {exclusion_reason}")
            
            # Create audit trail
            await self._create_phi_audit_trail({
                "event": "cache_exclusion",
                "reason": exclusion_reason,
                "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16],
                "query_phi_risk": query_analysis.risk_level if query_analysis else "none",
                "response_phi_risk": response_analysis.risk_level if response_analysis else "none",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return cache_allowed, query_analysis, response_analysis
    
    def _extract_text_from_response(self, response_data: Dict[str, Any]) -> Optional[str]:
        """Extract text content from response data for PHI analysis"""
        text_parts = []
        
        if isinstance(response_data, dict):
            # Common response fields that might contain text
            text_fields = ["response", "text", "content", "message", "answer", "guidance"]
            for field in text_fields:
                if field in response_data and isinstance(response_data[field], str):
                    text_parts.append(response_data[field])
            
            # Check nested structures
            if "recommendations" in response_data and isinstance(response_data["recommendations"], list):
                for rec in response_data["recommendations"]:
                    if isinstance(rec, str):
                        text_parts.append(rec)
                    elif isinstance(rec, dict) and "text" in rec:
                        text_parts.append(str(rec["text"]))
        
        return " ".join(text_parts) if text_parts else None
    
    async def _create_phi_audit_trail(self, audit_data: Dict[str, Any]):
        """Create audit trail for PHI-related cache operations"""
        if self.db is None:
            return
        
        try:
            audit_record = {
                **audit_data,
                "service": "therapeutic_cache_manager",
                "compliance_framework": "HIPAA",
                "audit_id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.phi_audit_trail.insert_one(audit_record)
            
        except Exception as e:
            logger.error(f"❌ Failed to create PHI audit trail: {e}")
    
    async def _create_encryption_audit_trail(self, audit_data: Dict[str, Any]):
        """Create audit trail for encryption-related cache operations"""
        if self.db is None:
            return
        
        try:
            audit_record = {
                **audit_data,
                "service": "therapeutic_cache_manager",
                "compliance_framework": "HIPAA",
                "encryption_algorithm": "AES-256-CBC",
                "audit_id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db.encryption_audit_trail.insert_one(audit_record)
            
        except Exception as e:
            logger.error(f"❌ Failed to create encryption audit trail: {e}")
    
    def _generate_cache_key(self, query: str, user_context: Dict[str, Any] = None,
                           care_contexts: List[str] = None, 
                           persona_version: str = None) -> str:
        """Generate deterministic cache key for therapeutic queries"""
        # Normalize inputs for consistent caching
        normalized_query = query.lower().strip()
        
        # Create cache key components
        key_parts = [normalized_query]
        
        if care_contexts:
            key_parts.append("contexts:" + "|".join(sorted(care_contexts)))
        
        if user_context:
            # Only include relevant user context fields for caching
            relevant_fields = ["age_group", "living_situation", "care_level", "language"]
            user_parts = []
            for field in relevant_fields:
                if field in user_context:
                    user_parts.append(f"{field}:{user_context[field]}")
            if user_parts:
                key_parts.append("user:" + "|".join(user_parts))
        
        if persona_version:
            key_parts.append(f"persona:{persona_version}")
        
        # Create hash
        cache_input = "|".join(key_parts)
        return hashlib.sha256(cache_input.encode()).hexdigest()
    
    async def get_cached_response(self, query: str, user_context: Dict[str, Any] = None,
                                care_contexts: List[str] = None,
                                persona_version: str = None,
                                cache_levels: List[CacheLevel] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached therapeutic response with cascade fallback, PHI check, and semantic clustering"""
        # Input validation
        if not query or not isinstance(query, str) or len(query.strip()) == 0:
            logger.warning("🚫 Invalid query provided to cache")
            return None
        
        if len(query) > 10000:  # Prevent extremely large queries
            logger.warning("🚫 Query too large for cache lookup")
            return None
        
        self.cache_stats["total_requests"] += 1
        
        # Rate limiting check
        user_id = user_context.get("user_id", "anonymous") if user_context else "anonymous"
        if not self._check_rate_limit(user_id):
            logger.warning(f"🚫 Cache request rate limited for user {user_id[:8]}...")
            # Log blocked access
            cache_key = self._generate_cache_key(query, user_context, care_contexts, persona_version)
            self._log_cache_access("GET", cache_key, user_context, "ALL", "rate_limited", 
                                 {"reason": "rate_limit_exceeded"})
            return None
        
        # HIPAA Compliance Check - analyze query for PHI content
        if self.hipaa_compliance_enabled:
            cache_allowed, query_analysis, _ = await self._analyze_phi_compliance(query, None)
            if not cache_allowed:
                logger.warning(f"🚫 Cache retrieval blocked due to PHI in query")
                cache_key = self._generate_cache_key(query, user_context, care_contexts, persona_version)
                phi_types = getattr(query_analysis, 'detected_types', []) if query_analysis else []
                self._log_cache_access("GET", cache_key, user_context, "ALL", "blocked", 
                                     {"reason": "phi_detected", "phi_types": phi_types})
                return None
        
        cache_key = self._generate_cache_key(query, user_context, care_contexts, persona_version)
        cache_levels = cache_levels or [CacheLevel.L1_MEMORY, CacheLevel.L2_MONGODB, CacheLevel.L3_PERSISTENT]
        
        # Try direct cache lookup first
        cached_response = await self._get_direct_cache_response(cache_key, cache_levels, user_context)
        if cached_response:
            return cached_response
        
        # If no direct hit and semantic clustering enabled, try cluster-based lookup
        if self.semantic_clustering_enabled:
            cluster_response = await self._get_cluster_based_response(query, user_context, care_contexts)
            if cluster_response:
                self.cache_stats["cluster_cache_hits"] += 1
                return cluster_response
        
        self.cache_stats["cache_misses"] += 1
        # Log cache miss
        self._log_cache_access("GET", cache_key, user_context, "ALL", "miss")
        return None
    
    async def _get_direct_cache_response(self, cache_key: str, cache_levels: List[CacheLevel], user_context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Direct cache lookup across all tiers"""
        for level in cache_levels:
            try:
                if level == CacheLevel.L1_MEMORY:
                    result = await self._get_l1_cache(cache_key)
                    if result:
                        self.cache_stats["l1_hits"] += 1
                        # Log successful L1 cache hit
                        self._log_cache_access("GET", cache_key, user_context, "L1", "hit")
                        await self._promote_to_higher_cache(cache_key, result, CacheLevel.L1_MEMORY)
                        return result
                
                elif level == CacheLevel.L2_MONGODB:
                    result = await self._get_l2_cache(cache_key)
                    if result:
                        self.cache_stats["l2_hits"] += 1
                        # Log successful L2 cache hit
                        self._log_cache_access("GET", cache_key, user_context, "L2", "hit")
                        # Promote to L1
                        await self._set_l1_cache(cache_key, result)
                        return result
                
                elif level == CacheLevel.L3_PERSISTENT:
                    result = await self._get_l3_cache(cache_key)
                    if result:
                        self.cache_stats["l3_hits"] += 1
                        # Log successful L3 cache hit
                        self._log_cache_access("GET", cache_key, user_context, "L3", "hit")
                        # Promote to L2 and L1
                        await self._set_l2_cache(cache_key, result, ttl_hours=24)
                        await self._set_l1_cache(cache_key, result)
                        return result
                
            except Exception as e:
                logger.warning(f"⚠️  Cache level {level.value} failed: {e}")
                continue
        
        return None
    
    async def _get_cluster_based_response(self, query: str, user_context: Dict[str, Any] = None, 
                                        care_contexts: List[str] = None) -> Optional[Dict[str, Any]]:
        """Attempt to find cached response using semantic clustering"""
        try:
            # Analyze query for clustering
            query_analysis = await self.semantic_clustering.analyze_query_for_clustering(
                query, {"user_context": user_context, "care_contexts": care_contexts}
            )
            
            # Find or create cluster
            cluster_id = await self.semantic_clustering.find_or_create_cluster(query_analysis)
            
            if not cluster_id:
                return None
            
            # Get related queries from the same cluster
            related_queries = await self.semantic_clustering.get_related_queries(cluster_id, limit=5)
            
            # Try to find cached responses for related queries
            for related_query in related_queries:
                if related_query != query:  # Don't try the same query
                    related_cache_key = self._generate_cache_key(
                        related_query, user_context, care_contexts
                    )
                    
                    # Try L1 and L2 cache for related queries
                    cached_response = await self._get_direct_cache_response(
                        related_cache_key, 
                        [CacheLevel.L1_MEMORY, CacheLevel.L2_MONGODB],
                        user_context
                    )
                    
                    if cached_response:
                        logger.info(f"🎯 Cluster-based cache hit: {cluster_id}")
                        
                        # Add cluster information to response
                        cached_response["cluster_match"] = {
                            "cluster_id": cluster_id,
                            "matched_query": related_query,
                            "original_query": query
                        }
                        
                        return cached_response
            
            # No related cached responses found, but we can preload cluster cache
            await self._preload_cluster_cache(cluster_id)
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️  Cluster-based lookup failed: {e}")
            return None
    
    async def _preload_cluster_cache(self, cluster_id: str):
        """Preload cache with common queries for this cluster"""
        try:
            cache_candidates = await self.semantic_clustering.get_cluster_cache_candidates(cluster_id)
            
            # Asynchronously warm cache with cluster-specific queries
            for candidate in cache_candidates[:3]:  # Limit to top 3 candidates
                asyncio.create_task(self._warm_cluster_candidate(candidate))
                self.cache_stats["cluster_preloads"] += 1
            
            logger.info(f"⚡ Preloading cluster cache: {cluster_id}")
            
        except Exception as e:
            logger.warning(f"⚠️  Cluster cache preload failed: {e}")
    
    async def _warm_cluster_candidate(self, candidate: Dict[str, Any]):
        """Warm cache with a cluster candidate query"""
        try:
            # Generate synthetic response for warming (in production, call actual AI service)
            synthetic_response = {
                "response_type": "cluster_warmed",
                "query_template": candidate["query_template"],
                "care_contexts": candidate["care_contexts"],
                "urgency_level": candidate["urgency_level"],
                "cluster_id": candidate["cluster_id"],
                "warmed_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Cache the synthetic response
            await self.set_cached_response(
                query=candidate["query_template"],
                response_data=synthetic_response,
                care_contexts=candidate["care_contexts"],
                ttl_hours=6  # Shorter TTL for preloaded content
            )
            
        except Exception as e:
            logger.warning(f"⚠️  Cluster warming failed: {e}")
    
    async def set_cached_response(self, query: str, response_data: Dict[str, Any],
                                user_context: Dict[str, Any] = None,
                                care_contexts: List[str] = None,
                                persona_version: str = None,
                                ttl_hours: int = 12) -> tuple[str, bool]:
        """
        Store therapeutic response in multi-tier cache with HIPAA compliance check
        
        Returns:
            tuple[cache_key, was_cached] - was_cached=False if excluded due to PHI
        """
        cache_key = self._generate_cache_key(query, user_context, care_contexts, persona_version)
        
        # Rate limiting check for cache writes
        user_id = user_context.get("user_id", "anonymous") if user_context else "anonymous"
        if not self._check_rate_limit(user_id):
            logger.warning(f"🚫 Cache write rate limited for user {user_id[:8]}...")
            return cache_key, False  # Return cache_key but indicate not cached
        
        # HIPAA Compliance Check - analyze for PHI content
        cache_allowed, query_analysis, response_analysis = await self._analyze_phi_compliance(
            query, response_data
        )
        
        # If PHI detected, do not cache but still return cache key for tracking
        if not cache_allowed:
            logger.warning(f"🚫 Skipping cache due to PHI content: {cache_key[:8]}...")
            return cache_key, False
        
        # Enrich response data with metadata (PHI-safe content only)
        cached_data = {
            "response": response_data,
            "query": query,
            "care_contexts": care_contexts or [],
            "user_context": user_context or {},
            "persona_version": persona_version,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "cache_key": cache_key,
            "access_count": 1,
            "hipaa_compliant": True,
            "phi_analysis": {
                "query_risk": query_analysis.risk_level if query_analysis else "none",
                "response_risk": response_analysis.risk_level if response_analysis else "none",
                "cleared_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        try:
            # Store in all cache levels (only PHI-safe content)
            await self._set_l1_cache(cache_key, cached_data)
            await self._set_l2_cache(cache_key, cached_data, ttl_hours)
            await self._set_l3_cache(cache_key, cached_data)
            
            self.cache_stats["cache_writes"] += 1
            # Log successful cache write
            self._log_cache_access("SET", cache_key, user_context, "ALL", "success", 
                                 {"ttl_hours": ttl_hours, "encrypted": self.encryption_enabled})
            logger.info(f"✅ Cached HIPAA-compliant therapeutic response: {cache_key[:8]}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to cache response: {e}")
            return cache_key, False
        
        return cache_key, True
    
    async def _get_l1_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from L1 in-memory cache"""
        cached_item = self.l1_cache.get(cache_key)
        if cached_item:
            # Update access time and count
            cached_item["last_accessed"] = datetime.now(timezone.utc).isoformat()
            cached_item["access_count"] = cached_item.get("access_count", 0) + 1
            return cached_item
        return None
    
    async def _set_l1_cache(self, cache_key: str, data: Dict[str, Any]):
        """Set L1 in-memory cache with LRU eviction"""
        # Check size limits
        if len(self.l1_cache) >= self.l1_max_size:
            await self._evict_l1_cache()
        
        data["last_accessed"] = datetime.now(timezone.utc).isoformat()
        self.l1_cache[cache_key] = data
    
    async def _evict_l1_cache(self):
        """Evict least recently used items from L1 cache with secure clearing"""
        if not self.l1_cache:
            return
        
        # Find least recently accessed item
        oldest_key = min(
            self.l1_cache.keys(),
            key=lambda k: self.l1_cache[k].get("last_accessed", "")
        )
        
        # Securely clear the data before removing from cache
        evicted_data = self.l1_cache[oldest_key]
        self._secure_clear_data(evicted_data)
        
        del self.l1_cache[oldest_key]
        self.cache_stats["evictions"] += 1
        
        # Log cache eviction
        self._log_cache_access("EVICT", oldest_key, None, "L1", "success", 
                             {"reason": "lru_eviction", "secure_clear": True})
        logger.debug(f"🧹 Securely evicted L1 cache item: {oldest_key[:16]}...")
    
    async def _get_l2_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from L2 MongoDB cache with healthcare decryption"""
        if self.db is None:
            return None
        
        try:
            cached_doc = await self.db.therapeutic_response_cache.find_one({
                "cache_key": cache_key,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            
            if cached_doc:
                # Update access statistics
                await self.db.therapeutic_response_cache.update_one(
                    {"cache_key": cache_key},
                    {
                        "$inc": {"access_count": 1},
                        "$set": {"last_accessed": datetime.now(timezone.utc)}
                    }
                )
                
                # Handle encrypted data
                if cached_doc.get("is_encrypted", False):
                    try:
                        decrypted_data = self.encryption_service.decrypt_from_storage(cached_doc)
                        
                        # Create decryption audit trail
                        await self._create_encryption_audit_trail({
                            "event": "l2_cache_decrypt",
                            "cache_key": cache_key[:16],
                            "encryption_key_id": self.encryption_service.key_id,
                            "storage_tier": "l2_mongodb"
                        })
                        
                        return decrypted_data
                        
                    except Exception as e:
                        logger.error(f"❌ L2 cache decryption failed: {e}")
                        return None
                else:
                    # Remove MongoDB specific fields for unencrypted data
                    cached_doc.pop("_id", None)
                    cached_doc.pop("expires_at", None)
                    return cached_doc
                
        except Exception as e:
            logger.warning(f"⚠️  L2 cache get failed: {e}")
            return None
    
    async def _set_l2_cache(self, cache_key: str, data: Dict[str, Any], ttl_hours: int = 12):
        """Set L2 MongoDB cache with TTL and healthcare encryption"""
        if self.db is None:
            return
        
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
            
            # Prepare cache document
            cache_doc_base = {
                **data,
                "cache_key": cache_key,
                "expires_at": expires_at,
                "created_at": datetime.now(timezone.utc)
            }
            
            # Apply healthcare encryption if enabled
            if self.encryption_enabled:
                try:
                    encrypted_storage = self.encryption_service.encrypt_for_storage(
                        cache_doc_base, 
                        storage_context="l2_mongodb_cache"
                    )
                    cache_doc = {
                        "cache_key": cache_key,
                        "expires_at": expires_at,
                        "created_at": datetime.now(timezone.utc),
                        **encrypted_storage
                    }
                    
                    # Create encryption audit trail
                    await self._create_encryption_audit_trail({
                        "event": "l2_cache_encrypt",
                        "cache_key": cache_key[:16],
                        "encryption_key_id": self.encryption_service.key_id,
                        "storage_tier": "l2_mongodb"
                    })
                    
                except Exception as e:
                    logger.error(f"❌ L2 cache encryption failed: {e}")
                    # Fall back to unencrypted storage with warning
                    cache_doc = cache_doc_base
                    cache_doc["encryption_failed"] = True
                    cache_doc["encryption_error"] = str(e)
            else:
                cache_doc = cache_doc_base
            
            # Upsert cache document
            await self.db.therapeutic_response_cache.update_one(
                {"cache_key": cache_key},
                {"$set": cache_doc},
                upsert=True
            )
            
        except Exception as e:
            logger.warning(f"⚠️  L2 cache set failed: {e}")
    
    async def _get_l3_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from L3 persistent cache with healthcare decryption"""
        if self.db is None:
            return None
        
        try:
            # Check persistent cache by content similarity
            persistent_doc = await self.db.therapeutic_persistent_cache.find_one({
                "cache_key": cache_key
            })
            
            if persistent_doc:
                # Update access statistics
                await self.db.therapeutic_persistent_cache.update_one(
                    {"cache_key": cache_key},
                    {
                        "$inc": {"access_count": 1},
                        "$set": {"last_accessed": datetime.now(timezone.utc)}
                    }
                )
                
                # Handle encrypted data
                if persistent_doc.get("is_encrypted", False):
                    try:
                        decrypted_data = self.encryption_service.decrypt_from_storage(persistent_doc)
                        
                        # Create decryption audit trail
                        await self._create_encryption_audit_trail({
                            "event": "l3_cache_decrypt",
                            "cache_key": cache_key[:16],
                            "encryption_key_id": self.encryption_service.key_id,
                            "storage_tier": "l3_persistent"
                        })
                        
                        return decrypted_data
                        
                    except Exception as e:
                        logger.error(f"❌ L3 cache decryption failed: {e}")
                        return None
                else:
                    # Remove MongoDB specific fields for unencrypted data
                    persistent_doc.pop("_id", None)
                    return persistent_doc
                
        except Exception as e:
            logger.warning(f"⚠️  L3 cache get failed: {e}")
            return None
    
    async def _set_l3_cache(self, cache_key: str, data: Dict[str, Any]):
        """Set L3 persistent cache with healthcare encryption"""
        if self.db is None:
            return
        
        try:
            # Prepare cache document
            cache_doc_base = {
                **data,
                "cache_key": cache_key,
                "created_at": datetime.now(timezone.utc),
                "access_count": 1,
                "last_accessed": datetime.now(timezone.utc)
            }
            
            # Apply healthcare encryption if enabled
            if self.encryption_enabled:
                try:
                    encrypted_storage = self.encryption_service.encrypt_for_storage(
                        cache_doc_base, 
                        storage_context="l3_persistent_cache"
                    )
                    cache_doc = {
                        "cache_key": cache_key,
                        "created_at": datetime.now(timezone.utc),
                        "access_count": 1,
                        "last_accessed": datetime.now(timezone.utc),
                        **encrypted_storage
                    }
                    
                    # Create encryption audit trail
                    await self._create_encryption_audit_trail({
                        "event": "l3_cache_encrypt",
                        "cache_key": cache_key[:16],
                        "encryption_key_id": self.encryption_service.key_id,
                        "storage_tier": "l3_persistent"
                    })
                    
                except Exception as e:
                    logger.error(f"❌ L3 cache encryption failed: {e}")
                    # Fall back to unencrypted storage with warning
                    cache_doc = cache_doc_base
                    cache_doc["encryption_failed"] = True
                    cache_doc["encryption_error"] = str(e)
            else:
                cache_doc = cache_doc_base
            
            # Upsert persistent cache document
            await self.db.therapeutic_persistent_cache.update_one(
                {"cache_key": cache_key},
                {"$set": cache_doc},
                upsert=True
            )
            
        except Exception as e:
            logger.warning(f"⚠️  L3 cache set failed: {e}")
    
    async def _promote_to_higher_cache(self, cache_key: str, data: Dict[str, Any], from_level: CacheLevel):
        """Promote frequently accessed items to higher cache tiers"""
        access_count = data.get("access_count", 0)
        
        # Promotion thresholds
        if from_level == CacheLevel.L2_MONGODB and access_count > 5:
            await self._set_l1_cache(cache_key, data)
        elif from_level == CacheLevel.L3_PERSISTENT and access_count > 10:
            await self._set_l2_cache(cache_key, data, ttl_hours=48)
            await self._set_l1_cache(cache_key, data)
    
    async def warm_cache(self, common_queries: List[Dict[str, Any]]):
        """Pre-warm cache with common therapeutic queries"""
        logger.info(f"🔥 Warming cache with {len(common_queries)} common queries...")
        
        for query_config in common_queries:
            query = query_config.get("query", "")
            care_contexts = query_config.get("care_contexts", [])
            
            # Check if already cached
            cached = await self.get_cached_response(query, care_contexts=care_contexts)
            if not cached:
                logger.info(f"⚡ Pre-warming cache for: {query[:50]}...")
                
                # Generate synthetic response for warming (in production, use real responses)
                synthetic_response = {
                    "response_type": "cache_warmed",
                    "query": query,
                    "care_contexts": care_contexts,
                    "warmed_at": datetime.now(timezone.utc).isoformat()
                }
                
                await self.set_cached_response(
                    query=query,
                    response_data=synthetic_response,
                    care_contexts=care_contexts,
                    ttl_hours=24
                )
        
        logger.info("✅ Cache warming completed")
    
    async def invalidate_cache(self, pattern: str = None, care_contexts: List[str] = None):
        """Invalidate cache entries matching pattern or care contexts"""
        invalidated_count = 0
        
        # L1 cache invalidation
        if pattern:
            l1_keys_to_remove = [k for k in self.l1_cache.keys() if pattern in k]
            for key in l1_keys_to_remove:
                del self.l1_cache[key]
                invalidated_count += 1
        
        # L2/L3 cache invalidation
        if self.db is not None:
            try:
                query_filter = {}
                if care_contexts:
                    query_filter["care_contexts"] = {"$in": care_contexts}
                
                l2_result = await self.db.therapeutic_response_cache.delete_many(query_filter)
                l3_result = await self.db.therapeutic_persistent_cache.delete_many(query_filter)
                
                invalidated_count += l2_result.deleted_count + l3_result.deleted_count
                
            except Exception as e:
                logger.warning(f"⚠️  Cache invalidation failed: {e}")
        
        logger.info(f"🗑️  Invalidated {invalidated_count} cache entries")
        return invalidated_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics with HIPAA compliance metrics"""
        total_hits = self.cache_stats["l1_hits"] + self.cache_stats["l2_hits"] + self.cache_stats["l3_hits"]
        total_requests = self.cache_stats["total_requests"]
        
        hit_rate = (total_hits / max(total_requests, 1)) * 100
        phi_exclusion_rate = (self.cache_stats["phi_exclusions"] / max(total_requests, 1)) * 100
        rate_limit_block_rate = (self.cache_stats["rate_limit_blocks"] / max(total_requests, 1)) * 100
        
        # Update active buckets count
        self.cache_stats["active_rate_limit_buckets"] = len(self.rate_limit_buckets)
        
        return {
            **self.cache_stats,
            "cache_hit_rate": f"{hit_rate:.2f}%",
            "phi_exclusion_rate": f"{phi_exclusion_rate:.2f}%",
            "rate_limit_block_rate": f"{rate_limit_block_rate:.2f}%",
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_limit_config": {
                "requests_per_minute": self.rate_limit_requests_per_minute,
                "burst_size": self.rate_limit_burst_size
            } if self.rate_limit_enabled else None,
            "l1_size": len(self.l1_cache),
            "l1_hit_rate": f"{(self.cache_stats['l1_hits'] / max(total_requests, 1)) * 100:.2f}%",
            "l2_hit_rate": f"{(self.cache_stats['l2_hits'] / max(total_requests, 1)) * 100:.2f}%",
            "l3_hit_rate": f"{(self.cache_stats['l3_hits'] / max(total_requests, 1)) * 100:.2f}%",
            "hipaa_compliance_enabled": self.hipaa_compliance_enabled,
            "encryption_enabled": self.encryption_enabled,
            "semantic_clustering_enabled": self.semantic_clustering_enabled,
            "phi_analyzer_active": self.phi_analyzer is not None,
            "encryption_service_active": self.encryption_service is not None,
            "semantic_clustering_active": self.semantic_clustering is not None,
            "encryption_key_id": getattr(self.encryption_service, 'key_id', 'unknown') if self.encryption_service else None,
            "clustering_stats": self.semantic_clustering.get_clustering_stats() if self.semantic_clustering else {}
        }
    
    def _log_cache_access(self, operation: str, cache_key: str, user_context: Dict[str, Any] = None, 
                          cache_level: str = None, result: str = "success", 
                          additional_info: Dict[str, Any] = None) -> None:
        """
        Log cache access operations for HIPAA compliance audit trail
        
        Args:
            operation: Type of operation (GET, SET, EVICT, DELETE, etc.)
            cache_key: Cache key involved (truncated for privacy)
            user_context: User context if available
            cache_level: Which cache tier (L1, L2, L3)
            result: Operation result (success, failure, blocked, etc.)
            additional_info: Any additional context to log
        """
        if not self.access_logging_enabled:
            return
        
        try:
            user_id = user_context.get("user_id", "anonymous") if user_context else "anonymous"
            session_id = user_context.get("session_id", "unknown") if user_context else "unknown"
            
            # Create audit log entry
            audit_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": operation,
                "cache_key_hash": cache_key[:16] + "..." if len(cache_key) > 16 else cache_key,  # Truncate for privacy
                "user_id_hash": user_id[:10] + "..." if len(user_id) > 10 else user_id,  # Truncate for privacy (HIPAA-compliant)
                "session_id": session_id,
                "cache_level": cache_level,
                "result": result,
                "service": "therapeutic_cache",
                "compliance": "hipaa"
            }
            
            # Add additional context if provided
            if additional_info:
                audit_entry.update(additional_info)
            
            # Log based on configured level
            log_message = (
                f"CACHE_ACCESS: {operation} | User: {audit_entry['user_id_hash']} | "
                f"Level: {cache_level} | Result: {result} | "
                f"Key: {audit_entry['cache_key_hash']}"
            )
            
            if self.access_log_level == "DEBUG":
                self.audit_logger.debug(f"{log_message} | Full_Context: {json.dumps(audit_entry)}")
            elif self.access_log_level == "INFO":
                self.audit_logger.info(log_message)
            elif self.access_log_level == "WARNING":
                if result in ["blocked", "failure", "rate_limited"]:
                    self.audit_logger.warning(log_message)
            elif self.access_log_level == "ERROR":
                if result in ["failure", "error"]:
                    self.audit_logger.error(log_message)
            
        except Exception as e:
            # Don't let logging failures break cache operations
            logger.warning(f"⚠️ Failed to log cache access: {e}")
    
    def _secure_clear_data(self, data: Any) -> None:
        """
        Securely clear sensitive data from memory
        
        This method attempts to overwrite sensitive data in memory to prevent
        recovery through memory dumps or swap files (HIPAA requirement)
        """
        try:
            if isinstance(data, dict):
                # Clear dictionary values
                for key, value in list(data.items()):
                    if isinstance(value, (str, bytes)):
                        # Overwrite string/bytes data with zeros
                        if isinstance(value, str) and len(value) > 0:
                            # Can't directly overwrite immutable strings in Python,
                            # but we can ensure references are cleared
                            data[key] = "0" * len(value)
                        elif isinstance(value, bytes) and len(value) > 0:
                            # Clear bytearray if possible
                            try:
                                if hasattr(value, '__len__'):
                                    data[key] = b"0" * len(value)
                            except (TypeError, AttributeError):
                                pass
                    elif isinstance(value, (dict, list)):
                        self._secure_clear_data(value)
                    
                    # Remove the key-value pair
                    data[key] = None
                    
                # Clear the dictionary
                data.clear()
                
            elif isinstance(data, list):
                # Clear list items
                for i, item in enumerate(data):
                    if isinstance(item, (str, bytes)):
                        if isinstance(item, str) and len(item) > 0:
                            data[i] = "0" * len(item)
                        elif isinstance(item, bytes) and len(item) > 0:
                            data[i] = b"0" * len(item)
                    elif isinstance(item, (dict, list)):
                        self._secure_clear_data(item)
                    
                    data[i] = None
                
                # Clear the list
                data.clear()
            
            # Force garbage collection to help clear memory
            gc.collect()
            
        except Exception as e:
            logger.warning(f"⚠️ Error during secure memory clearing: {e}")
    
    def _cleanup_old_rate_limit_buckets(self):
        """Clean up old rate limit buckets to prevent memory leaks"""
        now = datetime.now(timezone.utc)
        if (now - self.last_rate_limit_cleanup).total_seconds() < self.rate_limit_cleanup_interval:
            return
        
        # Remove buckets older than 1 hour
        cutoff_time = now - timedelta(hours=1)
        buckets_to_remove = []
        
        for user_id, bucket in self.rate_limit_buckets.items():
            if bucket.get("last_refill", now) < cutoff_time:
                buckets_to_remove.append(user_id)
        
        for user_id in buckets_to_remove:
            # Securely clear bucket data before removal
            bucket_data = self.rate_limit_buckets[user_id]
            self._secure_clear_data(bucket_data)
            del self.rate_limit_buckets[user_id]
        
        self.last_rate_limit_cleanup = now
        
        if buckets_to_remove:
            logger.debug(f"🧹 Cleaned up {len(buckets_to_remove)} old rate limit buckets")
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded rate limit using token bucket algorithm
        
        Args:
            user_id: User identifier for rate limiting
            
        Returns:
            bool: True if request is allowed, False if rate limited
        """
        if not self.rate_limit_enabled:
            return True
        
        # Periodic cleanup of old buckets
        self._cleanup_old_rate_limit_buckets()
        
        now = datetime.now(timezone.utc)
        
        # Initialize bucket if not exists
        if user_id not in self.rate_limit_buckets:
            self.rate_limit_buckets[user_id] = {
                "tokens": self.rate_limit_burst_size,
                "last_refill": now,
                "total_requests": 0,
                "blocked_requests": 0
            }
        
        bucket = self.rate_limit_buckets[user_id]
        
        # Calculate time since last refill
        time_since_refill = (now - bucket["last_refill"]).total_seconds()
        
        # Add tokens based on time passed (rate = requests per minute)
        tokens_to_add = int(time_since_refill * (self.rate_limit_requests_per_minute / 60.0))
        bucket["tokens"] = min(self.rate_limit_burst_size, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now
        bucket["total_requests"] += 1
        
        # Check if tokens are available
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        else:
            bucket["blocked_requests"] += 1
            self.cache_stats["rate_limit_blocks"] += 1
            logger.warning(f"🚫 Rate limit exceeded for user {user_id[:8]}... "
                         f"({bucket['blocked_requests']} blocked / {bucket['total_requests']} total)")
            return False
    
    def get_rate_limit_status(self, user_id: str) -> Dict[str, Any]:
        """Get current rate limit status for a user"""
        if not self.rate_limit_enabled:
            return {"enabled": False}
        
        bucket = self.rate_limit_buckets.get(user_id)
        if not bucket:
            return {
                "enabled": True,
                "tokens_remaining": self.rate_limit_burst_size,
                "requests_per_minute": self.rate_limit_requests_per_minute,
                "burst_size": self.rate_limit_burst_size,
                "total_requests": 0,
                "blocked_requests": 0
            }
        
        return {
            "enabled": True,
            "tokens_remaining": bucket["tokens"],
            "requests_per_minute": self.rate_limit_requests_per_minute,
            "burst_size": self.rate_limit_burst_size,
            "total_requests": bucket["total_requests"],
            "blocked_requests": bucket["blocked_requests"],
            "last_refill": bucket["last_refill"].isoformat()
        }
    
    async def cleanup(self):
        """Clean up cache manager resources with secure memory clearing"""
        logger.info("🧹 Starting secure cleanup of therapeutic cache manager...")
        
        # Securely clear L1 cache
        if self.l1_cache:
            logger.debug(f"🔐 Securely clearing {len(self.l1_cache)} L1 cache items")
            for cache_key, cache_data in list(self.l1_cache.items()):
                self._secure_clear_data(cache_data)
            self.l1_cache.clear()
        
        # Securely clear rate limiting buckets
        if self.rate_limit_buckets:
            logger.debug(f"🔐 Securely clearing {len(self.rate_limit_buckets)} rate limit buckets")
            for user_id, bucket_data in list(self.rate_limit_buckets.items()):
                self._secure_clear_data(bucket_data)
            self.rate_limit_buckets.clear()
        
        # Reset cache statistics (preserve structure but clear sensitive data)
        logger.debug("🔐 Resetting cache statistics")
        # Save the stats before clearing, then reinitialize
        stats_backup = {
            "total_requests": self.cache_stats.get("total_requests", 0),
            "rate_limit_blocks": self.cache_stats.get("rate_limit_blocks", 0),
            "phi_exclusions": self.cache_stats.get("phi_exclusions", 0)
        }
        self._secure_clear_data(self.cache_stats)
        
        # Reinitialize stats structure for future use
        self.cache_stats = {
            "total_requests": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "evictions": 0,
            "phi_exclusions": 0,
            "phi_detections": 0,
            "hipaa_violations_prevented": 0,
            "semantic_clusters_created": 0,
            "cluster_cache_hits": 0,
            "cluster_preloads": 0,
            "rate_limit_blocks": 0,
            "active_rate_limit_buckets": 0
        }
        
        # Close network connections
        if self.http_session:
            await self.http_session.close()
        if self.mongo_client:
            self.mongo_client.close()
            
        # Force garbage collection to help clear memory
        gc.collect()
        
        logger.info("✅ Therapeutic cache manager securely cleaned up")

# Global cache manager instance
_cache_manager_instance = None

async def get_therapeutic_cache_manager() -> TherapeuticCacheManager:
    """Get the global therapeutic cache manager instance"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = TherapeuticCacheManager()
        await _cache_manager_instance.initialize()
    return _cache_manager_instance