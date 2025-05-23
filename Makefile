
# MasterChef-Bench Makefile

.PHONY: help build test clean dev start stop frontend backend cli docker setup verify

# Default target
help: ## Show this help message
	@echo "MasterChef-Bench Build System"
	@echo "========================="
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Setup targets
setup: install-deps setup-env ## Complete setup for local development
	@echo "Setting up MasterChef-Bench..."
	@mkdir -p data grafana/provisioning/datasources grafana/provisioning/dashboards grafana/dashboards
	@cp .env.example .env 2>/dev/null || echo ".env file already exists"
	@echo "Setup complete! Edit .env file with your API keys"

setup-env: ## Create .env file from example
	@cp .env.example .env 2>/dev/null || echo ".env file already exists"
	@echo "Created .env file. Please edit it with your API keys."

verify: ## Verify system setup
	@chmod +x verify.sh
	@./verify.sh

# Build targets
build: backend cli frontend ## Build all components

backend: ## Build the backend API server
	@echo "Building backend..."
	@go build -o bin/masterchef-bench ./cmd/main.go

cli: ## Build the CLI client
	@echo "Building CLI..."
	@cd cli && go build -o ../bin/masterchef-cli main.go client.go

frontend: ## Build the frontend
	@echo "Building frontend..."
	@cd frontend && npm ci && npm run build

# Development targets
dev: ## Start development environment (interactive menu)
	@chmod +x dev.sh
	@./dev.sh

start: docker-run ## Start all services in production mode

start-local: ## Start all services locally (no Docker)
	@echo "Starting services locally..."
	@./start-all.sh

stop-local: ## Stop all local services
	@echo "Stopping services..."
	@./stop-all.sh

backend-dev: ## Start backend in development mode (standalone)
	@echo "Starting backend in development mode..."
	@go run cmd/main.go

frontend-dev: ## Start frontend development server (standalone)
	@echo "Starting frontend development server..."
	@cd frontend && npm start

# Test targets
test: test-go test-frontend ## Run all tests

test-go: ## Run Go tests
	@echo "Running Go tests..."
	@go test -v -race -coverprofile=coverage.txt -covermode=atomic ./...

test-frontend: ## Run frontend tests
	@echo "Running frontend tests..."
	@cd frontend && npm test -- --watchAll=false

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	@go test -v -tags=integration ./tests/...

# Quality targets
lint: lint-go lint-frontend ## Run all linters

lint-go: ## Run Go linter
	@echo "Running Go linter..."
	@golangci-lint run --timeout=10m || go vet ./...

lint-frontend: ## Run frontend linter
	@echo "Running frontend linter..."
	@cd frontend && npm run lint

fmt: ## Format all code
	@echo "Formatting Go code..."
	@go fmt ./...
	@goimports -w .
	@echo "Formatting frontend code..."
	@cd frontend && npm run lint:fix 2>/dev/null || true

# Docker targets
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	@docker build -t masterchef-bench:latest .

docker-run: ## Run with Docker Compose
	@echo "Starting with Docker Compose..."
	@docker-compose up -d
	@echo "Services started! Access:"
	@echo "  - API: http://localhost:8080"
	@echo "  - Playground: http://localhost:8090"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"

docker-stop: ## Stop Docker Compose
	@docker-compose down

docker-logs: ## Show Docker logs
	@docker-compose logs -f

docker-clean: docker-stop ## Clean Docker resources
	@docker-compose down -v
	@docker rmi masterchef-bench:latest 2>/dev/null || true

# Database targets
db-init: ## Initialize database
	@echo "Initializing database..."
	@psql -h localhost -U masterchef -d masterchef -f init.sql || echo "Using SQLite fallback"

db-reset: ## Reset database (WARNING: Deletes all data!)
	@echo "Resetting database..."
	@rm -f data/*.db
	@docker-compose exec postgres psql -U masterchef -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null || true

db-migrate: ## Run database migrations
	@echo "Running migrations..."
	@go run ./internal/database/migrate.go

# Cleanup targets
clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@rm -rf bin/
	@rm -rf frontend/build
	@rm -rf frontend/node_modules/.cache
	@rm -f coverage.txt

clean-all: clean clean-data ## Clean everything (WARNING: Deletes all data!)
	@rm -rf node_modules
	@rm -rf frontend/node_modules
	@rm -rf data/

clean-data: ## Clean database files (WARNING: Deletes all data!)
	@echo "Cleaning database files..."
	@rm -f data/*.db
	@rm -f *.db

# Installation targets
install-deps: ## Install all dependencies
	@echo "Installing Go dependencies..."
	@go mod download
	@go mod tidy
	@echo "Installing frontend dependencies..."
	@cd frontend && npm ci

install-tools: ## Install required tools
	@echo "Installing development tools..."
	@go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	@go install golang.org/x/tools/cmd/goimports@latest
	@go install github.com/cosmtrek/air@latest

# Monitoring targets
logs: ## Show application logs
	@echo "Showing logs..."
	@tail -f logs/*.log 2>/dev/null || echo "No log files found"

metrics: ## Open metrics dashboard
	@echo "Opening Prometheus metrics..."
	@open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 2>/dev/null || echo "Open http://localhost:9090"

grafana: ## Open Grafana dashboard
	@echo "Opening Grafana..."
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Open http://localhost:3000 (admin/admin)"

# Utility targets
version: ## Show version info
	@echo "MasterChef-Bench v1.0.0"
	@echo "Go version: $(shell go version)"
	@echo "Node version: $(shell node --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker version: $(shell docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Git commit: $(shell git rev-parse --short HEAD 2>/dev/null || echo 'Not in git repo')"

health: ## Check service health
	@echo "Checking service health..."
	@curl -s http://localhost:8080/health | jq . 2>/dev/null || echo "API not running"
	@curl -s http://localhost:9090/-/healthy 2>/dev/null && echo "Prometheus: OK" || echo "Prometheus: Not running"
	@curl -s http://localhost:3000/api/health 2>/dev/null && echo "Grafana: OK" || echo "Grafana: Not running"

# Quick start commands
quickstart: setup start-local ## Quick start for local development
	@echo ""
	@echo "MasterChef-Bench is starting up!"
	@echo "Services are running locally."

quickstart-docker: setup docker-run ## Quick start with Docker
	@echo ""
	@echo "MasterChef-Bench is starting up with Docker!"
	@echo "Wait a few seconds for services to initialize..."
	@sleep 5
	@make health
	@echo ""
	@echo "Access the services at:"
	@echo "  - API: http://localhost:8080"
	@echo "  - Playground: http://localhost:8090"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"

run: start-local ## Alias for start-local
stop: stop-local ## Alias for stop-local