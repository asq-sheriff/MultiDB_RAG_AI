"""Fixed billing service tests - properly uses getter functions and session parameters"""
import pytest
from uuid import uuid4
from unittest.mock import Mock
from app.dependencies import get_billing_service, MockBillingService
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

    async def test_check_user_quota_with_quota(self, mock_user, billing_service):
        """Test checking user quota when quota is available."""
        # For mock billing service, just verify it returns expected structure
        if isinstance(billing_service, MockBillingService):
            quota_info = await billing_service.check_user_quota(
                mock_user,
                "messages",
                None
            )
            assert quota_info["has_quota"] is True
            assert quota_info["max_allowed"] == 10
            assert "remaining" in quota_info
        else:
            # Real billing service test with database
            pytest.skip("Requires real database session for full billing service test")