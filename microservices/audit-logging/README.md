---
title: Audit Logging Service
owner: Compliance Team
last_updated: 2025-09-01
status: authoritative
---

# Audit Logging Service

> **HIPAA-compliant immutable audit trail service for comprehensive compliance logging**

## Purpose & Responsibilities

• **Audit Trail Creation**: Generate comprehensive audit logs for all user and system actions
• **HIPAA Compliance**: Ensure all audit events meet HIPAA §164.312(b) requirements
• **Immutable Storage**: Store audit logs with tamper detection and integrity protection
• **Event Correlation**: Link related audit events across distributed system components
• **Compliance Reporting**: Provide audit trail reports for regulatory compliance
• **Emergency Access Logging**: Track break-glass access with enhanced audit trails

**Service Level Objectives (SLO)**:
- Response time: <50ms (95th percentile)
- Availability: 99.95% uptime
- Audit coverage: 100% of PHI access events

**In Scope**: Audit event ingestion, storage, retrieval, compliance reporting
**Out of Scope**: Business logic processing, user data management, AI processing

## APIs

### Audit Event Creation

```http
POST /api/v1/audit/log
Content-Type: application/json
Authorization: Bearer <service-token>
```

**Request**:
```json
{
  "event_type": "phi_access",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "patient_id": "456e7890-e89b-12d3-a456-426614174000",
  "action": "view_patient_profile",
  "resource": "patient_demographics",
  "phi_accessed": true,
  "ip_address": "192.168.1.100",
  "purpose": "treatment_coordination"
}
```

**Response**:
```json
{
  "audit_id": "789e0123-e89b-12d3-a456-426614174000",
  "logged_at": "2025-09-01T12:00:00Z",
  "status": "logged"
}
```

### Audit Trail Retrieval

```http
GET /api/v1/audit/search?user_id={user_id}&start_date={date}&end_date={date}
Authorization: Bearer <admin-token>
```

**Error Codes**:
- `400` - Invalid audit event format
- `401` - Unauthorized access
- `403` - Insufficient permissions
- `500` - Audit storage failure

## Config

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PORT` | `8084` | No | Service port |
| `POSTGRES_URL` | - | Yes | PostgreSQL connection string |
| `LOG_LEVEL` | `info` | No | Logging level |
| `AUDIT_RETENTION_DAYS` | `2555` | No | Audit log retention (7 years) |
| `ENABLE_TAMPER_DETECTION` | `true` | No | Enable audit integrity checks |

**Security Considerations**:
```bash
# Production security settings
POSTGRES_URL="${SECRET_MANAGER_DB_URL}"  # Never hardcode
AUDIT_ENCRYPTION_KEY="${SECRET_MANAGER_AUDIT_KEY}"
TLS_CERT_FILE="/etc/certs/audit-service.crt"
TLS_KEY_FILE="/etc/certs/audit-service.key"
```

## Datastores

### PostgreSQL Tables

**Primary Table**: `audit_logs`
- **PII/PHI**: Contains patient IDs and access patterns (PHI metadata)
- **Retention**: 7 years (HIPAA requirement)
- **Backup**: Daily encrypted backups with 3-2-1 strategy

**Schema**:
```sql
CREATE TABLE audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    user_id UUID,
    patient_id UUID,
    action VARCHAR(200) NOT NULL,
    resource VARCHAR(500),
    phi_accessed BOOLEAN DEFAULT false,
    ip_address INET,
    hash_chain VARCHAR(64) NOT NULL
);

-- Immutability constraint (HIPAA requirement)
REVOKE UPDATE, DELETE ON audit_logs FROM ALL;
```

**Indexes**:
- Primary: `audit_id` (UUID)
- Performance: `user_id, timestamp DESC`
- Compliance: `patient_id, timestamp DESC`
- Search: `event_type, timestamp DESC`

## Dependencies

### Internal Services
- **Auth Service** (8080): Token validation and user context
- **Emergency Access** (8085): Break-glass access logging

### External Dependencies
- **PostgreSQL**: Primary audit storage
- **Secret Manager**: Encryption key management

**Service Call Graph**:
```
audit-logging:8084
  ├── auth-rbac:8080 (token validation)
  ├── postgresql:5432 (audit storage)
  └── secret-manager (encryption keys)
```

## Run & Test

### Local Development

```bash
# Prerequisites
make infrastructure  # Start PostgreSQL

# Environment setup
export PORT=8084
export POSTGRES_URL="postgresql://chatbot_user:${POSTGRES_PASSWORD}@localhost:5433/chatbot_app"

# Start service
go run main.go

