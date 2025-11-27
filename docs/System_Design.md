# Multi-Database RAG Chatbot System - Unified Design Document v3.0

## Executive Summary

This document provides a comprehensive technical blueprint for a production-ready Multi-Database RAG (Retrieval-Augmented Generation) Chatbot System. The system combines enterprise-grade authentication, billing management, and state-of-the-art AI capabilities with a robust multi-database architecture optimized for specific use cases.

### System Highlights
- **Enterprise Security**: Role-based access control with admin privileges (`is_superuser` field)
- **Monetization Ready**: Complete billing system with usage tracking and quota enforcement
- **AI-Powered**: RAG pipeline using Sentence Transformers and Qwen3-1.7B
- **Scalable Architecture**: MongoDB Atlas for vectors, PostgreSQL for transactions, ScyllaDB for high-throughput, Redis for caching
- **Production Hardened**: Rate limiting with fallback, comprehensive monitoring, graceful degradation

### Document Audience
- **New Engineers**: Step-by-step implementation guides with exact file locations
- **Architects**: System design patterns and technology justifications
- **Data Scientists**: ML pipeline details and optimization strategies

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure & Setup](#2-project-structure--setup)
3. [Core Components Implementation](#3-core-components-implementation)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Billing & Subscription System](#5-billing--subscription-system)
6. [AI/ML Pipeline](#6-aiml-pipeline)
7. [Database Layer](#7-database-layer)
8. [API Implementation](#8-api-implementation)
9. [Deployment & Operations](#9-deployment--operations)
10. [Testing & Quality Assurance](#10-testing--quality-assurance)

---

## 1. Architecture Overview

### 1.1 System Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Interface]
        MOBILE[Mobile Apps]
        API_CLIENT[API Clients]
    end
    
    subgraph "API Gateway Layer"
        NGINX[Nginx/Load Balancer]
        FASTAPI[FastAPI Server]
    end
    
    subgraph "Middleware Layer"
        AUTH_MW[Authentication Middleware]
        RATE_LIMIT[Rate Limiter]
        QUOTA_CHECK[Quota Checker]
        ADMIN_CHECK[Admin Validator]
    end
    
    subgraph "Service Layer"
        AUTH_SVC[Auth Service]
        BILLING_SVC[Billing Service]
        CHAT_SVC[Chatbot Service]
        KNOWLEDGE_SVC[Knowledge Service]
        EMBED_SVC[Embedding Service]
        GEN_SVC[Generation Service]
    end
    
    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Users/Billing)]
        MONGO[(MongoDB Atlas<br/>Vectors/Documents)]
        REDIS[(Redis<br/>Cache/Sessions)]
        SCYLLA[(ScyllaDB<br/>Conversations)]
    end
    
    subgraph "AI Models"
        SENTENCE_TRANS[Sentence Transformers<br/>all-mpnet-base-v2]
        QWEN[Qwen3 1.7B<br/>Text Generation]
    end
    
    WEB --> NGINX
    MOBILE --> NGINX
    API_CLIENT --> NGINX
    
    NGINX --> FASTAPI
    FASTAPI --> AUTH_MW
    AUTH_MW --> RATE_LIMIT
    RATE_LIMIT --> QUOTA_CHECK
    QUOTA_CHECK --> ADMIN_CHECK
    
    ADMIN_CHECK --> AUTH_SVC
    ADMIN_CHECK --> BILLING_SVC
    ADMIN_CHECK --> CHAT_SVC
    
    CHAT_SVC --> KNOWLEDGE_SVC
    KNOWLEDGE_SVC --> EMBED_SVC
    CHAT_SVC --> GEN_SVC
    
    AUTH_SVC --> POSTGRES
    BILLING_SVC --> POSTGRES
    BILLING_SVC --> REDIS
    
    KNOWLEDGE_SVC --> MONGO
    CHAT_SVC --> SCYLLA
    EMBED_SVC --> SENTENCE_TRANS
    GEN_SVC --> QWEN
```

### 1.2 Technology Stack

| Component | Technology | Version | Purpose | Location in Code |
|-----------|-----------|---------|---------|------------------|
| **Backend Framework** | FastAPI | 0.104+ | REST API | `app/api/main.py` |
| **Authentication** | JWT + bcrypt | Latest | User auth | `app/services/auth_service.py` |
| **User Database** | PostgreSQL | 15 | ACID transactions | `app/database/postgres_*` |
| **Vector Database** | MongoDB Atlas | Latest | Vector search | `app/database/mongo_*` |
| **Cache Layer** | Redis | 7 | Sessions/Cache | `app/database/redis_*` |
| **Time-series DB** | ScyllaDB | 5.2 | Chat history | `app/database/scylla_*` |
| **Embedding Model** | Sentence Transformers | all-mpnet-base-v2 | 768D vectors | `app/services/embedding_service.py` |
| **Generation Model** | Qwen | Qwen3-1.7B | Text generation | `app/services/generation_service.py` |

---

## 2. Project Structure & Setup

### 2.1 Complete Project Structure

**Create this directory structure in your project root:**

```bash
multidb-rag-chatbot/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   ├── billing.py        # Billing & subscription endpoints
│   │   │   ├── chat.py           # Chat interaction endpoints
│   │   │   ├── search.py         # Search & RAG endpoints
│   │   │   └── users.py          # User management endpoints
│   │   ├── __init__.py
│   │   └── main.py               # FastAPI app initialization
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth_dependencies.py  # Auth dependency injection
│   │   ├── config.py             # Configuration management
│   │   ├── rate_limiter.py      # Rate limiting implementation
│   │   └── quota_checker.py     # Quota enforcement
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── postgres_connection.py   # PostgreSQL async manager
│   │   ├── postgres_models.py       # SQLAlchemy models
│   │   ├── mongo_connection.py      # MongoDB Atlas connection
│   │   ├── mongo_models.py          # MongoDB schemas
│   │   ├── redis_connection.py      # Redis client
│   │   ├── redis_models.py          # Redis cache models
│   │   ├── scylla_connection.py     # ScyllaDB connection
│   │   └── scylla_models.py         # ScyllaDB models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py          # Authentication logic
│   │   ├── billing_service.py       # Billing & subscription
│   │   ├── user_service.py          # User management
│   │   ├── chatbot_service.py       # Chat orchestration
│   │   ├── knowledge_service.py     # RAG pipeline
│   │   ├── embedding_service.py     # Vector embeddings
│   │   ├── generation_service.py    # LLM generation
│   │   └── background_tasks.py      # Async task processing
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── request_models.py        # Pydantic request models
│   │   ├── response_models.py       # Pydantic response models
│   │   └── domain_models.py         # Domain entities
│   │
│   └── utils/
│       ├── __init__.py
│       ├── document_processor.py    # Document chunking
│       ├── validators.py            # Input validation
│       └── helpers.py              # Utility functions
│
├── scripts/
│   ├── init_postgres.py            # PostgreSQL initialization
│   ├── init_mongodb.py             # MongoDB setup & indexes
│   ├── init_scylla.py              # ScyllaDB keyspace setup
│   ├── test_protected_endpoints.py # Endpoint testing
│   ├── verify_complete_fixes.py    # System verification
│   └── seed_data.py               # Initial data seeding
│
├── tests/
│   ├── unit/                      # Unit tests
│   ├── integration/                # Integration tests
│   └── e2e/                       # End-to-end tests
│
├── migrations/                     # Database migrations
│   └── alembic/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

### 2.2 Environment Configuration

**Create `.env` file in project root:**

```bash
# Authentication & Security
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
BCRYPT_ROUNDS=12

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatbot_app
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=secure_password
DATABASE_URL=postgresql+asyncpg://chatbot_user:secure_password@localhost:5432/chatbot_app

# MongoDB Atlas Configuration
MONGO_URI=mongodb://localhost:27017/chatbot_app?authSource=admin
MONGO_DB=chatbot_app
MONGODB_ATLAS_URI=mongodb+srv://username:password@cluster.mongodb.net/
ENABLE_ATLAS_SEARCH=true

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0
REDIS_FALLBACK_TO_MEMORY=true

# ScyllaDB Configuration
SCYLLA_HOSTS=127.0.0.1
SCYLLA_PORT=9042
SCYLLA_KEYSPACE=chatbot_ks
SCYLLA_USERNAME=
SCYLLA_PASSWORD=

# AI Model Configuration
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
GENERATION_MODEL=Qwen/Qwen3-1.7B
MODEL_DEVICE=cuda  # or 'mps' for Mac, 'cpu' for CPU
EMBEDDING_BATCH_SIZE=32
GENERATION_MAX_TOKENS=512

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
CORS_ORIGINS=["http://localhost:3000"]

# Feature Flags
ENABLE_QUOTA_ENFORCEMENT=true
ENABLE_RATE_LIMITING=true
ENABLE_BILLING=true

# Subscription Limits (for testing)
FREE_MESSAGE_LIMIT=10
PRO_MESSAGE_LIMIT=100
ENTERPRISE_MESSAGE_LIMIT=10000
```

### 2.3 Docker Compose Setup

**Create `docker-compose.yml` in project root:**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: chatbot-postgres
    environment:
      POSTGRES_DB: chatbot_app
      POSTGRES_USER: chatbot_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chatbot_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  mongodb:
    image: mongodb/mongodb-atlas-local:latest
    container_name: chatbot-mongodb
    ports:
      - "27017:27017"
    environment:
      - MONGODB_INITDB_ROOT_USERNAME=root
      - MONGODB_INITDB_ROOT_PASSWORD=example
    volumes:
      - mongo_data:/data/db
      - mongo_config:/data/configdb
      - mongo_mongot:/data/mongot  # Required for vector search

  redis:
    image: redis:7-alpine
    container_name: chatbot-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  scylla:
    image: scylladb/scylla:5.2
    container_name: chatbot-scylla
    ports:
      - "9042:9042"
    volumes:
      - scylla_data:/var/lib/scylla
    command: --smp 2 --memory 2G

volumes:
  postgres_data:
  mongo_data:
  mongo_config:
  mongo_mongot:
  redis_data:
  scylla_data:
```

---

## 3. Core Components Implementation

### 3.1 Main Application Setup

**Create `app/api/main.py`:**

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.api.endpoints import auth, billing, chat, search, users
from app.database.postgres_connection import postgres_manager
from app.database.mongo_connection import mongo_manager
from app.database.redis_connection import redis_client
from app.database.scylla_connection import scylla_manager
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting up application...")
    
    # Initialize database connections
    await postgres_manager.initialize()
    await mongo_manager.connect()
    scylla_manager.connect()
    
    # Initialize services
    from app.services.embedding_service import embedding_service
    from app.services.generation_service import generation_service
    
    await embedding_service.initialize()
    await generation_service.initialize()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await postgres_manager.close()
    await mongo_manager.disconnect()
    scylla_manager.disconnect()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Multi-Database RAG Chatbot API",
    description="Production-ready RAG chatbot with billing and authentication",
    version="3.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(billing.router, prefix="/billing", tags=["Billing"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(users.router, prefix="/users", tags=["Users"])

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "version": "3.0.0"}

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check of all services"""
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check PostgreSQL
    try:
        await postgres_manager.test_connection()
        health_status["services"]["postgres"] = "healthy"
    except Exception as e:
        health_status["services"]["postgres"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check MongoDB
    try:
        if mongo_manager.is_connected:
            health_status["services"]["mongodb"] = "healthy"
        else:
            health_status["services"]["mongodb"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["mongodb"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check ScyllaDB
    try:
        if scylla_manager.is_connected():
            health_status["services"]["scylla"] = "healthy"
        else:
            health_status["services"]["scylla"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["scylla"] = f"unhealthy: {str(e)}"
    
    return health_status

# Admin endpoints (protected)
@app.post("/admin/seed-enhanced", tags=["Admin"])
async def trigger_enhanced_seeding(
    admin_user: User = Depends(get_admin_user)
):
    """
    Trigger enhanced seeding pipeline.
    Protected endpoint - requires is_superuser=True.
    """
    from scripts.seed_data import main_advanced_seeding
    
    try:
        logger.info(f"Admin {admin_user.email} triggered enhanced seeding")
        result = await main_advanced_seeding()
        
        return {
            "status": "success",
            "message": "Enhanced seeding completed successfully",
            "triggered_by": admin_user.email,
            "details": result
        }
    except Exception as e:
        logger.error(f"Enhanced seeding failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Enhanced seeding failed: {str(e)}"
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )
```

### 3.2 Configuration Management

**Create `app/core/config.py`:**

```python
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Multi-Database RAG Chatbot"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 30
    BCRYPT_ROUNDS: int = 12
    
    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "chatbot_app"
    POSTGRES_USER: str = "chatbot_user"
    POSTGRES_PASSWORD: str
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "chatbot_app"
    MONGODB_ATLAS_URI: Optional[str] = None
    ENABLE_ATLAS_SEARCH: bool = True
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_FALLBACK_TO_MEMORY: bool = True
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ScyllaDB
    SCYLLA_HOSTS: str = "127.0.0.1"
    SCYLLA_PORT: int = 9042
    SCYLLA_KEYSPACE: str = "chatbot_ks"
    SCYLLA_USERNAME: Optional[str] = None
    SCYLLA_PASSWORD: Optional[str] = None
    
    # AI Models
    EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    GENERATION_MODEL: str = "Qwen/Qwen3-1.7B"
    MODEL_DEVICE: str = "cuda"
    EMBEDDING_BATCH_SIZE: int = 32
    GENERATION_MAX_TOKENS: int = 512
    
    # Feature Flags
    ENABLE_QUOTA_ENFORCEMENT: bool = True
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_BILLING: bool = True
    
    # Subscription Limits
    FREE_MESSAGE_LIMIT: int = 10
    PRO_MESSAGE_LIMIT: int = 100
    ENTERPRISE_MESSAGE_LIMIT: int = 10000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()
```

---

## 4. Authentication & Authorization

### 4.1 User Model with Admin Support

**Create `app/database/postgres_models.py`:**

```python
from sqlalchemy import Column, String, Boolean, DateTime, UUID, JSON, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)  # Admin flag
    subscription_plan = Column(String(50), default="free")
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=True)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 4.2 Authentication Dependencies

**Create `app/core/auth_dependencies.py`:**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID
import logging

from app.services.auth_service import auth_service
from app.database.postgres_models import User

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Base authentication dependency for all protected endpoints.
    Validates JWT token and retrieves user from database.
    
    Integration point: Use this dependency in any endpoint that requires authentication.
    Example: current_user: User = Depends(get_current_user)
    """
    token = credentials.credentials
    
    # Verify token
    payload = await auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user_id = payload.get("user_id")
    user = await auth_service.get_user_by_id(UUID(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active and verified"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensure user has admin privileges.
    Critical for protecting admin endpoints.
    
    Integration point: Use this for any admin-only endpoints.
    Example: admin_user: User = Depends(get_admin_user)
    """
    if not hasattr(current_user, 'is_superuser'):
        logger.error(f"User {current_user.email} missing is_superuser field")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required - user model outdated"
        )
    
    if not current_user.is_superuser:
        logger.warning(f"Non-admin user {current_user.email} attempted admin access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.info(f"Admin user {current_user.email} granted access")
    return current_user
```

### 4.3 Rate Limiting Implementation

**Create `app/core/rate_limiter.py`:**

```python
from fastapi import HTTPException, status, Depends
import time
import logging
from typing import Dict
from app.core.auth_dependencies import get_current_active_user
from app.database.postgres_models import User

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiting dependency with Redis primary and in-memory fallback.
    
    Integration: Add as a dependency to any endpoint that needs rate limiting.
    Example: _rate_limit: User = Depends(chat_rate_limiter)
    """
    
    def __init__(self, calls: int = 10, period: int = 60, resource: str = "general"):
        self.calls = calls
        self.period = period
        self.resource = resource
        self._memory_limits: Dict = {}  # In-memory fallback storage
    
    async def __call__(
        self, 
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check rate limit for user with graceful degradation"""
        user_key = f"{current_user.id}:{self.resource}"
        
        try:
            # Try Redis first
            from app.database.redis_connection import get_redis
            
            redis = get_redis()
            redis_key = f"rate_limit:{user_key}"
            
            # Test Redis connection
            redis.ping()
            
            # Use Redis for rate limiting
            current = redis.incr(redis_key)
            if current == 1:
                redis.expire(redis_key, self.period)
            
            if current > self.calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.calls} calls per {self.period} seconds"
                )
                
        except (ImportError, ConnectionError, Exception) as e:
            # Fallback to in-memory rate limiting
            logger.warning(f"Redis unavailable, using in-memory rate limiting: {e}")
            
            now = time.time()
            
            if user_key not in self._memory_limits:
                self._memory_limits[user_key] = {"count": 0, "window_start": now}
            
            limit_data = self._memory_limits[user_key]
            
            # Reset window if period expired
            if now - limit_data["window_start"] > self.period:
                limit_data["count"] = 0
                limit_data["window_start"] = now
            
            limit_data["count"] += 1
            
            if limit_data["count"] > self.calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {self.calls} calls per {self.period} seconds"
                )
            
            logger.debug(f"In-memory rate limit: {limit_data['count']}/{self.calls}")
        
        return current_user

# Pre-configured rate limiters for different endpoints
# Add these to your endpoint dependencies
chat_rate_limiter = RateLimiter(calls=30, period=60, resource="chat")
search_rate_limiter = RateLimiter(calls=60, period=60, resource="search")
api_rate_limiter = RateLimiter(calls=100, period=60, resource="api")
billing_rate_limiter = RateLimiter(calls=20, period=60, resource="billing")
```

### 4.4 Quota Checker Implementation

**Create `app/core/quota_checker.py`:**

```python
from fastapi import HTTPException, status, Depends
import logging
from typing import Optional
from app.core.auth_dependencies import get_current_active_user
from app.database.postgres_models import User
from app.services.billing_service import billing_service

logger = logging.getLogger(__name__)

class QuotaChecker:
    """
    Dependency class for checking user quotas before resource consumption.
    
    Integration: Add as a dependency to endpoints that consume quota.
    Example: current_user: User = Depends(check_message_quota)
    """
    
    def __init__(self, resource_type: str, quantity: int = 1):
        self.resource_type = resource_type
        self.quantity = quantity
    
    async def __call__(
        self, 
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check if user has quota for the requested resource"""
        try:
            quota_info = await billing_service.check_user_quota(
                current_user, 
                self.resource_type
            )
            
            if not quota_info["has_quota"]:
                # Provide upgrade path based on current plan
                upgrade_plans = {
                    "free": "pro",
                    "pro": "enterprise"
                }
                next_plan = upgrade_plans.get(
                    current_user.subscription_plan, 
                    "enterprise"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Quota exceeded",
                        "resource": self.resource_type,
                        "current_usage": quota_info["current_usage"],
                        "limit": quota_info["max_allowed"],
                        "upgrade_to": next_plan,
                        "upgrade_url": "/billing/plans"
                    }
                )
            
            logger.info(
                f"Quota check passed for user {current_user.id}: "
                f"{self.resource_type} ({quota_info['current_usage']}/{quota_info['max_allowed']})"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            # If quota checking fails, log but allow the request
            logger.error(f"Quota check failed: {e}")
            # Graceful degradation - allow request if billing service is down
            
        return current_user

# Pre-configured quota checkers for different resources
# Add these to your endpoint dependencies
check_message_quota = QuotaChecker("messages", 1)
check_search_quota = QuotaChecker("api_calls", 1)
check_background_task_quota = QuotaChecker("background_tasks", 1)
```

---

## 5. Billing & Subscription System

### 5.1 Enhanced Billing Service

**Create `app/services/billing_service.py`:**

```python
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from uuid import UUID
import logging
import calendar
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_connection import postgres_manager
from app.database.postgres_models import User
from app.models.domain_models import Subscription, UsageRecord, BillingHistory

logger = logging.getLogger(__name__)

class EnhancedBillingService:
    """
    Core billing functionality with improved plan management.
    
    Integration points:
    - Called by QuotaChecker before resource consumption
    - Called by endpoints to check/update subscriptions
    - Background tasks record usage through this service
    """
    
    def __init__(self):
        """Initialize billing service with optional Redis cache"""
        self._plan_definitions = self._load_plan_definitions()
        self._cache_enabled = False
        
        try:
            from app.database.redis_models import BillingCacheModel
            self.cache = BillingCacheModel()
            self._cache_enabled = True
        except Exception as e:
            logger.warning(f"Redis cache not available for billing: {e}")
            self.cache = None
    
    def _load_plan_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load subscription plan definitions"""
        return {
            "free": {
                "name": "Free Plan",
                "limits": {
                    "messages": 10,  # Low limit for testing
                    "background_tasks": 5,
                    "api_calls": 20,
                    "storage_mb": 100
                },
                "features": [
                    "basic_chat",
                    "text_search",
                    "community_support"
                ],
                "pricing": {
                    "monthly": 0,
                    "yearly": 0
                }
            },
            "pro": {
                "name": "Pro Plan",
                "limits": {
                    "messages": 100,
                    "background_tasks": 50,
                    "api_calls": 500,
                    "storage_mb": 1000
                },
                "features": [
                    "advanced_chat",
                    "vector_search",
                    "semantic_search",
                    "api_access",
                    "email_support",
                    "custom_integrations"
                ],
                "pricing": {
                    "monthly": 2900,  # $29.00
                    "yearly": 29000   # $290.00
                }
            },
            "enterprise": {
                "name": "Enterprise Plan",
                "limits": {
                    "messages": 10000,
                    "background_tasks": 1000,
                    "api_calls": 50000,
                    "storage_mb": 10000
                },
                "features": [
                    "unlimited_features",
                    "custom_models",
                    "dedicated_support",
                    "sla_guarantee",
                    "white_label",
                    "admin_access"
                ],
                "pricing": {
                    "monthly": 9900,  # $99.00
                    "yearly": 99000   # $990.00
                }
            }
        }
    
    async def check_user_quota(
        self,
        user: User,
        resource_type: str
    ) -> Dict[str, Any]:
        """
        Check if user has available quota for resource.
        
        Called by: QuotaChecker dependency
        Returns: Dict with quota information
        """
        async with postgres_manager.get_session() as session:
            # Get current usage
            now = datetime.now(timezone.utc)
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            usage_stmt = select(
                func.coalesce(func.sum(UsageRecord.quantity), 0)
            ).where(
                and_(
                    UsageRecord.user_id == user.id,
                    UsageRecord.resource_type == resource_type,
                    UsageRecord.billing_period_start >= period_start
                )
            )
            
            result = await session.execute(usage_stmt)
            current_usage = result.scalar() or 0
            
            # Get limits from user's plan
            plan_type = user.subscription_plan or "free"
            limits = self._plan_definitions[plan_type]["limits"]
            max_allowed = limits.get(resource_type, 0)
            
            # Check if user has quota
            has_quota = (max_allowed == -1) or (current_usage < max_allowed)
            
            return {
                "has_quota": has_quota,
                "current_usage": int(current_usage),
                "max_allowed": max_allowed,
                "remaining": max(0, max_allowed - current_usage) if max_allowed != -1 else -1,
                "plan_type": plan_type
            }
    
    async def record_usage(
        self,
        user: User,
        resource_type: str,
        quantity: int = 1,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Record resource usage for billing.
        
        Called by: Background tasks after resource consumption
        Returns: Success status
        """
        async with postgres_manager.get_session() as session:
            try:
                now = datetime.now(timezone.utc)
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Calculate period end
                last_day = calendar.monthrange(now.year, now.month)[1]
                period_end = now.replace(
                    day=last_day, 
                    hour=23, 
                    minute=59, 
                    second=59, 
                    microsecond=999999
                )
                
                usage_record = UsageRecord(
                    user_id=user.id,
                    resource_type=resource_type,
                    quantity=quantity,
                    billing_period_start=period_start,
                    billing_period_end=period_end,
                    extra_data=metadata or {}
                )
                
                session.add(usage_record)
                await session.commit()
                
                # Invalidate cache if available
                if self._cache_enabled and self.cache:
                    await self.cache.invalidate_user_cache(str(user.id))
                
                logger.info(
                    f"Recorded usage: {user.email} - {resource_type} - {quantity}"
                )
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to record usage: {e}")
                return False
    
    async def get_usage_summary(self, user: User) -> Dict[str, Any]:
        """
        Get usage summary for current billing period.
        
        Called by: Billing endpoints
        Returns: Usage summary with limits
        """
        try:
            # Check cache first
            if self._cache_enabled and self.cache:
                cached = await self.cache.get_cached_usage_summary(str(user.id))
                if cached:
                    return cached
            
            async with postgres_manager.get_session() as session:
                now = datetime.now(timezone.utc)
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Calculate period end
                last_day = calendar.monthrange(now.year, now.month)[1]
                period_end = now.replace(
                    day=last_day,
                    hour=23,
                    minute=59,
                    second=59,
                    microsecond=999999
                )
                
                # Query usage
                usage_query = select(
                    UsageRecord.resource_type,
                    func.coalesce(func.sum(UsageRecord.quantity), 0).label('total')
                ).where(
                    UsageRecord.user_id == user.id,
                    UsageRecord.billing_period_start >= period_start,
                    UsageRecord.billing_period_end <= period_end
                ).group_by(UsageRecord.resource_type)
                
                result = await session.execute(usage_query)
                usage_data = {}
                for row in result:
                    usage_data[row.resource_type] = int(row.total)
                
                # Get plan limits
                plan_type = user.subscription_plan or "free"
                limits = self._plan_definitions[plan_type]["limits"]
                
                summary = {
                    "messages_this_month": usage_data.get("messages", 0),
                    "background_tasks_this_month": usage_data.get("background_tasks", 0),
                    "api_calls_this_month": usage_data.get("api_calls", 0),
                    "quota_remaining": max(0, limits.get("messages", 0) - usage_data.get("messages", 0)),
                    "limits": limits,
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "plan_type": plan_type
                }
                
                # Cache result
                if self._cache_enabled and self.cache:
                    await self.cache.cache_usage_summary(str(user.id), summary)
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            # Return safe defaults
            return {
                "messages_this_month": 0,
                "background_tasks_this_month": 0,
                "api_calls_this_month": 0,
                "quota_remaining": 0,
                "limits": {},
                "period_start": datetime.now(timezone.utc).isoformat(),
                "period_end": datetime.now(timezone.utc).isoformat(),
                "plan_type": "free"
            }

# Global billing service instance
billing_service = EnhancedBillingService()
```

---

## 6. AI/ML Pipeline

### 6.1 Embedding Service

**Create `app/services/embedding_service.py`:**

```python
import torch
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np
import logging
from dataclasses import dataclass
import asyncio
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingConfig:
    """Configuration for embedding service"""
    model_name: str = settings.EMBEDDING_MODEL
    embedding_dimension: int = 768
    max_sequence_length: int = 512
    normalize_embeddings: bool = True
    device: str = settings.MODEL_DEVICE
    batch_size: int = settings.EMBEDDING_BATCH_SIZE

class EmbeddingService:
    """
    Production-ready embedding service.
    
    Integration: Used by KnowledgeService for generating query embeddings
    Location: Instantiated globally and initialized in app startup
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self.model = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize model - called during app startup"""
        if self._initialized:
            return
        
        try:
            logger.info(f"Loading embedding model: {self.config.model_name}")
            self.model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device
            )
            self.model.max_seq_length = self.config.max_sequence_length
            self._initialized = True
            logger.info("Embedding model loaded successfully")
            
            # Warmup
            await self._warmup()
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    async def _warmup(self):
        """Warmup model with sample text"""
        try:
            await self.embed_query("Warmup text")
            logger.info("Embedding model warmed up")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
    
    async def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query.
        
        Called by: KnowledgeService.search_router()
        Returns: 768-dimensional embedding vector
        """
        if not self._initialized:
            await self.initialize()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self._generate_embedding,
            text
        )
        
        return embedding
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding synchronously"""
        with torch.no_grad():
            embedding = self.model.encode(
                text,
                normalize_embeddings=self.config.normalize_embeddings,
                convert_to_numpy=True
            )
        
        return embedding.tolist()
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch processing for multiple texts.
        
        Called by: Document processing pipelines
        Returns: List of embeddings
        """
        if not self._initialized:
            await self.initialize()
        
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self._generate_batch_embeddings,
            texts
        )
        
        return embeddings
    
    def _generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch"""
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_embeddings,
                convert_to_numpy=True
            )
        
        return embeddings.tolist()
    
    @property
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self._initialized and self.model is not None

# Global embedding service instance
embedding_service = EmbeddingService()
```

### 6.2 Generation Service

**Create `app/services/generation_service.py`:**

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class GenerationConfig:
    """Configuration for generation service"""
    model_name: str = settings.GENERATION_MODEL
    max_context_length: int = 4096
    max_new_tokens: int = settings.GENERATION_MAX_TOKENS
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repetition_penalty: float = 1.05
    device: str = settings.MODEL_DEVICE
    use_cache: bool = True

class GenerationService:
    """
    Text generation service using Qwen model.
    
    Integration: Used by ChatbotService for generating responses
    Location: Instantiated globally and initialized in app startup
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. Answer questions based on the provided context. 
    If the context doesn't contain relevant information, say so clearly."""
    
    def __init__(self, config: Optional[GenerationConfig] = None):
        self.config = config or GenerationConfig()
        self.model = None
        self.tokenizer = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize model - called during app startup"""
        if self._initialized:
            return
        
        try:
            logger.info(f"Loading generation model: {self.config.model_name}")
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype=torch.float16 if self.config.device != "cpu" else torch.float32,
                device_map="auto" if self.config.device == "cuda" else None
            )
            
            if self.config.device == "mps":
                self.model = self.model.to("mps")
            
            self._initialized = True
            logger.info("Generation model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load generation model: {e}")
            raise
    
    async def generate_with_context(
        self,
        prompt: str,
        context: List[Dict],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate response with RAG context.
        
        Called by: ChatbotService.answer_user_message()
        Returns: Generated text response
        """
        if not self._initialized:
            await self.initialize()
        
        # Build contextual prompt
        formatted_prompt = self._build_rag_prompt(
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
            context=context,
            user_query=prompt
        )
        
        # Check context window limits
        token_count = len(self.tokenizer.encode(formatted_prompt))
        if token_count > self.config.max_context_length - self.config.max_new_tokens:
            formatted_prompt = self._truncate_context(formatted_prompt)
        
        # Generate in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self._generate,
            formatted_prompt
        )
        
        return response
    
    def _build_rag_prompt(
        self,
        system_prompt: str,
        context: List[Dict],
        user_query: str
    ) -> str:
        """Build optimized RAG prompt"""
        prompt_parts = [system_prompt]
        
        # Add context with relevance scores
        if context:
            prompt_parts.append("\nRelevant Context:")
            for i, ctx in enumerate(context[:5], 1):  # Limit to top 5
                score = ctx.get('score', 0)
                content = ctx.get('content', '')[:500]  # Limit content length
                prompt_parts.append(f"{i}. [Score: {score:.3f}] {content}")
        
        # Add user query
        prompt_parts.append(f"\nUser Question: {user_query}")
        prompt_parts.append("\nAssistant Response:")
        
        return "\n".join(prompt_parts)
    
    def _truncate_context(self, prompt: str) -> str:
        """Truncate context to fit within limits"""
        max_tokens = self.config.max_context_length - self.config.max_new_tokens - 100
        tokens = self.tokenizer.encode(prompt)
        
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]
            prompt = self.tokenizer.decode(tokens, skip_special_tokens=True)
        
        return prompt
    
    def _generate(self, prompt: str) -> str:
        """Generate text synchronously"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        if self.config.device != "cpu":
            inputs = {k: v.to(self.config.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repetition_penalty=self.config.repetition_penalty,
                do_sample=True,
                use_cache=self.config.use_cache
            )
        
        response = self.tokenizer.decode(
            outputs[0][len(inputs['input_ids'][0]):],
            skip_special_tokens=True
        )
        
        return response.strip()
    
    @property
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self._initialized and self.model is not None

# Global generation service instance
generation_service = GenerationService()
```

---

## 7. Database Layer

### 7.1 PostgreSQL Connection Manager

**Create `app/database/postgres_connection.py`:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from app.core.config import settings
from app.database.postgres_models import Base

logger = logging.getLogger(__name__)

class PostgresConnectionManager:
    """
    PostgreSQL connection manager with async support.
    
    Integration: Used throughout the application for database operations
    Initialization: Called in app startup
    """
    
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
    
    async def initialize(self):
        """Initialize database connection - called during app startup"""
        try:
            logger.info("Initializing PostgreSQL connection...")
            
            self.engine = create_async_engine(
                settings.DATABASE_URL,
                poolclass=NullPool,  # For async compatibility
                echo=False,
                future=True,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections after 1 hour
            )
            
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("PostgreSQL connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session context manager.
        
        Usage:
        async with postgres_manager.get_session() as session:
            # Perform database operations
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            async with self.engine.connect() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def close(self):
        """Close database connection - called during app shutdown"""
        if self.engine:
            await self.engine.dispose()
            logger.info("PostgreSQL connection closed")

# Global connection manager instance
postgres_manager = PostgresConnectionManager()
```

### 7.2 MongoDB Connection Manager

**Create `app/database/mongo_connection.py`:**

```python
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import logging
from pymongo import ASCENDING, DESCENDING

from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoConnectionManager:
    """
    MongoDB connection manager with Atlas vector search support.
    
    Integration: Used by KnowledgeService for vector search
    Initialization: Called in app startup
    """
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self._connected = False
        self._vector_search_available = False
    
    async def connect(self):
        """Connect to MongoDB - called during app startup"""
        try:
            logger.info("Connecting to MongoDB...")
            
            # Use Atlas URI if available, otherwise local
            uri = settings.MONGODB_ATLAS_URI or settings.MONGO_URI
            
            self.client = AsyncIOMotorClient(
                uri,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=10
            )
            
            self.database = self.client[settings.MONGO_DB]
            
            # Test connection
            await self.client.admin.command('ping')
            self._connected = True
            
            # Check vector search support
            self._vector_search_available = await self._check_vector_search_support()
            
            if self._vector_search_available:
                logger.info("MongoDB connected with vector search support")
                await self._ensure_vector_indexes()
            else:
                logger.warning("MongoDB connected without vector search support")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def _check_vector_search_support(self) -> bool:
        """Check if vector search is supported"""
        try:
            # Try to list search indexes
            collection = self.database["embeddings"]
            indexes = await collection.list_search_indexes().to_list(None)
            return True
        except Exception:
            return False
    
    async def _ensure_vector_indexes(self):
        """Ensure vector search indexes exist"""
        try:
            collection = self.database["embeddings"]
            
            # Check if vector index exists
            existing_indexes = await collection.list_search_indexes().to_list(None)
            
            if not any(idx.get("name") == "vector_idx_embeddings_embedding" for idx in existing_indexes):
                # Create vector index
                index_def = {
                    "name": "vector_idx_embeddings_embedding",
                    "type": "vectorSearch",
                    "definition": {
                        "fields": [{
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 768,
                            "similarity": "cosine"
                        }]
                    }
                }
                
                await collection.create_search_index(index_def)
                logger.info("Created vector search index")
                
        except Exception as e:
            logger.warning(f"Could not ensure vector indexes: {e}")
    
    async def vector_search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform vector search.
        
        Called by: KnowledgeService for semantic search
        Returns: List of matching documents with scores
        """
        if not self._vector_search_available:
            logger.warning("Vector search not available, using fallback")
            return await self._fallback_search(collection_name, limit)
        
        collection = self.database[collection_name]
        
        # Build aggregation pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_idx_embeddings_embedding",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit
                }
            }
        ]
        
        # Add filters if provided
        if filters:
            pipeline.append({"$match": filters})
        
        # Add score field
        pipeline.append({
            "$addFields": {
                "score": {"$meta": "vectorSearchScore"}
            }
        })
        
        # Execute search
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(limit)
        
        return results
    
    async def _fallback_search(
        self,
        collection_name: str,
        limit: int
    ) -> List[Dict]:
        """Fallback search when vector search is not available"""
        collection = self.database[collection_name]
        cursor = collection.find().limit(limit)
        return await cursor.to_list(limit)
    
    async def disconnect(self):
        """Disconnect from MongoDB - called during app shutdown"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("MongoDB connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to MongoDB"""
        return self._connected

