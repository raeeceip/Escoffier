# Monorepo Structure

## Overview

MasterChef-Bench is structured as a monorepo containing both the backend Go application and the frontend React application. This structure allows for easier development, testing, and deployment of the entire application as a cohesive unit.

## Package Structure

The repository is organized as follows:

```
masterchef-bench/
├── .github/workflows/    # GitHub Actions CI/CD workflows
├── backend/              # Backend services and APIs
├── cli/                  # Command-line interface for the platform
├── cmd/                  # Application entry points
├── configs/              # Configuration files
├── data/                 # Data files and storage
├── docs/                 # Documentation
├── frontend/             # React-based web UI
├── guides/               # User and developer guides
├── internal/             # Private application code
│   ├── agents/           # Agent implementations
│   ├── api/              # API handlers
│   ├── database/         # Database access layer
│   ├── evaluation/       # Evaluation system
│   ├── models/           # Data models
│   ├── monitoring/       # Metrics and monitoring
│   ├── playground/       # LLM Playground implementation
│   └── tests/            # Internal tests
└── web/                  # Static web files (for Playground)
    ├── static/           # CSS, JS, and other static assets
    └── templates/        # HTML templates
```

## Key Components

### Backend

- **cmd/main.go**: Entry point for the application
- **internal/playground/**: LLM Playground implementation
- **internal/evaluation/**: LLM evaluation system
- **internal/monitoring/**: Metrics collection and reporting
- **internal/models/**: Model registry and data structures

### Frontend

- **frontend/**: React application
  - **src/components/**: React components including LLMPlayground
  - **package.json**: Frontend dependencies and scripts

### CLI

- **cli/main.go**: CLI application for controlling the platform

### Web

- **web/templates/playground.html**: HTML template for the non-React Playground UI
- **web/static/**: Static assets for the Playground UI

## Development Workflow

1. Use GitHub Actions for CI/CD

   - Run Go tests
   - Test and build the frontend
   - Build Docker images

2. Local Development
   - Run backend: `go run cmd/main.go`
   - Run frontend: `cd frontend && npm start`
   - Use CLI: `go run cli/main.go`

## Testing

- Go tests: `go test ./internal/monitoring ./internal/evaluation ./internal/playground`
- Frontend tests: `cd frontend && npm test`

## Deployment

The application can be deployed using Docker:

```bash
docker build -t masterchef-bench .
docker run -p 8080:8080 -p 8090:8090 masterchef-bench
```
