---
title: Emergency Access Service
owner: Security Team
last_updated: 2025-09-01
status: authoritative
---

# Emergency Access Service

> **Break-glass access controls and emergency PHI access with enhanced audit trails**

## Purpose & Responsibilities

• **Break-Glass Access**: Provide emergency access to PHI during life-threatening situations
• **Enhanced Auditing**: Comprehensive audit trails for all emergency access events
• **Access Justification**: Capture and validate emergency access justifications
• **Time-Limited Access**: Automatic access revocation after emergency periods
• **Compliance Monitoring**: Real-time monitoring of emergency access patterns
• **Post-Incident Review**: Automated workflows for emergency access review

**Service Level Objectives (SLO)**:
- Emergency access grant: <30 seconds
- Availability: 99.99% uptime
- Audit coverage: 100% of emergency events

**In Scope**: Emergency access authorization, audit logging, access review workflows
**Out of Scope**: Regular PHI access, user authentication, clinical decision support

## APIs

### Emergency Access Request

```http
POST /api/v1/emergency/request-access
Content-Type: application/json
Authorization: Bearer <healthcare-provider-token>
```

**Request**:
```json
{
  "patient_id": "123e4567-e89b-12d3-a456-426614174000",
  "requesting_provider_id": "456e7890-e89b-12d3-a456-426614174000",
  "emergency_type": "life_threatening",
  "justification": "Patient cardiac arrest - need immediate access to medication allergies",
  "estimated_duration_minutes": 60,
  "supervisor_notification": true
}
```

**Response**:
```json
{
  "access_token": "emergency_abc123def456",
  "access_granted": true,
  "access_expires_at": "2025-09-01T13:00:00Z",
  "scope": ["patient_medical_history", "medication_allergies", "emergency_contacts"],
  "audit_id": "789e0123-e89b-12d3-a456-426614174000",
  "supervisor_notified": true
}
```

### Access Revocation

```http
POST /api/v1/emergency/revoke-access
Content-Type: application/json
```

**Error Codes**:
- `400` - Invalid emergency request format
- `401` - Unauthorized provider
- `403` - Emergency access denied
- `500` - Emergency system failure

## Config

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PORT` | `8085` | No | Service port |
| `POSTGRES_URL` | - | Yes | PostgreSQL connection string |
| `MAX_EMERGENCY_DURATION` | `240` | No | Max emergency access (minutes) |
| `SUPERVISOR_NOTIFICATION` | `true` | No | Auto-notify supervisors |
| `AUDIT_LEVEL` | `enhanced` | No | Audit detail level |

**Security Considerations**:
```bash
# Production security settings  
POSTGRES_URL="${SECRET_MANAGER_DB_URL}"
EMERGENCY_SIGNING_KEY="${SECRET_MANAGER_EMERGENCY_KEY}"
NOTIFICATION_API_KEY="${SECRET_MANAGER_NOTIFICATION_KEY}"
```

## Datastores

### PostgreSQL Tables

**Primary Table**: `emergency_access_logs`
- **PII/PHI**: Provider IDs, patient IDs, access justifications (PHI metadata)
- **Retention**: Permanent retention (regulatory requirement)
- **Backup**: Real-time replication with immutable storage

**Schema**:
```sql
CREATE TABLE emergency_access_logs (
    access_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    provider_id UUID NOT NULL,
    emergency_type VARCHAR(50) NOT NULL,
    justification TEXT NOT NULL,
    access_granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_expires_at TIMESTAMPTZ NOT NULL,
    access_revoked_at TIMESTAMPTZ,
    supervisor_notified BOOLEAN DEFAULT false,
    review_status VARCHAR(20) DEFAULT 'pending',
    review_completed_at TIMESTAMPTZ
);

-- Immutability for compliance
REVOKE UPDATE ON emergency_access_logs FROM ALL;
```

## Dependencies

### Internal Services
- **Auth Service** (8080): Provider authentication and role validation
- **Audit Service** (8084): Enhanced audit logging for emergency events
- **Consent Service** (8083): Emergency consent override tracking

### External Dependencies
- **PostgreSQL**: Emergency access record storage
- **Notification Service**: Supervisor and administrator alerts

**Service Call Graph**:
```
emergency-access:8085
  ├── auth-rbac:8080 (provider validation)
  ├── audit-logging:8084 (emergency audit)
  ├── consent:8083 (consent override)
  ├── postgresql:5432 (access records)
  └── notification-service (alerts)
