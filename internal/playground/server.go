package playground

import (
	"masterchef/internal/evaluation"
	"masterchef/internal/models"
	"masterchef/internal/monitoring"

	"github.com/gin-gonic/gin"
)

// PlaygroundServer handles LLM evaluation requests
type PlaygroundServer struct {
	router    *gin.Engine
	registry  *models.ModelRegistry
	evaluator *evaluation.Evaluator
	monitor   *monitoring.Monitor
}

// NewPlaygroundServer creates a new playground server instance
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

// setupRoutes configures the API routes
func (s *PlaygroundServer) setupRoutes() {
	s.router.GET("/", s.handleHome)
	s.router.GET("/ws", s.handleWebSocket)

	// Serve static files
	s.router.Static("/static", "./web/static")
	s.router.LoadHTMLGlob("web/templates/*")

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
	c.HTML(200, "playground.html", gin.H{
		"title": "MasterChef-Bench LLM Playground",
	})
}
