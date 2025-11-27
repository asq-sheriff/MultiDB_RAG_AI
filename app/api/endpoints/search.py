"""Enhanced search endpoints with authentication and quota checks"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from pydantic import BaseModel, Field

# Import authentication dependencies
from app.core.auth_dependencies import (
    get_current_active_user,
    check_search_quota,
    RateLimiter,
)
from app.database.postgres_models import User

from app.dependencies import get_knowledge_service, get_billing_service
from app.services.knowledge_service import KnowledgeService
from app.services.billing_service import EnhancedBillingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# Rate limiter for search endpoints
search_rate_limiter = RateLimiter(
    calls=60, period=60, resource="search"
)  # 60 searches per minute


class SearchRequest(BaseModel):
    """Search request with validation"""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    route: Optional[str] = Field(
        default="auto", pattern="^(auto|exact|semantic|hybrid)$"
    )
    top_k: Optional[int] = Field(default=5, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = Field(default=None)
    include_metadata: bool = Field(default=True)


class SearchResult(BaseModel):
    """Individual search result"""

    document_id: Optional[str] = None
    title: str
    content: str
    score: float
    source: str
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response with results and metadata"""

    query: str
    results: List[SearchResult]
    total_results: int
    route_used: str
    processing_time_ms: float
    subscription_plan: str
    usage_info: Dict[str, Any]
    search_quality: Optional[str] = None


async def record_search_usage(
    user: User,
    query: str,
    results_count: int,
    search_type: str,
    billing_service: EnhancedBillingService,
):
    """Background task to record search usage"""
    try:
        await billing_service.record_usage(
            user=user,
            resource_type="api_calls",
            quantity=1,
            metadata={
                "type": "search",
                "query_length": len(query),
                "results_returned": results_count,
                "search_type": search_type,
            },
        )
    except Exception as e:
        logger.error(f"Failed to record search usage: {e}")


@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_search_quota),  # Quota check included
    _rate_limit: User = Depends(search_rate_limiter),  # Rate limiting
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    billing_service: EnhancedBillingService = Depends(get_billing_service),
) -> SearchResponse:
    """
    Perform semantic or hybrid search.

    Protected endpoint that:
    1. Requires authentication
    2. Checks API call quota before processing
    3. Applies rate limiting
    4. Records usage for billing
    5. Restricts features based on subscription plan
    """
    start_time = time.time()

    try:
        if not knowledge_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is not available",
            )

        # Determine allowed search types based on subscription
        allowed_routes = {
            "free": ["exact", "auto"],
            "pro": ["exact", "semantic", "hybrid", "auto"],
            "enterprise": ["exact", "semantic", "hybrid", "auto"],
        }

        user_allowed_routes = allowed_routes.get(
            current_user.subscription_plan, ["exact"]
        )

        # Adjust route if not allowed
        route = request.route
        if route not in user_allowed_routes:
            if current_user.subscription_plan == "free":
                route = "exact"  # Fallback for free users
                logger.info(
                    f"User {current_user.id} requested {request.route}, using {route} instead"
                )

        # Perform the search
        search_results = await knowledge_service.search_router(
            query=request.query,
            top_k=request.top_k or 5,
            route=route,
            filters=request.filters,
        )

        # Process results
        results = []
        for r in search_results.get("results", []):
            result = SearchResult(
                document_id=r.get("document_id"),
                title=r.get("title", "Document")[:100],
                content=r.get("content", "")[:500],  # Limit content length
                score=r.get("score", 0.0),
                source=r.get("source", "unknown"),
            )

            # Add metadata based on subscription
            if request.include_metadata and current_user.subscription_plan != "free":
                result.metadata = r.get("metadata", {})

            results.append(result)

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Get current usage
        quota_info = await billing_service.check_user_quota(current_user, "api_calls")

        # Record usage in background
        background_tasks.add_task(
            record_search_usage,
            user=current_user,
            query=request.query,
            results_count=len(results),
            search_type=search_results.get("route", route),
            billing_service=billing_service,
        )

        # Determine search quality
        if results and results[0].score > 0.8:
            search_quality = "excellent"
        elif results and results[0].score > 0.5:
            search_quality = "good"
        else:
            search_quality = "needs_improvement"

        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            route_used=search_results.get("route", route),
            processing_time_ms=processing_time_ms,
            subscription_plan=current_user.subscription_plan,
            usage_info={
                "api_calls_used": quota_info["current_usage"],
                "api_calls_limit": quota_info["max_allowed"],
                "api_calls_remaining": quota_info["remaining"],
            },
            search_quality=search_quality,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed"
        )


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_search_quota),
    _rate_limit: User = Depends(search_rate_limiter),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    billing_service: EnhancedBillingService = Depends(get_billing_service),
) -> SearchResponse:
    """
    Perform pure semantic/vector search.

    Available for Pro and Enterprise users only.
    """
    if current_user.subscription_plan == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Semantic search is not available for free plan",
                "upgrade_to": "pro",
                "upgrade_url": "/billing/plans",
            },
        )

    request.route = "semantic"
    return await search(
        request,
        background_tasks,
        current_user,
        _rate_limit,
        knowledge_service,
        billing_service,
    )


@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=5, ge=1, le=10),
    current_user: User = Depends(get_current_active_user),
) -> List[str]:
    """
    Get search suggestions based on partial query.

    Protected endpoint for autocomplete functionality.
    """
    try:
        suggestions = [
            f"{query} in MongoDB",
            f"{query} with Redis",
            f"{query} using PostgreSQL",
            f"How to {query}",
            f"What is {query}",
        ]

        return suggestions[:limit]

    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        return []