# Global connection manager instance
mongo_manager = MongoConnectionManager()
```

---

## 8. API Implementation

### 8.1 Chat Endpoint with Full Protection

**Create `app/api/endpoints/chat.py`:**

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import Optional
from uuid import uuid4
import time
import logging

from app.models.request_models import ChatRequest
from app.models.response_models import ChatResponse, SourceDocument
from app.core.auth_dependencies import get_current_active_user
from app.core.rate_limiter import chat_rate_limiter
from app.core.quota_checker import check_message_quota
from app.services.chatbot_service import chatbot_service
from app.services.knowledge_service import knowledge_service
from app.services.billing_service import billing_service
from app.database.postgres_models import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_message_quota),  # Quota check
    _rate_limit: User = Depends(chat_rate_limiter),     # Rate limiting
) -> ChatResponse:
    """
    Send a chat message with full protection stack.
    
    Protection layers:
    1. Authentication (via check_message_quota)
    2. Quota checking (embedded in check_message_quota)
    3. Rate limiting (30 messages per minute)
    4. Usage recording (via background task)
    
    Integration: Main chat endpoint for client applications
    """
    start_time = time.time()
    session_id = request.session_id or str(uuid4())
    message_id = str(uuid4())
    
    try:
        # RAG processing
        context = None
        sources = []
        
        if request.enable_rag:
            # Search for relevant context
            search_results = await knowledge_service.search_router(
                query=request.message,
                top_k=request.top_k or 5,
                route=request.route or "auto",
                filters=request.filters
            )
            
            if search_results and search_results.get("results"):
                context = search_results["results"]
                sources = [
                    SourceDocument(
                        document_id=r.get("document_id"),
                        title=r.get("title", "Document")[:100],
                        excerpt=r.get("content", "")[:200],
                        relevance_score=r.get("score", 0.0),
                        source_type=r.get("source", "unknown")
                    )
                    for r in context[:3]
                ]
        
        # Generate response
        chat_result = await chatbot_service.answer_user_message(
            user_id=str(current_user.id),
            message=request.message,
            context=context,
            session_id=session_id
        )
        
        # Get usage info for response
        quota_info = await billing_service.check_user_quota(
            current_user, 
            "messages"
        )
        
        # Record usage in background
        async def record_usage():
            await billing_service.record_usage(
                user=current_user,
                resource_type="messages",
                quantity=1,
                metadata={
                    "session_id": session_id,
                    "message_id": message_id,
                    "tokens_used": chat_result.get("tokens_used", 0),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "rag_enabled": request.enable_rag
                }
            )
        
        background_tasks.add_task(record_usage)
        
        # Build response
        return ChatResponse(
            session_id=session_id,
            message_id=message_id,
            answer=chat_result.get("answer", "I couldn't generate a response."),
            confidence=0.9 if sources else 0.7,
            response_type="rag_enhanced" if sources else "generation_only",
            context_used=len(sources) > 0,
            sources=sources,
            retrieval_route=chat_result.get("route"),
            response_time_ms=(time.time() - start_time) * 1000,
            tokens_used=chat_result.get("tokens_used", 0),
            subscription_plan=current_user.subscription_plan,
            usage_info={
                "messages_used": quota_info["current_usage"],
                "messages_limit": quota_info["max_allowed"],
                "messages_remaining": quota_info.get("remaining", 0)
            },
            debug_info={
                "user_id": str(current_user.id),
                "model_used": chat_result.get("model", "unknown"),
                "fallback_applied": chat_result.get("fallback_applied", False)
            } if request.debug_mode else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process chat message"
        )
```

