#!/bin/bash
# scripts/run_tests.sh - Fixed test runner with proper service detection
# This script properly checks Docker services and runs tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════╗"
echo "║     RAG Chatbot Platform - Test Suite v2.3        ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}❌ Virtual environment not found!${NC}"
        echo "Please create one with: python -m venv .venv"
        exit 1
    fi
fi

# Load .env file if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs -0) 2>/dev/null || true
fi

# Set test environment variables
export TESTING=true
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# Disable real AI services for testing (override .env)
export USE_REAL_EMBEDDINGS=0
export USE_REAL_GENERATION=0
export RAG_SYNTHETIC_QUERY_EMBEDDINGS=1
export RAG_SYNTHETIC_DIM=32

# Set timeouts to prevent hanging
export GENERATION_TIMEOUT=5.0
export EMBEDDING_QUERY_TIMEOUT=5.0
export EMBEDDING_BATCH_TIMEOUT=10.0

# Disable ScyllaDB extensions for Python 3.12+
export CASS_DRIVER_NO_EXTENSIONS=1
export CASS_DRIVER_NO_CYTHON=1
export CASS_DRIVER_NO_MURMUR3=1

# Parse command line arguments
TEST_TYPE=${1:-quick}
COVERAGE=${2:-false}
VERBOSE=${3:-false}

# Simple function to check if a port is open
check_port() {
    local port=$1
    # Try nc first (most reliable)
    if command -v nc >/dev/null 2>&1; then
        nc -z localhost $port 2>/dev/null
        return $?
    fi
    
    # Fallback to Python
    python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('localhost', $port))
    s.close()
    exit(0 if result == 0 else 1)
except:
    exit(1)
" 2>/dev/null
}

# Function to check services
check_services() {
    echo -e "${CYAN}Checking required services...${NC}"

    local all_healthy=true

    # Check PostgreSQL
    echo -n "PostgreSQL (port 5432): "
    if check_port 5432; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${RED}✗ Not accessible${NC}"
        echo -e "${YELLOW}  Start it with: docker-compose up -d postgres${NC}"
        all_healthy=false
    fi

    # Check Redis
    echo -n "Redis (port 6379): "
    if check_port 6379; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${RED}✗ Not accessible${NC}"
        echo -e "${YELLOW}  Start it with: docker-compose up -d redis${NC}"
        all_healthy=false
    fi

    # Check MongoDB (optional)
    echo -n "MongoDB (port 27017): "
    if check_port 27017; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${YELLOW}⚠ Not available (some tests may skip)${NC}"
    fi

    # Check ScyllaDB (optional)
    echo -n "ScyllaDB (port 9042): "
    if check_port 9042; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${CYAN}ℹ Not available (ScyllaDB tests will skip)${NC}"
    fi

    if [ "$all_healthy" = false ]; then
        echo -e "\n${RED}❌ Required services are not available.${NC}"
        echo -e "${CYAN}Please ensure Docker services are running:${NC}"
        echo -e "${YELLOW}  docker-compose up -d${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ All required services are available!${NC}"
    return 0
}

# Function to run test category
run_test_category() {
    local category=$1
    local path=$2
    local description=$3

    echo -e "\n${BLUE}══════════════════════════════════════${NC}"
    echo -e "${YELLOW}$description${NC}"
    echo -e "${BLUE}══════════════════════════════════════${NC}"

    # Build pytest command
    PYTEST_CMD="python -m pytest $path --tb=short --color=yes --disable-warnings"

    if [ "$VERBOSE" == "true" ]; then
        PYTEST_CMD="$PYTEST_CMD -v"
    else
        PYTEST_CMD="$PYTEST_CMD -q"
    fi

    if [ "$COVERAGE" == "true" ]; then
        PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=term-missing"
    fi

    # Run tests
    eval $PYTEST_CMD
    return $?
}

