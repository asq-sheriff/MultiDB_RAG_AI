---
title: Content Safety Service
owner: Security Team
last_updated: 2025-09-01
status: authoritative
---

# Content Safety Service

> **Real-time PHI detection, emotion analysis, and crisis intervention for therapeutic conversations**

## Purpose & Responsibilities

• **PHI Detection**: Automatically detect and mask personally identifiable health information
• **Crisis Detection**: Real-time analysis for mental health emergencies and suicide risk
• **Emotion Analysis**: Sentiment analysis optimized for elderly therapeutic conversations
• **Safety Filtering**: Content validation against therapeutic conversation guidelines
• **Regulatory Compliance**: Ensure all content meets HIPAA and healthcare safety standards
• **Emergency Escalation**: Trigger immediate alerts for crisis situations

**Service Level Objectives (SLO)**:
- Response time: <100ms (95th percentile)
- Availability: 99.9% uptime
- Crisis detection accuracy: >95%

**In Scope**: Content analysis, safety filtering, crisis detection, PHI protection
**Out of Scope**: Content generation, conversation storage, user management

## APIs

### Content Safety Analysis

```http
POST /api/v1/safety/analyze
Content-Type: application/json
Authorization: Bearer <service-token>
```

**Request**:
```json
{
  "content": "I'm feeling really sad today and thinking about my medication schedule",
  "user_context": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "age_group": "senior",
    "conversation_context": "therapeutic"
  }
}
```

**Response**:
```json
{
  "analysis_id": "456e7890-e89b-12d3-a456-426614174000",
  "safety_score": 0.85,
  "phi_detected": false,
  "crisis_risk": "low",
  "emotion_analysis": {
    "primary_emotion": "sadness",
    "intensity": 0.6,
    "therapeutic_response_needed": true
  },
  "content_safe": true,
  "filtered_content": "I'm feeling really sad today and thinking about my [REDACTED] schedule"
}
```

### Crisis Detection

```http
POST /api/v1/safety/crisis-check
Content-Type: application/json
```

**Error Codes**:
- `400` - Invalid content format
- `401` - Unauthorized access
- `429` - Rate limit exceeded
- `500` - Analysis service failure

## Config

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PORT` | `8007` | No | Service port |
| `REDIS_URL` | `localhost:6379` | Yes | Redis cache connection |
| `CRISIS_THRESHOLD` | `0.8` | No | Crisis detection threshold |
| `PHI_DETECTION_ENABLED` | `true` | No | Enable PHI detection |
| `EMOTION_MODEL_PATH` | `/models/emotion` | No | Emotion analysis model |

**Security Considerations**:
```bash
# Production security settings
REDIS_URL="${SECRET_MANAGER_REDIS_URL}"
ENCRYPTION_KEY="${SECRET_MANAGER_CONTENT_KEY}"
TLS_CERT_FILE="/etc/certs/content-safety.crt"
```

## Datastores

### Redis Cache

**Purpose**: Cache analysis results and model outputs
- **PII/PHI**: No PHI stored (analysis metadata only)
- **Retention**: 24 hours TTL for analysis cache
- **Backup**: Not required (cache only)

**Cache Keys**:
```
content_analysis:{hash} -> SafetyAnalysis
emotion_cache:{user_id}:{date} -> EmotionProfile
phi_patterns -> PHIDetectionRules
```

### External Model APIs

**Crisis Detection Model**: Local sentiment analysis model
**PHI Detection**: Rule-based + NLP pattern matching
**Emotion Analysis**: Therapeutic conversation specialized model

## Dependencies

### Internal Services
- **Audit Service** (8084): Log safety events and crisis alerts
- **Emergency Access** (8085): Crisis escalation procedures

### External Dependencies
- **Redis**: Analysis result caching
- **Emergency Notification Service**: Crisis alert delivery

**Service Call Graph**:
```
content-safety:8007
  ├── redis:6379 (analysis cache)
  ├── audit-logging:8084 (safety events)
  └── emergency-notification (crisis alerts)
```

## Run & Test

### Local Development

```bash
# Prerequisites  
make infrastructure  # Start Redis

# Environment setup
export PORT=8007
export REDIS_URL="redis://localhost:6379"
export CRISIS_THRESHOLD=0.8

# Start service
go run main.go
```

### Testing

```bash
# Unit tests
go test ./... -v

# Safety analysis tests
go test ./... -tags=safety -v

# Crisis detection tests
go test ./... -tags=crisis -v

# Performance benchmarks
go test ./... -bench=. -benchmem
```

### Test Data

```bash
# Test PHI detection
curl -X POST http://localhost:8007/api/v1/safety/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "My SSN is 123-45-6789", "user_context": {"age_group": "senior"}}'

# Test crisis detection
curl -X POST http://localhost:8007/api/v1/safety/crisis-check \
  -H "Content-Type: application/json" \
  -d '{"content": "I want to hurt myself", "user_context": {"user_id": "test-user"}}'
```

## Deploy

### Docker

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o content-safety .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/content-safety .
EXPOSE 8007
CMD ["./content-safety"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: content-safety
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: content-safety
        image: content-safety:latest
        ports:
        - containerPort: 8007
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: cache-secrets
              key: redis-url
        - name: CRISIS_THRESHOLD
          value: "0.8"
        readinessProbe:
          httpGet:
            path: /health
            port: 8007
        livenessProbe:
          httpGet:
            path: /health
            port: 8007
```

## Observability

### Logging

**Structured Logs**:
```json
{
  "timestamp": "2025-09-01T12:00:00Z",
  "level": "warn",
  "service": "content-safety",
  "event": "crisis_detected",
  "user_id": "456e7890-e89b-12d3-a456-426614174000",
  "crisis_score": 0.92,
  "escalation_triggered": true
}
```

### Metrics

**Key Performance Indicators**:
- `safety_analysis_total` - Total content analyses performed
- `crisis_detection_total` - Crisis situations detected
- `phi_detection_total` - PHI instances detected and masked
- `analysis_response_time_seconds` - Analysis latency

### Alerts

**Critical Alerts**:
- Crisis detection threshold exceeded (immediate escalation)
- PHI detection failure (5-minute SLA)
- Service unavailable (immediate escalation)

## Security

### Access Control

**API Security**:
- Service-to-service authentication required
- Rate limiting: 1000 requests/minute per service
- Content analysis results not logged (privacy protection)

### Key Management

**Encryption**: Analysis metadata encrypted with AES-256-GCM
**Secrets**: All sensitive configuration via secret manager

## Troubleshooting

### Common Issues

**Issue**: High crisis false positives
**Resolution**: Adjust `CRISIS_THRESHOLD` and validate analysis patterns

**Issue**: PHI detection misses
**Resolution**: Update PHI detection rules and validate against test cases

**Issue**: Analysis latency spikes
**Resolution**: Check Redis connectivity and model performance

### Playbook Links

- **[Crisis Response](../../docs/operations/Runbooks.md#crisis-response)**
- **[Safety Procedures](../../docs/ai/Safety_and_Therapeutic_Guards.md)**

---

**Service Version**: 1.0.0  
**Crisis Detection**: ✅ Real-time with <100ms response  
**HIPAA Compliance**: ✅ PHI protection and audit logging