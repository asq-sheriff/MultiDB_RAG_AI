"""Fixed error handling tests - properly uses getters and session parameters"""
import pytest
import asyncio
from sqlalchemy import text
from app.dependencies import get_chatbot_service, get_billing_service


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and recovery mechanisms."""

    async def test_database_connection_recovery(self, test_db_session):
        """Test database connection recovery."""
        try:
            # Simple connection test
            result = await test_db_session.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Test with rollback
            await test_db_session.rollback()

            # Should still work after rollback
            result = await test_db_session.execute(text("SELECT 2"))
            assert result.scalar() == 2

        except Exception as e:
            # If there's an error, ensure we rollback
            await test_db_session.rollback()
            raise

    async def test_service_error_handling(self):
        """Test service-level error handling."""
        # FIXED: Get chatbot service using getter
        chatbot_service = get_chatbot_service()
        assert chatbot_service is not None, "Chatbot service should be initialized"

        # Test with invalid input (empty message)
        response = await chatbot_service.answer_user_message(
            user_id="test_user",
            message=""  # Empty message
        )

        # Should handle gracefully
        assert response is not None
        # The response should either have an error or a fallback answer
        assert "error" in response or "answer" in response

    async def test_quota_exceeded_handling(self, test_db_session):
        """Test handling of quota exceeded scenarios."""
        # FIXED: Get billing service using getter
        billing_service = get_billing_service()
        assert billing_service is not None, "Billing service should be initialized"

        from app.database.postgres_models import User
        from uuid import uuid4

        # Create user with exhausted quota
        user = User(
            id=uuid4(),
            email=f"quota_test_{uuid4().hex[:8]}@example.com",
            hashed_password="test",
            subscription_plan="free"
        )
        test_db_session.add(user)
        await test_db_session.commit()
        await test_db_session.refresh(user)

        # Create default subscription
        await billing_service.create_default_subscription(user, test_db_session)

        # FIXED: Check the quota system with session parameter
        quota_info = await billing_service.check_user_quota(
            user,
            "messages",
            test_db_session
        )
        assert quota_info is not None
        assert "has_quota" in quota_info
        assert "remaining" in quota_info
        assert "max_allowed" in quota_info

        # Exhaust the quota
        for _ in range(quota_info["max_allowed"]):
            await billing_service.record_usage(
                user,
                "messages",
                test_db_session
            )

        # Check that quota is now exhausted
        quota_info = await billing_service.check_user_quota(
            user,
            "messages",
            test_db_session
        )
        assert quota_info["has_quota"] is False
        assert quota_info["remaining"] == 0