# MultiDB Therapeutic AI Chatbot - Demo System

## Overview

This demo system provides a comprehensive, guided exploration of the therapeutic AI chatbot designed for senior living facilities and healthcare organizations. Experience authentic user flows, real AI responses, and complete system capabilities through an interactive demo that showcases the full three-tier architecture via API Gateway (port 8090).

## 🚀 Quick Start

### Option 1: Database Demo (Quick Start)
```bash
# From project root - start demo databases and seed data
./demo/scripts/run_demo.sh --databases-only

# Run interactive demo with simulated responses (database connections only)
cd demo/ui && python3 interactive_demo.py --use-real-data
```

### Option 2: Full Service Stack with AI (Recommended for Full Demo)
```bash
# Complete architecture (databases + host services + microservices + API Gateway)
./demo/scripts/run_demo.sh --full-services

# OR start services separately for more control:
# 1. Start databases only
./demo/scripts/run_demo.sh --databases-only

# 2. Start host services (GPU-accelerated AI)
./demo/scripts/start_host_ai_services.sh

# 3. Start all microservices and API Gateway
./demo/scripts/start_local_services.sh

# 4. Run interactive demo with full API integration
cd demo/ui && python3 interactive_demo.py --use-real-data
```

### Option 3: Simulation Mode (No Setup)
```bash
# Simple demo with simulated responses
cd demo/ui && python3 interactive_demo.py
```

### Option 4: Persistent Data Mode (Fast Restart)
**⚡ Use this when you want to preserve existing demo data and avoid re-seeding:**

```bash
# 1. Start databases only (preserves existing data in volumes)
cd demo



# 2. Start AI services + main API (now includes chat functionality)
cd ..
./demo/scripts/start_host_ai_services.sh

# 3. Run demo with existing persistent data
cd demo/ui && python3 interactive_demo.py --use-real-data
```

**Benefits**: 
- ✅ Preserves conversation history and user data
- ✅ Faster startup (no re-seeding)
- ✅ Avoids ScyllaDB cluster synchronization issues
- ✅ Chat functionality works with AI services

**🗑️ Reset Data**: To start fresh, remove volumes:
```bash
cd demo && docker-compose -f config/docker-compose.demo-full.yml down -v
```

## 📁 Directory Structure

```
demo/
├── README.md                     # This comprehensive guide
├── config/                      # Demo configuration files
│   ├── .env.demo_v1             # Demo environment variables
│   ├── docker-compose.demo.yml  # Database-only demo
│   └── docker-compose.demo-full.yml # Complete service stack
├── scripts/                     # Demo automation scripts
│   ├── run_demo.sh              # Main demo launcher (databases + services)
│   ├── init_scylladb.sh         # ScyllaDB keyspace/table initialization
│   ├── seed_demo_data.py        # Demo data creation and seeding
│   ├── start_host_ai_services.sh # Host AI services (GPU-accelerated)
│   ├── start_local_services.sh  # All services + API Gateway
│   ├── stop_all_demo_services.sh # Stop all services
│   ├── test_demo_real_mode.py   # API Gateway connectivity testing
│   └── test_full_ai_pipeline.py # End-to-end AI pipeline testing
└── ui/                         # Demo user interfaces
    └── interactive_demo.py      # Main interactive demo (API Gateway mode)
```

## 🏗️ Service Architecture

### Database-Only Demo (Default)
- **PostgreSQL**: `localhost:5433` - User data, app schemas, compliance
- **MongoDB**: `localhost:27018` - Knowledge base, document storage  
- **Redis**: `localhost:6380` - Caching, session management
- **ScyllaDB**: `localhost:9045` - Conversation history, analytics
- **Auto-initialized**: Keyspace `demo_v1_chatbot_ks` and required tables created automatically

### Full Service Stack Demo (Three-Tier Architecture)

**Host Services (GPU-Accelerated):**
- **Embedding Service**: `localhost:8005` - BGE-Large 1024d embeddings with MPS/Metal acceleration
- **Generation Service**: `localhost:8006` - Qwen2.5 therapeutic AI with llama.cpp backend

**AI Services Layer (Python FastAPI):**
- **AI/ML Services**: `localhost:8000` - AI model orchestration, ingestion, seeding services
  - Vector similarity search (MongoDB aggregation)
  - Hybrid keyword + vector search
  - Cross-encoder re-ranking for therapeutic relevance
  - Intelligent data routing with query analysis

**Go Microservices (Behind API Gateway):**
- **Search Service**: `localhost:8001` - RAG pipeline and knowledge retrieval
- **Chat History Service**: `localhost:8002` - Conversation storage via ScyllaDB
- **Auth & RBAC**: `localhost:8081` - Authentication, authorization (internal)
- **Consent Management**: `localhost:8083` - HIPAA consent workflows (internal)
- **Audit Logging**: `localhost:8084` - HIPAA compliance audit trails (internal)

**API Gateway (Single Entry Point):**
- **API Gateway**: `localhost:8090` - Routes all `/api/v1/*` requests to appropriate services
  - `/api/v1/embedding/*` → Host Services (port 8005)
  - `/api/v1/generation/*` → Host Services (port 8006) 
  - `/api/v1/chat/*` → AI Services (port 8000) via Chat History Service (port 8002)
  - `/api/v1/search/*` → Search Service (port 8001)
  - `/api/v1/auth/*` → Auth Service (port 8081) 
  - `/api/v1/audit/*` → Audit Service (port 8084)
  - Single point of access for all demo interactions

## 👥 Demo User Personas & Credentials

**IMPORTANT**: The demo now requires real authentication. Use these credentials to log in during the demo:

### 🔐 Demo User Credentials

