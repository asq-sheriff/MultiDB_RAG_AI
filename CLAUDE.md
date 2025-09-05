# Claude Code Memory - MultiDB Therapeutic AI Chatbot

## Project Architecture Quick Reference

### **Core Services & Ports**
**Python AI/ML Services**:
- **AI Gateway**: Port 8000 (FastAPI) - AI orchestrator (`ai_services/main.py`)
- **Search Service**: Port 8001 - RAG pipeline
- **Embedding Service**: Port 8005 - BGE-large-en-v1.5
- **Generation Service**: Port 8006 - Qwen2.5-7B
- **BGE Host**: Port 8008 - GPU-accelerated embeddings
- **Qwen Host**: Port 8007 - GPU-accelerated generation

**Go Microservices**:
- **API Gateway**: Port 8090 - Primary entry point (`microservices/api-gateway/main.go`)
- **Auth/RBAC**: Port 8080 - Authentication & authorization
- **Chat History**: Port 8002 - Conversation storage (ScyllaDB)
- **Consent**: Port 8083 - HIPAA consent management
- **Audit Logging**: Port 8084 - Compliance audit trails
- **Billing**: Port 8081 - Usage tracking
- **Emergency Access**: Port 8085 - Break-glass access
- **Content Safety**: Port 8007 - PHI detection

### **Database Architecture**
- **PostgreSQL + pgvector**: Primary app data, 5 schemas (auth, compliance, app, memory, knowledge)
- **MongoDB Atlas**: Document storage, vector search
- **Redis**: Caching, session management, rate limiting  
- **ScyllaDB**: Conversation history, time-series analytics

### **Critical Commands**
```bash
# First-time setup
make setup && make infrastructure && make start && make test

# Daily development workflow
make dev              # Auto-reload development
make test             # Quick validation (3-5 min)
make health           # Service health check
make validate         # Setup validation

# Infrastructure management
make infrastructure   # Deploy all infrastructure (Terraform)
make database         # Setup databases and migrations
make seed            # Seed healthcare knowledge base

# Testing categories (9 total)
make test            # Quick smoke tests
make test-all        # Full test suite (15-20 min)
make test-hipaa      # HIPAA compliance (REQUIRED - blocking)
make test-ai         # AI quality benchmarks
make test-security   # Security audit tests

# Service management
make start           # Start all services
make stop            # Stop all services
make demo            # Interactive therapeutic AI demo
make reset           # Complete system reset
make production-ready # Full deployment readiness check
```

### **Key File Locations**
**Core Configuration**:
- **Main Config**: `config/config.py` (Enhanced with AI model configs)
- **Database Models**: `data_layer/models/postgres/postgres_models.py`
- **AI Gateway**: `ai_services/main.py` (Python FastAPI)
- **API Gateway**: `microservices/api-gateway/main.go` (Go primary entry)
- **Enhanced Chatbot**: `ai_services/core/chatbot_service.py`

**Critical Documentation**:
- **Architecture**: `docs/ARCHITECTURE.md` (858 lines - authoritative system design)
- **Requirements Analysis**: `docs/reqs/` (Comprehensive feature requirements and priorities)
  - **AI Features**: `docs/reqs/ai_features.md` - Therapeutic AI implementation roadmap (28-week plan)
  - **Tech Infrastructure**: `docs/reqs/tech_features.md` - Platform and infrastructure requirements  
  - **Feature Priorities**: `docs/reqs/features_priority.md` - Master prioritization matrix (safety-first approach)
- **Strategic Roadmap**: `docs/Strategic_Technology_Roadmap.md` - 18-month technology evolution plan
- **Product Roadmap**: `docs/Internal_Product_Roadmap.md` - Business and market strategy (confidential)
- **Documentation Index**: `docs/TOC.md` (Complete navigation guide)
- **Test Runner**: `scripts/test_runner.py` (1,300+ lines unified framework)
- **Testing Guide**: `TESTING_GUIDE.md` (Comprehensive testing workflows)
- **HIPAA Controls**: `docs/compliance/HIPAA_Controls_Matrix.md`
- **Deployment Guide**: `docs/operations/Deployment_Guide.md` (461 lines)

**AI Services Core** (`ai_services/core/`):
- **Intelligent Data Router**: `intelligent_data_router.py`
- **Therapeutic Cache Manager**: `therapeutic_cache_manager.py` 
- **Advanced Ranking**: `advanced_ranking_service.py`
- **Knowledge Service**: `knowledge_service.py`
- **Cross Encoder**: `cross_encoder_service.py`

