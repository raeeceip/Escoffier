package monitoring

import (
	"sync"
	"time"
)

// Monitor collects and provides metrics for the playground
type Monitor struct {
	metrics      map[string]interface{}
	metricsMutex sync.RWMutex
	startTime    time.Time
}

// NewMonitor creates a new monitoring instance
func NewMonitor() *Monitor {
	return &Monitor{
		metrics:   make(map[string]interface{}),
		startTime: time.Now(),
	}
}

// RecordMetric records a metric value
func (m *Monitor) RecordMetric(name string, value interface{}) {
	m.metricsMutex.Lock()
	defer m.metricsMutex.Unlock()
	m.metrics[name] = value
}

// GetMetric returns a specific metric value
func (m *Monitor) GetMetric(name string) (interface{}, bool) {
	m.metricsMutex.RLock()
	defer m.metricsMutex.RUnlock()
	value, exists := m.metrics[name]
	return value, exists
}

// GetMetrics returns all current metrics
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
