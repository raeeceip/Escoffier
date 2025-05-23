# Escoffier-Bench

A comprehensive benchmarking tool for large language models in kitchen management scenarios.

## Overview

Escoffier-Bench evaluates LLMs on their ability to perform complex real-world tasks in a simulated kitchen environment. The benchmark tests role coherence, task completion, coordination, and other metrics across multiple roles in a kitchen hierarchy.

## Features

- **Multi-agent evaluation framework** for kitchen management scenarios
- **Role-based testing** with hierarchical relationships (Executive Chef, Sous Chef, Line Cook, etc.)
- **Real-time visualization** of agent interactions and kitchen state
- **Standardized benchmarking scenarios** for consistent evaluation
- **Performance metrics and reporting** with Prometheus integration
- **LLM Playground** for interactive testing and comparison
- **CLI interface** for programmatic interaction
- **Web dashboard** for monitoring and visualization

## Quick Start

### Prerequisites

- **Go 1.22+** (for backend services)
- **Node.js 18+** (for frontend)
- **npm** (comes with Node.js)
- **LLM API keys** (OpenAI, Anthropic, Google - optional, or use free GitHub Models)

### 🚀 One-Command Start

```bash
# Clone and start everything
git clone <repository-url>
cd escoffier-bench
./start-all.sh
```

This will:
1. Check dependencies
2. Build all components
3. Start the backend API server
4. Start the LLM playground
5. Start metrics collection
6. Open the web interface

### 🛠️ Development Mode

For development with hot reloading:

```bash
# Interactive development menu
make dev
# or
./dev.sh
```

### 📋 Alternative Installation Methods

#### Method 1: Using Make (Recommended)

```bash
# Install dependencies and build everything
make install-deps
make build

# Start all services
make start

# Development mode
make dev
```

#### Method 2: Manual Setup

```bash
# Install Go dependencies
go mod download

# Install frontend dependencies
cd frontend && npm install && cd ..

# Build all components
make build

# Start backend
go run cmd/main.go

# In another terminal, start frontend dev server
cd frontend && npm start
```

### 🔧 Configuration

#### Environment Variables

```bash
# API Keys (optional for development)
export OPENAI_API_KEY=your_openai_key
export ANTHROPIC_API_KEY=your_anthropic_key
export GOOGLE_API_KEY=your_google_key

# Free GitHub Models (recommended for testing)
export GITHUB_TOKEN=your_github_token

# Database (optional, defaults to SQLite)
export DATABASE_URL=data/masterchef.db

# Server Configuration (optional)
export PORT=8080
export PLAYGROUND_PORT=8090
export METRICS_PORT=9090
```

#### Configuration File

Create `configs/config.yaml`:

```yaml
database_url: data/masterchef.db
log_level: info
metrics:
  enabled: true
  port: 9090
  path: /metrics
```

### 🌐 Access Points

Once running, access the system at:

- **Main API**: http://localhost:8080
- **LLM Playground**: http://localhost:8090
- **Metrics Dashboard**: http://localhost:9090/metrics
- **Health Check**: http://localhost:8080/health

### 🎯 Available Make Commands

```bash
make help              # Show all available commands
make build             # Build all components
make test              # Run all tests
make dev               # Start development environment
make start             # Start production mode
make clean             # Clean build artifacts
make lint              # Run linters
make docker-build      # Build Docker image
```

## LLM Playground

The LLM Playground provides an interactive environment for testing and comparing different LLMs.

### Starting the Playground

Option 1: Using the CLI tool:

1. Run `go run cli/main.go`
2. Select "LLM Playground" from the main menu
3. Follow the on-screen instructions to access the web interface

Option 2: Running directly:

```bash
go run cmd/main.go --enable-playground --playground-port 8090
```

### Accessing the Playground

Once running, access the playground at:

- Web interface: http://localhost:8090
- API endpoint: http://localhost:8090/api
- WebSocket: ws://localhost:8090/ws

### Features

- Test multiple LLMs on different kitchen scenarios
- Real-time evaluation and metrics
- Visual comparison of model performance
- Detailed logs of agent interactions
- Export reports for further analysis

## Benchmarking Scenarios

- **Busy Night**: High-volume service with double the normal orders
- **Overstocked Kitchen**: Managing excess inventory with expiry concerns
- **Slow Business**: Optimizing operations during low customer volume
- **Low Inventory**: Handling service with critically low ingredient stock
- **High Labor Cost**: Managing an overstaffed kitchen efficiently
- **Quality Control**: Maintaining standards during normal service volume

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- LangChain-Go team for the LLM integration framework
- OpenAI for the GPT models
- The Go community for various tools and libraries

## Contact

For questions and support, please open an issue or contact the maintainers:

- GitHub Issues: [Project Issues](https://github.com/yourusername/masterchef-bench/issues)
- Email: your.email@example.com

## Testing

### Go Tests

Run tests for specific packages:

```bash
# Run all tests
go test ./...

# Run specific package tests
go test ./internal/monitoring
go test ./internal/evaluation
go test ./internal/playground

# Run tests with coverage
go test ./internal/monitoring ./internal/evaluation ./internal/playground -cover
```

### Frontend Tests

The frontend is built with React and can be tested using Jest:

```bash
cd frontend
npm test
```

### Test Structure

- **Go Tests**: Located in the `internal/<package>/tests` directories
- **React Tests**: Located alongside the components they test with a `.test.tsx` extension

### Debugging Tests

If you encounter issues with tests:

1. Check that all dependencies are installed:

   ```bash
   go mod tidy
   cd frontend && npm install
   ```

2. Run tests with verbose output:

   ```bash
   go test -v ./...
   ```

3. Run specific failing tests:
   ```bash
   go test -v ./path/to/package -run TestName
   ```
