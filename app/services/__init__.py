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

from .background_tasks import BackgroundTaskService, TaskResult
from .request_analyzer import RequestAnalyzer, RequestAnalysis, TaskComplexity
from .timeout_processor import TimeoutProcessor, TimeoutConfig
from .auth_service import auth_service
from .billing_service import billing_service
from .user_service import user_service
from .multi_db_service import multi_db_service

__all__ = [
    "ChatbotService",
    "ChatResponse",
    "KnowledgeService",
    "SearchConfig",
    "BackgroundTaskService",
    "TaskResult",
    "RequestAnalyzer",
    "RequestAnalysis",
    "TaskComplexity",
    "TimeoutProcessor",
    "TimeoutConfig",
    "auth_service",
    "billing_service",
    "user_service",
    "multi_db_service",
]