| User Type | Email | Password |
|-----------|--------|----------|
| **Senior Resident** | `sarah.martinez.demo@example.com` | `demo_password_resident_sarah` |
| **Family Member** | `jennifer.martinez.demo@example.com` | `demo_password_family_jennifer` |
| **Care Staff** | `maria.rodriguez.demo@example.com` | `demo_password_staff_maria` |
| **Care Manager** | `james.chen.demo@example.com` | `demo_password_manager_james` |
| **Administrator** | `linda.thompson.demo@example.com` | `demo_password_admin_linda` |

### Sarah Martinez (Senior Resident)
- **Age**: 78, Independent Living
- **Background**: Recent widow, mild anxiety, managing diabetes
- **Journey**: Onboarding → Trust Building → Crisis Navigation → Wellness Achievement
- **90-Day Progress**: UCLA-3 loneliness score improved from 8.1 to 5.4
- **Login**: sarah.martinez.demo@example.com / demo_password_resident_sarah

### Jennifer Martinez (Family Member)
- **Role**: Sarah's daughter, lives 2 hours away
- **Concerns**: Mother's emotional wellbeing, medication adherence, social isolation
- **Experience**: Portal access, weekly summaries, emergency notifications
- **Login**: jennifer.martinez.demo@example.com / demo_password_family_jennifer

### Maria Rodriguez, RN (Care Staff)
- **Role**: Day shift nurse, 25 residents on caseload
- **Responsibilities**: Real-time monitoring, crisis response, family communication
- **Benefits**: Early intervention alerts, documentation efficiency
- **Login**: maria.rodriguez.demo@example.com / demo_password_staff_maria

### Dr. James Chen (Care Manager)
- **Role**: Health plan case manager, 150-member caseload
- **Focus**: Population health, loneliness intervention, utilization management
- **Outcomes**: 78% intervention success rate, measurable health improvements
- **Login**: james.chen.demo@example.com / demo_password_manager_james

### Linda Thompson (Administrator)
- **Role**: Facility Director, organizational oversight
- **Metrics**: 245 residents, 87% adoption rate, 100% HIPAA compliance
- **Benefits**: Staff efficiency, family satisfaction, quality outcomes
- **Login**: linda.thompson.demo@example.com / demo_password_admin_linda

## 📊 Demo Data Generated

### PostgreSQL (demo_v1_chatbot_app)
- **5 Users** with complete profiles and personas
- **1 Resident** with medical conditions, care plan, family relationships
- **1 Family Member** with portal access and communication preferences  
- **1 Care Staff** with certifications and assigned residents
- **90 Days** of conversation history with emotional progression
- **270+ Wellness Metrics** showing improvement trends
- **1,800+ Audit Logs** for HIPAA compliance demonstration
- **25 Consent Records** covering all privacy categories

### MongoDB (demo_v1_chatbot_app)
- **10 Healthcare Knowledge Documents** covering common senior topics
- **3 Therapeutic Conversation Examples** with emotional impact data
- **Vector Search Indexes** for semantic retrieval

### Redis (demo_v1 keys)
- **Session Data** for active user sessions
- **System Health Cache** with current status
- **Staff Alerts** for current shift notifications
- **Wellness Trends** for quick dashboard access

### ScyllaDB (demo_v1_chatbot_ks)
- **30 Days Conversation History** with timestamps and emotional data
- **Wellness Analytics** time-series data for trend analysis

## 🎯 Demo Features

### 🔐 User Authentication & Role Selection
- Experience login flows for different user types
- Role-based permissions and access controls
- HIPAA compliance verification

### 👥 User Personas & Story Scenarios
- Meet realistic user personas with detailed backgrounds
- Understand user needs, challenges, and goals
- Explore care contexts and medical histories

### 💬 Live Conversation Simulation
- Interactive AI conversations tailored to user role
- Emotional analysis with sentiment and arousal detection
- Crisis detection and response simulation
- Real-time response adaptation and personalization

### 📊 Dashboard & Analytics Views
- Role-specific dashboards and metrics
- Real-time performance monitoring
- Quality assurance and compliance reporting

### 🆘 Crisis Management Demonstration
- Multi-level crisis detection scenarios
- Emergency response protocols
- Human escalation workflows
- Safety documentation and audit trails

### ⚙️ Administrative Features
- User management and onboarding
- Privacy and consent controls
- HIPAA compliance monitoring

### 🔗 Integration & API Demonstrations
- Healthcare system connectivity
- API endpoint examples
- Data flow illustrations

### 📱 Mobile & Accessibility Features
- Senior-friendly mobile interface
- WCAG 2.1 AA compliance demonstration
- Voice control and assistive technology support

### 🏥 HIPAA Compliance Overview
- Administrative, physical, and technical safeguards
- Audit logging and privacy controls
- Data retention and access management

### 📈 Quality Metrics & Reporting
- Evidence-based outcome measurement
- Performance indicators and benchmarks
- Clinical effectiveness tracking

### 🎯 Full End-to-End User Journey
- Complete resident experience from onboarding to outcomes
- 90-day care journey with measurable improvements
- Family and care team coordination

## 🔄 Demo Modes

### Simulation Mode (Default)
- **UI**: Full interactive experience with realistic mock responses
- **Data**: No database dependencies required
- **Performance**: Instant responses, perfect for presentations
- **Setup**: Zero configuration required

### Real Database Mode
- **UI**: Interactive experience with live database queries
- **Data**: Connects to isolated demo databases (demo_v1 prefix)
- **Performance**: Real database latency, authentic experience
- **Setup**: Requires demo database containers

