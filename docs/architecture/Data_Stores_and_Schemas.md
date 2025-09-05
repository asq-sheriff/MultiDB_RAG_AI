# 🗄️ Data Stores and Schemas Guide  
> **Comprehensive Guide to Multi-Database Architecture**

**Objective**: Detailed documentation of each data store, schema definitions, data lifecycle policies, and backup/recovery procedures  
**Audience**: Database Engineers, Backend Developers, DevOps Engineers  
**Prerequisites**: Understanding of SQL, NoSQL, vector databases, and HIPAA requirements

---

## 📋 Key Concepts

### Multi-Database Strategy
The MultiDB-Chatbot implements **database specialization** where each data store is optimized for specific data patterns and access requirements:

- **PostgreSQL**: ACID compliance for user data and relationships
- **MongoDB**: Document flexibility for unstructured healthcare content  
- **Redis**: In-memory performance for sessions and real-time caching
- **ScyllaDB**: High-write throughput for conversation analytics

### HIPAA Compliance Design
- **Data Minimization**: Store only necessary PHI with explicit consent
- **Encryption at Rest**: AES-256 encryption for all sensitive data
- **Audit Trails**: Complete access logging for compliance reporting
- **Right to Erasure**: Standardized data deletion across all stores

---

## 🐘 PostgreSQL + pgvector

### Purpose & Rationale
**Primary Use**: User accounts, relationships, audit trails, and vector search infrastructure
**Technology Choice**: PostgreSQL 15 with pgvector extension  
**Rationale**: ACID compliance essential for healthcare user data, pgvector enables hybrid SQL+vector queries

### Schema Architecture

**5-Schema Architecture** (Implemented via Alembic `alembic/versions/09dbb6e2818c_initial_phase_1_schema_with_pgvector_.py`):
```sql
-- Complete 5-schema design with pgvector + citext extensions
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector for 1024-dim embeddings
CREATE EXTENSION IF NOT EXISTS citext;    -- Case-insensitive email storage

auth            -- User management, organizations, API keys, subscriptions, feature flags
compliance      -- HIPAA audit logs, consent tracking, DSAR requests, PHI access logs
app             -- Sessions, messages, user profiles, tool actions, emotion analysis
memory          -- Episodic summaries, personal embeddings (1024-dim pgvector)
knowledge       -- Documents, playbooks, document chunks with vectors (1024-dim pgvector)
```

**Complete Table Schema** (Current Alembic Implementation `alembic/versions/09dbb6e2818c*`):