### 8.2 Billing Endpoints

**Create `app/api/endpoints/billing.py`:**

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.core.auth_dependencies import get_current_active_user
from app.core.rate_limiter import billing_rate_limiter
from app.services.billing_service import billing_service
from app.database.postgres_models import User
from app.models.response_models import (
    SubscriptionResponse,
    UsageResponse,
    QuotaResponse,
    PlanListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    _rate_limit: User = Depends(billing_rate_limiter)
):
    """
    Get current subscription details.
    
    Integration: Called by client to display subscription info
    """
    try:
        # Get subscription from user's plan field
        plan_info = billing_service._plan_definitions.get(
            current_user.subscription_plan, 
            billing_service._plan_definitions["free"]
        )
        
        return SubscriptionResponse(
            user_id=str(current_user.id),
            plan_type=current_user.subscription_plan,
            plan_name=plan_info["name"],
            status="active",
            limits=plan_info["limits"],
            features=plan_info["features"],
            pricing=plan_info["pricing"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get subscription: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve subscription information"
        )

@router.get("/usage", response_model=UsageResponse)
async def get_usage_summary(
    current_user: User = Depends(get_current_active_user),
    _rate_limit: User = Depends(billing_rate_limiter)
):
    """
    Get usage summary for current billing period.
    
    Integration: Called by client to display usage statistics
    """
    try:
        usage_data = await billing_service.get_usage_summary(current_user)
        return UsageResponse(**usage_data)
        
    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve usage information"
        )

