package api

import (
	"context"
	"net/http"
	"time"

	"escoffier/internal/agents"
	"escoffier/internal/models"

	"github.com/gin-gonic/gin"
	"github.com/tmc/langchaingo/llms"
)

// KitchenAPI represents the main API handler for the kitchen
type KitchenAPI struct {
	Router        *gin.Engine
	ExecutiveChef *agents.ExecutiveChef
	SousChefs     map[string]*agents.SousChef
	DB            Database
}

// Database represents the kitchen's database interface
type Database interface {
	GetOrder(ctx context.Context, id string) (*models.Order, error)
	SaveOrder(ctx context.Context, order *models.Order) error
	GetInventory(ctx context.Context) (map[string]float64, error)
	UpdateInventory(ctx context.Context, updates map[string]float64) error
}

// NewKitchenAPI creates a new kitchen API instance
func NewKitchenAPI(model llms.LLM, db Database) *KitchenAPI {
	router := gin.Default()

	api := &KitchenAPI{
		Router:        router,
		ExecutiveChef: agents.NewExecutiveChef(context.Background(), model),
		SousChefs:     make(map[string]*agents.SousChef),
		DB:            db,
	}

	api.setupRoutes()
	return api
}

// setupRoutes configures all API endpoints
func (k *KitchenAPI) setupRoutes() {
	// Health check
	k.Router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "message": "MasterChef-Bench API is running"})
	})

	v1 := k.Router.Group("/api/v1")
	{
		// Order management
		v1.POST("/orders", k.CreateOrder)
		v1.GET("/orders/:id", k.GetOrder)
		v1.PUT("/orders/:id", k.UpdateOrder)
		v1.DELETE("/orders/:id", k.CancelOrder)

		// Kitchen operations
		v1.GET("/kitchen/status", k.GetKitchenStatus)
		v1.POST("/kitchen/prep", k.StartPreparation)
		v1.POST("/kitchen/cook", k.StartCooking)
		v1.POST("/kitchen/plate", k.StartPlating)

		// Inventory management
		v1.GET("/inventory", k.GetInventory)
		v1.POST("/inventory/update", k.UpdateInventory)
		v1.POST("/inventory/order", k.OrderSupplies)

		// Staff management
		v1.GET("/staff", k.GetStaffStatus)
		v1.POST("/staff/assign", k.AssignStaff)
	}
}

// Order management handlers

func (k *KitchenAPI) CreateOrder(c *gin.Context) {
	var order models.Order
	if err := c.ShouldBindJSON(&order); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Set initial order properties
	order.TimeReceived = time.Now()
	order.Status = "received"

	// Delegate to executive chef
	if err := k.ExecutiveChef.AssignOrder(c.Request.Context(), order); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, order)
}

func (k *KitchenAPI) GetOrder(c *gin.Context) {
	orderID := c.Param("id")
	order, err := k.DB.GetOrder(c.Request.Context(), orderID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
		return
	}

	c.JSON(http.StatusOK, order)
}

func (k *KitchenAPI) UpdateOrder(c *gin.Context) {
	orderID := c.Param("id")
	var updates map[string]interface{}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	order, err := k.DB.GetOrder(c.Request.Context(), orderID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
		return
	}

	// Apply updates
	if status, ok := updates["status"].(string); ok {
		order.Status = status
	}

	if err := k.DB.SaveOrder(c.Request.Context(), order); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, order)
}

func (k *KitchenAPI) CancelOrder(c *gin.Context) {
	orderID := c.Param("id")
	order, err := k.DB.GetOrder(c.Request.Context(), orderID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
		return
	}

	order.Status = "cancelled"
	if err := k.DB.SaveOrder(c.Request.Context(), order); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Order cancelled successfully"})
}

// Kitchen operations handlers

func (k *KitchenAPI) GetKitchenStatus(c *gin.Context) {
	status := k.ExecutiveChef.KitchenStatus
	c.JSON(http.StatusOK, status)
}

func (k *KitchenAPI) StartPreparation(c *gin.Context) {
	var req struct {
		OrderID string `json:"order_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	order, err := k.DB.GetOrder(c.Request.Context(), req.OrderID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
		return
	}

	// Assign to appropriate sous chef
	sousChef := k.selectSousChef(order)
	if err := sousChef.HandleOrder(c.Request.Context(), *order); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Preparation started"})
}

func (k *KitchenAPI) StartCooking(c *gin.Context) {
	// Implement cooking start logic
	c.JSON(http.StatusOK, gin.H{"message": "Cooking started"})
}

func (k *KitchenAPI) StartPlating(c *gin.Context) {
	// Implement plating start logic
	c.JSON(http.StatusOK, gin.H{"message": "Plating started"})
}

// Inventory management handlers

func (k *KitchenAPI) GetInventory(c *gin.Context) {
	inventory, err := k.DB.GetInventory(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, inventory)
}

func (k *KitchenAPI) UpdateInventory(c *gin.Context) {
	var updates map[string]float64
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := k.DB.UpdateInventory(c.Request.Context(), updates); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Inventory updated successfully"})
}

func (k *KitchenAPI) OrderSupplies(c *gin.Context) {
	// Implement supply ordering logic
	c.JSON(http.StatusOK, gin.H{"message": "Supplies ordered"})
}

// Staff management handlers

func (k *KitchenAPI) GetStaffStatus(c *gin.Context) {
	c.JSON(http.StatusOK, k.ExecutiveChef.KitchenStatus.StaffStatus)
}

func (k *KitchenAPI) AssignStaff(c *gin.Context) {
	var req struct {
		StaffID string `json:"staff_id"`
		OrderID string `json:"order_id"`
		Station string `json:"station"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Implement staff assignment logic
	c.JSON(http.StatusOK, gin.H{"message": "Staff assigned successfully"})
}

// Private helper methods

func (k *KitchenAPI) selectSousChef(order *models.Order) *agents.SousChef {
	// Implement sous chef selection logic
	return nil
}
