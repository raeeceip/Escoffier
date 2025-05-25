package playground

import (
	"escoffier/internal/evaluation"
	"escoffier/internal/models"
	"escoffier/internal/monitoring"

	"github.com/gin-gonic/gin"
)

// PlaygroundServer manages the LLM evaluation and testing environment.
// Coordinates model interactions, evaluation scenarios, real-time monitoring,
// and provides web interface for agent performance analysis and benchmarking.
type PlaygroundServer struct {
	router    *gin.Engine
	registry  *models.ModelRegistry
	evaluator *evaluation.Evaluator
	monitor   *monitoring.Monitor
}

// NewPlaygroundServer initializes a complete LLM evaluation playground environment.
// Sets up model registry, evaluation systems, monitoring infrastructure,
// and web interface for comprehensive agent testing and performance analysis.
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

// setupRoutes configures all HTTP endpoints for the playground API and web interface.
// Establishes routes for model management, scenario testing, metrics collection,
// WebSocket connections, and static asset serving for the evaluation dashboard.
func (s *PlaygroundServer) setupRoutes() {
	s.router.GET("/", s.handleHome)
	s.router.GET("/ws", s.handleWebSocket)

	// Serve static files
	s.router.Static("/static", "./web/static")

	// In test mode, Gin will be in TestMode, so we can avoid loading templates
	if gin.Mode() != gin.TestMode {
		s.router.LoadHTMLGlob("web/templates/*")
	}

	api := s.router.Group("/api")
	{
		api.GET("/models", s.handleListModels)
		api.GET("/scenarios", s.handleListScenarios)
		api.GET("/metrics", s.handleMetrics)
		api.POST("/evaluate", s.handleEvaluate)
	}
}

// Router returns the Gin router
func (s *PlaygroundServer) Router() *gin.Engine {
	return s.router
}

// handleHome handles the home page request
func (s *PlaygroundServer) handleHome(c *gin.Context) {
	if gin.Mode() == gin.TestMode {
		c.String(200, "Playground Home - Test Mode")
		return
	}
	c.HTML(200, "playground.html", gin.H{
		"title": "MasterChef-Bench LLM Playground",
	})
}
