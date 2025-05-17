# Build stage
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git gcc musl-dev

# Set working directory
WORKDIR /app

# Copy go mod and sum files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -o masterchef-bench ./cmd/main.go

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache ca-certificates curl

# Set working directory
WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/masterchef-bench .

# Copy configuration files
COPY configs/config.yaml /app/configs/
COPY prometheus.yml /app/
COPY grafana/provisioning /app/grafana/provisioning
COPY grafana/dashboards /app/grafana/dashboards

# Create necessary directories
RUN mkdir -p /app/data

# Set environment variables
ENV GIN_MODE=release

# Expose ports
EXPOSE 8080

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["./masterchef-bench"] 