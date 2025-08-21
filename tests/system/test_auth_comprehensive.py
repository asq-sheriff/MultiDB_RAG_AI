"""Fixed comprehensive auth tests - properly uses getter"""
import pytest
import asyncio
from datetime import timedelta
from uuid import uuid4
from app.dependencies import get_auth_service  # FIXED: Use getter


@pytest.mark.asyncio
class TestAuthenticationComplete:
    async def test_jwt_token_lifecycle(self):
        """Test JWT token creation and verification."""
        # FIXED: Get auth service using getter
        auth_service = get_auth_service()
        assert auth_service is not None, "Auth service should be initialized"

        user_id = str(uuid4())
        test_user_data = {"user_id": user_id}

        # Create access token (expires_delta is handled internally now)
        access_token = auth_service.create_access_token(data=test_user_data)
        assert access_token is not None
        assert isinstance(access_token, str)

        # Verify the token
        payload = await auth_service.verify_token(access_token)
        assert payload is not None
        assert payload["user_id"] == user_id