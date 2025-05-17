# MasterChef-Bench

MasterChef-Bench is a multi-agent system benchmark for evaluating LLM-based agents in a simulated kitchen environment. The system implements a hierarchical structure of agents that must coordinate to handle kitchen operations, from menu planning to order fulfillment.

## Features

- **Hierarchical Agent System**: Multiple agents with distinct roles and responsibilities

  - Executive Chef: Overall kitchen management and coordination
  - Sous Chefs: Station management and order execution
  - Specialized Roles: Prep cooks, line cooks, etc.

- **Comprehensive Evaluation Metrics**:

  - Role Coherence
  - Task Completion
  - Coordination Efficiency
  - Long-term Consistency
  - Resource Utilization

- **Real-time Monitoring**:

  - Prometheus integration for metrics collection
  - Grafana dashboards for visualization
  - Detailed logging and performance tracking

- **Flexible Configuration**:
  - YAML-based configuration
  - Environment variable support
  - Pluggable components

## Prerequisites

- Go 1.21 or later
- PostgreSQL 14 or later
- Redis 7.0 or later
- Docker (optional)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/masterchef-bench.git
cd masterchef-bench
```

2. Install dependencies:

```bash
go mod download
```

3. Set up the configuration:

```bash
cp configs/config.yaml.example configs/config.yaml
# Edit configs/config.yaml with your settings
```

4. Set up environment variables:

```bash
export OPENAI_API_KEY="your-api-key"
export DATABASE_URL="postgresql://user:password@localhost:5432/masterchef"
```

## Running the Benchmark

1. Start the services:

```bash
# Using Docker
docker-compose up -d

# Or manually start PostgreSQL and Redis
```

2. Run the application:

```bash
go run cmd/main.go
```

3. Access the API:

```bash
curl http://localhost:8080/api/v1/kitchen/status
```

4. View metrics:

```bash
curl http://localhost:9090/metrics
```

## API Endpoints

### Order Management

- `POST /api/v1/orders`: Create a new order
- `GET /api/v1/orders/:id`: Get order status
- `PUT /api/v1/orders/:id`: Update order
- `DELETE /api/v1/orders/:id`: Cancel order

### Kitchen Operations

- `GET /api/v1/kitchen/status`: Get kitchen status
- `POST /api/v1/kitchen/prep`: Start preparation
- `POST /api/v1/kitchen/cook`: Start cooking
- `POST /api/v1/kitchen/plate`: Start plating

### Inventory Management

- `GET /api/v1/inventory`: Get inventory levels
- `POST /api/v1/inventory/update`: Update inventory
- `POST /api/v1/inventory/order`: Order supplies

### Staff Management

- `GET /api/v1/staff`: Get staff status
- `POST /api/v1/staff/assign`: Assign staff to tasks

## Configuration

The system can be configured through `configs/config.yaml`. Key configuration sections include:

- API settings
- Database connections
- Agent configurations
- Evaluation parameters
- Metrics collection
- Memory systems

See the [Configuration Guide](docs/configuration.md) for detailed settings.

## Evaluation Metrics

### Role Coherence

Measures how well agents maintain their assigned roles and responsibilities:

- Knowledge consistency
- Authority adherence
- Task appropriateness

### Task Completion

Evaluates the effectiveness of task execution:

- Completion rate
- Time efficiency
- Quality score

### Coordination

Assesses inter-agent communication and cooperation:

- Communication efficiency
- Resource utilization
- Conflict resolution

### Long-term Consistency

Tracks sustained performance over time:

- Decision consistency
- Learning progression
- Adaptation capability

## Development

### Adding New Agents

1. Create a new agent type in `internal/agents/`:

```go
type NewAgent struct {
    *Agent
    // Additional fields
}
```

2. Implement the agent interface:

```go
func (a *NewAgent) HandleTask(ctx context.Context, task Task) error {
    // Implementation
}
```

### Adding New Metrics

1. Define the metric in `internal/evaluation/metrics.go`:

```go
var newMetric = prometheus.NewGaugeVec(
    prometheus.GaugeOpts{
        Name: "new_metric_name",
        Help: "Description",
    },
    []string{"label1", "label2"},
)
```

2. Register the metric in `NewMetricsCollector()`.

### Running Tests

```bash
# Run all tests
go test ./...

# Run specific tests
go test ./internal/agents -run TestExecutiveChef

# Run with race detection
go test -race ./...
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- LangChain-Go team for the LLM integration framework
- OpenAI for the GPT models
- The Go community for various tools and libraries

## Contact

For questions and support, please open an issue or contact the maintainers:

- GitHub Issues: [Project Issues](https://github.com/yourusername/masterchef-bench/issues)
- Email: your.email@example.com
