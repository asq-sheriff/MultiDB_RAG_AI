"""Fixed billing service tests - properly uses getter functions and session parameters"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock
from app.dependencies import get_billing_service
from app.database.postgres_models import User


@pytest.mark.asyncio
class TestBillingService:
    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.subscription_plan = "free"
        return user

    @pytest.fixture
    def billing_service(self):
        """Get the billing service instance using getter."""
        service = get_billing_service()
        assert service is not None, "Billing service should be initialized"
        return service

    async def test_get_plan_limits(self, billing_service):
        """Test getting plan limits."""
        limits = billing_service._get_plan_limits("free")
        assert limits["messages"] == 10
        assert limits["background_tasks"] == 5
        assert limits["api_calls"] == 20

    async def test_check_user_quota_with_quota(self, mock_user, test_db_session, billing_service):
        """Test checking user quota when quota is available."""
        # Create a mock for the database query result
        mock_result = Mock()
        mock_result.scalar.return_value = 5  # Current usage is 5

        # Mock the session.execute to return our mock result
        test_db_session.execute = AsyncMock(return_value=mock_result)

        # Now call check_user_quota which should calculate: max_allowed (10) - current_usage (5) = 5
        quota_info = await billing_service.check_user_quota(
            mock_user,
            "messages",
            test_db_session
        )

        assert quota_info["has_quota"] is True
        assert quota_info["max_allowed"] == 10
        assert quota_info["current_usage"] == 5
        assert quota_info["remaining"] == 5  # This should now be correct: 10 - 5 = 5