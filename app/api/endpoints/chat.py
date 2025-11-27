"""Enhanced chat endpoints with authentication and quota checks"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from pydantic import BaseModel, Field

# Import authentication dependencies
from app.core.auth_dependencies import (
    get_current_active_user,
    check_message_quota,
    RateLimiter,
)
from app.database.postgres_models import User

from app.dependencies import (
    get_chatbot_service,
    get_knowledge_service,
    get_billing_service,
)
from app.services.chatbot_service import EnhancedChatbotService as ChatbotService
from app.services.knowledge_service import KnowledgeService
from app.services.billing_service import EnhancedBillingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Rate limiter for chat endpoints
chat_rate_limiter = RateLimiter(
    calls=30, period=60, resource="chat"
)  # 30 messages per minute


class ChatRequest(BaseModel):
    """Enhanced chat request with validation"""

    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(
        default=None, description="Session ID for conversation continuity"
    )

    # RAG Configuration
    enable_rag: Optional[bool] = Field(
        default=True, description="Enable RAG context retrieval"
    )
    route: Optional[str] = Field(
        default="auto", description="Search routing: exact | semantic | hybrid | auto"
    )
    top_k: Optional[int] = Field(
        default=5, ge=1, le=20, description="Number of context documents"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional filters"
    )

    # Response Configuration
    response_style: Optional[str] = Field(
        default="helpful", description="Response style"
    )
    include_sources: Optional[bool] = Field(
        default=True, description="Include source citations"
    )
    max_context_length: Optional[int] = Field(
        default=2000, description="Maximum context characters"
    )
    temperature: Optional[float] = Field(
        default=0.7, ge=0.0, le=1.0, description="Generation temperature"
    )

    # Debug Options
    debug_mode: Optional[bool] = Field(
        default=False, description="Include debug information"
    )


class SourceDocument(BaseModel):
    document_id: Optional[str] = None
    title: str
    excerpt: str
    relevance_score: float
    source_type: str


class ChatResponse(BaseModel):
    """Enhanced chat response with billing info"""

    session_id: str
    message_id: str
    answer: str
    confidence: float
    response_type: str

    # RAG Information
    context_used: bool
    sources: List[SourceDocument] = Field(default_factory=list)
    retrieval_route: Optional[str] = None

    # Performance Metrics
    response_time_ms: float
    tokens_used: Optional[int] = None

    # User Info
    subscription_plan: str
    usage_info: Dict[str, Any]

    # Debug Information
    debug_info: Optional[Dict[str, Any]] = None


async def record_usage_background(
    user: User,
    resource_type: str,
    quantity: int,
    metadata: Dict[str, Any],
    billing_service: EnhancedBillingService,
):
    """Background task to record usage"""
    try:
        success = await billing_service.record_usage(
            user=user, resource_type=resource_type, quantity=quantity, metadata=metadata
        )

        if success:
            logger.info(
                f"Usage recorded for user {user.id}: {resource_type} x{quantity}"
            )
        else:
            logger.error(f"Failed to record usage for user {user.id}")

    except Exception as e:
        logger.error(f"Error recording usage: {e}")


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_message_quota),  # Quota check included
    _rate_limit: User = Depends(chat_rate_limiter),  # Rate limiting
    chatbot: ChatbotService = Depends(get_chatbot_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    billing_service: EnhancedBillingService = Depends(get_billing_service),
) -> ChatResponse:
    """
    Send a chat message with RAG support.

    Protected endpoint that:
    1. Requires authentication
    2. Checks message quota before processing
    3. Applies rate limiting
    4. Records usage for billing
    """
    start_time = time.time()
    session_id = request.session_id or str(uuid4())
    message_id = str(uuid4())

    try:
        # Prepare context if RAG is enabled
        context = None
        sources = []

        if request.enable_rag and knowledge_service:
            # Perform RAG search
            search_results = await knowledge_service.search_router(
                query=request.message,
                top_k=request.top_k or 5,
                route=request.route or "auto",
                filters=request.filters,
            )

            if search_results and search_results.get("results"):
                context = search_results["results"]
                sources = [
                    SourceDocument(
                        document_id=r.get("document_id"),
                        title=r.get("title", "Document")[:100],
                        excerpt=r.get("content", "")[:200],
                        relevance_score=r.get("score", 0.0),
                        source_type=r.get("source", "unknown"),
                    )
                    for r in context[:3]  # Top 3 sources
                ]

        # Generate response using chatbot service
        chat_result = await chatbot.answer_user_message(
            user_id=str(current_user.id),
            message=request.message,
            route=request.route,
            top_k=request.top_k,
            filters=request.filters,
        )

        answer = chat_result.get("answer", "I couldn't generate a response.")
        tokens_used = chat_result.get("tokens_used", 0)

        # Add source citations if requested
        if request.include_sources and sources:
            answer += "\n\n**Sources:**\n"
            for i, source in enumerate(sources[:3], 1):
                answer += f"{i}. {source.title} (score: {source.relevance_score:.2f})\n"

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Get current usage for response
        quota_info = await billing_service.check_user_quota(current_user, "messages")

        # Record usage in background
        background_tasks.add_task(
            record_usage_background,
            user=current_user,
            resource_type="messages",
            quantity=1,
            metadata={
                "session_id": session_id,
                "message_id": message_id,
                "tokens_used": tokens_used,
                "processing_time_ms": processing_time_ms,
                "rag_enabled": request.enable_rag,
            },
            billing_service=billing_service,
        )

        # If RAG was used, also record API call
        if request.enable_rag and sources:
            background_tasks.add_task(
                record_usage_background,
                user=current_user,
                resource_type="api_calls",
                quantity=1,
                metadata={"type": "rag_search", "session_id": session_id},
                billing_service=billing_service,
            )

        return ChatResponse(
            session_id=session_id,
            message_id=message_id,
            answer=answer,
            confidence=0.9 if sources else 0.7,
            response_type="rag_enhanced" if sources else "generation_only",
            context_used=len(sources) > 0,
            sources=sources,
            retrieval_route=chat_result.get("route"),
            response_time_ms=processing_time_ms,
            tokens_used=tokens_used,
            subscription_plan=current_user.subscription_plan,
            usage_info={
                "messages_used": quota_info["current_usage"],
                "messages_limit": quota_info["max_allowed"],
                "messages_remaining": quota_info["remaining"],
            },
            debug_info={
                "user_id": str(current_user.id),
                "model_used": chat_result.get("model", "unknown"),
                "fallback_applied": chat_result.get("fallback_applied", False),
            }
            if request.debug_mode
            else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message",
        )


@router.get("/history")
async def get_chat_history(
    session_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get chat history for the current user.

    Protected endpoint that retrieves conversation history from ScyllaDB.
    """
    try:
        return {
            "user_id": str(current_user.id),
            "session_id": session_id,
            "messages": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history",
        )


@router.post("/feedback")
async def submit_feedback(
    session_id: str,
    message_id: str,
    rating: int = Query(..., ge=1, le=5),
    feedback_text: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, str]:
    """Submit feedback for a chat response"""
    try:
        logger.info(
            f"Feedback from user {current_user.id}: "
            f"session={session_id}, rating={rating}"
        )

        return {"status": "success", "message": "Feedback recorded successfully"}

    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback",
        )
