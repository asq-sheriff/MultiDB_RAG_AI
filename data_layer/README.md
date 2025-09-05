# 📊 Unified Data Layer

This directory provides a unified abstraction layer for all database interactions across the MultiDB-Chatbot system.

## Directory Structure

### Database Models
- **`models/postgres/`** - PostgreSQL/SQLAlchemy models
- **`models/mongodb/`** - MongoDB/Motor document models  
- **`models/redis/`** - Redis data structures and caching models
- **`models/scylla/`** - ScyllaDB/Cassandra models for high-throughput data

### Database Connections
- **`connections/`** - Database connection managers and pools
  - Connection pooling and lifecycle management
  - Health checking and failover logic
  - Configuration management per database

### Database Migrations
- **`migrations/`** - Database schema migrations and versioning
  - Alembic migrations for PostgreSQL
  - MongoDB schema evolution scripts
  - ScyllaDB keyspace and table management

### Data Access Patterns
- **`repositories/`** - Repository pattern implementations
  - Generic CRUD operations
  - Complex query builders
  - Cross-database transaction management

## Database Usage by Component

### PostgreSQL (Primary OLTP)
**Used by**: Go microservices, Python auth/billing
**Data Types**: 
- User accounts and authentication
- Billing and subscription data
- HIPAA audit logs
- Patient relationships and consent
- Configuration and metadata

### MongoDB (Document Store + Vector Search)
**Used by**: AI services, RAG pipeline
**Data Types**:
- Document chunks and embeddings (pgvector alternative)
- Chat conversations and history
- Therapeutic content and playbooks  
- Patient interaction logs
- AI model responses and feedback

### Redis (High-Speed Cache)
**Used by**: All services for caching
**Data Types**:
- Embedding cache (BGE vectors)
- Generation cache (LLM responses)
- Session data and JWT tokens
- Rate limiting counters
- Real-time analytics

### ScyllaDB (High-Throughput Analytics)
**Used by**: Analytics, monitoring, logging
**Data Types**:
- Time-series metrics and events
- Chat message archives
- Performance and usage analytics
- Large-scale logging data
- Historical reporting data

## Connection Management

### Connection Pooling
- **PostgreSQL**: SQLAlchemy async pools (5-20 connections)
- **MongoDB**: Motor connection pools (10-50 connections)  
- **Redis**: Redis-py connection pools (5-25 connections)
- **ScyllaDB**: Cassandra driver pools (3-10 connections)

### Health Checking
Each connection manager provides:
- Health check endpoints
- Connection retry logic with exponential backoff
- Circuit breaker patterns for failed connections
- Graceful degradation when databases are unavailable

### Configuration
- Environment-based configuration
- Secret management integration
- Connection string validation
- Pool size auto-tuning based on load

## Repository Patterns

### Generic Repository Interface
```python
class Repository[T]:
    async def create(entity: T) -> T
    async def get(id: str) -> T | None
    async def update(id: str, updates: dict) -> T | None
    async def delete(id: str) -> bool
    async def list(filters: dict = None, limit: int = 100) -> List[T]
```

### Database-Specific Extensions
Each database type extends the base repository with:
- Custom query builders
- Database-specific optimizations
- Transaction management
- Bulk operations

## Data Consistency

### Cross-Database Transactions
- **Saga Pattern** - For multi-database operations
- **Event Sourcing** - For audit trail requirements
- **Eventual Consistency** - For non-critical cross-DB updates

### Data Synchronization
- **Change Data Capture** - PostgreSQL -> other systems
- **Event Bus** - For real-time updates
- **Batch Sync** - For large data migrations

## Performance Optimization

### Query Optimization
- Connection pooling with optimal pool sizes
- Query result caching for frequently accessed data
- Index optimization and monitoring
- Query performance profiling

### Caching Strategy  
- **L1 Cache**: In-memory application cache
- **L2 Cache**: Redis distributed cache
- **L3 Cache**: Database query result cache
- Cache invalidation strategies

## HIPAA Compliance

### Data Protection
- Encryption at rest and in transit
- PHI data masking and tokenization
- Access logging for all database operations
- Data retention and deletion policies

### Audit Requirements
- Complete audit trail for all PHI access
- User action logging with timestamps
- Change tracking for sensitive data
- Compliance reporting and monitoring

## Development Guidelines

1. **Use Repository Pattern** - Never access databases directly
2. **Async Operations** - All database operations should be async
3. **Connection Management** - Always use connection managers
4. **Error Handling** - Implement retry logic and graceful degradation
5. **Testing** - Include integration tests with real databases
6. **Documentation** - Document all models and relationships

---
# Addendum (v2) — Unified Data Layer
*Appended on 2025-09-03. Original content preserved above.*

## Rights Metadata Storage
- Table/collection `media_assets`: `uri`, `source`, `license`, `expires_at`, `hash`.
- Nightly job `media_rights_prune` disables/removes expired assets and updates dependent records.

## Retention Policies
- PHI access logs: retain **6 years** (HIPAA).
- Analytics events: retain **13 months** (configurable).

## Change Data Capture (CDC) to Analytics
- Emit sanitized `ce.*` events (no PHI) to analytics store (e.g., ScyllaDB) via CDC.
- Strip PHI fields before export; keep a mapping of redactions for audit.
