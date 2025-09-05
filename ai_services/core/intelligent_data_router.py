"""
Intelligent Therapeutic Data Router
Routes queries to optimal databases based on query characteristics and therapeutic context
Implements Priority 2 from MongoDB-PostgreSQL Integration Analysis
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import hashlib
import json
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp
import os

from data_layer.connections.postgres_connection import postgres_manager
from .therapeutic_cache_manager import get_therapeutic_cache_manager

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Query type classification for routing decisions"""
    USER_AUTH = "user_auth"
    DOCUMENT_SEARCH = "document_search"
    KNOWLEDGE_SEARCH = "knowledge_search"
    THERAPEUTIC_CONTEXT = "therapeutic_context"
    CRISIS_DETECTION = "crisis_detection"
    PERSONA_LOOKUP = "persona_lookup"
    HYBRID_SEARCH = "hybrid_search"
    CONVERSATION_HISTORY = "conversation_history"
    CACHED_RESULT = "cached_result"

class TherapeuticContext(Enum):
    """Therapeutic context for care-specific routing"""
    GRIEF = "grief"
    LONELINESS = "loneliness"
    ANXIETY = "anxiety"
    CAREGIVER_STRESS = "caregiver-stress"
    CRISIS = "crisis"
    HEALTH = "health"
    GENERAL = "general"

