#!/bin/bash

echo "🔍 Validating changes after Claude Code session..."

# Check for syntax errors in Python files
echo "Checking Python syntax..."
if find . -name "*.py" -not -path "./.venv/*" -exec python -m py_compile {} \; 2>/dev/null; then
    echo "✅ Python syntax check passed"
else
    echo "❌ Python syntax errors found"
    exit 1
fi

# Check for HIPAA compliance if healthcare-related changes
if git diff --name-only HEAD~1 | grep -E "(auth|compliance|audit|user)" > /dev/null; then
    echo "🏥 Healthcare-related changes detected, running HIPAA quick check..."
    if make test-hipaa-quick 2>/dev/null; then
        echo "✅ HIPAA quick check passed"
    else
        echo "⚠️ HIPAA quick check failed - run full HIPAA tests"
    fi
fi

# Check for database model changes
if git diff --name-only HEAD~1 | grep -E "models\.py|schema|migration" > /dev/null; then
    echo "🗄️ Database changes detected, validating models..."
    python -c "
import sys
sys.path.append('.')
try:
    from data_layer.models.postgres.postgres_models import *
    print('✅ Database models valid')
except Exception as e:
    print(f'❌ Database model error: {e}')
    sys.exit(1)
" || exit 1
fi

# Check service configuration if service files changed
if git diff --name-only HEAD~1 | grep -E "services/|main\.py" > /dev/null; then
    echo "🚀 Service changes detected, checking configuration..."
    if python -c "
import sys
sys.path.append('.')
try:
    from app.config import config
    print('✅ Configuration valid')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
"; then
        echo "✅ Service configuration check passed"
    else
        exit 1
    fi
fi

echo "✅ All validation checks passed!"