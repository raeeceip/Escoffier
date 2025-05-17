FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM golang:1.22-alpine AS backend-builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
COPY --from=frontend-builder /app/frontend/build ./frontend/build

RUN go build -o masterchef-bench ./cmd/main.go

FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app
COPY --from=backend-builder /app/masterchef-bench .
COPY --from=frontend-builder /app/frontend/build ./frontend/build
COPY --from=backend-builder /app/web ./web
COPY --from=backend-builder /app/configs ./configs

# Create necessary directories
RUN mkdir -p data/logs

# Set environment variables for the API keys
# These will be overridden by environment variables in production
ENV OPENAI_API_KEY="your-openai-key"
ENV ANTHROPIC_API_KEY="your-anthropic-key"
ENV GOOGLE_API_KEY="your-google-key"
ENV GIN_MODE="release"

EXPOSE 8080 8090

CMD ["./masterchef-bench", "--enable-playground"] 