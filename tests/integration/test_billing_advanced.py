"""Fixed advanced billing tests - properly uses getter and session parameters"""
import pytest
from uuid import uuid4
from unittest.mock import Mock
from app.dependencies import get_billing_service
from app.database.postgres_models import User


@pytest.mark.asyncio
class TestAdvancedBilling:
    @pytest.fixture
    def mock_user(self):
        """Creates a mock user for testing."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.email = f"billing_{uuid4().hex[:8]}@example.com"
        user.subscription_plan = "free"
        return user

    async def test_plan_change_workflow(self, mock_user):
        """Test the complete plan change process."""
        billing_service = get_billing_service()
        assert billing_service is not None, "Billing service should be initialized"

        # Update subscription plan with all required parameters
        enterprise_sub = await billing_service.update_subscription_plan(
            user=mock_user,
            new_plan="enterprise",
            billing_cycle="yearly",
            session=None
        )

        assert enterprise_sub is not None
        assert enterprise_sub.plan_type == "enterprise"
        assert enterprise_sub.limits["messages"] == 10000