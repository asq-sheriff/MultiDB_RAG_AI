"""AI services dependencies and service initialization"""

from __future__ import annotations

import logging
import os
import httpx
from typing import Optional, TYPE_CHECKING, Any, List

from ai_services.shared.config.config import config

if TYPE_CHECKING:
    from ai_services.core.knowledge_service import KnowledgeService
    from ai_services.core.chatbot_service import ChatbotService
    from ai_services.core.multi_db_service import MultiDatabaseService

embedding_service: Optional[Any] = None
generation_service: Optional[Any] = None
knowledge_service: Optional["KnowledgeService"] = None
chatbot_service: Optional["ChatbotService"] = None
multi_db_service: Optional["MultiDatabaseService"] = None

logger = logging.getLogger(__name__)


def get_embedding_service() -> Any:
    """Get embedding service - now uses API Gateway routing"""
    global embedding_service
    if embedding_service is None:
        try:
            embedding_service = APIGatewayEmbeddingService()
            logger.info("Created API Gateway embedding service instance")
        except Exception as e:
            logger.error(f"Failed to create embedding service: {e}")
            embedding_service = MockEmbeddingService()
    return embedding_service


def get_generation_service() -> Any:
    """Get generation service - now uses API Gateway routing"""
    global generation_service
    if generation_service is None:
        try:
            generation_service = APIGatewayGenerationService()
            logger.info("Created API Gateway generation service instance")
        except Exception as e:
            logger.error(f"Failed to create generation service: {e}")
            generation_service = MockGenerationService()
    return generation_service


def get_knowledge_service() -> "KnowledgeService":
    """Get or create knowledge service instance"""
    global knowledge_service
    if knowledge_service is None:
        try:
            from ai_services.core.knowledge_service import KnowledgeService

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
            from ai_services.core.chatbot_service import EnhancedChatbotService

            chatbot_service = EnhancedChatbotService(
                knowledge_service=get_knowledge_service(),
                generation_service=get_generation_service(),
            )
            logger.info("Created ChatbotService instance")
        except Exception as e:
            logger.error(f"Failed to create ChatbotService: {e}")
            raise
    return chatbot_service


# Auth, billing, and user services are handled by Go microservices
# Call them directly via HTTP API


def get_multi_db_service() -> "MultiDatabaseService":
    """Get or create multi-database service instance"""
    global multi_db_service
    if multi_db_service is None:
        try:
            from ai_services.core.multi_db_service import MultiDatabaseService

            multi_db_service = MultiDatabaseService()
            logger.info("Created MultiDatabaseService instance")
        except Exception as e:
            logger.error(f"Failed to create MultiDatabaseService: {e}")
            raise
    return multi_db_service




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


class APIGatewayEmbeddingService:
    """API Gateway embedding service client"""
    
    def __init__(self):
        self.api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8090")
        self.timeout = 30.0
        
    async def embed_query(self, text: str) -> List[float]:
        """Embed query via API Gateway"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_gateway_url}/api/v1/embedding/embed",
                json={"text": text}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [])
            
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents via API Gateway"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_gateway_url}/api/v1/embedding/v1/embeddings",
                json={"model": "bge-large", "input": texts}
            )
            response.raise_for_status()
            result = response.json()
            return [item.get("embedding", []) for item in result.get("data", [])]
            
    async def warmup(self):
        """Warmup via API Gateway"""
        await self.embed_query("test warmup query")
        
    def cleanup(self):
        pass


class APIGatewayGenerationService:
    """API Gateway generation service client"""
    
    def __init__(self):
        self.api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8090")
        self.timeout = 60.0
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate via API Gateway"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_gateway_url}/api/v1/generation/v1/chat/completions",
                json={
                    "model": "gpt-3.5-turbo", 
                    "messages": [{"role": "user", "content": prompt}],
                    **kwargs
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
    async def chat_completion(self, messages, **kwargs):
        """Chat completion via API Gateway"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_gateway_url}/api/v1/generation/v1/chat/completions",
                json={"messages": messages, **kwargs}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
    async def warmup(self):
        """Warmup via API Gateway"""
        await self.chat_completion([{"role": "user", "content": "test"}])
        
    def cleanup(self):
        pass




def reset_services():
    """Reset all AI services - useful for testing"""
    global embedding_service, generation_service, knowledge_service
    global chatbot_service, multi_db_service

    embedding_service = None
    generation_service = None
    knowledge_service = None
    chatbot_service = None
    multi_db_service = None

    logger.info("All AI services reset")


def get_comprehensive_service_status():
    """Get comprehensive status of all services for health checks"""
    try:
        services_ready = 0
        total_services = 2  # Focus on core AI services (embedding + generation)
        
        # Check embedding service via API Gateway
        embedding_ready = False
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get("http://localhost:8090/api/v1/embedding/health")
                embedding_ready = response.status_code == 200
                if embedding_ready:
                    services_ready += 1
        except Exception:
            pass
            
        # Check generation service via API Gateway
        generation_ready = False
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get("http://localhost:8090/api/v1/generation/health")
                generation_ready = response.status_code == 200
                if generation_ready:
                    services_ready += 1
        except Exception:
            pass
            
        # Check if services have been instantiated (lazy loading)
        knowledge_ready = knowledge_service is not None
        chatbot_ready = chatbot_service is not None
        
        return {
            "services": {
                "services_ready": services_ready,
                "total_services": total_services,
                "embedding_service": embedding_ready,
                "generation_service": generation_ready,
                "knowledge_service": knowledge_ready,
                "chatbot_service": chatbot_ready,
            }
        }
    except Exception as e:
        logger.error(f"Service status check failed: {e}")
        return {
            "services": {
                "services_ready": 0,
                "total_services": 2,
                "embedding_service": False,
                "generation_service": False,
                "knowledge_service": False,
                "chatbot_service": False,
                "error": str(e)
            }
        }


# Admin authentication for internal AI service endpoints
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID

security = HTTPBearer()

async def get_admin_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Any:
    """Simple admin auth for internal AI service endpoints."""
    # In production, this would validate actual admin tokens
    # For now, return mock admin user for internal endpoints
    logger.info("Admin auth for internal AI service endpoint")
    
    from data_layer.models.postgres.postgres_models import User
    mock_admin = User(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        email="admin@internal.local",
        full_name="Internal Admin", 
        is_active=True
    )
    return mock_admin


__all__ = [
    "get_embedding_service",
    "get_generation_service", 
    "get_knowledge_service",
    "get_chatbot_service",
    "get_multi_db_service",
    "get_admin_user",
    "embedding_service",
    "generation_service",
    "knowledge_service",
    "chatbot_service",
    "multi_db_service",
    "reset_services",
    "get_comprehensive_service_status",
]
