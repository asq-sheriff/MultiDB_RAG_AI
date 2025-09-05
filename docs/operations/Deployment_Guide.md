---
title: Deployment Guide
owner: DevOps Team
last_updated: 2025-09-01
status: authoritative
---

# Deployment Guide

> **Complete production deployment procedures for healthcare AI platform**

## Table of Contents

1. [Environment Strategy](#environment-strategy)
2. [Local Development](#local-development)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Secret Management](#secret-management)
6. [Health Checks](#health-checks)
7. [Rollback Procedures](#rollback-procedures)

## Environment Strategy

### Environment Hierarchy

| Environment | Purpose | Compliance Level | Data |
|-------------|---------|------------------|------|
| **Local** | Developer workstations | None | Synthetic test data |
| **Development** | Shared development | Basic | De-identified test data |
| **Staging** | Pre-production testing | HIPAA-like | Anonymized production-like data |
| **Production** | Live healthcare platform | Full HIPAA | Real PHI data |

### Promotion Strategy

```mermaid
flowchart LR
    LOCAL[👨‍💻 Local Development<br/>Feature development]
    DEV[🔧 Development<br/>Integration testing]
    STAGING[🎭 Staging<br/>Pre-production validation]
    PROD[🏥 Production<br/>Live healthcare platform]
    
    LOCAL -->|PR Merge| DEV
    DEV -->|Release Branch| STAGING
    STAGING -->|HIPAA Validation| PROD
    
    style LOCAL fill:#e3f2fd
    style DEV fill:#e8f5e8
    style STAGING fill:#fff3e0
    style PROD fill:#ffebee
```

## Local Development

### Prerequisites

**System Requirements**:
- **OS**: macOS (ARM64), Linux (x86_64/ARM64), Windows with WSL2
- **Memory**: 8GB minimum, 16GB recommended
- **Storage**: 20GB available for containers and models
- **Docker**: Docker Desktop 4.0+ with Docker Compose

**Development Tools**:
```bash
# Required tools
brew install docker docker-compose terraform
brew install go python@3.11 node
brew install jq curl make

# Optional but recommended
brew install air      # Go hot reload
brew install httpie   # API testing
brew install k9s      # Kubernetes UI
```

### Quick Start

```bash
# 1. Repository setup
git clone <repository-url>
cd Lilo_EmotionalAI_Backend
make setup

# 2. Infrastructure deployment (Terraform + Docker)
make infrastructure

# 3. Database setup and migrations
make database

# 4. Service startup (20 services: 12 Go + 6 Python AI + 2 GPU host)
make start

# 5. Health verification
make health

# 6. Healthcare knowledge seeding
make seed

# 7. Run validation tests
make test
```

### Development Workflow

```bash
# Daily development commands
make dev              # Start with auto-reload
make test             # Quick validation tests (3-5 min)
make health           # Check all 20 services health
make validate         # Setup validation

# Testing categories (9 total)
make test-all         # Full test suite (15-20 min)
make test-hipaa       # HIPAA compliance (100% required)
make test-ai          # AI quality benchmarks
make test-security    # Security audit tests

# Infrastructure operations
make demo             # Interactive therapeutic AI demo
make reset            # Complete system reset
make production-ready # Full deployment readiness check
```

## Staging Deployment

### Infrastructure Setup

**Kubernetes Cluster Requirements**:
- **Nodes**: 3 worker nodes minimum
- **CPU**: 16 cores total
- **Memory**: 64GB total
- **Storage**: 500GB persistent storage
- **Network**: Private VPC with jump host access

### Staging Deployment

```bash
# 1. Infrastructure provisioning via Terraform
cd terraform
terraform init
terraform plan -var-file="staging.tfvars"
terraform apply

# 2. Kubernetes cluster setup
kubectl config use-context staging-cluster
kubectl create namespace therapeutic-ai

# 3. Secret deployment
kubectl apply -f deployment/staging/secrets.yaml

# 4. Database deployment (4 databases)
helm install postgres bitnami/postgresql -f deployment/staging/postgres-values.yaml
helm install mongodb bitnami/mongodb -f deployment/staging/mongodb-values.yaml
helm install redis bitnami/redis -f deployment/staging/redis-values.yaml
helm install scylladb scylladb/scylla -f deployment/staging/scylla-values.yaml

# 5. Go microservices deployment (12 services)
kubectl apply -f deployment/staging/microservices/

# 6. Python AI services deployment (6 services + 2 GPU hosts)
kubectl apply -f deployment/staging/ai-services/

# 7. Health verification (20 services total)
kubectl get pods -n therapeutic-ai
make health
make test-hipaa
```

### Staging Validation

```bash
# HIPAA compliance pre-check
make test-hipaa-staging

# Performance validation
make test-performance-staging

# Integration testing
make test-integration-staging

# Security scanning
make security-scan-staging
```

## Production Deployment

### Pre-Deployment Checklist

**Required Validations**:
- [ ] ✅ HIPAA compliance tests pass 100%
- [ ] ✅ Security penetration testing completed
- [ ] ✅ Performance benchmarks meet SLA requirements
- [ ] ✅ Backup and recovery procedures tested
- [ ] ✅ Incident response procedures validated
- [ ] ✅ Change approval documentation completed

### Production Infrastructure

**20-Service High-Availability Architecture**:
```yaml
# Production cluster configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: production-config
data:
  # Database configuration (4 databases)
  postgres_replicas: "3"     # PostgreSQL with pgvector
  mongodb_replica_set: "true" # MongoDB Atlas with vector search  
  redis_cluster_mode: "true"  # Redis for caching
  scylla_datacenter_count: "3" # ScyllaDB for chat history
  
  # Go Microservices scaling (12 services)
  api_gateway_replicas: "5"     # Primary entry point
  auth_rbac_replicas: "3"       # Authentication & authorization
  chat_history_replicas: "3"    # Conversation storage
  search_service_replicas: "3"  # RAG pipeline
  billing_replicas: "2"         # Usage tracking
  audit_logging_replicas: "3"   # HIPAA compliance
  content_safety_replicas: "2"  # PHI detection
  consent_replicas: "2"         # HIPAA consent
  emergency_access_replicas: "2" # Break-glass access
  background_tasks_replicas: "2" # Async processing
  relationship_mgmt_replicas: "2" # User relationships
  user_subscription_replicas: "2" # Subscription management
  
  # Python AI Services scaling (6 services + 2 GPU hosts)
  ai_gateway_replicas: "3"       # AI orchestration
  embedding_service_replicas: "2" # Vector embeddings
  generation_service_replicas: "2" # LLM generation
  bge_host_replicas: "2"         # GPU-accelerated BGE
  qwen_host_replicas: "2"        # GPU-accelerated Qwen
  
  # Performance settings
  max_connections_per_service: "100"
  cache_ttl_seconds: "3600"
  request_timeout_seconds: "30"
  confidence_threshold: "0.7"
```

### Blue-Green Deployment

```bash
# 1. Deploy green environment (20 services)
export DEPLOYMENT_COLOR=green
kubectl apply -f deployment/production/green/microservices/
kubectl apply -f deployment/production/green/ai-services/

# 2. Health check all services in green environment
make health  # Checks all 20 services
curl http://api-gateway-green:8090/health

# 3. Run comprehensive validation tests
make test-hipaa      # HIPAA compliance (100% required)
make test-ai         # AI quality benchmarks
make test-security   # Security audit

# 4. Switch traffic to green (API Gateway entry point)
kubectl patch service api-gateway -p '{"spec":{"selector":{"version":"green"}}}'

# 5. Monitor all service metrics
make production-ready
watch kubectl get pods -l version=green

# 6. Cleanup blue environment (after 24h monitoring)
kubectl delete -f deployment/production/blue/
```

## Secret Management

### Secret Categories

| Secret Type | Examples | Rotation Period | Storage |
|-------------|----------|-----------------|---------|
| **Database Credentials** | PostgreSQL, MongoDB passwords | 90 days | Vault + K8s Secrets |
| **API Keys** | External service keys | 180 days | Vault |
| **Encryption Keys** | AES keys for PHI data | 90 days | HSM + Vault |
| **TLS Certificates** | Service certificates | 90 days | cert-manager |
| **JWT Signing Keys** | Authentication tokens | 30 days | Vault |

### Secret Deployment

```bash
# 1. Initialize Vault
vault auth -method=kubernetes

# 2. Store production secrets
vault kv put secret/therapeutic-ai/production \
  postgres_password="${POSTGRES_PASSWORD}" \
  mongodb_password="${MONGODB_PASSWORD}" \
  redis_password="${REDIS_PASSWORD}"

# 3. Deploy Kubernetes secrets
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: database-secrets
type: Opaque
stringData:
  postgres-url: "postgresql://user:${POSTGRES_PASSWORD}@postgres:5432/therapeutic_ai"
  mongodb-url: "mongodb://user:${MONGODB_PASSWORD}@mongodb:27017/therapeutic_ai"
  redis-url: "redis://:${REDIS_PASSWORD}@redis:6379"
EOF
```

## Health Checks

### Service Health Monitoring

**Health Check Endpoints**:
```bash
# Primary entry point
curl http://api-gateway:8090/health

# Go microservices (12 services)
curl http://auth-rbac:8080/health
curl http://chat-history:8002/health
curl http://search-service:8001/health
curl http://billing:8081/health
curl http://audit-logging:8084/health
curl http://content-safety:8007/health
curl http://consent:8083/health
curl http://emergency-access:8085/health
curl http://background-tasks:8086/health
curl http://relationship-mgmt:8087/health
curl http://user-subscription:8088/health

# Python AI services (6 services)
curl http://ai-gateway:8000/health
curl http://embedding-service:8005/health
curl http://generation-service:8006/health

# GPU host services (2 services)
curl http://bge-host:8008/health
curl http://qwen-host:8009/health

# Database health via API Gateway
curl http://api-gateway:8090/health/database
```

**Health Check Response**:
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "1.0.0",
  "timestamp": "2025-09-01T12:00:00Z",
  "dependencies": {
    "auth-service": "healthy",
    "ai-gateway": "healthy", 
    "database": "healthy",
    "cache": "healthy"
  },
  "compliance": {
    "hipaa_audit_enabled": true,
    "encryption_active": true,
    "access_controls_active": true
  }
}
```

### Readiness vs Liveness

**Readiness Probe**: Service can accept traffic
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
```

**Liveness Probe**: Service is running correctly
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
```

## Rollback Procedures

### Automated Rollback Triggers

**Automatic Rollback Conditions**:
- Health check failure rate >10% for 5 minutes
- Error rate >5% for 3 minutes
- HIPAA compliance test failures
- Security alert threshold exceeded

### Manual Rollback Process

```bash
# 1. Identify current deployment
kubectl get deployments -l version=current

# 2. Quick rollback to previous version
kubectl rollout undo deployment/api-gateway
kubectl rollout undo deployment/auth-rbac
kubectl rollout undo deployment/ai-gateway

# 3. Verify rollback success
kubectl rollout status deployment/api-gateway
make health-check-production

# 4. Update traffic routing
kubectl patch service api-gateway -p '{"spec":{"selector":{"version":"previous"}}}'

# 5. Incident documentation
# Document rollback reason and timeline in incident response system
```

### Database Rollback

```bash
# Database schema rollback (if needed)
alembic downgrade -1  # PostgreSQL schema
mongo --eval "db.runCommand({drop: 'new_collection'})"  # MongoDB cleanup

# Data restoration from backup (extreme cases only)
kubectl exec -it postgres-0 -- pg_restore -d therapeutic_ai /backup/latest.dump
```

## Monitoring & Validation

### Post-Deployment Validation

```bash
# 1. Service health validation (20 services)
make health

# 2. HIPAA compliance verification (100% required)
make test-hipaa

# 3. AI quality and performance validation
make test-ai

# 4. Security audit validation
make test-security

# 5. Full system integration testing
make test-all

# 6. Production readiness check
make production-ready

# 7. Performance benchmarking
make test | grep "Performance:"
```

### Production Monitoring

**Key Metrics to Monitor**:
- **Response Times**: API Gateway <100ms, AI Gateway <2s, Auth <50ms
- **Error Rates**: <1% for all 20 services
- **Database Performance**: <10ms PostgreSQL, <20ms MongoDB, <5ms Redis, <5ms ScyllaDB
- **AI Performance**: <500ms search, <1s embedding, <2s generation
- **Queue Depth**: <100 background tasks
- **HIPAA Compliance**: 100% audit coverage, 100% PHI detection
- **Cache Performance**: >85% hit rate across L1/L2/L3 cache tiers
- **GPU Utilization**: <80% average for BGE/Qwen hosts

**Monitoring Dashboard**: [Production Dashboard](http://grafana.internal/d/production-overview)

## Troubleshooting Deployment Issues

### Common Deployment Problems

**Issue**: Pod startup failures
```bash
# Diagnosis
kubectl describe pod <pod-name>
kubectl logs <pod-name> --previous

# Resolution
# Check resource limits, secrets availability, and image pull status
```

**Issue**: Database connection failures
```bash
# Diagnosis  
kubectl exec -it <api-pod> -- nc -zv postgres 5432

# Resolution
# Verify database pod health, secret values, and network policies
```

**Issue**: HIPAA compliance failures
```bash
# Diagnosis
make test-hipaa-verbose

# Resolution  
# Check audit service health, encryption configuration, and access controls
```

### Emergency Procedures

**Production Incident Response**:
1. **Immediate**: Switch to maintenance mode
2. **Assess**: Run diagnostic health checks
3. **Mitigate**: Apply immediate fixes or rollback
4. **Communicate**: Notify stakeholders of status
5. **Resolve**: Implement permanent fix
6. **Document**: Complete incident post-mortem

---

**Deployment Version**: 3.0  
**Last Production Deployment**: 2025-09-01  
**Next Scheduled Deployment**: 2025-09-08  
**Maintained By**: DevOps Team + Platform Team