```sql
-- === AUTH SCHEMA === (User Management + Organization Structure)
CREATE TABLE auth.organizations (
    organization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,  -- Healthcare facility domain
    settings JSONB,              -- Organization-specific configurations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE auth.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email CITEXT UNIQUE NOT NULL,  -- Case-insensitive email
    full_name TEXT,
    hashed_password VARCHAR(255),
    disabled BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    subscription_plan VARCHAR(50) NOT NULL DEFAULT 'free',
    organization_id UUID REFERENCES auth.organizations(organization_id),
    preferences JSONB,  -- User preferences + healthcare role data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX ix_auth_users_email ON auth.users(email);

CREATE TABLE auth.api_clients (
    client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE auth.api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES auth.api_clients(client_id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE auth.subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    plan_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    billing_cycle VARCHAR(20) NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ends_at TIMESTAMP WITH TIME ZONE,
    auto_renew BOOLEAN NOT NULL,
    limits JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE auth.usage_records (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    billing_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    billing_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_usage_resource_type ON auth.usage_records(resource_type);
CREATE INDEX idx_usage_user_period ON auth.usage_records(user_id, billing_period_start, billing_period_end);

CREATE TABLE auth.feature_flags (
    flag_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_enabled BOOLEAN NOT NULL,
    rollout_percentage INTEGER NOT NULL,
    target_user_segments VARCHAR[],
    conditions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE auth.system_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_by UUID REFERENCES auth.users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- === COMPLIANCE SCHEMA === (HIPAA + Regulatory Requirements)
CREATE TABLE compliance.audit_log (
    audit_id SERIAL PRIMARY KEY,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actor TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(user_id),
    event_type TEXT NOT NULL,
    details JSONB NOT NULL
);
CREATE INDEX idx_audit_event ON compliance.audit_log(event_type, occurred_at);
CREATE INDEX idx_audit_user_action ON compliance.audit_log(user_id, actor);

CREATE TABLE compliance.consents (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,
    granted BOOLEAN NOT NULL,
    scope JSONB NOT NULL,  -- Detailed consent scope and restrictions
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE compliance.dsar_requests (
    dsar_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    request_type TEXT NOT NULL,  -- access, portability, erasure
    status TEXT NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT
);

-- === APP SCHEMA === (Application Data + Sessions)
CREATE TABLE app.sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_sessions_user_started ON app.sessions(user_id, started_at);

CREATE TABLE app.user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(user_id) ON DELETE CASCADE,
    timezone TEXT,
    locale TEXT,
    caregiver_opt_in BOOLEAN NOT NULL,
    risk_notes TEXT,  -- Clinical risk assessment notes
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE app.messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES app.sessions(session_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    content_hash BYTEA,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    pii_present BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX idx_messages_user_created ON app.messages(user_id, created_at);

CREATE TABLE app.message_emotions (
    message_id UUID PRIMARY KEY REFERENCES app.messages(message_id) ON DELETE CASCADE,
    valence NUMERIC(4,3) NOT NULL CHECK (valence BETWEEN -1.0 AND 1.0),
    arousal NUMERIC(4,3) NOT NULL CHECK (arousal BETWEEN -1.0 AND 1.0),
    label VARCHAR(20) NOT NULL,
    confidence NUMERIC(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    prosody_features JSONB,  -- Voice analysis features if available
    inferred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_emotions_label_inferred ON app.message_emotions(label, inferred_at);

CREATE TABLE app.tool_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES app.sessions(session_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    params JSONB NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    error TEXT
);
CREATE INDEX idx_tool_actions_user_started ON app.tool_actions(user_id, started_at);

CREATE TABLE app.assistant_rationales (
    message_id UUID PRIMARY KEY REFERENCES app.messages(message_id) ON DELETE CASCADE,
    policy_selected TEXT NOT NULL,
    target_state JSONB NOT NULL,
    selected_tools VARCHAR[],
    citations JSONB NOT NULL
);

-- === MEMORY SCHEMA === (Personal Context + Episodic Memory)
CREATE TABLE memory.episodic_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    session_id UUID REFERENCES app.sessions(session_id) ON DELETE SET NULL,
    t_start TIMESTAMP WITH TIME ZONE NOT NULL,
    t_end TIMESTAMP WITH TIME ZONE NOT NULL,
    summary_text TEXT NOT NULL,
    actions_helpful VARCHAR[],
    outcome_notes TEXT,
    valence_mean NUMERIC(4,3),  -- Average emotional valence
    arousal_mean NUMERIC(4,3),  -- Average emotional arousal
    consent_required BOOLEAN NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE memory.personal_embeddings (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    summary_id UUID REFERENCES memory.episodic_summaries(summary_id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,  -- BGE-large-en-v1.5 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_personal_embeddings_user_created ON memory.personal_embeddings(user_id, created_at);
CREATE INDEX idx_personal_embeddings_embedding ON memory.personal_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- === KNOWLEDGE SCHEMA === (Healthcare Knowledge Base)
CREATE TABLE knowledge.documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    jurisdiction TEXT,  -- Healthcare regulation jurisdiction
    risk_level VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    modality TEXT NOT NULL,  -- text, audio, video, image
    url_or_path TEXT,
    checksum TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE knowledge.document_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES knowledge.documents(doc_id) ON DELETE CASCADE,
    index_type TEXT NOT NULL,
    section_path TEXT[] NOT NULL,
    heading TEXT,
    page INTEGER,
    order_in_doc INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,  -- BGE-large-en-v1.5 embeddings
    chunk_metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_doc_chunks_doc ON knowledge.document_chunks(doc_id, index_type, order_in_doc);
CREATE INDEX idx_doc_chunks_path_gin ON knowledge.document_chunks USING gin(section_path);
CREATE INDEX idx_document_chunks_embedding ON knowledge.document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE knowledge.playbooks (
    playbook_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_key TEXT UNIQUE NOT NULL,
    jurisdiction TEXT NOT NULL,
    escalation_level VARCHAR(20) NOT NULL,  -- green, yellow, orange, red
    wording_version TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE knowledge.playbook_chunks (
    pb_chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES knowledge.playbooks(playbook_id) ON DELETE CASCADE,
    order_in_pb INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,  -- BGE-large-en-v1.5 embeddings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX idx_playbook_chunks_embedding ON knowledge.playbook_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Performance Optimization

**Indexes**:
```sql
-- Vector similarity search optimization
CREATE INDEX CONCURRENTLY idx_query_embeddings_vector 
ON query_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- User lookup optimization
CREATE INDEX CONCURRENTLY idx_users_email_active 
ON users(email) WHERE is_active = true;

