from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import get_db_session, get_current_user
from app.services.auth_service import auth_service
from app.database.postgres_models import User

# Create API router
router = APIRouter(prefix="/auth", tags=["authentication"])


# Pydantic models for request/response
class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    subscription_plan: str = "free"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserProfile(BaseModel):
    id: str
    email: str
    subscription_plan: str
    is_active: bool
    is_verified: bool


@router.post("/register", response_model=AuthResponse)
async def register_user(
    user_data: UserRegistration, session: AsyncSession = Depends(get_db_session)
) -> AuthResponse:
    """Register a new user account with detailed error logging"""
    import traceback
    import logging

    logger = logging.getLogger(__name__)

    try:
        logger.info(f"🔄 Attempting to register user: {user_data.email}")

        # Create user account
        user = await auth_service.create_user(
            email=user_data.email,
            password=user_data.password,
            subscription_plan=user_data.subscription_plan,
        )

        logger.info(f"✅ User created successfully: {user.id}")

        # Generate access token
        token_data = {"user_id": str(user.id), "email": user.email}
        access_token = auth_service.create_access_token(token_data)

        logger.info(f"✅ Token generated for user: {user.email}")

        return AuthResponse(
            access_token=access_token,
            user={
                "id": str(user.id),
                "email": user.email,
                "subscription_plan": user.subscription_plan,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
            },
        )

    except ValueError as e:
        logger.error(f"❌ ValueError in registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in registration: {e}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {e}",
        )


@router.post("/login", response_model=AuthResponse)
async def login_user(
    login_data: UserLogin, session: AsyncSession = Depends(get_db_session)
) -> AuthResponse:
    """
    Authenticate user and return JWT token.

    Integration: Validates credentials in PostgreSQL, creates JWT
    Used by: Frontend login forms, API clients

    Args:
        login_data: User login credentials
        session: Database session dependency

    Returns:
        AuthResponse: JWT token and user information

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(
            email=login_data.email, password=login_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Generate access token
        token_data = {"user_id": str(user.id), "email": user.email}
        access_token = auth_service.create_access_token(token_data)

        return AuthResponse(
            access_token=access_token,
            user={
                "id": str(user.id),
                "email": user.email,
                "subscription_plan": user.subscription_plan,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
            },
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    """
    Get current user profile information.

    Integration: Uses authentication dependency to get current user
    Used by: Frontend for user profile display

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        UserProfile: Current user information
    """
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        subscription_plan=current_user.subscription_plan,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
    )


@router.get("/dashboard")
async def get_user_dashboard(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get comprehensive user dashboard data.

    Integration: Uses multi_db_service to get data from all databases
    Used by: Frontend dashboard, user analytics

    Args:
        current_user: Current authenticated user

    Returns:
        Dict: Dashboard data from PostgreSQL, Redis, and ScyllaDB
    """
    try:
        from app.services.multi_db_service import multi_db_service

        # Create temporary token for multi_db_service
        token_data = {"user_id": str(current_user.id)}
        temp_token = auth_service.create_access_token(token_data)

        # Get comprehensive dashboard data
        dashboard_data = await multi_db_service.get_user_dashboard_data(temp_token)

        return dashboard_data

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data",
        )


# Export router for main app integration
__all__ = ["router"]
