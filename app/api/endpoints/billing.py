"""Billing and subscription management API endpoints"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_models import User
from app.core.auth_dependencies import get_current_user, get_db_session
from app.services.billing_service import billing_service

from app.core.auth_dependencies import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/billing", tags=["billing"], responses={404: {"description": "Not found"}}
)


# Request/Response Models
class SubscriptionPlanUpdate(BaseModel):
    """Request model for updating subscription plan"""

    plan_type: str = Field(..., pattern="^(free|pro|enterprise)$")
    billing_cycle: Optional[str] = Field(
        default="monthly", pattern="^(monthly|yearly)$"
    )

    @field_validator("plan_type")
    @classmethod
    def validate_plan_type(cls, v):
        if v not in ["free", "pro", "enterprise"]:
            raise ValueError("Plan type must be free, pro, or enterprise")
        return v

    @field_validator("billing_cycle")
    @classmethod
    def validate_billing_cycle(cls, v):
        if v and v not in ["monthly", "yearly"]:
            raise ValueError("Billing cycle must be monthly or yearly")
        return v


class UsageRequest(BaseModel):
    """Request model for recording usage"""

    resource_type: str = Field(
        ..., description="Type of resource (messages, api_calls, etc.)"
    )
    quantity: int = Field(default=1, ge=1, description="Quantity of resource used")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class SubscriptionResponse(BaseModel):
    """Response model for subscription details"""

    id: UUID
    plan_type: str
    status: str
    billing_cycle: str
    started_at: datetime
    ends_at: Optional[datetime]
    auto_renew: bool
    limits: Dict[str, int]
    amount_cents: int
    currency: str


class UsageResponse(BaseModel):
    """Response model for usage summary"""

    messages_this_month: int
    background_tasks_this_month: int
    api_calls_this_month: int
    quota_remaining: int
    limits: Dict[str, int]
    period_start: str
    period_end: str
    plan_type: str


class QuotaResponse(BaseModel):
    """Response model for quota check"""

    has_quota: bool
    current_usage: int
    max_allowed: int
    remaining: int
    resource_type: str
    period_start: str
    period_end: str


class BillingHistoryItem(BaseModel):
    """Response model for billing history item"""

    date: datetime
    description: str
    amount_cents: int
    currency: str
    status: str
    invoice_url: Optional[str]


# Endpoints
@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionResponse:
    """Get current user's subscription details"""
    try:
        subscription = await billing_service.get_active_subscription(
            current_user, session
        )

        if not subscription:
            # Create default free subscription if none exists
            subscription = await billing_service.create_default_subscription(
                current_user, session
            )

        return SubscriptionResponse(
            id=subscription.id,
            plan_type=subscription.plan_type,
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            started_at=subscription.started_at,
            ends_at=subscription.ends_at,
            auto_renew=subscription.auto_renew,
            limits=subscription.limits
            or billing_service._get_plan_limits(subscription.plan_type),
            amount_cents=subscription.amount_cents,
            currency=subscription.currency,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscription: {str(e)}",
        )


@router.put("/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    plan_update: SubscriptionPlanUpdate,
    current_user: User = Depends(get_current_active_user),  # Changed
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionResponse:
    """Update user's subscription plan"""
    try:
        # Check if upgrade/downgrade is allowed
        can_change, reason = await billing_service.can_change_plan(
            current_user, plan_update.plan_type, session
        )

        if not can_change:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        # Update subscription
        updated_subscription = await billing_service.update_subscription_plan(
            current_user, plan_update.plan_type, plan_update.billing_cycle, session
        )

        return SubscriptionResponse(
            id=updated_subscription.id,
            plan_type=updated_subscription.plan_type,
            status=updated_subscription.status,
            billing_cycle=updated_subscription.billing_cycle,
            started_at=updated_subscription.started_at,
            ends_at=updated_subscription.ends_at,
            auto_renew=updated_subscription.auto_renew,
            limits=updated_subscription.limits
            or billing_service._get_plan_limits(updated_subscription.plan_type),
            amount_cents=updated_subscription.amount_cents,
            currency=updated_subscription.currency,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}",
        )


@router.post("/subscription/cancel", response_model=Dict[str, Any])
async def cancel_subscription(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Cancel user's subscription at end of billing period"""
    try:
        result = await billing_service.cancel_subscription(current_user, session)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("reason", "Failed to cancel subscription"),
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}",
        )


@router.get("/usage", response_model=UsageResponse)
async def get_usage_summary(
    current_user: User = Depends(get_current_active_user),
) -> UsageResponse:
    """Get current billing period usage summary"""
    try:
        # Get usage data - billing_service already returns everything including plan_type
        usage_data = await billing_service.get_usage_summary(current_user)

        return UsageResponse(
            messages_this_month=usage_data["messages_this_month"],
            background_tasks_this_month=usage_data["background_tasks_this_month"],
            api_calls_this_month=usage_data["api_calls_this_month"],
            quota_remaining=usage_data["quota_remaining"],
            limits=usage_data["limits"],
            period_start=usage_data["period_start"],
            period_end=usage_data["period_end"],
            plan_type=usage_data["plan_type"],  # This is already in usage_data!
        )
    except Exception as e:
        logger.error(f"Failed to retrieve usage summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage summary: {str(e)}",
        )


@router.post("/usage/record", response_model=Dict[str, bool])
async def record_usage(
    usage: UsageRequest, current_user: User = Depends(get_current_user)
) -> Dict[str, bool]:
    """Record resource usage (internal use)"""
    try:
        success = await billing_service.record_usage(
            current_user, usage.resource_type, usage.quantity, usage.metadata
        )

        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record usage: {str(e)}",
        )


@router.get("/quota/{resource_type}", response_model=QuotaResponse)
async def check_quota(
    resource_type: str,
    current_user: User = Depends(get_current_active_user),
) -> QuotaResponse:
    """Check if user has quota for specific resource"""
    try:
        quota_info = await billing_service.check_user_quota(current_user, resource_type)

        return QuotaResponse(
            has_quota=quota_info["has_quota"],
            current_usage=quota_info["current_usage"],
            max_allowed=quota_info["max_allowed"],
            remaining=quota_info["remaining"],
            resource_type=resource_type,
            period_start=quota_info["period_start"],
            period_end=quota_info["period_end"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check quota: {str(e)}",
        )


@router.get("/history")
async def get_billing_history(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get billing history for user"""
    try:
        history = await billing_service.get_billing_history(
            current_user, session, limit=limit, offset=offset
        )

        return {
            "total": history["total"],
            "items": history["items"],
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve billing history: {str(e)}",
        )


@router.get("/plans")
async def get_available_plans() -> Dict[str, Any]:
    """Get all available subscription plans with pricing"""
    return billing_service.get_available_plans()


@router.get("/usage/details")
async def get_detailed_usage(
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get detailed usage breakdown"""
    try:
        usage_details = await billing_service.get_detailed_usage(
            current_user,
            session,
            start_date=start_date,
            end_date=end_date,
            resource_type=resource_type,
        )

        return usage_details
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve detailed usage: {str(e)}",
        )


@router.post("/webhook/stripe")
async def handle_stripe_webhook(
    payload: Dict[str, Any], stripe_signature: str = Query(default=None)
) -> Dict[str, str]:
    """Handle Stripe webhook events"""
    return {"status": "webhook_received"}
