# 🐹 Go Microservices

This directory contains all Go-based microservices for the MultiDB-Chatbot system.

## Services Overview

### Core Business Services
- **`auth-rbac/`** - Authentication and Role-Based Access Control
- **`billing/`** - Billing and Subscription Management  
- **`user-subscription/`** - User Subscription Lifecycle
- **`relationship-management/`** - Patient Relationship Management

### System Services
- **`api-gateway/`** - API Gateway and Request Routing
- **`audit-logging/`** - HIPAA-Compliant Audit Logging
- **`chat-history/`** - Chat History and Conversation Storage
- **`background-tasks/`** - Background Task Processing

### Healthcare Services
- **`consent/`** - HIPAA Consent Management
- **`emergency-access/`** - Emergency Access Protocols

### Shared Components
- **`shared/models/`** - Common Go data models
- **`shared/middleware/`** - Shared middleware components
- **`shared/database/`** - Database connection utilities
- **`shared/utils/`** - Common Go utilities

## Architecture Principles

1. **Service Independence** - Each service is self-contained
2. **Database Per Service** - Each service owns its data
3. **API-First Design** - REST APIs with OpenAPI specs
4. **HIPAA Compliance** - Built-in healthcare compliance
5. **Observability** - Comprehensive logging and metrics

## Development Guidelines

- Use Go modules for dependency management
- Follow Go naming conventions
- Include comprehensive tests (unit + integration)
- Implement health check endpoints
- Use structured logging
- Include Docker configurations

## Service Communication

Services communicate via:
- **HTTP REST APIs** - Primary communication method
- **Message Queues** - For async operations
- **Shared Database** - For reference data only

## Testing

Each service should include:
- Unit tests (`*_test.go`)
- Integration tests (with `+build integration` tag)
- Performance benchmarks
- Health check validation