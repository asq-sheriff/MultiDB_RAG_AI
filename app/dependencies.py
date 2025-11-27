"""Application dependencies and service initialization"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService
    from app.services.generation_service import GenerationService
    from app.services.knowledge_service import KnowledgeService
    from app.services.chatbot_service import ChatbotService
    from app.services.billing_service import EnhancedBillingService
    from app.services.auth_service import AuthService
    from app.services.user_service import UserService
    from app.services.multi_db_service import MultiDatabaseService
    from app.database.scylla_connection import ScyllaDBConnection

embedding_service: Optional["EmbeddingService"] = None
generation_service: Optional["GenerationService"] = None
knowledge_service: Optional["KnowledgeService"] = None
chatbot_service: Optional["ChatbotService"] = None
billing_service: Optional["EnhancedBillingService"] = None
auth_service: Optional["AuthService"] = None
user_service: Optional["UserService"] = None
multi_db_service: Optional["MultiDatabaseService"] = None
scylla_manager: Optional["ScyllaDBConnection"] = None

postgres_manager: Optional[AsyncSession] = None

logger = logging.getLogger(__name__)


def get_embedding_service() -> "EmbeddingService":
    """Get or create embedding service instance"""
    global embedding_service
    if embedding_service is None:
        try:
            from app.services.embedding_service import EmbeddingService

            embedding_service = EmbeddingService()
            logger.info("Created EmbeddingService instance")
        except Exception as e:
            logger.error(f"Failed to create EmbeddingService: {e}")
            embedding_service = MockEmbeddingService()
    return embedding_service


def get_generation_service() -> "GenerationService":
    """Get or create generation service instance"""
    global generation_service
    if generation_service is None:
        try:
            from app.services.generation_service import GenerationService

            generation_service = GenerationService()
            logger.info("Created GenerationService instance")
        except Exception as e:
            logger.error(f"Failed to create GenerationService: {e}")
            generation_service = MockGenerationService()
    return generation_service


def get_knowledge_service() -> "KnowledgeService":
    """Get or create knowledge service instance"""
    global knowledge_service
    if knowledge_service is None:
        try:
            from app.services.knowledge_service import KnowledgeService

            embedder = get_embedding_service()
            if hasattr(embedder, "embed_query"):
                knowledge_service = KnowledgeService(
                    query_embedder=embedder.embed_query
                )
            else:
                knowledge_service = KnowledgeService()
            logger.info("Created KnowledgeService instance")
        except Exception as e:
            logger.error(f"Failed to create KnowledgeService: {e}")
            raise
    return knowledge_service


def get_chatbot_service() -> "ChatbotService":
    """Get or create chatbot service instance"""
    global chatbot_service
    if chatbot_service is None:
        try:
            from app.services.chatbot_service import EnhancedChatbotService

            chatbot_service = EnhancedChatbotService(
                knowledge_service=get_knowledge_service(),
                generation_service=get_generation_service(),
            )
            logger.info("Created ChatbotService instance")
        except Exception as e:
            logger.error(f"Failed to create ChatbotService: {e}")
            raise
    return chatbot_service


def get_billing_service() -> "EnhancedBillingService":
    """Get or create billing service instance"""
    global billing_service
    if billing_service is None:
        try:
            from app.services.billing_service import EnhancedBillingService

            billing_service = EnhancedBillingService()
            logger.info("Created BillingService instance")
        except Exception as e:
            logger.error(f"Failed to create BillingService: {e}")
            raise
    return billing_service


def get_auth_service() -> "AuthService":
    """Get or create auth service instance"""
    global auth_service
    if auth_service is None:
        try:
            from app.services.auth_service import AuthService

            auth_service = AuthService()
            logger.info("Created AuthService instance")
        except Exception as e:
            logger.error(f"Failed to create AuthService: {e}")
            raise
    return auth_service


def get_user_service() -> "UserService":
    """Get or create user service instance"""
    global user_service
    if user_service is None:
        try:
            from app.services.user_service import UserService

            auth_svc = get_auth_service()
            user_service = UserService(auth_service=auth_svc)
            logger.info("Created UserService instance")
        except Exception as e:
            logger.error(f"Failed to create UserService: {e}")
            raise
    return user_service


def get_multi_db_service() -> "MultiDatabaseService":
    """Get or create multi-database service instance"""
    global multi_db_service
    if multi_db_service is None:
        try:
            from app.services.multi_db_service import MultiDatabaseService

            auth_svc = get_auth_service()
            billing_svc = get_billing_service()
            multi_db_service = MultiDatabaseService(
                auth_service=auth_svc, billing_service=billing_svc
            )
            logger.info("Created MultiDatabaseService instance")
        except Exception as e:
            logger.error(f"Failed to create MultiDatabaseService: {e}")
            raise
    return multi_db_service


def get_scylla_manager() -> "ScyllaDBConnection":
    """Get or create ScyllaDB manager instance"""
    global scylla_manager
    if scylla_manager is None:
        try:
            from app.database.scylla_connection import ScyllaDBConnection

            scylla_manager = ScyllaDBConnection()
            if not scylla_manager.is_connected():
                scylla_manager.connect()
            logger.info("Created ScyllaDBConnection instance")
        except Exception as e:
            logger.warning(f"ScyllaDB not available, using mock: {e}")
            scylla_manager = MockScyllaManager()
    return scylla_manager


def get_postgres_manager():
    """Get PostgreSQL manager instance"""
    global postgres_manager
    if postgres_manager is None:
        try:
            from app.database.postgres_connection import postgres_manager as pm

            postgres_manager = pm
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL manager: {e}")
            raise
    return postgres_manager


class MockScyllaManager:
    """Mock ScyllaDB manager for testing"""

    def is_connected(self):
        return False

    def connect(self):
        pass

    def get_session(self):
        return None

    def ensure_keyspace(self, keyspace):
        pass

    def get_connection_info(self):
        return {"connected": False}


class MockEmbeddingService:
    """Mock embedding service for testing"""

    async def embed_query(self, text: str):
        import hashlib
        import math

        h = hashlib.sha256(text.encode("utf-8")).digest()
        dim = 768 if config.use_real_embeddings else 32
        vec = [((h[i % len(h)] / 255.0) - 0.5) for i in range(dim)]
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed_documents(self, texts):
        return [await self.embed_query(text) for text in texts]

    def cleanup(self):
        pass


class MockGenerationService:
    """Mock generation service for testing"""

    async def generate(self, prompt: str, **kwargs):
        return f"Mock response to: {prompt[:50]}..."

    async def chat_completion(self, messages, **kwargs):
        last_message = messages[-1] if messages else {"content": ""}
        return f"Mock response to: {last_message.get('content', '')[:50]}..."


async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get PostgreSQL session"""
    pm = get_postgres_manager()
    async with pm.get_session() as session:
        yield session


get_db_session = get_postgres_session


def reset_services():
    """Reset all services - useful for testing"""
    global embedding_service, generation_service, knowledge_service
    global chatbot_service, billing_service, auth_service
    global user_service, multi_db_service, scylla_manager

    embedding_service = None
    generation_service = None
    knowledge_service = None
    chatbot_service = None
    billing_service = None
    auth_service = None
    user_service = None
    multi_db_service = None
    scylla_manager = None

    logger.info("All services reset")


__all__ = [
    "get_embedding_service",
    "get_generation_service",
    "get_knowledge_service",
    "get_chatbot_service",
    "get_billing_service",
    "get_auth_service",
    "get_user_service",
    "get_multi_db_service",
    "get_scylla_manager",
    "get_postgres_manager",
    "get_db_session",
    "get_postgres_session",
    "embedding_service",
    "generation_service",
    "knowledge_service",
    "chatbot_service",
    "billing_service",
    "auth_service",
    "user_service",
    "multi_db_service",
    "scylla_manager",
    "reset_services",
]
