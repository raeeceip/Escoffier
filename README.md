# Escoffier Kitchen Simulation Platform

A comprehensive multi-agent kitchen simulation system for research in computational cooking, agent coordination, and Large Language Model (LLM) integration. Built for MasterChef-Bench research with real LLM providers and advanced analytics.

## 🌟 Features

### 🤖 Multi-Agent System
- **Real LLM Integration**: OpenAI GPT-4, Anthropic Claude, Cohere Command, and Hugging Face Transformers
- **Agent Hierarchy**: Executive Chef, Head Chef, Sous Chef, Line Cook, Prep Cook with specialized roles
- **Dynamic Coordination**: Hierarchical command structure with real-time communication
- **Skill System**: 20+ culinary skills including leadership, knife skills, sauce making, grilling, baking
- **Provider Flexibility**: Mix and match different LLM providers for comparative research

### 🍳 Kitchen Simulation
- **Realistic Constraints**: Equipment capacity, ingredient availability, timing pressure
- **Station Management**: Prep, hot, cold, grill, pastry, garde manger stations
- **Equipment Modeling**: Ovens, stoves, grills, fryers with capacity and timing constraints
- **Crisis Simulation**: Equipment failures, ingredient shortages, rush periods
- **State Tracking**: Complete kitchen state with real-time monitoring

### 📊 Advanced Analytics & Visualization
- **Comprehensive Metrics**: Task completion rates, quality scores, collaboration effectiveness
- **Interactive Charts**: Plotly-based visualizations (performance, timeline, distribution)
- **CSV Export**: Complete data export for statistical analysis
- **Research Reports**: Automated analysis with findings and recommendations
- **Real-time Monitoring**: Live metrics collection during scenario execution

### 🎯 Scenario Execution
- **Research Scenarios**: Cooking challenges, service rush, crisis management, skill assessment
- **Parallel Processing**: Concurrent task execution with multiple agents
- **Performance Scoring**: Quality, efficiency, and collaboration metrics
- **Event Logging**: Detailed execution traces for research analysis
- **Configurable Parameters**: Duration, difficulty, team size, crisis probability

### 🛠️ Modern Python Architecture
- **FastAPI Server**: RESTful API with auto-generated OpenAPI documentation
- **Fire CLI**: Powerful command-line interface for research workflows
- **Type Safety**: Comprehensive type hints and Pydantic validation
- **Async/Await**: High-performance asynchronous processing
- **Database ORM**: SQLAlchemy with SQLite (dev) and PostgreSQL (production) support

## 🚀 Quick Start

### Installation

Choose your preferred installation method:

#### Option 1: Automated Setup (Recommended)

**Windows (PowerShell):**
```powershell
# Run setup script
.\scripts\setup.ps1
```

**Windows (Command Prompt):**
```cmd
# Run setup script
scripts\setup.bat
```

**Unix/Linux/macOS:**
```bash
# Make script executable and run
chmod +x scripts/setup.sh
./scripts/setup.sh
```

#### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/raeeceip/escoffier.git
cd escoffier

# Install with UV (recommended)
uv sync

# Or create virtual environment and install with pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create data directories
mkdir -p data/{analytics/{charts,reports},metrics}

# Copy configuration template
cp configs/config.yaml.example configs/config.yaml

# Initialize database
python -m cli.main init_db
```

### Configuration

1. **Edit your configuration file** (`configs/config.yaml`):
```yaml
llm_providers:
  openai:
    api_key: "your-openai-api-key"
  anthropic:
    api_key: "your-anthropic-api-key"
  cohere:
    api_key: "your-cohere-api-key"
  huggingface:
    enabled: true  # No API key needed for local models
```

2. **Set environment variables** (optional):
```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export COHERE_API_KEY="your-key"
```

## 📖 Usage

### Command Line Interface (CLI)

The Fire-based CLI provides comprehensive research and development workflows:

#### Agent Management
```bash
# Create agents with different providers
python -m cli.main create_agent "Gordon Ramsay" head_chef "leadership,knife_skills,sauce_making" --provider openai
python -m cli.main create_agent "Julia Child" sous_chef "baking,pastry,organization" --provider anthropic
python -m cli.main create_agent "Anthony Bourdain" line_cook "grilling,international_cuisine" --provider cohere
python -m cli.main create_agent "Local Chef" prep_cook "knife_skills,organization" --provider huggingface