-- Audit trail performance  
CREATE INDEX CONCURRENTLY idx_phi_access_logs_user_time
ON phi_access_logs(user_id, access_timestamp DESC);
```

### Backup & Recovery
```bash
# Automated daily backups
pg_dump --host=localhost --username=chatbot_user --format=custom \
        --file=backups/postgres_$(date +%Y%m%d_%H%M%S).dump chatbot_app

# Point-in-time recovery setup
# WAL archiving enabled in postgresql.conf
# Recovery target: 15-minute RPO (Recovery Point Objective)
```

---

## 🍃 MongoDB Atlas Local

### Purpose & Rationale
**Primary Use**: Healthcare knowledge base, document storage, semantic search
**Technology Choice**: MongoDB 7.0 with Atlas Search (vector search)
**Rationale**: Document flexibility for unstructured medical content, built-in vector search capabilities

### Collection Architecture

**Current MongoDB Collections** (Implemented in `data_layer/connections/mongo_connection.py`):
```javascript
// === PRIMARY COLLECTION: therapeutic_content ===
// Used by: ai_services/search/ + confidence-based RAG pipeline
{
  "_id": ObjectId("66f1234567890abcdef12345"),
  "title": "Diabetes Management Guidelines for Seniors",
  "content": "Comprehensive diabetes care for elderly residents involves...",
  "content_type": "clinical_guideline",  // clinical_guideline, therapeutic_protocol, safety_procedure
  "source": "ADA Clinical Practice Guidelines 2025",
  "category": "chronic_disease_management",
  "subcategory": "endocrinology",
  "safety_level": "healthcare_provider",  // public, resident_accessible, healthcare_provider, clinical_staff_only
  "embedding": [0.123, -0.456, ...], // 1024-dimensional BGE-large-en-v1.5 vector
  "embedding_model": "BAAI/bge-large-en-v1.5",
  "embedding_dimension": 1024,
  "metadata": {
    "medical_specialty": ["endocrinology", "geriatrics"],
    "evidence_level": "A",  // A=strong evidence, B=moderate, C=limited, D=expert opinion
    "target_audience": ["healthcare_provider", "care_staff"],
    "last_reviewed": ISODate("2025-08-15"),
    "review_cycle_months": 12,
    "therapeutic_categories": ["medication_management", "lifestyle_counseling"],
    "crisis_indicators": [],  // Crisis keywords for safety routing
    "cultural_considerations": ["dietary_restrictions", "language_preferences"]
  },
  "phi_status": "sanitized",  // none, sanitized, contains_phi (blocked from caching)
  "search_optimization": {
    "confidence_keywords": ["diabetes", "blood sugar", "insulin", "glucose"],
    "therapeutic_patterns": ["medication_inquiry", "symptom_management"],
    "expected_search_strategy": "text_first"  // text_first, hybrid_preferred, vector_only
  },
  "created_at": ISODate("2025-08-01"),
  "updated_at": ISODate("2025-08-15"),
  "indexed_at": ISODate("2025-08-15")
}

