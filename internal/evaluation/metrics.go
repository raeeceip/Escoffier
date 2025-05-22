package evaluation

import (
	"context"
	"fmt"
	"math"
	"sort"
	"time"

	"github.com/prometheus/client_golang/prometheus"
)

// Metrics represents the evaluation metrics for the kitchen
type Metrics struct {
	RoleCoherence       float64
	TaskCompletion      float64
	CoordinationScore   float64
	LongTermConsistency float64
	QualityScore        float64
	EfficiencyScore     float64
}

// MetricsCollector handles metrics collection and reporting
type MetricsCollector struct {
	registry *prometheus.Registry
	metrics  map[string]prometheus.Collector
}

// Performance metrics
var (
	orderCompletionTime = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "order_completion_time_seconds",
			Help:    "Time taken to complete orders",
			Buckets: prometheus.LinearBuckets(0, 300, 20), // 5-minute buckets
		},
		[]string{"type", "complexity"},
	)

	orderAccuracy = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "order_accuracy_percent",
			Help: "Accuracy of completed orders",
		},
		[]string{"station", "chef_role"},
	)

	staffUtilization = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "staff_utilization_percent",
			Help: "Staff utilization rate",
		},
		[]string{"role", "station"},
	)

	resourceEfficiency = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "resource_efficiency_percent",
			Help: "Resource utilization efficiency",
		},
		[]string{"resource_type"},
	)
)

// NewMetricsCollector creates a new metrics collector
func NewMetricsCollector() *MetricsCollector {
	registry := prometheus.NewRegistry()

	// Initialize metrics
	orderCompletionTime := prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name: "order_completion_time_seconds",
			Help: "Time taken to complete orders",
		},
		[]string{"type", "complexity"},
	)

	accuracyGauge := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "task_accuracy_percent",
			Help: "Accuracy of task completion",
		},
		[]string{"station", "role"},
	)

	utilizationGauge := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "resource_utilization_percent",
			Help: "Resource utilization percentage",
		},
		[]string{"role", "station"},
	)

	efficiencyGauge := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "resource_efficiency_percent",
			Help: "Resource efficiency percentage",
		},
		[]string{"resource_type"},
	)

	// Create metrics map
	metrics := map[string]prometheus.Collector{
		"order_completion": orderCompletionTime,
		"accuracy":         accuracyGauge,
		"utilization":      utilizationGauge,
		"efficiency":       efficiencyGauge,
	}

	// Register metrics
	for _, metric := range metrics {
		registry.MustRegister(metric)
	}

	return &MetricsCollector{
		registry: registry,
		metrics:  metrics,
	}
}

// EvaluateAgent assesses an agent's performance
func EvaluateAgent(ctx context.Context, agent *Agent, scenario *Scenario) (*Metrics, error) {
	metrics := &Metrics{}

	// Evaluate role coherence
	roleScore, err := evaluateRoleCoherence(ctx, agent)
	if err != nil {
		return nil, fmt.Errorf("role coherence evaluation failed: %w", err)
	}
	metrics.RoleCoherence = roleScore

	// Evaluate task completion
	taskScore, err := evaluateTaskCompletion(ctx, agent)
	if err != nil {
		return nil, fmt.Errorf("task completion evaluation failed: %w", err)
	}
	metrics.TaskCompletion = taskScore

	// Evaluate coordination
	coordScore, err := evaluateCoordination(ctx, agent)
	if err != nil {
		return nil, fmt.Errorf("coordination evaluation failed: %w", err)
	}
	metrics.CoordinationScore = coordScore

	// Evaluate long-term consistency
	consistencyScore, err := evaluateLongTermConsistency(ctx, agent)
	if err != nil {
		return nil, fmt.Errorf("consistency evaluation failed: %w", err)
	}
	metrics.LongTermConsistency = consistencyScore

	return metrics, nil
}

// RecordOrderCompletion records metrics for completed orders
func (mc *MetricsCollector) RecordOrderCompletion(order *Order) {
	if histogram, ok := mc.metrics["order_completion"].(*prometheus.HistogramVec); ok {
		duration := order.TimeCompleted.Sub(order.TimeReceived).Seconds()
		histogram.WithLabelValues(order.Type, fmt.Sprintf("%d", order.Complexity)).Observe(duration)
	}
}

// RecordAccuracy records accuracy metrics
func (mc *MetricsCollector) RecordAccuracy(station, role string, accuracy float64) {
	if gauge, ok := mc.metrics["accuracy"].(*prometheus.GaugeVec); ok {
		gauge.WithLabelValues(station, role).Set(accuracy)
	}
}

