#!/bin/bash

# Stop All Demo Services
# ======================
# Stops all local services and Docker containers for demo

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛑 Stopping All Demo Services...${NC}"

# Change to demo directory
cd "$(dirname "$0")/.."

# Stop host AI services
echo -e "${YELLOW}Stopping AI services...${NC}"
./scripts/stop_host_ai_services.sh

# Stop local Go and Python services
echo -e "${YELLOW}Stopping local services...${NC}"

# Function to stop service by PID file or port
stop_service() {
    local service_name=$1
    local port=$2
    local pid_file="/tmp/demo_${service_name}_pid"
    
    if [ -f "${pid_file}" ]; then
        local pid=$(cat "${pid_file}")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -e "${BLUE}Stopping ${service_name} (PID: ${pid})...${NC}"
            kill "${pid}" 2>/dev/null || true
            sleep 1
            if kill -0 "${pid}" 2>/dev/null; then
                kill -9 "${pid}" 2>/dev/null || true
            fi
            echo -e "${GREEN}✅ ${service_name} stopped${NC}"
        fi
        rm -f "${pid_file}"
    fi
    
    # Also kill any process on the port
    lsof -ti:${port} | xargs kill -9 2>/dev/null || true
}

# Stop all local services
stop_service "main-api" "8000"
stop_service "search-service" "8001" 
stop_service "content-safety" "8007"
stop_service "auth-rbac" "8080"
stop_service "audit-logging" "8084"
stop_service "consent" "8083"
stop_service "chat-history" "8085"
stop_service "api-gateway" "8090"

# Stop Docker services
echo -e "${YELLOW}Stopping Docker services...${NC}"
docker-compose -f config/docker-compose.demo.yml down 2>/dev/null || true
docker-compose -f config/docker-compose.demo-full.yml down 2>/dev/null || true

# Clean up log files
echo -e "${BLUE}🧹 Cleaning up log files...${NC}"
rm -rf /tmp/demo_service_logs
rm -rf /tmp/demo_ai_logs

echo -e "${GREEN}✅ All demo services stopped${NC}"
echo