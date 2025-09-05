# Auth-RBAC Service

A comprehensive Go-based authentication and role-based access control service designed for healthcare applications with HIPAA compliance requirements.

## Features

- **JWT Authentication**: Secure token-based authentication with access and refresh tokens
- **Role-Based Access Control**: Healthcare-specific roles and permissions
- **HIPAA Compliance**: Comprehensive audit logging and access controls
- **Session Management**: Secure session tracking and management
- **Password Security**: Argon2 password hashing with strength validation
- **PostgreSQL Integration**: Full database persistence with connection pooling
- **RESTful API**: Complete REST API with comprehensive error handling

## Healthcare Roles

- **Resident**: Can access only their own data
- **Family Member**: Limited access to assigned family member's data
- **Health Plan Member**: Access to their own data with crisis escalation
- **Care Staff**: Access to assigned patients and crisis management
- **Case Manager**: Broader access for care coordination
- **Care Manager**: Supervisory access over care operations
- **Admin**: Full system access with audit requirements

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/verify` - Verify token validity
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/reset-password` - Password reset

### User Management
- `GET /api/v1/profile` - Get user profile
- `PUT /api/v1/profile` - Update user profile
- `POST /api/v1/change-password` - Change password
- `GET /api/v1/sessions` - Get user sessions
- `DELETE /api/v1/sessions/:session_id` - Delete session

### RBAC
- `GET /api/v1/rbac/permissions` - Get all permissions
- `GET /api/v1/rbac/roles` - Get all roles
- `POST /api/v1/rbac/check-permission` - Check user permission
- `POST /api/v1/rbac/check-access` - Comprehensive access check

### Admin (Admin/Care Manager only)
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/users/:user_id` - Get user details
- `PUT /api/v1/admin/users/:user_id` - Update user
- `DELETE /api/v1/admin/users/:user_id` - Delete user
- `GET /api/v1/admin/audit-logs` - Get audit logs
- `GET /api/v1/admin/stats` - Get service statistics

## Setup

### Prerequisites
- Go 1.21+
- PostgreSQL 13+
- Environment variables configured

### Environment Variables
```bash
PORT=8080
ENVIRONMENT=development
DATABASE_URL=postgresql://username:password@localhost:5432/database
JWT_SECRET=your-secret-key-here
ACCESS_TOKEN_DURATION=15m
REFRESH_TOKEN_DURATION=7d
JWT_ISSUER=auth-rbac-service
HIPAA_MODE=true
LOG_LEVEL=info
```

### Database Setup
1. Run migrations:
```bash
cd migrations
go run run_migrations.go
```

### Running the Service
```bash
go mod tidy
go run main.go
```

### Building for Production
```bash
go build -o auth-rbac-service main.go
./auth-rbac-service
```

## Testing

Run the comprehensive test suite:
```bash
go test ./...
```

Run RBAC-specific tests:
```bash
go test ./tests -v
```

## Architecture

### Core Components
- **Auth Package**: JWT management, password hashing, middleware
- **RBAC Package**: Role definitions, permission checking, access control
- **Database Package**: PostgreSQL connection, queries, migrations
- **Models Package**: Data structures and validation
- **Handlers Package**: HTTP request handlers

### Security Features
- Argon2 password hashing
- JWT with configurable expiration
- Session tracking and management
- Token blacklisting support
- Comprehensive audit logging
- Rate limiting ready endpoints
- CORS middleware included

### HIPAA Compliance
- Comprehensive audit trails
- Access purpose tracking
- Minimum necessary access principles
- Emergency access controls
- Session management
- User authentication logs

## Deployment

### Docker (Recommended)
```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o auth-rbac-service main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/auth-rbac-service .
CMD ["./auth-rbac-service"]
```

### Health Checks
- `GET /health` - Basic health check
- `GET /ready` - Comprehensive readiness check

## Integration

This service is designed to integrate with other microservices in the healthcare platform:
- API Gateway for routing and rate limiting
- User management services for profile data
- Care coordination services for patient assignments
- Billing services for subscription management

## Development

### Adding New Roles
1. Update `rbac/roles.go` with new role constants
2. Update `rbac/permissions.go` with role permissions
3. Update database constraints in migrations
4. Add tests in `tests/rbac_test.go`

### Adding New Permissions
1. Add permission constant in `rbac/permissions.go`
2. Update role permission mappings
3. Update access control logic
4. Add appropriate tests

## License

This service is part of a healthcare platform and follows HIPAA compliance requirements.