// === SECONDARY COLLECTION: therapeutic_response_cache ===
// Used by: ai_services/core/therapeutic_cache_manager.py
{
  "_id": "cache_sha256_hash_12345",
  "cache_key": "therapeutic_diabetes_management_senior_emotional_support", 
  "original_query": "How can I manage my diabetes when I'm feeling overwhelmed?",
  "user_context": {
    "user_id": "user_uuid_string",
    "session_id": "session_uuid_string",
    "healthcare_role": "resident",
    "age_group": "senior",
    "medical_conditions": ["diabetes", "hypertension"]
  },
  "response_data": {
    "ai_response": "I understand feeling overwhelmed with diabetes management...",
    "rag_sources": ["doc_id_1", "doc_id_2"],
    "confidence_score": 0.89,
    "search_strategy_used": "hybrid",
    "response_quality_score": 4.3,
    "safety_validated": true
  },
  "metadata": {
    "care_contexts": ["chronic_disease_management", "emotional_support"],
    "therapeutic_categories": ["diabetes", "anxiety", "self_care"],
    "semantic_cluster": "diabetes_emotional_support_cluster_7",
    "personalization_factors": ["senior_friendly_language", "step_by_step_guidance"]
  },
  "performance_data": {
    "generation_time_ms": 1245,
    "search_time_ms": 445,
    "total_response_time_ms": 1690,
    "cache_level": "L3"
  },
  "encryption": {
    "encrypted": true,
    "encryption_method": "AES-256-GCM",
    "key_id": "healthcare_cache_key_v2",
    "phi_detected": false
  },
  "expiry_date": ISODate("2025-09-05"),  // 5-day TTL for therapeutic cache
  "created_at": ISODate("2025-09-01"),
  "last_accessed": ISODate("2025-09-04"),
  "access_count": 23
}

// === SEARCH OPTIMIZATION COLLECTION: search_strategy_performance ===
// Used by: ai_services/core/confidence_evaluator.py
{
  "_id": ObjectId("66f1234567890abcdef12346"),
  "query_pattern": "medication + dosage + senior",
  "strategy_performance": {
    "text_only": {"avg_latency_ms": 25, "relevance_score": 4.6, "success_rate": 0.94},
    "hybrid": {"avg_latency_ms": 520, "relevance_score": 4.4, "success_rate": 0.91},
    "vector_only": {"avg_latency_ms": 285, "relevance_score": 4.2, "success_rate": 0.88}
  },
  "optimal_strategy": "text_only",
  "confidence_threshold": 0.85,
  "query_count": 1247,
  "last_updated": ISODate("2025-09-04")
}
```

### Vector Search Configuration

**Atlas Search Index** (`app/utils/create_mongodb_vector_indexes.py`):
```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "embedding": {
        "dimensions": 1024,
        "similarity": "cosine", 
        "type": "knnVector"
      },
      "content": {"type": "string"},
      "category": {"type": "string"},
      "safety_level": {"type": "string"}
    }
  }
}
```

### Data Lifecycle Policies

**Content Refresh Cycle**:
- **Medical Guidelines**: 12-month review cycle with evidence level tracking
- **Conversation Cache**: 30-day TTL with automatic purging
- **Safety Protocols**: 6-month review with immediate updates for incidents

**Archival Strategy**:
```javascript
// Automatic archival for outdated content
db.healthcare_knowledge.updateMany(
  { 
    "metadata.last_reviewed": { $lt: new Date(Date.now() - 365*24*60*60*1000) }
  },
  { 
    $set: { 
      "status": "archived",
      "archived_date": new Date(),
      "archive_reason": "outdated_content"
    }
  }
)
```

---

## ⚡ Redis Cache

### Purpose & Rationale  
**Primary Use**: Session management, rate limiting, and real-time caching
**Technology Choice**: Redis 6 with persistence and clustering support
**Rationale**: Sub-millisecond performance for conversational AI responsiveness

### Data Patterns

**Session Management** (`data_layer/models/redis/redis_models.py`):
```python
# User session storage
class SessionModel:
    def store_session(self, session_id: str, user_data: Dict):
        """Store user session with 24-hour expiry"""
        key = f"session:{session_id}"
        self.client.hset(key, mapping=user_data)
        self.client.expire(key, 86400)  # 24 hours

# Chat history cache (last 10 messages)
class ChatHistoryCache:
    def add_message(self, session_id: str, message: Dict):
        """Add message to conversation history cache"""
        key = f"chat_history:{session_id}"
        self.client.lpush(key, json.dumps(message))
        self.client.ltrim(key, 0, 9)  # Keep last 10 messages
        self.client.expire(key, 3600)  # 1 hour TTL
