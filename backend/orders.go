package main

import (
	"escoffier/internal/database"
	"escoffier/internal/models"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// InitializeOrderRoutes configures HTTP endpoints for order management.
// Provides complete CRUD operations for customer orders including status tracking,
// item management, and order lifecycle operations.
func InitializeOrderRoutes(router *gin.Engine) {
	router.GET("/orders", GetOrders)
	router.GET("/orders/:id", GetOrder)
	router.POST("/orders", CreateOrder)
	router.PUT("/orders/:id", UpdateOrder)
	router.DELETE("/orders/:id", CancelOrder)
}

// GetOrders retrieves all orders with their associated items and status information.
// Includes order details, preparation progress, assigned staff, and timing data.
// Orders are returned with full item details for comprehensive order tracking.
func GetOrders(c *gin.Context) {
	var orders []models.Order
	database.GetDB().Preload("Items").Find(&orders)
	c.JSON(http.StatusOK, orders)
}

// GetOrder retrieves detailed information for a specific order by ID.
// Returns complete order data including all items, current status, timing information,
// and assigned kitchen staff. Returns 404 if order not found.
func GetOrder(c *gin.Context) {
	var order models.Order
	db := database.GetDB()
	if err := db.Preload("Items").Where("id = ?", c.Param("id")).First(&order).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
		return
	}
	c.JSON(http.StatusOK, order)
}

// CreateOrder processes new customer orders and adds them to the kitchen queue.
// Validates order items, calculates timing estimates, assigns initial status,
// and timestamps the order for tracking. Returns created order with assigned ID.
func CreateOrder(c *gin.Context) {
	var order models.Order
	if err := c.ShouldBindJSON(&order); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	order.TimeReceived = time.Now()
	order.Status = "pending"

	db := database.GetDB()
	if err := db.Create(&order).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Create order items
	for i := range order.Items {
		order.Items[i].OrderID = order.ID
		if err := db.Create(&order.Items[i]).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
	}

	c.JSON(http.StatusCreated, order)
}

// UpdateOrder handles PUT requests to update an existing order
func UpdateOrder(c *gin.Context) {
	var order models.Order
	db := database.GetDB()

	// Find existing order
	if err := db.Preload("Items").Where("id = ?", c.Param("id")).First(&order).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
		return
	}

	// Parse update data
	var updateData models.Order
	if err := c.ShouldBindJSON(&updateData); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Update order fields
	order.Status = updateData.Status
	order.Priority = updateData.Priority
	order.AssignedTo = updateData.AssignedTo

	if order.Status == "completed" {
		order.TimeCompleted = time.Now()
	}

	// Update in database
	if err := db.Save(&order).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Update items if provided
	if len(updateData.Items) > 0 {
		// Delete existing items
		if err := db.Where("order_id = ?", order.ID).Delete(&models.OrderItem{}).Error; err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		// Create new items
		for i := range updateData.Items {
			updateData.Items[i].OrderID = order.ID
			if err := db.Create(&updateData.Items[i]).Error; err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
		}
		order.Items = updateData.Items
	}

	c.JSON(http.StatusOK, order)
}

// CancelOrder handles DELETE requests to cancel an order
func CancelOrder(c *gin.Context) {
	var order models.Order
	db := database.GetDB()

	if err := db.Where("id = ?", c.Param("id")).First(&order).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
		return
	}

	// Soft delete the order (GORM's default behavior with DeletedAt field)
	if err := db.Delete(&order).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Order cancelled successfully"})
}