### **HIPAA Compliance Requirements**
- **100% pass rate required** on HIPAA tests (blocking)
- **Technical Safeguards**: §164.312(a-e) fully implemented
- **Healthcare Roles**: system, admin, health_provider, care_staff, family_member, resident
- **Audit Controls**: Comprehensive logging with tamper protection (HMAC-SHA256)
- **Access Control**: Multi-factor auth for healthcare providers
- **Emergency Access**: Break-glass protocols with full audit trails
- **PHI Protection**: Real-time PHI detection and encryption
- **Consent Management**: HIPAA-compliant consent workflows

**Critical HIPAA Files**:
- **Controls Matrix**: `docs/compliance/HIPAA_Controls_Matrix.md`
- **Audit Trail Guide**: `docs/compliance/Audit_Trail_Guide.md`
- **PHI Data Inventory**: `docs/compliance/PHI_Data_Inventory.md`
- **Consent Service**: `microservices/consent/README.md`
- **Emergency Access**: `microservices/emergency-access/README.md`

### **Critical Implementation Gaps (Updated 2025-09-05)**
- **🚨 BLOCKING: Crisis Detection System** - Basic keyword matching insufficient for healthcare; need ML-based crisis classification with <30 second escalation
- **🚨 BLOCKING: MongoDB Atlas Performance** - 0.82 precision unacceptable for healthcare; PostgreSQL+pgvector required (9.5x performance, >0.85 precision)
- **🚨 BLOCKING: Production UI Infrastructure** - Senior-friendly interface with WCAG 2.1 AAA compliance essential for therapeutic AI adoption
- **❌ Missing: Stateful Agentic RAG** - Router/Dispatcher Agent system with specialized therapeutic sub-agents required
- **❌ Missing: Evidence-Based Modules** - Reminiscence Therapy, Behavioral Activation, Grounding techniques for clinical outcomes
- **❌ Missing: Production Kubernetes** - Current Docker Compose insufficient for enterprise scale

### **Testing Categories (9 total)**
1. **unit**: Individual component tests
2. **integration**: Cross-service functionality
3. **system**: End-to-end system tests  
4. **performance**: Latency/throughput SLA validation
5. **security**: Security and auth testing
6. **hipaa**: HIPAA compliance (100% required)
7. **billing**: Usage tracking validation
8. **slow**: Long-running tests (>30s)
9. **quick**: Fast feedback tests (<10s)

### **Performance SLA Targets**
**Service Performance**:
- **API Gateway**: <100ms response, 1000 req/sec, 99.9% availability
- **AI Gateway**: <2s response, 100 req/sec, 99.5% availability
- **Auth/RBAC**: <50ms response, 500 req/sec, 99.95% availability
- **Search Service**: <500ms response, 200 req/sec, 99.5% availability

**Database Performance**:
- **PostgreSQL**: <10ms read, <50ms write, 10K TPS
- **MongoDB**: <20ms read, <100ms write, 5K TPS
- **Redis**: <1ms read, <5ms write, 100K ops/sec
- **ScyllaDB**: <5ms read, <10ms write, 50K writes/sec

**AI Performance**:
- **Safety Analysis**: <1.0s response, >5 req/sec
- **Combined Analysis**: <3.0s response, >1.5 req/sec
- **Cache Performance**: 10x speedup requirement
- **Stress Test**: 95%+ success rate over 2 minutes

### **Development Workflow**
1. Always run `make test-quick` before changes
2. HIPAA tests must pass before any deployment
3. Use `make health-check` to validate service status
4. Performance tests for any AI/database changes
5. Full `make test-comprehensive` before major releases

### **Service Dependencies**
```
API Gateway (Go:8090) - Primary Entry Point
    ├── Auth/RBAC (Go:8080) - Authentication
    ├── AI Gateway (Python:8000) - AI Orchestrator
    │   ├── Search Service (Python:8001) - RAG pipeline
    │   ├── Embedding Service (Python:8005) - BGE embeddings
    │   ├── Generation Service (Python:8006) - Qwen LLM
    │   ├── BGE Host (Python:8008) - GPU-accelerated
    │   └── Qwen Host (Python:8007) - GPU-accelerated
    ├── Chat History (Go:8002) - ScyllaDB integration
    ├── Consent (Go:8083) - HIPAA consent management
    ├── Audit Logging (Go:8084) - Compliance trails
    ├── Content Safety (Go:8007) - PHI detection
    └── Databases (PostgreSQL, MongoDB, Redis, ScyllaDB)
```

### **Environment Variables (Key)**
- `ENABLE_POSTGRESQL=true` (required)
- `ENABLE_MONGODB=true` (vector search)
- `USE_REAL_EMBEDDINGS=true` (production)
- `HIPAA_AUDIT_LEVEL=strict` (compliance)
- `CACHE_TTL=3600` (performance)

