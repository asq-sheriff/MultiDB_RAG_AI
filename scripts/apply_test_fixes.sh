#!/bin/bash
# scripts/apply_test_fixes.sh
# Quick script to apply all test fixes

echo "🔧 Applying test fixes..."

# Make scripts executable
chmod +x scripts/run_comprehensive_tests.sh
chmod +x scripts/wait-for-scylla.sh

# Create .coveragerc if it doesn't exist
if [ ! -f .coveragerc ]; then
    echo "📝 Creating .coveragerc..."
    cat > .coveragerc << 'EOF'
[run]
source = app
omit =
    */tests/*
    */test_*.py
    */__pycache__/*
    */venv/*
    */.venv/*

[report]
precision = 2
skip_empty = True
show_missing = True
EOF
fi

echo "✅ Test fixes applied!"
echo ""
echo "Next steps:"
echo "1. Replace the failing test files with the fixed versions"
echo "2. Run: make test-all"
echo ""
echo "Available commands:"
echo "  make test           - Run simple test suite"
echo "  make test-unit      - Run unit tests only"
echo "  make test-integration - Run integration tests"
echo "  make test-system    - Run system tests"
echo "  make test-all       - Run comprehensive suite with coverage"
echo "  make coverage       - Generate coverage report"