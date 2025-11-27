import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import config
from app.database.postgres_connection import (
    get_postgres_manager,
)  # FIXED: Import getter
from app.database.postgres_models import User, AuditLog
import warnings

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and authorization service."""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=config.postgresql.jwt_expire_minutes
        )
        to_encode.update({"exp": expire})

        return jwt.encode(
            to_encode,
            config.postgresql.secret_key,
            algorithm=config.postgresql.jwt_algorithm,
        )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        manager = get_postgres_manager()  # FIXED: Get initialized manager
        async with manager.get_session() as session:
            # Get user by email
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user or not self.verify_password(password, user.hashed_password):
                return None

            if not user.is_active:
                return None

            # Log successful authentication
            await self._log_audit(session, user.id, "login_success", "authentication")

            return user

    async def create_user(
        self,
        email: str,
        password: str,
        session: AsyncSession,
        subscription_plan: str = "free",
        **kwargs,
    ) -> User:
        """Create new user account."""
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("User with this email already exists")

        user = User(
            email=email,
            hashed_password=self.get_password_hash(password),
            subscription_plan=subscription_plan,
            **kwargs,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Log user creation
        await self._log_audit(
            session,
            user.id,
            "user_created",
            "user",
            new_values={"email": email, "subscription_plan": user.subscription_plan},
        )

        logger.info(f"Created new user: {email}")
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        manager = get_postgres_manager()  # FIXED: Get initialized manager
        async with manager.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        manager = get_postgres_manager()  # FIXED: Get initialized manager
        async with manager.get_session() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(
                token,
                config.postgresql.secret_key,
                algorithms=[config.postgresql.jwt_algorithm],
            )
            return payload
        except JWTError:
            return None

    async def _log_audit(
        self,
        session: AsyncSession,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ):
        """Internal method to log audit events"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
        )
        session.add(audit_log)


# Global auth service instance
auth_service: Optional["AuthService"] = None


def get_auth_service() -> "AuthService":
    global auth_service
    if auth_service is None:
        auth_service = AuthService()
    return auth_service
