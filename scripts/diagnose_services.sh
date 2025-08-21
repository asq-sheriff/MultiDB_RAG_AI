#!/bin/bash
# scripts/diagnose_services.sh - Diagnose service connectivity issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}     Service Connectivity Diagnostic Tool       ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}\n"

# Function to test port connectivity
test_port() {
    local service=$1
    local host=$2
    local port=$3

    echo -e "${YELLOW}Testing $service on $host:$port...${NC}"

    # Method 1: Using Python (most reliable)
    if python3 -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
result = sock.connect_ex(('$host', $port))
sock.close()
exit(0 if result == 0 else 1)
" 2>/dev/null; then
        echo -e "  ${GREEN}✓ Python socket test: Connected${NC}"
    else
        echo -e "  ${RED}✗ Python socket test: Failed${NC}"
    fi

    # Method 2: Using nc if available
    if command -v nc &> /dev/null; then
        if nc -zv $host $port 2>&1 | grep -q "succeeded\|connected"; then
            echo -e "  ${GREEN}✓ Netcat test: Connected${NC}"
        else
            echo -e "  ${RED}✗ Netcat test: Failed${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ Netcat not installed (skipping)${NC}"
    fi

    # Method 3: Using telnet if available
    if command -v telnet &> /dev/null; then
        if timeout 2 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
            echo -e "  ${GREEN}✓ Telnet test: Connected${NC}"
        else
            echo -e "  ${RED}✗ Telnet test: Failed${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ Telnet not available (skipping)${NC}"
    fi

    echo ""
}

# Check Docker daemon
echo -e "${CYAN}1. Docker Status:${NC}"
if docker version > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker daemon is running${NC}"
    DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
    echo -e "  Version: $DOCKER_VERSION"
else
    echo -e "${RED}✗ Docker daemon is not running or not accessible${NC}"
    exit 1
fi
echo ""

# Check Docker Compose
echo -e "${CYAN}2. Docker Compose Status:${NC}"
if docker-compose version > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker Compose is available${NC}"
    DC_VERSION=$(docker-compose version --short 2>/dev/null || echo "unknown")
    echo -e "  Version: $DC_VERSION"
else
    echo -e "${RED}✗ Docker Compose is not available${NC}"
fi
echo ""

# List running containers
echo -e "${CYAN}3. Running Containers:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
echo ""

# Test each service
echo -e "${CYAN}4. Service Connectivity Tests:${NC}\n"

# PostgreSQL
test_port "PostgreSQL" "localhost" "5432"

