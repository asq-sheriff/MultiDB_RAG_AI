"""Service layer for the enhanced chatbot application."""

try:
    from .chatbot_service import ChatbotService, ChatResponse
except ImportError:
    ChatbotService = None
    ChatResponse = None

try:
    from .knowledge_service import KnowledgeService, SearchConfig
except ImportError:
    KnowledgeService = None
    SearchConfig = None

# Background tasks handled by Go microservice
# Timeout processing for local Python operations only
try:
    from .multi_db_service import multi_db_service
except ImportError:
    multi_db_service = None

# Auth, billing, and user services are handled by Go microservices

__all__ = [
    "ChatbotService",
    "ChatResponse", 
    "KnowledgeService",
    "SearchConfig",
    "multi_db_service",
]
