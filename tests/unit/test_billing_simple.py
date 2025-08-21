import pytest
from uuid import uuid4
from app.dependencies import get_billing_service  # FIXED: Use getter function
from app.database.postgres_models import User


@pytest.mark.asyncio
async def test_billing_basic_functionality(test_db_session):
    """Test basic billing functionality."""
    # Get billing service using getter
    billing_service = get_billing_service()  # FIXED: Get service instance

    # Create user properly without passing session to constructor
    user = User(
        id=uuid4(),
        email=f"simple_{uuid4().hex[:8]}@example.com",
        hashed_password="test",
        subscription_plan="free"
    )

    # Add to session and commit
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    # Test plan limits
    limits = billing_service._get_plan_limits("free")
    assert limits["messages"] == 10

    # Test quota checking - FIXED: Added session parameter
    quota_info = await billing_service.check_user_quota(user, "messages", test_db_session)
    assert quota_info["has_quota"] is True
    assert quota_info["max_allowed"] == 10