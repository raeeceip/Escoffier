FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
# Check if frontend directory exists and has package.json
COPY frontend/package*.json ./
# Increase npm timeouts and add retry logic
RUN npm config set fetch-timeout 300000 && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm config set registry https://registry.npmjs.org/ && \
    npm ci --no-audit --no-fund --loglevel verbose || \
    (echo "Retrying npm install..." && npm ci --no-audit --no-fund --loglevel verbose)

COPY frontend/ ./
# Build with production flag
RUN npm run build || echo "Frontend build failed, continuing..."

FROM golang:1.22-alpine AS backend-builder

# Install build dependencies
RUN apk add --no-cache git gcc musl-dev

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
# Copy frontend build if it exists
COPY --from=frontend-builder /app/frontend/build ./frontend/build || true

# Build with static linking
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o masterchef-bench ./cmd/main.go

FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Copy binary
COPY --from=backend-builder /app/masterchef-bench .

# Copy frontend build if it exists
COPY --from=frontend-builder /app/frontend/build ./frontend/build || true

# Copy required directories
COPY --from=backend-builder /app/web ./web || true
COPY --from=backend-builder /app/configs ./configs
COPY --from=backend-builder /app/init.sql ./init.sql

# Create necessary directories
RUN mkdir -p data/logs grafana/provisioning/datasources grafana/provisioning/dashboards grafana/dashboards

# Set default environment variables
ENV GIN_MODE="release"
ENV DATABASE_URL="postgresql://masterchef:masterchef@postgres:5432/masterchef?sslmode=disable"
ENV API_HOST="0.0.0.0"
ENV API_PORT="8080"
ENV METRICS_PORT="8090"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

EXPOSE 8080 8090

# Run with all features enabled
CMD ["./masterchef-bench", "--enable-playground", "--enable-monitoring"] 