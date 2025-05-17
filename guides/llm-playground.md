# MasterChef-Bench: LLM Playground Guide

This guide provides instructions for setting up a development and evaluation playground for testing LLMs in the MasterChef-Bench environment.

## Table of Contents

- [Setup](#setup)
- [Model Integration](#model-integration)
- [Playground Interface](#playground-interface)
- [Evaluation Tools](#evaluation-tools)
- [Monitoring Dashboard](#monitoring-dashboard)
- [Analysis Tools](#analysis-tools)

## Setup

### Prerequisites

```bash
# Create playground directory
mkdir masterchef-playground
cd masterchef-playground

# Initialize Go module
go mod init masterchef-playground

# Install dependencies
go get github.com/tmc/langchaingo
go get github.com/gin-gonic/gin
go get github.com/prometheus/client_golang/prometheus
go get github.com/redis/go-redis/v9
go get github.com/lib/pq
go get github.com/gorilla/websocket
```

### Project Structure

```
masterchef-playground/
├── cmd/
│   └── playground/
│       └── main.go
├── internal/
│   ├── models/
│   │   ├── registry.go
│   │   ├── openai.go
│   │   ├── anthropic.go
│   │   ├── gemini.go
│   │   └── local.go
│   ├── playground/
│   │   ├── server.go
│   │   ├── handlers.go
│   │   └── websocket.go
│   ├── evaluation/
│   │   ├── metrics.go
│   │   ├── scenarios.go
│   │   └── reports.go
│   └── monitoring/
│       ├── prometheus.go
│       └── grafana.go
├── web/
│   ├── templates/
│   │   └── playground.html
│   └── static/
│       ├── css/
│       └── js/
└── configs/
    ├── models.yaml
    └── scenarios.yaml
```

## Model Integration

### Model Registry

```go
// internal/models/registry.go

type ModelProvider struct {
    Name        string
    Type        string
    MaxTokens   int
    Endpoint    string
    Credentials ModelCredentials
}

type ModelRegistry struct {
    providers map[string]*ModelProvider
    instances map[string]llms.LLM
}

func NewModelRegistry() *ModelRegistry {
    return &ModelRegistry{
        providers: map[string]*ModelProvider{
            "gpt4": {
                Name: "gpt-4-turbo-preview",
                Type: "openai",
                MaxTokens: 128000,
            },
            "claude3": {
                Name: "claude-3-sonnet",
                Type: "anthropic",
                MaxTokens: 200000,
            },
            "gemini": {
                Name: "gemini-1.5-pro",
                Type: "google",
                MaxTokens: 100000,
            },
            "mixtral": {
                Name: "mixtral-8x7b",
                Type: "local",
                MaxTokens: 32000,
            },
        },
        instances: make(map[string]llms.LLM),
    }
}

func (r *ModelRegistry) GetModel(name string) (llms.LLM, error) {
    if model, exists := r.instances[name]; exists {
        return model, nil
    }

    provider, exists := r.providers[name]
    if !exists {
        return nil, fmt.Errorf("unknown model: %s", name)
    }

    model, err := r.initializeModel(provider)
    if err != nil {
        return nil, err
    }

    r.instances[name] = model
    return model, nil
}
```

### Playground Server

```go
// internal/playground/server.go

type PlaygroundServer struct {
    router     *gin.Engine
    registry   *models.ModelRegistry
    evaluator  *evaluation.Evaluator
    monitor    *monitoring.Monitor
}

func NewPlaygroundServer() *PlaygroundServer {
    server := &PlaygroundServer{
        router:    gin.Default(),
        registry:  models.NewModelRegistry(),
        evaluator: evaluation.NewEvaluator(),
        monitor:   monitoring.NewMonitor(),
    }

    server.setupRoutes()
    return server
}

func (s *PlaygroundServer) setupRoutes() {
    s.router.GET("/", s.handleHome)
    s.router.GET("/ws", s.handleWebSocket)

    api := s.router.Group("/api")
    {
        api.POST("/evaluate", s.handleEvaluate)
        api.GET("/models", s.handleListModels)
        api.GET("/scenarios", s.handleListScenarios)
        api.GET("/metrics", s.handleMetrics)
    }
}
```

### WebSocket Handler

```go
// internal/playground/websocket.go

type WSConnection struct {
    conn      *websocket.Conn
    send      chan []byte
    evaluator *evaluation.Evaluator
}

func (s *PlaygroundServer) handleWebSocket(c *gin.Context) {
    conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
    if err != nil {
        return
    }

    wsConn := &WSConnection{
        conn:      conn,
        send:      make(chan []byte, 256),
        evaluator: s.evaluator,
    }

    go wsConn.writePump()
    go wsConn.readPump()
}

func (c *WSConnection) handleMessage(message []byte) {
    var req EvaluationRequest
    if err := json.Unmarshal(message, &req); err != nil {
        return
    }

    // Start evaluation in background
    go func() {
        results := c.evaluator.EvaluateModel(req.Model, req.Scenario)
        c.sendResults(results)
    }()
}
```

## Evaluation Interface

```html
<!-- web/templates/playground.html -->
<!DOCTYPE html>
<html>
	<head>
		<title>MasterChef-Bench Playground</title>
		<link rel="stylesheet" href="/static/css/playground.css" />
	</head>
	<body>
		<div class="container">
			<div class="models-panel">
				<h2>Available Models</h2>
				<div id="model-list"></div>
			</div>

			<div class="scenario-panel">
				<h2>Test Scenarios</h2>
				<div id="scenario-list"></div>
			</div>

			<div class="evaluation-panel">
				<h2>Live Evaluation</h2>
				<div id="metrics-display"></div>
				<div id="log-output"></div>
			</div>
		</div>

		<script src="/static/js/playground.js"></script>
	</body>
</html>
```

### Playground JavaScript

```javascript
// web/static/js/playground.js

class PlaygroundUI {
	constructor() {
		this.ws = new WebSocket("ws://" + window.location.host + "/ws");
		this.setupWebSocket();
		this.loadModels();
		this.loadScenarios();
	}

	setupWebSocket() {
		this.ws.onmessage = (event) => {
			const data = JSON.parse(event.data);
			this.updateMetrics(data);
		};
	}

	async loadModels() {
		const response = await fetch("/api/models");
		const models = await response.json();
		this.renderModels(models);
	}

	async loadScenarios() {
		const response = await fetch("/api/scenarios");
		const scenarios = await response.json();
		this.renderScenarios(scenarios);
	}

	startEvaluation(model, scenario) {
		const request = {
			model: model,
			scenario: scenario,
		};
		this.ws.send(JSON.stringify(request));
	}

	updateMetrics(data) {
		const metricsDisplay = document.getElementById("metrics-display");
		// Update metrics visualization
	}
}
```

## Monitoring Setup

### Prometheus Configuration

```yaml
# configs/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "masterchef-playground"
    static_configs:
      - targets: ["localhost:8080"]
    metrics_path: "/metrics"
```

### Grafana Dashboard

```json
{
	"dashboard": {
		"title": "MasterChef LLM Evaluation",
		"panels": [
			{
				"title": "Model Performance Comparison",
				"type": "graph",
				"targets": [
					{
						"expr": "model_performance_score{model=~'$model'}",
						"legendFormat": "{{model}}"
					}
				]
			},
			{
				"title": "Role Coherence by Model",
				"type": "heatmap",
				"targets": [
					{
						"expr": "role_coherence_score{model=~'$model',role=~'$role'}"
					}
				]
			},
			{
				"title": "Task Completion Success",
				"type": "gauge",
				"targets": [
					{
						"expr": "avg(task_completion_rate) by (model)"
					}
				]
			}
		],
		"templating": {
			"list": [
				{
					"name": "model",
					"type": "query",
					"query": "label_values(model_performance_score, model)"
				},
				{
					"name": "role",
					"type": "query",
					"query": "label_values(role_coherence_score, role)"
				}
			]
		}
	}
}
```

## Analysis Tools

### Metric Collection

```go
// internal/monitoring/metrics.go

type MetricCollector struct {
    modelPerformance *prometheus.GaugeVec
    roleCoherence   *prometheus.GaugeVec
    taskCompletion  *prometheus.GaugeVec
    responseTime    *prometheus.HistogramVec
}

func NewMetricCollector() *MetricCollector {
    return &MetricCollector{
        modelPerformance: prometheus.NewGaugeVec(
            prometheus.GaugeOpts{
                Name: "model_performance_score",
                Help: "Overall model performance score",
            },
            []string{"model", "scenario"},
        ),
        roleCoherence: prometheus.NewGaugeVec(
            prometheus.GaugeOpts{
                Name: "role_coherence_score",
                Help: "Role coherence score by model and role",
            },
            []string{"model", "role"},
        ),
        // Add more metrics
    }
}

func (c *MetricCollector) RecordMetrics(result *evaluation.Result) {
    c.modelPerformance.WithLabelValues(
        result.Model,
        result.Scenario,
    ).Set(result.OverallScore)

    for role, score := range result.RoleScores {
        c.roleCoherence.WithLabelValues(
            result.Model,
            role,
        ).Set(score)
    }
    // Record other metrics
}
```

### Report Generation

```go
// internal/evaluation/reports.go

type Report struct {
    ModelName    string
    ScenarioName string
    Timestamp    time.Time
    Metrics      map[string]float64
    Events       []Event
    Analysis     string
}

func GenerateReport(result *evaluation.Result) *Report {
    report := &Report{
        ModelName:    result.Model,
        ScenarioName: result.Scenario,
        Timestamp:    time.Now(),
        Metrics:      make(map[string]float64),
    }

    // Calculate metrics
    report.Metrics["overall_score"] = result.OverallScore
    report.Metrics["role_coherence"] = calculateAverageRoleCoherence(result.RoleScores)
    report.Metrics["task_completion"] = result.TaskCompletionRate

    // Analyze performance
    report.Analysis = analyzePerformance(result)

    return report
}
```

## Evaluation Scenarios

### Scenario Implementation

```go
// internal/evaluation/scenarios/types.go

type ScenarioType string

const (
    BusyNight      ScenarioType = "busy_night"
    Overstocked    ScenarioType = "overstocked"
    SlowBusiness   ScenarioType = "slow_business"
    LowInventory   ScenarioType = "low_inventory"
    HighLabor      ScenarioType = "high_labor"
    StaffShortage  ScenarioType = "staff_shortage"
    QualityControl ScenarioType = "quality_control"
    MenuChange     ScenarioType = "menu_change"
)

type ScenarioConfig struct {
    Type           ScenarioType
    Duration       time.Duration
    OrderVolume    int
    StaffCount     int
    InventoryLevel map[string]float64
    Constraints    map[string]interface{}
    Events         []Event
}
```

### Busy Night Scenario

```go
// internal/evaluation/scenarios/busy_night.go

func NewBusyNightScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        BusyNight,
            Duration:    4 * time.Hour,
            OrderVolume: 40, // Double normal volume
            StaffCount:  6,
            InventoryLevel: map[string]float64{
                "proteins": 0.8,
                "produce":  0.9,
                "dairy":    0.7,
            },
            Constraints: map[string]interface{}{
                "max_wait_time":    30 * time.Minute,
                "quality_threshold": 0.85,
                "stress_factor":    1.5,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

func (s *BusyNightScenario) EvaluateAgents() map[string]float64 {
    scores := make(map[string]float64)

    // Evaluate Executive Chef
    scores["executive_chef"] = evaluateExecutiveChef(s.Config, []string{
        "order_prioritization",
        "staff_coordination",
        "quality_maintenance",
        "stress_management",
    })

    // Evaluate Sous Chef
    scores["sous_chef"] = evaluateSousChef(s.Config, []string{
        "station_management",
        "expediting_efficiency",
        "staff_support",
    })

    // Evaluate other roles...
    return scores
}
```

### Overstocked Kitchen Scenario

```go
// internal/evaluation/scenarios/overstocked.go

func NewOverstockedScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        Overstocked,
            Duration:    3 * time.Hour,
            OrderVolume: 15,
            StaffCount:  5,
            InventoryLevel: map[string]float64{
                "proteins": 1.5, // 50% over capacity
                "produce":  1.8,
                "dairy":    1.3,
            },
            Constraints: map[string]interface{}{
                "storage_capacity": 0.9,
                "expiry_risk":     0.7,
                "waste_threshold": 0.1,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

func (s *OverstockedScenario) EvaluateInventoryManagement() InventoryMetrics {
    return InventoryMetrics{
        StorageEfficiency: calculateStorageEfficiency(s.Config.InventoryLevel),
        WastePrevention:   evaluateWastePrevention(s.Config),
        CostControl:       evaluateCostControl(s.Config),
    }
}
```

### Slow Business Scenario

```go
// internal/evaluation/scenarios/slow_business.go

func NewSlowBusinessScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        SlowBusiness,
            Duration:    6 * time.Hour,
            OrderVolume: 8, // Low volume
            StaffCount:  4,
            InventoryLevel: map[string]float64{
                "proteins": 0.6,
                "produce":  0.7,
                "dairy":    0.5,
            },
            Constraints: map[string]interface{}{
                "labor_cost_target": 0.25,
                "prep_optimization": 0.8,
                "menu_flexibility": 0.7,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

func (s *SlowBusinessScenario) EvaluateEfficiency() EfficiencyMetrics {
    return EfficiencyMetrics{
        LaborUtilization:  calculateLaborUtilization(s.Config),
        PrepOptimization:  evaluatePrepEfficiency(s.Config),
        ResourceUsage:     evaluateResourceUsage(s.Config),
    }
}
```

### Low Inventory Scenario

```go
// internal/evaluation/scenarios/low_inventory.go

func NewLowInventoryScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        LowInventory,
            Duration:    4 * time.Hour,
            OrderVolume: 20,
            StaffCount:  5,
            InventoryLevel: map[string]float64{
                "proteins": 0.3, // Critical low
                "produce":  0.2,
                "dairy":    0.4,
            },
            Constraints: map[string]interface{}{
                "menu_adaptation": true,
                "substitution_allowed": true,
                "emergency_supply": 0.2,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

func (s *LowInventoryScenario) EvaluateAdaptation() AdaptationMetrics {
    return AdaptationMetrics{
        MenuFlexibility:     evaluateMenuAdaptation(s.Config),
        SupplyManagement:    evaluateSupplyChain(s.Config),
        CustomerSatisfaction: evaluateCustomerImpact(s.Config),
    }
}
```

### High Labor Cost Scenario

```go
// internal/evaluation/scenarios/high_labor.go

func NewHighLaborScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        HighLabor,
            Duration:    5 * time.Hour,
            OrderVolume: 25,
            StaffCount:  7, // Overstaffed
            InventoryLevel: map[string]float64{
                "proteins": 0.7,
                "produce":  0.8,
                "dairy":    0.6,
            },
            Constraints: map[string]interface{}{
                "labor_cost_ratio": 0.4,
                "efficiency_target": 0.85,
                "staff_utilization": 0.7,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

func (s *HighLaborScenario) EvaluateOptimization() OptimizationMetrics {
    return OptimizationMetrics{
        StaffUtilization:   calculateStaffUtilization(s.Config),
        TaskDistribution:   evaluateTaskAllocation(s.Config),
        CostEffectiveness: evaluateLaborCosts(s.Config),
    }
}
```

### Quality Control Scenario

```go
// internal/evaluation/scenarios/quality_control.go

func NewQualityControlScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        QualityControl,
            Duration:    3 * time.Hour,
            OrderVolume: 15,
            StaffCount:  6,
            Constraints: map[string]interface{}{
                "quality_threshold": 0.95,
                "presentation_score": 0.9,
                "taste_score": 0.95,
                "consistency_required": 0.9,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

func (s *QualityControlScenario) EvaluateQuality() QualityMetrics {
    return QualityMetrics{
        Consistency:    evaluateConsistency(s.Config),
        Presentation:   evaluatePresentation(s.Config),
        TasteProfile:   evaluateTaste(s.Config),
        CustomerRating: evaluateCustomerFeedback(s.Config),
    }
}
```

### Scenario Evaluation Metrics

```go
// internal/evaluation/metrics/scenario_metrics.go

type ScenarioMetrics struct {
    AgentPerformance map[string]float64
    TaskCompletion   float64
    Efficiency       float64
    Quality         float64
    Adaptation      float64
    Communication   float64
}

func CalculateScenarioScore(metrics ScenarioMetrics) float64 {
    weights := map[string]float64{
        "agent_performance": 0.3,
        "task_completion":   0.2,
        "efficiency":        0.15,
        "quality":          0.15,
        "adaptation":       0.1,
        "communication":    0.1,
    }

    var score float64
    score += calculateWeightedAverage(metrics.AgentPerformance) * weights["agent_performance"]
    score += metrics.TaskCompletion * weights["task_completion"]
    score += metrics.Efficiency * weights["efficiency"]
    score += metrics.Quality * weights["quality"]
    score += metrics.Adaptation * weights["adaptation"]
    score += metrics.Communication * weights["communication"]

    return score
}
```

### Scenario Runner

```go
// internal/evaluation/runner/scenario_runner.go

type ScenarioRunner struct {
    scenarios map[ScenarioType]Scenario
    metrics   *MetricCollector
    logger    *Logger
}

func (r *ScenarioRunner) RunScenario(scenarioType ScenarioType, agents []Agent) (*Report, error) {
    scenario, exists := r.scenarios[scenarioType]
    if !exists {
        return nil, fmt.Errorf("unknown scenario: %s", scenarioType)
    }

    // Initialize scenario
    if err := scenario.Setup(); err != nil {
        return nil, fmt.Errorf("scenario setup failed: %v", err)
    }

    // Run scenario
    metrics := scenario.Run(agents)

    // Generate report
    report := &Report{
        ScenarioType: scenarioType,
        StartTime:    time.Now(),
        Duration:     scenario.Config.Duration,
        Metrics:      metrics,
        AgentScores:  scenario.EvaluateAgents(),
        Analysis:     analyzeScenarioResults(metrics),
    }

    return report, nil
}
```

## Running the Playground

```bash
# Start all services
docker-compose up -d

# Run the playground server
go run cmd/playground/main.go

# Access the playground
open http://localhost:8080

# View metrics
open http://localhost:3000  # Grafana
open http://localhost:9090  # Prometheus
```

## Development Workflow

1. Start the playground server
2. Select models to evaluate
3. Choose test scenarios
4. Monitor real-time metrics
5. Generate evaluation reports
6. Compare model performance
7. Analyze results in Grafana

## Next Steps

1. Implement additional evaluation scenarios
2. Add more visualization options
3. Enhance real-time monitoring
4. Implement A/B testing capabilities
5. Add support for custom models
6. Create benchmark suites

For detailed API documentation and examples, visit the [project documentation](https://github.com/your-username/masterchef-playground).

### Role-Specific Evaluation Criteria

```go
// internal/evaluation/roles/criteria.go

type RoleEvaluation struct {
    RoleName    string
    Criteria    map[string]EvaluationCriteria
    Weights     map[string]float64
}

type EvaluationCriteria struct {
    Description string
    Metrics     []string
    MinScore    float64
    MaxScore    float64
}

// Executive Chef Criteria
func NewExecutiveChefEvaluation() *RoleEvaluation {
    return &RoleEvaluation{
        RoleName: "executive_chef",
        Criteria: map[string]EvaluationCriteria{
            "leadership": {
                Description: "Ability to lead and coordinate kitchen staff",
                Metrics: []string{
                    "staff_coordination_score",
                    "decision_making_speed",
                    "conflict_resolution_rate",
                },
                MinScore: 0.8,
                MaxScore: 1.0,
            },
            "menu_management": {
                Description: "Menu planning and adaptation",
                Metrics: []string{
                    "menu_innovation_score",
                    "cost_optimization",
                    "seasonal_adaptation",
                },
                MinScore: 0.75,
                MaxScore: 1.0,
            },
            "quality_control": {
                Description: "Maintaining food quality standards",
                Metrics: []string{
                    "dish_consistency",
                    "presentation_score",
                    "taste_rating",
                },
                MinScore: 0.85,
                MaxScore: 1.0,
            },
            "resource_management": {
                Description: "Managing kitchen resources effectively",
                Metrics: []string{
                    "inventory_efficiency",
                    "staff_utilization",
                    "equipment_usage",
                },
                MinScore: 0.7,
                MaxScore: 1.0,
            },
        },
        Weights: map[string]float64{
            "leadership":          0.3,
            "menu_management":     0.25,
            "quality_control":     0.25,
            "resource_management": 0.2,
        },
    }
}

// Sous Chef Criteria
func NewSousChefEvaluation() *RoleEvaluation {
    return &RoleEvaluation{
        RoleName: "sous_chef",
        Criteria: map[string]EvaluationCriteria{
            "operational_execution": {
                Description: "Day-to-day kitchen operations",
                Metrics: []string{
                    "service_flow_management",
                    "station_coordination",
                    "timing_accuracy",
                },
                MinScore: 0.8,
                MaxScore: 1.0,
            },
            "staff_supervision": {
                Description: "Direct supervision of kitchen staff",
                Metrics: []string{
                    "team_performance",
                    "training_effectiveness",
                    "workflow_optimization",
                },
                MinScore: 0.75,
                MaxScore: 1.0,
            },
            "quality_assurance": {
                Description: "Maintaining quality during service",
                Metrics: []string{
                    "plate_inspection_accuracy",
                    "standard_adherence",
                    "consistency_maintenance",
                },
                MinScore: 0.85,
                MaxScore: 1.0,
            },
        },
        Weights: map[string]float64{
            "operational_execution": 0.4,
            "staff_supervision":     0.3,
            "quality_assurance":     0.3,
        },
    }
}

// Line Cook Criteria
func NewLineCookEvaluation() *RoleEvaluation {
    return &RoleEvaluation{
        RoleName: "line_cook",
        Criteria: map[string]EvaluationCriteria{
            "cooking_skills": {
                Description: "Technical cooking abilities",
                Metrics: []string{
                    "technique_mastery",
                    "cooking_precision",
                    "temperature_control",
                },
                MinScore: 0.8,
                MaxScore: 1.0,
            },
            "speed_efficiency": {
                Description: "Speed and efficiency during service",
                Metrics: []string{
                    "ticket_time",
                    "multitasking_ability",
                    "station_organization",
                },
                MinScore: 0.75,
                MaxScore: 1.0,
            },
            "consistency": {
                Description: "Consistency in dish preparation",
                Metrics: []string{
                    "recipe_adherence",
                    "portion_control",
                    "plating_consistency",
                },
                MinScore: 0.85,
                MaxScore: 1.0,
            },
        },
        Weights: map[string]float64{
            "cooking_skills":   0.4,
            "speed_efficiency": 0.3,
            "consistency":      0.3,
        },
    }
}
```

### Additional Scenarios

```go
// internal/evaluation/scenarios/special_event.go

func NewSpecialEventScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        SpecialEvent,
            Duration:    6 * time.Hour,
            OrderVolume: 50,
            StaffCount:  8,
            InventoryLevel: map[string]float64{
                "premium_proteins": 1.0,
                "specialty_produce": 1.0,
                "exotic_ingredients": 0.8,
            },
            Constraints: map[string]interface{}{
                "vip_tables": 5,
                "custom_menu_items": true,
                "presentation_priority": 0.95,
                "timing_critical": true,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

// internal/evaluation/scenarios/equipment_failure.go

func NewEquipmentFailureScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        EquipmentFailure,
            Duration:    4 * time.Hour,
            OrderVolume: 30,
            StaffCount:  6,
            EquipmentStatus: map[string]bool{
                "main_oven": false,
                "grill_station": true,
                "fryer": true,
                "walk_in_cooler": true,
            },
            Constraints: map[string]interface{}{
                "menu_adaptation_required": true,
                "cooking_method_flexibility": true,
                "emergency_procedures": true,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}

// internal/evaluation/scenarios/health_inspection.go

func NewHealthInspectionScenario() *Scenario {
    return &Scenario{
        Config: ScenarioConfig{
            Type:        HealthInspection,
            Duration:    5 * time.Hour,
            OrderVolume: 25,
            StaffCount:  6,
            Constraints: map[string]interface{}{
                "sanitation_priority": 1.0,
                "documentation_required": true,
                "procedure_adherence": 0.98,
                "temperature_monitoring": true,
            },
        },
        Metrics: NewScenarioMetrics(),
    }
}
```

### Enhanced Metric Calculations

```go
// internal/evaluation/metrics/calculations.go

type MetricCalculator struct {
    weights    map[string]float64
    thresholds map[string]float64
    history    []MetricSnapshot
}

// Performance Metrics
func (mc *MetricCalculator) CalculatePerformanceMetrics(data *ScenarioData) PerformanceMetrics {
    return PerformanceMetrics{
        Speed: calculateSpeedScore(data.OrderTimes, data.Config.Constraints),
        Accuracy: calculateAccuracyScore(data.OrderResults),
        Efficiency: calculateEfficiencyScore(data.ResourceUsage),
        Quality: calculateQualityScore(data.QualityChecks),
    }
}

// Time-based Metrics
func calculateSpeedScore(times []OrderTime, constraints map[string]interface{}) float64 {
    var score float64
    targetTime := constraints["target_time"].(float64)

    for _, time := range times {
        ratio := targetTime / time.Duration.Seconds()
        score += math.Min(1.0, ratio)
    }

    return score / float64(len(times))
}

// Quality Metrics
func calculateQualityScore(checks []QualityCheck) float64 {
    weights := map[string]float64{
        "taste":        0.4,
        "presentation": 0.3,
        "temperature":  0.2,
        "consistency":  0.1,
    }

    var weightedScore float64
    for _, check := range checks {
        for aspect, weight := range weights {
            weightedScore += check.Scores[aspect] * weight
        }
    }

    return weightedScore / float64(len(checks))
}

// Resource Efficiency
func calculateEfficiencyScore(usage ResourceUsage) float64 {
    weights := map[string]float64{
        "ingredients": 0.4,
        "equipment":   0.3,
        "labor":      0.3,
    }

    var score float64
    for resource, weight := range weights {
        optimal := usage.OptimalUsage[resource]
        actual := usage.ActualUsage[resource]
        score += (optimal / actual) * weight
    }

    return math.Min(1.0, score)
}

// Coordination Metrics
func calculateCoordinationScore(interactions []Interaction) float64 {
    var score float64

    for _, interaction := range interactions {
        communicationScore := evaluateCommunication(interaction)
        timingScore := evaluateTiming(interaction)
        collaborationScore := evaluateCollaboration(interaction)

        score += (communicationScore*0.4 + timingScore*0.3 + collaborationScore*0.3)
    }

    return score / float64(len(interactions))
}

// Stress Management
func calculateStressManagement(data *ScenarioData) float64 {
    baseStress := calculateBaseStress(data.OrderVolume, data.StaffCount)
    adaptationScore := calculateAdaptationScore(data.StressEvents)
    recoveryScore := calculateRecoveryScore(data.StressResponses)

    return (baseStress*0.3 + adaptationScore*0.4 + recoveryScore*0.3)
}

// Innovation Metrics
func calculateInnovationScore(data *ScenarioData) float64 {
    menuAdaptations := evaluateMenuAdaptations(data.MenuChanges)
    problemSolving := evaluateProblemSolving(data.Challenges)
    creativity := evaluateCreativity(data.Solutions)

    return (menuAdaptations*0.4 + problemSolving*0.3 + creativity*0.3)
}
```

### Metric Aggregation and Analysis

```go
// internal/evaluation/metrics/aggregation.go

type MetricAggregator struct {
    timeWindow time.Duration
    samples    []MetricSample
}

func (ma *MetricAggregator) AggregateMetrics(scenario *Scenario) *AggregatedMetrics {
    return &AggregatedMetrics{
        OverallPerformance: ma.calculateOverallPerformance(scenario),
        RoleSpecific:       ma.aggregateRoleMetrics(scenario),
        Temporal:           ma.analyzeTemporalTrends(scenario),
        Comparative:        ma.compareToBaseline(scenario),
    }
}

func (ma *MetricAggregator) analyzeTemporalTrends(scenario *Scenario) *TemporalAnalysis {
    return &TemporalAnalysis{
        TrendLines:      calculateTrendLines(scenario.Metrics),
        PerformanceDips: identifyPerformanceDips(scenario.Metrics),
        PeakPeriods:     identifyPeakPeriods(scenario.Metrics),
        Seasonality:     analyzeSeasonality(scenario.Metrics),
    }
}

func (ma *MetricAggregator) compareToBaseline(scenario *Scenario) *ComparativeAnalysis {
    return &ComparativeAnalysis{
        BaselineDeviation: calculateBaselineDeviation(scenario),
        ImprovementAreas: identifyImprovementAreas(scenario),
        Recommendations:  generateRecommendations(scenario),
    }
}
```