### Real API Mode (Full Stack) - **ENHANCED & RECOMMENDED**
- **UI**: Interactive experience with live API calls through API Gateway
- **Data**: Complete three-tier service stack with real AI responses
- **Performance**: Complete end-to-end system behavior via port 8090
- **Setup**: Requires host services + AI services + Go microservices + API Gateway
- **Entry Point**: All demo interactions route through `localhost:8090/api/v1/*`
- **Features**: 
  - Real BGE embeddings with GPU acceleration
  - Live Qwen2.5 AI generation responses
  - Authentic database operations across all 4 databases
  - HIPAA-compliant audit logging
  - Production-like service architecture
  - **Enhanced**: Improved service routing and error handling
  - **Enhanced**: Better API Gateway integration with real services
  - **Enhanced**: Optimized authentication flow for demo users

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.8+
- Docker and Docker Compose
- Terminal with color support
- 2GB available RAM for full stack

### Manual Database Setup

1. **Start Demo Databases**
```bash
cd demo
docker-compose -f config/docker-compose.demo.yml up -d
```

2. **Verify Database Health**
```bash
# Check PostgreSQL
docker exec demo-v1-postgres pg_isready -U demo_v1_user

# Check MongoDB  
docker exec demo-v1-mongodb mongosh --eval "db.runCommand('ping').ok" --quiet

# Check Redis
docker exec demo-v1-redis redis-cli ping

# Check ScyllaDB
docker exec demo-v1-scylla-node1 nodetool status
```

3. **Seed Demo Data**
```bash
cd scripts && python3 seed_demo_data.py
```

### API Gateway Testing
Once the full service stack is running, test the API Gateway endpoints:

```bash
# Test API Gateway health
curl http://localhost:8090/health

# Test service routing through API Gateway
curl http://localhost:8090/api/v1/search/health
curl http://localhost:8090/api/v1/embedding/health  
curl http://localhost:8090/api/v1/generation/health

# Test chat endpoint (requires authentication)
curl -X POST http://localhost:8090/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "enable_rag": true}'
```

## 📈 Performance Expectations

### Database Response Times (Real Mode)
- **PostgreSQL Queries**: <50ms for user/conversation data
- **MongoDB Searches**: <100ms for knowledge base queries
- **Redis Cache**: <5ms for session and metrics
- **ScyllaDB Analytics**: <200ms for time-series queries

### Demo Session Metrics
- **Full Setup Time**: 5-8 minutes (including database startup)
- **Data Seeding**: 2-3 minutes for complete dataset
- **Demo Session**: 15-60 minutes depending on exploration depth
- **Memory Usage**: ~500MB total for all demo databases

## 🛠️ Comprehensive Troubleshooting Guide

### Critical Setup Issues (Start Here)

#### 1. Environment Configuration Problems
**Issue**: Services connect to production databases instead of demo databases
**Symptoms**: 
- Tests failing with wrong database ports
- Services not finding demo data
- MongoDB authentication errors

**Solution**:
```bash
# STEP 1: Always load demo environment BEFORE starting services
export $(cat demo/config/.env.demo_v1 | grep -v '^#' | xargs)

# STEP 2: Verify environment variables are loaded
env | grep -E "(DEMO_MODE|ENVIRONMENT|POSTGRES_PORT|REDIS_PORT|MONGO_PASSWORD)"
# Should show: DEMO_MODE=1, ENVIRONMENT=demo_v1, POSTGRES_PORT=5433, etc.

# STEP 3: Start services with demo environment loaded
PYTHONPATH=/path/to/project uvicorn ai_services.main:app --host 0.0.0.0 --port 8000
```

#### 2. Wrong Database Instance Connection
**Issue**: Services connecting to production databases (ports 5432, 6379, 27017) instead of demo databases
**Symptoms**:
- "Connection refused" errors
- Wrong database schema or missing demo data
- Authentication failures

**Critical Fix**:
```bash
# Check which containers are running
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "(demo-v1|multidb-chatbot)"

# You should see DEMO containers:
# demo-v1-postgres     0.0.0.0:5433->5432/tcp
# demo-v1-mongodb      0.0.0.0:27018->27017/tcp  
# demo-v1-redis        0.0.0.0:6380->6379/tcp

# Start missing demo containers
docker-compose -f demo/config/docker-compose.demo-full.yml up -d postgres-demo redis-demo

# Verify demo database connectivity
python -c "
import asyncpg, asyncio
async def test():
    conn = await asyncpg.connect('postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app')
    print('✅ Demo PostgreSQL connected')
    await conn.close()
asyncio.run(test())
"
```

#### 3. MongoDB Authentication and DirectConnection Issues
**Issue**: MongoDB connection failures with authentication errors
**Symptoms**: 
- "Authentication failed" errors
- Wrong password being used
- Connection timeouts in hybrid setup

**Critical Fixes**:
```bash
# Verify MongoDB demo container is running
docker exec demo-v1-mongodb mongosh --eval "db.runCommand('ping').ok" --quiet

# Test correct authentication
mongosh "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true"

# Check if directConnection=true is in connection string
python -c "
from data_layer.config import database_config
print(f'MongoDB URI: {database_config.mongo.build_uri()}')
# Should show: directConnection=true and password=demo_example_v1
"
```

#### 4. llama.cpp Generation Service Setup
**Issue**: Generation service degraded - missing llama.cpp backend
**Symptoms**: Generation service returns fallback responses instead of AI responses

**Setup Steps**:
```bash
# Install llama.cpp if not available
brew install llama.cpp

# Download Qwen model (one-time setup)
mkdir -p ~/models
curl -L -o ~/models/Qwen2-1.5B-Instruct-Q4_K_M.gguf \
  "https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF/resolve/main/qwen2-1_5b-instruct-q4_k_m.gguf"

# Start llama server (required for generation service)
llama-server \
  -m ~/models/Qwen2-1.5B-Instruct-Q4_K_M.gguf \
  -c 8192 \
  -ngl 999 \
  -t 8 \
  --port 8004 \
  --host 0.0.0.0 \
  --chat-template qwen &

# Test generation service
curl -X POST http://localhost:8006/generate/response \
  -H "Content-Type: application/json" \
  -d '{"message": "I feel anxious", "user_id": "demo_user"}'
```

