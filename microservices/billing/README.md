---
title: Billing Service
owner: Platform Team
last_updated: 2025-09-01
status: authoritative
---

# Billing Service

> **Usage tracking, subscription management, and healthcare billing compliance**

## Purpose & Responsibilities

• **Usage Tracking**: Monitor and track API usage, conversation minutes, and feature utilization
• **Subscription Management**: Handle subscription tiers, upgrades, downgrades, and billing cycles
• **Healthcare Billing**: Comply with healthcare billing regulations and Medicare requirements
• **Cost Analytics**: Provide detailed cost breakdowns for healthcare administrators
• **Rate Limiting**: Enforce usage quotas based on subscription levels
• **Billing Integration**: Interface with external billing systems and payment processors

**Service Level Objectives (SLO)**:
- Response time: <100ms (95th percentile)
- Availability: 99.9% uptime
- Billing accuracy: 99.99%

**In Scope**: Usage metering, subscription lifecycle, billing calculations, quota enforcement
**Out of Scope**: Payment processing, user authentication, clinical data management

## APIs

### Usage Tracking

```http
POST /api/v1/billing/usage
Content-Type: application/json
Authorization: Bearer <service-token>
```

**Request**:
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "organization_id": "456e7890-e89b-12d3-a456-426614174000",
  "usage_type": "conversation_minutes",
  "quantity": 15.5,
  "metadata": {
    "conversation_id": "789e0123-e89b-12d3-a456-426614174000",
    "ai_model_used": "qwen2.5-7b"
  }
}
```

**Response**:
```json
{
  "usage_id": "abc12345-e89b-12d3-a456-426614174000",
  "recorded_at": "2025-09-01T12:00:00Z",
  "quota_remaining": 1440.5,
  "quota_exceeded": false
}
```

### Subscription Management

```http
GET /api/v1/billing/subscription/{user_id}
Authorization: Bearer <admin-token>
```

**Error Codes**:
- `400` - Invalid usage data format
- `401` - Unauthorized access
- `403` - Insufficient billing permissions
- `429` - Quota exceeded
- `500` - Billing calculation failure

## Config

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PORT` | `8081` | No | Service port |
| `DATABASE_URL` | - | Yes | PostgreSQL connection string |
| `REDIS_URL` | `localhost:6379` | Yes | Redis cache connection |
| `BILLING_TIER_DEFAULT` | `basic` | No | Default subscription tier |
| `QUOTA_ENFORCEMENT` | `true` | No | Enable quota checking |

**Security Considerations**:
```bash
# Production security settings
DATABASE_URL="${SECRET_MANAGER_DB_URL}"
REDIS_URL="${SECRET_MANAGER_REDIS_URL}"
STRIPE_API_KEY="${SECRET_MANAGER_STRIPE_KEY}"  # Payment processing
```

## Datastores

### PostgreSQL Tables

**Primary Tables**: `subscriptions`, `usage_records`, `billing_plans`
- **PII/PHI**: Organization billing information (no clinical PHI)
- **Retention**: 7 years for financial records
- **Backup**: Daily encrypted backups with compliance requirements

**Schema**:
```sql
CREATE TABLE subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    organization_id UUID,
    plan_tier VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE usage_records (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    usage_type VARCHAR(100) NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    billing_period DATE NOT NULL
);
```

### Redis Cache

**Purpose**: Real-time quota tracking and billing calculations
- **TTL**: 24 hours for quota cache
- **Keys**: `quota:{user_id}`, `billing_cache:{org_id}`

## Dependencies

### Internal Services
- **Auth Service** (8080): User authentication and organization mapping
- **Audit Service** (8084): Financial event logging

### External Dependencies
- **PostgreSQL**: Subscription and usage data storage
- **Redis**: Real-time quota and billing cache
- **Payment Gateway**: External billing system integration

**Service Call Graph**:
```
billing:8081
  ├── auth-rbac:8080 (user validation)
  ├── audit-logging:8084 (billing events)
  ├── postgresql:5432 (billing data)
  ├── redis:6379 (quota cache)
  └── stripe-api (payment processing)
```

## Run & Test

### Local Development

```bash
# Prerequisites
make infrastructure  # Start PostgreSQL and Redis

# Environment setup
export PORT=8081
export DATABASE_URL="postgresql://chatbot_user:${POSTGRES_PASSWORD}@localhost:5433/chatbot_app"
export REDIS_URL="redis://localhost:6379"

# Start service
go run main.go
```

### Testing

```bash
# Unit tests
go test ./... -v

# Integration tests
go test ./... -tags=integration -v

# Billing accuracy tests
go test ./... -tags=billing -v

# Load testing
go test ./... -bench=. -benchmem
```

### Test Data

```bash
# Test usage tracking
curl -X POST http://localhost:8081/api/v1/billing/usage \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user", "usage_type": "api_calls", "quantity": 10}'

# Test quota check
curl http://localhost:8081/api/v1/billing/quota/test-user
```

## Deploy

### Docker

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o billing-service .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/billing-service .
EXPOSE 8081
CMD ["./billing-service"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billing-service
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: billing
        image: billing-service:latest
        ports:
        - containerPort: 8081
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: postgres-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: cache-secrets
              key: redis-url
```

## Observability

### Logging

**Financial Event Logs**:
```json
{
  "timestamp": "2025-09-01T12:00:00Z",
  "level": "info",
  "service": "billing",
  "event": "usage_recorded",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "usage_type": "conversation_minutes",
  "amount": 15.5,
  "quota_remaining": 1440.5
}
```

### Metrics

**Financial KPIs**:
- `billing_usage_total` - Total usage recorded
- `billing_revenue_total` - Total revenue tracked
- `billing_quota_exceeded_total` - Quota violations
- `billing_response_time_seconds` - Service latency

### Alerts

**Financial Alerts**:
- Quota exceeded for premium customers (immediate)
- Billing calculation errors (5-minute SLA)
- Payment processing failures (15-minute SLA)

## Security

### Financial Data Protection

**Access Control**:
- Billing data requires admin or finance role
- Usage data viewable by organization administrators
- Individual users can view own usage only

**Audit Requirements**:
```go
// All billing operations require audit logging
func (b *BillingService) recordUsage(usage UsageRecord) error {
    // Record usage
    err := b.db.CreateUsageRecord(usage)
    
    // Audit financial event
    auditEvent := AuditEvent{
        EventType: "billing_usage_recorded",
        UserID: usage.UserID,
        Amount: usage.Quantity,
        BillingCategory: usage.UsageType,
    }
    b.auditClient.LogEvent(auditEvent)
    
    return err
}
```

## Troubleshooting

### Common Issues

**Issue**: Quota calculation errors
**Resolution**: Verify Redis cache consistency and recalculate from PostgreSQL

**Issue**: Billing discrepancies  
**Resolution**: Run billing reconciliation job and audit usage records

**Issue**: Payment integration failures
**Resolution**: Check external payment gateway connectivity and API keys

### Playbook Links

- **[Financial Operations](../../docs/operations/Runbooks.md#billing-issues)**
- **[Quota Management](../../docs/operations/Runbooks.md#quota-enforcement)**

---

**Service Version**: 1.0.0  
**Financial Compliance**: ✅ Healthcare billing regulations  
**Data Protection**: ✅ Financial data encryption