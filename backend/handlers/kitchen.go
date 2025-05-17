package handlers

import (
	"net/http"

	"masterchef/internal/database"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/gorm"
)

// Kitchen represents the state of the kitchen
type Kitchen struct {
	gorm.Model
	Inventory []InventoryItem
	Equipment []EquipmentItem
	Status    string
}

// InventoryItem represents an item in the kitchen inventory
type InventoryItem struct {
	gorm.Model
	Name     string
	Quantity int
}

// EquipmentItem represents an item of equipment in the kitchen
type EquipmentItem struct {
	gorm.Model
	Name   string
	Status string
}

// GetKitchenState retrieves the current state of the kitchen
func GetKitchenState() Kitchen {
	db := database.GetDB()
	var kitchen Kitchen
	db.First(&kitchen)
	db.Model(&kitchen).Related(&kitchen.Inventory)
	db.Model(&kitchen).Related(&kitchen.Equipment)
	return kitchen
}

// UpdateKitchenState updates the state of the kitchen
func UpdateKitchenState(kitchen Kitchen) {
	db := database.GetDB()
	db.Save(&kitchen)
}

// GetKitchenStateHandler handles GET requests for kitchen state
func GetKitchenStateHandler(c *gin.Context) {
	kitchen := GetKitchenState()
	c.JSON(http.StatusOK, kitchen)
}

// UpdateKitchenStateHandler handles POST requests to update kitchen state
func UpdateKitchenStateHandler(c *gin.Context) {
	var kitchen Kitchen
	if err := c.ShouldBindJSON(&kitchen); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	UpdateKitchenState(kitchen)
	c.JSON(http.StatusOK, gin.H{"message": "Kitchen state updated"})
}