### Database-Specific Issues

#### PostgreSQL Demo Issues
**Problem**: Demo PostgreSQL missing required schema or user tables
```bash
# Check demo PostgreSQL schema
docker exec demo-v1-postgres psql -U demo_v1_user -d demo_v1_chatbot_app -c "\dt"

# Create missing users table if needed
docker exec demo-v1-postgres psql -U demo_v1_user -d demo_v1_chatbot_app -c "
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"

# Create demo admin user
docker exec demo-v1-postgres psql -U demo_v1_user -d demo_v1_chatbot_app -c "
INSERT INTO users (email, password_hash, role, is_active) 
VALUES ('linda.thompson.demo@example.com', 'demo_password_hash', 'admin', true)
ON CONFLICT (email) DO NOTHING;"
```

#### MongoDB Demo Issues
**Problem**: Authentication failures, wrong password, missing collections
```bash
# Test MongoDB connection with correct credentials
mongosh "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true"

# Check if therapeutic knowledge exists
mongosh "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true" --eval "
db.demo_v1_knowledge_base.countDocuments();
db.demo_v1_therapeutic_knowledge.countDocuments();
"

# If collections are empty, seed therapeutic knowledge
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def seed_knowledge():
    client = AsyncIOMotorClient('mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true')
    db = client.demo_v1_chatbot_app
    
    # Insert sample therapeutic knowledge
    await db.demo_v1_knowledge_base.insert_many([
        {'title': 'Anxiety Support', 'content': 'Therapeutic techniques for managing anxiety in elderly care...'},
        {'title': 'Loneliness Management', 'content': 'Evidence-based interventions for social isolation...'}
    ])
    print('✅ Therapeutic knowledge seeded')
    client.close()

asyncio.run(seed_knowledge())
"
```

#### Redis Demo Issues
**Problem**: Redis connection to wrong port or missing demo Redis instance
```bash
# Check Redis demo connectivity
docker exec demo-v1-redis redis-cli ping

# Test connection from application
python -c "
import redis
r = redis.Redis(host='localhost', port=6380, db=10)
print(f'✅ Redis demo connected: {r.ping()}')
"

# Start demo Redis if missing
docker-compose -f demo/config/docker-compose.demo-full.yml up -d redis-demo
```

#### ScyllaDB Demo Issues  
**Problem**: ScyllaDB cluster connectivity or timing issues
```bash
# Check ScyllaDB cluster status
docker exec demo-v1-scylla-node1 nodetool status

# Start ScyllaDB cluster sequentially (timing important)
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node1
sleep 30  # Wait for node1 to be healthy
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node2
sleep 30  # Wait for node2 to be healthy  
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node3

# Test ScyllaDB connectivity
python -c "
from cassandra.cluster import Cluster
cluster = Cluster(['127.0.0.1'], port=9045)
session = cluster.connect()
print('✅ ScyllaDB demo connected')
cluster.shutdown()
"
```

### Service Configuration Issues

#### Admin Authentication Errors
**Problem**: Admin endpoints return 403/500 errors due to User model issues
**Fix Applied**:
```bash
# The User model constructor was fixed in: ai_services/shared/dependencies/dependencies.py
# Changed from: User(id=...) 
# To: User(user_id=..., email=..., full_name=..., is_active=True)

# Test admin endpoint
curl -H "Authorization: Bearer demo-token" http://localhost:8000/admin/seed-status
```

#### Import Path Migration Issues
**Problem**: Tests failing with "ModuleNotFoundError: No module named 'app'"
**Fix Applied**:
```bash
# Updated import paths in test files:
# From: from app.utils.document_processor import EnhancedDocumentProcessor
# To: from ai_services.ingestion_pipeline.document_processor import EnhancedDocumentProcessor

# Search for remaining app imports
rg "from app\." tests/ --type py
```

#### Service Port Configuration Issues
**Problem**: Tests connecting to wrong service ports
**Fix Applied**:
```bash
# Updated test configuration in tests/integration/test_full_user_paths.py:
# EMBEDDING_SERVICE_URL = "http://localhost:8005"  # Was 8001
# GENERATION_SERVICE_URL = "http://localhost:8006"  # Was 8003
# MONGO_URI = "mongodb://root:demo_example_v1@localhost:27018/..."  # Updated password
```

### Database Connection Issues

#### PostgreSQL Demo Issues
**Problem**: Demo PostgreSQL missing required schema or user tables
```bash
# Check demo PostgreSQL schema
docker exec demo-v1-postgres psql -U demo_v1_user -d demo_v1_chatbot_app -c "\dt"

# Create missing users table if needed
docker exec demo-v1-postgres psql -U demo_v1_user -d demo_v1_chatbot_app -c "
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"

# Create demo admin user
docker exec demo-v1-postgres psql -U demo_v1_user -d demo_v1_chatbot_app -c "
INSERT INTO users (email, password_hash, role, is_active) 
VALUES ('linda.thompson.demo@example.com', 'demo_password_hash', 'admin', true)
ON CONFLICT (email) DO NOTHING;"
```

#### MongoDB Demo Issues
**Problem**: Authentication failures, wrong password, missing collections
```bash
# Test MongoDB connection with correct credentials
mongosh "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true"

# Check if therapeutic knowledge exists
mongosh "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true" --eval "
db.demo_v1_knowledge_base.countDocuments();
db.demo_v1_therapeutic_knowledge.countDocuments();
"

# If collections are empty, seed therapeutic knowledge
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def seed_knowledge():
    client = AsyncIOMotorClient('mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true')
    db = client.demo_v1_chatbot_app
    
    # Insert sample therapeutic knowledge
    await db.demo_v1_knowledge_base.insert_many([
        {'title': 'Anxiety Support', 'content': 'Therapeutic techniques for managing anxiety in elderly care...'},
        {'title': 'Loneliness Management', 'content': 'Evidence-based interventions for social isolation...'}
    ])
    print('✅ Therapeutic knowledge seeded')
    client.close()

asyncio.run(seed_knowledge())
"
```