# List all agents
python -m cli.main list_agents

# View agent details
python -m cli.main get_agent_details "Gordon Ramsay"
```

#### Scenario Execution
```bash
# Run different scenario types
python -m cli.main run_scenario cooking_challenge
python -m cli.main run_scenario service_rush  
python -m cli.main run_scenario crisis_management
python -m cli.main run_scenario skill_assessment

# List available scenarios
python -m cli.main list_scenarios
```

#### Advanced Analytics
```bash
# View current metrics
python -m cli.main metrics

# Export metrics to CSV
python -m cli.main metrics --export_csv

# Generate interactive charts
python -m cli.main metrics --generate_charts

# Export both CSV and charts
python -m cli.main metrics --export_csv --generate_charts --output_dir "research_data"

# Generate comprehensive analysis report
python -m cli.main generate_report

# Analyze agent performance
python -m cli.main analyze_performance

# Analyze collaboration patterns
python -m cli.main analyze_collaboration
```

#### Recipe Management
```bash
# Search recipes by criteria
python -m cli.main search_recipes --cuisine="french" --difficulty="medium" --max_time=60

# Get recipe recommendations for specific agents
python -m cli.main get_recipe_recommendations --agent_skills="grilling,sauteing" --time_limit=45

# View recipe statistics
python -m cli.main recipe_stats
```

#### Data Management
```bash
# Export all data for research
python -m cli.main export_data --format="excel" --output_dir="research_exports"

# Initialize or reset database
python -m cli.main init_db

# Clean up old data
python -m cli.main cleanup --days=30
```

### REST API Server

Start the FastAPI server for web integration:

```bash
python -m cli.main serve --host="0.0.0.0" --port=8000
```

Access the interactive documentation at `http://localhost:8000/docs`

#### Key API Endpoints

**Agent Management:**
- `POST /agents` - Create new agent
- `GET /agents` - List all agents  
- `GET /agents/{id}` - Get agent details
- `PUT /agents/{id}` - Update agent
- `DELETE /agents/{id}` - Delete agent

**Scenario Execution:**
- `POST /scenarios/execute` - Execute scenario
- `GET /scenarios/{id}` - Get scenario results
- `GET /scenarios/{id}/metrics` - Get scenario metrics

**Kitchen State:**
- `GET /kitchen/state` - Current kitchen state
- `POST /kitchen/reset` - Reset kitchen
- `GET /kitchen/equipment` - Equipment status

**Analytics:**
- `GET /metrics` - Current system metrics
- `GET /metrics/analysis` - Performance analysis
- `GET /metrics/export` - Export metrics data

### Python API

```python
import asyncio
from cli.main import EscoffierCLI
from escoffier_types import ScenarioType

async def research_experiment():
    # Initialize the system
    cli = EscoffierCLI()
    
    # Create diverse agent team
    await cli.create_agent("Research Chef A", "head_chef", "leadership,sauce_making", "openai")
    await cli.create_agent("Research Chef B", "sous_chef", "baking,organization", "anthropic") 
    await cli.create_agent("Research Chef C", "line_cook", "grilling,knife_skills", "cohere")
    await cli.create_agent("Research Chef D", "prep_cook", "organization,basics", "huggingface")
    
    # Execute multiple scenarios for data collection
    scenarios = ["cooking_challenge", "service_rush", "crisis_management"]
    
    results = []
    for scenario_type in scenarios:
        print(f"Executing {scenario_type}...")
        result = await cli.run_scenario(scenario_type)
        results.append(result)
    
    # Generate analytics
    await cli.metrics(export_csv=True, generate_charts=True)
    report = await cli.generate_report()
    
    return results, report

# Run the experiment
results, report = asyncio.run(research_experiment())
```

## 🏗️ Architecture

### Core Components

