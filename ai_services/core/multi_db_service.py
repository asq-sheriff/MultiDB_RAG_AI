"""
Multi-Database Service
======================

Simplified data coordination service that focuses only on data operations.
Auth, billing, and user management are handled by Go microservices.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging

from data_layer.models.redis.redis_models import CacheModel, SessionModel, AnalyticsModel
from data_layer.models.scylla.scylla_models import ConversationHistory

logger = logging.getLogger(__name__)


class MultiDatabaseService:
    """Coordinates data operations across Redis and ScyllaDB only."""

    def __init__(self):
        # Database connections (no auth/billing - handled by Go services)
        self.cache_model = CacheModel()
        self.session_model = SessionModel()
        self.analytics_model = AnalyticsModel()
        self.conversation_history = ConversationHistory()

    async def store_conversation(
        self, session_id: str, user_message: str, bot_response: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store conversation in ScyllaDB and update Redis session."""
        
        # Store user message in ScyllaDB
        try:
            user_item = await self.conversation_history.add_conversation_item(
                session_id=session_id,
                actor="user",
                message_id=str(uuid.uuid4()),
                text_content=user_message,
                service_context="conversation_storage",
                user_id=user_id,
                metadata={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info(f"💬 User message stored: {user_item.message_id}")
        except Exception as e:
            logger.warning(f"📂 Failed to store user message in ScyllaDB: {e}")

        # Store bot response in ScyllaDB
        try:
            bot_item = await self.conversation_history.add_conversation_item(
                session_id=session_id,
                actor="bot",
                message_id=str(uuid.uuid4()),
                text_content=bot_response,
                service_context="conversation_storage",
                user_id=user_id,
                metadata={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info(f"🤖 Bot response stored: {bot_item.message_id}")
        except Exception as e:
            logger.warning(f"📂 Failed to store bot response in ScyllaDB: {e}")

        # Update Redis session history
        try:
            self.session_model.add_to_chat_history(
                session_id, {"actor": "user", "message": user_message}
            )
            self.session_model.add_to_chat_history(
                session_id, {"actor": "bot", "message": bot_response}
            )
            logger.info(f"📋 Session {session_id} updated in Redis")
        except Exception as e:
            logger.warning(f"📋 Failed to update session in Redis: {e}")

        return {
            "status": "stored",
            "session_id": session_id,
            "user_message_id": user_item.message_id if 'user_item' in locals() else None,
            "bot_message_id": bot_item.message_id if 'bot_item' in locals() else None,
        }

    async def get_conversation_history(
        self, session_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history from ScyllaDB."""
        try:
            history = await self.conversation_history.get_conversation_history(
                session_id=session_id,
                limit=limit
            )
            
            return [
                {
                    "message_id": item.message_id,
                    "actor": item.actor,
                    "content": item.text_content,
                    "timestamp": item.created_at.isoformat() if item.created_at else None,
                    "metadata": item.metadata or {}
                }
                for item in history
            ]
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    async def cache_user_preferences(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> bool:
        """Cache user preferences in Redis."""
        try:
            await self.cache_model.set_user_cache(user_id, "preferences", preferences)
            logger.info(f"📋 User preferences cached for {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache user preferences: {e}")
            return False

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user preferences from Redis."""
        try:
            return await self.cache_model.get_user_cache(user_id, "preferences")
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return None


# Utility functions for data processing
def _norm_txt(s: Optional[str]) -> str:
    return (s or "").strip()


def _to_iso(dt) -> Optional[str]:
    try:
        # Accept str, datetime, or anything with isoformat()
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        if isinstance(dt, str):
            return dt
    except Exception:
        pass
    return None