<div align="center">

# MultiDB-AI

### Enterprise-Grade AI Architecture for Production Systems

[![CI](https://github.com/asq-sheriff/MultiDB-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/asq-sheriff/MultiDB-AI/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=white)](https://mongodb.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<br/>

**A production-ready Retrieval-Augmented Generation (RAG) system demonstrating polyglot persistence, two-plane architecture, and enterprise patterns.**

[Quick Start](#-quick-start) · [Architecture](#-architecture) · [Documentation](#-documentation) · [Tech Stack](#-tech-stack)

<br/>

<img src="docs/images/architecture.png" alt="System Architecture" width="800"/>

</div>

---

## The Challenge

Building a chatbot is straightforward. Building one that **scales to millions of users** while maintaining **sub-100ms latency**, **controlling costs**, and enabling **zero-downtime deployments** is an engineering challenge that most implementations fail to address.

This project demonstrates how to architect AI systems for the real world.

---

## Key Features

<table>
<tr>
<td width="50%">

### Polyglot Persistence
Each database chosen for its strengths:
- **MongoDB Atlas** — Vector search & semantic retrieval
- **PostgreSQL** — Users, auth, billing (ACID)
- **ScyllaDB** — High-throughput conversation logs
- **Redis** — Session cache & rate limiting

</td>
<td width="50%">

### Two-Plane Architecture
Clean separation of concerns:
- **Data Plane** — Async ingestion, chunking, embedding
- **Serving Plane** — Real-time inference & API
- Independent scaling & fault isolation
- Zero-downtime model deployments

</td>
</tr>
<tr>
<td width="50%">

### Production-Ready
Enterprise patterns from day one:
- JWT auth with role-based access control
- Usage-based billing & quota enforcement
- Structured logging & health checks
- Connection pooling & query caching

</td>
<td width="50%">

### RAG Pipeline
Complete retrieval-augmented generation:
- Document ingestion & chunking
- Semantic search with re-ranking
- Context-aware response generation
- Conversation memory management

</td>
</tr>
</table>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│                    Web Apps  ·  Mobile  ·  API Clients                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                              API GATEWAY                                     │
│              FastAPI  ·  JWT Auth  ·  Rate Limiting  ·  OpenAPI             │
└───────────────────┬─────────────────────────────────────┬───────────────────┘
                    │                                     │
    ┌───────────────▼───────────────┐     ┌───────────────▼───────────────┐
    │         DATA PLANE            │     │        SERVING PLANE          │
    │  ┌─────────────────────────┐  │     │  ┌─────────────────────────┐  │
    │  │   Document Loaders      │  │     │  │    LangGraph Agent      │  │
    │  │   Text Splitters        │  │     │  │    Stateful Reasoning   │  │
    │  │   Embedding Service     │  │     │  │    Tool Orchestration   │  │
    │  │   Vector Indexing       │  │     │  │    Response Generation  │  │
    │  └─────────────────────────┘  │     │  └─────────────────────────┘  │
    └───────────────┬───────────────┘     └───────────────┬───────────────┘
                    │                                     │
┌───────────────────▼─────────────────────────────────────▼───────────────────┐
│                              DATA LAYER                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  MongoDB    │  │ PostgreSQL  │  │  ScyllaDB   │  │    Redis    │        │
│  │  Vectors    │  │  Users/Auth │  │  Chat Logs  │  │    Cache    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why this design?**
- **Data Plane** handles batch processing independently from real-time serving
- **Serving Plane** scales horizontally without affecting ingestion pipelines
- **Specialized databases** deliver 10x better performance than one-size-fits-all solutions
- **Composable interfaces** allow swapping components without architectural rewrites

---

## Quick Start

```bash
# Clone and start all services
git clone https://github.com/asq-sheriff/MultiDB-AI.git
cd MultiDB-AI
docker-compose up -d

# Get authentication token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}'

# Send your first message
curl -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What databases are best for AI applications?"}'
```

**Development commands:**
```bash
make dev          # Start with hot reload
make test         # Run test suite
make lint         # Format and lint
make build        # Build production image
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API** | FastAPI | Async web framework with automatic OpenAPI docs |
| **Vector Store** | MongoDB Atlas | Semantic search with native vector indexing |
| **Relational DB** | PostgreSQL 15 | Users, auth, billing with ACID guarantees |
| **Time-Series** | ScyllaDB | High-throughput conversation logging (1M+ writes/sec) |
| **Cache** | Redis 7 | Sub-millisecond session and rate limit lookups |
| **Embeddings** | Sentence Transformers | Open-source 768-dim embeddings |
| **Agent Framework** | LangGraph | Stateful reasoning with tool orchestration |
| **Containers** | Docker Compose | Local development environment |
| **CI/CD** | GitHub Actions | Automated testing and quality gates |

---

## Project Structure

```
multidb-ai/
├── app/
│   ├── api/                 # FastAPI routes and schemas
│   │   └── endpoints/       # Auth, chat, billing, search
│   ├── services/            # Business logic layer
│   │   ├── chatbot_service.py
│   │   ├── knowledge_service.py
│   │   ├── embedding_service.py
│   │   └── billing_service.py
│   ├── database/            # Database connections and models
│   └── config.py            # Pydantic settings
├── docs/                    # Technical documentation
├── tests/                   # Unit and integration tests
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Local development stack
├── Makefile                 # Development commands
└── requirements.txt         # Python dependencies
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [System Design](docs/System_Design.md) | Comprehensive architecture deep-dive |
| [Architecture Overview](docs/Architecture_Overview.md) | High-level system design |
| [Codebase Overview](docs/Codebase_Overview.md) | Quick orientation for contributors |
| [Roadmap](docs/Roadmap.md) | Current state and future direction |
| [RAG Fundamentals](docs/RAG_101.md) | Introduction to RAG concepts |

See [docs/README.md](docs/README.md) for the complete documentation index.

---

## Design Decisions

### Why Multiple Databases?

Different data types have fundamentally different access patterns:

| Data Type | Access Pattern | Best Fit | Why Not Alternatives |
|-----------|---------------|----------|---------------------|
| Vectors | Similarity search | MongoDB Atlas | pgvector lacks scale; Pinecone = vendor lock |
| Users/Billing | ACID transactions | PostgreSQL | MongoDB lacks ACID; need complex queries |
| Chat History | Append-only, time-series | ScyllaDB | 10x faster than Cassandra; built for writes |
| Sessions | Sub-ms lookups | Redis | Nothing else matches latency requirements |

### Why Two-Plane Architecture?

| Concern | Single-Plane Problem | Two-Plane Solution |
|---------|---------------------|-------------------|
| Scaling | Ingestion spikes affect serving | Independent scaling |
| Deployments | Model updates risk downtime | Blue-green deployments |
| Failures | One failure affects everything | Fault isolation |
| Costs | Can't optimize separately | Right-size each plane |

---

## Roadmap

**Current (v1.0)** — Foundation
- Multi-database architecture with specialized stores
- JWT authentication with RBAC
- Usage-based billing with quota enforcement
- Complete RAG pipeline
- Docker-based local development

**Next (v1.1)** — Cloud Native
- Terraform infrastructure as code
- Kubernetes deployment manifests
- OpenTelemetry observability
- Automated blue-green deployments

**Future (v2.0)** — Advanced Features
- Multi-agent orchestration
- Long-term conversation memory
- Streaming responses
- A/B testing infrastructure

---

## Contributing

```bash
# Create feature branch
git checkout -b feat/your-feature

# Run quality checks
make test && make lint

# Submit PR with:
# - Clear description of changes
# - Test coverage for new code
# - Documentation updates if needed
```

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built to demonstrate production AI engineering**

[View Documentation](docs/) · [Report Issue](https://github.com/asq-sheriff/MultiDB-AI/issues) · [Connect on LinkedIn](https://www.linkedin.com/in/asheriff)

</div>
