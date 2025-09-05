---
title: Local Development Infrastructure Guide
owner: DevOps Team
last_updated: 2025-09-03
status: authoritative
---

# Local Development Infrastructure Guide

> **Complete local infrastructure setup and dependency management for the MultiDB Therapeutic AI Chatbot platform**

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Architecture](#infrastructure-architecture)
3. [Quick Setup Commands](#quick-setup-commands)
4. [Service Dependencies](#service-dependencies)
5. [Database Configuration](#database-configuration)
6. [AI Service Dependencies](#ai-service-dependencies)
7. [Environment Management](#environment-management)
8. [Demo vs Production](#demo-vs-production)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **OS**: macOS (ARM64), Linux (x86_64/ARM64), Windows with WSL2
- **Memory**: 8GB minimum, 16GB recommended
- **Storage**: 20GB available for containers and models
- **Docker**: Docker Desktop 4.0+ with Docker Compose V2
- **Network**: Internet access for model downloads (first run)

### Development Tools Installation
```bash
# Required tools (macOS)
brew install docker docker-compose terraform
brew install go python@3.11 node jq curl make

# Required tools (Linux)
sudo apt-get install docker.io docker-compose terraform
sudo apt-get install golang python3.11 nodejs jq curl make

# Optional but recommended
brew install air      # Go hot reload
brew install httpie   # API testing
brew install k9s      # Kubernetes UI (for production)
```

### Python Environment Setup
```bash
# Create isolated virtual environment
python3.11 -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

# Install dependencies by category
pip install -r requirements.txt                            # Main application (190 packages)
pip install -r requirements.demo.txt                       # Demo environment (lightweight)
pip install -r host_services/requirements_host.txt         # GPU services (optional)
```

## Infrastructure Architecture

### Service Port Map
| Service Category | Service Name | Port | Dependencies | Required For |
|-----------------|--------------|------|--------------|--------------|
| **Database Layer** | PostgreSQL | 5432/5433 | Terraform | All services |
| | MongoDB Atlas | 27017/27018 | Terraform | AI services, Search |
| | Redis | 6379/6380 | Terraform | Caching, Sessions |
| | ScyllaDB (3 nodes) | 9042-9044/9045-9047 | Terraform | Chat History |
| **Go Microservices** | API Gateway | 8090 | All services | Entry point |
| | Auth/RBAC | 8080 | PostgreSQL | Authentication |
| | Chat History | 8002 | ScyllaDB | Conversations |
| | Search Service | 8001 | MongoDB, PostgreSQL | RAG pipeline |
| | Billing | 8081 | PostgreSQL | Usage tracking |
| | Audit Logging | 8084 | PostgreSQL | HIPAA compliance |
| | Content Safety | 8007 | None | PHI detection |
| | Consent Management | 8083 | PostgreSQL | HIPAA consent |
| | Emergency Access | 8085 | PostgreSQL | Break-glass access |
| **Python AI Services** | AI Gateway | 8000 | All AI services | AI orchestration |
| | Embedding Service | 8005 | Host services | Vector embeddings |
| | Generation Service | 8006 | Host services | LLM responses |
| **Host Services** | BGE Server | 8008 | GPU (optional) | Embeddings |
| | Qwen Server | 8009 | GPU (optional) | Generation |
| | Llama Server | 8004 | GPU (optional) | Alternative LLM |

### Service Dependencies Chain
```
Client Request
    ↓
API Gateway (8090) ──┐
                     ├──→ Auth/RBAC (8080) ──→ PostgreSQL
                     ├──→ AI Gateway (8000) ──┐
                     │                        ├──→ Search Service (8001) ──→ MongoDB
                     │                        │                           ├──→ Redis (cache)
                     │                        ├──→ Embedding Service (8005) ──→ BGE Host (8008)
                     │                        └──→ Generation Service (8006) ──→ Qwen Host (8009)
                     ├──→ Chat History (8002) ──→ ScyllaDB
                     └──→ Audit Logging (8084) ──→ PostgreSQL
```

## Quick Setup Commands

### First-Time Setup
```bash
# Complete infrastructure setup (20 services)
make setup                  # Install dependencies, create .env
make infrastructure        # Deploy 4 databases via Terraform
make database             # Initialize schemas and migrations
make start                # Start all 20 services (12 Go + 6 Python AI + 2 GPU host)
make seed                 # Seed healthcare knowledge base (therapeutic content)
make health               # Verify all 20 services healthy
make test                 # Run quick validation tests (9 categories)
```

### Daily Development Workflow
```bash
make dev                  # Start with auto-reload
make test                 # Quick validation (3-5 min)
make logs                 # View all service logs
make health               # Check service health

# Database operations
make db-reset             # Reset all databases
make db-backup           # Backup development data
make db-restore          # Restore from backup
```

### Demo Environment Setup
```bash
# Option 1: Full service demo
./demo/scripts/run_demo.sh --full-services

# Option 2: Database-only demo
./demo/scripts/run_demo.sh --databases-only

# Option 3: Persistent data (fast restart)
cd demo && docker-compose -f config/docker-compose.demo-full.yml up -d
cd .. && ./demo/scripts/start_host_ai_services.sh
cd demo/ui && python3 interactive_demo.py --use-real-data
```

## Service Dependencies

### Startup Order Requirements
```yaml
startup_sequence:
  1. Infrastructure Layer:
     - Terraform deployment (docker containers)
     - Docker network creation
     - Volume initialization
     
  2. Database Layer:
     - PostgreSQL with pgvector extension
     - MongoDB Atlas Local with vector search
     - Redis for caching
     - ScyllaDB 3-node cluster
     
  3. Database Initialization:
     - Alembic schema migrations
     - MongoDB vector indexes
     - ScyllaDB keyspace setup
     - Data seeding (optional)
     
  4. Host Services (if GPU available):
     - BGE embedding server (8008)
     - Qwen generation server (8009) 
     - Llama server (8004) - optional
     
  5. Python AI Services:
     - AI Gateway (8000)
     - Embedding Service (8005)
     - Generation Service (8006)
     - Search Service (8001)
     
  6. Go Microservices:
     - Auth/RBAC (8080)
     - Chat History (8002)
     - Audit Logging (8084)
     - Content Safety (8007)
     - Billing (8081)
     - Consent Management (8083)
     
  7. API Gateway (8090):
     - Entry point for all client requests
     - Proxies to all backend services
```

### Critical Dependencies
- **AI Gateway (8000)**: Requires Embedding (8005) + Generation (8006)
- **Search Service (8001)**: Requires MongoDB + Embedding (8005)
- **Chat History (8002)**: Requires ScyllaDB cluster (3 nodes)
- **Auth/RBAC (8080)**: Requires PostgreSQL
- **All Services**: Require Redis for session management

## Database Configuration

### Port Configuration Matrix
| Database | Production | Demo | Docker Container | Volume |
|----------|------------|------|------------------|--------|
| PostgreSQL | 5432 | 5433 | pgvector/pgvector:pg15 | postgres_data |
| MongoDB | 27017 | 27018 | mongodb/mongodb-atlas-local | mongo_data |
| Redis | 6379 | 6380 | redis:6-alpine | redis_data |
| ScyllaDB Node1 | 9042 | 9042/9045 | scylladb/scylla:latest | scylla_data1 |
| ScyllaDB Node2 | 9043 | 9043/9046 | scylladb/scylla:latest | scylla_data2 |
| ScyllaDB Node3 | 9044 | 9044/9047 | scylladb/scylla:latest | scylla_data3 |

### Database Initialization Commands
```bash
# PostgreSQL with pgvector extension
alembic upgrade head                    # Apply schema migrations
python init_database.py               # Test connections

# MongoDB vector search indexes
python ai_services/ingestion_pipeline/create_mongodb_vector_indexes.py

# ScyllaDB keyspace and tables
# Automatic via demo/scripts/init_scylladb.sh

# Redis configuration
# No setup required - auto-configured via connection string
```

### Database Schemas (PostgreSQL)
```sql
-- Five separate schemas for data isolation
CREATE SCHEMA IF NOT EXISTS chatbot_auth;        -- Authentication data
CREATE SCHEMA IF NOT EXISTS chatbot_compliance;  -- HIPAA audit logs
CREATE SCHEMA IF NOT EXISTS chatbot_app;         -- Application data
CREATE SCHEMA IF NOT EXISTS chatbot_memory;      -- Conversation context
CREATE SCHEMA IF NOT EXISTS chatbot_knowledge;   -- Healthcare knowledge base
```

## AI Service Dependencies

### GPU Requirements (Optional)
- **Apple Silicon**: Metal Performance Shaders (MPS) enabled
- **Linux/Windows**: CUDA-compatible GPU with 8GB+ VRAM
- **Memory**: 8GB+ system RAM recommended for full models
- **Fallback**: Mock services for CPU-only environments

### Model Dependencies (First Run Downloads)
```bash
# Embedding model (BGE-large-en-v1.5)
# Download size: ~1.5GB
# Cache location: ~/.cache/huggingface/hub/

# Generation model (Qwen2.5-7B)
# Download size: ~7GB  
# Cache location: ~/.cache/huggingface/hub/

# Docker volumes for model caching
sentence_transformers_cache     # BGE model cache
huggingface_cache              # General model cache
```

### AI Service Configuration
```yaml
# Production Configuration (GPU enabled)
ai_services:
  use_real_embeddings: true
  use_real_generation: true
  embedding_device: "auto"      # Detects MPS/CUDA/CPU
  generation_device: "auto"
  cache_embeddings: true
  
# Demo Configuration (Mock services)
ai_services:
  use_real_embeddings: false
  use_real_generation: false
  embedding_device: "cpu"
  generation_device: "cpu" 
  mock_responses: true
```

### Host Service Setup (GPU Acceleration)
```bash
# One-time setup for GPU services
./host_services/setup_generation.sh        # Download Qwen model
./host_services/setup_embedding.sh         # Download BGE model

# Start GPU-accelerated services
./demo/scripts/start_host_ai_services.sh
```

## Environment Management

### Environment Variable Categories

#### Database Connections
```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432          # 5433 for demo
POSTGRES_DB=chatbot_app     # demo_v1_chatbot_app for demo
POSTGRES_USER=chatbot_user  # demo_v1_user for demo
POSTGRES_PASSWORD=secure_password

# MongoDB
MONGO_HOST=localhost
MONGO_PORT=27017            # 27018 for demo
MONGO_USER=root
MONGO_PASSWORD=example      # demo_example_v1 for demo
MONGO_DB=chatbot_app        # demo_v1_chatbot_app for demo

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379             # 6380 for demo
REDIS_DB=0                  # 10 for demo

# ScyllaDB
SCYLLA_HOSTS=127.0.0.1:9042 # localhost:9045,localhost:9046,localhost:9047 for demo
SCYLLA_KEYSPACE=chatbot_ks  # demo_v1_chatbot_ks for demo
```

#### AI Service Configuration
```bash
# AI Service Enablement
USE_REAL_EMBEDDINGS=true
USE_REAL_GENERATION=true
EMBEDDING_SERVICE_URL=http://localhost:8005
GENERATION_SERVICE_URL=http://localhost:8006

# GPU Configuration
CUDA_VISIBLE_DEVICES=0      # Linux GPU selection
PYTORCH_MPS_ENABLED=1       # macOS Metal Performance Shaders
```

#### Feature Toggles
```bash
# Database Enablement
ENABLE_POSTGRESQL=true
ENABLE_MONGODB=true
ENABLE_ATLAS_SEARCH=auto

# HIPAA Compliance
HIPAA_AUDIT_LEVEL=strict
ENABLE_PHI_DETECTION=true
ENABLE_AUDIT_LOGGING=true

# Performance Settings
CACHE_TTL=3600
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30
```

### Environment Files
```bash
# Production environment
.env                        # Main configuration

# Demo environments  
demo/config/.env.demo_v1    # Demo-specific overrides
.env.local                  # Local development overrides
.env.test                   # Test environment settings
```

## Demo vs Production Infrastructure

### Demo Environment Characteristics
- **Purpose**: Local development and testing
- **Database Ports**: Custom (5433, 27018, 6380, 9045-9047)
- **Container Names**: `demo-v1-*` prefix for isolation
- **AI Services**: Optional GPU, mock mode fallback
- **Data**: Synthetic healthcare data (5 demo users)
- **Setup Commands**:
  ```bash
  ./demo/scripts/run_demo.sh --full-services
  ./demo/scripts/start_host_ai_services.sh
  ```

### Production Environment Characteristics  
- **Purpose**: Live healthcare platform
- **Database Ports**: Standard (5432, 27017, 6379, 9042)
- **Container Names**: `multidb-chatbot-*` prefix
- **AI Services**: Full GPU acceleration required
- **Data**: Real PHI data (HIPAA compliant)
- **Setup Commands**:
  ```bash
  make infrastructure
  make start
  make production-ready
  ```

### Key Differences Table
| Aspect | Demo | Production |
|--------|------|------------|
| **Database Ports** | 5433, 27018, 6380 | 5432, 27017, 6379 |
| **Container Prefix** | `demo-v1-*` | `multidb-chatbot-*` |
| **AI Models** | Optional (mock fallback) | Required (GPU) |
| **Data Volume** | 5 synthetic users | Real healthcare data |
| **HIPAA Level** | Simulation | Full compliance |
| **Infrastructure** | Docker Compose | Kubernetes + Terraform |
| **Startup Method** | Demo scripts | Make commands |

## Container Management

### Docker Infrastructure
```yaml
# Network Configuration
networks:
  multidb-chatbot-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

# Volume Management
volumes:
  postgres_data:        # PostgreSQL data persistence
  mongo_data:          # MongoDB data and indexes  
  mongo_config:        # MongoDB configuration
  mongo_mongot:        # MongoDB Atlas Search
  redis_data:          # Redis RDB snapshots
  scylla_data1:        # ScyllaDB node 1 data
  scylla_data2:        # ScyllaDB node 2 data  
  scylla_data3:        # ScyllaDB node 3 data
```

### Resource Allocation Requirements
```yaml
# Container resource limits
resource_requirements:
  postgres:
    memory: 1GB
    cpu: 0.5 cores
    storage: 5GB
    
  mongodb:
    memory: 2GB  
    cpu: 1 core
    storage: 10GB
    
  redis:
    memory: 512MB
    cpu: 0.25 cores
    storage: 1GB
    
  scylla_cluster:
    memory: 2.25GB (750MB x 3 nodes)
    cpu: 1 core (total)
    storage: 15GB (5GB x 3 nodes)
    
  total_requirements:
    memory: ~6GB
    cpu: ~3 cores
    storage: ~31GB
```

### Health Check Commands
```bash
# Database health checks
docker exec multidb-chatbot-postgres pg_isready -U chatbot_user
docker exec multidb-chatbot-mongodb mongosh --eval "db.runCommand('ping')" --quiet
docker exec multidb-chatbot-redis redis-cli ping
docker exec multidb-chatbot-scylla nodetool status

# Service health checks via API
curl http://localhost:8000/health        # AI Gateway
curl http://localhost:8001/health        # Search Service  
curl http://localhost:8005/health        # Embedding Service
curl http://localhost:8006/health        # Generation Service
curl http://localhost:8090/health        # API Gateway (entry point)
```

## Service Discovery and Dependencies

### Critical Service Dependencies
```mermaid
graph TD
    Client[👤 Client Request] --> Gateway[🌐 API Gateway :8090]
    
    Gateway --> Auth[🔐 Auth/RBAC :8080]
    Gateway --> AI[🤖 AI Gateway :8000]
    Gateway --> Chat[💬 Chat History :8002]
    Gateway --> Audit[📋 Audit Logging :8084]
    
    Auth --> PG[(🐘 PostgreSQL)]
    AI --> Search[🔍 Search Service :8001]
    AI --> Embed[🧠 Embedding :8005]
    AI --> Gen[📝 Generation :8006]
    Chat --> Scylla[(⚡ ScyllaDB)]
    Audit --> PG
    
    Search --> Mongo[(🍃 MongoDB)]
    Search --> Redis[(🗄️ Redis)]
    Embed --> BGE[🎯 BGE Host :8008]
    Gen --> Qwen[🧠 Qwen Host :8007]
```

### Startup Validation Sequence
```bash
# 1. Infrastructure validation
make validate               # Check prerequisites
terraform plan             # Verify infrastructure plan

# 2. Database readiness
make database-health        # Verify all databases connected
make schema-check           # Verify migrations applied

# 3. Service health verification  
make health                 # Check all service endpoints
make connectivity-test      # Verify inter-service communication

# 4. End-to-end validation
make test-quick             # Quick smoke tests
make test-integration       # Cross-service functionality
```

## Troubleshooting

### Common Infrastructure Issues

#### Port Conflicts
```bash
# Check what's using a port
lsof -i :8000
lsof -i :5432

# Kill processes on specific ports
lsof -ti:8000 | xargs kill -9
lsof -ti:5432 | xargs kill -9

# Reset all demo services
./demo/scripts/stop_all_demo_services.sh
```

#### Database Connection Issues
```bash
# PostgreSQL connection test
PGPASSWORD=password psql -h localhost -p 5432 -U chatbot_user -d chatbot_app -c "SELECT 1;"

# MongoDB connection test
mongosh "mongodb://root:password@localhost:27017/chatbot_app?authSource=admin"

# Redis connection test
redis-cli -h localhost -p 6379 ping

# ScyllaDB connection test
docker exec multidb-chatbot-scylla cqlsh -e "DESCRIBE KEYSPACES;"
```

#### Service Discovery Issues
```bash
# Check Docker network
docker network inspect multidb-chatbot-network

# Verify service endpoints
make health-check           # All services
make database-check         # Database connectivity
make ai-service-check       # AI service availability
```

#### AI Service Issues
```bash
# Check GPU availability
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Verify model downloads
ls -la ~/.cache/huggingface/hub/
du -sh ~/.cache/huggingface/hub/

# Test AI service endpoints (6 Python AI services)
curl http://localhost:8000/health        # AI Gateway (orchestrator)
curl http://localhost:8005/health        # Embedding service
curl http://localhost:8006/health        # Generation service

# Test GPU host services (2 services)
curl http://localhost:8008/health        # BGE host
curl http://localhost:8009/health        # Qwen host
curl http://localhost:8004/health        # Llama server (optional)
```

### Reset Procedures

#### Complete Infrastructure Reset
```bash
# Stop all services
make stop
./demo/scripts/stop_all_demo_services.sh

# Remove all containers and volumes
make clean
docker-compose down -v
docker system prune -a

# Restart from scratch
make setup
make infrastructure
make start
```

#### Selective Reset
```bash
# Reset databases only (preserve services)
make db-reset

# Reset AI models only
rm -rf ~/.cache/huggingface/hub/
./host_services/setup_generation.sh

# Reset demo environment only
cd demo && docker-compose -f config/docker-compose.demo-full.yml down -v
```

### Environment Debugging

#### Configuration Validation
```bash
# Check environment variable loading
make config-check           # Validate all config files
make env-debug             # Debug environment variables

# Verify service configuration
make service-config-check   # Check service-specific configs
make database-config-check  # Verify database connection strings
```

#### Log Analysis
```bash
# View all service logs
make logs                   # Combined logs from all services

# Individual service logs
docker-compose logs postgres
docker-compose logs mongodb
tail -f /tmp/demo_ai_logs/embedding.log
tail -f /tmp/demo_service_logs/api_gateway.log

# Error pattern search
make logs | grep -i "error\|failed\|exception"
```

## Performance Considerations

### Local Development Performance Tuning
```yaml
# Docker resource allocation (Docker Desktop)
memory: 8GB                 # Increase if available
cpu: 4 cores               # Use available cores
disk_image_size: 64GB      # Ensure adequate space

# Database performance settings
postgres:
  shared_buffers: 256MB
  effective_cache_size: 1GB
  
mongodb:
  cache_size_gb: 1
  
scylla:
  memory_per_node: 750MB
```

### Service Performance Monitoring
```bash
# Resource usage monitoring
docker stats                # Container resource usage
make performance-check      # Service performance validation
make benchmark-quick        # Quick performance test
```

This infrastructure guide fills the major gaps in operations documentation, providing complete local development setup instructions that were missing from the production-focused deployment guides.