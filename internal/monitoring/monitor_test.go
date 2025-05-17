package monitoring

import (
	"testing"
)

func TestMonitor_GetMetrics(t *testing.T) {
	m := NewMonitor()
	m.RecordMetric("test_metric", 42)

	metrics := m.GetMetrics()

	// Check if our metric is present
	value, exists := metrics["test_metric"]
	if !exists {
		t.Fatalf("Expected 'test_metric' to be present in metrics, but it was not")
	}

	// Check value
	if value != 42 {
		t.Errorf("Expected 'test_metric' to be 42, but got %v", value)
	}

	// Check uptime presence
	_, exists = metrics["uptime_seconds"]
	if !exists {
		t.Errorf("Expected 'uptime_seconds' to be present in metrics, but it was not")
	}
}

func TestMonitor_RecordEvaluationResult(t *testing.T) {
	m := NewMonitor()

	testMetrics := map[string]interface{}{
		"score": 0.85,
		"time":  123,
	}

	m.RecordEvaluationResult("gpt4", "busy_night", testMetrics)

	metrics := m.GetMetrics()

	// Check if metrics are recorded with the proper prefix
	value, exists := metrics["gpt4_busy_night_score"]
	if !exists {
		t.Fatalf("Expected 'gpt4_busy_night_score' to be present in metrics, but it was not")
	}

	if value != 0.85 {
		t.Errorf("Expected 'gpt4_busy_night_score' to be 0.85, but got %v", value)
	}

	// Check timestamp is recorded
	_, exists = metrics["gpt4_busy_night_last_evaluated"]
	if !exists {
		t.Errorf("Expected 'gpt4_busy_night_last_evaluated' to be present in metrics, but it was not")
	}
}

func TestMonitor_Reset(t *testing.T) {
	m := NewMonitor()
	m.RecordMetric("test_metric", 42)

	m.Reset()

	metrics := m.GetMetrics()

	// Our test metric should be gone, but uptime should still be there
	_, exists := metrics["test_metric"]
	if exists {
		t.Errorf("Expected 'test_metric' to be removed after Reset(), but it was present")
	}

	// Uptime should still be present (it's added on GetMetrics call)
	_, exists = metrics["uptime_seconds"]
	if !exists {
		t.Errorf("Expected 'uptime_seconds' to be present in metrics, but it was not")
	}
}