```

**Rate Limiting** (`app/core/auth_dependencies.py:RateLimiter`):
```python
# Token bucket rate limiting
rate_limit_key = f"rate_limit:{user_id}:{resource}"
current_count = redis.incr(rate_limit_key)
if current_count == 1:
    redis.expire(rate_limit_key, time_window)
    
if current_count > max_requests:
    raise RateLimitExceeded()
```

### Performance Configuration
```yaml
# Redis optimization for conversational AI
maxmemory: 512mb
maxmemory-policy: allkeys-lru  # Evict least recently used
save: 900 1 300 10 60 10000    # Persistence snapshots
appendonly: yes                 # AOF for durability
```

---

## 🏛️ ScyllaDB Cluster

### Purpose & Rationale
**Primary Use**: High-volume conversation history and analytics
**Technology Choice**: ScyllaDB 3-node cluster  
**Rationale**: 10x higher write throughput than Cassandra, essential for conversation-heavy workloads

### Schema Design

**Conversation Storage** (`data_layer/models/scylla/scylla_models.py` + `data_layer/connections/scylla_connection.py`):
```cql
-- === PRIMARY TABLE: conversation_items ===
-- Used by: microservices/chat-history/main.go + ai_services/core/
CREATE TABLE chatbot_ks.conversation_items (
    session_id UUID,
    created_at TIMESTAMP,
    message_id UUID,
    actor TEXT,  -- 'user' or 'assistant'
    text_content TEXT,
    metadata MAP<TEXT, TEXT>,  -- Emotion data, safety flags, performance metrics
    user_id UUID,
    service_context TEXT,  -- Which AI service generated the response
    content_hash TEXT,  -- For deduplication and integrity
    safety_analysis MAP<TEXT, TEXT>,  -- PHI detected, crisis indicators, emotional tone
    performance_data MAP<TEXT, TEXT>,  -- Response time, search strategy, cache hits
    PRIMARY KEY (session_id, created_at, message_id)
) WITH CLUSTERING ORDER BY (created_at DESC)
  AND gc_grace_seconds = 864000  -- 10-day grace period
  AND default_time_to_live = 47304000;  -- 18-month retention

-- === ANALYTICS TABLE: conversation_analytics ===
-- Used by: Background analytics processing + reporting
CREATE TABLE chatbot_ks.conversation_analytics (
    date DATE,
    user_id UUID, 
    total_messages INT,
    avg_response_time_ms INT,
    emotion_distribution MAP<TEXT, INT>,  -- emotion_label -> count
    safety_incidents INT,
    search_strategy_usage MAP<TEXT, INT>,  -- text_only, hybrid, vector_only counts
    cache_hit_rate DECIMAL,
    therapeutic_quality_avg DECIMAL,  -- Average quality score for the day
    PRIMARY KEY (date, user_id)
) WITH default_time_to_live = 220752000;  -- 7-year retention for analytics

-- === PERFORMANCE TABLE: service_performance_metrics ===
-- Used by: Real-time performance monitoring
CREATE TABLE chatbot_ks.service_performance_metrics (
    service_name TEXT,
    timestamp TIMESTAMP,
    metric_id UUID,
    metric_name TEXT,  -- latency, throughput, error_rate, cache_hits
    metric_value DECIMAL,
    tags MAP<TEXT, TEXT>,  -- Additional context tags
    PRIMARY KEY (service_name, timestamp, metric_id)
) WITH CLUSTERING ORDER BY (timestamp DESC)
  AND default_time_to_live = 2678400;  -- 31-day retention for performance data
```

### Cluster Configuration
```yaml
# 3-node cluster for high availability
Nodes:
  - scylla-node1: localhost:9042 (seed node)
  - scylla-node2: localhost:9043  
  - scylla-node3: localhost:9044

Replication: 
  strategy: NetworkTopologyStrategy
  replication_factor: 2  # 2/3 node redundancy

Consistency:
  read: LOCAL_ONE   # Fast reads
  write: LOCAL_ONE  # Fast writes with eventual consistency
```

### Data Retention Policies
```cql
-- Conversation history retention (18 months for compliance)
ALTER TABLE conversation_items 
WITH default_time_to_live = 47304000;  -- 18 months in seconds

