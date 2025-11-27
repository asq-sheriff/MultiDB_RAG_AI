"""
Users API Router
===============

User management endpoints for profile updates, preferences, and account management.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.dependencies import get_auth_service
from app.core.auth_dependencies import get_current_user
from app.database.postgres_models import User

# Create API router
router = APIRouter(prefix="/users", tags=["users"])

auth_service = get_auth_service()


# Pydantic models for request/response
class UserUpdateRequest(BaseModel):
    subscription_plan: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserProfileResponse(BaseModel):
    id: str
    email: str
    subscription_plan: str
    is_active: bool
    is_verified: bool
    preferences: Dict[str, Any]
    created_at: str
    updated_at: str


class UserPreferencesRequest(BaseModel):
    preferences: Dict[str, Any]


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Get current user's complete profile information.

    Returns:
        UserProfileResponse: Complete user profile data
    """
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        subscription_plan=current_user.subscription_plan,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        preferences=current_user.preferences or {},
        created_at=current_user.created_at.isoformat(),
        updated_at=current_user.updated_at.isoformat(),
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    update_data: UserUpdateRequest, current_user: User = Depends(get_current_user)
) -> UserProfileResponse:
    """
    Update current user's profile information.

    Args:
        update_data: Fields to update
        current_user: Current authenticated user

    Returns:
        UserProfileResponse: Updated user profile
    """
    try:
        # Prepare update data
        update_fields = {}

        if update_data.subscription_plan is not None:
            # Validate subscription plan
            valid_plans = ["free", "pro", "enterprise"]
            if update_data.subscription_plan not in valid_plans:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid subscription plan. Must be one of: {valid_plans}",
                )
            update_fields["subscription_plan"] = update_data.subscription_plan

        if update_data.preferences is not None:
            update_fields["preferences"] = update_data.preferences

        # Update user
        updated_user = await auth_service.update_user(current_user.id, **update_fields)

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile",
            )

        return UserProfileResponse(
            id=str(updated_user.id),
            email=updated_user.email,
            subscription_plan=updated_user.subscription_plan,
            is_active=updated_user.is_active,
            is_verified=updated_user.is_verified,
            preferences=updated_user.preferences or {},
            created_at=updated_user.created_at.isoformat(),
            updated_at=updated_user.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.get("/preferences")
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current user's preferences.

    Returns:
        Dict: User preferences
    """
    return current_user.preferences or {}


@router.put("/preferences")
async def update_user_preferences(
    preferences_data: UserPreferencesRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Update current user's preferences.

    Args:
        preferences_data: New preferences data
        current_user: Current authenticated user

    Returns:
        Dict: Updated preferences
    """
    try:
        updated_user = await auth_service.update_user(
            current_user.id, preferences=preferences_data.preferences
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences",
            )

        return updated_user.preferences or {}

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )


@router.delete("/account")
async def deactivate_account(
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Deactivate current user's account.

    Args:
        current_user: Current authenticated user

    Returns:
        Dict: Success message
    """
    try:
        updated_user = await auth_service.update_user(current_user.id, is_active=False)

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate account",
            )

        return {"message": "Account deactivated successfully"}

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate account",
        )


@router.get("/dashboard")
async def get_user_dashboard(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get comprehensive user dashboard data from all databases.

    Args:
        current_user: Current authenticated user

    Returns:
        Dict: Dashboard data aggregated from PostgreSQL, MongoDB, and ScyllaDB
    """
    try:
        # Get basic user information
        user_info = {
            "id": str(current_user.id),
            "email": current_user.email,
            "subscription_plan": current_user.subscription_plan,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "member_since": current_user.created_at.isoformat(),
        }

        # Try to get multi-database dashboard data
        dashboard_data = {"user": user_info}

        try:
            from app.services.multi_db_service import multi_db_service
            from app.services.auth_service import auth_service as auth_svc

            # Create temporary token for multi_db_service
            token_data = {"user_id": str(current_user.id)}
            temp_token = auth_svc.create_access_token(token_data)

            # Get comprehensive dashboard data
            multi_db_data = await multi_db_service.get_user_dashboard_data(temp_token)
            dashboard_data.update(multi_db_data)

        except Exception as e:
            # If multi-db service fails, continue with basic user data
            dashboard_data["multi_db_error"] = str(e)
            dashboard_data["note"] = (
                "Limited dashboard data due to service unavailability"
            )

        # Add system status information
        try:
            from app.core.auth_dependencies import get_comprehensive_service_status

            service_status = get_comprehensive_service_status()
            dashboard_data["system_status"] = {
                "ai_services_ready": service_status.get("services", {}).get(
                    "services_ready", 0
                ),
                "atlas_search_available": service_status.get("database", {}).get(
                    "atlas_search_available", False
                ),
            }
        except Exception:
            dashboard_data["system_status"] = {"status": "unknown"}

        return dashboard_data

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data",
        )


# Export router for main app integration
__all__ = ["router"]