# Function to print test statistics
print_stats() {
    echo -e "\n${CYAN}📊 Test Statistics:${NC}"
    echo -e "${CYAN}───────────────────${NC}"

    # Count test files
    if [ -d "tests" ]; then
        UNIT_COUNT=$(find tests/unit -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
        INT_COUNT=$(find tests/integration -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
        SYS_COUNT=$(find tests/system -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')

        echo "  Unit Test Files:        ${UNIT_COUNT:-0}"
        echo "  Integration Test Files: ${INT_COUNT:-0}"
        echo "  System Test Files:      ${SYS_COUNT:-0}"
    fi
}

# Check services before running tests
echo ""
if ! check_services; then
    echo -e "\n${YELLOW}Tip: Run ./scripts/ops/docker/health-check.sh to see detailed service status${NC}"
    exit 1
fi

# Main test execution
echo ""
case $TEST_TYPE in
    quick)
        echo -e "${CYAN}Running Quick Smoke Tests...${NC}"
        echo -e "${CYAN}Testing basic functionality to verify setup${NC}\n"

        # Run available system tests (most reliable)
        python -m pytest tests/system/test_services.py \
                        -v --tb=short --disable-warnings \
                        --maxfail=3  # Stop after 3 failures
        EXIT_CODE=$?
        ;;

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

    billing)
        echo -e "${CYAN}Running All Billing Tests...${NC}"
        echo -e "${YELLOW}No billing tests found, running system tests instead${NC}"
        python -m pytest tests/system/ \
                        -v --tb=short --disable-warnings
        EXIT_CODE=$?
        ;;

    rag)
        echo -e "${CYAN}Running RAG Pipeline Tests...${NC}"
        python -m pytest tests/system/test_rag_pipeline.py \
                        tests/system/test_ai_quality.py \
                        -v --tb=short --disable-warnings
        EXIT_CODE=$?
        ;;

    all)
        echo -e "${CYAN}Running Complete Test Suite...${NC}\n"

        # Track results
        FAILURES=0

        # Run each category
        for category in unit integration system; do
            case $category in
                unit) desc="1️⃣  Unit Tests" ;;
                integration) desc="2️⃣  Integration Tests" ;;
                system) desc="3️⃣  System Tests" ;;
            esac

            if run_test_category "$category" "tests/$category" "$desc"; then
                echo -e "${GREEN}✅ ${category^} tests passed${NC}"
            else
                echo -e "${RED}❌ ${category^} tests failed${NC}"
                FAILURES=$((FAILURES + 1))
            fi
        done

        EXIT_CODE=$FAILURES
        ;;

    single)
        # Run a single test file
        if [ -z "$2" ]; then
            echo -e "${RED}Please specify a test file${NC}"
            echo "Usage: $0 single path/to/test_file.py"
            exit 1
        fi
        echo -e "${CYAN}Running single test: $2${NC}"
        python -m pytest "$2" -v --tb=short --disable-warnings
        EXIT_CODE=$?
        ;;

    *)
        echo -e "${RED}❌ Invalid test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: $0 [test_type] [coverage] [verbose]"
        echo ""
        echo "Test Types:"
        echo "  quick       - Run quick smoke tests (default)"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests only"
        echo "  system      - Run system tests only"
        echo "  billing     - Run all billing-related tests"
        echo "  rag         - Run RAG pipeline tests"
        echo "  all         - Run all test suites"
        echo "  single      - Run a single test file"
        echo ""
        echo "Options:"
        echo "  coverage    - true/false (default: false)"
        echo "  verbose     - true/false (default: false)"
        echo ""
        echo "Examples:"
        echo "  $0              # Run quick smoke tests"
        echo "  $0 unit         # Run unit tests"
        echo "  $0 all true     # Run all tests with coverage"
        echo "  $0 billing false true  # Run billing tests verbosely"
        echo "  $0 single tests/unit/test_billing_simple.py  # Run single test"
        exit 1
        ;;
esac

# Generate HTML coverage report if coverage was enabled
if [ "$COVERAGE" == "true" ] && [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "\n${CYAN}Generating HTML coverage report...${NC}"
    python -m pytest --cov=app --cov-report=html --no-header --quiet > /dev/null 2>&1 || true
    echo -e "${GREEN}📁 Coverage report: htmlcov/index.html${NC}"
fi

# Print summary statistics
print_stats

# Final summary
echo -e "\n${BLUE}══════════════════════════════════════${NC}"
if [ "$EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}🎉 Tests completed successfully!${NC}"

    # Suggest next steps
    echo -e "\n${CYAN}Next steps:${NC}"
    echo "  • Run more comprehensive tests: $0 all"
    echo "  • Check test coverage: $0 all true"
    echo "  • Run specific category: $0 integration"
else
    echo -e "${RED}⚠️  Some tests failed.${NC}"
    echo -e "\n${CYAN}Debugging tips:${NC}"
    echo "  • Check service logs: docker-compose logs [service-name]"
    echo "  • Run tests verbosely: $0 $TEST_TYPE false true"
    echo "  • Check individual test: $0 single tests/path/to/test.py"
    echo "  • Run diagnostics: ./scripts/diagnose_services.sh"
fi
echo -e "${BLUE}══════════════════════════════════════${NC}\n"

exit $EXIT_CODE