# MasterChef-Bench Makefile

.PHONY: help build test clean dev start stop frontend backend cli docker

# Default target
help: ## Show this help message
	@echo "MasterChef-Bench Build System"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Build targets
build: backend cli frontend ## Build all components

backend: ## Build the backend API server
	@echo "Building backend..."
	@go build -o cmd/masterchef cmd/main.go

cli: ## Build the CLI client
	@echo "Building CLI..."
	@cd cli && go build -o cli main.go client.go

frontend: ## Build the frontend
	@echo "Building frontend..."
	@cd frontend && npm ci && npm run build

# Development targets
dev: ## Start development environment (interactive menu)
	@chmod +x dev.sh
	@./dev.sh

start: ## Start all services in production mode
	@chmod +x start-all.sh
	@./start-all.sh

backend-dev: ## Start backend in development mode
	@echo "Starting backend in development mode..."
	@go run cmd/main.go --port=8080 --playground-port=8090 --metrics-port=9090

frontend-dev: ## Start frontend development server
	@echo "Starting frontend development server..."
	@cd frontend && npm start

# Test targets
test: test-go test-frontend ## Run all tests

test-go: ## Run Go tests
	@echo "Running Go tests..."
	@go test -v ./internal/...

test-frontend: ## Run frontend tests
	@echo "Running frontend tests..."
	@cd frontend && npm test -- --watchAll=false

# Quality targets
lint: ## Run linters
	@echo "Running Go linter..."
	@go vet ./...
	@echo "Running frontend linter..."
	@cd frontend && npm run lint

fmt: ## Format code
	@echo "Formatting Go code..."
	@go fmt ./...
	@echo "Formatting frontend code..."
	@cd frontend && npm run lint:fix

# Cleanup targets
clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@rm -f cmd/masterchef
	@rm -f cli/cli
	@rm -rf frontend/build
	@rm -rf frontend/node_modules/.cache

clean-data: ## Clean database files (WARNING: This removes all data!)
	@echo "Cleaning database files..."
	@rm -f data/*.db
	@rm -f *.db

# Docker targets
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	@docker build -t masterchef-bench .

docker-run: ## Run with Docker Compose
	@echo "Starting with Docker Compose..."
	@docker-compose up --build

docker-stop: ## Stop Docker Compose
	@docker-compose down

# Installation targets
install-deps: ## Install all dependencies
	@echo "Installing Go dependencies..."
	@go mod download
	@echo "Installing frontend dependencies..."
	@cd frontend && npm ci

install-dev-tools: ## Install development tools
	@echo "Installing development tools..."
	@go install github.com/cosmtrek/air@latest
	@go install golang.org/x/tools/cmd/goimports@latest

# Database targets
db-reset: ## Reset database (recreate schema)
	@echo "Resetting database..."
	@rm -f data/*.db
	@go run cmd/main.go --init-db-only

# Monitoring targets
logs: ## Show application logs
	@echo "Showing logs..."
	@tail -f logs/*.log || echo "No log files found"

metrics: ## Open metrics dashboard
	@echo "Opening metrics at http://localhost:9090/metrics"
	@open http://localhost:9090/metrics || echo "Open http://localhost:9090/metrics in your browser"

# Release targets
version: ## Show version info
	@echo "MasterChef-Bench"
	@echo "Go version: $(shell go version)"
	@echo "Node version: $(shell node --version)"
	@echo "Git commit: $(shell git rev-parse --short HEAD)"

release: clean build test ## Prepare release build
	@echo "Release build complete"