#### Redis Demo Issues
**Problem**: Redis connection to wrong port or missing demo Redis instance
```bash
# Check Redis demo connectivity
docker exec demo-v1-redis redis-cli ping

# Test connection from application
python -c "
import redis
r = redis.Redis(host='localhost', port=6380, db=10)
print(f'✅ Redis demo connected: {r.ping()}')
"

# Start demo Redis if missing
docker-compose -f demo/config/docker-compose.demo-full.yml up -d redis-demo
```

#### ScyllaDB Demo Issues  
**Problem**: ScyllaDB cluster connectivity or timing issues
```bash
# Check ScyllaDB cluster status
docker exec demo-v1-scylla-node1 nodetool status

# Start ScyllaDB cluster sequentially (timing important)
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node1
sleep 30  # Wait for node1 to be healthy
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node2
sleep 30  # Wait for node2 to be healthy  
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node3

# Test ScyllaDB connectivity
python -c "
from cassandra.cluster import Cluster
cluster = Cluster(['127.0.0.1'], port=9045)
session = cluster.connect()
print('✅ ScyllaDB demo connected')
cluster.shutdown()
"
```

### Demo User and Authentication Issues

#### Missing Demo Users
**Problem**: Admin endpoints fail due to missing user accounts in demo database
**Solution**:
```bash
# Create all required demo users in PostgreSQL
export $(cat demo/config/.env.demo_v1 | grep -v '^#' | xargs)
python -c "
import asyncio, asyncpg

async def create_demo_users():
    conn = await asyncpg.connect('postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app')
    
    # Create users table with proper schema
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert demo users from README personas
    demo_users = [
        ('linda.thompson.demo@example.com', 'demo_password_admin_linda', 'admin'),
        ('sarah.martinez.demo@example.com', 'demo_password_resident_sarah', 'resident'),
        ('jennifer.martinez.demo@example.com', 'demo_password_family_jennifer', 'family_member'),
        ('maria.rodriguez.demo@example.com', 'demo_password_staff_maria', 'care_staff'),
        ('james.chen.demo@example.com', 'demo_password_manager_james', 'health_provider')
    ]
    
    for email, password, role in demo_users:
        try:
            await conn.execute(
                'INSERT INTO users (email, password_hash, role, is_active) VALUES (\$1, \$2, \$3, \$4)',
                email, password, role, True
            )
            print(f'✅ Created demo user: {email} ({role})')
        except Exception as e:
            if 'duplicate key' in str(e):
                print(f'✅ Demo user exists: {email}')
            else:
                print(f'❌ Error: {e}')
    
    await conn.close()

asyncio.run(create_demo_users())
"
```

#### Authentication Token Issues
**Problem**: Admin endpoints require Bearer tokens but mock authentication fails
**Current Status**: Admin endpoints use mock authentication for demo purposes
```bash
# Test admin endpoints (should work with any Bearer token in demo)
curl -H "Authorization: Bearer demo-token" http://localhost:8000/admin/seed-status

# If getting 500 errors, check User model constructor in logs:
# Common issue: User() constructor parameters don't match model definition
```

### Service Startup and Dependency Issues

#### Wrong Service Startup Order
**Problem**: Services fail because dependencies aren't ready
**Critical Startup Sequence**:
```bash
# STEP 1: Load demo environment (CRITICAL - do this first)
export $(cat demo/config/.env.demo_v1 | grep -v '^#' | xargs)

# STEP 2: Start demo databases
docker-compose -f demo/config/docker-compose.demo-full.yml up -d postgres-demo redis-demo mongodb-demo

# STEP 3: Wait for databases to be ready
sleep 10

# STEP 4: Start llama.cpp server (required for generation)
~/models/start_qwen.sh &  # Or manual llama-server command

# STEP 5: Start AI services with demo environment
PYTHONPATH=/Users/asqmac/git-repos/Lilo_EmotionalAI_Backend uvicorn ai_services.main:app --host 0.0.0.0 --port 8000 &

# STEP 6: Start host services (embedding/generation)
PYTHONPATH=/Users/asqmac/git-repos/Lilo_EmotionalAI_Backend python host_services/embed_server.py &
GENERATION_SERVICE_PORT=8006 PYTHONPATH=/Users/asqmac/git-repos/Lilo_EmotionalAI_Backend python host_services/generation_server.py &

# STEP 7: Verify all services healthy
curl http://localhost:8000/health/detailed
```

#### Mixed Production/Demo Container Issues
**Problem**: Both production and demo containers running simultaneously
```bash
# Check for container conflicts
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "(demo-v1|multidb-chatbot)"

# Clean approach: stop production containers during demo
docker stop multidb-chatbot-postgres multidb-chatbot-mongodb multidb-chatbot-redis
docker-compose -f demo/config/docker-compose.demo-full.yml up -d
```

### Integration Test Issues

#### Test Configuration Mismatches
**Problem**: Tests connect to wrong service ports or use old import paths
**Fix Applied**:
```bash
# Updated test configuration in tests/integration/test_full_user_paths.py:
# OLD: EMBEDDING_SERVICE_URL = "http://localhost:8001"
# NEW: EMBEDDING_SERVICE_URL = "http://localhost:8005"
# OLD: GENERATION_SERVICE_URL = "http://localhost:8003"  
# NEW: GENERATION_SERVICE_URL = "http://localhost:8006"
# OLD: MONGO_URI = "mongodb://root:example@localhost:27017/..."
# NEW: MONGO_URI = "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true"

# Updated import paths:
# OLD: from app.utils.document_processor import EnhancedDocumentProcessor
# NEW: from ai_services.ingestion_pipeline.document_processor import EnhancedDocumentProcessor
```

