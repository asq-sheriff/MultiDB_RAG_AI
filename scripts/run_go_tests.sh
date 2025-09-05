#!/bin/bash

# Go Microservices Test Runner for Lilo_EmotionalAI_Backend
# Enhanced testing for Go services after Python service removal

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICES_DIR="${PROJECT_ROOT}/microservices"
REPORTS_DIR="${PROJECT_ROOT}/test_reports/go_services"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Options
RUN_COVERAGE=false
VERBOSE=false
SPECIFIC_SERVICE=""

# Go services (updated list for new structure)
GO_SERVICES=(
    "auth-rbac"
    "billing"
    "api-gateway"
    "audit-logging"
    "relationship-management"
    "user-subscription"
    "chat-history"
    "background-tasks"
    "consent"
    "emergency-access"
)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Go Services Test Runner"
            echo "Usage: $0 [--coverage] [--verbose] [service-name]"
            exit 0
            ;;
        *)
            SPECIFIC_SERVICE="$1"
            shift
            ;;
    esac
done

# Setup environment
setup_environment() {
    echo -e "${CYAN}🔧 Setting up Go test environment...${NC}"
    mkdir -p "$REPORTS_DIR"
    
    export TESTING=true
    export POSTGRES_HOST=localhost
    export POSTGRES_PORT=5432
    export POSTGRES_USER=chatbot_user
    export POSTGRES_PASSWORD=secure_password
    export POSTGRES_DB=chatbot_app
    export REDIS_URL=redis://localhost:6379
    
    if ! command -v go &> /dev/null; then
        echo -e "${RED}❌ Go not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Go detected: $(go version | awk '{print $3}')${NC}"
}

# Run tests for service
run_service_tests() {
    local service="$1"
    local service_dir="${SERVICES_DIR}/${service}"
    
    if [[ ! -d "$service_dir" ]]; then
        echo -e "${RED}❌ Service not found: $service${NC}"
        return 1
    fi
    
    echo -e "${PURPLE}🐹 Testing: $service${NC}"
    cd "$service_dir"
    
    local passed=0
    local total=0
    
    # Unit tests
    echo -e "${CYAN}🧪 Running unit tests...${NC}"
    if go test -short ./...; then
        echo -e "${GREEN}✅ Unit tests passed${NC}"
        ((passed++))
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
    fi
    ((total++))
    
    # Integration tests
    echo -e "${CYAN}🔗 Running integration tests...${NC}"
    if go test -tags=integration ./...; then
        echo -e "${GREEN}✅ Integration tests passed${NC}"
        ((passed++))
    else
        echo -e "${RED}❌ Integration tests failed${NC}"
    fi
    ((total++))
    
    # Coverage
    if [[ "$RUN_COVERAGE" == true ]]; then
        echo -e "${CYAN}📊 Running coverage...${NC}"
        if go test -cover -coverprofile=coverage.out ./...; then
            local coverage=$(go tool cover -func=coverage.out | grep total | awk '{print $3}')
            echo -e "${BLUE}📈 Coverage: $coverage${NC}"
            go tool cover -html=coverage.out -o "${REPORTS_DIR}/${service}_coverage.html"
        fi
    fi
    
    echo -e "${PURPLE}📋 $service: $passed/$total tests passed${NC}"
    cd "$PROJECT_ROOT"
    
    return $((total - passed))
}

# Run all tests
run_all_tests() {
    echo -e "${CYAN}🚀 Testing all Go services...${NC}"
    
    local total_services=0
    local passed_services=0
    
    for service in "${GO_SERVICES[@]}"; do
        echo -e "\n================================================================"
        
        if run_service_tests "$service"; then
            ((passed_services++))
        fi
        ((total_services++))
        
        echo -e "================================================================"
    done
    
    # Summary
    local success_rate=$((passed_services * 100 / total_services))
    echo -e "\n${BLUE}📊 Results: $passed_services/$total_services services passed ($success_rate%)${NC}"
    
    if [[ $success_rate -ge 80 ]]; then
        echo -e "${GREEN}🏆 Go services are ready${NC}"
        return 0
    else
        echo -e "${RED}🔥 Go services need attention${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${CYAN}🐹 Go Microservices Test Runner${NC}"
    echo -e "${CYAN}Updated for enhanced Go architecture${NC}"
    
    setup_environment
    
    if [[ -n "$SPECIFIC_SERVICE" ]]; then
        run_service_tests "$SPECIFIC_SERVICE"
    else
        run_all_tests
    fi
}

main "$@"