-- Analytics aggregation (7 years for business intelligence)  
ALTER TABLE conversation_analytics
WITH default_time_to_live = 220752000;  -- 7 years
```

---

## 🔄 Data Lifecycle Management

### Ingestion Workflows

**Healthcare Knowledge Ingestion**:
```python
# Automated document processing pipeline
async def ingest_healthcare_document(file_path: str):
    # 1. Extract and validate content
    content = await document_processor.extract_text(file_path)
    
    # 2. Safety and PHI screening
    safety_check = await content_safety.screen_document(content)
    if safety_check["phi_detected"]:
        raise PHIDetectedError("Document contains PHI")
    
    # 3. Semantic chunking and embedding
    chunks = await chunk_document(content, max_tokens=512)
    embeddings = await embedding_service.embed_documents(chunks)
    
    # 4. MongoDB storage with metadata  
    for chunk, embedding in zip(chunks, embeddings):
        doc = {
            "content": chunk,
            "embedding": embedding,
            "source": file_path,
            "safety_level": safety_check["safety_level"],
            "processed_date": datetime.utcnow()
        }
        await mongodb.healthcare_knowledge.insert_one(doc)
```

### Data Governance Procedures

**PHI Handling Protocol**:
1. **Detection**: Automated PHI scanning on all data ingestion
2. **Classification**: Data tagged with PHI sensitivity levels  
3. **Access Control**: Role-based access with audit logging
4. **Retention**: Automated deletion based on consent expiration

**Quality Assurance**:
- **Data Validation**: Schema enforcement with Pydantic models
- **Content Review**: Healthcare professional validation for medical content
- **Version Control**: Document versioning with approval workflows

### Backup & Recovery Strategies

**PostgreSQL Backup**:
```bash
#!/bin/bash
# Daily automated backups with encryption
pg_dump --host=$POSTGRES_HOST --username=$POSTGRES_USER \
        --format=custom --compress=9 \
        --file=backups/postgres_$(date +%Y%m%d).dump $POSTGRES_DB

# Encrypt backup
gpg --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
    --recipient backup@company.com --encrypt \
    backups/postgres_$(date +%Y%m%d).dump

# Clean old backups (retain 30 days)
find backups/ -name "postgres_*.dump.gpg" -mtime +30 -delete
```

**MongoDB Backup**:
```bash
#!/bin/bash  
# MongoDB dump with vector index preservation
mongodump --host=$MONGO_HOST --port=$MONGO_PORT \
          --username=$MONGO_USER --password=$MONGO_PASS \
          --authenticationDatabase=admin \
          --db=$MONGO_DB \
          --out=backups/mongo_$(date +%Y%m%d)

# Backup vector indexes separately
mongo --eval "
  db.healthcare_knowledge.getIndexes().forEach(function(index) {
    if (index.key && index.key.embedding) {
      print('Vector index config: ' + JSON.stringify(index));
    }
  })
" > backups/mongo_indexes_$(date +%Y%m%d).json
```

**Redis Backup**:
```bash
# Redis persistence configuration (automatic)
# AOF (Append Only File) + RDB snapshots
save: 900 1 300 10 60 10000
appendonly: yes
auto-aof-rewrite-percentage: 100
auto-aof-rewrite-min-size: 64mb
```

**ScyllaDB Backup**:  
```bash
# ScyllaDB snapshot backup
nodetool snapshot chatbot_keyspace
# Snapshots stored in: /var/lib/scylla/data/chatbot_keyspace/

# Full cluster backup script
for node in node1 node2 node3; do
    docker exec scylla-$node nodetool snapshot chatbot_keyspace
    docker cp scylla-$node:/var/lib/scylla/data/chatbot_keyspace/ \
              backups/scylla_$node_$(date +%Y%m%d)/
done
```

---

## 🔄 Data Access Patterns

### Read Patterns by Service

**Go Microservices** (OLTP Patterns):
```go
// High-frequency user lookups
SELECT id, email, subscription_plan, healthcare_role 
FROM users 
WHERE email = $1 AND is_active = true;