### Environment Configuration Validation

#### Step-by-Step Environment Setup Verification
```bash
# 1. Verify demo environment file exists
test -f demo/config/.env.demo_v1 && echo "✅ Demo config found" || echo "❌ Missing demo/config/.env.demo_v1"

# 2. Load and verify demo environment variables
export $(cat demo/config/.env.demo_v1 | grep -v '^#' | xargs)

# 3. Critical environment validation
python -c "
import os
required_vars = {
    'DEMO_MODE': '1',
    'ENVIRONMENT': 'demo_v1', 
    'POSTGRES_PORT': '5433',
    'MONGO_PASSWORD': 'demo_example_v1',
    'REDIS_PORT': '6380',
    'MONGO_PORT': '27018'
}

print('Environment Validation:')
all_good = True
for var, expected in required_vars.items():
    actual = os.getenv(var, 'NOT_SET')
    status = '✅' if actual == expected else '❌'
    print(f'{status} {var}: {actual} (expected: {expected})')
    if actual != expected:
        all_good = False

print(f'\nOverall Status: {\"✅ Environment Ready\" if all_good else \"❌ Environment Issues Found\"}')
"

# 4. Database connection string validation
python -c "
import os
from data_layer.config import database_config

print('Database Connection Validation:')
print(f'PostgreSQL URI: {database_config.postgres.build_database_url()}')
print(f'MongoDB URI: {database_config.mongo.build_uri()}')
print(f'Redis URI: redis://localhost:{os.getenv(\"REDIS_PORT\", \"6380\")}/{os.getenv(\"REDIS_DB\", \"10\")}')

# Verify directConnection=true in MongoDB URI
mongo_uri = database_config.mongo.build_uri()
if 'directConnection=true' in mongo_uri:
    print('✅ MongoDB directConnection configured')
else:
    print('❌ MongoDB missing directConnection=true')
"
```

### Complete Demo Validation Checklist

#### Pre-Demo Validation
```bash
# 1. Environment check
env | grep -E "(DEMO_MODE|ENVIRONMENT)" | grep -q "demo_v1" && echo "✅ Demo environment loaded" || echo "❌ Load demo environment first"

# 2. Database connectivity check  
python -c "
import asyncio, asyncpg, redis
from motor.motor_asyncio import AsyncIOMotorClient

async def check_all():
    # PostgreSQL
    try:
        conn = await asyncpg.connect('postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app')
        await conn.close()
        print('✅ PostgreSQL demo: Connected')
    except: print('❌ PostgreSQL demo: Failed')
    
    # MongoDB  
    try:
        client = AsyncIOMotorClient('mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true')
        await client.admin.command('ping')
        client.close()
        print('✅ MongoDB demo: Connected')
    except: print('❌ MongoDB demo: Failed')
    
    # Redis
    try:
        r = redis.Redis(host='localhost', port=6380, db=10)
        r.ping()
        print('✅ Redis demo: Connected')
    except: print('❌ Redis demo: Failed')

asyncio.run(check_all())
"

# 3. Service health check
curl -s http://localhost:8000/health | jq .status
curl -s http://localhost:8005/health | jq .status  
curl -s http://localhost:8006/health | jq .status

# 4. AI functionality test
curl -X POST http://localhost:8006/generate/response \
  -H "Content-Type: application/json" \
  -d '{"message": "Test therapeutic response"}' | jq .message

# 5. Integration test validation
export $(cat demo/config/.env.demo_v1 | grep -v '^#' | xargs) && python -m pytest tests/integration/test_full_user_paths.py::TestAIServices -v
```

### Port Conflicts
```bash
# Check what's using demo ports
lsof -i :5433  # PostgreSQL demo
lsof -i :27018 # MongoDB demo
lsof -i :6380  # Redis demo
lsof -i :9045  # ScyllaDB demo

# Kill conflicting processes if needed
sudo kill -9 <PID>
```

### Data Reset
```bash
# Reset all demo data (nuclear option)
docker-compose -f config/docker-compose.demo.yml down -v

# Restart setup process
./scripts/run_demo.sh --databases-only
```

### Demo Script Issues
```bash
# Test API Gateway and service connectivity
python3 scripts/test_demo_real_mode.py

# Check service status
curl http://localhost:8090/health  # API Gateway
curl http://localhost:8005/health  # Embedding Service  
curl http://localhost:8006/health  # Generation Service
curl http://localhost:8001/health  # Search Service

# Check service logs
tail -f /tmp/demo_service_logs/api_gateway.log
tail -f /tmp/demo_service_logs/search_service.log

# Run demo in simulation mode if API services fail
cd ui && python3 interactive_demo.py  # No --real-data flag
```

### API Gateway Issues
```bash
# Check if API Gateway is running
lsof -i :8090

# Restart API Gateway if needed
cd microservices/api-gateway
PORT=8090 SEARCH_SERVICE_URL=http://localhost:8001 \
CHAT_SERVICE_URL=http://localhost:8002 \
EMBEDDING_SERVICE_URL=http://localhost:8005 \
GENERATION_SERVICE_URL=http://localhost:8006 \
go run . &

# Test routing
curl http://localhost:8090/api/v1/search/health
curl http://localhost:8090/api/v1/embedding/health
```

### Service Startup Order and Dependencies

