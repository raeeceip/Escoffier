package main

import (
	"masterchef/internal/database"
	"masterchef/internal/models"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

// InitializeEvaluationRoutes initializes the evaluation system routes
func InitializeEvaluationRoutes(router *gin.Engine) {
	router.GET("/evaluation/logs", GetAgentActionLogs)
	router.POST("/evaluation/logs", LogAgentAction)
	router.GET("/evaluation/metrics", GetEvaluationMetrics)
	router.POST("/evaluation/metrics", CollectEvaluationMetrics)
}

// GetAgentActionLogs handles GET requests to retrieve all agent action logs
func GetAgentActionLogs(c *gin.Context) {
	var logs []models.AgentActionLog
	database.GetDB().Find(&logs)
	c.JSON(http.StatusOK, logs)
}

// LogAgentAction handles POST requests to log an agent's action
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

// GetEvaluationMetrics handles GET requests to retrieve evaluation metrics
func GetEvaluationMetrics(c *gin.Context) {
	var metrics []models.EvaluationMetrics
	database.GetDB().Find(&metrics)
	c.JSON(http.StatusOK, metrics)
}

// CollectEvaluationMetrics handles POST requests to collect evaluation metrics
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
