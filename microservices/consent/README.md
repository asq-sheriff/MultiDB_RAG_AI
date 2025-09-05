# Go Consent Service

A high-performance, HIPAA-compliant consent management microservice built in Go for the MultiDB-Chatbot healthcare platform.

## 🚀 Overview

The Go Consent Service provides secure, efficient consent-based access control for protected health information (PHI). It serves as a critical component in the hybrid Python/Go architecture, handling consent validation, emergency access protocols, and comprehensive audit logging.

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│          Go Consent Service         │
├─────────────────────────────────────┤
│  • HIPAA-compliant consent logic    │
│  • Emergency access protocols       │
│  • Comprehensive audit logging      │  
│  • Rate limiting & security         │
│  • Redis caching layer              │
└─────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│         Data Layer                  │
├─────────────────────────────────────┤
│  • PostgreSQL (consent records)     │
│  • Redis (session & cache)          │ 
│  • Structured logging               │
└─────────────────────────────────────┘
```

## 🔐 Key Features

### HIPAA Compliance
- ✅ **Consent-based access control** - All PHI access requires explicit consent
- ✅ **Minimum necessary principle** - Access limited to required data types
- ✅ **Comprehensive audit logging** - All actions tracked with immutable logs
- ✅ **Emergency access protocols** - Break-glass access with mandatory justification
- ✅ **Data encryption in transit** - TLS encryption for all communications
- ✅ **Session management** - Secure user authentication and authorization

### High Performance
- ⚡ **Sub-millisecond consent validation** - Optimized for healthcare workflows
- ⚡ **Redis caching** - Hot consent data cached for instant access
- ⚡ **Database connection pooling** - Efficient PostgreSQL connections
- ⚡ **Concurrent request handling** - Go's goroutines for scalability
- ⚡ **Rate limiting** - Protection against abuse and DoS attacks

### Developer Experience  
- 🧪 **Comprehensive test suite** - Unit, integration, and benchmark tests
- 📊 **Prometheus metrics** - Detailed performance and health monitoring
- 🔍 **Structured logging** - JSON logs with correlation IDs
- 📚 **OpenAPI documentation** - Auto-generated API docs
- 🐳 **Docker support** - Containerized deployment ready

## 🛠️ API Endpoints

### Consent Management
```http
POST   /consents              # Create new consent
GET    /consents              # List consents (filtered)
GET    /consents/{id}         # Get specific consent
PUT    /consents/{id}         # Update consent
DELETE /consents/{id}         # Revoke consent
```

### Access Validation
```http
POST   /validate-access       # Validate data access request
POST   /emergency-access      # Request emergency access
GET    /access-decisions      # Get access decision history
```

### Monitoring & Health
```http
GET    /health               # Health check endpoint
GET    /metrics              # Prometheus metrics
GET    /ready                # Readiness probe
```

## 🧪 Testing

The Go Consent Service includes comprehensive testing integrated with the main project test suite.

### Run via Main Test Suite
```bash
# Run all Go service tests
python scripts/run_comprehensive_tests.py --category go-services

# Run with HIPAA compliance tests (includes Go tests)
python scripts/run_comprehensive_tests.py --category hipaa

# Run complete test suite (includes Go tests)
python scripts/run_comprehensive_tests.py --category all
```

### Run Go Tests Directly (when Go is installed)
```bash
# Option 1: Use dedicated script
./scripts/run_go_tests.sh

# Option 2: Run manually
cd services/consent-service-go
go test -v                    # Unit tests
go test -v -bench=.           # Benchmarks
go test -v -race              # Race detection
go test -v -tags=integration  # Integration tests
```

### Test Categories

#### Unit Tests
- ✅ Consent CRUD operations
- ✅ Access validation logic
- ✅ Emergency access protocols  
- ✅ Cache operations
- ✅ Input validation
- ✅ Error handling

#### Integration Tests  
- ✅ PostgreSQL database operations
- ✅ Redis caching integration
- ✅ HTTP endpoint functionality
- ✅ Authentication middleware
- ✅ Rate limiting enforcement
- ✅ Audit logging verification

#### Performance Tests
- ⚡ Consent validation benchmarks
- ⚡ Database query performance
- ⚡ Cache hit/miss ratios
- ⚡ Concurrent request handling
- ⚡ Memory usage optimization

## 🚀 Quick Start

### Prerequisites
- Go 1.21+
- PostgreSQL 13+ (running on localhost:5432)
- Redis 6+ (running on localhost:6379)
- Required environment variables:
  ```bash
  export POSTGRES_HOST=localhost
  export POSTGRES_PORT=5432
  export POSTGRES_USER=chatbot_user
  export POSTGRES_PASSWORD=secure_password
  export POSTGRES_DB=chatbot_app
  export REDIS_URL=redis://localhost:6379
  ```

### Installation & Running
```bash
# Install dependencies
cd services/consent-service-go
go mod download