```

## Run & Test

### Local Development

```bash
# Prerequisites
make infrastructure  # Start PostgreSQL

# Environment setup
export PORT=8085
export POSTGRES_URL="postgresql://chatbot_user:${POSTGRES_PASSWORD}@localhost:5433/chatbot_app"
export MAX_EMERGENCY_DURATION=240

# Start service
go run main.go
```

### Testing

```bash
# Unit tests
go test ./... -v

# Emergency scenario tests
go test ./... -tags=emergency -v

# Compliance tests
go test ./... -tags=hipaa -v

# Load testing for crisis scenarios
go test ./... -bench=BenchmarkEmergencyAccess
```

### Test Emergency Scenarios

```bash
# Life-threatening emergency
curl -X POST http://localhost:8085/api/v1/emergency/request-access \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "test-patient",
    "requesting_provider_id": "test-provider", 
    "emergency_type": "life_threatening",
    "justification": "Cardiac arrest - need medication allergies"
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
RUN go build -o emergency-access .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/emergency-access .
EXPOSE 8085
CMD ["./emergency-access"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: emergency-access
spec:
  replicas: 3  # High availability for emergencies
  template:
    spec:
      containers:
      - name: emergency-access
        image: emergency-access:latest
        ports:
        - containerPort: 8085
        env:
        - name: MAX_EMERGENCY_DURATION
          value: "240"
        readinessProbe:
          httpGet:
            path: /health
            port: 8085
          initialDelaySeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8085
          initialDelaySeconds: 10
```

## Observability

### Logging

**Emergency Event Logs**:
```json
{
  "timestamp": "2025-09-01T12:00:00Z",
  "level": "critical",
  "service": "emergency-access",
  "event": "emergency_access_granted",
  "provider_id": "456e7890-e89b-12d3-a456-426614174000",
  "patient_id": "123e4567-e89b-12d3-a456-426614174000",
  "emergency_type": "life_threatening",
  "access_duration_minutes": 60
}
```

### Metrics

**Emergency Access KPIs**:
- `emergency_access_requests_total` - Total emergency access requests
- `emergency_access_granted_total` - Emergency access approvals
- `emergency_access_duration_seconds` - Access duration tracking
- `emergency_response_time_seconds` - Time to grant access

### Alerts

**Critical Alerts**:
- Emergency access service down (immediate escalation)
- Unusual emergency access patterns (30-minute SLA)
- Emergency access abuse detected (immediate escalation)

## Security

### Access Control

**Emergency Authorization**:
- Only licensed healthcare providers can request emergency access
- Supervisor notification required for all emergency access
- Automatic access revocation after time limit

**Audit Requirements**:
```go
// Enhanced audit logging for emergency access
func (e *EmergencyService) grantAccess(request EmergencyAccessRequest) error {
    // Create enhanced audit event
    auditEvent := AuditEvent{
        EventType: "emergency_access_granted",
        ProviderID: request.ProviderID,
        PatientID: request.PatientID,
        EmergencyType: request.EmergencyType,
        Justification: request.Justification,
        AccessScope: request.AccessScope,
        SupervisorNotified: true,
        AuditLevel: "critical",
    }
    
    // Log to both audit service and emergency-specific logs
    e.auditClient.LogEmergencyEvent(auditEvent)
    e.emergencyAuditLogger.LogAccess(request)
    
    return nil
}
```

## Troubleshooting

### Common Issues

**Issue**: Emergency access denied during crisis
**Resolution**: 
1. Verify provider credentials and licensing
2. Check emergency type classification
3. Escalate to security team if persistent

**Issue**: Supervisor notification failures
**Resolution**:
1. Verify notification service connectivity
2. Check supervisor contact information
3. Manual notification as backup

**Issue**: Access token validation errors
**Resolution**:
1. Check emergency token signing keys
2. Verify token expiration times
3. Regenerate access tokens if needed

### Playbook Links

- **[Emergency Response](../../docs/operations/Runbooks.md#emergency-procedures)**
- **[Break-Glass Protocol](../../docs/security/Access_Control_Model.md#emergency-access)**

---

**Service Version**: 1.0.0  
**Emergency Response**: ✅ <30 second access grant  
**HIPAA Compliance**: ✅ Enhanced audit trails for emergency access