#### Critical Startup Sequence (Must Follow Order)
```bash
# PHASE 1: Environment and Database Layer (Foundation)
# ================================================================

# Step 1: Load demo environment (CRITICAL - Always first)
export $(cat demo/config/.env.demo_v1 | grep -v '^#' | xargs)
echo "✅ Demo environment loaded - DEMO_MODE=$DEMO_MODE"

# Step 2: Start database containers (can be parallel)
docker-compose -f demo/config/docker-compose.demo-full.yml up -d postgres-demo mongodb-demo redis-demo

# Step 3: Start ScyllaDB cluster (sequential startup required)
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node1
sleep 30  # Critical: wait for node1 to initialize
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node2  
sleep 30  # Critical: wait for node2 to join cluster
docker-compose -f demo/config/docker-compose.demo-full.yml up -d scylla-demo-node3

# Step 4: Verify database readiness
curl -s http://localhost:5433 2>/dev/null && echo "✅ PostgreSQL ready" || echo "❌ PostgreSQL not ready"
docker exec demo-v1-mongodb mongosh --eval "db.runCommand('ping').ok" --quiet && echo "✅ MongoDB ready" || echo "❌ MongoDB not ready"
docker exec demo-v1-redis redis-cli ping | grep PONG && echo "✅ Redis ready" || echo "❌ Redis not ready"
docker exec demo-v1-scylla-node1 nodetool status | grep UN && echo "✅ ScyllaDB ready" || echo "❌ ScyllaDB not ready"

# PHASE 2: AI/ML Host Services (GPU Layer)
# ================================================================

# Step 5: Start llama.cpp server (required for generation service)
llama-server \
  -m ~/models/Qwen2-1.5B-Instruct-Q4_K_M.gguf \
  -c 8192 -ngl 999 -t 8 --port 8004 --host 0.0.0.0 --chat-template qwen &
sleep 5  # Wait for llama server to start

# Step 6: Start embedding service (BGE with GPU acceleration)
cd /Users/asqmac/git-repos/Lilo_EmotionalAI_Backend
PYTHONPATH=$PWD python host_services/embed_server.py &
sleep 5  # Wait for embedding service to initialize

# Step 7: Start generation service (depends on llama.cpp)
GENERATION_SERVICE_PORT=8006 PYTHONPATH=$PWD python host_services/generation_server.py &
sleep 5  # Wait for generation service to connect to llama

# PHASE 3: Python AI Services Layer
# ================================================================

# Step 8: Start AI Gateway (orchestrates AI/ML workloads)
PYTHONPATH=$PWD uvicorn ai_services.main:app --host 0.0.0.0 --port 8000 &
sleep 10  # Wait for AI Gateway to connect to all databases

# PHASE 4: Go Microservices Layer  
# ================================================================

# Step 9: Start search service (RAG pipeline)
cd microservices/search-service && ./search-service &
sleep 3

# Step 10: Start chat history service (ScyllaDB integration)  
cd ../chat-history && ./chat-history &
sleep 3

# Step 11: Start other microservices (parallel)
cd ../auth-rbac && ./auth-rbac &
cd ../audit-logging && ./audit-logging &
cd ../consent && ./consent &

# PHASE 5: API Gateway (Entry Point)
# ================================================================

# Step 12: Start API Gateway (single entry point)
cd ../api-gateway
PORT=8090 \
SEARCH_SERVICE_URL=http://localhost:8001 \
CHAT_SERVICE_URL=http://localhost:8002 \
EMBEDDING_SERVICE_URL=http://localhost:8005 \
GENERATION_SERVICE_URL=http://localhost:8006 \
./api-gateway &

sleep 5  # Wait for API Gateway to discover all services

# PHASE 6: Validation and Demo Launch
# ================================================================

# Step 13: Comprehensive health check
echo "🔍 Running comprehensive health check..."
curl -s http://localhost:8090/health && echo "✅ API Gateway healthy"
curl -s http://localhost:8000/health && echo "✅ AI Gateway healthy"  
curl -s http://localhost:8005/health && echo "✅ Embedding service healthy"
curl -s http://localhost:8006/health && echo "✅ Generation service healthy"

# Step 14: Run integration tests
python -m pytest tests/integration/test_full_user_paths.py::TestAIServices -v

# Step 15: Launch demo
cd demo/ui && python interactive_demo.py --use-real-data
```

#### Service Dependency Matrix
```
API Gateway (8090) [ENTRY POINT]
├─ Depends On: Search (8001), Chat History (8002), AI Gateway (8000)
│
Search Service (8001)  
├─ Depends On: AI Gateway (8000), PostgreSQL, MongoDB, Redis
│
Chat History Service (8002)
├─ Depends On: ScyllaDB cluster (9045,9046,9047)
│
AI Gateway (8000) [AI ORCHESTRATOR]
├─ Depends On: Embedding (8005), Generation (8006), All Databases
│
Host Services:
├─ Embedding Service (8005) - Independent (GPU acceleration)
├─ Generation Service (8006) 
│   └─ Depends On: llama.cpp server (8004)
└─ llama.cpp server (8004) - Independent (model file required)
```

#### Environment Variable Dependencies
```
Critical Variables (Required for proper demo operation):
- DEMO_MODE=1                 # Enables demo-specific features
- ENVIRONMENT=demo_v1         # Isolation from production
- POSTGRES_PORT=5433          # Demo PostgreSQL port
- MONGO_PASSWORD=demo_example_v1  # Correct demo password
- REDIS_PORT=6380            # Demo Redis port  
- MONGO_PORT=27018           # Demo MongoDB port
- PYTHONPATH=/path/to/project # Module resolution
```

### Holistic Troubleshooting Guide for New Team Members

