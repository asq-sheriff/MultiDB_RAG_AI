# Codebase Overview — MultiDB Chatbot

> **Audience:** New contributors, reviewers, and hiring managers who want a fast, accurate mental model of the project.  
> **Goal:** Explain structure, responsibilities, key flows, and how to get productive in <60 minutes.

---

## 1) What this project is

A production‑minded **Retrieval‑Augmented Generation (RAG)** chatbot demonstrating a **Composable AI Stack**:

- **Data Plane (Dagster)** — ingest → chunk → embed → vector store (MongoDB Atlas Vector Search)
- **Serving Plane (Ray Serve + FastAPI)** — low‑latency, stateful agent built with **LangGraph**
- **Control Plane (Prefect)** — optional blue/green rollout, validation, and approvals

It also showcases **multi‑database** integration: MongoDB (vectors), PostgreSQL (auth/billing), ScyllaDB (conversation history), Redis (cache/session).

---

## 2) Repo layout (high‑signal)

```
.
├── app/                      # Application source
│   ├── api/                  # FastAPI routes & request/response models
│   ├── services/             # Business logic (ChatbotService, KnowledgeService, Auth/Billing)
│   ├── agents/               # LangGraph graphs, tools, memory
│   ├── data/                 # Data plane glue (loaders, splitters, embedding ops)
│   ├── stores/               # DB adapters (Mongo/Vector, Postgres, Scylla, Redis)
│   ├── config/               # Settings, pydantic models, feature flags
│   └── telemetry/            # Logging/metrics hooks (Langfuse/Loki placeholders)
├── docs/                     # Human docs (this overview, design, diagrams)
│   ├── images/               # Architecture diagrams
│   ├── multidb_rag_chatbot_v3.0.md     # Engineering‑focused system design
│   └── Composable_AI_Stack_Blueprint.pdf
├── tests/                    # Pytest suites (unit/integration)
├── scripts/                  # Dev scripts (codex_publish, setup)
├── docker-compose.yml        # Local dev stack (dbs + app)
├── requirements.txt          # Python dependencies
├── main.py                   # Local entry point / bootstrap
├── Makefile                  # Common dev commands (lint/test/build/release)
├── README.md                 # Employer‑ready project landing page
└── pytest.ini                # Pytest config
```

> If a folder isn’t present yet (e.g., `agents/`), it’s a placeholder in this overview for where that responsibility should live as the code evolves.

---

## 3) How the pieces fit (E2E flow)

### 3.1 Request/response (Serving Plane)

1. **Client** calls FastAPI `POST /chat` with a user message.
2. **Router** invokes `ChatbotService` (app/services/chatbot_service.py).
3. **ChatbotService** calls the **LangGraph agent** with the current state (user msg + short‑term memory).
4. **Agent tools** query the **Vector Store** via `KnowledgeService` (semantic search, optional re‑ranking).
5. Agent composes **final answer**; `ChatbotService` returns JSON.
6. **Conversation event** is appended to **ScyllaDB**; **Redis** may cache hot contexts.

### 3.2 Data ingestion (Data Plane)

1. Dagster **asset** loads sources (PDF/TXT/HTML/Git) via `DocumentLoaders`.
2. Text is chunked (e.g., `RecursiveCharacterTextSplitter`) with overlap.
3. **Embeddings** are generated; vectors and metadata are upserted to **MongoDB Atlas**.
4. Asset **materialization** emits lineage + version; optional sensor notifies serving layer.

### 3.3 Blue/green rollout (Control Plane, optional)

1. Dagster sensor triggers a **Prefect flow** after a new vector asset is built.
2. Prefect deploys a **blue** Ray Serve replica group pointing at the new index.
3. Runs a **validation suite** (golden Q/A) and awaits approval.
4. On approval, traffic shifts to **blue**; **green** is drained and removed.

---

## 4) Key modules & responsibilities

- **`app/services/chatbot_service.py`**  
  Orchestrates a single chat turn: calls agent, routes retrieval to `KnowledgeService`, persists events, enforces rate/quotas.

