package main

import (
	"github.com/gin-gonic/gin"
	"net/http"
	"time"
)

// AgentActionLog represents a log of an agent's action
type AgentActionLog struct {
	ID        uint      `json:"id"`
	AgentID   uint      `json:"agent_id"`
	Action    string    `json:"action"`
	Timestamp time.Time `json:"timestamp"`
}

// EvaluationMetrics represents the metrics collected for evaluation
type EvaluationMetrics struct {
	ID         uint    `json:"id"`
	AgentID    uint    `json:"agent_id"`
	Coherence  float64 `json:"coherence"`
	Performance float64 `json:"performance"`
}

// InitializeEvaluationRoutes initializes the evaluation system routes
func InitializeEvaluationRoutes(router *gin.Engine) {
	router.GET("/evaluation/logs", GetAgentActionLogs)
	router.POST("/evaluation/logs", LogAgentAction)
	router.GET("/evaluation/metrics", GetEvaluationMetrics)
	router.POST("/evaluation/metrics", CollectEvaluationMetrics)
}

// GetAgentActionLogs handles GET requests to retrieve all agent action logs
func GetAgentActionLogs(c *gin.Context) {
	var logs []AgentActionLog
	db.Find(&logs)
	c.JSON(http.StatusOK, logs)
}

// LogAgentAction handles POST requests to log an agent's action
func LogAgentAction(c *gin.Context) {
	var log AgentActionLog
	if err := c.ShouldBindJSON(&log); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	log.Timestamp = time.Now()
	db.Create(&log)
	c.JSON(http.StatusCreated, log)
}

// GetEvaluationMetrics handles GET requests to retrieve evaluation metrics
func GetEvaluationMetrics(c *gin.Context) {
	var metrics []EvaluationMetrics
	db.Find(&metrics)
	c.JSON(http.StatusOK, metrics)
}

// CollectEvaluationMetrics handles POST requests to collect evaluation metrics
func CollectEvaluationMetrics(c *gin.Context) {
	var metrics EvaluationMetrics
	if err := c.ShouldBindJSON(&metrics); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	db.Create(&metrics)
	c.JSON(http.StatusCreated, metrics)
}
