# Multi-stage build for User Subscription Service
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o user-subscription-service .

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates tzdata

# Create non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup appuser

# Set working directory
WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/user-subscription-service .

# Set ownership
RUN chown appuser:appgroup user-subscription-service

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8010/health || exit 1

# Run the service
CMD ["./user-subscription-service"]