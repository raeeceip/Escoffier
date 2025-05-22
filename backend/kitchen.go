package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sort"
	"strings"
	"time"

	"masterchef/internal/database"
	"masterchef/internal/models"

	"github.com/gin-gonic/gin"
)

// SimulateTime simulates the passage of time in the kitchen
func SimulateTime(duration time.Duration) {
	time.Sleep(duration)
}

// ValidateKitchenAction validates if a kitchen action is possible
func ValidateKitchenAction(action string) bool {
	// Define allowed actions
	allowedActions := map[string]bool{
		"cook":      true,
		"prep":      true,
		"plate":     true,
		"serve":     true,
		"clean":     true,
		"store":     true,
		"retrieve":  true,
		"inventory": true,
		"order":     true,
		"staff":     true,
	}

	// Check if the action is allowed
	if allowed, exists := allowedActions[action]; exists && allowed {
		return true
	}

	// Handle composite actions (e.g., "cook_steak")
	for allowedAction := range allowedActions {
		if strings.HasPrefix(action, allowedAction+"_") {
			return true
		}
	}

	return false
}

// ProcessRecipe processes a cooking recipe
func ProcessRecipe(recipeName string) error {
	// Check if recipe exists
	if !recipeExists(recipeName) {
		return fmt.Errorf("recipe not found: %s", recipeName)
	}

	// Load recipe
	recipe, err := loadRecipe(recipeName)
	if err != nil {
		return fmt.Errorf("failed to load recipe: %w", err)
	}

	// Check ingredient availability
	if err := checkIngredients(recipe); err != nil {
		return fmt.Errorf("ingredient check failed: %w", err)
	}

	// Reserve equipment
	if err := reserveEquipment(recipe); err != nil {
		return fmt.Errorf("equipment reservation failed: %w", err)
	}

	// Execute recipe steps
	if err := executeRecipeSteps(recipe); err != nil {
		// Release equipment if execution fails
		releaseEquipment(recipe)
		return fmt.Errorf("recipe execution failed: %w", err)
	}

	// Update inventory
	if err := updateInventory(recipe); err != nil {
		return fmt.Errorf("inventory update failed: %w", err)
	}

	// Record recipe execution
	recordRecipeExecution(recipe)

	return nil
}

// Helper functions for recipe processing

// recipeExists checks if a recipe exists in the database
func recipeExists(recipeName string) bool {
	db := database.GetDB()
	var count int64
	db.Model(&models.Recipe{}).Where("name = ?", recipeName).Count(&count)
	return count > 0
}

// loadRecipe loads a recipe from the database
func loadRecipe(recipeName string) (*models.Recipe, error) {
	db := database.GetDB()
	var recipe models.Recipe

	if err := db.Where("name = ?", recipeName).First(&recipe).Error; err != nil {
		return nil, err
	}

	// Load related data (steps and ingredients would be in JSON fields)
	var steps []models.CookingStep
	var ingredients []models.IngredientRequirement

	// Deserialize steps and ingredients if available
	if recipe.StepsJSON != "" {
		if err := json.Unmarshal([]byte(recipe.StepsJSON), &steps); err != nil {
			return nil, fmt.Errorf("failed to deserialize recipe steps: %w", err)
		}
	}

	if recipe.IngredientsJSON != "" {
		if err := json.Unmarshal([]byte(recipe.IngredientsJSON), &ingredients); err != nil {
			return nil, fmt.Errorf("failed to deserialize recipe ingredients: %w", err)
		}
	}

	// Set the steps and ingredients (even though we already have them in JSON form)
	// This maintains compatibility with the existing code
	if err := recipe.SetSteps(steps); err != nil {
		return nil, fmt.Errorf("failed to set recipe steps: %w", err)
	}

	if err := recipe.SetIngredients(ingredients); err != nil {
		return nil, fmt.Errorf("failed to set recipe ingredients: %w", err)
	}

	return &recipe, nil
}

// checkIngredients verifies that all required ingredients are available
func checkIngredients(recipe *models.Recipe) error {
	db := database.GetDB()

	// Get the ingredients
	ingredients, err := recipe.GetIngredients()
	if err != nil {
		return fmt.Errorf("failed to parse recipe ingredients: %w", err)
	}

	// Check each ingredient
	for _, ingredient := range ingredients {
		var inventoryItem models.InventoryItem

		if err := db.Where("name = ?", ingredient.Name).First(&inventoryItem).Error; err != nil {
			return fmt.Errorf("ingredient %s not found in inventory", ingredient.Name)
		}

		if inventoryItem.Quantity < ingredient.Quantity {
			return fmt.Errorf("insufficient quantity of %s (have: %.2f, need: %.2f)",
				ingredient.Name, inventoryItem.Quantity, ingredient.Quantity)
		}
	}

	return nil
}

// reserveEquipment marks equipment as in-use for the recipe
func reserveEquipment(recipe *models.Recipe) error {
	db := database.GetDB()

	// Get the steps
	steps, err := recipe.GetSteps()
	if err != nil {
		return fmt.Errorf("failed to parse recipe steps: %w", err)
	}

	// Get required equipment
	var requiredEquipment []string
	for _, step := range steps {
		requiredEquipment = append(requiredEquipment, step.RequiredEquipment...)
	}

	// Remove duplicates
	equipmentMap := make(map[string]bool)
	for _, eq := range requiredEquipment {
		equipmentMap[eq] = true
	}

	// Check and reserve each piece of equipment
	for equipment := range equipmentMap {
		var kitchenEquipment models.Equipment

		if err := db.Where("name = ?", equipment).First(&kitchenEquipment).Error; err != nil {
			return fmt.Errorf("equipment %s not found", equipment)
		}

		if kitchenEquipment.Status != string(models.EquipmentStatusAvailable) {
			return fmt.Errorf("equipment %s is not available (status: %s)",
				equipment, kitchenEquipment.Status)
		}

		// Reserve equipment
		kitchenEquipment.Status = string(models.EquipmentStatusInUse)
		if err := db.Save(&kitchenEquipment).Error; err != nil {
			return fmt.Errorf("failed to reserve equipment %s: %w", equipment, err)
		}
	}

	return nil
}

