package playground

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// ModelInfo represents information about an available LLM
type ModelInfo struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Type      string `json:"type"`
	MaxTokens int    `json:"maxTokens"`
}

// ScenarioInfo represents information about an available test scenario
type ScenarioInfo struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Type        string `json:"type"`
	Description string `json:"description"`
}

// EvaluationRequest represents a request to evaluate a model on a scenario
type EvaluationRequest struct {
	Model    string `json:"model"`
	Scenario string `json:"scenario"`
}

// handleListModels returns a list of available models
func (s *PlaygroundServer) handleListModels(c *gin.Context) {
	models := []ModelInfo{
		{
			ID:        "gpt4",
			Name:      "GPT-4 Turbo",
			Type:      "openai",
			MaxTokens: 128000,
		},
		{
			ID:        "claude3",
			Name:      "Claude 3 Sonnet",
			Type:      "anthropic",
			MaxTokens: 200000,
		},
		{
			ID:        "gemini",
			Name:      "Gemini 1.5 Pro",
			Type:      "google",
			MaxTokens: 100000,
		},
		{
			ID:        "mixtral",
			Name:      "Mixtral 8x7B",
			Type:      "local",
			MaxTokens: 32000,
		},
	}

	c.JSON(http.StatusOK, models)
}

// handleListScenarios returns a list of available test scenarios
func (s *PlaygroundServer) handleListScenarios(c *gin.Context) {
	scenarios := []ScenarioInfo{
		{
			ID:          "busy_night",
			Name:        "Busy Night",
			Type:        "operational",
			Description: "High-volume service with double the normal orders and limited staff.",
		},
		{
			ID:          "overstocked",
			Name:        "Overstocked Kitchen",
			Type:        "inventory",
			Description: "Manage an overstocked kitchen with expiring ingredients.",
		},
		{
			ID:          "slow_business",
			Name:        "Slow Business",
			Type:        "operational",
			Description: "Optimize kitchen operations during a slow night with low customer volume.",
		},
		{
			ID:          "low_inventory",
			Name:        "Low Inventory",
			Type:        "inventory",
			Description: "Handle service with critically low stock of essential ingredients.",
		},
		{
			ID:          "high_labor",
			Name:        "High Labor Cost",
			Type:        "resource",
			Description: "Optimize staff utilization in an overstaffed kitchen.",
		},
		{
			ID:          "quality_control",
			Name:        "Quality Control",
			Type:        "quality",
			Description: "Maintain stringent quality standards during normal service volume.",
		},
	}

	c.JSON(http.StatusOK, scenarios)
}

// handleMetrics returns current evaluation metrics
func (s *PlaygroundServer) handleMetrics(c *gin.Context) {
	metrics := s.monitor.GetMetrics()
	c.JSON(http.StatusOK, metrics)
}

// handleEvaluate initiates a model evaluation
func (s *PlaygroundServer) handleEvaluate(c *gin.Context) {
	var req EvaluationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Validate model
	if _, err := s.registry.GetModel(req.Model); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid model: " + req.Model})
		return
	}

	// Validate scenario
	if !s.evaluator.HasScenario(req.Scenario) {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid scenario: " + req.Scenario})
		return
	}

	// Start evaluation in background
	go func() {
		s.evaluator.EvaluateModel(req.Model, req.Scenario)
	}()

	c.JSON(http.StatusOK, gin.H{"status": "evaluation_started"})
}
