#!/bin/bash
# scripts/run_comprehensive_tests.sh
# Comprehensive Test Runner with Categories and Better Reporting

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ASCII art header
echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════╗"
echo "║     RAG Chatbot Platform - Test Suite v2.0        ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Set test environment variables
export TESTING=true
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export PYTEST_CURRENT_TEST=""

# Parse command line arguments
TEST_TYPE=${1:-all}
COVERAGE=${2:-true}
VERBOSE=${3:-false}

# Function to run tests with nice output
run_test_category() {
    local category=$1
    local path=$2
    local description=$3

    echo -e "\n${BLUE}══════════════════════════════════════${NC}"
    echo -e "${YELLOW}$description${NC}"
    echo -e "${BLUE}══════════════════════════════════════${NC}"

    if [ "$VERBOSE" == "true" ]; then
        pytest $path -v --tb=short --color=yes
    else
        pytest $path --tb=short --color=yes -q
    fi

    return $?
}

# Function to print test statistics
print_stats() {
    echo -e "\n${CYAN}📊 Test Statistics:${NC}"
    echo -e "${CYAN}───────────────────${NC}"

    # Count test files and tests
    UNIT_COUNT=$(find tests/unit -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
    INT_COUNT=$(find tests/integration -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
    SYS_COUNT=$(find tests/system -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')

    TOTAL_TESTS=$(pytest --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1 || echo "0")

    echo "  Unit Test Files:        $UNIT_COUNT"
    echo "  Integration Test Files: $INT_COUNT"
    echo "  System Test Files:      $SYS_COUNT"
    echo "  Total Tests Collected:  $TOTAL_TESTS"
}

# Main test execution
case $TEST_TYPE in
    unit)
        run_test_category "unit" "tests/unit" "🧪 Unit Tests"
        EXIT_CODE=$?
        ;;

    integration)
        run_test_category "integration" "tests/integration" "🔗 Integration Tests"
        EXIT_CODE=$?
        ;;

    system)
        run_test_category "system" "tests/system" "🖥️  System Tests"
        EXIT_CODE=$?
        ;;

    performance)
        echo -e "\n${YELLOW}⚡ Performance Tests${NC}"
        pytest tests/system/test_performance.py -v --tb=short
        EXIT_CODE=$?
        ;;

    all)
        echo -e "${CYAN}Running Complete Test Suite...${NC}\n"

        # Track results
        FAILURES=0

        # Run unit tests
        if run_test_category "unit" "tests/unit" "1️⃣  Unit Tests"; then
            echo -e "${GREEN}✅ Unit tests passed${NC}"
        else
            echo -e "${RED}❌ Unit tests failed${NC}"
            FAILURES=$((FAILURES + 1))
        fi

        # Run integration tests
        if run_test_category "integration" "tests/integration" "2️⃣  Integration Tests"; then
            echo -e "${GREEN}✅ Integration tests passed${NC}"
        else
            echo -e "${RED}❌ Integration tests failed${NC}"
            FAILURES=$((FAILURES + 1))
        fi

        # Run system tests
        if run_test_category "system" "tests/system" "3️⃣  System Tests"; then
            echo -e "${GREEN}✅ System tests passed${NC}"
        else
            echo -e "${RED}❌ System tests failed${NC}"
            FAILURES=$((FAILURES + 1))
        fi

        EXIT_CODE=$FAILURES
        ;;

    *)
        echo -e "${RED}❌ Invalid test type: $TEST_TYPE${NC}"
        echo "Usage: $0 [unit|integration|system|performance|all] [coverage] [verbose]"
        echo "  coverage: true|false (default: true)"
        echo "  verbose: true|false (default: false)"
        exit 1
        ;;
esac

# Generate coverage report if requested
if [ "$COVERAGE" == "true" ] && [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "\n${BLUE}══════════════════════════════════════${NC}"
    echo -e "${YELLOW}📊 Generating Coverage Report...${NC}"
    echo -e "${BLUE}══════════════════════════════════════${NC}"

    pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml \
           --cov-config=.coveragerc -q 2>/dev/null || true

    # Display coverage summary
    if [ -f "coverage.xml" ]; then
        COVERAGE_PERCENT=$(python -c "import xml.etree.ElementTree as ET; \
            tree = ET.parse('coverage.xml'); \
            root = tree.getroot(); \
            print(f\"{float(root.attrib.get('line-rate', 0)) * 100:.1f}\")" 2>/dev/null || echo "N/A")

        echo -e "${CYAN}Overall Coverage: ${COVERAGE_PERCENT}%${NC}"
        echo -e "${GREEN}📁 Detailed report: htmlcov/index.html${NC}"
    fi
fi

# Print final statistics
print_stats

# Final summary
echo -e "\n${BLUE}══════════════════════════════════════${NC}"
if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed successfully!${NC}"
else
    echo -e "${RED}⚠️  Some tests failed. Check output above.${NC}"
fi
echo -e "${BLUE}══════════════════════════════════════${NC}\n"

exit $EXIT_CODE