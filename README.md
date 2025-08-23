# Escoffier: Multi-Agent Kitchen Simulation Platform

A research platform for studying multi agent systems, agent coordination, and Large Language Model performance in complex task environments. Escoffier provides a realistic kitchen simulation with professional agent hierarchies, real LLM integration, and comprehensive analytics for reproducible research.

## Research Objectives

Escoffier addresses critical research questions in multi-agent systems, computational cooking, and LLM evaluation:

- **Multi-Agent Coordination**: How do hierarchical teams coordinate under pressure and resource constraints?
- **LLM Performance**: How do different language models perform in domain-specific, collaborative environments?
- **Crisis Management**: How do intelligent agents adapt to equipment failures, time pressure, and resource scarcity?
- **Skill Transfer**: How effectively do agents apply specialized knowledge across diverse cooking contexts?
- **Communication Patterns**: What communication strategies emerge in high-stakes collaborative environments?

## System Architecture

### Core Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **Agent System** | Multi-agent coordination with professional kitchen hierarchy | Real LLM integration, role-based behavior, skill specialization |
| **Kitchen Engine** | Realistic cooking environment simulation | Equipment constraints, ingredient tracking, timing pressure |
| **Scenario Executor** | Configurable research scenario orchestration | Parallel processing, crisis injection, performance measurement |
| **Analytics Engine** | Comprehensive data collection and visualization | Interactive charts, statistical analysis, research reports |
| **API Layer** | REST interface for external integrations | FastAPI with OpenAPI documentation, async processing |

### Supported LLM Providers

| Provider | Models | Use Case | Performance Tier |
|----------|--------|----------|------------------|
| **OpenAI** | GPT-4, GPT-3.5-turbo | High-performance reasoning | Premium |
| **Anthropic** | Claude-3-Haiku, Claude-3-Sonnet | Safety-focused responses | Premium |
| **Cohere** | Command-R, Command-Light | Instruction-following | Standard |
| **Hugging Face** | DialoGPT, Local models | Open-source evaluation | Research |

## Evaluation Framework

### Performance Metrics

| Metric Category | Measurements | Evaluation Criteria |
|-----------------|--------------|-------------------|
| **Task Completion** | Success rate, timing, quality scores | Percentage of successful task completion within time constraints |
| **Collaboration** | Communication frequency, coordination effectiveness | Quality and timing of inter-agent communication |
| **Crisis Response** | Adaptation time, solution quality | Speed and effectiveness of response to equipment failures |
| **Resource Management** | Efficiency, waste reduction | Optimal utilization of ingredients and equipment |
| **Skill Application** | Technique accuracy, knowledge transfer | Correct application of culinary skills across contexts |

### Scenario Types

| Scenario | Duration | Complexity | Evaluation Focus |
|----------|----------|------------|-----------------|
| **Cooking Challenge** | 3-6 min | Medium-High | Task coordination, quality output |
| **Service Rush** | 5-10 min | High | Time pressure, parallel processing |
| **Crisis Management** | 3-8 min | Very High | Adaptability, problem-solving |
| **Skill Assessment** | 2-5 min | Medium | Individual performance, technique |
| **Team Building** | 8-15 min | Variable | Communication, hierarchy establishment |

### Recipe Dataset Integration

Escoffier supports large-scale recipe datasets for realistic task assignment:

