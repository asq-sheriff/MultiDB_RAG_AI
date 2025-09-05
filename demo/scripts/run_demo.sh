#!/bin/bash

# MultiDB Therapeutic AI Chatbot - Demo Runner
# ============================================
# Comprehensive demo launcher with full service stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
DEMO_MODE="databases"  # Default: just databases
FULL_SERVICES=false
REAL_API=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --full-services)
      DEMO_MODE="full"
      FULL_SERVICES=true
      shift
      ;;
    --databases-only)
      DEMO_MODE="databases"
      shift
      ;;
    --real-api)
      REAL_API=true
      shift
      ;;
    --help)
      echo -e "${PURPLE}MultiDB Therapeutic AI Chatbot - Demo Runner${NC}"
      echo
      echo -e "${YELLOW}Usage:${NC}"
      echo "  $0 [OPTIONS]"
      echo
      echo -e "${YELLOW}Options:${NC}"
      echo "  --databases-only    Start only demo databases (default)"
      echo "  --full-services     Start all services (databases + Go microservices + AI services)"
      echo "  --real-api          Enable real API integration with full service stack"
      echo "  --help              Show this help message"
      echo
      echo -e "${YELLOW}Examples:${NC}"
      echo "  $0                          # Start demo databases only"
      echo "  $0 --full-services          # Start complete service architecture"
      echo "  $0 --real-api               # Full stack with real API integration"
      echo
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo -e "${PURPLE}==========================================="
echo -e "🏥 MultiDB Therapeutic AI Chatbot"
echo -e "   Demo Environment Launcher"
echo -e "==========================================${NC}"
echo

if [ "$DEMO_MODE" = "full" ]; then
    echo -e "${CYAN}🚀 Starting Full Service Stack Demo${NC}"
    echo -e "${BLUE}Services: Databases + Go Microservices + AI Services + API Gateway${NC}"
elif [ "$DEMO_MODE" = "databases" ]; then
    echo -e "${CYAN}🗄️  Starting Database-Only Demo${NC}"
    echo -e "${BLUE}Services: PostgreSQL + MongoDB + Redis + ScyllaDB${NC}"
fi

if [ "$REAL_API" = true ]; then
    echo -e "${GREEN}🌐 Real API Integration: Enabled${NC}"
else
    echo -e "${YELLOW}🎭 Demo Mode: Simulation + Real Data${NC}"
fi

echo

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is required but not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is required but not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites satisfied${NC}"

# Set up directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${DEMO_DIR}/.." && pwd)"
cd "${DEMO_DIR}"

# Select appropriate docker-compose file
if [ "$DEMO_MODE" = "full" ]; then
    COMPOSE_FILE="config/docker-compose.demo-full.yml"
    echo -e "${BLUE}📦 Using full service stack: ${COMPOSE_FILE}${NC}"
else
    COMPOSE_FILE="config/docker-compose.demo.yml"
    echo -e "${BLUE}📦 Using database-only stack: ${COMPOSE_FILE}${NC}"
fi

# Stop any existing demo containers
echo -e "${YELLOW}🛑 Stopping existing demo containers...${NC}"
docker-compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

# Start Docker databases
echo -e "${BLUE}🚀 Starting demo databases...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d

# Wait for core databases first
echo -e "${YELLOW}⏳ Waiting for databases to initialize...${NC}"

# Wait functions
wait_for_postgres() {
    echo -e "${BLUE}🐘 Waiting for PostgreSQL...${NC}"
    timeout=60
    counter=0
    while ! docker exec demo-v1-postgres pg_isready -U demo_v1_user -d demo_v1_chatbot_app; do
        sleep 2
        counter=$((counter + 2))
        if [ $counter -ge $timeout ]; then
            echo -e "${RED}❌ PostgreSQL failed to start within ${timeout}s${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}✅ PostgreSQL ready${NC}"
}

wait_for_mongodb() {
    echo -e "${BLUE}🍃 Waiting for MongoDB...${NC}"
    timeout=60
    counter=0
    while ! docker exec demo-v1-mongodb mongosh --eval "db.runCommand('ping').ok" --quiet; do
        sleep 3
        counter=$((counter + 3))
        if [ $counter -ge $timeout ]; then
            echo -e "${RED}❌ MongoDB failed to start within ${timeout}s${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}✅ MongoDB ready${NC}"
}

wait_for_redis() {
    echo -e "${BLUE}🗄️ Waiting for Redis...${NC}"
    timeout=30
    counter=0
    while ! docker exec demo-v1-redis redis-cli ping; do
        sleep 2
        counter=$((counter + 2))
        if [ $counter -ge $timeout ]; then
            echo -e "${RED}❌ Redis failed to start within ${timeout}s${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}✅ Redis ready${NC}"
}

# Wait for databases
wait_for_postgres &
wait_for_mongodb &
wait_for_redis &
wait