// Audit trail queries  
SELECT access_log_id, accessed_data_type, access_timestamp
FROM phi_access_logs 
WHERE user_id = $1 
ORDER BY access_timestamp DESC 
LIMIT 100;
```

**Python AI Services** (Analytics + Vector Patterns):
```python
# Vector similarity search (MongoDB)
pipeline = [
    {
        "$vectorSearch": {
            "index": "healthcare_vector_index",
            "path": "embedding", 
            "queryVector": query_embedding,
            "numCandidates": 100,
            "limit": 10
        }
    },
    {
        "$project": {
            "title": 1, "content": 1, "score": {"$meta": "vectorSearchScore"}
        }
    }
]

# Conversation history retrieval (ScyllaDB)
SELECT actor, text_content, created_at, metadata
FROM conversation_items  
WHERE session_id = ? AND created_at > ?
ORDER BY created_at DESC
LIMIT 50;
```

### Write Patterns by Service

**High-Volume Writes** (ScyllaDB):
- **Conversation Messages**: 1000+ writes/minute during peak hours
- **Analytics Events**: User interaction tracking and metrics

**Transactional Writes** (PostgreSQL):
- **User Registration**: ACID compliance for account creation
- **Billing Events**: Consistent subscription and usage tracking  
- **Audit Logs**: Compliance-required activity logging

**Document Writes** (MongoDB):
- **Knowledge Base Updates**: Medical guideline revisions
- **Cache Storage**: Conversation response caching

---

## 🛠️ Local Development Guide

### Database Setup

**1. Infrastructure Deployment**:
```bash
# Terraform-managed database deployment
make terraform-init
make terraform-apply

# Wait for health checks
make terraform-status
```

**2. Schema Initialization**:
```bash
# PostgreSQL schema and tables
python init_database.py

# Alembic migrations
alembic upgrade head

# MongoDB indexes  
python app/utils/create_mongodb_vector_indexes.py
```

**3. Test Data Seeding**:
```bash
# Healthcare knowledge base
python run_seeding.py

# Validate data loading
python scripts/test_runner.py --database
```

### Connection Testing

**Database Connectivity Validation**:
```bash
# Test all database connections
python tests/system/test_databases.py

# Individual database tests
python -c "
from data_layer.connections.postgres_connection import postgres_manager
from data_layer.connections.mongo_connection import get_mongo_manager  
from data_layer.connections.redis_connection import redis_manager
from data_layer.connections.scylla_connection import ScyllaDBConnection

# Test connections
print('PostgreSQL:', postgres_manager.test_connection())
print('MongoDB:', get_mongo_manager().test_connection())  
print('Redis:', redis_manager.test_connection())
print('ScyllaDB:', ScyllaDBConnection().test_connection())
"
```

---

## 📊 Monitoring & Observability

### Database Health Metrics

**PostgreSQL Monitoring**:
- **Connection Pool**: Active connections, pool exhaustion alerts
- **Query Performance**: Slow query log (>100ms), index usage
- **Storage**: Database size, table growth, vacuum statistics

**MongoDB Monitoring**:
- **Vector Search Performance**: Query latency, index efficiency  
- **Document Growth**: Collection size, index memory usage
- **Replica Set Health**: Primary/secondary status, replication lag

**Redis Monitoring**:
- **Memory Usage**: Peak usage, eviction rate, hit/miss ratio
- **Connection Health**: Client connections, command statistics
- **Persistence**: AOF rewrite frequency, RDB snapshot timing

**ScyllaDB Monitoring**:  
- **Cluster Health**: Node status, token distribution, repair schedules
- **Write Performance**: Throughput, latency percentiles, compaction
- **Storage**: SSTable count, disk usage, garbage collection

### Alerting Thresholds

```yaml
Critical Alerts:
  - PostgreSQL connection failure
  - MongoDB vector index corruption
  - Redis memory exhaustion (>90%)
  - ScyllaDB node failure

Warning Alerts:  
  - Query performance degradation (>2x baseline)
  - Storage usage >85% capacity
  - Replication lag >30 seconds
  - Connection pool usage >80%
```

---

## 🔧 Configuration Management

### Environment-Specific Configs

**Development** (`.env`):
```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatbot_app
POSTGRES_USER=chatbot_user