### **Therapeutic AI Context**
- **Target**: Elderly care conversations
- **Safety**: Content validation required
- **Emotional AI**: Sentiment analysis integrated
- **Memory**: Relationship context preservation
- **Cultural Sensitivity**: Response adaptation

## Session Notes

### Recent Accomplishments
- **Architecture Migration**: Completed migration from legacy `app/` to hybrid `ai_services/` + `microservices/`
- **Documentation Overhaul**: Created authoritative `docs/ARCHITECTURE.md` (858 lines) and `docs/TOC.md`
- **Testing Framework**: Enhanced unified test runner with 9 categories and comprehensive reporting
- **HIPAA Compliance**: Implemented technical safeguards §164.312(a-e) with 100% pass rate
- **Hybrid Service Model**: 11 Go microservices + Python AI services architecture
- **Production Readiness**: Enhanced Makefile with 20+ operational commands

### Current Focus Areas (Updated 2025-09-05)
1. **🚨 Priority 1 Implementation**: Crisis detection system and security infrastructure (Weeks 1-4)
2. **🎯 Production UI Development**: Senior-friendly web + mobile interfaces with WCAG 2.1 AAA compliance (Weeks 5-8)
3. **🏗️ Platform Migration**: MongoDB Atlas → PostgreSQL+pgvector for healthcare-grade performance (9.5x improvement)
4. **🤖 Therapeutic AI Architecture**: Stateful Agentic RAG with Router/Dispatcher Agent system
5. **📊 Evidence-Based Implementation**: Clinical validation with measurable outcomes (loneliness ↓2 points, anxiety ↓35%)

### Next Priority Tasks (28-Week Roadmap)
**🚨 CRITICAL (Weeks 1-12)**:
1. **Crisis Detection & Safety Pipeline** - ML-based crisis classification with SBAR handoff protocol
2. **Advanced Security Infrastructure** - Zero-trust networking, threat detection, vulnerability management  
3. **Production UI Framework** - Mobile-first design with healthcare accessibility standards
4. **Core Therapeutic Chat Interface** - Emotion-aware responses with crisis intervention UI
5. **Healthcare Staff Dashboard** - Real-time patient monitoring and care coordination
6. **Production Kubernetes Infrastructure** - Auto-scaling, high availability, service mesh

**🎯 HIGH (Weeks 13-20)**:
7. **Stateful Agentic RAG Architecture** - Router/Dispatcher with specialized sub-agents
8. **Evidence-Based Therapeutic Modules** - Reminiscence, Behavioral Activation, Grounding techniques
9. **Mobile Application Development** - React Native apps for seniors and family members
10. **Real-Time Event Streaming Platform** - Apache Kafka for therapeutic event processing

## Implementation Status & Requirements Reference

### **Current Implementation Assessment**
**🟢 Strong Foundation (Implemented)**:
- ✅ Hybrid microservices architecture (12 Go + 6 Python services)
- ✅ Multi-database specialization (PostgreSQL, MongoDB, Redis, ScyllaDB)
- ✅ HIPAA-compliant security framework with comprehensive audit trails
- ✅ GPU-accelerated AI services with BGE embeddings + Qwen generation
- ✅ Basic RAG pipeline with therapeutic optimizations
- ✅ Infrastructure-as-Code with Terraform

**🟡 Partially Implemented (In Progress)**:
- ⚠️ Crisis detection (basic keyword matching, needs ML classification)
- ⚠️ Therapeutic personalization (framework exists, rules incomplete)  
- ⚠️ Multi-database routing (infrastructure present, intelligence limited)
- ⚠️ Service mesh and observability (basic monitoring, needs production-grade)

**🔴 Critical Gaps (Blocking Production)**:
- ❌ **Production UI/UX Platform** - Senior-friendly interfaces with accessibility compliance
- ❌ **ML-Based Crisis Detection** - Clinical-grade safety monitoring and escalation
- ❌ **Stateful Agentic RAG** - Router/Dispatcher with therapeutic sub-agents
- ❌ **Evidence-Based Modules** - Clinically-validated therapeutic interventions
- ❌ **Production Kubernetes** - Enterprise-scale deployment and orchestration
- ❌ **Healthcare Integration** - FHIR R4 compliance and EHR connectivity

### **Detailed Requirements References**
For comprehensive implementation details, see:
- **AI & Therapeutic Features**: [docs/reqs/ai_features.md](docs/reqs/ai_features.md)
  - Prioritized 28-week AI implementation plan
  - Clinical validation requirements and success metrics
  - Evidence-based therapeutic modules specifications

