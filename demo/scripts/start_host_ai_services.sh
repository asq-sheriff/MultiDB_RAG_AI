#!/bin/bash

# Start Host AI Services for Demo
# ===============================
# Starts GPU-accelerated AI services on host for demo environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}==========================================="
echo -e "🤖 Starting Host AI Services for Demo"
echo -e "==========================================${NC}"
echo

# Change to project root
cd "$(dirname "$0")/../.."

# Check Python environment
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    exit 1
fi

echo -e "${BLUE}🔧 Checking AI service dependencies...${NC}"

# Check if host service requirements are installed
python3 -c "
import sys
try:
    import torch
    import FlagEmbedding
    import aiohttp
    import fastapi
    print('✅ All required packages available')
except ImportError as e:
    print(f'❌ Missing package: {e}')
    print('Install with: pip install -r host_services/requirements_host.txt')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}📦 Installing host service requirements...${NC}"
    pip install -r host_services/requirements_host.txt
fi

# Set demo environment variables for AI services
export DEMO_MODE=1
export REDIS_HOST=localhost
export REDIS_PORT=6380
export REDIS_DB=2
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_USER=demo_v1_user
export POSTGRES_PASSWORD=demo_secure_password_v1
export POSTGRES_DB=demo_v1_chatbot_app
export MONGO_HOST=localhost
export MONGO_PORT=27018
export MONGO_USER=root
export MONGO_PASSWORD=demo_example_v1
export MONGO_DB=demo_v1_chatbot_app

echo -e "${BLUE}🚀 Starting AI services...${NC}"

# Check if llama-server is available for generation service
if command -v llama-server &> /dev/null; then
    echo -e "${GREEN}✅ llama-server available for generation service${NC}"
    
    # Check if llama-server is running on port 8004
    if ! curl -s -f http://localhost:8004/health > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  llama-server not running on port 8004${NC}"
        
        # Check if model and startup script exist
        if [ -f ~/models/start_qwen.sh ] && [ -f ~/models/Qwen2-1.5B-Instruct-Q4_K_M.gguf ]; then
            echo -e "${BLUE}🚀 Starting llama-server for full generation capabilities...${NC}"
            # Start llama-server in background
            nohup ~/models/start_qwen.sh > /tmp/demo_ai_logs/llama_server.log 2>&1 &
            llama_pid=$!
            echo "Started llama-server (PID: ${llama_pid})"
            
            # Wait for llama-server to be ready
            echo -e "${YELLOW}Waiting for llama-server to load model...${NC}"
            for i in {1..60}; do  # llama models take time to load
                if curl -s -f http://localhost:8004/health > /dev/null 2>&1; then
                    echo -e "${GREEN}✅ llama-server ready on port 8004${NC}"
                    break
                fi
                sleep 2
            done
        else
            echo -e "${BLUE}💡 To enable full generation capabilities:${NC}"
            echo -e "   1. Run: ./host_services/setup_generation.sh (one-time setup)"
            echo -e "   2. Restart demo with: ./demo/scripts/run_demo.sh --full-services"
            echo -e "${BLUE}📍 Generation service will run in degraded mode${NC}"
        fi
    else
        echo -e "${GREEN}✅ llama-server ready on port 8004${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  llama-server not installed${NC}"
    echo -e "${BLUE}💡 For full generation capabilities, run: ./host_services/setup_generation.sh${NC}"
fi

echo

