# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install git for module downloads
RUN apk add --no-cache git ca-certificates tzdata

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -ldflags '-extldflags "-static"' -o consent-service .

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata curl

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/consent-service .

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN chown -R appuser:appgroup /root/
USER appuser

# Expose port
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8083/health || exit 1

# Run the binary
CMD ["./consent-service"]