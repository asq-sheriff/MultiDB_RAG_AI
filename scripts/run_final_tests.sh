#!/bin/bash
# scripts/run_final_tests.sh
# Final test runner with all corrections applied

set -e

echo "🚀 FINAL TEST RUN - All Corrections Applied"
echo "==========================================="

# Show plan limits first
echo -e "\n📊 Verifying Plan Limits:"
python -c "
from app.services.billing_service import billing_service
for plan in ['free', 'pro', 'enterprise']:
    limits = billing_service._get_plan_limits(plan)
    print(f'{plan.upper()}: {limits.get(\"messages\")} messages, {limits.get(\"api_calls\")} API calls')
"

# Run tests
echo -e "\n🧪 Running Test Suite:\n"

# Unit tests
echo "1️⃣ Unit Tests:"
pytest tests/unit -q --tb=no

# Integration tests
echo -e "\n2️⃣ Integration Tests:"
pytest tests/integration -q --tb=no

# System tests
echo -e "\n3️⃣ System Tests:"
pytest tests/system -q --tb=no

# Generate coverage
echo -e "\n📊 Coverage Report:"
pytest --cov=app --cov-report=term-missing:skip-covered --quiet

echo -e "\n✅ All tests complete!"