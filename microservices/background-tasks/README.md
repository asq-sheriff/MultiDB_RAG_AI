---
title: Background Tasks Service
owner: Platform Team
last_updated: 2025-09-01
status: authoritative
---

# Background Tasks Service

> **Asynchronous task processing and job scheduling for healthcare workflows**

## Purpose & Responsibilities

• **Task Queue Management**: Process asynchronous tasks using Redis-based queues
• **Healthcare Notifications**: Send care alerts, medication reminders, and wellness check-ins
• **Data Processing**: Background processing of large healthcare datasets
• **Scheduled Jobs**: Execute recurring tasks like report generation and data cleanup
• **Event Processing**: Handle system events and trigger appropriate workflows
• **Batch Operations**: Process bulk operations like data exports and analytics

**Service Level Objectives (SLO)**:
- Task processing: <5 seconds (95th percentile)
- Availability: 99.5% uptime
- Queue throughput: 1000 tasks/minute

**In Scope**: Async task processing, job scheduling, notification delivery, batch operations
**Out of Scope**: Real-time user interactions, synchronous API processing, data storage

## APIs

### Task Submission

```http
POST /api/v1/tasks/submit
Content-Type: application/json
Authorization: Bearer <service-token>
```

**Request**:
```json
{
  "task_type": "send_medication_reminder",
  "priority": "high",
  "scheduled_for": "2025-09-01T14:00:00Z",
  "payload": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "medication_name": "Lisinopril",
    "dosage": "10mg",
    "reminder_time": "14:00"
  },
  "max_retries": 3,
  "timeout_seconds": 30
}
```

**Response**:
```json
{
  "task_id": "456e7890-e89b-12d3-a456-426614174000",
  "status": "queued",
  "scheduled_for": "2025-09-01T14:00:00Z",
  "estimated_completion": "2025-09-01T14:01:00Z"
}
```

### Task Status

```http
GET /api/v1/tasks/{task_id}/status
Authorization: Bearer <service-token>
```

**Error Codes**:
- `400` - Invalid task format
- `401` - Unauthorized access
- `404` - Task not found
- `500` - Task processing failure

## Config

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PORT` | `8086` | No | Service port |
| `REDIS_URL` | `localhost:6379` | Yes | Redis queue connection |
| `WORKER_COUNT` | `5` | No | Number of worker goroutines |
| `MAX_RETRIES` | `3` | No | Default task retry limit |
| `NOTIFICATION_ENABLED` | `true` | No | Enable notification tasks |

**Security Considerations**:
```bash
# Production security settings
REDIS_URL="${SECRET_MANAGER_REDIS_URL}"
NOTIFICATION_API_KEY="${SECRET_MANAGER_NOTIFICATION_KEY}"
WEBHOOK_SECRET="${SECRET_MANAGER_WEBHOOK_SECRET}"
```

## Datastores

### Redis Queues

**Task Queues**:
- `high_priority_tasks` - Critical healthcare notifications
- `normal_priority_tasks` - Regular scheduled tasks  
- `low_priority_tasks` - Analytics and cleanup jobs
- `failed_tasks` - Failed task retry queue

**PII/PHI**: Task metadata only (no PHI content in queue)
**Retention**: 48 hours TTL for completed tasks
**Backup**: Not required (tasks are ephemeral)

**Queue Structure**:
```json
{
  "task_id": "456e7890-e89b-12d3-a456-426614174000",
  "task_type": "medication_reminder",
  "priority": "high",
  "payload": {"user_id": "...", "message": "..."},
  "created_at": "2025-09-01T12:00:00Z",
  "retry_count": 0
}
```

## Dependencies

### Internal Services
- **Audit Service** (8084): Task execution audit logging
- **Notification Service**: Delivery of healthcare notifications
- **User Service** (8088): User preference and contact information

### External Dependencies
- **Redis**: Task queue storage and management
- **SMTP Service**: Email notification delivery
- **SMS Gateway**: Text message delivery

**Service Call Graph**:
```
background-tasks:8086
  ├── redis:6379 (task queues)
  ├── audit-logging:8084 (task audit)
  ├── notification-service (delivery)
  └── smtp-gateway (email delivery)
