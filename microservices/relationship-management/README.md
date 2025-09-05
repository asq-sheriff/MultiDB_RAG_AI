---
title: Relationship Management Service
owner: Clinical Team
last_updated: 2025-09-01
status: authoritative
---

# Relationship Management Service

> **Patient-provider relationship verification and healthcare delegation management**

## Purpose & Responsibilities

• **Relationship Verification**: Validate patient-provider relationships for PHI access authorization
• **Delegation Management**: Handle family member and caregiver access delegation
• **Care Team Coordination**: Manage multi-provider care teams and access permissions
• **Consent Workflow**: Interface with consent service for relationship-based access
• **Emergency Contacts**: Maintain emergency contact relationships and notification preferences
• **HIPAA Compliance**: Ensure all relationship-based access meets HIPAA requirements

**Service Level Objectives (SLO)**:
- Response time: <100ms (95th percentile)
- Availability: 99.9% uptime
- Relationship validation accuracy: 99.99%

**In Scope**: Relationship verification, delegation workflows, care team management
**Out of Scope**: User authentication, clinical decision making, direct patient care

## APIs

### Relationship Verification

```http
POST /api/v1/relationships/verify
Content-Type: application/json
Authorization: Bearer <service-token>
```

**Request**:
```json
{
  "requesting_user_id": "123e4567-e89b-12d3-a456-426614174000",
  "patient_id": "456e7890-e89b-12d3-a456-426614174000",
  "relationship_type": "healthcare_provider",
  "access_purpose": "treatment_coordination",
  "data_scope": ["medical_history", "medication_list"]
}
```

**Response**:
```json
{
  "relationship_verified": true,
  "relationship_type": "healthcare_provider",
  "access_granted": true,
  "access_scope": ["medical_history", "medication_list"],
  "expiration": "2025-09-01T23:59:59Z",
  "delegation_chain": [
    {
      "delegator_id": "456e7890-e89b-12d3-a456-426614174000",
      "delegated_to": "123e4567-e89b-12d3-a456-426614174000",
      "relationship": "primary_care_physician"
    }
  ]
}
```

### Delegation Management

```http
POST /api/v1/relationships/delegate
Content-Type: application/json
Authorization: Bearer <patient-token>
```

**Error Codes**:
- `400` - Invalid relationship request
- `401` - Unauthorized access
- `403` - Relationship not authorized
- `404` - Patient or provider not found
- `500` - Relationship service failure