# Test PostgreSQL with Docker exec
echo -e "${YELLOW}Testing PostgreSQL via Docker exec...${NC}"
if docker exec chatbot-postgres pg_isready -U chatbot_user 2>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is ready inside container${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not ready or container not found${NC}"
fi
echo ""

# Redis
test_port "Redis" "localhost" "6379"

# Test Redis with Docker exec
echo -e "${YELLOW}Testing Redis via Docker exec...${NC}"
if docker exec my-redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✓ Redis is responding inside container${NC}"
else
    echo -e "${RED}✗ Redis is not responding or container not found${NC}"
fi
echo ""

# MongoDB
test_port "MongoDB" "localhost" "27017"

# Test MongoDB with Docker exec
echo -e "${YELLOW}Testing MongoDB via Docker exec...${NC}"
if docker exec mongodb-atlas-local mongosh --eval "db.adminCommand('ping')" --quiet 2>/dev/null | grep -q "1"; then
    echo -e "${GREEN}✓ MongoDB is responding inside container${NC}"
else
    echo -e "${YELLOW}⚠ MongoDB may still be initializing${NC}"
fi
echo ""

# ScyllaDB
test_port "ScyllaDB" "localhost" "9042"

# Test ScyllaDB cluster status
echo -e "${YELLOW}Testing ScyllaDB cluster status...${NC}"
if docker exec scylla-node1 nodetool status 2>/dev/null | grep -q "^UN"; then
    NODES_UP=$(docker exec scylla-node1 nodetool status 2>/dev/null | grep -c "^UN" || echo 0)
    echo -e "${GREEN}✓ ScyllaDB cluster has $NODES_UP/3 nodes up${NC}"
else
    echo -e "${YELLOW}⚠ ScyllaDB cluster may still be forming${NC}"
fi
echo ""

# Python connectivity test
echo -e "${CYAN}5. Python Database Connectivity Test:${NC}\n"

python3 << 'EOF'
import sys
import os

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

# Test PostgreSQL with psycopg2
try:
    import asyncpg
    print(f"{GREEN}✓ asyncpg is installed{NC}")
except ImportError:
    print(f"{YELLOW}⚠ asyncpg not installed (PostgreSQL async driver){NC}")

try:
    import psycopg2
    print(f"{GREEN}✓ psycopg2 is installed{NC}")
except ImportError:
    print(f"{YELLOW}⚠ psycopg2 not installed (PostgreSQL driver){NC}")

# Test Redis
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
    r.ping()
    print(f"{GREEN}✓ Redis connection successful from Python{NC}")
except Exception as e:
    print(f"{RED}✗ Redis connection failed from Python: {e}{NC}")

# Test MongoDB
try:
    from pymongo import MongoClient
    client = MongoClient('mongodb://root:example@localhost:27017/', serverSelectionTimeoutMS=2000)
    client.admin.command('ping')
    print(f"{GREEN}✓ MongoDB connection successful from Python{NC}")
except Exception as e:
    print(f"{YELLOW}⚠ MongoDB connection failed from Python: {e}{NC}")

# Test ScyllaDB (if cassandra-driver is installed)
try:
    from cassandra.cluster import Cluster
    cluster = Cluster(['localhost'], port=9042, connect_timeout=2)
    session = cluster.connect()
    print(f"{GREEN}✓ ScyllaDB connection successful from Python{NC}")
    cluster.shutdown()
except ImportError:
    print(f"{YELLOW}⚠ cassandra-driver not installed (ScyllaDB driver){NC}")
except Exception as e:
    print(f"{YELLOW}⚠ ScyllaDB connection failed from Python: {e}{NC}")
EOF

echo -e "\n${CYAN}6. Environment Variables:${NC}"
echo "POSTGRES_HOST=${POSTGRES_HOST:-not set}"
echo "POSTGRES_PORT=${POSTGRES_PORT:-not set}"
echo "REDIS_HOST=${REDIS_HOST:-not set}"
echo "REDIS_PORT=${REDIS_PORT:-not set}"
echo "MONGO_HOST=${MONGO_HOST:-not set}"
echo "MONGO_PORT=${MONGO_PORT:-not set}"
echo "SCYLLA_HOST=${SCYLLA_HOST:-not set}"
echo "SCYLLA_PORT=${SCYLLA_PORT:-not set}"

echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}                  Summary                        ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}\n"

# Quick summary
all_good=true

if docker exec chatbot-postgres pg_isready -U chatbot_user &>/dev/null && \
   python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost', 5432)); s.close()" 2>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL: OK${NC}"
else
    echo -e "${RED}✗ PostgreSQL: Issues detected${NC}"
    all_good=false
fi

if docker exec my-redis redis-cli ping &>/dev/null && \
   python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost', 6379)); s.close()" 2>/dev/null; then
    echo -e "${GREEN}✓ Redis: OK${NC}"
else
    echo -e "${RED}✗ Redis: Issues detected${NC}"
    all_good=false
fi

if docker exec mongodb-atlas-local mongosh --eval "db.adminCommand('ping')" --quiet &>/dev/null; then
    echo -e "${GREEN}✓ MongoDB: OK${NC}"
else
    echo -e "${YELLOW}⚠ MongoDB: May still be initializing${NC}"
fi

if docker exec scylla-node1 nodetool status &>/dev/null; then
    echo -e "${GREEN}✓ ScyllaDB: OK${NC}"
else
    echo -e "${YELLOW}⚠ ScyllaDB: May still be forming cluster${NC}"
fi

echo ""
if [ "$all_good" = true ]; then
    echo -e "${GREEN}All required services are healthy and accessible!${NC}"
    echo -e "${CYAN}You can now run tests with: ./scripts/run_tests.sh${NC}"
else
    echo -e "${YELLOW}Some services have issues. Troubleshooting tips:${NC}"
    echo "1. Wait 30 seconds for services to fully start"
    echo "2. Check Docker logs: docker-compose logs [service-name]"
    echo "3. Restart services: docker-compose restart"
    echo "4. Rebuild if needed: docker-compose down && docker-compose up -d"
fi
echo ""