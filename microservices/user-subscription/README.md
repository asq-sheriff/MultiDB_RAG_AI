# User Subscription Service (Go)

A high-performance Go microservice for managing user subscription tiers, usage quotas, and billing in a healthcare AI platform.

## 🏥 Healthcare AI Platform - Subscription Management

This service handles subscription lifecycle management, quota enforcement, and usage tracking for our therapeutic AI chatbot platform with HIPAA compliance and healthcare-specific features.

## ✨ Features

### 📊 Subscription Management
- **Three-tier system**: Free, Professional, Enterprise
- **Flexible billing cycles**: Monthly, yearly, weekly
- **Subscription lifecycle**: Create, upgrade, downgrade, cancel, pause, resume
- **Automatic renewals** with configurable settings
- **Trial period support** with automatic conversion

### 💳 Usage Tracking & Quotas
- **Real-time quota enforcement** across multiple resource types
- **Usage recording** with metadata support
- **Redis caching** for high-performance quota checks
- **Overage handling** for Enterprise customers
- **Detailed usage analytics** and reporting

### 🔒 Security & Compliance
- **JWT authentication** integration ready
- **Rate limiting** with Redis backend
- **CORS support** for cross-origin requests
- **Request/response logging** for audit trails
- **Health checks** and monitoring endpoints

### 🗄️ Multi-Database Architecture
- **PostgreSQL**: Primary subscription data with JSONB support
- **Redis**: High-performance caching and rate limiting
- **Connection pooling** and health monitoring
- **Automatic migrations** and schema management

## 🚀 Quick Start

### Prerequisites
- Go 1.21+
- PostgreSQL 13+
- Redis 6+
- Docker (optional)

### Environment Configuration

```bash
# Service Configuration
PORT=8010
ENVIRONMENT=development
LOG_LEVEL=info
ENABLE_METRICS=true
ENABLE_DEBUG=false

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=chatbot_app

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=""
REDIS_DB=0

# Timeouts
GRACEFUL_SHUTDOWN_TIMEOUT=30s
HTTP_READ_TIMEOUT=30s
HTTP_WRITE_TIMEOUT=30s
```

### Running Locally

```bash
# Install dependencies
go mod tidy

# Build the service
go build -o user-subscription-service .

# Run the service
./user-subscription-service
```

### Using Docker

```bash
# Build Docker image
docker build -t user-subscription-service .

# Run with Docker
docker run -p 8010:8010 \
  -e POSTGRES_HOST=host.docker.internal \
  -e REDIS_HOST=host.docker.internal \
  user-subscription-service
```

## 📡 API Endpoints

### Subscription Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/subscriptions/` | Create new subscription |
| `GET` | `/api/v1/subscriptions/user/{user_id}` | Get user subscription |
| `PUT` | `/api/v1/subscriptions/user/{user_id}/upgrade` | Upgrade subscription |
| `PUT` | `/api/v1/subscriptions/user/{user_id}/downgrade` | Schedule downgrade |
| `DELETE` | `/api/v1/subscriptions/user/{user_id}/cancel` | Cancel subscription |
| `POST` | `/api/v1/subscriptions/user/{user_id}/reactivate` | Reactivate subscription |
| `POST` | `/api/v1/subscriptions/user/{user_id}/pause` | Pause subscription |
| `POST` | `/api/v1/subscriptions/user/{user_id}/resume` | Resume subscription |

### Usage & Quota Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/usage/record` | Record usage |
| `GET` | `/api/v1/usage/user/{user_id}/quota/{resource}` | Check quota |
| `GET` | `/api/v1/usage/user/{user_id}/summary` | Usage summary |

### Plan Information

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/plans/` | List all plans |
| `GET` | `/api/v1/plans/{plan}/features` | Get plan features |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/metrics` | Service metrics |
| `POST` | `/api/v1/admin/renewals/process` | Process renewals |
| `POST` | `/api/v1/admin/expired/process` | Process expired |

### Health & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |

## 💰 Subscription Tiers

### 🆓 Free Tier
- **Price**: $0/month
- **Messages**: 100/month
- **API Calls**: 500/month
- **Storage**: 1GB
- **Users**: 1
- **Features**: Basic therapeutic chat, emotion analysis, safety monitoring