# Alternative: Use air for hot reload
air -c .air.toml
```

### Testing

```bash
# Unit tests
go test ./... -v

# Integration tests
go test ./... -tags=integration -v

# HIPAA compliance tests
go test ./... -tags=hipaa -v

# Performance tests
go test ./... -bench=. -benchmem
```

### Seed Data

```bash
# Create test audit events
curl -X POST http://localhost:8084/api/v1/audit/log \
  -H "Content-Type: application/json" \
  -d '{"event_type": "user_login", "user_id": "test-user", "action": "login"}'
```

## Deploy

### Docker

```dockerfile
# Dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o audit-logging-service .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/audit-logging-service .
EXPOSE 8084
CMD ["./audit-logging-service"]
```

### Kubernetes

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: audit-logging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: audit-logging
  template:
    spec:
      containers:
      - name: audit-logging
        image: audit-logging:latest
        ports:
        - containerPort: 8084
        env:
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: postgres-url
        readinessProbe:
          httpGet:
            path: /health
            port: 8084
          initialDelaySeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8084
          initialDelaySeconds: 30
```

### Health Checks

```bash
# Readiness: Service accepting requests
curl http://localhost:8084/health

# Liveness: Service healthy and responsive
curl http://localhost:8084/health/live
```

## Observability

### Logging

**Structured Logs** (JSON format):
```json
{
  "timestamp": "2025-09-01T12:00:00Z",
  "level": "info",
  "service": "audit-logging",
  "event": "audit_logged",
  "audit_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "456e7890-e89b-12d3-a456-426614174000"
}
```

### Metrics

**Key Performance Indicators**:
- `audit_events_total` - Total audit events logged
- `audit_events_failed_total` - Failed audit logging attempts
- `audit_response_time_seconds` - Response time histogram
- `audit_storage_size_bytes` - Total audit storage size

### Traces

**Distributed Tracing** (OpenTelemetry):
- Request ID correlation across services
- Audit event processing spans
- Database operation tracing

### Dashboards

**Grafana Dashboard**: [Audit Service Dashboard](http://grafana:3000/d/audit-service)

**Key Panels**:
- Audit event rate (events/second)
- Response time percentiles
- Error rate by event type
- Storage growth trends

### Alerts

**Critical Alerts**:
- Audit logging failures (immediate escalation)
- Storage capacity >80% (4-hour SLA)
- Tamper detection triggered (immediate escalation)

## Security

### Authentication & Authorization

**Service Authentication**:
- Service-to-service JWT tokens
- Admin API requires admin role validation
- Read access requires compliance officer role

**Access Control**:
```go
// RBAC enforcement for audit access
func (s *AuditService) authorizeAuditAccess(userID string, action string) error {
    roles, err := s.authClient.GetUserRoles(userID)
    if err != nil {
        return fmt.Errorf("failed to get user roles: %w", err)
    }
    
    switch action {
    case "read_audit_logs":
        return s.requireRole(roles, []string{"compliance_officer", "security_admin"})
    case "delete_audit_logs":
        return s.requireRole(roles, []string{"security_admin"})
    default:
        return fmt.Errorf("unknown audit action: %s", action)
    }
}
```

### Key Management

**Encryption Keys**:
- Audit log encryption: AES-256-GCM
- Hash chain keys: HMAC-SHA256
- Key rotation: 90-day cycle

**Secret Management**:
```bash
# Kubernetes secrets
kubectl create secret generic audit-secrets \
  --from-literal=encryption-key="${AUDIT_ENCRYPTION_KEY}" \
  --from-literal=hash-key="${AUDIT_HASH_KEY}"
```

## Troubleshooting

### Common Issues

**Issue**: Audit logging failures
**Symptoms**: HTTP 500 responses, missing audit events
**Resolution**: 
1. Check PostgreSQL connectivity
2. Verify disk space for audit storage
3. Check encryption key availability

**Issue**: High response latency
**Symptoms**: >100ms response times
**Resolution**:
1. Check database connection pool utilization
2. Verify audit log table indexes
3. Consider batch audit logging

**Issue**: Tamper detection alerts
**Symptoms**: Hash chain validation failures
**Resolution**:
1. Investigate potential security incident
2. Verify audit log integrity
3. Contact security team immediately

### Playbook Links

- **[Incident Response](../../docs/operations/Runbooks.md#audit-logging-incidents)**
- **[HIPAA Compliance](../../docs/compliance/Audit_Trail_Guide.md)**
- **[Security Procedures](../../docs/security/Security_Architecture.md#audit-security)**

---

**Service Version**: 1.0.0  
**HIPAA Compliance**: ✅ §164.312(b) Technical Safeguards  
**Last Security Review**: 2025-09-01