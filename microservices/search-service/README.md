---
title: Search Service (Go)
owner: Platform Team
last_updated: 2025-09-01
status: authoritative
---

# Search Service (Go)

> **High-performance business search operations and metadata queries**

## Purpose & Responsibilities

• **Business Search**: Handle non-AI search operations for user data and system metadata
• **Query Routing**: Route search requests to appropriate data stores based on query type
• **Search Indexing**: Maintain search indexes for user profiles and system data
• **Search Analytics**: Track search patterns and performance metrics
• **Access Control**: Enforce search permissions based on user roles and relationships
• **Cache Management**: Optimize search performance with intelligent caching

**Service Level Objectives (SLO)**:
- Response time: <200ms (95th percentile)
- Availability: 99.5% uptime
- Search accuracy: >90% relevance

**In Scope**: Business data search, metadata queries, search performance optimization
**Out of Scope**: AI-powered semantic search, content generation, PHI content search

## APIs

### Business Search

```http
POST /api/v1/search/query
Content-Type: application/json
Authorization: Bearer <user-token>
```

**Request**:
```json
{
  "query": "care staff wellness reports",
  "search_type": "business_data",
  "filters": {
    "data_type": "reports",
    "date_range": "last_30_days",
    "organization_id": "456e7890-e89b-12d3-a456-426614174000"
  },
  "pagination": {
    "page": 1,
    "limit": 20
  }
}
```

**Response**:
```json
{
  "search_id": "789e0123-e89b-12d3-a456-426614174000",
  "query": "care staff wellness reports",
  "total_results": 45,
  "page": 1,
  "results": [
    {
      "id": "abc12345-e89b-12d3-a456-426614174000",
      "title": "Weekly Wellness Report - Care Unit A",
      "type": "wellness_report",
      "created_at": "2025-08-25T10:00:00Z",
      "relevance_score": 0.92
    }
  ],
  "search_time_ms": 125
}
```

### Metadata Search

```http
GET /api/v1/search/metadata?type={type}&organization={org_id}
Authorization: Bearer <admin-token>
```

**Error Codes**:
- `400` - Invalid search query format
- `401` - Unauthorized search access
- `403` - Search permissions denied
- `404` - No search results found
- `500` - Search service failure

## Config

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PORT` | `8089` | No | Service port |
| `MONGO_URL` | - | Yes | MongoDB connection string |
| `POSTGRES_URL` | - | Yes | PostgreSQL connection string |
| `SEARCH_INDEX_SIZE` | `10000` | No | Maximum search index size |
| `CACHE_TTL_SECONDS` | `3600` | No | Search result cache TTL |

**Security Considerations**:
```bash
# Production security settings
MONGO_URL="${SECRET_MANAGER_MONGO_URL}"
POSTGRES_URL="${SECRET_MANAGER_DB_URL}" 
SEARCH_ENCRYPTION_KEY="${SECRET_MANAGER_SEARCH_KEY}"
```

## Datastores

### MongoDB Collections

**Search Collections**: `business_documents`, `system_metadata`, `search_indexes`
- **PII/PHI**: Business metadata only (no clinical PHI)
- **Retention**: Business documents 3 years, metadata permanent
- **Backup**: Daily backups with search index reconstruction

**Document Structure**:
```javascript
{
  "_id": ObjectId("..."),
  "document_type": "wellness_report",
  "organization_id": "456e7890-e89b-12d3-a456-426614174000",
  "title": "Weekly Wellness Report",
  "content_summary": "Care staff wellness metrics and feedback",
  "searchable_fields": ["title", "tags", "organization"],
  "access_permissions": ["care_staff", "administrators"],
  "created_at": ISODate("2025-09-01T12:00:00Z")
}
```

### PostgreSQL Indexes

**Search Metadata**: Stored in `search_metadata` table for relational queries
- **Indexes**: Full-text search on titles and descriptions
- **Performance**: GIN indexes for JSONB search criteria

## Dependencies

### Internal Services
- **Auth Service** (8080): User role and permission validation
- **Relationship Service** (8087): Relationship-based search authorization

### External Dependencies
- **MongoDB**: Primary search document storage
- **PostgreSQL**: Search metadata and permissions
- **Elasticsearch** (future): Advanced full-text search capabilities

**Service Call Graph**:
```
search-service:8089
  ├── auth-rbac:8080 (user permissions)
  ├── relationship-management:8087 (access authorization)
  ├── mongodb:27017 (search documents)
  └── postgresql:5432 (search metadata)