```
escoffier/
├── config.py              # Pydantic configuration management
├── escoffier_types.py      # Type definitions and enums
├── agents/                 # Multi-agent system
│   ├── manager.py         # Agent lifecycle and coordination
│   └── context.py         # Agent state and memory
├── api/                   # FastAPI REST server
│   └── server.py          # Route definitions and handlers
├── cli/                   # Fire-based command interface  
│   └── main.py            # CLI commands and workflows
├── database/              # Data persistence layer
│   ├── models.py          # SQLAlchemy ORM models
│   └── manager.py         # Database operations
├── kitchen/               # Kitchen simulation engine
│   └── engine.py          # State management and constraints
├── metrics/               # Analytics and visualization
│   └── collector.py       # Metrics calculation and export
├── providers/             # LLM integrations
│   └── llm.py             # Provider abstractions
├── recipes/               # Recipe management system
│   └── manager.py         # Recipe operations and recommendations
└── scenarios/             # Scenario execution engine
    └── executor.py        # Scenario orchestration
```

### Design Principles

- **Research-First**: Built specifically for computational cooking and multi-agent research
- **Real LLM Integration**: Actual API calls to leading LLM providers, not mocks
- **Comprehensive Analytics**: Every interaction tracked for research insights
- **Scalable Architecture**: Async/await throughout with parallel processing
- **Type Safety**: Full type hints and Pydantic validation for reliability
- **Modular Design**: Loosely coupled components for easy extension

## 🔬 Research Applications

### Multi-Agent Coordination Studies
- **Communication Patterns**: Analyze message frequency, timing, and content
- **Hierarchy Effectiveness**: Compare flat vs. hierarchical team structures
- **Collaboration Quality**: Measure coordination and task distribution
- **Crisis Response**: Study adaptive behavior under pressure

### LLM Performance Comparison
- **Provider Benchmarking**: Compare OpenAI, Anthropic, Cohere, HuggingFace on kitchen tasks
- **Prompt Engineering**: Test different prompting strategies for culinary tasks
- **Context Understanding**: Evaluate situational awareness and task interpretation
- **Consistency Analysis**: Measure response reliability across providers

### Computational Cooking Research
- **Recipe Optimization**: Analyze ingredient substitutions and technique modifications
- **Skill Transfer**: Study how skills apply across different cooking contexts
- **Quality Prediction**: Model factors that influence dish quality
- **Efficiency Analysis**: Optimize workflows and resource allocation

### Crisis Management Studies
- **Equipment Failure Response**: Simulate and analyze adaptation strategies
- **Resource Scarcity**: Study decision-making under constraint
- **Time Pressure**: Analyze performance degradation under stress
- **Recovery Patterns**: Model bounce-back from disruptions

## 📊 Analytics and Visualization

### Comprehensive Metrics
- **Performance Metrics**: Task completion rates, timing, quality scores
- **Collaboration Metrics**: Communication frequency, coordination effectiveness
- **Agent Metrics**: Individual performance, skill utilization, stress levels
- **System Metrics**: Resource utilization, bottleneck identification

### Interactive Visualizations
- **Performance Dashboards**: Real-time agent and system performance
- **Timeline Charts**: Task execution and communication patterns
- **Network Analysis**: Agent interaction and communication networks
- **Distribution Charts**: Skill usage, task types, outcome distributions

### Export Formats
- **CSV Files**: Raw data for statistical analysis (R, Python, SPSS)
- **Excel Workbooks**: Multi-sheet reports with charts and analysis
- **JSON Data**: Structured data for programmatic access
- **Interactive HTML**: Plotly charts for presentations and exploration

### Example Analytics Commands
```bash
# Export complete dataset
python -m cli.main metrics --export_csv --output_dir "research_study_2024"

# Generate publication-ready charts
python -m cli.main metrics --generate_charts --output_dir "paper_figures"

# Create comprehensive research report
python -m cli.main generate_report --detailed --format="pdf"
```

## 🧪 Example Research Scenarios

### 1. LLM Provider Comparison Study
```bash
# Create agents with different providers
python -m cli.main create_agent "GPT Chef" head_chef "leadership,sauce_making" --provider openai
python -m cli.main create_agent "Claude Chef" head_chef "leadership,sauce_making" --provider anthropic
python -m cli.main create_agent "Cohere Chef" head_chef "leadership,sauce_making" --provider cohere
python -m cli.main create_agent "Local Chef" head_chef "leadership,sauce_making" --provider huggingface

# Run identical scenarios with each team
for i in {1..10}; do
    python -m cli.main run_scenario cooking_challenge --duration=60 --difficulty=hard
done

# Analyze comparative performance
python -m cli.main analyze_performance --group_by="llm_provider"
```

