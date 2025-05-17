package evaluation

import (
	"context"
	"testing"
	"time"

	"masterchef/internal/evaluation"

	"github.com/stretchr/testify/assert"
)

func TestNewMetricsCollector(t *testing.T) {
	collector := evaluation.NewMetricsCollector()

	assert.NotNil(t, collector)
	// Skip private field tests - fields are unexported
	// assert.NotNil(t, collector.registry)
	// assert.NotNil(t, collector.metrics)
	// assert.Len(t, collector.metrics, 4)
}

func TestRecordOrderCompletion(t *testing.T) {
	collector := evaluation.NewMetricsCollector()

	order := &evaluation.Order{
		ID:            "test-order-1",
		Type:          "main_course",
		Complexity:    3,
		TimeReceived:  time.Now().Add(-30 * time.Minute),
		TimeCompleted: time.Now(),
	}

	// Record metrics
	collector.RecordOrderCompletion(order)

	// Verify metrics were recorded (using prometheus test utilities)
	// Note: In a real implementation, you would use prometheus test utilities
	// to verify the actual metric values
}

func TestRecordAccuracy(t *testing.T) {
	collector := evaluation.NewMetricsCollector()

	// Test recording accuracy for different stations and roles
	testCases := []struct {
		station  string
		role     string
		accuracy float64
	}{
		{"hot", "sous_chef", 95.5},
		{"cold", "line_cook", 88.0},
		{"pastry", "chef_de_partie", 92.5},
	}

	for _, tc := range testCases {
		collector.RecordAccuracy(tc.station, tc.role, tc.accuracy)
	}
}

func TestRecordUtilization(t *testing.T) {
	collector := evaluation.NewMetricsCollector()

	// Test recording utilization for different roles and stations
	testCases := []struct {
		role        string
		station     string
		utilization float64
	}{
		{"line_cook", "hot", 85.0},
		{"prep_cook", "cold", 70.0},
		{"sous_chef", "pastry", 90.0},
	}

	for _, tc := range testCases {
		collector.RecordUtilization(tc.role, tc.station, tc.utilization)
	}
}

func TestRecordEfficiency(t *testing.T) {
	collector := evaluation.NewMetricsCollector()

	// Test recording efficiency for different resource types
	testCases := []struct {
		resourceType string
		efficiency   float64
	}{
		{"stove", 88.5},
		{"oven", 92.0},
		{"refrigerator", 95.5},
	}

	for _, tc := range testCases {
		collector.RecordEfficiency(tc.resourceType, tc.efficiency)
	}
}

func TestEvaluateAgent(t *testing.T) {
	ctx := context.Background()

	// Create mock agent and scenario
	agent := &Agent{
		Role: "sous_chef",
		Memory: &Memory{
			ShortTerm: []Event{
				{
					Type:      "order_completed",
					Content:   "Completed order #123",
					Timestamp: time.Now(),
				},
			},
			TaskQueue: []Task{
				{
					ID:        "task1",
					Status:    "completed",
					StartTime: time.Now().Add(-1 * time.Hour),
					EndTime:   time.Now(),
				},
			},
		},
	}

	scenario := &Scenario{
		// Add scenario configuration
	}

	// Evaluate agent
	metrics, err := EvaluateAgent(ctx, agent, scenario)

	// Verify evaluation results
	assert.NoError(t, err)
	assert.NotNil(t, metrics)
	assert.Greater(t, metrics.RoleCoherence, float64(0))
	assert.Greater(t, metrics.TaskCompletion, float64(0))
	assert.Greater(t, metrics.CoordinationScore, float64(0))
	assert.Greater(t, metrics.LongTermConsistency, float64(0))
}

func TestEvaluateRoleCoherence(t *testing.T) {
	ctx := context.Background()

	// Create test agent with various events and tasks
	agent := &Agent{
		Role: "sous_chef",
		Memory: &Memory{
			ShortTerm: []Event{
				{
					Type:    "task_assignment",
					Content: "Assigned prep task",
				},
				{
					Type:    "order_supervision",
					Content: "Supervised order preparation",
				},
			},
		},
	}

	// Evaluate role coherence
	score, err := evaluateRoleCoherence(ctx, agent)

	assert.NoError(t, err)
	assert.Greater(t, score, float64(0))
	assert.LessOrEqual(t, score, float64(1))
}

func TestEvaluateTaskCompletion(t *testing.T) {
	ctx := context.Background()

	// Create test agent with completed tasks
	agent := &Agent{
		Memory: &Memory{
			TaskQueue: []Task{
				{
					Status:    "completed",
					StartTime: time.Now().Add(-30 * time.Minute),
					EndTime:   time.Now(),
				},
				{
					Status:    "completed",
					StartTime: time.Now().Add(-1 * time.Hour),
					EndTime:   time.Now().Add(-30 * time.Minute),
				},
			},
		},
	}

	// Evaluate task completion
	score, err := evaluateTaskCompletion(ctx, agent)

	assert.NoError(t, err)
	assert.Greater(t, score, float64(0))
	assert.LessOrEqual(t, score, float64(1))
}

func TestEvaluateCoordination(t *testing.T) {
	ctx := context.Background()

	// Create test agent with coordination events
	agent := &Agent{
		Memory: &Memory{
			ShortTerm: []Event{
				{
					Type:    "communication",
					Content: "Coordinated with line cook",
				},
				{
					Type:    "resource_allocation",
					Content: "Allocated oven time",
				},
			},
		},
	}

	// Evaluate coordination
	score, err := evaluateCoordination(ctx, agent)

	assert.NoError(t, err)
	assert.Greater(t, score, float64(0))
	assert.LessOrEqual(t, score, float64(1))
}

func TestEvaluateLongTermConsistency(t *testing.T) {
	ctx := context.Background()

	// Create test agent with long-term memory
	agent := &Agent{
		Memory: &Memory{
			LongTerm: &VectorStore{
				embeddings: make(map[string][]float32),
				metadata:   make(map[string]interface{}),
			},
		},
	}

	// Add some test data to long-term memory
	// This would typically involve adding embeddings and metadata

	// Evaluate long-term consistency
	score, err := evaluateLongTermConsistency(ctx, agent)

	assert.NoError(t, err)
	assert.Greater(t, score, float64(0))
	assert.LessOrEqual(t, score, float64(1))
}