class IntelligentTherapeuticRouter:
    """Routes queries to optimal database based on therapeutic context and query characteristics"""
    
    def __init__(self):
        self.postgres_manager = None
        self.mongo_client = None
        self.mongo_database = None
        self.embedding_session = None
        self.cache_manager = None
        
        # MongoDB configuration
        self.mongo_host = os.getenv("MONGO_HOST", "localhost")
        self.mongo_port = int(os.getenv("MONGO_PORT", "27017"))
        self.mongo_user = os.getenv("MONGO_USER", "root")
        self.mongo_password = os.getenv("MONGO_PASSWORD", "example")
        self.mongo_db = os.getenv("MONGO_DB", "chatbot_app")
        
        # Query routing performance tracking
        self.routing_stats = {
            "total_queries": 0,
            "mongodb_queries": 0,
            "postgres_queries": 0,
            "hybrid_queries": 0,
            "cache_hits": 0
        }
    
    async def initialize(self):
        """Initialize database connections and HTTP session"""
        # PostgreSQL connection
        self.postgres_manager = postgres_manager
        await self.postgres_manager.initialize()
        logger.info("✅ Connected to PostgreSQL")
        
        # MongoDB connection
        try:
            mongo_uri = f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/?authSource=admin&directConnection=true"
            self.mongo_client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            await self.mongo_client.admin.command('ping')
            self.mongo_database = self.mongo_client[self.mongo_db]
            logger.info(f"✅ Connected to MongoDB: {self.mongo_host}:{self.mongo_port}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            self.mongo_client = None
            self.mongo_database = None
        
        # HTTP session for embedding service
        self.embedding_session = aiohttp.ClientSession()
        
        # Initialize therapeutic cache manager
        self.cache_manager = await get_therapeutic_cache_manager()
        await self.cache_manager.initialize()
        logger.info("✅ Cache manager initialized")
        
        logger.info("✅ Initialized intelligent therapeutic router")
    
    async def route_query(self, query_type: QueryType, **kwargs) -> Dict[str, Any]:
        """Main routing method - directs queries to optimal database(s)"""
        self.routing_stats["total_queries"] += 1
        
        routing_map = {
            QueryType.USER_AUTH: self._postgres_auth_query,
            QueryType.DOCUMENT_SEARCH: self._mongodb_therapeutic_search,
            QueryType.KNOWLEDGE_SEARCH: self._postgres_knowledge_search,
            QueryType.THERAPEUTIC_CONTEXT: self._mongodb_context_search,
            QueryType.CRISIS_DETECTION: self._postgres_crisis_lookup,
            QueryType.PERSONA_LOOKUP: self._postgres_persona_query,
            QueryType.HYBRID_SEARCH: self._hybrid_therapeutic_search,
            QueryType.CONVERSATION_HISTORY: self._postgres_conversation_history,
            QueryType.CACHED_RESULT: self._cache_lookup
        }
        
        try:
            return await routing_map[query_type](**kwargs)
        except Exception as e:
            logger.error(f"❌ Routing failed for {query_type}: {e}")
            return {"error": str(e), "query_type": query_type.value}
    
    async def _mongodb_therapeutic_search(self, query: str, care_contexts: List[str] = None, 
                                        limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Search therapeutic documents in MongoDB using cosine similarity"""
        self.routing_stats["mongodb_queries"] += 1
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Build aggregation pipeline for local MongoDB
            pipeline = []
            
            # Match by care context if specified
            if care_contexts:
                pipeline.append({
                    "$match": {
                        "care_contexts": {"$in": care_contexts}
                    }
                })
            
            # Add vector similarity calculation
            pipeline.append({
                "$addFields": {
                    "vector_score": {
                        "$let": {
                            "vars": {
                                "dotProduct": {
                                    "$reduce": {
                                        "input": {"$zip": {"inputs": ["$embedding", query_embedding]}},
                                        "initialValue": 0,
                                        "in": {"$add": ["$$value", {"$multiply": [{"$arrayElemAt": ["$$this", 0]}, {"$arrayElemAt": ["$$this", 1]}]}]}
                                    }
                                },
                                "queryMagnitude": {
                                    "$sqrt": {"$reduce": {
                                        "input": query_embedding,
                                        "initialValue": 0,
                                        "in": {"$add": ["$$value", {"$multiply": ["$$this", "$$this"]}]}
                                    }}
                                },
                                "docMagnitude": {
                                    "$sqrt": {"$reduce": {
                                        "input": "$embedding",
                                        "initialValue": 0,
                                        "in": {"$add": ["$$value", {"$multiply": ["$$this", "$$this"]}]}
                                    }}
                                }
                            },
                            "in": {
                                "$divide": [
                                    "$$dotProduct",
                                    {"$multiply": ["$$queryMagnitude", "$$docMagnitude"]}
                                ]
                            }
                        }
                    },
                    "care_context_match": {
                        "$size": {
                            "$setIntersection": [
                                "$care_contexts",
                                care_contexts or ["general"]
                            ]
                        }
                    }
                }
            })
            
            # Filter by minimum similarity
            pipeline.append({
                "$match": {
                    "vector_score": {"$gte": 0.3}  # Minimum similarity threshold
                }
            })
            
            # Calculate combined score
            pipeline.append({
                "$addFields": {
                    "combined_score": {
                        "$add": [
                            "$vector_score",
                            {"$multiply": ["$care_context_match", 0.1]}
                        ]
                    }
                }
            })
            
            # Sort and limit
            pipeline.extend([
                {"$sort": {"combined_score": -1}},
                {"$limit": limit}
            ])
            
            # Execute search
            if self.mongo_database is None:
                return {"error": "MongoDB not connected", "source": "mongodb_therapeutic"}
                
            results = await self.mongo_database.therapeutic_content.aggregate(pipeline).to_list(limit)
            
            return {
                "source": "mongodb_therapeutic",
                "results": results,
                "count": len(results),
                "query_type": "cosine_similarity",
                "care_contexts": care_contexts
            }
            
        except Exception as e:
            logger.error(f"❌ MongoDB therapeutic search failed: {e}")
            # Fallback to text search
            return await self._mongodb_text_fallback_search(query, care_contexts, limit)
    
    async def _mongodb_text_fallback_search(self, query: str, care_contexts: List[str] = None,
                                          limit: int = 10) -> Dict[str, Any]:
        """Fallback text search for MongoDB when vector search fails"""
        try:
            if self.mongo_database is None:
                return {"error": "MongoDB not connected", "source": "mongodb_therapeutic"}
            
            # Build text search query
            search_query = {"$text": {"$search": query}}
            
            # Add care context filter if specified
            if care_contexts:
                search_query["care_contexts"] = {"$in": care_contexts}
            
            # Execute text search
            cursor = self.mongo_database.therapeutic_content.find(search_query).limit(limit)
            results = await cursor.to_list(limit)
            
            # Add text score
            for result in results:
                result["combined_score"] = result.pop("score", 0.5)  # Default text score
            
            return {
                "source": "mongodb_therapeutic",
                "results": results,
                "count": len(results),
                "query_type": "text_search_fallback",
                "care_contexts": care_contexts
            }
            
        except Exception as e:
            logger.error(f"❌ MongoDB text fallback search failed: {e}")
            return {
                "source": "mongodb_therapeutic",
                "results": [],
                "count": 0,
                "error": str(e)
            }
    
    async def _postgres_knowledge_search(self, query: str, knowledge_type: str = "general",
                                       limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Search structured knowledge in PostgreSQL using pgvector"""
        self.routing_stats["postgres_queries"] += 1
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Convert embedding to PostgreSQL array format
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Use SQLAlchemy session for raw SQL
            async with self.postgres_manager.get_session() as session:
                # Search knowledge cards with vector similarity
                from sqlalchemy import text
                sql_query = text("""
                SELECT 
                    kc.kc_id,
                    kc.topic,
                    kc.do_list,
                    kc.dont_list,
                    kc.empathy_examples,
                    kc.action_examples,
                    kc.escalation_rules,
                    1 - (kc.embedding <=> :embedding_vec) as similarity
                FROM kb.knowledge_card kc
                WHERE 1 - (kc.embedding <=> :embedding_vec) > 0.7
                ORDER BY similarity DESC
                LIMIT :limit_val
                """)
                
                result = await session.execute(sql_query, {
                    "embedding_vec": embedding_str, 
                    "limit_val": limit
                })
                rows = result.fetchall()
                
                # Convert to dict format
                results = []
                for row in rows:
                    results.append({
                        "kc_id": str(row.kc_id),
                        "topic": row.topic,
                        "do_list": list(row.do_list) if row.do_list else [],
                        "dont_list": list(row.dont_list) if row.dont_list else [],
                        "empathy_examples": list(row.empathy_examples) if row.empathy_examples else [],
                        "action_examples": list(row.action_examples) if row.action_examples else [],
                        "escalation_rules": row.escalation_rules if row.escalation_rules else {},
                        "similarity": float(row.similarity)
                    })
                
                return {
                    "source": "postgres_knowledge",
                    "results": results,
                    "count": len(results),
                    "query_type": "pgvector_search",
                    "knowledge_type": knowledge_type
                }
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL knowledge search failed: {e}")
            return {"error": str(e), "source": "postgres_knowledge"}
    
    async def _postgres_crisis_lookup(self, risk_indicators: List[str], user_context: Dict[str, Any],
                                    **kwargs) -> Dict[str, Any]:
        """Look up crisis intervention scripts and policies in PostgreSQL"""
        try:
            async with self.postgres_manager.get_session() as session:
                from sqlalchemy import text
                # Find matching SAFE-T scripts
                sql_query = text("""
                SELECT 
                    ss.script_id,
                    ss.name,
                    ss.copy_md,
                    rt.pattern_regex,
                    rt.severity
                FROM policy.safet_script ss,
                     policy.risk_trigger rt
                WHERE rt.pattern_regex ~* :risk_pattern
                ORDER BY rt.severity DESC, ss.name
                LIMIT 5
                """)
                
                # Combine risk indicators into regex pattern
                risk_pattern = '|'.join(risk_indicators)
                result = await session.execute(sql_query, {"risk_pattern": risk_pattern})
                rows = result.fetchall()
                
                scripts = []
                for row in rows:
                    scripts.append({
                        "script_id": str(row['script_id']),
                        "name": row['name'],
                        "copy_md": row['copy_md'],
                        "pattern_regex": row['pattern_regex'],
                        "severity": row['severity']
                    })
                
                return {
                    "source": "postgres_crisis",
                    "scripts": scripts,
                    "count": len(scripts),
                    "risk_indicators": risk_indicators,
                    "user_context": user_context
                }
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL crisis lookup failed: {e}")
            return {"error": str(e), "source": "postgres_crisis"}
    
    async def _postgres_persona_query(self, persona_key: str, **kwargs) -> Dict[str, Any]:
        """Retrieve persona configuration from PostgreSQL"""
        try:
            async with self.postgres_manager.get_session() as session:
                # Get active persona version with all components
                sql = """
                SELECT 
                    p.persona_id,
                    p.key,
                    p.display_name,
                    pv.version_number,
                    pv.description,
                    pb.block_type,
                    pb.content,
                    pb.order_index,
                    sp.parameter_name,
                    sp.parameter_value
                FROM persona.persona p
                JOIN persona.persona_version pv ON p.active_version_id = pv.version_id
                LEFT JOIN persona.prompt_block pb ON pv.version_id = pb.version_id
                LEFT JOIN persona.style_parameter sp ON pv.version_id = sp.version_id
                WHERE p.key = %s AND p.is_active = true
                ORDER BY pb.order_index, sp.parameter_name
                """
                
                result = await session.execute(sql, (persona_key,))
                rows = result.fetchall()
                
                if not rows:
                    return {"error": "Persona not found", "persona_key": persona_key}
                
                # Build persona structure
                persona_data = {
                    "persona_id": str(rows[0].persona_id),
                    "key": rows[0].key,
                    "display_name": rows[0].display_name,
                    "version_number": rows[0].version_number,
                    "description": rows[0].description,
                    "prompt_blocks": [],
                    "style_parameters": {}
                }
                
                for row in rows:
                    if row.block_type and row.content:
                        persona_data["prompt_blocks"].append({
                            "type": row.block_type,
                            "content": row.content,
                            "order": row.order_index
                        })
                    
                    if row.parameter_name and row.parameter_value:
                        persona_data["style_parameters"][row.parameter_name] = row.parameter_value
                
                return {
                    "source": "postgres_persona",
                    "persona": persona_data,
                    "query_type": "persona_lookup"
                }
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL persona query failed: {e}")
            return {"error": str(e), "source": "postgres_persona"}
    
    async def _hybrid_therapeutic_search(self, query: str, user_id: str = None,
                                       care_contexts: List[str] = None, 
                                       limit: int = 20, **kwargs) -> Dict[str, Any]:
        """Execute hybrid search across MongoDB documents and PostgreSQL knowledge"""
        self.routing_stats["hybrid_queries"] += 1
        
        try:
            # Execute searches in parallel
            tasks = []
            
            # MongoDB therapeutic document search
            tasks.append(self._mongodb_therapeutic_search(
                query=query, 
                care_contexts=care_contexts, 
                limit=limit//2
            ))
            
            # PostgreSQL knowledge card search
            tasks.append(self._postgres_knowledge_search(
                query=query,
                limit=limit//2
            ))
            
            # Execute in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            mongodb_results = results[0] if not isinstance(results[0], Exception) else {"results": []}
            postgres_results = results[1] if not isinstance(results[1], Exception) else {"results": []}
            
            # Merge and re-rank results
            combined_results = self._merge_therapeutic_results(
                mongodb_results.get("results", []),
                postgres_results.get("results", [])
            )
            
            return {
                "source": "hybrid_therapeutic",
                "results": combined_results[:limit],
                "count": len(combined_results[:limit]),
                "mongodb_count": len(mongodb_results.get("results", [])),
                "postgres_count": len(postgres_results.get("results", [])),
                "care_contexts": care_contexts,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"❌ Hybrid therapeutic search failed: {e}")
            return {"error": str(e), "source": "hybrid_therapeutic"}
    
    def _merge_therapeutic_results(self, mongodb_results: List[Dict], 
                                 postgres_results: List[Dict]) -> List[Dict]:
        """Merge and re-rank MongoDB and PostgreSQL results for therapeutic context"""
        merged_results = []
        
        # Process MongoDB results
        for result in mongodb_results:
            merged_results.append({
                **result,
                "source_db": "mongodb",
                "result_type": "therapeutic_document",
                "combined_score": result.get("combined_score", result.get("vector_score", 0))
            })
        
        # Process PostgreSQL results
        for result in postgres_results:
            merged_results.append({
                **result,
                "source_db": "postgres",
                "result_type": "knowledge_card",
                "combined_score": result.get("similarity", 0)
            })
        
        # Sort by combined score
        merged_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        return merged_results
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using the BGE service"""
        try:
            async with self.embedding_session.post(
                "http://localhost:8005/embeddings",
                json={"texts": [text]}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["embeddings"][0]
                else:
                    raise Exception(f"Embedding service error: {response.status}")
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}")
            # Return zero vector as fallback
            return [0.0] * 1024
    
    async def _postgres_auth_query(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Placeholder for user authentication queries"""
        return {"source": "postgres_auth", "user_id": user_id, "authenticated": True}
    
    async def _mongodb_context_search(self, context: str, **kwargs) -> Dict[str, Any]:
        """Placeholder for MongoDB context-specific searches"""
        return {"source": "mongodb_context", "context": context}
    
    async def _postgres_conversation_history(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """Placeholder for conversation history retrieval"""
        return {"source": "postgres_history", "user_id": user_id}
    
    async def _cache_lookup(self, query: str, user_context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Intelligent therapeutic cache lookup with multi-tier support"""
        if not self.cache_manager:
            return {"source": "cache", "hit": False, "reason": "cache_manager_not_initialized"}
        
        try:
            # Get cached response using therapeutic context
            cached_response = await self.cache_manager.get_cached_response(
                query=query,
                user_context=user_context or {},
                care_contexts=kwargs.get("care_contexts", ["general"])
            )
            
            if cached_response:
                self.routing_stats["cache_hits"] += 1
                logger.info(f"🎯 Cache HIT for query: {query[:50]}...")
                return {
                    "source": "therapeutic_cache",
                    "hit": True,
                    "cache_level": cached_response.get("cache_level", "unknown"),
                    "response_data": cached_response,
                    "cached_at": cached_response.get("cached_at"),
                    "ttl_remaining": cached_response.get("ttl_remaining_hours")
                }
            else:
                logger.info(f"🔍 Cache MISS for query: {query[:50]}...")
                return {
                    "source": "therapeutic_cache", 
                    "hit": False,
                    "reason": "no_matching_cache_entry",
                    "should_cache_result": True
                }
                
        except Exception as e:
            logger.error(f"❌ Cache lookup error: {e}")
            return {
                "source": "cache_error",
                "hit": False,
                "error": str(e),
                "should_cache_result": False
            }
    
    async def cache_query_result(self, query: str, result_data: Dict[str, Any], 
                                user_context: Dict[str, Any] = None, **kwargs) -> bool:
        """Cache a successful query result for future use"""
        if not self.cache_manager:
            return False
            
        try:
            await self.cache_manager.set_cached_response(
                query=query,
                response_data=result_data,
                user_context=user_context or {},
                care_contexts=kwargs.get("care_contexts", ["general"]),
                ttl_hours=kwargs.get("ttl_hours", 12)
            )
            logger.info(f"💾 Cached result for query: {query[:50]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cache result: {e}")
            return False
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing performance statistics with cache insights"""
        base_stats = {
            **self.routing_stats,
            "cache_hit_rate": (
                self.routing_stats["cache_hits"] / max(self.routing_stats["total_queries"], 1)
            ),
            "hybrid_query_rate": (
                self.routing_stats["hybrid_queries"] / max(self.routing_stats["total_queries"], 1)
            )
        }
        
        # Add therapeutic cache statistics if available
        if self.cache_manager:
            try:
                cache_stats = self.cache_manager.get_cache_stats()
                base_stats["cache_details"] = {
                    "multi_tier_cache": True,
                    "l1_cache_size": len(self.cache_manager.l1_cache),
                    "total_cache_requests": cache_stats["total_requests"],
                    "l1_hit_rate": cache_stats.get("l1_hit_rate", 0.0),
                    "l2_hit_rate": cache_stats.get("l2_hit_rate", 0.0),
                    "l3_hit_rate": cache_stats.get("l3_hit_rate", 0.0),
                    "cache_performance": cache_stats.get("performance_metrics", {})
                }
            except Exception as e:
                logger.error(f"Failed to get cache stats: {e}")
                base_stats["cache_details"] = {"error": "cache_stats_unavailable"}
        
        return base_stats
    
    async def cleanup(self):
        """Clean up connections and resources"""
        if self.embedding_session:
            await self.embedding_session.close()
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("✅ Intelligent therapeutic router cleanup completed")

# Global router instance
_router_instance = None

async def get_therapeutic_router() -> IntelligentTherapeuticRouter:
    """Get the global therapeutic router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = IntelligentTherapeuticRouter()
        await _router_instance.initialize()
    return _router_instance