- **Technical Infrastructure**: [docs/reqs/tech_features.md](docs/reqs/tech_features.md)  
  - Production Kubernetes platform requirements
  - MLOps and real-time event streaming architecture
  - Healthcare integration and security infrastructure

- **Master Priority Matrix**: [docs/reqs/features_priority.md](docs/reqs/features_priority.md)
  - Cross-referenced priority framework with safety-first approach
  - UI/UX requirements for web and mobile platforms
  - Resource requirements and implementation timeline

### **Expected Clinical Outcomes**
Based on evidence-based interventions implementation:
- **Loneliness** ↓ ~2 points (UCLA-3 scale)
- **Anxiety incidents** ↓ ~35% (GAD-7 improvements)  
- **ED visits** ↓ ~8% through proactive care
- **Readmissions** ↓ ~12% via continuous monitoring
- **Family/staff satisfaction** ↑ +18% through enhanced care coordination

## Code Patterns to Remember

### Database Connection Pattern
```python
# Use the unified data layer abstraction
from data_layer.connections.postgres_connection import get_enhanced_postgres_manager
from data_layer.connections.mongo_connection import get_enhanced_mongo_manager
from data_layer.connections.redis_connection import get_redis_manager
from data_layer.connections.scylla_connection import get_scylla_manager

async def get_db_session():
    return await get_enhanced_postgres_manager()
```

### HIPAA Audit Logging Pattern
```python
# All user actions require audit trails
await audit_service.log_action(
    user_id=user.id,
    action="conversation_start",
    resource_type="therapeutic_session",
    additional_context=context
)
```

### Service Health Check Pattern
```python
# Standard health check response
return {
    "status": "healthy",
    "service": "api-gateway",
    "timestamp": datetime.utcnow(),
    "dependencies": {...}
}
```

### RAG Pipeline Pattern
```python
# Enhanced multi-database RAG with therapeutic context
from ai_services.core.intelligent_data_router import IntelligentDataRouter
from ai_services.core.therapeutic_cache_manager import TherapeuticCacheManager

router = IntelligentDataRouter()
cache_manager = TherapeuticCacheManager()

search_results = await router.route_query(
    query=user_query,
    user_context=session_context,
    preferred_sources=["mongodb", "postgresql"],
    therapeutic_context=therapeutic_context
)
```

## Troubleshooting Quick Reference

### Service Won't Start
1. Check `make health` or `make validate`
2. Verify infrastructure: `make infrastructure`
3. Check service logs: `docker-compose logs [service]`
4. Database status: `make database` and check port conflicts
5. Reset if needed: `make reset` (destructive operation)

### Tests Failing
1. **HIPAA tests fail**: Check audit logging setup in `microservices/audit-logging/`
2. **Performance tests fail**: Verify cache configuration in `ai_services/core/therapeutic_cache_manager.py`
3. **Integration tests fail**: Ensure all services running with `make start`
4. **AI quality tests fail**: Check RAG pipeline in `ai_services/core/intelligent_data_router.py`
5. **Go tests fail**: Run `scripts/run_go_tests.sh` for microservices debugging

### Database Issues
1. **PostgreSQL**: Check pgvector extension installation and `data_layer/models/postgres/`
2. **MongoDB**: Verify Atlas configuration and indexes in `ai_services/ingestion_pipeline/`
3. **Redis**: Check connection pooling settings in `data_layer/connections/redis_connection.py`
4. **ScyllaDB**: Verify cluster health status and `data_layer/connections/scylla_connection.py`

## Architecture Evolution Notes

### **System Migration Status**
- **From**: Monolithic `app/` structure (deleted in current branch)
- **To**: Hybrid architecture with `ai_services/` (Python) + `microservices/` (Go) + `data_layer/` (unified)
- **Branch**: `feat/phase1-emotional-ai-foundation` (active development)
- **Status**: Phase 1 implementation with emotional AI foundation

### **Critical Architecture Files**
- **System Design**: `docs/ARCHITECTURE.md` (858 lines - authoritative)
- **Documentation Navigation**: `docs/TOC.md` (Complete file reference)
- **Testing Framework**: `TESTING_GUIDE.md` + `scripts/test_runner.py`
- **Deployment Procedures**: `docs/operations/Deployment_Guide.md` (461 lines)
- **HIPAA Controls**: `docs/compliance/HIPAA_Controls_Matrix.md`

### **Development Environment**
- **Terraform**: Infrastructure as Code for local development
- **Docker**: Infrastructure services (databases)
- **Go Services**: Business logic microservices
- **Python Services**: AI/ML workloads with GPU acceleration
- **Unified Testing**: Single test runner for all services