"""
Semantic Conversation Search Service
Enables semantic search across conversation history using query embeddings
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import text, select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from data_layer.connections.postgres_connection import PostgreSQLConnectionManager
from data_layer.models.postgres.postgres_models import QueryEmbedding, ConversationAnalytics
from data_layer.connections.scylla_connection import ScyllaDBConnection

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single conversation turn from ScyllaDB"""
    message_id: str
    actor: str  # 'user' or 'assistant'
    message: str
    timestamp: datetime
    confidence: Optional[float] = None
    route_used: Optional[str] = None


@dataclass
class ConversationMatch:
    """Semantic match between current query and past conversation"""
    similarity_score: float
    matched_query: str
    session_id: str
    conversation_context: List[ConversationTurn]
    timestamp: datetime
    query_id: str
    response_quality: Optional[float] = None


class SemanticConversationSearch:
    """Search past conversations using query embedding similarity"""
    
    def __init__(self):
        self.pg_manager = PostgreSQLConnectionManager()
        self.scylla_connection = ScyllaDBConnection()
        
    async def initialize(self):
        """Initialize database connections"""
        await self.pg_manager.initialize()
        self.scylla_connection.connect()
        
    async def cleanup(self):
        """Cleanup database connections"""
        if self.scylla_connection.is_connected():
            self.scylla_connection.disconnect()
            
    async def store_query_embedding(
        self,
        user_id: str,
        session_id: str, 
        query_text: str,
        query_embedding: List[float],
        conversation_turn: Optional[int] = None,
        followup_to_query_id: Optional[str] = None,
        search_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store query embedding with conversation context"""
        
        try:
            async with self.pg_manager.get_session() as session:
                query_record = QueryEmbedding(
                    user_id=uuid.UUID(user_id),
                    session_id=uuid.UUID(session_id),
                    query_text=query_text,
                    query_embedding=query_embedding,
                    conversation_turn=conversation_turn,
                    followup_to_query_id=uuid.UUID(followup_to_query_id) if followup_to_query_id else None,
                    
                    # Store search metrics if provided
                    search_results_count=search_metrics.get('results_count') if search_metrics else None,
                    avg_similarity_score=search_metrics.get('avg_score') if search_metrics else None,
                    route_used=search_metrics.get('route') if search_metrics else None,
                    response_quality_score=search_metrics.get('quality_score') if search_metrics else None,
                    processing_time_ms=search_metrics.get('processing_time_ms') if search_metrics else None,
                )
                
                session.add(query_record)
                await session.commit()
                await session.refresh(query_record)
                
                logger.info(f"Stored query embedding for user {user_id}, query: {query_text[:50]}...")
                return str(query_record.query_id)
                
        except Exception as e:
            logger.error(f"Failed to store query embedding: {e}")
            raise

    async def find_similar_conversations(
        self,
        current_query: str,
        current_query_embedding: List[float],
        user_id: str,
        similarity_threshold: float = 0.75,
        time_window_days: int = 30,
        max_results: int = 5,
        exclude_current_session: Optional[str] = None
    ) -> List[ConversationMatch]:
        """Find semantically similar past conversations"""
        
        try:
            async with self.pg_manager.get_session() as session:
                # Build similarity search query
                similarity_query = text("""
                SELECT 
                    qe.query_id,
                    qe.session_id,
                    qe.query_text,
                    qe.query_embedding <=> CAST(:query_embedding AS vector) as similarity_distance,
                    1 - (qe.query_embedding <=> CAST(:query_embedding AS vector)) as similarity_score,
                    qe.timestamp,
                    qe.conversation_turn,
                    qe.response_quality_score,
                    qe.route_used
                FROM query_embeddings qe
                WHERE qe.user_id = CAST(:user_id AS uuid)
                AND qe.timestamp > NOW() - INTERVAL '30 days'
                AND qe.query_embedding <=> CAST(:query_embedding AS vector) < :distance_threshold
                AND (CAST(:exclude_session AS text) IS NULL OR qe.session_id::text != CAST(:exclude_session AS text))
                ORDER BY similarity_distance ASC
                LIMIT :max_results
                """)
                
                result = await session.execute(similarity_query, {
                    'query_embedding': current_query_embedding,
                    'user_id': user_id,
                    'time_window': time_window_days,
                    'distance_threshold': 1 - similarity_threshold,  # Convert to distance
                    'exclude_session': exclude_current_session,
                    'max_results': max_results
                })
                
                similar_queries = result.fetchall()
                
                if not similar_queries:
                    logger.info(f"No similar conversations found for user {user_id}")
                    return []
                
                # Retrieve full conversations from ScyllaDB
                conversation_matches = []
                
                for query_row in similar_queries:
                    conversation_context = await self._get_conversation_from_scylla(
                        session_id=str(query_row.session_id),
                        around_turn=query_row.conversation_turn
                    )
                    
                    match = ConversationMatch(
                        similarity_score=query_row.similarity_score,
                        matched_query=query_row.query_text,
                        session_id=str(query_row.session_id),
                        conversation_context=conversation_context,
                        timestamp=query_row.timestamp,
                        query_id=str(query_row.query_id),
                        response_quality=query_row.response_quality_score
                    )
                    
                    conversation_matches.append(match)
                
                logger.info(f"Found {len(conversation_matches)} similar conversations for user {user_id}")
                return conversation_matches
                
        except Exception as e:
            logger.error(f"Semantic conversation search failed: {e}")
            return []

    async def _get_conversation_from_scylla(
        self, 
        session_id: str, 
        around_turn: Optional[int] = None,
        context_window: int = 5
    ) -> List[ConversationTurn]:
        """Retrieve conversation context from ScyllaDB"""
        
        try:
            if not self.scylla_connection.is_connected():
                self.scylla_connection.connect()
                
            session = self.scylla_connection.get_session()
            session.execute("USE chatbot_ks")
            
            # Get conversation messages
            if around_turn is not None:
                # Get messages around specific turn
                query = """
                SELECT message_id, actor, message, timestamp, confidence, route_used
                FROM conversation_history 
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """
            else:
                # Get entire conversation
                query = """
                SELECT message_id, actor, message, timestamp, confidence, route_used
                FROM conversation_history 
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """
            
            if around_turn is not None:
                result = session.execute(query, [uuid.UUID(session_id)])
            else:
                result = session.execute(query, [uuid.UUID(session_id), context_window * 2])
            
            conversation_turns = []
            for row in result:
                turn = ConversationTurn(
                    message_id=str(row.message_id),
                    actor=row.actor,
                    message=row.message,
                    timestamp=row.timestamp,
                    confidence=row.confidence,
                    route_used=row.route_used
                )
                conversation_turns.append(turn)
            
            logger.debug(f"Retrieved {len(conversation_turns)} conversation turns for session {session_id}")
            return conversation_turns
            
        except Exception as e:
            logger.error(f"Failed to retrieve conversation from ScyllaDB: {e}")
            return []

    async def find_user_query_patterns(
        self,
        user_id: str,
        days_lookback: int = 30,
        min_cluster_size: int = 3
    ) -> List[Dict[str, Any]]:
        """Analyze user's query patterns for personalization"""
        
        try:
            async with self.pg_manager.get_session() as session:
                # Get user's recent queries with their embeddings
                pattern_query = text("""
                SELECT 
                    qe.query_text,
                    qe.query_embedding,
                    qe.route_used,
                    qe.response_quality_score,
                    qe.avg_similarity_score,
                    qe.timestamp
                FROM query_embeddings qe
                WHERE qe.user_id = CAST(:user_id AS uuid)
                AND qe.timestamp > NOW() - INTERVAL '30 days'
                ORDER BY qe.timestamp DESC
                """)
                
                result = await session.execute(pattern_query, {
                    'user_id': user_id,
                    'days': days_lookback
                })
                
                queries = result.fetchall()
                
                if len(queries) < min_cluster_size:
                    logger.info(f"Insufficient query history for pattern analysis: {len(queries)} queries")
                    return []
                
                # Simple clustering by topic similarity
                patterns = []
                processed_queries = set()
                
                for i, query in enumerate(queries):
                    if i in processed_queries:
                        continue
                        
                    cluster = [query]
                    cluster_embedding = query.query_embedding
                    
                    # Find similar queries
                    for j, other_query in enumerate(queries[i+1:], start=i+1):
                        if j in processed_queries:
                            continue
                            
                        # Calculate similarity (simplified - would use proper clustering in production)
                        similarity = await self._calculate_embedding_similarity(
                            cluster_embedding, other_query.query_embedding
                        )
                        
                        if similarity > 0.8:  # High similarity threshold
                            cluster.append(other_query)
                            processed_queries.add(j)
                    
                    if len(cluster) >= min_cluster_size:
                        patterns.append({
                            'cluster_size': len(cluster),
                            'representative_query': cluster[0].query_text,
                            'avg_quality_score': sum(q.response_quality_score or 0 for q in cluster) / len(cluster),
                            'common_routes': list(set(q.route_used for q in cluster if q.route_used)),
                            'frequency': len(cluster),
                            'last_seen': max(q.timestamp for q in cluster)
                        })
                
                logger.info(f"Identified {len(patterns)} query patterns for user {user_id}")
                return patterns
                
        except Exception as e:
            logger.error(f"Query pattern analysis failed: {e}")
            return []

    async def _calculate_embedding_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        try:
            # Use numpy if available for efficiency
            import numpy as np
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
            
        except ImportError:
            # Fallback to pure Python
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            norm1 = sum(a * a for a in embedding1) ** 0.5
            norm2 = sum(b * b for b in embedding2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)

    async def enhance_query_with_conversation_context(
        self, 
        current_query: str,
        current_query_embedding: List[float], 
        user_id: str,
        session_id: str,
        similarity_threshold: float = 0.8
    ) -> Tuple[str, List[ConversationMatch]]:
        """Enhance current query with semantically similar conversation context"""
        
        try:
            # Find similar past conversations
            similar_conversations = await self.find_similar_conversations(
                current_query=current_query,
                current_query_embedding=current_query_embedding,
                user_id=user_id,
                similarity_threshold=similarity_threshold,
                time_window_days=7,  # Recent context
                max_results=3,
                exclude_current_session=session_id
            )
            
            if not similar_conversations:
                return current_query, []
            
            # Build enhanced query with context
            context_queries = [match.matched_query for match in similar_conversations[:2]]
            enhanced_query = f"Previous related topics: {'; '.join(context_queries)}. Current question: {current_query}"
            
            logger.info(f"Enhanced query with {len(similar_conversations)} conversation matches")
            return enhanced_query, similar_conversations
            
        except Exception as e:
            logger.error(f"Query enhancement failed: {e}")
            return current_query, []

    async def _update_query_metrics(self, query_id: str, search_metrics: Dict[str, Any]):
        """Update stored query embedding with search performance metrics"""
        
        try:
            async with self.pg_manager.get_session() as session:
                update_query = text("""
                UPDATE query_embeddings
                SET 
                    search_results_count = :results_count,
                    avg_similarity_score = :avg_score,
                    route_used = :route,
                    response_quality_score = :quality_score,
                    processing_time_ms = :processing_time_ms
                WHERE query_id = :query_id
                """)
                
                await session.execute(update_query, {
                    'query_id': query_id,
                    'results_count': search_metrics.get('results_count'),
                    'avg_score': search_metrics.get('avg_score'),
                    'route': search_metrics.get('route'),
                    'quality_score': search_metrics.get('quality_score'),
                    'processing_time_ms': search_metrics.get('processing_time_ms')
                })
                
                await session.commit()
                logger.debug(f"Updated query metrics for query {query_id}")
                
        except Exception as e:
            logger.error(f"Failed to update query metrics: {e}")


# Global instance for dependency injection
semantic_conversation_search = SemanticConversationSearch()