import pytest
from uuid import uuid4
from unittest.mock import Mock
from app.dependencies import get_billing_service
from app.database.postgres_models import User


@pytest.mark.asyncio
async def test_billing_basic_functionality():
    """Test basic billing functionality."""
    # Get billing service using getter
    billing_service = get_billing_service()

    # Test plan limits - works for both real and mock service
    limits = billing_service._get_plan_limits("free")
    assert limits["messages"] == 10

    # Create mock user for quota test
    mock_user = Mock(spec=User)
    mock_user.id = uuid4()
    mock_user.email = "test@example.com"
    mock_user.subscription_plan = "free"

    # Test quota checking - works for both real and mock service
    quota_info = await billing_service.check_user_quota(mock_user, "messages", None)
    assert quota_info["has_quota"] is True
    assert quota_info["max_allowed"] == 10