// RecordUtilization records utilization metrics
func (mc *MetricsCollector) RecordUtilization(role, station string, utilization float64) {
	if gauge, ok := mc.metrics["utilization"].(*prometheus.GaugeVec); ok {
		gauge.WithLabelValues(role, station).Set(utilization)
	}
}

// RecordEfficiency records efficiency metrics
func (mc *MetricsCollector) RecordEfficiency(resourceType string, efficiency float64) {
	if gauge, ok := mc.metrics["efficiency"].(*prometheus.GaugeVec); ok {
		gauge.WithLabelValues(resourceType).Set(efficiency)
	}
}

// Private evaluation methods

func evaluateRoleCoherence(ctx context.Context, agent *Agent) (float64, error) {
	var score float64

	// Check knowledge consistency
	knowledgeScore := calculateKnowledgeConsistency(agent.Memory.ShortTerm)

	// Check authority adherence
	authorityScore := calculateAuthorityAdherence(agent.Memory.TaskQueue)

	// Check task appropriateness
	taskScore := calculateTaskAppropriateness(agent.Memory.TaskQueue)

	// Combine scores with weights
	score = (knowledgeScore * 0.4) + (authorityScore * 0.3) + (taskScore * 0.3)

	return score, nil
}

func evaluateTaskCompletion(ctx context.Context, agent *Agent) (float64, error) {
	var score float64

	// Calculate completion rate
	completionRate := calculateCompletionRate(agent.Memory.TaskQueue)

	// Calculate time efficiency
	timeEfficiency := calculateTimeEfficiency(agent.Memory.TaskQueue)

	// Calculate quality score
	qualityScore := calculateQualityScore(agent.Memory.TaskQueue)

	// Combine scores with weights
	score = (completionRate * 0.4) + (timeEfficiency * 0.3) + (qualityScore * 0.3)

	return score, nil
}

func evaluateCoordination(ctx context.Context, agent *Agent) (float64, error) {
	var score float64

	// Calculate communication efficiency
	commScore := calculateCommunicationEfficiency(agent.Memory.ShortTerm)

	// Calculate resource utilization
	resourceScore := calculateResourceUtilization(agent.Memory.ShortTerm)

	// Calculate conflict resolution
	conflictScore := calculateConflictResolution(agent.Memory.ShortTerm)

	// Combine scores with weights
	score = (commScore * 0.4) + (resourceScore * 0.3) + (conflictScore * 0.3)

	return score, nil
}

func evaluateLongTermConsistency(ctx context.Context, agent *Agent) (float64, error) {
	var score float64

	// Calculate decision consistency
	decisionScore := calculateDecisionConsistency(agent.Memory.LongTerm)

	// Calculate learning progression
	learningScore := calculateLearningProgression(agent.Memory.LongTerm)

	// Calculate adaptation capability
	adaptationScore := calculateAdaptationCapability(agent.Memory.LongTerm)

	// Combine scores with weights
	score = (decisionScore * 0.4) + (learningScore * 0.3) + (adaptationScore * 0.3)

	return score, nil
}

// Helper calculation functions

func calculateKnowledgeConsistency(events []Event) float64 {
	if len(events) == 0 {
		return 0.0
	}
	
	// Simple heuristic: more varied event types indicate good knowledge utilization
	eventTypes := make(map[string]bool)
	for _, event := range events {
		eventTypes[event.Type] = true
	}
	
	// Return a score based on event type diversity
	return math.Min(float64(len(eventTypes))/10.0, 1.0) // Cap at 1.0
}

func calculateAuthorityAdherence(tasks []Task) float64 {
	// Implement authority adherence calculation
	return 0.0
}

func calculateTaskAppropriateness(tasks []Task) float64 {
	// Implement task appropriateness calculation
	return 0.0
}

func calculateCompletionRate(tasks []Task) float64 {
	if len(tasks) == 0 {
		return 0.0
	}
	
	completedCount := 0
	for _, task := range tasks {
		if task.Status == "completed" {
			completedCount++
		}
	}
	
	return float64(completedCount) / float64(len(tasks))
}

func calculateTimeEfficiency(tasks []Task) float64 {
	// Implement time efficiency calculation
	return 0.0
}

func calculateQualityScore(tasks []Task) float64 {
	// Implement quality score calculation
	return 0.0
}