echo -e "${GREEN}✅ All databases are ready!${NC}"

# Initialize ScyllaDB keyspace and tables (required for chat-history service)
echo -e "${BLUE}🗄️  Initializing ScyllaDB keyspace and tables...${NC}"
bash "${SCRIPT_DIR}/init_scylladb.sh"

# Initialize PostgreSQL schemas
echo -e "${BLUE}🗄️  Initializing PostgreSQL schemas...${NC}"
POSTGRES_USER=demo_v1_user POSTGRES_PASSWORD=demo_secure_password_v1 POSTGRES_DB=demo_v1_chatbot_app POSTGRES_PORT=5433 python3 -c "
import asyncio
import asyncpg

async def create_schemas():
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        user='demo_v1_user', 
        password='demo_secure_password_v1',
        database='demo_v1_chatbot_app'
    )
    schemas = ['demo_v1_auth', 'demo_v1_compliance', 'demo_v1_app', 'demo_v1_memory', 'demo_v1_knowledge']
    for schema in schemas:
        await conn.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')
    await conn.close()
    print('✅ PostgreSQL schemas ready')

asyncio.run(create_schemas())
"

# Seed demo data
echo -e "${BLUE}🌱 Seeding demo data...${NC}"
cd "${SCRIPT_DIR}"
POSTGRES_USER=demo_v1_user POSTGRES_PASSWORD=demo_secure_password_v1 POSTGRES_DB=demo_v1_chatbot_app POSTGRES_PORT=5433 REDIS_PORT=6380 MONGO_HOST=localhost MONGO_PORT=27018 MONGO_USER=root MONGO_PASSWORD=demo_example_v1 MONGO_DB=chatbot_app python3 seed_demo_data.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Demo data seeded successfully${NC}"
else
    echo -e "${RED}❌ Demo data seeding failed${NC}"
    exit 1
fi

cd "${PROJECT_ROOT}"

# Start local services if full mode
if [ "$DEMO_MODE" = "full" ]; then
    echo -e "${BLUE}🚀 Starting local application services...${NC}"
    bash "${SCRIPT_DIR}/start_local_services.sh"
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠️  Some local services failed, check logs for details${NC}"
    fi
fi

echo
echo -e "${PURPLE}🎉 Demo environment ready!${NC}"
echo

if [ "$DEMO_MODE" = "full" ]; then
    echo -e "${YELLOW}📋 Full Service Stack Summary:${NC}"
    echo -e "${CYAN}Databases:${NC}"
    echo -e "   • PostgreSQL: localhost:5433"
    echo -e "   • MongoDB: localhost:27018"
    echo -e "   • Redis: localhost:6380"
    echo -e "   • ScyllaDB: localhost:9045"
    echo
    echo -e "${CYAN}AI Services (Host):${NC}"
    echo -e "   • Embedding Service: localhost:8005 (BGE-Large, GPU-accelerated)"
    echo -e "   • Generation Service: localhost:8006 (Qwen2.5-7B, GPU-accelerated)"
    echo
    echo -e "${CYAN}Application Services (Docker):${NC}"
    echo -e "   • Main API: localhost:8000"
    echo -e "   • Search Service: localhost:8001 (RAG Pipeline)"
    echo -e "   • Content Safety: localhost:8007 (PHI Detection)"
    echo
    echo -e "${CYAN}Go Microservices:${NC}"
    echo -e "   • Auth & RBAC: localhost:8080"
    echo -e "   • Audit Logging: localhost:8084"
    echo -e "   • Consent Management: localhost:8083"
    echo -e "   • Chat History: localhost:8085"
    echo -e "   • API Gateway: localhost:8090"
    echo
    echo -e "${GREEN}🚀 Ready for real API demo:${NC}"
    echo -e "   cd demo/ui && python interactive_demo.py --use-real-data"
    echo -e "${BLUE}🌐 All services accessible via API Gateway: http://localhost:8090${NC}"
else
    echo -e "${YELLOW}📋 Database Demo Summary:${NC}"
    echo -e "   • PostgreSQL: localhost:5433"
    echo -e "   • MongoDB: localhost:27018"
    echo -e "   • Redis: localhost:6380"
    echo -e "   • ScyllaDB: localhost:9045"
    echo
    echo -e "${GREEN}🚀 Ready for database demo:${NC}"
    echo -e "   cd demo/ui && python interactive_demo.py --use-real-data"
    echo
    echo -e "${BLUE}📚 To start full services later:${NC}"
    echo -e "   ./scripts/run_demo.sh --full-services"
fi

echo
echo -e "${BLUE}📚 Additional commands:${NC}"
echo -e "   • View logs: docker-compose -f $COMPOSE_FILE logs"
echo -e "   • Stop demo: docker-compose -f $COMPOSE_FILE down"
echo -e "   • Reset data: docker-compose -f $COMPOSE_FILE down -v"
echo