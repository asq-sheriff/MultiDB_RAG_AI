"""Fixed user management tests - uses session consistently"""
import pytest
from uuid import uuid4
from app.dependencies import get_auth_service
from app.database.postgres_models import User
from sqlalchemy import select


@pytest.mark.asyncio
class TestUserManagement:
    """Test user management functionality."""

    async def test_user_creation_and_retrieval(self, test_db_session):
        """Test creating and retrieving a user."""
        # Get auth service using getter
        auth_service = get_auth_service()
        assert auth_service is not None, "Auth service should be initialized"

        user_data = {
            "email": f"test_{uuid4().hex[:8]}@example.com",
            "password": "SecurePass123!"
        }

        # Create user with session parameter
        user = await auth_service.create_user(
            email=user_data["email"],
            password=user_data["password"],
            session=test_db_session,
            subscription_plan="free"
        )

        assert user is not None
        assert user.email == user_data["email"]
        assert user.subscription_plan == "free"

        # Retrieve user directly from test session instead of using get_user_by_email
        result = await test_db_session.execute(
            select(User).where(User.email == user_data["email"])
        )
        retrieved = result.scalar_one_or_none()

        assert retrieved is not None
        assert retrieved.email == user.email
        assert retrieved.id == user.id

        # Test password verification directly (doesn't need database)
        is_valid = auth_service.verify_password(
            user_data["password"],
            user.hashed_password
        )
        assert is_valid is True

        # Test wrong password
        is_invalid = auth_service.verify_password(
            "WrongPassword",
            user.hashed_password
        )
        assert is_invalid is False

        # Test token creation (doesn't need database)
        token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        assert token is not None
        assert isinstance(token, str)

        # Verify token
        payload = await auth_service.verify_token(token)
        assert payload is not None
        assert payload.get("sub") == str(user.id)
        assert payload.get("email") == user.email