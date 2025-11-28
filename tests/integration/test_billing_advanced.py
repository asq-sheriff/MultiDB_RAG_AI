"""Fixed advanced billing tests - properly uses getter and session parameters"""
import pytest
from app.dependencies import get_billing_service


@pytest.mark.asyncio
class TestAdvancedBilling:
    async def test_plan_definitions(self):
        """Test that plan definitions are correctly configured."""
        billing_service = get_billing_service()
        assert billing_service is not None, "Billing service should be initialized"

        # Test all plan limits are correctly defined
        free_limits = billing_service._get_plan_limits("free")
        assert free_limits["messages"] == 10
        assert free_limits["background_tasks"] == 5

        pro_limits = billing_service._get_plan_limits("pro")
        assert pro_limits["messages"] == 1000
        assert pro_limits["background_tasks"] == 50

        enterprise_limits = billing_service._get_plan_limits("enterprise")
        assert enterprise_limits["messages"] == 10000
        assert enterprise_limits["background_tasks"] == 1000

    async def test_available_plans(self):
        """Test getting available plans."""
        billing_service = get_billing_service()

        plans = billing_service.get_available_plans()
        assert "plans" in plans
        assert "currency" in plans
        assert plans["currency"] == "USD"