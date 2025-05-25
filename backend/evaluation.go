package main

import (
	"escoffier/internal/database"
	"escoffier/internal/models"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

// InitializeEvaluationRoutes sets up endpoints for the LLM agent evaluation system.
// Provides routes for logging agent actions, collecting performance metrics,
// and retrieving evaluation data for benchmarking and analysis.
func InitializeEvaluationRoutes(router *gin.Engine) {
	router.GET("/evaluation/logs", GetAgentActionLogs)
	router.POST("/evaluation/logs", LogAgentAction)
	router.GET("/evaluation/metrics", GetEvaluationMetrics)
	router.POST("/evaluation/metrics", CollectEvaluationMetrics)
}

// GetAgentActionLogs retrieves comprehensive logs of all agent actions for analysis.
// Returns timestamped records of agent decisions, actions taken, and their outcomes
// used for performance evaluation and behavioral analysis of LLM agents.
func GetAgentActionLogs(c *gin.Context) {
	var logs []models.AgentActionLog
	database.GetDB().Find(&logs)
	c.JSON(http.StatusOK, logs)
}

// LogAgentAction records a specific agent action with context for evaluation.
// Captures action type, timing, decision rationale, and environmental context
// to build comprehensive datasets for agent performance analysis.
func LogAgentAction(c *gin.Context) {
	var log models.AgentActionLog
	if err := c.ShouldBindJSON(&log); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	log.Timestamp = time.Now().Format(time.RFC3339)
	database.GetDB().Create(&log)
	c.JSON(http.StatusCreated, log)
}

// GetEvaluationMetrics retrieves performance metrics for agent benchmarking.
// Returns quantitative measures of agent effectiveness including success rates,
// efficiency scores, decision quality, and comparative performance data.
func GetEvaluationMetrics(c *gin.Context) {
	var metrics []models.EvaluationMetrics
	database.GetDB().Find(&metrics)
	c.JSON(http.StatusOK, metrics)
}

// CollectEvaluationMetrics processes and stores new performance measurements.
// Accepts metric data from various evaluation systems, validates the data,
// and persists it for analysis and reporting purposes.
func CollectEvaluationMetrics(c *gin.Context) {
	var metrics models.EvaluationMetrics
	if err := c.ShouldBindJSON(&metrics); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	metrics.Timestamp = time.Now().Format(time.RFC3339)
	database.GetDB().Create(&metrics)
	c.JSON(http.StatusCreated, metrics)
}
