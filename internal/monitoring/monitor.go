package monitoring

import (
	"sync"
	"time"
)

// Monitor provides real-time metrics collection and reporting for the evaluation playground.
// Tracks performance data, resource usage, evaluation progress, and system health
// with thread-safe operations for concurrent access during active evaluations.
type Monitor struct {
	metrics      map[string]interface{}
	metricsMutex sync.RWMutex
	startTime    time.Time
}

// NewMonitor initializes a monitoring system with baseline metrics and timing.
// Sets up thread-safe metric storage, establishes start time for uptime tracking,
// and prepares the system for real-time performance data collection.
func NewMonitor() *Monitor {
	return &Monitor{
		metrics:   make(map[string]interface{}),
		startTime: time.Now(),
	}
}

// RecordMetric safely stores a named metric value with thread-safe access.
// Supports any metric type and maintains data consistency during concurrent
// operations from multiple evaluation sessions and monitoring processes.
func (m *Monitor) RecordMetric(name string, value interface{}) {
	m.metricsMutex.Lock()
	defer m.metricsMutex.Unlock()
	m.metrics[name] = value
}

// GetMetric retrieves a specific metric value with thread-safe read access.
// Returns the current value and existence status for the requested metric,
// ensuring data consistency during concurrent evaluation operations.
func (m *Monitor) GetMetric(name string) (interface{}, bool) {
	m.metricsMutex.RLock()
	defer m.metricsMutex.RUnlock()
	value, exists := m.metrics[name]
	return value, exists
}

// GetMetrics returns a snapshot of all current metrics with system information.
// Creates a thread-safe copy of metric data including uptime calculations,
// providing comprehensive monitoring data for dashboard display and analysis.
func (m *Monitor) GetMetrics() map[string]interface{} {
	m.metricsMutex.RLock()
	defer m.metricsMutex.RUnlock()

	// Create a copy to avoid concurrent map access
	metrics := make(map[string]interface{}, len(m.metrics))
	for k, v := range m.metrics {
		metrics[k] = v
	}

	// Add system metrics
	metrics["uptime_seconds"] = time.Since(m.startTime).Seconds()

	return metrics
}

// Reset clears all metrics
func (m *Monitor) Reset() {
	m.metricsMutex.Lock()
	defer m.metricsMutex.Unlock()
	m.metrics = make(map[string]interface{})
}

// RecordEvaluationResult records metrics from an evaluation result
func (m *Monitor) RecordEvaluationResult(model string, scenario string, metrics map[string]interface{}) {
	m.metricsMutex.Lock()
	defer m.metricsMutex.Unlock()

	prefix := model + "_" + scenario + "_"

	for k, v := range metrics {
		m.metrics[prefix+k] = v
	}

	// Record evaluation timestamp
	m.metrics[prefix+"last_evaluated"] = time.Now().Format(time.RFC3339)
}
