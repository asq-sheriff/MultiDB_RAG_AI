import pytest
from app.dependencies import get_billing_service


@pytest.mark.asyncio
async def test_billing_basic_functionality():
    """Test basic billing functionality."""
    # Get billing service using getter
    billing_service = get_billing_service()

    # Test plan limits - works for both real and mock service
    limits = billing_service._get_plan_limits("free")
    assert limits["messages"] == 10

    # Test pro plan limits
    pro_limits = billing_service._get_plan_limits("pro")
    assert pro_limits["messages"] == 1000

    # Test enterprise plan limits
    enterprise_limits = billing_service._get_plan_limits("enterprise")
    assert enterprise_limits["messages"] == 10000