# Function to start service in background
start_service() {
    local service_name=$1
    local script_path=$2
    local port=$3
    local log_file=$4
    
    echo -e "${BLUE}Starting ${service_name} on port ${port}...${NC}"
    
    # Kill any existing process on the port
    lsof -ti:${port} | xargs kill -9 2>/dev/null || true
    
    # Start service in background with port environment variable
    if [[ "${service_name}" == "embedding-service" ]]; then
        nohup env EMBEDDING_SERVICE_PORT=${port} python3 ${script_path} > ${log_file} 2>&1 &
    elif [[ "${service_name}" == "generation-service" ]]; then
        nohup env GENERATION_SERVICE_PORT=${port} LLAMA_SERVER_URL=http://localhost:8004 python3 ${script_path} > ${log_file} 2>&1 &
    else
        nohup python3 ${script_path} > ${log_file} 2>&1 &
    fi
    local pid=$!
    
    # Wait for service to start
    echo -e "${YELLOW}Waiting for ${service_name} to start...${NC}"
    for i in {1..30}; do
        if curl -s -f http://localhost:${port}/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${service_name} started successfully (PID: ${pid})${NC}"
            echo "${pid}" > "/tmp/demo_${service_name}_pid"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ ${service_name} failed to start${NC}"
    cat ${log_file}
    return 1
}

# Create logs directory
mkdir -p /tmp/demo_ai_logs

# Start embedding service (BGE Large)
start_service "embedding-service" "host_services/embed_server.py" "8005" "/tmp/demo_ai_logs/embedding.log"

# Start generation service (Qwen) - separate from llama-server
start_service "generation-service" "host_services/generation_server.py" "8006" "/tmp/demo_ai_logs/generation.log"

echo -e "${CYAN}🐍 Starting Main API (FastAPI Gateway)...${NC}"

# Start Main API (FastAPI) with uvicorn and demo environment
echo -e "${BLUE}Starting main-api on port 8000...${NC}"
# Kill any existing process on the port
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start service with uvicorn and demo environment
nohup env POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=demo_v1_chatbot_app POSTGRES_USER=demo_v1_user POSTGRES_PASSWORD=demo_secure_password_v1 ENABLE_POSTGRESQL=true ENABLE_MONGODB=true MONGO_HOST=localhost MONGO_PORT=27018 MONGO_DB=demo_v1_chatbot_app MONGO_USER=root MONGO_PASSWORD=demo_example_v1 REDIS_HOST=localhost REDIS_PORT=6380 EMBEDDING_SERVICE_URL=http://localhost:8005 GENERATION_SERVICE_URL=http://localhost:8006 uvicorn ai_services.main:app --host 0.0.0.0 --port 8000 > "/tmp/demo_ai_logs/main_api.log" 2>&1 &
pid=$!

# Wait for service to start
echo -e "${YELLOW}Waiting for main-api to start...${NC}"
for i in {1..30}; do
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ main-api started successfully (PID: ${pid})${NC}"
        echo "${pid}" > "/tmp/demo_main_api_pid"
        break
    fi
    sleep 2
done

echo
echo -e "${GREEN}🎉 Host AI Services + Main API Started Successfully!${NC}"
echo
echo -e "${YELLOW}📋 Services Summary:${NC}"
echo -e "   • Embedding Service: http://localhost:8005"
echo -e "   • Generation Service: http://localhost:8006"
echo -e "   • Main API Gateway: http://localhost:8000"
echo -e "   • Llama Server (if available): http://localhost:8004"
echo
echo -e "${BLUE}📊 Service Status:${NC}"
curl -s http://localhost:8005/health | jq . 2>/dev/null || echo "   • Embedding: Starting..."
curl -s http://localhost:8006/health | jq . 2>/dev/null || echo "   • Generation: Starting..."
curl -s http://localhost:8000/health | jq . 2>/dev/null || echo "   • Main API: Starting..."
curl -s http://localhost:8004/health | jq . 2>/dev/null || echo "   • Llama Server: Not running (optional)"
echo
echo -e "${YELLOW}📄 Log Files:${NC}"
echo -e "   • Embedding: /tmp/demo_ai_logs/embedding.log"
echo -e "   • Generation: /tmp/demo_ai_logs/generation.log"
echo -e "   • Main API: /tmp/demo_ai_logs/main_api.log"
echo
echo -e "${BLUE}🛑 To stop services later:${NC}"
echo -e "   ./demo/scripts/stop_host_ai_services.sh"
echo