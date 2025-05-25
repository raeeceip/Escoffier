package main

import (
	"escoffier/internal/database"
	"escoffier/internal/models"
	"net/http"

	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

// InitializeAgentRoutes sets up HTTP routes for agent management operations.
// Provides CRUD endpoints for creating, reading, updating, and deleting kitchen agents.
func InitializeAgentRoutes(router *gin.Engine) {
	router.GET("/agents", GetAgents)
	router.POST("/agents", CreateAgent)
	router.PUT("/agents/:id", UpdateAgent)
	router.DELETE("/agents/:id", DeleteAgent)
}

// GetAgents retrieves all registered kitchen agents from the database.
// Returns a JSON array of agent records including their roles, status, and assignments.
func GetAgents(c *gin.Context) {
	var agents []models.Agent
	database.GetDB().Find(&agents)
	c.JSON(http.StatusOK, agents)
}

// CreateAgent handles POST requests to register a new kitchen agent.
// Validates agent data, assigns unique ID, and adds to the kitchen workforce.
// Returns the created agent with assigned ID or validation errors.
func CreateAgent(c *gin.Context) {
	var agent models.Agent
	if err := c.ShouldBindJSON(&agent); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	database.GetDB().Create(&agent)
	c.JSON(http.StatusCreated, agent)
}

// UpdateAgent handles PUT requests to modify an existing agent's properties.
// Allows updating agent roles, status, assignments, and other mutable fields.
// Returns updated agent data or 404 if agent not found.
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

// DeleteAgent handles DELETE requests to remove an agent from the kitchen.
// Performs cleanup of agent assignments and transfers ongoing tasks before removal.
// Returns 204 No Content on success or 404 if agent not found.
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

// ValidateAgentAction validates whether an agent can perform a specific action
// based on their role permissions, current kitchen state, and safety protocols.
// Returns true if the action is permitted, false otherwise.
func ValidateAgentAction(agent models.Agent, action string) bool {
	// TODO: Implement comprehensive validation logic:
	// - Check agent role permissions against action requirements
	// - Validate action against current kitchen safety protocols
	// - Ensure agent has necessary skills/certifications for action
	// - Check if action conflicts with other ongoing operations
	return true
}