### 2. Crisis Management Resilience Study
```bash
# High-stress scenario with equipment failures
python -m cli.main run_scenario crisis_management \
  --duration=45 \
  --crisis_probability=0.4 \
  --max_agents=6 \
  --equipment_failures=true

# Export crisis response data
python -m cli.main export_data --filter="crisis_events" --format="csv"
```

### 3. Skill Transfer Analysis
```bash
# Create specialists and generalists
python -m cli.main create_agent "Specialist" chef_de_partie "sauce_making,sauce_making,sauce_making"
python -m cli.main create_agent "Generalist" chef_de_partie "sauce_making,grilling,baking"

# Test performance across different recipe types
python -m cli.main run_scenario skill_assessment --recipe_variety=high
```

## 🔧 Configuration

The `configs/config.yaml` file provides comprehensive customization:

```yaml
# LLM Provider Settings
llm_providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"  # or gpt-3.5-turbo
    max_tokens: 1500
    temperature: 0.7
  
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-3-sonnet-20240229"
    max_tokens: 1500
    temperature: 0.7

# Kitchen Simulation Parameters
kitchen:
  stations:
    - name: "prep"
      capacity: 2
      equipment: ["cutting_boards", "knives"]
    - name: "hot"
      capacity: 4
      equipment: ["stoves", "ovens", "grills"]

# Research Settings
research:
  random_seed: 42
  save_all_interactions: true
  statistical_analysis: true
```

## 🚦 Development Workflow

### Setup Development Environment
```bash
# Clone and setup
git clone https://github.com/raeeceip/escoffier.git
cd escoffier
./scripts/setup.sh  # or setup.ps1 on Windows

# Install development dependencies
uv sync --dev

# Run tests
python -m pytest

# Code formatting
black .
isort .
flake8 .
```

### Running Experiments
```bash
# 1. Reset environment
python -m cli.main init_db --reset

# 2. Create experimental agents
python -m cli.main create_agent "Control Agent" head_chef "leadership" --provider openai
python -m cli.main create_agent "Test Agent" head_chef "leadership" --provider anthropic

# 3. Execute scenarios
python -m cli.main run_scenario cooking_challenge

# 4. Collect results
python -m cli.main metrics --export_csv --generate_charts

# 5. Generate analysis
python -m cli.main generate_report --detailed
```

## 🤝 Contributing

We welcome contributions from researchers and developers:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-research-feature`
3. **Install development dependencies**: `uv sync --dev`
4. **Make your changes** with proper type hints and documentation
5. **Add tests**: `pytest tests/test_your_feature.py`
6. **Run quality checks**: `black . && isort . && flake8 . && mypy .`
7. **Submit a pull request**

### Research Contributions
- Novel scenario types
- Additional LLM providers
- Advanced analytics methods
- Visualization improvements
- Performance optimizations

### Development Contributions
- Bug fixes and stability improvements
- Documentation enhancements
- Test coverage improvements
- Code quality and performance

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Research Foundation**: Built for MasterChef-Bench and computational cooking research
- **Inspiration**: Real kitchen operations and professional chef coordination
- **Technology**: Leverages state-of-the-art LLM providers for realistic agent behavior
- **Community**: Designed for reproducible research with comprehensive metrics

## 📚 Research Citations

If you use Escoffier in your research, please cite:

```bibtex
@software{escoffier2024,
  title={Escoffier: A Multi-Agent Kitchen Simulation Platform for Computational Cooking Research},
  author={MasterChef-Bench Research Team},
  year={2024},
  url={https://github.com/raeeceip/escoffier},
  version={2.0.0}
}
```

## 📞 Support

- **Documentation**: Full API documentation at `/docs` when server is running
- **Issues**: Report bugs and request features on GitHub Issues
- **Discussions**: Join research discussions on GitHub Discussions
- **Community**: Connect with other researchers using Escoffier

---

## 🎯 Quick Commands Reference

**Essential Commands:**
```bash
# Setup
./scripts/setup.sh

# Create agent
python -m cli.main create_agent "Chef Name" role "skills" --provider llm_provider

# Run scenario  
python -m cli.main run_scenario scenario_type

# View metrics with visualization
python -m cli.main metrics --export_csv --generate_charts

# Start API server
python -m cli.main serve
```

**Ready to revolutionize computational cooking research?** 👨‍🍳🤖🔬

Start exploring multi-agent coordination with real LLM-powered kitchen simulation!