#### Quick Diagnostic Commands
```bash
# Single command to check everything
python -c "
import os, asyncio, subprocess, asyncpg, redis
from motor.motor_asyncio import AsyncIOMotorClient

async def full_diagnostic():
    print('🔍 MultiDB Therapeutic AI Demo - Complete Diagnostic')
    print('=' * 60)
    
    # Environment check
    demo_mode = os.getenv('DEMO_MODE', 'NOT_SET')
    environment = os.getenv('ENVIRONMENT', 'NOT_SET') 
    postgres_port = os.getenv('POSTGRES_PORT', 'NOT_SET')
    mongo_password = os.getenv('MONGO_PASSWORD', 'NOT_SET')
    
    print(f'Environment: {\"✅\" if demo_mode == \"1\" else \"❌\"} DEMO_MODE={demo_mode}')
    print(f'Environment: {\"✅\" if environment == \"demo_v1\" else \"❌\"} ENVIRONMENT={environment}')
    print(f'PostgreSQL: {\"✅\" if postgres_port == \"5433\" else \"❌\"} PORT={postgres_port}')
    print(f'MongoDB: {\"✅\" if mongo_password == \"demo_example_v1\" else \"❌\"} PASSWORD={mongo_password}')
    
    # Database connectivity
    print('\n🔗 Database Connectivity:')
    try:
        conn = await asyncpg.connect('postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app')
        await conn.close()
        print('✅ PostgreSQL demo: Connected')
    except Exception as e: print(f'❌ PostgreSQL demo: {str(e)[:50]}...')
    
    try:
        client = AsyncIOMotorClient('mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true')
        await client.admin.command('ping')
        client.close()
        print('✅ MongoDB demo: Connected')
    except Exception as e: print(f'❌ MongoDB demo: {str(e)[:50]}...')
    
    try:
        r = redis.Redis(host='localhost', port=6380, db=10)
        r.ping()
        print('✅ Redis demo: Connected')
    except Exception as e: print(f'❌ Redis demo: {str(e)[:50]}...')
    
    # Service health
    print('\n🏥 Service Health:')
    services = [
        ('AI Gateway', 'http://localhost:8000/health'),
        ('Embedding', 'http://localhost:8005/health'),
        ('Generation', 'http://localhost:8006/health'),
        ('API Gateway', 'http://localhost:8090/health')
    ]
    
    for name, url in services:
        try:
            result = subprocess.run(['curl', '-s', url], capture_output=True, timeout=3)
            status = '✅' if result.returncode == 0 else '❌'
            print(f'{status} {name}: {\"Healthy\" if result.returncode == 0 else \"Unhealthy\"}')
        except: print(f'❌ {name}: Timeout/Error')
    
    print('\n📋 Next Steps:')
    print('1. If environment ❌: export \$(cat demo/config/.env.demo_v1 | grep -v \"^#\" | xargs)')
    print('2. If databases ❌: docker-compose -f demo/config/docker-compose.demo-full.yml up -d')
    print('3. If services ❌: Follow service startup sequence in README')
    print('4. Run integration tests: pytest tests/integration/test_full_user_paths.py -v')
    print('5. Launch demo: cd demo/ui && python interactive_demo.py --use-real-data')

asyncio.run(full_diagnostic())
"
```

#### Common Resolution Patterns

**Pattern 1: Environment Not Loaded**
```bash
# Symptom: Wrong database ports, authentication failures
# Root Cause: Demo environment variables not loaded
# Fix: Always run FIRST: export $(cat demo/config/.env.demo_v1 | grep -v '^#' | xargs)
```

**Pattern 2: Database Connection Refused**  
```bash
# Symptom: Connection refused errors to databases
# Root Cause: Demo containers not running or wrong ports
# Fix: Check docker ps, start demo containers, verify ports match environment
```

**Pattern 3: Service Startup Failures**
```bash
# Symptom: Services crash on startup or can't connect to dependencies
# Root Cause: Wrong startup order or missing dependencies
# Fix: Follow 5-phase startup sequence, wait for dependencies
```

**Pattern 4: Import/Module Errors**
```bash
# Symptom: ModuleNotFoundError in tests or services
# Root Cause: Missing PYTHONPATH or old import paths
# Fix: Set PYTHONPATH, update imports from 'app.' to 'ai_services.'
```

**Pattern 5: Authentication Failures**
```bash
# Symptom: Admin endpoints return 403/500 errors
# Root Cause: User model constructor issues or missing demo users
# Fix: Check User() parameters, create demo users in PostgreSQL
```

## 🎓 Educational Value

### For Product Teams
- Complete feature walkthrough
- User acceptance testing scenarios
- Stakeholder demonstration tool
- Requirements validation

### For Healthcare Organizations
- Implementation planning
- Staff training preparation
- Change management support
- ROI demonstration

### For Technical Teams
- Architecture understanding
- API integration examples
- Security and compliance requirements
- Performance characteristics

## 🧹 Clean Up

```bash
# Stop demo databases
docker-compose -f config/docker-compose.demo.yml down

# Remove demo data volumes (optional)
docker-compose -f config/docker-compose.demo.yml down -v

# Remove demo Docker images (optional)
docker system prune -f
```

## 🔄 Demo Customization

### Adding New Scenarios
1. Extend the `DemoUser` class with new personas
2. Add conversation flows in respective `_conversation_flow` methods
3. Create dashboard views in `dashboard_analytics_demo`
4. Update menu options and navigation

### Modifying User Data
- Edit persona data in `scripts/seed_demo_data.py`
- Adjust metrics and outcomes in dashboard functions
- Customize conversation responses and interventions

### Branding and Messaging
- Update `Colors` class for custom color scheme
- Modify headers and titles throughout the demo
- Customize organization names and contexts

## 📞 Support and Documentation

- **Technical Architecture**: See `../CLAUDE.md` for system details
- **Business Value**: Review `../docs/Business_Value_Proposition.md`
- **User Workflows**: Reference `../docs/User_Guide.md`
- **Demo Data**: Realistic files available in `../data/demo/`
- **System Architecture**: Check `../docs/00_System_Architecture_Overview.md`

---

**Demo Session Analytics**: The system tracks session duration, feature exploration, user engagement patterns, and common exit points to continuously improve the demonstration experience.