### 💼 Professional
- **Price**: $49.99/month ($479.88/year - 20% savings)
- **Messages**: 5,000/month
- **API Calls**: 10,000/month
- **Storage**: 10GB
- **Users**: 5
- **Features**: Advanced therapeutic protocols, crisis intervention, RAG search, progress tracking

### 🏢 Enterprise
- **Price**: $199.99/month ($1919.88/year - 20% savings)
- **Messages**: 50,000/month
- **API Calls**: 100,000/month
- **Storage**: 100GB
- **Users**: 50
- **Features**: Custom model training, HIPAA compliance reporting, 24/7 support, white-label options

## 🧪 Testing

```bash
# Run unit tests
go test -v

# Run with coverage
go test -cover -v

# Run benchmarks
go test -bench=. -benchmem

# Run specific test
go test -v -run TestCreateSubscriptionAPI
```

## 📊 Example API Usage

### Create Subscription
```bash
curl -X POST http://localhost:8010/api/v1/subscriptions/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "plan_type": "pro",
    "billing_cycle": "monthly"
  }'
```

### Check Quota
```bash
curl http://localhost:8010/api/v1/usage/user/123e4567-e89b-12d3-a456-426614174000/quota/messages
```

### Record Usage
```bash
curl -X POST http://localhost:8010/api/v1/usage/record \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "resource_type": "messages",
    "quantity": 1,
    "metadata": {"session_id": "abc123"}
  }'
```

## 🔧 Configuration

The service supports extensive configuration through environment variables:

- **Service Settings**: Port, environment, debug mode
- **Database**: PostgreSQL and Redis connection settings
- **Performance**: Timeouts, connection pooling, caching
- **Security**: Authentication, rate limiting, CORS
- **Monitoring**: Health checks, metrics, logging

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTTP Client   │    │      Gin        │    │   Controllers   │
│                 │───▶│   Web Server    │───▶│   (Handlers)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   Service       │    │   Database      │
│  (Primary DB)   │◀───│   Layer         │───▶│   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐                               ┌─────────────────┐
│     Redis       │                               │     Models      │
│ (Cache/Limits)  │◀──────────────────────────────│   & Schemas     │
└─────────────────┘                               └─────────────────┘
```

## 🔄 Background Processes

The service runs several background processes:

1. **Subscription Renewals** (every hour)
   - Processes automatic renewals
   - Handles billing cycle transitions
   - Updates subscription status

2. **Expired Subscriptions** (every 30 minutes)
   - Marks expired subscriptions
   - Handles grace periods
   - Triggers notifications

3. **Health Monitoring** (every 5 minutes)
   - Database connectivity checks
   - Redis availability monitoring
   - Service health reporting

## 🚀 Production Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  subscription-service:
    build: .
    ports:
      - "8010:8010"
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - ENVIRONMENT=production
    depends_on:
      - postgres
      - redis
    
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=chatbot_app
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    
  redis:
    image: redis:6-alpine
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: subscription-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: subscription-service
  template:
    metadata:
      labels:
        app: subscription-service
    spec:
      containers:
      - name: subscription-service
        image: subscription-service:latest
        ports:
        - containerPort: 8010
        env:
        - name: POSTGRES_HOST
          value: "postgres-service"
        - name: REDIS_HOST
          value: "redis-service"
        - name: ENVIRONMENT
          value: "production"
        livenessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 5
          periodSeconds: 5
```

## 📈 Monitoring & Observability

- **Health Checks**: `/health` endpoint with database status
- **Structured Logging**: JSON logs with correlation IDs
- **Metrics**: Ready for Prometheus integration
- **Request Tracing**: Request/response logging with timing
- **Error Handling**: Comprehensive error responses with context

## 🤝 Integration

This service integrates with:

- **Authentication Service**: JWT token validation
- **Billing Provider**: Stripe webhook processing  
- **Notification Service**: Subscription events
- **Analytics Service**: Usage metrics
- **API Gateway**: Centralized routing and middleware

## 📝 License

This project is part of the MultiDB Chatbot healthcare AI platform. All rights reserved.

## 🔗 Related Services

- **Chat History Service**: Message persistence and retrieval
- **Background Tasks Service**: Async job processing
- **Billing Service**: Payment and invoice management
- **API Gateway**: Request routing and middleware

---

🏥 **Healthcare AI Platform** - Empowering therapeutic conversations with advanced AI technology and subscription management.