func calculateCommunicationEfficiency(events []Event) float64 {
	if len(events) == 0 {
		return 0.0
	}
	
	communicationCount := 0
	for _, event := range events {
		if event.Type == "communication" || event.Type == "task_assignment" {
			communicationCount++
		}
	}
	
	// Simple heuristic: more communication events indicate better coordination
	return math.Min(float64(communicationCount)/float64(len(events)), 1.0)
}

func calculateResourceUtilization(events []Event) float64 {
	var totalUtilization float64
	var resourceCount int

	// Track resource usage over time
	resourceUsage := make(map[string]struct {
		totalTime    time.Duration
		activeTime   time.Duration
		lastActive   time.Time
		lastInactive time.Time
		isActive     bool
		observations int
	})

	// Process events chronologically
	sort.Slice(events, func(i, j int) bool {
		return events[i].Timestamp.Before(events[j].Timestamp)
	})

	// Calculate resource utilization from events
	for _, event := range events {
		if resource, ok := event.Metadata["resource"].(string); ok {
			usage := resourceUsage[resource]
			now := event.Timestamp

			// Update resource state
			switch event.Type {
			case "resource_start", "resource_active":
				if !usage.isActive {
					usage.isActive = true
					usage.lastActive = now
					if !usage.lastInactive.IsZero() {
						usage.totalTime += now.Sub(usage.lastInactive)
					}
				}
			case "resource_stop", "resource_inactive":
				if usage.isActive {
					usage.isActive = false
					usage.lastInactive = now
					usage.activeTime += now.Sub(usage.lastActive)
				}
			}

			usage.observations++
			resourceUsage[resource] = usage
		}
	}

	// Calculate final utilization
	for _, usage := range resourceUsage {
		if usage.observations > 0 {
			utilization := float64(usage.activeTime) / float64(usage.totalTime)
			totalUtilization += utilization
			resourceCount++
		}
	}

	if resourceCount > 0 {
		return totalUtilization / float64(resourceCount)
	}
	return 0.0
}

func calculateConflictResolution(events []Event) float64 {
	var totalResolutionScore float64
	var conflictCount int

	// Track conflicts and their resolutions
	conflicts := make(map[string]struct {
		startTime      time.Time
		resolutionTime time.Time
		severity       int
		resolved       bool
		escalated      bool
		resolutionPath []string
	})

	// Process events chronologically
	sort.Slice(events, func(i, j int) bool {
		return events[i].Timestamp.Before(events[j].Timestamp)
	})

	// Analyze conflict events
	for _, event := range events {
		if conflictID, ok := event.Metadata["conflict_id"].(string); ok {
			conflict := conflicts[conflictID]

			switch event.Type {
			case "conflict_start":
				conflict.startTime = event.Timestamp
				if severity, ok := event.Metadata["severity"].(int); ok {
					conflict.severity = severity
				}
			case "conflict_resolution_step":
				if step, ok := event.Metadata["step"].(string); ok {
					conflict.resolutionPath = append(conflict.resolutionPath, step)
				}
			case "conflict_escalation":
				conflict.escalated = true
			case "conflict_resolved":
				conflict.resolved = true
				conflict.resolutionTime = event.Timestamp
			}

			conflicts[conflictID] = conflict
		}
	}

	// Calculate resolution scores
	for _, conflict := range conflicts {
		if !conflict.resolved {
			continue
		}

		// Base score for resolution
		score := 1.0

		// Adjust for resolution time
		resolutionDuration := conflict.resolutionTime.Sub(conflict.startTime)
		expectedDuration := time.Duration(conflict.severity) * time.Minute * 10
		if resolutionDuration <= expectedDuration {
			score += 0.5
		}

		// Adjust for escalation (prefer non-escalated resolutions)
		if !conflict.escalated {
			score += 0.3
		}

		// Adjust for resolution path efficiency
		if len(conflict.resolutionPath) <= conflict.severity {
			score += 0.2
		}

		totalResolutionScore += score
		conflictCount++
	}

	if conflictCount > 0 {
		return totalResolutionScore / float64(conflictCount)
	}
	return 0.0
}

