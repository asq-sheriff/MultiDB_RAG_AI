---
title: System Diagrams
owner: Platform Architecture Team
last_updated: 2025-09-01
status: authoritative
---

# System Diagrams

> **Comprehensive visual documentation of system architecture, data flows, and operational processes**

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Microservices Architecture](#microservices-architecture)
3. [Data Architecture](#data-architecture)
4. [Security Architecture](#security-architecture)
5. [AI/ML Pipeline](#aiml-pipeline)
6. [Crisis Intervention Flow](#crisis-intervention-flow)
7. [Deployment Architecture](#deployment-architecture)
8. [Monitoring and Observability](#monitoring-and-observability)

## High-Level Architecture

### System Context Diagram

```mermaid
flowchart TB
    subgraph "External Actors"
        SENIOR[👴 Senior Residents<br/>Primary Users]
        CAREGIVER[👩‍⚕️ Healthcare Staff<br/>Care Coordinators]  
        ADMIN[👨‍💼 System Administrators<br/>IT Operations]
        FAMILY[👨‍👩‍👧‍👦 Family Members<br/>Authorized Caregivers]
        CLINICIAN[👩‍⚕️ Healthcare Providers<br/>Physicians, Nurses]
    end

    subgraph "MultiDB Therapeutic AI Platform"
        PLATFORM[🤖 Therapeutic AI Chatbot<br/>HIPAA-Compliant Conversational AI<br/>Microservices Architecture]
    end

    subgraph "External Systems"
        EHR[🏥 EHR Systems<br/>Epic, Cerner, AllScripts]
        EMERGENCY[🚨 Emergency Services<br/>911, Crisis Hotlines]
        NOTIFICATION[📱 Notification Services<br/>SMS, Email, Push]
        MONITORING[📊 Monitoring Systems<br/>DataDog, New Relic]
        AI_PROVIDERS[🧠 AI Model Providers<br/>HuggingFace, Local Models]
    end

    %% User Interactions
    SENIOR -.->|Therapeutic Conversations| PLATFORM
    CAREGIVER -.->|Care Coordination| PLATFORM
    ADMIN -.->|System Management| PLATFORM
    FAMILY -.->|Care Updates| PLATFORM
    CLINICIAN -.->|Clinical Oversight| PLATFORM
    
    %% External System Integrations
    PLATFORM -.->|PHI Data Exchange| EHR
    PLATFORM -.->|Crisis Escalation| EMERGENCY
    PLATFORM -.->|Care Alerts| NOTIFICATION
    PLATFORM -.->|System Metrics| MONITORING
    PLATFORM -.->|AI Processing| AI_PROVIDERS

    style PLATFORM fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    style SENIOR fill:#fff3e0
    style CAREGIVER fill:#f3e5f5
    style FAMILY fill:#e8f5e8
    style CLINICIAN fill:#fce4ec
    style ADMIN fill:#f1f8e9
```

## Microservices Architecture

### Complete Service Topology

```mermaid
flowchart TB
    subgraph "Client Layer"
        WEB[🌐 Web Interface<br/>React/Next.js<br/>Port: 3000]
        MOBILE[📱 Mobile App<br/>React Native<br/>iOS/Android]
        API_DOCS[📋 API Documentation<br/>OpenAPI/Swagger<br/>Auto-generated]
    end

    subgraph "API Gateway Layer"
        GATEWAY[🚪 API Gateway<br/>Go + Gin<br/>Port: 8090]
    end

    subgraph "Go Microservices Tier"
        AUTH[🔐 Auth/RBAC<br/>Go + PostgreSQL<br/>Port: 8080]
        CONSENT[📝 Consent<br/>Go + PostgreSQL<br/>Port: 8083]
        CHAT_HIST[💬 Chat History<br/>Go + ScyllaDB<br/>Port: 8002]
        AUDIT[📋 Audit Logging<br/>Go + PostgreSQL<br/>Port: 8084]
        BILLING[💳 Billing<br/>Go + PostgreSQL<br/>Port: 8081]
        EMERGENCY[🚨 Emergency Access<br/>Go + PostgreSQL<br/>Port: 8082]
        TASKS[⚙️ Background Tasks<br/>Go + Redis<br/>Port: 8086]
        RELATIONSHIPS[👥 Relationship Mgmt<br/>Go + PostgreSQL<br/>Port: 8087]
        SUBSCRIPTIONS[📄 User Subscriptions<br/>Go + PostgreSQL<br/>Port: 8088]
        SEARCH_GO[🔍 Search Service<br/>Go + MongoDB<br/>Port: 8089]
        CONTENT_SAFETY_GO[🛡️ Content Safety<br/>Go + Redis<br/>Port: 8007]
    end

    subgraph "Python AI Services Tier"
        AI_GATEWAY[🤖 AI Gateway<br/>FastAPI + Python<br/>Port: 8000]
        SEARCH_PY[🔍 Search Service<br/>Python + MongoDB<br/>Port: 8001]
        EMBEDDING[🧠 Embedding Service<br/>BGE + FastAPI<br/>Port: 8005]
        GENERATION[✍️ Generation Service<br/>Qwen + FastAPI<br/>Port: 8006]
    end

    subgraph "Host AI Services (GPU)"
        BGE_HOST[🧠 BGE Host Server<br/>PyTorch + MPS<br/>Port: 8008]
        QWEN_HOST[✍️ Qwen Host Server<br/>PyTorch + MPS<br/>Port: 8007]
    end

    subgraph "Data Layer"
        POSTGRES[(🐘 PostgreSQL 15<br/>HIPAA Schema + pgvector<br/>Port: 5432)]
        MONGODB[(🍃 MongoDB Atlas Local<br/>Knowledge Base + Vector Search<br/>Port: 27017)]
        REDIS[(⚡ Redis 7<br/>Sessions + Cache<br/>Port: 6379)]
        SCYLLADB[(🏛️ ScyllaDB Cluster<br/>Chat History + Analytics<br/>Ports: 9042-9044)]
    end

    %% Client Connections
    WEB --> GATEWAY
    MOBILE --> GATEWAY
    API_DOCS --> GATEWAY

    %% Gateway to Services
    GATEWAY --> AUTH
    GATEWAY --> AI_GATEWAY
    GATEWAY --> CHAT_HIST
    GATEWAY --> CONSENT
    GATEWAY --> AUDIT

    %% Go Service Dependencies
    AUTH --> POSTGRES
    CONSENT --> POSTGRES
    CHAT_HIST --> SCYLLADB
    AUDIT --> POSTGRES
    BILLING --> POSTGRES
    EMERGENCY --> POSTGRES
    TASKS --> REDIS
    RELATIONSHIPS --> POSTGRES
    SUBSCRIPTIONS --> POSTGRES
    SEARCH_GO --> MONGODB
    CONTENT_SAFETY_GO --> REDIS

    %% AI Service Dependencies
    AI_GATEWAY --> SEARCH_PY
    AI_GATEWAY --> EMBEDDING
    AI_GATEWAY --> GENERATION
    AI_GATEWAY --> POSTGRES
    AI_GATEWAY --> REDIS
    
    SEARCH_PY --> MONGODB
    SEARCH_PY --> EMBEDDING
    
    EMBEDDING --> BGE_HOST
    EMBEDDING --> REDIS
    
    GENERATION --> QWEN_HOST
    GENERATION --> REDIS

    %% Styling
    classDef client fill:#e3f2fd,stroke:#1976d2
    classDef gateway fill:#fff3e0,stroke:#f57c00
    classDef go fill:#00ADD8,color:#fff,stroke:#006064
    classDef python fill:#3776ab,color:#fff,stroke:#1565c0
    classDef ai fill:#4caf50,color:#fff,stroke:#2e7d32
    classDef data fill:#f8f8f8,stroke:#333

    class WEB,MOBILE,API_DOCS client
    class GATEWAY gateway
    class AUTH,CONSENT,CHAT_HIST,AUDIT,BILLING,EMERGENCY,TASKS,RELATIONSHIPS,SUBSCRIPTIONS,SEARCH_GO,CONTENT_SAFETY_GO go
    class AI_GATEWAY,SEARCH_PY,EMBEDDING,GENERATION python
    class BGE_HOST,QWEN_HOST ai
    class POSTGRES,MONGODB,REDIS,SCYLLADB data
```

## Data Architecture

### Multi-Database Strategy

```mermaid
erDiagram
    PostgreSQL {
        string purpose "HIPAA-compliant user data"
        string schemas "auth, compliance, app, memory, knowledge"
        string features "ACID, pgvector, audit trails"
        string use_cases "User profiles, consent, audit logs"
        string encryption "AES-256-GCM at rest"
        string compliance "HIPAA Technical Safeguards"
    }
    
    MongoDB {
        string purpose "Healthcare knowledge base"
        string features "Vector search, flexible schema"
        string collections "therapeutic_content, documents"
        string use_cases "RAG knowledge, document storage"
        string encryption "AES-256-GCM at rest"
        string compliance "HIPAA compliant with BAA"
    }
    
    Redis {
        string purpose "Performance caching"
        string features "In-memory, pub/sub, TTL"
        string data_types "Sessions, embeddings, generations"
        string use_cases "Real-time chat, cache layer"
        string encryption "TLS in transit, no PHI cached"
        string compliance "Session management only"
    }
    
    ScyllaDB {
        string purpose "High-volume conversation history"
        string features "Time-series, horizontal scaling"
        string partitioning "By user_id and time"
        string use_cases "Chat logs, analytics"
        string encryption "AES-256-GCM at rest"
        string compliance "HIPAA compliant storage"
    }
    
    PostgreSQL ||--o{ MongoDB : "Reference data sync"
    PostgreSQL ||--o{ Redis : "Cache invalidation"
    MongoDB ||--o{ Redis : "Search result cache"
    ScyllaDB ||--o{ Redis : "Recent conversation cache"
```

### Data Flow Architecture

```mermaid
flowchart LR
    subgraph "Data Ingestion"
        DOCS[📄 Healthcare Documents<br/>PDF, MD, TXT, DOCX]
        PHI_CLEAN[🔍 PHI Removal<br/>De-identification]
        CHUNK[✂️ Semantic Chunking<br/>Medical Context Aware]
        EMBED[🧠 Vectorization<br/>BGE-large-en-v1.5]
        MONGO_STORE[🍃 MongoDB Storage<br/>therapeutic_content]
    end
    
    subgraph "User Data Flow"
        USER_REG[👤 User Registration<br/>Healthcare Roles]
        CONSENT_FLOW[📝 Consent Collection<br/>HIPAA Compliance]
        PROFILE_ENCRYPT[🔒 Profile Encryption<br/>AES-256-GCM]
        PG_STORE[🐘 PostgreSQL Storage<br/>Encrypted User Data]
    end
    
    subgraph "Conversation Flow"
        CHAT_INPUT[💬 Chat Message<br/>User Input]
        SAFETY_ANALYSIS[🛡️ Safety Analysis<br/>PHI + Crisis Detection]
        RAG_PROCESS[🔍 RAG Processing<br/>Knowledge Retrieval]
        AI_GENERATION[🤖 AI Generation<br/>Therapeutic Response]
        CONV_ENCRYPT[🔒 Conversation Encryption<br/>AES-256-GCM]
        SCYLLA_STORE[🏛️ ScyllaDB Storage<br/>Encrypted History]
    end
    
    subgraph "Audit Flow"
        ALL_ACTIONS[📊 All User Actions<br/>System Events]
        AUDIT_ENRICH[📋 Audit Enrichment<br/>Context + Compliance]
        HASH_CHAIN[🔗 Hash Chain<br/>Tamper Protection]
        AUDIT_STORE[🗄️ Audit Storage<br/>Immutable PostgreSQL]
    end
    
    %% Data flow connections
    DOCS --> PHI_CLEAN --> CHUNK --> EMBED --> MONGO_STORE
    USER_REG --> CONSENT_FLOW --> PROFILE_ENCRYPT --> PG_STORE
    CHAT_INPUT --> SAFETY_ANALYSIS --> RAG_PROCESS --> AI_GENERATION --> CONV_ENCRYPT --> SCYLLA_STORE
    ALL_ACTIONS --> AUDIT_ENRICH --> HASH_CHAIN --> AUDIT_STORE
    
    %% Cross-references
    RAG_PROCESS -.-> MONGO_STORE
    AI_GENERATION -.-> PG_STORE
    SAFETY_ANALYSIS -.-> AUDIT_ENRICH
    
    style DOCS fill:#e3f2fd
    style CHAT_INPUT fill:#e8f5e8
    style ALL_ACTIONS fill:#fff3e0
    style AUDIT_STORE fill:#ffebee
```

## Security Architecture

### Zero-Trust Network Model

```mermaid
flowchart TB
    subgraph "External Network"
        INTERNET[🌐 Internet<br/>External Users]
        VPN[🔒 VPN Gateway<br/>Healthcare Staff]
    end
    
    subgraph "DMZ Layer"
        WAF[🛡️ Web Application Firewall<br/>DDoS + Attack Protection]
        LB[⚖️ Load Balancer<br/>TLS Termination]
        API_GW[🚪 API Gateway<br/>Authentication Edge]
        RATE_LIMIT[🚦 Rate Limiting<br/>DoS Protection]
    end
    
    subgraph "Service Mesh Layer"
        ISTIO[🕸️ Istio Service Mesh<br/>mTLS + Policies]
        CIRCUIT_BREAKER[⚡ Circuit Breakers<br/>Fault Isolation]
        RETRY_LOGIC[🔄 Retry Logic<br/>Resilience Patterns]
    end
    
    subgraph "Application Network"
        GO_SERVICES[🐹 Go Microservices<br/>Business Logic]
        AI_SERVICES[🤖 Python AI Services<br/>ML Workloads]
        HOST_AI[🖥️ Host AI Services<br/>GPU Acceleration]
    end
    
    subgraph "Data Network"
        DB_PROXY[🗄️ Database Proxy<br/>Connection Pooling + Security]
        PG_CLUSTER[🐘 PostgreSQL HA<br/>Primary + Replicas]
        MONGO_CLUSTER[🍃 MongoDB Atlas<br/>Managed Service]
        REDIS_CLUSTER[⚡ Redis Cluster<br/>High Availability]
        SCYLLA_CLUSTER[🏛️ ScyllaDB Cluster<br/>Multi-Node]
    end
    
    subgraph "Security Services"
        VAULT[🔐 HashiCorp Vault<br/>Secret Management]
        CERT_MGR[📜 Certificate Manager<br/>TLS Automation]
        RBAC[👥 RBAC Service<br/>Healthcare Roles]
        AUDIT_SVC[📋 Audit Service<br/>Compliance Logging]
    end
    
    subgraph "Monitoring Layer"
        PROMETHEUS[📊 Prometheus<br/>Metrics Collection]
        GRAFANA[📈 Grafana<br/>Dashboards]
        JAEGER[🔍 Jaeger<br/>Distributed Tracing]
        ALERTS[🔔 AlertManager<br/>Incident Response]
    end
    
    %% Network flow
    INTERNET --> WAF
    VPN --> WAF
    WAF --> LB
    LB --> API_GW
    API_GW --> RATE_LIMIT
    RATE_LIMIT --> ISTIO
    
    ISTIO --> CIRCUIT_BREAKER
    CIRCUIT_BREAKER --> RETRY_LOGIC
    RETRY_LOGIC --> GO_SERVICES
    RETRY_LOGIC --> AI_SERVICES
    RETRY_LOGIC --> HOST_AI
    
    GO_SERVICES --> DB_PROXY
    AI_SERVICES --> DB_PROXY
    DB_PROXY --> PG_CLUSTER
    DB_PROXY --> MONGO_CLUSTER
    DB_PROXY --> REDIS_CLUSTER
    DB_PROXY --> SCYLLA_CLUSTER
    
    %% Security integration
    GO_SERVICES -.-> VAULT
    AI_SERVICES -.-> VAULT
    API_GW -.-> RBAC
    ISTIO -.-> CERT_MGR
    
    %% Monitoring integration
    GO_SERVICES -.-> PROMETHEUS
    AI_SERVICES -.-> PROMETHEUS
    PROMETHEUS --> GRAFANA
    PROMETHEUS --> ALERTS
    GO_SERVICES -.-> JAEGER
    AI_SERVICES -.-> JAEGER
    
    %% Audit integration
    GO_SERVICES -.-> AUDIT_SVC
    AI_SERVICES -.-> AUDIT_SVC
    AUDIT_SVC --> PG_CLUSTER
    
    style WAF fill:#ffebee
    style API_GW fill:#fff3e0
    style ISTIO fill:#e8f5e8
    style VAULT fill:#f3e5f5
    style AUDIT_SVC fill:#fff3e0
```

### Authentication and Authorization Flow

```mermaid
sequenceDiagram
    participant U as User (Healthcare Provider)
    participant G as API Gateway
    participant A as Auth/RBAC Service
    participant C as Consent Service
    participant T as Target Service
    participant Au as Audit Service
    
    Note over U,Au: Multi-Factor Authentication Flow
    
    U->>G: Login request (email + password + MFA)
    G->>A: Forward authentication request
    
    A->>A: Validate credentials (Argon2)
    A->>A: Verify TOTP/SMS token
    A->>A: Check device fingerprint
    A->>A: Calculate risk score
    A->>A: Generate JWT tokens
    
    A-->>G: JWT access + refresh tokens
    G-->>U: Authentication successful
    
    Note over U,Au: PHI Access Authorization Flow
    
    U->>G: Request patient data access
    G->>A: Validate JWT token + extract claims
    A-->>G: Valid session + user healthcare role
    
    G->>C: Check patient consent for PHI access
    C->>C: Validate active consent
    C->>C: Check consent scope + purpose
    C->>C: Apply minimum necessary principle
    C-->>G: Consent approved + access scope
    
    G->>T: Forward request with user context
    T->>T: Process with RBAC enforcement
    T->>T: Filter response by role permissions
    T-->>G: Authorized data (role-filtered)
    
    G->>Au: Log PHI access event
    Au->>Au: Create immutable audit record
    Au->>Au: Check for compliance violations
    Au-->>G: Audit logged + compliance validated
    
    G-->>U: Authorized response with PHI
    
    Note over U,Au: Emergency Access Override
    
    alt Emergency Situation
        U->>G: Emergency access request + justification
        G->>A: Validate emergency authority
        A->>A: Grant temporary elevated access
        A->>Au: Log emergency access grant
        Au->>Au: Alert compliance team immediately
        A-->>G: Emergency access token (time-limited)
        G-->>U: Emergency access granted (requires post-review)
    end
```

## AI/ML Pipeline

### Complete RAG Pipeline Architecture

```mermaid
flowchart TD
    subgraph "Input Processing"
        USER_MSG[👴 User Message<br/>Therapeutic Query]
        PHI_DETECT[🔍 PHI Detection<br/>Real-time Scanning]
        CRISIS_DETECT[🚨 Crisis Detection<br/>Multi-modal Analysis]
        CONTEXT_PREP[🧠 Context Preparation<br/>Session + Medical History]
        CONSENT_VALID[✅ Consent Validation<br/>AI Processing Authorization]
    end
    
    subgraph "Knowledge Retrieval"
        QUERY_ANALYSIS[📝 Query Analysis<br/>Medical Intent Recognition]
        EMBED_QUERY[📊 Query Embedding<br/>BGE-large-en-v1.5]
        VECTOR_SEARCH[🔍 Vector Search<br/>MongoDB Atlas Search]
        KEYWORD_SEARCH[🔤 Keyword Search<br/>BM25 + Medical Terms]
        HYBRID_FUSION[🔄 Hybrid Score Fusion<br/>RRF + Weighted Combination]
        CLINICAL_RERANK[🏥 Clinical Re-ranking<br/>Medical Concept Priority]
    end
    
    subgraph "Response Generation"
        CONTEXT_INJECT[💉 Context Injection<br/>Retrieved + Session Context]
        PROMPT_TEMPLATE[📝 Therapeutic Prompt<br/>Senior Care Specialized]
        LLM_GENERATE[🤖 LLM Generation<br/>Qwen2.5-7B-Instruct]
        SAFETY_VALIDATE[🛡️ Safety Validation<br/>Therapeutic Guidelines]
        EMPATHY_ENHANCE[💝 Empathy Enhancement<br/>Emotional Intelligence]
    end
    
    subgraph "Output Processing"
        FINAL_SAFETY[🔒 Final Safety Check<br/>Output PHI Scan]
        CITATION_ADD[📚 Citation Addition<br/>Source Attribution]
        THERAPEUTIC_POLISH[✨ Therapeutic Polish<br/>Senior-Appropriate Language]
        AUDIT_LOG[📋 AI Decision Audit<br/>Model Reasoning + Sources]
        RESPONSE_DELIVER[📤 Response Delivery<br/>To User Interface]
    end
    
    USER_MSG --> PHI_DETECT
    PHI_DETECT --> CRISIS_DETECT
    CRISIS_DETECT --> CONTEXT_PREP
    CONTEXT_PREP --> CONSENT_VALID
    CONSENT_VALID --> QUERY_ANALYSIS
    
    QUERY_ANALYSIS --> EMBED_QUERY
    EMBED_QUERY --> VECTOR_SEARCH
    QUERY_ANALYSIS --> KEYWORD_SEARCH
    VECTOR_SEARCH --> HYBRID_FUSION
    KEYWORD_SEARCH --> HYBRID_FUSION
    HYBRID_FUSION --> CLINICAL_RERANK
    
    CLINICAL_RERANK --> CONTEXT_INJECT
    CONTEXT_PREP --> CONTEXT_INJECT
    CONTEXT_INJECT --> PROMPT_TEMPLATE
    PROMPT_TEMPLATE --> LLM_GENERATE
    LLM_GENERATE --> SAFETY_VALIDATE
    SAFETY_VALIDATE --> EMPATHY_ENHANCE
    
    EMPATHY_ENHANCE --> FINAL_SAFETY
    FINAL_SAFETY --> CITATION_ADD
    CITATION_ADD --> THERAPEUTIC_POLISH
    THERAPEUTIC_POLISH --> AUDIT_LOG
    AUDIT_LOG --> RESPONSE_DELIVER
    
    %% Crisis intervention bypass
    CRISIS_DETECT -.->|Crisis Detected| CRISIS_RESPONSE[🚨 Immediate Crisis Response]
    CRISIS_RESPONSE -.-> RESPONSE_DELIVER
    
    style PHI_DETECT fill:#ffebee
    style CRISIS_DETECT fill:#ffebee
    style CONSENT_VALID fill:#fff3e0
    style LLM_GENERATE fill:#e8f5e8
    style FINAL_SAFETY fill:#ffebee
    style AUDIT_LOG fill:#f3e5f5
    style CRISIS_RESPONSE fill:#d32f2f,color:#fff
```

### AI Model Architecture

```mermaid
flowchart LR
    subgraph "Embedding Pipeline"
        TEXT_INPUT[📝 Text Input]
        TEXT_PREPROCESS[🔧 Text Preprocessing<br/>Medical Term Normalization]
        BGE_MODEL[🧠 BGE-large-en-v1.5<br/>1024-dim Embeddings]
        EMBED_CACHE[⚡ Embedding Cache<br/>Redis TTL: 24h]
        EMBED_OUTPUT[📊 Vector Output<br/>1024-dimensional]
    end
    
    subgraph "Generation Pipeline"
        PROMPT_INPUT[📝 Prompt Input<br/>Therapeutic Template]
        CONTEXT_MERGE[🔄 Context Merging<br/>Retrieved + Session]
        QWEN_MODEL[🤖 Qwen2.5-7B-Instruct<br/>8K Context Window]
        GEN_CACHE[⚡ Generation Cache<br/>Redis TTL: 30min]
        RESPONSE_OUTPUT[💬 Response Output<br/>Therapeutic Text]
    end
    
    subgraph "Safety Pipeline"
        CONTENT_INPUT[📄 Content Input]
        PHI_PATTERNS[🔍 PHI Pattern Matching<br/>HIPAA-defined Patterns]
        ML_CLASSIFIER[🤖 ML Classification<br/>NER + Custom Models]
        CRISIS_KEYWORDS[🚨 Crisis Keywords<br/>Suicide + Self-harm]
        SENTIMENT_ANALYSIS[😊 Sentiment Analysis<br/>Mental Health Focus]
        SAFETY_OUTPUT[🛡️ Safety Decision<br/>Allow/Block/Mask]
    end
    
    %% Pipeline flows
    TEXT_INPUT --> TEXT_PREPROCESS --> BGE_MODEL --> EMBED_CACHE --> EMBED_OUTPUT
    PROMPT_INPUT --> CONTEXT_MERGE --> QWEN_MODEL --> GEN_CACHE --> RESPONSE_OUTPUT
    CONTENT_INPUT --> PHI_PATTERNS --> ML_CLASSIFIER --> CRISIS_KEYWORDS --> SENTIMENT_ANALYSIS --> SAFETY_OUTPUT
    
    %% Cross-pipeline integration
    EMBED_OUTPUT -.-> CONTEXT_MERGE
    SAFETY_OUTPUT -.-> QWEN_MODEL
    SAFETY_OUTPUT -.-> RESPONSE_OUTPUT
    
    style BGE_MODEL fill:#4caf50,color:#fff
    style QWEN_MODEL fill:#4caf50,color:#fff
    style PHI_PATTERNS fill:#ffebee
    style CRISIS_KEYWORDS fill:#ffebee
    style SAFETY_OUTPUT fill:#ffebee
```

## Crisis Intervention Flow

### Emergency Response System

```mermaid
sequenceDiagram
    participant P as Patient
    participant AI as AI Gateway
    participant CS as Content Safety
    participant CD as Crisis Detection
    participant CC as Care Coordination
    participant ES as Emergency Services
    participant A as Audit Service
    
    Note over P,A: Crisis Detection and Intervention Flow
    
    P->>AI: Send message with crisis indicators
    AI->>CS: Analyze message for safety
    CS->>CD: Perform crisis risk assessment
    
    CD->>CD: Multi-modal crisis analysis
    CD->>CD: Calculate aggregate risk score
    
    alt High Crisis Risk (≥0.8)
        CD->>CC: IMMEDIATE: Alert care team
        CD->>ES: Contact emergency services
        CD->>A: Log CRITICAL crisis event
        
        CC->>CC: Locate on-duty care staff
        CC->>CC: Retrieve patient emergency contacts
        CC-->>P: "Help is on the way. You're not alone."
        
        ES->>ES: Validate emergency contact authority
        ES->>ES: Dispatch emergency response
        ES-->>CC: Emergency response dispatched
        
        AI-->>P: Crisis intervention response + resources
        
    else Medium Crisis Risk (0.5-0.8)
        CD->>CC: URGENT: Alert care coordinators
        CD->>A: Log HIGH priority event
        
        CC->>CC: Schedule immediate check-in
        CC-->>P: "Someone will check on you soon."
        
        AI-->>P: Supportive response + crisis resources
        
    else Low Crisis Risk (0.3-0.5)
        CD->>CC: Schedule wellness check
        CD->>A: Log MEDIUM priority event
        
        AI-->>P: Empathetic therapeutic response
        
    else No Crisis Detected (<0.3)
        AI-->>P: Standard therapeutic response
    end
    
    Note over P,A: Post-Crisis Follow-up
    
    CC->>A: Log intervention outcomes
    CC->>P: Follow-up wellness check
    A->>A: Generate crisis intervention report
```

### Crisis Escalation Matrix

```mermaid
flowchart TD
    subgraph "Crisis Assessment"
        MESSAGE[💬 User Message]
        ANALYSIS[🔍 Multi-Modal Analysis<br/>Keywords + Sentiment + ML]
        RISK_SCORE[📊 Risk Score<br/>0.0 - 1.0 Scale]
    end
    
    subgraph "Risk Level 0.9-1.0: IMMINENT DANGER"
        IMMEDIATE[🚨 IMMEDIATE RESPONSE]
        EMERGENCY_911[📞 Emergency Services (911)]
        CARE_ALERT[🏥 Care Team STAT Alert]
        FAMILY_NOTIFY[👨‍👩‍👧‍👦 Emergency Contact Notification]
        CONTINUOUS_MONITOR[👁️ Continuous Monitoring]
    end
    
    subgraph "Risk Level 0.7-0.9: HIGH RISK"
        URGENT[⚠️ URGENT RESPONSE]
        CRISIS_TEAM[🏥 Facility Crisis Team]
        CLINICAL_ASSESS[👩‍⚕️ Clinical Assessment<br/>Within 1 Hour]
        SAFETY_PLAN[📋 Safety Planning]
        FREQUENT_CHECK[📅 Frequent Check-ins]
    end
    
    subgraph "Risk Level 0.5-0.7: MODERATE RISK"
        ELEVATED[📈 ELEVATED CONCERN]
        CARE_COORD[👩‍⚕️ Care Coordinator Alert]
        NEXT_DAY[📅 Next Day Check-in]
        SUPPORT_RESOURCES[📚 Mental Health Resources]
        DOCUMENT_CONCERN[📝 Document in Care Plan]
    end
    
    subgraph "Risk Level 0.3-0.5: LOW RISK"
        SUPPORTIVE[💝 SUPPORTIVE RESPONSE]
        WELLNESS_CHECK[📅 Routine Wellness Check]
        PEER_SUPPORT[👥 Peer Support Groups]
        ACTIVITY_SUGGEST[🎨 Activity Suggestions]
        GENTLE_MONITOR[👁️ Gentle Monitoring]
    end
    
    subgraph "Risk Level 0.0-0.3: MINIMAL RISK"
        STANDARD[💬 STANDARD RESPONSE]
        THERAPEUTIC[🤖 Therapeutic Conversation]
        ROUTINE_CARE[📅 Routine Care Planning]
        WELLNESS_PROMOTE[🌱 Wellness Promotion]
    end
    
    MESSAGE --> ANALYSIS --> RISK_SCORE
    
    RISK_SCORE -->|0.9-1.0| IMMEDIATE
    RISK_SCORE -->|0.7-0.9| URGENT
    RISK_SCORE -->|0.5-0.7| ELEVATED
    RISK_SCORE -->|0.3-0.5| SUPPORTIVE
    RISK_SCORE -->|0.0-0.3| STANDARD
    
    IMMEDIATE --> EMERGENCY_911
    IMMEDIATE --> CARE_ALERT
    IMMEDIATE --> FAMILY_NOTIFY
    IMMEDIATE --> CONTINUOUS_MONITOR
    
    URGENT --> CRISIS_TEAM
    URGENT --> CLINICAL_ASSESS
    URGENT --> SAFETY_PLAN
    URGENT --> FREQUENT_CHECK
    
    ELEVATED --> CARE_COORD
    ELEVATED --> NEXT_DAY
    ELEVATED --> SUPPORT_RESOURCES
    ELEVATED --> DOCUMENT_CONCERN
    
    SUPPORTIVE --> WELLNESS_CHECK
    SUPPORTIVE --> PEER_SUPPORT
    SUPPORTIVE --> ACTIVITY_SUGGEST
    SUPPORTIVE --> GENTLE_MONITOR
    
    STANDARD --> THERAPEUTIC
    STANDARD --> ROUTINE_CARE
    STANDARD --> WELLNESS_PROMOTE
    
    style IMMEDIATE fill:#d32f2f,color:#fff
    style URGENT fill:#ff5722,color:#fff
    style ELEVATED fill:#ff9800,color:#fff
    style SUPPORTIVE fill:#4caf50,color:#fff
    style STANDARD fill:#2196f3,color:#fff
```

## Deployment Architecture

### Local Development Environment

```mermaid
flowchart TB
    subgraph "Developer Machine (macOS/Linux)"
        DEV_ENV[💻 Development Environment<br/>Docker + Python + Go]
        
        subgraph "Infrastructure Services (Containerized)"
            TF_LOCAL[🏗️ Terraform Local<br/>Infrastructure as Code]
            POSTGRES_DEV[🐘 PostgreSQL<br/>localhost:5433]
            MONGO_DEV[🍃 MongoDB Atlas Local<br/>localhost:27018]
            REDIS_DEV[⚡ Redis<br/>localhost:6380]
            SCYLLA_DEV[🏛️ ScyllaDB 3-node<br/>localhost:9045-9047]
        end
        
        subgraph "Python AI Services (Host)"
            AI_GATEWAY_DEV[🤖 AI Gateway<br/>uvicorn --reload :8000]
            SEARCH_DEV[🔍 Search Service<br/>:8001]
            EMBED_DEV[🧠 Embedding Service<br/>:8005]
            GEN_DEV[✍️ Generation Service<br/>:8006]
        end
        
        subgraph "GPU-Accelerated Services (Host)"
            BGE_HOST_DEV[🧠 BGE Host Server<br/>PyTorch MPS :8008]
            QWEN_HOST_DEV[✍️ Qwen Host Server<br/>PyTorch MPS :8007]
        end
        
        subgraph "Go Services (Future/Testing)"
            GO_SERVICES_DEV[🐹 Go Microservices<br/>Development Mode]
        end
    end
    
    TF_LOCAL --> POSTGRES_DEV
    TF_LOCAL --> MONGO_DEV
    TF_LOCAL --> REDIS_DEV
    TF_LOCAL --> SCYLLA_DEV
    
    AI_GATEWAY_DEV --> POSTGRES_DEV
    AI_GATEWAY_DEV --> MONGO_DEV
    AI_GATEWAY_DEV --> REDIS_DEV
    AI_GATEWAY_DEV --> SCYLLA_DEV
    
    SEARCH_DEV --> MONGO_DEV
    EMBED_DEV --> BGE_HOST_DEV
    GEN_DEV --> QWEN_HOST_DEV
    
    AI_GATEWAY_DEV --> SEARCH_DEV
    AI_GATEWAY_DEV --> EMBED_DEV
    AI_GATEWAY_DEV --> GEN_DEV
    
    style DEV_ENV fill:#e3f2fd
    style TF_LOCAL fill:#fff3e0
    style AI_GATEWAY_DEV fill:#3776ab,color:#fff
    style BGE_HOST_DEV fill:#4caf50,color:#fff
    style QWEN_HOST_DEV fill:#4caf50,color:#fff
```

### Production Kubernetes Architecture

```mermaid
flowchart TB
    subgraph "Production Kubernetes Cluster"
        subgraph "Ingress Layer"
            NGINX[🌐 NGINX Ingress<br/>External Traffic]
            CERT_MGR[🔒 cert-manager<br/>TLS Automation]
            WAF_K8S[🛡️ WAF<br/>Security Filtering]
        end
        
        subgraph "Service Mesh"
            ISTIO_CONTROL[🕸️ Istio Control Plane<br/>Service Mesh Management]
            ISTIO_PROXY[🔀 Envoy Sidecars<br/>mTLS + Observability]
        end
        
        subgraph "Application Pods"
            API_PODS[🚪 API Gateway Pods<br/>3 replicas, HPA enabled]
            GO_PODS[🐹 Go Service Pods<br/>Auto-scaling by CPU/Memory]
            AI_PODS[🤖 AI Service Pods<br/>GPU node affinity]
        end
        
        subgraph "GPU Node Pool"
            GPU_NODES[🖥️ GPU Nodes<br/>NVIDIA A100/V100]
            BGE_DEPLOY[🧠 BGE Deployment<br/>Model serving]
            QWEN_DEPLOY[✍️ Qwen Deployment<br/>Model serving]
        end
        
        subgraph "Data Tier"
            PG_OPERATOR[🐘 PostgreSQL Operator<br/>High Availability]
            MONGO_ATLAS[🍃 MongoDB Atlas<br/>Managed Service]
            REDIS_SENTINEL[⚡ Redis Sentinel<br/>HA Configuration]
            SCYLLA_OPERATOR[🏛️ ScyllaDB Operator<br/>Multi-region Cluster]
        end
        
        subgraph "Platform Services"
            VAULT_K8S[🔐 Vault<br/>Secret Management]
            PROMETHEUS_K8S[📊 Prometheus<br/>Metrics Collection]
            GRAFANA_K8S[📈 Grafana<br/>Dashboards]
            JAEGER_K8S[🔍 Jaeger<br/>Distributed Tracing]
        end
    end
    
    NGINX --> ISTIO_CONTROL
    CERT_MGR --> NGINX
    WAF_K8S --> NGINX
    
    ISTIO_CONTROL --> ISTIO_PROXY
    ISTIO_PROXY --> API_PODS
    ISTIO_PROXY --> GO_PODS
    ISTIO_PROXY --> AI_PODS
    
    AI_PODS --> GPU_NODES
    GPU_NODES --> BGE_DEPLOY
    GPU_NODES --> QWEN_DEPLOY
    
    GO_PODS --> PG_OPERATOR
    AI_PODS --> MONGO_ATLAS
    API_PODS --> REDIS_SENTINEL
    AI_PODS --> SCYLLA_OPERATOR
    
    API_PODS -.-> VAULT_K8S
    GO_PODS -.-> VAULT_K8S
    AI_PODS -.-> VAULT_K8S
    
    API_PODS -.-> PROMETHEUS_K8S
    GO_PODS -.-> PROMETHEUS_K8S
    AI_PODS -.-> PROMETHEUS_K8S
    
    style NGINX fill:#e3f2fd
    style ISTIO_CONTROL fill:#e8f5e8
    style API_PODS fill:#fff3e0
    style GO_PODS fill:#00ADD8,color:#fff
    style AI_PODS fill:#3776ab,color:#fff
    style GPU_NODES fill:#4caf50,color:#fff
    style VAULT_K8S fill:#f3e5f5
```

## Monitoring and Observability

### Observability Stack Architecture

```mermaid
flowchart TB
    subgraph "Application Layer"
        GO_APPS[🐹 Go Microservices<br/>Structured Logging]
        PYTHON_APPS[🐍 Python AI Services<br/>Structured Logging]
        AI_MODELS[🤖 AI Models<br/>Performance Metrics]
    end
    
    subgraph "Metrics Collection"
        PROMETHEUS[📊 Prometheus<br/>Metrics Scraping]
        NODE_EXPORTER[🖥️ Node Exporter<br/>System Metrics]
        GPU_EXPORTER[🎮 GPU Exporter<br/>GPU Utilization]
        DB_EXPORTERS[🗄️ Database Exporters<br/>DB Performance]
    end
    
    subgraph "Logging Pipeline"
        FLUENTD[📝 Fluentd<br/>Log Aggregation]
        ELASTICSEARCH[🔍 Elasticsearch<br/>Log Storage + Search]
        KIBANA[📈 Kibana<br/>Log Visualization]
    end
    
    subgraph "Distributed Tracing"
        JAEGER_COLLECTOR[🔍 Jaeger Collector<br/>Trace Ingestion]
        JAEGER_STORAGE[🗄️ Jaeger Storage<br/>Trace Persistence]
        JAEGER_UI[🖥️ Jaeger UI<br/>Trace Visualization]
    end
    
    subgraph "Visualization & Alerting"
        GRAFANA[📈 Grafana<br/>Unified Dashboards]
        ALERTMANAGER[🔔 AlertManager<br/>Alert Routing]
        PAGERDUTY[📟 PagerDuty<br/>Incident Management]
        SLACK[💬 Slack<br/>Team Notifications]
    end
    
    subgraph "Health Monitoring"
        HEALTH_CHECKS[✅ Health Checks<br/>Service Status]
        SYNTHETIC_TESTS[🧪 Synthetic Tests<br/>User Journey Validation]
        SLA_MONITOR[📊 SLA Monitoring<br/>Performance Targets]
    end
    
    %% Data flow
    GO_APPS --> PROMETHEUS
    PYTHON_APPS --> PROMETHEUS
    AI_MODELS --> PROMETHEUS
    
    GO_APPS --> FLUENTD
    PYTHON_APPS --> FLUENTD
    
    GO_APPS --> JAEGER_COLLECTOR
    PYTHON_APPS --> JAEGER_COLLECTOR
    
    NODE_EXPORTER --> PROMETHEUS
    GPU_EXPORTER --> PROMETHEUS
    DB_EXPORTERS --> PROMETHEUS
    
    FLUENTD --> ELASTICSEARCH
    ELASTICSEARCH --> KIBANA
    
    JAEGER_COLLECTOR --> JAEGER_STORAGE
    JAEGER_STORAGE --> JAEGER_UI
    
    PROMETHEUS --> GRAFANA
    ELASTICSEARCH --> GRAFANA
    JAEGER_UI --> GRAFANA
    
    PROMETHEUS --> ALERTMANAGER
    ALERTMANAGER --> PAGERDUTY
    ALERTMANAGER --> SLACK
    
    HEALTH_CHECKS --> GRAFANA
    SYNTHETIC_TESTS --> PROMETHEUS
    SLA_MONITOR --> ALERTMANAGER
    
    style PROMETHEUS fill:#e8f5e8
    style GRAFANA fill:#fff3e0
    style ALERTMANAGER fill:#ffebee
    style JAEGER_COLLECTOR fill:#f3e5f5
    style HEALTH_CHECKS fill:#e3f2fd
```

### Real-Time Dashboards

```mermaid
flowchart LR
    subgraph "Healthcare Operations Dashboard"
        PATIENT_METRICS[👴 Patient Engagement<br/>Active Users, Sessions]
        CRISIS_METRICS[🚨 Crisis Monitoring<br/>Detection Rate, Response Time]
        THERAPEUTIC_METRICS[🏥 Therapeutic Quality<br/>Conversation Quality, Empathy]
        COMPLIANCE_METRICS[📋 HIPAA Compliance<br/>Audit Coverage, Violations]
    end
    
    subgraph "Technical Operations Dashboard"
        SERVICE_HEALTH[🔧 Service Health<br/>Uptime, Response Time]
        AI_PERFORMANCE[🤖 AI Performance<br/>Model Latency, Quality]
        DATABASE_METRICS[🗄️ Database Performance<br/>Query Time, Connections]
        INFRASTRUCTURE_METRICS[🏗️ Infrastructure<br/>CPU, Memory, Storage]
    end
    
    subgraph "Security Dashboard"
        AUTH_METRICS[🔐 Authentication<br/>Login Success, MFA Usage]
        ACCESS_PATTERNS[👥 Access Patterns<br/>PHI Access, Unusual Activity]
        SECURITY_EVENTS[🛡️ Security Events<br/>Threats, Violations]
        AUDIT_SUMMARY[📊 Audit Summary<br/>Log Completeness, Integrity]
    end
    
    subgraph "AI/ML Dashboard"
        MODEL_PERFORMANCE[📊 Model Performance<br/>Accuracy, Drift Detection]
        RAG_METRICS[🔍 RAG Pipeline<br/>Retrieval Quality, Generation]
        SAFETY_METRICS[🛡️ AI Safety<br/>Crisis Detection, PHI Protection]
        TRAINING_METRICS[📚 Model Training<br/>Training Progress, Validation]
    end
    
    style PATIENT_METRICS fill:#e8f5e8
    style CRISIS_METRICS fill:#ffebee
    style COMPLIANCE_METRICS fill:#fff3e0
    style AI_PERFORMANCE fill:#3776ab,color:#fff
    style SECURITY_EVENTS fill:#ffebee
    style MODEL_PERFORMANCE fill:#4caf50,color:#fff
```

---

**Diagram Library Version**: 2.0  
**Mermaid Version**: 10.6+  
**Last Visual Review**: 2025-09-01  
**Maintained By**: Platform Architecture Team + Technical Documentation Team