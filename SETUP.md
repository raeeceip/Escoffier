# MasterChef-Bench Setup Guide

This guide will help you set up and run the MasterChef-Bench system with all its components.

## Prerequisites

- **Go 1.22+** - [Install Go](https://golang.org/doc/install)
- **Node.js 20+** - [Install Node.js](https://nodejs.org/)
- **Docker & Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)
- **Make** - Usually pre-installed on Unix systems
- **Git** - For cloning the repository

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/masterchef.git
cd masterchef
```

### 2. Set Up Environment

```bash
# Create environment file from example
make setup-env

# Edit .env file with your API keys
# You need at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY
nano .env
```

### 3. Run with Docker (Recommended)

```bash
# Quick start - sets up everything and starts services
make quickstart

# Or manually:
make setup          # Install dependencies and create directories
make docker-run     # Start all services with Docker Compose
```

### 4. Access the Services

- **API**: http://localhost:8080
- **LLM Playground**: http://localhost:8090
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Jaeger**: http://localhost:16686
- **pgAdmin**: http://localhost:5050 (optional, use `docker-compose --profile tools up`)

## Local Development Setup

### 1. Install Dependencies

```bash
# Install all dependencies
make install-deps

# Install development tools (optional)
make install-tools
```

### 2. Set Up Database

```bash
# Using PostgreSQL (requires running PostgreSQL)
psql -h localhost -U postgres -c "CREATE DATABASE masterchef;"
psql -h localhost -U postgres -d masterchef -f init.sql

# Or use SQLite (automatic fallback)
# Database will be created automatically in data/masterchef.db
```

### 3. Run Services Locally

```bash
# Start all services locally (3 terminals)
make start-local

# Or run individually:
make backend-dev    # Terminal 1: Backend API
make frontend-dev   # Terminal 2: Frontend
make monitoring-dev # Terminal 3: Prometheus (optional)
```

## API Keys Configuration

The system requires at least one LLM provider API key:

```bash
# .env file
OPENAI_API_KEY=sk-...         # For GPT models
ANTHROPIC_API_KEY=sk-ant-...  # For Claude models
GOOGLE_API_KEY=...            # For Gemini models
```

**Note**: Without API keys, the agent system will not function, but you can still explore the UI and monitoring.

## Building from Source

### Build All Components

```bash
make build
```

### Build Individual Components

```bash
make backend    # Build backend binary
make frontend   # Build frontend assets
make cli        # Build CLI tool
```

### Run Tests

```bash
make test       # Run all tests
make test-go    # Run Go tests only
make test-frontend # Run frontend tests only
```

## Common Operations

### Database Management

```bash
make db-init    # Initialize database schema
make db-reset   # Reset database (WARNING: Deletes all data!)
make db-migrate # Run migrations (if any)
```

### Monitoring

```bash
make logs       # View application logs
make metrics    # Open Prometheus metrics
make grafana    # Open Grafana dashboard
make health     # Check service health
```

### Cleaning Up

```bash
make clean      # Clean build artifacts
make clean-data # Clean database files (WARNING: Deletes data!)
make clean-all  # Clean everything
make docker-clean # Stop and remove Docker containers/images
```

## Troubleshooting

### Port Conflicts

If you get port binding errors, check for services using the required ports:

```bash
# Check what's using ports
lsof -i :8080  # API
lsof -i :8090  # Playground
lsof -i :3000  # Grafana
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :9090  # Prometheus
```

### Docker Issues

```bash
# View Docker logs
make docker-logs

# Restart services
make docker-stop
make docker-run

# Complete cleanup and restart
make docker-clean
make quickstart
```

### Frontend Build Issues

```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Database Connection Issues

1. Check if PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Verify connection:
   ```bash
   psql -h localhost -U masterchef -d masterchef
   ```

3. Fall back to SQLite:
   - The system automatically uses SQLite if PostgreSQL is unavailable
   - Database file: `data/masterchef.db`

## Configuration

### Main Configuration File

Edit `configs/config.yaml` for system configuration:

```yaml
database:
  type: "postgres"  # or "sqlite"
  url: "postgresql://masterchef:masterchef@localhost:5432/masterchef"

api:
  host: "0.0.0.0"
  port: 8080
  playground_port: 8090

agents:
  executive_chef:
    model: "gpt-4"
    temperature: 0.7
  # ... other agents
```

### Environment Variables

See `.env.example` for all available environment variables.

## Development Workflow

### 1. Make Changes

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Make your changes
# ...

# Format code
make fmt

# Run linter
make lint

# Run tests
make test
```

### 2. Test with Docker

```bash
# Build and run with Docker
make docker-build
make docker-run

# Check logs
make docker-logs
```

### 3. Verify Everything Works

```bash
# Run verification script
make verify

# Check service health
make health
```

## Additional Resources

- [Architecture Guide](docs/architecture.md)
- [Agent Development Guide](guides/agent-guide.md)
- [LLM Playground Guide](guides/llm-playground.md)
- [API Documentation](docs/api.md)

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review logs: `make logs`
3. Open an issue on GitHub

## License

See [LICENSE](LICENSE) file for details.