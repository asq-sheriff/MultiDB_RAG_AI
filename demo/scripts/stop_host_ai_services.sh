#!/bin/bash

# Stop Host AI Services for Demo
# ==============================
# Stops all host AI services started for demo

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛑 Stopping Host AI Services...${NC}"

# Function to stop service by PID file
stop_service() {
    local service_name=$1
    local port=$2
    local pid_file="/tmp/demo_${service_name}_pid"
    
    if [ -f "${pid_file}" ]; then
        local pid=$(cat "${pid_file}")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -e "${YELLOW}Stopping ${service_name} (PID: ${pid})...${NC}"
            kill "${pid}" 2>/dev/null || true
            sleep 2
            if kill -0 "${pid}" 2>/dev/null; then
                echo -e "${YELLOW}Force killing ${service_name}...${NC}"
                kill -9 "${pid}" 2>/dev/null || true
            fi
            echo -e "${GREEN}✅ ${service_name} stopped${NC}"
        else
            echo -e "${YELLOW}${service_name} already stopped${NC}"
        fi
        rm -f "${pid_file}"
    else
        echo -e "${YELLOW}No PID file for ${service_name}, checking port...${NC}"
        # Kill any process on the port
        lsof -ti:${port} | xargs kill -9 2>/dev/null || true
    fi
}

# Stop services
stop_service "embedding-service" "8005"
stop_service "generation-service" "8006"

# Also kill any remaining processes on the ports
echo -e "${BLUE}🧹 Cleaning up any remaining processes...${NC}"
lsof -ti:8005 | xargs kill -9 2>/dev/null || true
lsof -ti:8006 | xargs kill -9 2>/dev/null || true

# Clean up log files
rm -f /tmp/demo_ai_logs/embedding.log
rm -f /tmp/demo_ai_logs/generation.log
rmdir /tmp/demo_ai_logs 2>/dev/null || true

echo -e "${GREEN}✅ All host AI services stopped${NC}"
echo