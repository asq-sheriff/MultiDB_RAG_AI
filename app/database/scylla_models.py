import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncio

from app.database.scylla_connection import ScyllaDBConnection

logger = logging.getLogger(__name__)

CHATBOT_KEYSPACE = "chatbot_ks"


@dataclass
class ConversationMessage:
    """Individual conversation message"""

    session_id: uuid.UUID
    actor: str
    message: str
    timestamp: datetime
    message_id: Optional[uuid.UUID] = None
    confidence: Optional[float] = None
    cached: Optional[bool] = None
    response_time_ms: Optional[int] = None
    route_used: Optional[str] = None
    generation_used: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UserFeedback:
    """User feedback entry"""

    feedback_id: uuid.UUID
    user_id: str
    session_id: uuid.UUID
    feedback_message: str
    timestamp: datetime
    rating: Optional[int] = None
    sentiment_score: Optional[float] = None
    feedback_type: Optional[str] = None


@dataclass
class KnowledgeEntry:
    """Knowledge base entry"""

    category: str
    question_hash: str
    question: str
    answer: str
    confidence: float
    usage_count: int
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime] = None
    embedding_model: Optional[str] = None


class EnhancedConversationHistory:
    """ScyllaDB conversation history storage"""

    def __init__(self):
        self.connection = ScyllaDBConnection()
        self.keyspace = CHATBOT_KEYSPACE
        self._ensure_connection()
        self._ensure_tables()

    def _ensure_connection(self) -> None:
        """Ensure ScyllaDB connection"""
        try:
            if not self.connection.is_connected():
                self.connection.connect()
                self.connection.ensure_keyspace(self.keyspace)
        except Exception as e:
            logger.error(f"Failed to connect to ScyllaDB: {e}")
            logger.warning("ScyllaDB operations will gracefully degrade to no-ops")

    def _ensure_tables(self) -> None:
        """Create conversation history tables"""
        if not self.connection.is_connected():
            return

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            create_table_cql = f"""
                CREATE TABLE IF NOT EXISTS {self.keyspace}.conversation_history (
                    session_id UUID,
                    timestamp TIMESTAMP,
                    message_id UUID,
                    actor TEXT,
                    message TEXT,
                    confidence DOUBLE,
                    cached BOOLEAN,
                    response_time_ms INT,
                    route_used TEXT,
                    generation_used BOOLEAN,
                    embedding_model TEXT,
                    metadata MAP<TEXT, TEXT>,
                    PRIMARY KEY (session_id, timestamp)
                ) WITH CLUSTERING ORDER BY (timestamp DESC)
                AND gc_grace_seconds = 864000;
            """
            session.execute(create_table_cql)

            create_summary_cql = f"""
                CREATE TABLE IF NOT EXISTS {self.keyspace}.conversation_summary (
                    session_id UUID,
                    user_id TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    message_count INT,
                    total_response_time_ms BIGINT,
                    avg_confidence DOUBLE,
                    routes_used SET<TEXT>,
                    generation_count INT,
                    cache_hit_rate DOUBLE,
                    PRIMARY KEY (session_id)
                );
            """
            session.execute(create_summary_cql)

            logger.debug("Conversation history tables ensured")

        except Exception as e:
            logger.error(f"Failed to ensure conversation history tables: {e}")

    async def save_message(
        self,
        session_id: uuid.UUID,
        actor: str,
        message: str,
        confidence: Optional[float] = None,
        cached: Optional[bool] = None,
        response_time_ms: Optional[int] = None,
        route_used: Optional[str] = None,
        generation_used: Optional[bool] = None,
        embedding_model: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> uuid.UUID:
        """Save message to conversation history"""
        if not self.connection.is_connected():
            logger.warning("ScyllaDB not connected, message not saved")
            return uuid.uuid4()

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            message_id = uuid.uuid4()
            timestamp = datetime.now(timezone.utc)

            insert_cql = f"""
                INSERT INTO {self.keyspace}.conversation_history (
                    session_id, timestamp, message_id, actor, message, 
                    confidence, cached, response_time_ms, route_used, 
                    generation_used, embedding_model, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            metadata_map = {}
            if metadata:
                metadata_map = {k: str(v) for k, v in metadata.items()}

            session.execute(
                insert_cql,
                (
                    session_id,
                    timestamp,
                    message_id,
                    actor,
                    message,
                    confidence,
                    cached,
                    response_time_ms,
                    route_used,
                    generation_used,
                    embedding_model,
                    metadata_map,
                ),
            )

            asyncio.create_task(
                self._update_conversation_summary(
                    session_id,
                    actor,
                    response_time_ms,
                    confidence,
                    route_used,
                    generation_used,
                )
            )

            logger.debug(f"Message saved: {message_id} for session {session_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return uuid.uuid4()

    async def _update_conversation_summary(
        self,
        session_id: uuid.UUID,
        actor: str,
        response_time_ms: Optional[int],
        confidence: Optional[float],
        route_used: Optional[str],
        generation_used: Optional[bool],
    ) -> None:
        """Update conversation summary statistics"""
        if not self.connection.is_connected():
            return

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            update_cql = f"""
                UPDATE {self.keyspace}.conversation_summary
                SET 
                    message_count = message_count + 1,
                    end_time = ?,
                    total_response_time_ms = total_response_time_ms + ?,
                    routes_used = routes_used + ?,
                    generation_count = generation_count + ?
                WHERE session_id = ?
            """

            routes_set = {route_used} if route_used else set()
            generation_increment = 1 if generation_used else 0
            response_time = response_time_ms or 0

            session.execute(
                update_cql,
                (
                    datetime.now(timezone.utc),
                    response_time,
                    routes_set,
                    generation_increment,
                    session_id,
                ),
            )

        except Exception as e:
            logger.debug(f"Failed to update conversation summary: {e}")

    def get_session_history(
        self,
        session_id: uuid.UUID,
        limit: int = 50,
        start_time: Optional[datetime] = None,
    ) -> List[ConversationMessage]:
        """Get conversation history for a session"""
        if not self.connection.is_connected():
            logger.warning("ScyllaDB not connected, returning empty history")
            return []

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            if start_time:
                select_cql = f"""
                    SELECT session_id, timestamp, message_id, actor, message, 
                           confidence, cached, response_time_ms, route_used,
                           generation_used, embedding_model, metadata
                    FROM {self.keyspace}.conversation_history
                    WHERE session_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """
                rows = session.execute(select_cql, (session_id, start_time, limit))
            else:
                select_cql = f"""
                    SELECT session_id, timestamp, message_id, actor, message,
                           confidence, cached, response_time_ms, route_used,
                           generation_used, embedding_model, metadata
                    FROM {self.keyspace}.conversation_history
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """
                rows = session.execute(select_cql, (session_id, limit))

            messages = []
            for row in rows:
                message = ConversationMessage(
                    session_id=row.session_id,
                    timestamp=row.timestamp,
                    message_id=row.message_id,
                    actor=row.actor,
                    message=row.message,
                    confidence=row.confidence,
                    cached=row.cached,
                    response_time_ms=row.response_time_ms,
                    route_used=row.route_used,
                    generation_used=row.generation_used,
                    metadata=dict(row.metadata) if row.metadata else None,
                )
                messages.append(message)

            messages.reverse()
            logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            return []

    def get_conversation_analytics(
        self, session_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get conversation analytics"""
        if not self.connection.is_connected():
            return None

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            summary_cql = f"""
                SELECT session_id, user_id, start_time, end_time, message_count,
                       total_response_time_ms, avg_confidence, routes_used, 
                       generation_count, cache_hit_rate
                FROM {self.keyspace}.conversation_summary
                WHERE session_id = ?
            """
            summary_result = session.execute(summary_cql, (session_id,))
            summary_row = summary_result.one()

            if not summary_row:
                return None

            avg_response_time = (
                summary_row.total_response_time_ms / summary_row.message_count
                if summary_row.message_count > 0
                else 0
            )

            generation_rate = (
                summary_row.generation_count / summary_row.message_count
                if summary_row.message_count > 0
                else 0
            )

            return {
                "session_id": str(summary_row.session_id),
                "user_id": summary_row.user_id,
                "start_time": summary_row.start_time.isoformat()
                if summary_row.start_time
                else None,
                "end_time": summary_row.end_time.isoformat()
                if summary_row.end_time
                else None,
                "message_count": summary_row.message_count,
                "avg_response_time_ms": avg_response_time,
                "avg_confidence": summary_row.avg_confidence,
                "routes_used": list(summary_row.routes_used)
                if summary_row.routes_used
                else [],
                "generation_rate": generation_rate,
                "cache_hit_rate": summary_row.cache_hit_rate,
                "real_ai_usage": generation_rate > 0,
            }

        except Exception as e:
            logger.error(f"Failed to get conversation analytics: {e}")
            return None

    def delete_session(self, session_id: uuid.UUID) -> bool:
        """Delete all messages for a session"""
        if not self.connection.is_connected():
            logger.warning("ScyllaDB not connected, session not deleted")
            return False

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            delete_history_cql = (
                f"DELETE FROM {self.keyspace}.conversation_history WHERE session_id = ?"
            )
            session.execute(delete_history_cql, (session_id,))

            delete_summary_cql = (
                f"DELETE FROM {self.keyspace}.conversation_summary WHERE session_id = ?"
            )
            session.execute(delete_summary_cql, (session_id,))

            logger.info(f"Session deleted: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False


class EnhancedUserFeedbackRepository:
    """ScyllaDB user feedback storage"""

    def __init__(self):
        self.connection = ScyllaDBConnection()
        self.keyspace = CHATBOT_KEYSPACE
        self._ensure_connection()
        self._ensure_tables()

    def _ensure_connection(self) -> None:
        """Ensure ScyllaDB connection"""
        try:
            if not self.connection.is_connected():
                self.connection.connect()
                self.connection.ensure_keyspace(self.keyspace)
        except Exception as e:
            logger.error(f"Failed to connect to ScyllaDB: {e}")

    def _ensure_tables(self) -> None:
        """Create user feedback table"""
        if not self.connection.is_connected():
            return

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            create_table_cql = f"""
                CREATE TABLE IF NOT EXISTS {self.keyspace}.user_feedback (
                    user_id TEXT,
                    timestamp TIMESTAMP,
                    feedback_id UUID,
                    session_id UUID,
                    feedback_message TEXT,
                    rating INT,
                    sentiment_score DOUBLE,
                    feedback_type TEXT,
                    route_related TEXT,
                    generation_related BOOLEAN,
                    processed BOOLEAN,
                    PRIMARY KEY (user_id, timestamp)
                ) WITH CLUSTERING ORDER BY (timestamp DESC);
            """
            session.execute(create_table_cql)

            logger.debug("User feedback tables ensured")

        except Exception as e:
            logger.error(f"Failed to ensure user feedback tables: {e}")


class EnhancedKnowledgeBase:
    """ScyllaDB knowledge base storage"""

    def __init__(self):
        self.connection = ScyllaDBConnection()
        self.keyspace = CHATBOT_KEYSPACE
        self._ensure_connection()
        self._ensure_tables()

    def _ensure_connection(self) -> None:
        """Ensure ScyllaDB connection"""
        try:
            if not self.connection.is_connected():
                self.connection.connect()
                self.connection.ensure_keyspace(self.keyspace)
        except Exception as e:
            logger.error(f"Failed to connect to ScyllaDB: {e}")

    def _ensure_tables(self) -> None:
        """Create knowledge base table"""
        if not self.connection.is_connected():
            return

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            create_table_cql = f"""
                CREATE TABLE IF NOT EXISTS {self.keyspace}.knowledge_base (
                    category TEXT,
                    question_hash TEXT,
                    question TEXT,
                    answer TEXT,
                    confidence DOUBLE,
                    usage_count COUNTER,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    last_accessed TIMESTAMP,
                    embedding_model TEXT,
                    source_type TEXT,
                    version INT,
                    PRIMARY KEY (category, question_hash)
                );
            """
            session.execute(create_table_cql)

            logger.debug("Knowledge base tables ensured")

        except Exception as e:
            logger.error(f"Failed to ensure knowledge base tables: {e}")

    async def get_faq_seed_rows(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get FAQ rows for seeding MongoDB"""
        if not self.connection.is_connected():
            sample_faqs = [
                {
                    "scylla_key": "faq:reset_password_v2",
                    "question": "How do I reset my password with the new AI assistant?",
                    "answer": "Go to Settings → Security → Reset Password and follow the AI-guided instructions. The assistant will help you through each step.",
                    "updated_at": "2025-08-12T12:00:00Z",
                    "version": 2,
                    "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                },
                {
                    "scylla_key": "faq:contact_support_ai",
                    "question": "How do I contact support using the AI features?",
                    "answer": "You can reach our support team via the AI chat interface, email at support@company.com, or through the intelligent help desk that routes your query automatically.",
                    "updated_at": "2025-08-12T12:00:00Z",
                    "version": 2,
                    "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                },
                {
                    "scylla_key": "faq:ai_features",
                    "question": "What AI features are available in the application?",
                    "answer": "Our application includes semantic search, intelligent routing, real-time text generation, and contextual responses using advanced language models.",
                    "updated_at": "2025-08-12T12:00:00Z",
                    "version": 1,
                    "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                },
                {
                    "scylla_key": "faq:vector_search",
                    "question": "How does the semantic search work?",
                    "answer": "Our semantic search uses sentence-transformers/all-mpnet-base-v2 embeddings and MongoDB Atlas Vector Search to find relevant information based on meaning, not just keywords.",
                    "updated_at": "2025-08-12T12:00:00Z",
                    "version": 1,
                    "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                },
            ]

            if limit is not None and limit > 0:
                return sample_faqs[:limit]
            return sample_faqs

        try:
            session = self.connection.get_session()
            session.execute(f"USE {self.keyspace}")

            select_cql = f"""
                SELECT category, question_hash, question, answer, 
                       updated_at, version, embedding_model
                FROM {self.keyspace}.knowledge_base
            """

            if limit:
                select_cql += f" LIMIT {limit}"

            rows = session.execute(select_cql)

            faq_rows = []
            for row in rows:
                faq_row = {
                    "scylla_key": f"faq:{row.question_hash}",
                    "question": row.question,
                    "answer": row.answer,
                    "updated_at": row.updated_at.isoformat()
                    if row.updated_at
                    else None,
                    "version": getattr(row, "version", 1),
                    "embedding_model": row.embedding_model,
                }
                faq_rows.append(faq_row)

            return faq_rows

        except Exception as e:
            logger.error(f"Failed to get FAQ seed rows: {e}")
            return []


ConversationHistory = EnhancedConversationHistory
UserFeedbackRepository = EnhancedUserFeedbackRepository
KnowledgeBase = EnhancedKnowledgeBase