## Config

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PORT` | `8087` | No | Service port |
| `POSTGRES_URL` | - | Yes | PostgreSQL connection string |
| `RELATIONSHIP_TTL` | `2592000` | No | Relationship cache TTL (30 days) |
| `DELEGATION_APPROVAL` | `auto` | No | Delegation approval mode |
| `EMERGENCY_BYPASS` | `true` | No | Allow emergency relationship bypass |

**Security Considerations**:
```bash
# Production security settings
POSTGRES_URL="${SECRET_MANAGER_DB_URL}"
ENCRYPTION_KEY="${SECRET_MANAGER_RELATIONSHIP_KEY}"
NOTIFICATION_API_KEY="${SECRET_MANAGER_NOTIFICATION_KEY}"
```

## Datastores

### PostgreSQL Tables

**Primary Tables**: `patient_relationships`, `care_delegations`, `emergency_contacts`
- **PII/PHI**: Patient IDs, provider IDs, relationship details (PHI metadata)
- **Retention**: Active relationships permanent, inactive 7 years
- **Backup**: Daily encrypted backups with relationship integrity

**Schema**:
```sql
CREATE TABLE patient_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    provider_id UUID NOT NULL,
    relationship_type VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    start_date DATE NOT NULL,
    end_date DATE,
    access_scope JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE care_delegations (
    delegation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delegator_id UUID NOT NULL,  -- Patient
    delegate_id UUID NOT NULL,   -- Family/Caregiver
    delegation_scope JSONB NOT NULL,
    active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes**:
- Performance: `patient_id, status`
- Lookup: `provider_id, relationship_type`
- Delegation: `delegator_id, active`

## Dependencies

### Internal Services
- **Auth Service** (8080): User and provider authentication
- **Consent Service** (8083): Relationship-based consent validation
- **Audit Service** (8084): Relationship access audit logging

### External Dependencies
- **PostgreSQL**: Relationship data storage
- **Provider Registry**: External healthcare provider verification

**Service Call Graph**:
```
relationship-management:8087
  ├── auth-rbac:8080 (user verification)
  ├── consent:8083 (consent validation)
  ├── audit-logging:8084 (access audit)
  ├── postgresql:5432 (relationship data)
  └── provider-registry (external verification)
```

## Run & Test

### Local Development

```bash
# Prerequisites
make infrastructure  # Start PostgreSQL

# Environment setup
export PORT=8087
export POSTGRES_URL="postgresql://chatbot_user:${POSTGRES_PASSWORD}@localhost:5433/chatbot_app"
export DELEGATION_APPROVAL="auto"

# Start service
go run main.go
```

### Testing

```bash
# Unit tests
go test ./... -v

# Relationship verification tests
go test ./... -tags=relationships -v

# Delegation workflow tests
go test ./... -tags=delegation -v

# HIPAA compliance tests
go test ./... -tags=hipaa -v
```

### Test Relationships

```bash
# Test relationship verification
curl -X POST http://localhost:8087/api/v1/relationships/verify \
  -H "Content-Type: application/json" \
  -d '{
    "requesting_user_id": "test-provider",
    "patient_id": "test-patient",
    "relationship_type": "healthcare_provider"
  }'

# Test delegation
curl -X POST http://localhost:8087/api/v1/relationships/delegate \
  -H "Content-Type: application/json" \
  -d '{
    "delegator_id": "test-patient",
    "delegate_id": "test-family-member",
    "delegation_scope": ["basic_health_info"]
  }'
```

## Deploy

### Docker

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o relationship-manager .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/relationship-manager .
EXPOSE 8087
CMD ["./relationship-manager"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: relationship-management
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: relationship-manager
        image: relationship-management:latest
        ports:
        - containerPort: 8087
        env:
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: postgres-url
```

## Observability

### Logging

**Relationship Event Logs**:
```json
{
  "timestamp": "2025-09-01T12:00:00Z",
  "level": "info", 
  "service": "relationship-management",
  "event": "relationship_verified",
  "patient_id": "456e7890-e89b-12d3-a456-426614174000",
  "provider_id": "123e4567-e89b-12d3-a456-426614174000",
  "relationship_type": "healthcare_provider",
  "access_granted": true
}
```

### Metrics

**Relationship KPIs**:
- `relationship_verifications_total` - Total relationship checks
- `delegation_requests_total` - Delegation workflow requests
- `relationship_cache_hits` - Cache performance
- `verification_response_time_seconds` - Response latency

### Alerts

**Relationship Alerts**:
- Unusual delegation patterns (30-minute SLA)
- Relationship verification failures (10-minute SLA)
- Emergency relationship bypass usage (immediate)

## Security

### Access Control

**Relationship Authorization**:
```go
// Relationship-based access control
func (r *RelationshipService) verifyAccess(request AccessRequest) (*AccessDecision, error) {
    // Verify active relationship
    relationship, err := r.getActiveRelationship(request.ProviderID, request.PatientID)
    if err != nil {
        return nil, fmt.Errorf("relationship verification failed: %w", err)
    }
    
    // Check relationship scope
    if !r.isAccessAuthorized(relationship, request.DataScope) {
        return &AccessDecision{Authorized: false, Reason: "insufficient_scope"}, nil
    }
    
    // Audit relationship access
    r.auditClient.LogRelationshipAccess(relationship, request)
    
    return &AccessDecision{
        Authorized: true,
        Scope: relationship.AccessScope,
        ExpiresAt: relationship.ExpiresAt,
    }, nil
}
```

## Troubleshooting

### Common Issues

**Issue**: Relationship verification failures
**Resolution**: Check provider credentials and patient relationship status

**Issue**: Delegation workflow errors
**Resolution**: Verify patient consent and delegation authorization

**Issue**: Emergency access delays
**Resolution**: Check emergency bypass configuration and provider authentication

### Playbook Links

- **[Relationship Issues](../../docs/operations/Runbooks.md#relationship-management)**
- **[Delegation Workflows](../../docs/compliance/Consent_Management.md#delegation)**

---

**Service Version**: 1.0.0  
**Relationship Verification**: ✅ Real-time healthcare relationship validation  
**HIPAA Compliance**: ✅ Delegation and consent management