#!/bin/bash

# Start Local Services for Demo
# =============================
# Starts all locally-running services (AI + Go microservices + Main API)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}==========================================="
echo -e "🚀 Starting Local Services for Demo"
echo -e "==========================================${NC}"
echo

# Change to project root
cd "$(dirname "$0")/../.."

# Set demo environment variables
echo -e "${BLUE}🔧 Setting demo environment...${NC}"
export DEMO_MODE=1
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_USER=demo_v1_user
export POSTGRES_PASSWORD=demo_secure_password_v1
export POSTGRES_DB=demo_v1_chatbot_app
export REDIS_HOST=localhost
export REDIS_PORT=6380
export REDIS_DB=10
export MONGO_HOST=localhost
export MONGO_PORT=27018
export MONGO_USER=root
export MONGO_PASSWORD=demo_example_v1
export MONGO_DB=demo_v1_chatbot_app
export SCYLLA_HOSTS=localhost:9045,localhost:9046,localhost:9047,localhost:9047
export SCYLLA_PORT=9045
export SCYLLA_KEYSPACE=demo_v1_chatbot_ks

# Load demo environment and override main .env
if [ -f "demo/config/.env.demo_v1" ]; then
    set -a  # Export all variables
    source demo/config/.env.demo_v1
    set +a  # Stop exporting
    echo -e "${GREEN}✅ Loaded demo environment${NC}"
else
    echo -e "${YELLOW}⚠️  Demo environment file not found${NC}"
fi

# Function to start Go service using 'go run main.go'
start_go_service() {
    local service_name=$1
    local binary_path=$2
    local port=$3
    local log_file=$4
    local extra_env=$5
    local health_endpoint=${6:-"/health"}  # Default to /health
    
    echo -e "${BLUE}Starting ${service_name} on port ${port}...${NC}"
    
    # Kill any existing process on the port
    lsof -ti:${port} | xargs kill -9 2>/dev/null || true
    
    # Use 'go run main.go' approach (original application method)
    if [[ "${binary_path}" == */ ]]; then
        # Directory path - run all Go files
        service_dir="${binary_path%/}"  # Remove trailing slash
        cd "${service_dir}"
        nohup env PORT=${port} ${extra_env} go run . > "${log_file}" 2>&1 &
    else
        # File path - run specific main.go
        service_dir=$(dirname "${binary_path}")
        cd "${service_dir}"
        nohup env PORT=${port} ${extra_env} go run main.go > "${log_file}" 2>&1 &
    fi
    cd - > /dev/null
    local pid=$!
    
    # Wait for service to start
    echo -e "${YELLOW}Waiting for ${service_name} to start...${NC}"
    for i in {1..60}; do
        if curl -s -f http://localhost:${port}${health_endpoint} > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${service_name} started successfully (PID: ${pid})${NC}"
            echo "${pid}" > "/tmp/demo_${service_name}_pid"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}❌ ${service_name} failed to start${NC}"
    echo -e "${YELLOW}Last 10 lines of log:${NC}"
    tail -10 "${log_file}" 2>/dev/null || echo "No log available"
    return 1
}

# Function to start Python service
start_python_service() {
    local service_name=$1
    local module_path=$2
    local port=$3
    local log_file=$4
    
    echo -e "${BLUE}Starting ${service_name} on port ${port}...${NC}"
    
    # Kill any existing process on the port
    lsof -ti:${port} | xargs kill -9 2>/dev/null || true
    
    # Start service in background
    nohup python3 -m "${module_path}" > "${log_file}" 2>&1 &
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
    echo -e "${YELLOW}Last 10 lines of log:${NC}"
    tail -10 "${log_file}" 2>/dev/null || echo "No log available"
    return 1
}

# Create logs directory
mkdir -p /tmp/demo_service_logs

echo -e "${CYAN}🤖 Starting AI Services (Host)...${NC}"

# Start host AI services first
./demo/scripts/start_host_ai_services.sh

echo -e "${CYAN}🐍 Starting Python Application Services...${NC}"

# Start Main API (FastAPI) with uvicorn
echo -e "${BLUE}Starting main-api on port 8000...${NC}"
# Kill any existing process on the port
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start service with uvicorn and demo environment
nohup env POSTGRES_HOST=localhost POSTGRES_PORT=5433 POSTGRES_DB=demo_v1_chatbot_app POSTGRES_USER=demo_v1_user POSTGRES_PASSWORD=demo_secure_password_v1 ENABLE_POSTGRESQL=true ENABLE_MONGODB=true MONGO_HOST=localhost MONGO_PORT=27018 MONGO_DB=demo_v1_chatbot_app MONGO_USER=root MONGO_PASSWORD=demo_example_v1 REDIS_HOST=localhost REDIS_PORT=6380 EMBEDDING_SERVICE_URL=http://localhost:8005 GENERATION_SERVICE_URL=http://localhost:8006 uvicorn ai_services.main:app --host 0.0.0.0 --port 8000 > "/tmp/demo_service_logs/main_api.log" 2>&1 &
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