| Dataset Type | Format | Parser | Source |
|--------------|--------|--------|--------|
| **Kaggle Recipe Dataset** | JSON | `KaggleRecipeParser` | [kaggle.com/datasets/kaggle/recipe-ingredients-dataset](https://www.kaggle.com/datasets/kaggle/recipe-ingredients-dataset) |
| **Custom CSV** | CSV | `RecipeManager` | User-provided structured data |
| **JSON Recipes** | JSON | `KaggleRecipeParser` | Custom or third-party recipe APIs |

#### Loading Large Recipe Datasets

```bash
# Download Kaggle dataset (requires kaggle CLI)
python -m cli.main download_kaggle_dataset

# Parse downloaded dataset  
python -m cli.main parse_kaggle_recipes "data/train.json" --test_path "data/test.json"

# Analyze processed dataset
python -m cli.main analyze_recipe_dataset

# Run scenarios with large recipe database
python -m cli.main run_scenario cooking_challenge --duration 5 --agents 4
```

The Kaggle Recipe Dataset contains **40,000+ recipes** across **20 cuisines** with ingredient lists, making it ideal for:
- Realistic chef task assignment based on cuisine expertise
- Ingredient availability constraints 
- Recipe complexity analysis and difficulty estimation
- Cross-cultural cooking scenario development

### Research Applications

| Research Area | Metrics | Expected Outcomes |
|---------------|---------|-------------------|
| **LLM Comparison** | Response quality, consistency, task completion | Quantitative performance benchmarks across providers |
| **Agent Coordination** | Communication patterns, hierarchy effectiveness | Optimal team structures and communication protocols |
| **Crisis Resilience** | Recovery time, solution quality | Strategies for maintaining performance under stress |
| **Skill Transfer** | Cross-domain application, learning efficiency | Models for knowledge application across contexts |

## Installation and Setup

### Prerequisites

- Python 3.12+
- 4GB+ RAM recommended
- LLM provider API keys (optional for local models)

### Quick Start

#### Automated Installation

```bash
# Windows PowerShell
.\scripts\setup.ps1

# Unix/Linux/macOS
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

#### Manual Installation

```bash
git clone https://github.com/raeeceip/escoffier.git
cd escoffier

# Install dependencies
uv sync  # or pip install -r requirements.txt

# Initialize database
python -m cli.main init_db

# Configure API keys (optional)
cp configs/config.yaml.example configs/config.yaml
# Edit config.yaml with your API keys
```

## Usage Guide

### Command Line Interface

#### Agent Management

```bash
# Create research agents with different LLM providers
python -m cli.main create_agent "Chef-GPT" head_chef "leadership,sauce_making" --provider openai
python -m cli.main create_agent "Chef-Claude" sous_chef "organization,baking" --provider anthropic
python -m cli.main create_agent "Chef-Cohere" line_cook "grilling,knife_skills" --provider cohere
python -m cli.main create_agent "Chef-Local" prep_cook "basics,organization" --provider huggingface

# List all agents with performance metrics
python -m cli.main list_agents
```

#### Scenario Execution

```bash
# Execute evaluation scenarios
python -m cli.main run_scenario cooking_challenge    # Standard coordination test
python -m cli.main run_scenario service_rush         # High-pressure evaluation
python -m cli.main run_scenario crisis_management    # Adaptability assessment
python -m cli.main run_scenario skill_assessment     # Individual performance
```

#### Analytics and Reporting

```bash
# Generate comprehensive analytics
python -m cli.main metrics summary                   # Current performance overview
python -m cli.main metrics --export_csv             # Export raw data for analysis
python -m cli.main metrics --generate_charts        # Create interactive visualizations

# Research reporting
python -m cli.main generate_report                   # Comprehensive analysis report
python -m cli.main analyze_performance              # Provider comparison analysis
python -m cli.main analyze_collaboration           # Communication pattern analysis
```

#### Recipe Dataset Management

```bash
# Download Kaggle recipe dataset
python -m cli.main download_kaggle_dataset kaggle/recipe-ingredients-dataset

# Parse large recipe datasets
python -m cli.main parse_kaggle_recipes "data/train.json" \
  --test_path "data/test.json" \
  --use_multiprocessing true \
  --export_to_manager true

# Analyze recipe datasets
python -m cli.main analyze_recipe_dataset            # Current loaded recipes
python -m cli.main analyze_recipe_dataset "data/recipes.csv"  # Specific file
```

### REST API

```bash
# Start research server
python -m cli.main serve --host 0.0.0.0 --port 8000

# Access documentation at http://localhost:8000/docs
```

## Research Workflows

### LLM Provider Comparison Study

```bash
# 1. Create control groups
for provider in openai anthropic cohere huggingface; do
    python -m cli.main create_agent "Chef-${provider}" head_chef "leadership,sauce_making" --provider $provider
done

# 2. Execute standardized scenarios
for scenario in cooking_challenge service_rush crisis_management; do
    for trial in {1..10}; do
        python -m cli.main run_scenario $scenario --duration 5
    done
done

# 3. Generate comparative analysis
python -m cli.main analyze_performance --group_by llm_provider --export_results
```

### Crisis Resilience Assessment

```bash
# High-stress evaluation with equipment failures
python -m cli.main run_scenario crisis_management \
  --duration 5 \
  --crisis_probability 0.6 \
  --equipment_failures true \
  --ingredient_shortage true

# Export crisis response data
python -m cli.main export_data --filter crisis_events --format excel
```

## Analytics and Visualization

### Available Visualizations

| Chart Type | Purpose | Output Format |
|------------|---------|---------------|
| **Performance Timeline** | Agent performance over time | Interactive HTML |
| **Task Distribution** | Workload analysis across agents | Bar charts, heatmaps |
| **Communication Network** | Inter-agent communication patterns | Network graphs |
| **Crisis Response** | Adaptation strategies and timing | Timeline visualization |
| **Skill Utilization** | Frequency and effectiveness of skill usage | Distribution charts |

### Export Formats

| Format | Use Case | Command |
|--------|----------|---------|
| **CSV** | Statistical analysis (R, Python, SPSS) | `--export_csv` |
| **Excel** | Structured reports with multiple sheets | `--format excel` |
| **JSON** | Programmatic data access | `--format json` |
| **Interactive HTML** | Presentation and exploration | `--generate_charts` |

## Configuration

### LLM Provider Settings

```yaml
llm_providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    max_tokens: 1500
    temperature: 0.7
  
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-3-haiku-20240307"
    max_tokens: 1500
    temperature: 0.7

  cohere:
    api_key: "${COHERE_API_KEY}"
    model: "command-r"
    max_tokens: 1500
    temperature: 0.7

  huggingface:
    enabled: true
    model: "microsoft/DialoGPT-medium"
    cache_dir: "./models"
```

### Research Parameters

```yaml
research:
  random_seed: 42
  save_all_interactions: true
  statistical_analysis: true
  metrics_interval: 30  # seconds
  
kitchen:
  max_agents: 8
  equipment_failure_rate: 0.1
  crisis_probability: 0.2
  
scenarios:
  default_duration: 5  # minutes
  quality_threshold: 0.75
  efficiency_weight: 0.3
  collaboration_weight: 0.4
```

## Evaluation Options

### Standard Evaluation Suite

| Evaluation Type | Scenarios | Metrics | Duration |
|-----------------|-----------|---------|----------|
| **Basic Performance** | cooking_challenge | Task completion, quality | 3-6 min |
| **Stress Testing** | service_rush | Response time, error rate | 5-10 min |
| **Adaptability** | crisis_management | Recovery time, solution quality | 3-8 min |
| **Skill Assessment** | skill_assessment | Technique accuracy, knowledge application | 2-5 min |
| **Long-term Study** | All scenarios (repeated) | Learning curves, consistency | Multiple sessions |

### Advanced Evaluation Options

| Option | Purpose | Configuration |
|---------|---------|---------------|
| **Multi-Provider Comparison** | Benchmark different LLMs | `--compare_providers` |
| **Crisis Injection** | Test adaptability | `--crisis_probability 0.4` |
| **Skill Specialization** | Evaluate expertise | `--specialist_teams` |
| **Communication Analysis** | Study coordination patterns | `--track_communications` |
| **Performance Degradation** | Stress testing | `--increasing_difficulty` |

## Research Applications

### Multi-Agent Systems Research

- **Coordination Protocols**: Analysis of hierarchical vs. flat team structures
- **Communication Efficiency**: Optimal message frequency and content patterns
- **Load Balancing**: Task distribution strategies in resource-constrained environments
- **Conflict Resolution**: Decision-making processes during disagreements

### LLM Evaluation Studies

- **Domain Adaptation**: Performance in specialized culinary contexts
- **Instruction Following**: Adherence to complex, multi-step cooking procedures
- **Consistency Analysis**: Response reliability across repeated identical scenarios
- **Context Understanding**: Situational awareness in dynamic environments

### Computational Cooking Research

- **Recipe Optimization**: Ingredient substitution and technique modification
- **Quality Prediction**: Factors influencing dish quality and presentation
- **Efficiency Analysis**: Time and resource optimization strategies
- **Knowledge Transfer**: Application of techniques across different cuisines

## Contributing to Research

### Adding New Evaluation Scenarios

1. Define scenario parameters in `scenarios/executor.py`
2. Implement evaluation metrics in `metrics/collector.py`
3. Add CLI commands in `cli/main.py`
4. Update documentation with scenario specifications

### Extending LLM Provider Support

1. Implement provider interface in `providers/llm.py`
2. Add configuration schema in `config.py`
3. Update agent creation logic in `agents/manager.py`
4. Add provider-specific tests

### Research Data Guidelines

- All experiments should use consistent random seeds for reproducibility
- Performance metrics should be collected at regular intervals
- Control groups should be established for comparative studies
- Statistical significance testing should be applied to results

## Research Output

### Publications and Citations

If you use Escoffier in your research, please cite:

```bibtex
@software{escoffier2025,
  title={Escoffier: A Multi-Agent Kitchen Simulation Platform for Computational Cooking Research},
  author={@raeeceip},
  year={2025},
  url={https://github.com/raeeceip/escoffier},
  version={2.0.0}
}
```

### Expected Research Contributions

- Benchmarking LLM performance in domain-specific collaborative tasks
- Analysis of hierarchical multi-agent coordination strategies
- Crisis management and adaptation patterns in intelligent systems
- Communication protocol effectiveness in high-pressure environments
- Skill transfer and knowledge application across diverse contexts

## Technical Specifications

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Python** | 3.12+ | 3.12+ |
| **Memory** | 4GB RAM | 8GB+ RAM |
| **Storage** | 2GB free space | 5GB+ free space |
| **CPU** | 2 cores | 4+ cores |
| **Network** | Internet for LLM APIs | Stable broadband |

### Performance Benchmarks

| Scenario Type | Agents | Duration | Memory Usage | CPU Usage |
|---------------|--------|----------|--------------|-----------|
| **Small Study** | 2-4 agents | 30 min | ~2GB | ~30% |
| **Medium Study** | 4-6 agents | 60 min | ~4GB | ~50% |
| **Large Study** | 6-8 agents | 90 min | ~6GB | ~70% |

## License and Support

This project is licensed under the MIT License. For support, documentation, and research collaboration:

- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for research questions and methodology
- **Documentation**: Complete API documentation available at `/docs` endpoint
- **Community**: Join the computational cooking research community

---