- **`app/services/knowledge_service.py`**  
  Abstraction over vector retrieval: build query, filters, k, re‑rank; returns documents + metadata for grounding.

- **`app/agents/graph.py`** (LangGraph)  
  Defines the reasoning loop (nodes/edges), tools (search/db), and memory policy (short‑term in process; long‑term in ScyllaDB).

- **`app/stores/vector_mongo.py`**  
  MongoDB Atlas Vector Search client with create/search/update index helpers and schema guards.

- **`app/stores/postgres.py`**  
  Users, auth, billing/subscriptions, and RBAC with SQLAlchemy models and migrations (future‑proof placeholder if not present).

- **`app/stores/scylla.py`**  
  Append‑only conversation timelines; partitioned by `user_id` with time clustering; TTL for cost control.

- **`app/stores/redis.py`**  
  Session cache, rate limits, ephemeral feature flags (low‑latency path only).

- **`app/api/routes.py`**  
  FastAPI endpoints, DTOs (pydantic), and OpenAPI docs.

---

## 5) Configuration & secrets

- **`.env.example`** shows required variables:
  - Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
  - Scylla: `SCYLLA_HOSTS`, `SCYLLA_KEYSPACE`
  - Postgres: `POSTGRES_*` (enable/disable with flag)
  - Mongo: `ENABLE_MONGODB`, `MONGO_*`
  - App: `LOG_LEVEL`, `API_RATE_LIMIT`, `SECRET_KEY`
- Load via **pydantic settings** in `app/config/settings.py` (recommended pattern).  
- Never commit real secrets. Use **Docker secrets**/GitHub **Actions secrets** for CI/CD.

---

## 6) Local development quickstart

```bash
# 1) Python venv
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) Lint & tests
ruff check .
pytest -q

# 3) Bring up services locally (Mongo/Redis/Postgres/Scylla as needed)
docker-compose up -d

# 4) Run API
python main.py   # visit http://localhost:8000/docs
```

Common issues & fixes:
- **Port collisions**: stop old containers (`docker ps` / `docker stop <id>`).  
- **Cannot connect to Mongo/Redis**: check `.env`, container health (`docker compose ps`).  
- **SSL with Atlas**: ensure correct SRV URI and CA bundle if using TLS verification.

---

## 7) Testing strategy

- **Unit tests**: services/tools in isolation; fake DB adapters (mocks).  
- **Integration tests**: ephemeral containers (test‑containers) for Mongo/Redis.  
- **Golden‑set regression**: fixed prompts/answers to catch semantic drift in RAG.  
- **Performance smoke**: p95 latency on `/chat` with small concurrency (locust or artillery).

---

## 8) Production notes (when moving to AWS)

- **Networking**: VPC, private subnets, NAT; security groups per service.  
- **Ray Serve**: autoscaling replicas, sticky‑session or keyed routing for actor affinity.  
- **Dagster**: ECS/EKS task with persistent object store for asset materialization.  
- **Secrets**: SSM Parameter Store or Secrets Manager; no plaintext in env.  
- **Observability**: structured logs, metrics (Prometheus), traces (OTel), prompt/response tracking (Langfuse).  
- **Blue/green**: ALB target groups + Prefect flow; health checks before cutover.

---

## 9) What to learn next (curated pointers)

- **LangGraph**: stateful graphs, interrupt/resume, tool calling best practices.  
- **MongoDB Atlas Vector Search**: schema design for metadata filters; HNSW params.  
- **Ray Serve**: deployment graphs, autoscaling policies, request batching.  
- **Dagster SDAs**: asset sensors, FreshnessPolicy, IO managers for vector artifacts.  
- **Prompt safety & evals**: red teaming, hallucination checks, confidence scoring.  
- **Cost controls**: embedding batching, caching, and TTLs on conversation storage.

---

## 10) Contribution guide (TL;DR)

1. Create a branch: `feat/<slug>` or `fix/<slug>`  
2. Run: `ruff check . && pytest -q`  
3. Open PR with context + screenshots/logs  
4. CI must be green before merge

> See `.github/pull_request_template.md` for the checklist.