```

## Run & Test

### Local Development

```bash
# Prerequisites
make infrastructure  # Start Redis

# Environment setup
export PORT=8086
export REDIS_URL="redis://localhost:6379"
export WORKER_COUNT=3

# Start service
go run main.go
```

### Testing

```bash
# Unit tests
go test ./... -v

# Queue processing tests
go test ./... -tags=queue -v

# Notification tests
go test ./... -tags=notification -v

# Load testing
go test ./... -bench=BenchmarkTaskProcessing
```

### Test Tasks

```bash
# Submit test task
curl -X POST http://localhost:8086/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "test_notification",
    "priority": "normal",
    "payload": {"message": "Test notification"}
  }'

# Check task status
curl http://localhost:8086/api/v1/tasks/{task_id}/status
```

## Deploy

### Docker

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o background-tasks .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/background-tasks .
EXPOSE 8086
CMD ["./background-tasks"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: background-tasks
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: background-tasks
        image: background-tasks:latest
        ports:
        - containerPort: 8086
        env:
        - name: WORKER_COUNT
          value: "5"
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: cache-secrets
              key: redis-url
```

## Observability

### Logging

**Task Processing Logs**:
```json
{
  "timestamp": "2025-09-01T12:00:00Z",
  "level": "info",
  "service": "background-tasks",
  "event": "task_completed",
  "task_id": "456e7890-e89b-12d3-a456-426614174000",
  "task_type": "medication_reminder",
  "duration_ms": 1250,
  "retry_count": 0
}
```

### Metrics

**Task Processing KPIs**:
- `tasks_processed_total` - Total tasks processed
- `task_processing_duration_seconds` - Task processing time
- `task_queue_size` - Current queue depth
- `task_failures_total` - Failed task count

### Alerts

**Operational Alerts**:
- Queue depth >1000 tasks (15-minute SLA)
- Task failure rate >5% (10-minute SLA)
- Notification delivery failures (5-minute SLA)

## Security

### Task Security

**Access Control**:
- Task submission requires service authentication
- Task payloads encrypted in transit
- Sensitive task data not logged

**Queue Security**:
```go
// Secure task processing with audit logging
func (t *TaskProcessor) processTask(task Task) error {
    // Audit task start
    t.auditClient.LogEvent(AuditEvent{
        EventType: "background_task_started",
        TaskID: task.ID,
        TaskType: task.Type,
        Priority: task.Priority,
    })
    
    // Process with timeout
    ctx, cancel := context.WithTimeout(context.Background(), 
        time.Duration(task.TimeoutSeconds)*time.Second)
    defer cancel()
    
    err := t.executeTask(ctx, task)
    
    // Audit completion
    t.auditClient.LogEvent(AuditEvent{
        EventType: "background_task_completed",
        TaskID: task.ID,
        Success: err == nil,
        ErrorMessage: errorString(err),
    })
    
    return err
}
```

## Troubleshooting

### Common Issues

**Issue**: Tasks stuck in queue
**Resolution**: Check worker process health and Redis connectivity

**Issue**: Notification delivery failures
**Resolution**: Verify external notification service credentials and connectivity

**Issue**: High memory usage
**Resolution**: Optimize task payload sizes and worker count configuration

### Playbook Links

- **[Task Processing Issues](../../docs/operations/Runbooks.md#background-tasks)**
- **[Notification Failures](../../docs/operations/Runbooks.md#notification-issues)**

---

**Service Version**: 1.0.0  
**Task Processing**: ✅ Async healthcare workflows  
**Notification Delivery**: ✅ Multi-channel care alerts