```

## Run & Test

### Local Development

```bash
# Prerequisites
make infrastructure  # Start MongoDB and PostgreSQL

# Environment setup
export PORT=8089
export MONGO_URL="mongodb://root:example@localhost:27018/chatbot_app?authSource=admin"
export POSTGRES_URL="postgresql://chatbot_user:${POSTGRES_PASSWORD}@localhost:5433/chatbot_app"

# Start service
go run main.go
```

### Testing

```bash
# Unit tests
go test ./... -v

# Search functionality tests
go test ./... -tags=search -v

# Performance tests
go test ./... -bench=BenchmarkSearch

# Integration tests
go test ./... -tags=integration -v
```

### Test Searches

```bash
# Test business document search
curl -X POST http://localhost:8089/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wellness reports",
    "search_type": "business_data",
    "filters": {"data_type": "reports"}
  }'

# Test metadata search
curl "http://localhost:8089/api/v1/search/metadata?type=reports&organization=test-org"
```

## Deploy

### Docker

```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o search-service .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/search-service .
EXPOSE 8089
CMD ["./search-service"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: search-service
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: search-service
        image: search-service:latest
        ports:
        - containerPort: 8089
        env:
        - name: MONGO_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: mongo-url
        - name: SEARCH_INDEX_SIZE
          value: "10000"
```

## Observability

### Logging

**Search Event Logs**:
```json
{
  "timestamp": "2025-09-01T12:00:00Z",
  "level": "info",
  "service": "search-service",
  "event": "search_executed",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "query": "wellness reports",
  "results_count": 15,
  "search_time_ms": 125
}
```

### Metrics

**Search Performance KPIs**:
- `search_queries_total` - Total search requests
- `search_response_time_seconds` - Search latency histogram
- `search_cache_hits` - Cache performance
- `search_results_count` - Result set size distribution

### Alerts

**Search Alerts**:
- Search response time >500ms (10-minute SLA)
- Search index corruption (immediate escalation)
- Cache performance degradation (30-minute SLA)

## Security

### Search Security

**Access Control**:
- Search results filtered by user permissions
- Business data requires organization membership
- Administrative searches require admin role

**Search Privacy**:
```go
// Privacy-preserving search with access control
func (s *SearchService) executeSearch(userID string, query SearchQuery) (*SearchResults, error) {
    // Get user permissions
    permissions, err := s.authClient.GetUserPermissions(userID)
    if err != nil {
        return nil, fmt.Errorf("failed to get user permissions: %w", err)
    }
    
    // Filter search scope based on permissions
    filteredQuery := s.applyPermissionFilters(query, permissions)
    
    // Execute search with privacy filtering
    results, err := s.mongodb.Search(filteredQuery)
    if err != nil {
        return nil, fmt.Errorf("search execution failed: %w", err)
    }
    
    // Remove unauthorized fields from results
    sanitizedResults := s.sanitizeResults(results, permissions)
    
    // Audit search operation
    s.auditClient.LogSearchEvent(userID, query, len(sanitizedResults))
    
    return sanitizedResults, nil
}
```

## Troubleshooting

### Common Issues

**Issue**: Slow search performance
**Resolution**: Check MongoDB indexes and optimize search queries

**Issue**: No search results for valid queries
**Resolution**: Verify search index integrity and data synchronization

**Issue**: Permission denied errors
**Resolution**: Check user role assignments and relationship verifications

### Playbook Links

- **[Search Performance](../../docs/operations/Runbooks.md#search-performance)**
- **[Index Management](../../docs/operations/Runbooks.md#search-indexes)**

---

**Service Version**: 1.0.0  
**Search Performance**: ✅ <200ms average response time  
**Access Control**: ✅ Permission-based search filtering