"""Fixed advanced billing tests - properly uses getter and session parameters"""
import pytest
from uuid import uuid4
from app.dependencies import get_billing_service  # FIXED: Use getter
from app.database.postgres_models import User


@pytest.mark.asyncio
class TestAdvancedBilling:
    @pytest.fixture
    async def sample_user(self, test_db_session):
        """Creates a new user for each test."""
        user = User(
            id=uuid4(),
            email=f"billing_{uuid4().hex[:8]}@example.com",
            hashed_password="testpassword",
            subscription_plan="free",
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        return user

    async def test_plan_change_workflow(self, test_db_session, sample_user):
        """Test the complete plan change process."""
        # FIXED: Get billing service using getter
        billing_service = get_billing_service()
        assert billing_service is not None, "Billing service should be initialized"

        # Update subscription plan with all required parameters
        enterprise_sub = await billing_service.update_subscription_plan(
            user=sample_user,
            new_plan="enterprise",
            billing_cycle="yearly",
            session=test_db_session
        )

        assert enterprise_sub is not None
        assert enterprise_sub.plan_type == "enterprise"
        assert enterprise_sub.limits["messages"] == 10000

        # Verify the user object is also updated in the database
        await test_db_session.refresh(sample_user)
        assert sample_user.subscription_plan == "enterprise"