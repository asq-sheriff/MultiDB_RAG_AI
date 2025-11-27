"""Enhanced authentication dependencies with role-based access control - FIXED"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

# FIXED: Import the GETTER functions, not the service instances
from app.dependencies import get_auth_service, get_billing_service, get_db_session
from app.database.postgres_models import User

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current user from JWT token."""
    auth_service = get_auth_service()  # Get initialized service inside the function
    token = credentials.credentials
    payload = await auth_service.verify_token(token)
    if not payload or not (user_id := payload.get("user_id")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    try:
        user = await auth_service.get_user_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return user
    except (ValueError, HTTPException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token"
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Ensure user has admin privileges."""
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


class QuotaChecker:
    """Dependency class for checking user quotas - FIXED to provide session."""

    def __init__(self, resource_type: str):
        self.resource_type = resource_type

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(
            get_db_session
        ),  # FIXED: Get session dependency
    ) -> User:
        """Check if user has quota for the requested resource."""
        # Get the billing service inside the call
        billing_service = get_billing_service()
        try:
            # FIXED: Pass the session to check_user_quota
            quota_info = await billing_service.check_user_quota(
                current_user,
                self.resource_type,
                session,  # FIXED: Added session parameter
            )
            if not quota_info.get("has_quota"):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Quota exceeded for resource: {self.resource_type}",
                )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(
                f"Quota check failed for user {current_user.id}, allowing request: {e}"
            )
            # Allow request on error (fail open)
        return current_user


# Pre-configured quota checkers for common resources
check_message_quota = QuotaChecker("messages")
check_search_quota = QuotaChecker("api_calls")
check_background_task_quota = QuotaChecker("background_tasks")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get user if authenticated, otherwise return None."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


class RateLimiter:
    """Rate limiting dependency - FIXED for better Redis handling."""

    def __init__(self, calls: int = 10, period: int = 60, resource: str = "general"):
        self.calls = calls
        self.period = period
        self.resource = resource
        self._memory_limits = {}

    async def __call__(
        self, current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check rate limit for user."""
        user_key = f"{current_user.id}:{self.resource}"

        # Try Redis first
        redis_available = False
        try:
            from app.database.redis_connection import redis_manager

            if redis_manager and redis_manager.client:
                redis_manager.client.ping()
                redis_available = True

                redis_key = f"rate_limit:{user_key}"
                current = redis_manager.client.incr(redis_key)
                if current == 1:
                    redis_manager.client.expire(redis_key, self.period)

                if current > self.calls:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Max {self.calls} calls per {self.period} seconds.",
                    )
        except ImportError:
            logger.debug("Redis not available for rate limiting")
        except Exception as e:
            logger.debug(f"Redis rate limiting failed: {e}")
            redis_available = False

        # Fallback to in-memory rate limiting if Redis is not available
        if not redis_available:
            import time

            now = time.time()
            if user_key not in self._memory_limits:
                self._memory_limits[user_key] = []

            # Remove timestamps outside the current window
            self._memory_limits[user_key] = [
                t for t in self._memory_limits[user_key] if now - t < self.period
            ]

            if len(self._memory_limits[user_key]) >= self.calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.calls} calls per {self.period} seconds.",
                )
            self._memory_limits[user_key].append(now)

        return current_user