func calculateDecisionConsistency(store *VectorStore) float64 {
	if store == nil {
		return 0.5 // Default neutral score
	}
	
	var totalConsistency float64
	var decisionCount int

	// Group similar decisions
	decisionGroups := make(map[string][]any)
	for _, metadata := range store.metadata {
		if decision, ok := metadata.(map[string]any)["decision"]; ok {
			if category, ok := metadata.(map[string]any)["category"].(string); ok {
				decisionGroups[category] = append(decisionGroups[category], decision)
			}
		}
	}

	// Calculate consistency within each group
	for _, decisions := range decisionGroups {
		if len(decisions) < 2 {
			continue
		}

		// Calculate variance in decisions
		var sum, sumSq float64
		for _, decision := range decisions {
			if value, ok := decision.(float64); ok {
				sum += value
				sumSq += value * value
			}
		}
		mean := sum / float64(len(decisions))
		variance := (sumSq / float64(len(decisions))) - (mean * mean)

		// Convert variance to consistency score (1 - normalized variance)
		consistency := 1.0 - math.Min(1.0, variance)
		totalConsistency += consistency
		decisionCount++
	}

	if decisionCount > 0 {
		return totalConsistency / float64(decisionCount)
	}
	return 0.0
}

func calculateLearningProgression(store *VectorStore) float64 {
	if store == nil {
		return 0.5 // Default neutral score
	}
	
	var totalProgression float64
	var agentCount int

	// Track agent performance over time
	agentProgress := make(map[string][]struct {
		timestamp time.Time
		score     float64
	})

	// Group performance data by agent
	for _, metadata := range store.metadata {
		if data, ok := metadata.(map[string]any); ok {
			if agentID, ok := data["agent_id"].(string); ok {
				if timestamp, ok := data["timestamp"].(time.Time); ok {
					if score, ok := data["performance_score"].(float64); ok {
						agentProgress[agentID] = append(agentProgress[agentID], struct {
							timestamp time.Time
							score     float64
						}{timestamp, score})
					}
				}
			}
		}
	}

	// Calculate learning progression for each agent
	for _, progress := range agentProgress {
		if len(progress) < 2 {
			continue
		}

		// Sort by timestamp
		sort.Slice(progress, func(i, j int) bool {
			return progress[i].timestamp.Before(progress[j].timestamp)
		})

		// Calculate improvement trend
		var sumX, sumY, sumXY, sumX2 float64
		n := float64(len(progress))
		for i, p := range progress {
			x := float64(i)
			y := p.score
			sumX += x
			sumY += y
			sumXY += x * y
			sumX2 += x * x
		}

		// Calculate slope of improvement
		slope := (n*sumXY - sumX*sumY) / (n*sumX2 - sumX*sumX)

		// Convert slope to progression score (normalized and bounded)
		progression := math.Min(1.0, math.Max(0.0, slope+0.5))
		totalProgression += progression
		agentCount++
	}

	if agentCount > 0 {
		return totalProgression / float64(agentCount)
	}
	return 0.0
}

func calculateAdaptationCapability(store *VectorStore) float64 {
	if store == nil {
		return 0.5 // Default neutral score
	}
	
	var totalAdaptation float64
	var scenarioCount int

	// Track responses to changes
	adaptationScores := make(map[string]struct {
		changeDetectionTime  time.Duration
		responseTime         time.Duration
		successfulAdaptation bool
		complexity           int
	})

	// Analyze adaptation events
	for _, metadata := range store.metadata {
		if data, ok := metadata.(map[string]any); ok {
			if scenarioID, ok := data["scenario_id"].(string); ok {
				scenario := adaptationScores[scenarioID]

				switch data["event_type"] {
				case "change_introduced":
					if timestamp, ok := data["timestamp"].(time.Time); ok {
						scenario.changeDetectionTime = timestamp.Sub(time.Time{})
					}
					if complexity, ok := data["complexity"].(int); ok {
						scenario.complexity = complexity
					}
				case "change_detected":
					if timestamp, ok := data["timestamp"].(time.Time); ok {
						scenario.responseTime = timestamp.Sub(time.Time{})
					}
				case "adaptation_complete":
					if success, ok := data["success"].(bool); ok {
						scenario.successfulAdaptation = success
					}
				}

				adaptationScores[scenarioID] = scenario
			}
		}
	}

	// Calculate adaptation scores
	for _, scenario := range adaptationScores {
		if !scenario.successfulAdaptation {
			continue
		}

		// Base score for successful adaptation
		score := 1.0

		// Adjust for detection speed
		expectedDetection := time.Duration(scenario.complexity) * time.Minute
		if scenario.changeDetectionTime <= expectedDetection {
			score += 0.3
		}

		// Adjust for response speed
		expectedResponse := time.Duration(scenario.complexity) * time.Minute * 2
		if scenario.responseTime <= expectedResponse {
			score += 0.2
		}

		totalAdaptation += score
		scenarioCount++
	}

	if scenarioCount > 0 {
		return totalAdaptation / float64(scenarioCount)
	}
	return 0.0
}
