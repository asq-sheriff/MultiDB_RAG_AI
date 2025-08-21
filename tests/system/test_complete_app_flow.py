"""Fixed complete app flow tests - properly uses getters and session parameters"""
import pytest
from uuid import uuid4
from app.dependencies import get_billing_service, get_chatbot_service
from app.database.postgres_models import User


@pytest.mark.asyncio
class TestCompleteAppFlow:
    """Test complete application workflows."""

    @pytest.fixture
    async def flow_user(self, test_db_session):
        """Create a user for flow testing."""
        user = User(
            id=uuid4(),
            email=f"flow_{uuid4().hex[:8]}@example.com",
            hashed_password="test",
            subscription_plan="free"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)
        return user

    async def test_complete_chat_flow(self, test_db_session, flow_user):
        """Test complete chat flow from user creation to response."""
        # FIXED: Get services using getters
        billing_service = get_billing_service()
        chatbot_service = get_chatbot_service()

        assert billing_service is not None, "Billing service should be initialized"
        assert chatbot_service is not None, "Chatbot service should be initialized"

        # 1. Create subscription
        subscription = await billing_service.create_default_subscription(
            flow_user,
            test_db_session
        )
        assert subscription is not None

        # 2. Check initial quota with session parameter
        quota = await billing_service.check_user_quota(
            flow_user,
            "messages",
            test_db_session
        )
        assert quota["has_quota"] is True
        assert quota["max_allowed"] == 10  # Free plan

        # 3. Send a chat message
        response = await chatbot_service.answer_user_message(
            user_id=str(flow_user.id),
            message="What is machine learning?"
        )

        assert response is not None
        assert "answer" in response
        assert len(response["answer"]) > 0

        # 4. Check detailed usage if available
        detailed_usage = await billing_service.get_detailed_usage(
            flow_user,
            test_db_session
        )
        assert detailed_usage is not None

    async def test_quota_enforcement(self, test_db_session, flow_user):
        """Test that quotas are properly enforced."""
        # FIXED: Get billing service using getter
        billing_service = get_billing_service()
        assert billing_service is not None, "Billing service should be initialized"

        # Create subscription first
        await billing_service.create_default_subscription(
            flow_user,
            test_db_session
        )

        # Record usage 9 times with session parameter
        for _ in range(9):
            await billing_service.record_usage(
                flow_user,
                "messages",
                test_db_session
            )

        # Check quota - should have 1 remaining
        quota = await billing_service.check_user_quota(
            flow_user,
            "messages",
            test_db_session
        )
        assert quota["has_quota"] is True
        assert quota["remaining"] == 1

        # Record one more time
        await billing_service.record_usage(
            flow_user,
            "messages",
            test_db_session
        )

        # Check quota - should now be exhausted
        quota = await billing_service.check_user_quota(
            flow_user,
            "messages",
            test_db_session
        )
        assert quota["has_quota"] is False
        assert quota["remaining"] == 0