# Run the service
go run .

# Or build and run
go build -o consent-service
./consent-service
```

The service will start on `http://localhost:8009` with the following endpoints available:
- Health check: `GET http://localhost:8009/health`
- API documentation: `GET http://localhost:8009/docs`

## 🔧 Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | HTTP server port | `8009` |
| `POSTGRES_HOST` | PostgreSQL hostname | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | Database user | `chatbot_user` |
| `POSTGRES_PASSWORD` | Database password | Required |
| `POSTGRES_DB` | Database name | `chatbot_app` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `LOG_LEVEL` | Logging level | `info` |
| `TESTING` | Enable test mode | `false` |

### HIPAA Configuration
- **Consent TTL**: 1 year (configurable)
- **Emergency access window**: 72 hours
- **Audit log retention**: 6 years  
- **Session timeout**: 30 minutes
- **Rate limiting**: 100 requests/minute per user

## 📊 Integration with Main Project

The Go Consent Service seamlessly integrates with the existing Python-based MultiDB-Chatbot platform:

### Service Discovery
- Registered with main test suite health checks
- Monitored by comprehensive test runner
- Included in startup automation scripts

### Database Integration
- Shares PostgreSQL database with Python services
- Uses dedicated consent-related tables
- Maintains referential integrity across services

### Security Integration
- Participates in unified HIPAA compliance testing
- Shares Redis session storage with Python services
- Follows consistent audit logging patterns

### Testing Integration
- Included in CI/CD pipeline via Python test runner
- HIPAA compliance tests include Go service validation
- Performance benchmarks integrated with main metrics

## 🏥 HIPAA Compliance Details

### Access Control Implementation
```go
func (db *PostgresDB) checkDataAccess(params CheckDataAccessParams) (*AccessDecision, error) {
    // 1. Check self-access (patient accessing own data)
    if params.UserID == params.PatientID {
        return &AccessDecision{Allowed: true, Reason: "Self-access"}, nil
    }
    
    // 2. Check emergency access protocols
    if params.IsEmergency {
        return db.handleEmergencyAccess(params)
    }
    
    // 3. Validate explicit consent
    return db.validateConsent(params)
}
```

### Audit Logging
- **What**: All consent operations and data access requests
- **When**: Real-time with microsecond precision
- **Who**: User ID, role, and authentication context  
- **Where**: Immutable PostgreSQL audit table
- **Why**: Purpose of data access and legal basis

### Data Encryption
- **In Transit**: TLS 1.3 for all communications
- **At Rest**: PostgreSQL transparent data encryption
- **In Memory**: Sensitive data cleared after use
- **Caching**: Encrypted Redis storage with TTL

## 🤝 Contributing

### Development Workflow
1. **Setup**: Follow quick start guide
2. **Testing**: Run `go test -v` before committing
3. **Linting**: Use `golangci-lint` for code quality
4. **Integration**: Test with Python services using comprehensive test suite

### Code Standards
- Follow Go best practices and idioms
- Maintain >90% test coverage
- Include benchmarks for performance-critical code
- Document all exported functions and types
- Use structured logging with correlation IDs

## 📞 Support & Documentation

- **Main Project**: [MultiDB-Chatbot README](../../README.md)
- **API Documentation**: Available at `/docs` endpoint when service is running
- **Test Results**: Included in comprehensive test suite reports
- **Performance Metrics**: Available at `/metrics` endpoint

## 🎯 Roadmap

- [ ] **gRPC API**: High-performance binary protocol option  
- [ ] **GraphQL Gateway**: Integration with GraphQL federation
- [ ] **WebSocket Support**: Real-time consent status updates
- [ ] **Machine Learning**: Anomaly detection for consent patterns
- [ ] **Multi-tenancy**: Support for multiple healthcare organizations

---

**🏥 Built for Healthcare. Optimized for Performance. Designed for Compliance.**