# MongoDB  
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=chatbot_app
MONGO_USER=root

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# ScyllaDB
SCYLLA_HOSTS=localhost:9042,localhost:9043,localhost:9044
SCYLLA_KEYSPACE=chatbot_keyspace
```

**Production** (Terraform-managed):
```hcl
# Terraform variables for production deployment
variable "postgres_instance_class" { default = "db.r6g.xlarge" }
variable "mongodb_cluster_tier" { default = "M30" }  
variable "redis_node_type" { default = "cache.r6g.large" }
variable "scylla_instance_type" { default = "i3.2xlarge" }
```

### Schema Versioning

**Alembic Migrations** (PostgreSQL):
```python
# Migration versioning strategy
# Format: YYYYMMDD_HHMMSS_description.py
# Example: 20240815_143022_add_healthcare_roles.py

def upgrade():
    op.create_table(
        'healthcare_providers',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id')),
        sa.Column('license_number', sa.String(100), nullable=False),
        sa.Column('specialty', sa.String(100)),
        sa.Column('verified_at', sa.DateTime(timezone=True))
    )
```

**MongoDB Schema Evolution**:
- **Versioned Collections**: healthcare_knowledge_v2, healthcare_knowledge_v3
- **Gradual Migration**: Blue-green deployment with validation
- **Index Migration**: Separate index creation with performance validation

---

## 🚨 Disaster Recovery Procedures

### Recovery Time Objectives (RTO) & Recovery Point Objectives (RPO)

| Database | RTO Target | RPO Target | Recovery Strategy |
|----------|------------|------------|------------------|
| PostgreSQL | < 15 minutes | < 5 minutes | Point-in-time recovery + hot standby |
| MongoDB | < 30 minutes | < 15 minutes | Replica set failover + backup restore |
| Redis | < 5 minutes | < 1 minute | AOF replay + replica promotion |  
| ScyllaDB | < 45 minutes | < 30 minutes | Multi-node cluster + snapshot restore |

### Emergency Recovery Workflow

**Complete System Recovery**:
```bash
#!/bin/bash
# Multi-database emergency recovery script

echo "🚨 Starting emergency recovery..."

# 1. Restore PostgreSQL (primary user data)
pg_restore --host=$POSTGRES_HOST --username=postgres \
           --dbname=chatbot_app --clean --if-exists \
           backups/latest_postgres.dump

# 2. Restore MongoDB (knowledge base)  
mongorestore --host=$MONGO_HOST --authenticationDatabase=admin \
             --drop backups/latest_mongo/

# 3. Restart Redis (cache rebuilt automatically)
docker restart multidb-chatbot-redis

# 4. Restore ScyllaDB (conversation history)
for node in node1 node2 node3; do
    docker exec scylla-$node nodetool refresh chatbot_keyspace conversation_items
done

# 5. Validate all connections
python tests/system/test_databases.py

echo "✅ Emergency recovery completed"
```

---

## 🔍 Troubleshooting Guide

### Common Issues & Solutions

**Vector Search Performance**:
```bash
# Issue: Slow MongoDB vector queries
# Solution: Rebuild vector indexes with optimal configuration  
db.healthcare_knowledge.dropIndex("healthcare_vector_index")
python app/utils/create_mongodb_vector_indexes.py
```

**PostgreSQL Connection Exhaustion**:
```sql
-- Issue: "too many connections" errors
-- Solution: Optimize connection pooling
SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';
ALTER SYSTEM SET max_connections = '200';
SELECT pg_reload_conf();
```

**ScyllaDB Cluster Issues**:
```bash
# Issue: Node appears down
# Solution: Check cluster status and repair
docker exec scylla-node1 nodetool status
docker exec scylla-node1 nodetool repair chatbot_keyspace
```

### Performance Optimization

**Query Optimization Checklist**:
- [ ] PostgreSQL queries use appropriate indexes
- [ ] MongoDB aggregations leverage vector indexes  
- [ ] Redis TTL values optimized for hit ratios
- [ ] ScyllaDB partition keys distribute load evenly

**Storage Optimization**:
- [ ] PostgreSQL VACUUM and ANALYZE scheduled
- [ ] MongoDB compaction running efficiently
- [ ] Redis memory policy prevents OOM
- [ ] ScyllaDB compaction completing successfully