// executeRecipeSteps processes each step in the recipe
func executeRecipeSteps(recipe *models.Recipe) error {
	// Get the steps
	steps, err := recipe.GetSteps()
	if err != nil {
		return fmt.Errorf("failed to parse recipe steps: %w", err)
	}

	// Sort steps by sequence number
	sort.Slice(steps, func(i, j int) bool {
		return steps[i].Sequence < steps[j].Sequence
	})

	// Execute each step
	for _, step := range steps {
		// Simulate step execution time
		duration := step.Duration
		if duration == 0 {
			duration = 5 * time.Minute // Default duration if not specified
		}

		// Don't actually sleep in production code
		// This is just for demonstration
		if duration > 0 {
			time.Sleep(duration / 10) // Accelerated for simulation
		}

		// Log step execution
		log.Printf("Executed step %d of recipe %s: %s",
			step.Sequence, recipe.Name, step.Description)
	}

	return nil
}

// releaseEquipment marks equipment as available after use
func releaseEquipment(recipe *models.Recipe) {
	db := database.GetDB()

	// Get the steps
	steps, err := recipe.GetSteps()
	if err != nil {
		log.Printf("Failed to parse recipe steps: %v", err)
		return
	}

	// Get required equipment
	var requiredEquipment []string
	for _, step := range steps {
		requiredEquipment = append(requiredEquipment, step.RequiredEquipment...)
	}

	// Remove duplicates
	equipmentMap := make(map[string]bool)
	for _, eq := range requiredEquipment {
		equipmentMap[eq] = true
	}

	// Release each piece of equipment
	for equipment := range equipmentMap {
		var kitchenEquipment models.Equipment

		if err := db.Where("name = ?", equipment).First(&kitchenEquipment).Error; err != nil {
			log.Printf("Equipment %s not found during release", equipment)
			continue
		}

		// Release equipment
		kitchenEquipment.Status = string(models.EquipmentStatusAvailable)
		if err := db.Save(&kitchenEquipment).Error; err != nil {
			log.Printf("Failed to release equipment %s: %v", equipment, err)
		}
	}
}

// updateInventory reduces inventory levels based on used ingredients
func updateInventory(recipe *models.Recipe) error {
	db := database.GetDB()

	// Get the ingredients
	ingredients, err := recipe.GetIngredients()
	if err != nil {
		return fmt.Errorf("failed to parse recipe ingredients: %w", err)
	}

	// Update each ingredient
	for _, ingredient := range ingredients {
		var inventoryItem models.InventoryItem

		if err := db.Where("name = ?", ingredient.Name).First(&inventoryItem).Error; err != nil {
			return fmt.Errorf("ingredient %s not found in inventory", ingredient.Name)
		}

		// Reduce quantity
		inventoryItem.Quantity -= ingredient.Quantity

		// Update inventory
		if err := db.Save(&inventoryItem).Error; err != nil {
			return fmt.Errorf("failed to update inventory for %s: %w", ingredient.Name, err)
		}
	}

	return nil
}

// recordRecipeExecution logs the recipe execution for tracking
func recordRecipeExecution(recipe *models.Recipe) {
	db := database.GetDB()

	// Find the numeric ID for the recipe in the database
	var dbRecipe models.Recipe

	// First try to find by recipe ID
	err := db.Where("id = ?", recipe.RecipeID).First(&dbRecipe).Error
	if err != nil {
		// If not found by ID, try by name
		err = db.Where("name = ?", recipe.Name).First(&dbRecipe).Error
		if err != nil {
			log.Printf("Failed to find recipe in database by ID or name: %v", err)
			return
		}
	}

	// Create execution record
	execution := models.RecipeExecution{
		RecipeID:   dbRecipe.ID,                                          // Use the gorm.Model ID
		StartTime:  time.Now().Add(-time.Duration(recipe.EstimatedTime)), // Simulate start time
		EndTime:    time.Now(),
		Status:     string(models.ExecutionStatusCompleted),
		Notes:      "Automated execution via API",
		ExecutedBy: "system",
	}

	// Save execution record
	if err := db.Create(&execution).Error; err != nil {
		log.Printf("Failed to record recipe execution: %v", err)
	} else {
		log.Printf("Successfully recorded execution of recipe %s (ID: %s)", recipe.Name, recipe.RecipeID)
	}
}

// GetKitchenStateHandler handles GET requests for kitchen state
func GetKitchenStateHandler(c *gin.Context) {
	db := database.GetDB()
	var kitchen models.Kitchen
	db.First(&kitchen)
	db.Model(&kitchen).Related(&kitchen.Inventory)
	db.Model(&kitchen).Related(&kitchen.Equipment)
	c.JSON(http.StatusOK, kitchen)
}

// UpdateKitchenStateHandler handles POST requests to update kitchen state
func UpdateKitchenStateHandler(c *gin.Context) {
	var kitchen models.Kitchen
	if err := c.ShouldBindJSON(&kitchen); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	db := database.GetDB()
	if err := db.Save(&kitchen).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Kitchen state updated"})
}
