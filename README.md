# MasterChef-Bench

A comprehensive benchmarking tool for large language models in kitchen management scenarios.

## Overview

MasterChef-Bench evaluates LLMs on their ability to perform complex real-world tasks in a simulated kitchen environment. The benchmark tests role coherence, task completion, coordination, and other metrics across multiple roles in a kitchen hierarchy.

## Features

- Multi-agent evaluation framework for kitchen management
- Role-based testing with hierarchical relationships
- Real-time visualization of agent interactions
- Standardized benchmarking scenarios
- Performance metrics and reporting
- LLM Playground for interactive testing

## Getting Started

### Prerequisites

- Go 1.17+
- Node.js 14+ (for frontend)
- Docker (optional, for containerized deployment)
- API keys for LLMs (OpenAI, Anthropic, etc.)

### Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/masterchef-bench.git
cd masterchef-bench
```

Install Go dependencies:

```bash
go mod download
```

Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

### Configuration

Set up your environment variables:

```bash
export OPENAI_API_KEY=your_openai_key
export ANTHROPIC_API_KEY=your_anthropic_key
export GOOGLE_API_KEY=your_google_key
```

Or create a `.env` file in the root directory.

### Running the Backend

Start the main backend server:

```bash
go run cmd/main.go
```

### Running the Frontend

In a separate terminal:

```bash
cd frontend
npm start
```

### Using the CLI

For command-line interaction:

```bash
cd cli
go run main.go
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
