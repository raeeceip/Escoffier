package main

import (
	"escoffier/internal/database"
	"escoffier/internal/models"
	"net/http"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

// InitializeAgentRoutes initializes the agent interaction routes
func InitializeAgentRoutes(router *gin.Engine) {
	router.GET("/agents", GetAgents)
	router.POST("/agents", CreateAgent)
	router.PUT("/agents/:id", UpdateAgent)
	router.DELETE("/agents/:id", DeleteAgent)
}

// GetAgents handles GET requests to retrieve all agents
func GetAgents(c *gin.Context) {
	var agents []models.Agent
	database.GetDB().Find(&agents)
	c.JSON(http.StatusOK, agents)
}

// CreateAgent handles POST requests to create a new agent
func CreateAgent(c *gin.Context) {
	var agent models.Agent
	if err := c.ShouldBindJSON(&agent); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	database.GetDB().Create(&agent)
	c.JSON(http.StatusCreated, agent)
}

// UpdateAgent handles PUT requests to update an existing agent
func UpdateAgent(c *gin.Context) {
	var agent models.Agent
	db := database.GetDB()
	if err := db.Where("id = ?", c.Param("id")).First(&agent).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Agent not found"})
		return
	}
	if err := c.ShouldBindJSON(&agent); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	db.Save(&agent)
	c.JSON(http.StatusOK, agent)
}

// DeleteAgent handles DELETE requests to delete an agent
func DeleteAgent(c *gin.Context) {
	var agent models.Agent
	db := database.GetDB()
	if err := db.Where("id = ?", c.Param("id")).First(&agent).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Agent not found"})
		return
	}
	db.Delete(&agent)
	c.JSON(http.StatusNoContent, gin.H{})
}

// ValidateAgentAction validates an agent's action based on kitchen rules
func ValidateAgentAction(agent models.Agent, action string) bool {
	// Placeholder implementation for action validation
	return true
}