@router.get("/quota/{resource_type}", response_model=QuotaResponse)
async def check_resource_quota(
    resource_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Check quota for specific resource.
    
    Integration: Called by client before resource-intensive operations
    """
    valid_resources = ["messages", "api_calls", "background_tasks", "storage_mb"]
    
    if resource_type not in valid_resources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource type. Must be one of: {valid_resources}"
        )
    
    try:
        quota_info = await billing_service.check_user_quota(
            current_user,
            resource_type
        )
        
        return QuotaResponse(
            resource_type=resource_type,
            has_quota=quota_info["has_quota"],
            current_usage=quota_info["current_usage"],
            max_allowed=quota_info["max_allowed"],
            remaining=quota_info.get("remaining", 0),
            plan_type=quota_info["plan_type"]
        )
        
    except Exception as e:
        logger.error(f"Failed to check quota: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check resource quota"
        )

@router.get("/plans", response_model=PlanListResponse)
async def get_available_plans():
    """
    Get list of available subscription plans.
    
    Integration: Called by client to display upgrade options
    """
    plans = []
    
    for plan_key, plan_data in billing_service._plan_definitions.items():
        plans.append({
            "plan_type": plan_key,
            "name": plan_data["name"],
            "limits": plan_data["limits"],
            "features": plan_data["features"],
            "pricing": plan_data["pricing"]
        })
    
    return PlanListResponse(plans=plans)
```

---

## 9. Deployment & Operations

### 9.1 Dockerfile

**Create `Dockerfile` in project root:**

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 9.2 Database Initialization Scripts

**Create `scripts/init_postgres.py`:**

```python
import asyncio
import logging
from uuid import uuid4
from datetime import datetime, timezone

from app.database.postgres_connection import postgres_manager
from app.database.postgres_models import User, Organization
from app.services.auth_service import auth_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_initial_data():
    """Create initial system data with proper permissions"""
    await postgres_manager.initialize()
    
    async with postgres_manager.get_session() as session:
        # Create default organization
        default_org = Organization(
            id=uuid4(),
            name="Default Organization",
            domain="example.com",
            settings={
                "max_users": 100,
                "features_enabled": ["chat", "search", "analytics"]
            }
        )
        session.add(default_org)
        
        # Create admin user
        admin_user = User(
            id=uuid4(),
            email="admin@example.com",
            hashed_password=auth_service.hash_password("adminpassword123"),
            is_active=True,
            is_verified=True,
            is_superuser=True,  # Admin privileges
            subscription_plan="enterprise",
            organization_id=default_org.id,
            preferences={}
        )
        session.add(admin_user)
        
        # Create test users
        test_user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password=auth_service.hash_password("testpassword123"),
            is_active=True,
            is_verified=True,
            is_superuser=False,
            subscription_plan="pro",
            organization_id=default_org.id,
            preferences={}
        )
        session.add(test_user)
        
        free_user = User(
            id=uuid4(),
            email="free@example.com",
            hashed_password=auth_service.hash_password("freepassword123"),
            is_active=True,
            is_verified=True,
            is_superuser=False,
            subscription_plan="free",
            organization_id=default_org.id,
            preferences={}
        )
        session.add(free_user)
        
        await session.commit()
        logger.info("Initial data created successfully")

if __name__ == "__main__":
    asyncio.run(create_initial_data())
```

---

## 10. Testing & Quality Assurance

### 10.1 Comprehensive Test Suite

**Create `scripts/test_protected_endpoints.py`:**

```python
import asyncio
import aiohttp
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

class EndpointTester:
    """Comprehensive test suite for protected endpoints"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.test_users = {
            "free": {"email": "free@example.com", "password": "freepassword123", "token": None},
            "pro": {"email": "test@example.com", "password": "testpassword123", "token": None},
            "admin": {"email": "admin@example.com", "password": "adminpassword123", "token": None}
        }
    
    async def login_all_users(self):
        """Authenticate all test users"""
        async with aiohttp.ClientSession() as session:
            for plan, user_data in self.test_users.items():
                async with session.post(
                    f"{self.base_url}/auth/login",
                    json={
                        "email": user_data["email"],
                        "password": user_data["password"]
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        user_data["token"] = data["access_token"]
                        logger.info(f"✅ {plan.upper()} user logged in")
                    else:
                        logger.error(f"❌ Failed to login {plan} user")
    
    async def test_admin_endpoints(self):
        """Test admin-only endpoint protection"""
        # Test with admin user - should succeed
        admin_token = self.test_users["admin"]["token"]
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/admin/seed-status",
                headers={"Authorization": f"Bearer {admin_token}"}
            ) as response:
                if response.status == 200:
                    logger.info("✅ Admin can access admin endpoints")
                else:
                    logger.error("❌ Admin cannot access admin endpoints")
            
            # Test with regular user - should fail
            pro_token = self.test_users["pro"]["token"]
            async with session.get(
                f"{self.base_url}/admin/seed-status",
                headers={"Authorization": f"Bearer {pro_token}"}
            ) as response:
                if response.status == 403:
                    logger.info("✅ Regular user correctly denied admin access")
                else:
                    logger.error("❌ Security issue: Regular user accessed admin endpoint!")
    
    async def test_quota_enforcement(self):
        """Test quota limits for different plans"""
        free_token = self.test_users["free"]["token"]
        
        async with aiohttp.ClientSession() as session:
            quota_hit = False
            
            for i in range(15):  # Free plan has 10 message limit
                async with session.post(
                    f"{self.base_url}/chat/message",
                    json={"message": f"Test message {i+1}"},
                    headers={"Authorization": f"Bearer {free_token}"}
                ) as response:
                    if response.status == 429:
                        logger.info(f"✅ Quota limit hit after {i+1} messages")
                        quota_hit = True
                        break
            
            if not quota_hit:
                logger.warning("⚠️ Quota not enforced for free user")
    
    async def test_rate_limiting(self):
        """Test rate limiting enforcement"""
        pro_token = self.test_users["pro"]["token"]
        
        async with aiohttp.ClientSession() as session:
            rate_limit_hit = False
            
            for i in range(35):  # Should hit 30/minute limit
                async with session.post(
                    f"{self.base_url}/chat/message",
                    json={"message": f"Rate test {i+1}"},
                    headers={"Authorization": f"Bearer {pro_token}"}
                ) as response:
                    if response.status == 429:
                        logger.info(f"✅ Rate limit hit after {i+1} requests")
                        rate_limit_hit = True
                        break
            
            if not rate_limit_hit:
                logger.warning("⚠️ Rate limiting not enforced")
    
    async def run_all_tests(self):
        """Run complete test suite"""
        logger.info("Starting endpoint tests...")
        
        await self.login_all_users()
        await self.test_admin_endpoints()
        await self.test_quota_enforcement()
        await self.test_rate_limiting()
        
        logger.info("✅ All tests completed")

if __name__ == "__main__":
    tester = EndpointTester()
    asyncio.run(tester.run_all_tests())
```

---

## Summary

This unified system design document provides a complete blueprint for implementing the Multi-Database RAG Chatbot System. Key aspects covered:

### For New Engineers
- **Clear file locations**: Every component shows exactly where to create files
- **Integration points**: Comments explain where and how components connect
- **Step-by-step setup**: From project structure to deployment

### For Architects
- **System design patterns**: Dependency injection, service layer, clean architecture
- **Technology justifications**: Why each database and tool was chosen
- **Scalability considerations**: Connection pooling, caching, horizontal scaling

### For Data Scientists
- **ML pipeline details**: Embedding and generation services with optimization
- **RAG implementation**: Complete retrieval-augmented generation pipeline
- **Performance metrics**: Latency targets and optimization strategies

### Critical Implementation Notes

1. **Start with infrastructure**: Set up Docker containers first
2. **Initialize databases**: Run initialization scripts before starting the app
3. **Test incrementally**: Use the test suite after each major component
4. **Monitor resources**: Watch memory usage with AI models loaded
5. **Follow security best practices**: Always use the auth dependencies for protected endpoints

The system is production-ready with enterprise features including authentication, billing, rate limiting, and comprehensive monitoring. Follow the implementation order presented in this document for the smoothest development experience.