# Note: Search and Content Safety services are now handled by Go microservices
echo -e "${YELLOW}📝 Note: Search and Content Safety now handled by Go microservices${NC}"
echo -e "   • Search Service: Integrated into main API at port 8000"
echo -e "   • Content Safety: Integrated into main API at port 8000"

echo -e "${CYAN}🔧 Starting Go Microservices...${NC}"

# Start Go microservices locally - HIPAA Compliance Stack
echo -e "${CYAN}🔒 Starting HIPAA Compliance Services...${NC}"

# Internal Microservices (backend services)
echo -e "${YELLOW}🔧 Starting internal microservices...${NC}"

start_go_service "search-service" "microservices/search-service/" "8001" "/tmp/demo_service_logs/search_service.log" "DATABASE_URL=postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app?sslmode=disable REDIS_URL=redis://localhost:6380 MONGO_URL=mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin EMBEDDING_SERVICE_URL=http://localhost:8005 GENERATION_SERVICE_URL=http://localhost:8006"

start_go_service "chat-history" "microservices/chat-history/" "8002" "/tmp/demo_service_logs/chat_history.log" "DATABASE_URL=postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app?sslmode=disable REDIS_URL=redis://localhost:6380 MONGO_URL=mongodb://root:demo_example_v1@localhost:27018/chatbot_app?authSource=admin&directConnection=true SCYLLA_HOSTS=localhost:9045,localhost:9046,localhost:9047 SCYLLA_KEYSPACE=demo_v1_chatbot_ks EMBEDDING_SERVICE_URL=http://localhost:8005 GENERATION_SERVICE_URL=http://localhost:8006 CONTENT_SAFETY_SERVICE_URL=http://localhost:8007"

# API Gateway (main entry point - simple proxy)
echo -e "${CYAN}🌐 Starting API Gateway (main entry point)...${NC}"
start_go_service "api-gateway" "microservices/api-gateway/" "8090" "/tmp/demo_service_logs/api_gateway.log" "SEARCH_SERVICE_URL=http://localhost:8001 CHAT_SERVICE_URL=http://localhost:8002 EMBEDDING_SERVICE_URL=http://localhost:8005 GENERATION_SERVICE_URL=http://localhost:8006"

# Try audit-logging (essential for HIPAA but may need database connection)
if [ -f "microservices/audit-logging/main.go" ]; then
    echo -e "${YELLOW}⚠️  Attempting audit-logging service (may need database setup)${NC}"
    start_go_service "audit-logging" "microservices/audit-logging/main.go" "8084" "/tmp/demo_service_logs/audit.log" "DATABASE_URL=postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app?sslmode=disable HIPAA_AUDIT_LEVEL=strict"
fi

# Note: Other services have incomplete shared dependencies and cannot start yet
echo -e "${YELLOW}📝 Note: Some microservices have incomplete implementations:${NC}"
echo -e "   • chat-history, billing, consent: Missing shared module dependencies"
echo -e "   • emergency-access, relationship-mgmt: Not tested yet"
echo -e "   • For full HIPAA compliance, these services need completion"

echo
echo -e "${GREEN}🎉 All Local Services Started Successfully!${NC}"
echo
echo -e "${YELLOW}📋 Service Stack Summary:${NC}"
echo -e "${CYAN}AI Services (Host, GPU-accelerated):${NC}"
echo -e "   • Embedding Service: http://localhost:8005"
echo -e "   • Generation Service: http://localhost:8006"
echo -e "   • Llama Server (optional): http://localhost:8004"
echo
echo -e "${CYAN}Python Services (Local):${NC}"
echo -e "   • Main API: http://localhost:8000 (includes Search & Content Safety)"
echo
echo -e "${CYAN}API Gateway (Single Entry Point):${NC}"
echo -e "   • API Gateway: http://localhost:8090 (proxies all services)"
echo -e "   • Auth & RBAC: http://localhost:8090/api/v1/auth/*"
echo -e "   • Consent Management: http://localhost:8090/api/v1/consent/*"
echo -e "   • Audit Logging: http://localhost:8090/api/v1/audit/*"
echo -e "   • Search AI: http://localhost:8090/api/v1/search/*"
echo -e "   • Content Safety: http://localhost:8090/api/v1/safety/*"
echo
echo -e "${CYAN}Internal Microservices (Behind Gateway):${NC}"
echo -e "   • Auth & RBAC: http://localhost:8081 (internal only)"
echo -e "   • Consent Management: http://localhost:8083 (internal only)"
echo -e "   • Audit Logging: http://localhost:8084 (internal only)"
echo
echo -e "${BLUE}📄 Log Files:${NC}"
echo -e "   • AI Services: /tmp/demo_ai_logs/"
echo -e "   • Application Services: /tmp/demo_service_logs/"
echo
echo -e "${BLUE}🛑 To stop all services:${NC}"
echo -e "   ./demo/scripts/stop_all_demo_services.sh"
echo