package main

import (
	"escoffier/internal/database"
	"escoffier/internal/models"
	"fmt"
	"log"
	"time"

	"github.com/jinzhu/gorm"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

var db *gorm.DB

// Kitchen represents the complete state and configuration of the kitchen environment.
// Tracks operational status, active sessions, and overall kitchen readiness
// for coordinating all kitchen activities and agent operations.
type Kitchen struct {
	gorm.Model
	Status string
}

// InventoryItem represents individual ingredients and supplies in kitchen storage.
// Tracks quantities, expiration dates, storage locations, and availability
// for recipe planning and automatic inventory management.
type InventoryItem struct {
	gorm.Model
	KitchenID uint
	Name      string
	Quantity  int
}

// EquipmentItem represents kitchen tools and appliances with their operational status.
// Manages equipment availability, maintenance schedules, and usage tracking
// for efficient kitchen resource allocation and workflow optimization.
type EquipmentItem struct {
	gorm.Model
	KitchenID uint
	Name      string
	Status    string
}

// InitializeDatabase creates and configures all required database tables and relationships.
// Sets up the complete schema for kitchen operations, agent management, order tracking,
// evaluation metrics, and all supporting data structures with proper indexing.
func InitializeDatabase() {
	db := database.GetDB()
	db.AutoMigrate(
		&Kitchen{},
		&InventoryItem{},
		&EquipmentItem{},
		&models.Agent{},
		&models.AgentActionLog{},
		&models.EvaluationMetrics{},
		&models.Order{},
		&models.OrderItem{},
		&models.Recipe{},
		&models.RecipeExecution{},
		&models.Equipment{},
	)

	// After migration, ensure default data exists
	seedDefaultData(db)
}

// seedDefaultData ensures essential data exists in the database
func seedDefaultData(db *gorm.DB) {
	// Create default kitchen if it doesn't exist
	var kitchenCount int64
	db.Model(&Kitchen{}).Count(&kitchenCount)
	if kitchenCount == 0 {
		kitchen := Kitchen{
			Status: "operational",
		}
		db.Create(&kitchen)
	}

	// Create default equipment if none exists
	var equipmentCount int64
	db.Model(&models.Equipment{}).Count(&equipmentCount)
	if equipmentCount == 0 {
		defaultEquipment := []models.Equipment{
			{Name: "Oven", Type: string(models.EquipmentTypeCooking), Status: string(models.EquipmentStatusAvailable), Station: "hot"},
			{Name: "Grill", Type: string(models.EquipmentTypeCooking), Status: string(models.EquipmentStatusAvailable), Station: "hot"},
			{Name: "Refrigerator", Type: string(models.EquipmentTypeStorage), Status: string(models.EquipmentStatusAvailable), Station: "prep"},
			{Name: "Mixer", Type: string(models.EquipmentTypeAppliance), Status: string(models.EquipmentStatusAvailable), Station: "pastry"},
		}
		for _, equipment := range defaultEquipment {
			db.Create(&equipment)
		}
	}

	// Create default inventory items if none exist
	var inventoryCount int64
	db.Model(&InventoryItem{}).Count(&inventoryCount)
	if inventoryCount == 0 {
		defaultInventory := []InventoryItem{
			{Name: "Flour", Quantity: 100},
			{Name: "Sugar", Quantity: 50},
			{Name: "Salt", Quantity: 20},
			{Name: "Chicken", Quantity: 30},
			{Name: "Beef", Quantity: 25},
			{Name: "Tomatoes", Quantity: 40},
			{Name: "Lettuce", Quantity: 15},
		}
		for _, item := range defaultInventory {
			db.Create(&item)
		}
	}

	// Create sample recipes if none exist
	var recipeCount int64
	db.Model(&models.Recipe{}).Count(&recipeCount)
	if recipeCount == 0 {
		createSampleRecipes(db)
	}
}

// createSampleRecipes creates sample recipes for testing
func createSampleRecipes(db *gorm.DB) {
	// Create a simple recipe
	pastaRecipe := models.Recipe{
		RecipeID:      "pasta-1",
		Name:          "Simple Pasta",
		Description:   "A quick and easy pasta dish",
		Category:      "main",
		Complexity:    2,
		PrepTime:      15 * time.Minute,
		CookTime:      20 * time.Minute,
		EstimatedTime: 35 * time.Minute,
		Servings:      4,
		Equipment:     models.StringSlice{"pot", "pan", "colander"},
		Tags:          models.StringSlice{"pasta", "quick", "easy"},
	}

	// Create ingredients
	ingredients := []models.IngredientRequirement{
		{ID: "ing-1", Name: "Pasta", Quantity: 500, Unit: "g"},
		{ID: "ing-2", Name: "Tomato Sauce", Quantity: 400, Unit: "g"},
		{ID: "ing-3", Name: "Olive Oil", Quantity: 2, Unit: "tbsp"},
		{ID: "ing-4", Name: "Salt", Quantity: 1, Unit: "tsp"},
	}

	// Create steps
	steps := []models.CookingStep{
		{
			ID:          "step-1",
			Name:        "Boil Water",
			Description: "Bring a large pot of water to a boil.",
			Duration:    5 * time.Minute,
			Sequence:    1,
			Equipment:   []string{"pot"},
		},
		{
			ID:          "step-2",
			Name:        "Cook Pasta",
			Description: "Add pasta to boiling water and cook until al dente.",
			Duration:    10 * time.Minute,
			Sequence:    2,
			Equipment:   []string{"pot"},
		},
		{
			ID:          "step-3",
			Name:        "Drain Pasta",
			Description: "Drain the pasta using a colander.",
			Duration:    1 * time.Minute,
			Sequence:    3,
			Equipment:   []string{"colander"},
		},
		{
			ID:          "step-4",
			Name:        "Heat Sauce",
			Description: "Heat tomato sauce in a pan.",
			Duration:    5 * time.Minute,
			Sequence:    4,
			Equipment:   []string{"pan"},
		},
		{
			ID:          "step-5",
			Name:        "Combine",
			Description: "Add pasta to the sauce and mix well.",
			Duration:    2 * time.Minute,
			Sequence:    5,
			Equipment:   []string{"pan"},
		},
	}

	// Set serialized data
	if err := pastaRecipe.SetIngredients(ingredients); err != nil {
		log.Printf("Failed to serialize ingredients: %v", err)
		return
	}

	if err := pastaRecipe.SetSteps(steps); err != nil {
		log.Printf("Failed to serialize steps: %v", err)
		return
	}

	// Save the recipe
	if err := db.Create(&pastaRecipe).Error; err != nil {
		log.Printf("Failed to create sample recipe: %v", err)
	}

	// Create a second recipe
	chickenRecipe := models.Recipe{
		RecipeID:      "chicken-1",
		Name:          "Roast Chicken",
		Description:   "A classic roast chicken dish",
		Category:      "main",
		Complexity:    3,
		PrepTime:      20 * time.Minute,
		CookTime:      60 * time.Minute,
		EstimatedTime: 80 * time.Minute,
		Servings:      4,
		Equipment:     models.StringSlice{"oven", "roasting pan", "knife"},
		Tags:          models.StringSlice{"chicken", "roast", "dinner"},
	}

	// Create ingredients for chicken
	chickenIngredients := []models.IngredientRequirement{
		{ID: "ing-1", Name: "Whole Chicken", Quantity: 1, Unit: "kg"},
		{ID: "ing-2", Name: "Salt", Quantity: 2, Unit: "tsp"},
		{ID: "ing-3", Name: "Pepper", Quantity: 1, Unit: "tsp"},
		{ID: "ing-4", Name: "Olive Oil", Quantity: 2, Unit: "tbsp"},
		{ID: "ing-5", Name: "Garlic", Quantity: 3, Unit: "cloves"},
	}

	// Create steps for chicken
	chickenSteps := []models.CookingStep{
		{
			ID:          "step-1",
			Name:        "Preheat Oven",
			Description: "Preheat oven to 425°F (220°C).",
			Duration:    10 * time.Minute,
			Sequence:    1,
			Equipment:   []string{"oven"},
		},
		{
			ID:          "step-2",
			Name:        "Prepare Chicken",
			Description: "Season chicken with salt, pepper, and olive oil. Stuff with garlic.",
			Duration:    10 * time.Minute,
			Sequence:    2,
			Equipment:   []string{"knife"},
		},
		{
			ID:          "step-3",
			Name:        "Roast Chicken",
			Description: "Place chicken in a roasting pan and roast for 1 hour or until internal temperature reaches 165°F (74°C).",
			Duration:    60 * time.Minute,
			Sequence:    3,
			Equipment:   []string{"oven", "roasting pan"},
		},
		{
			ID:          "step-4",
			Name:        "Rest Chicken",
			Description: "Remove chicken from oven and let rest for 10 minutes before carving.",
			Duration:    10 * time.Minute,
			Sequence:    4,
		},
	}

	// Set serialized data for chicken
	if err := chickenRecipe.SetIngredients(chickenIngredients); err != nil {
		log.Printf("Failed to serialize chicken ingredients: %v", err)
		return
	}

	if err := chickenRecipe.SetSteps(chickenSteps); err != nil {
		log.Printf("Failed to serialize chicken steps: %v", err)
		return
	}

	// Save the chicken recipe
	if err := db.Create(&chickenRecipe).Error; err != nil {
		log.Printf("Failed to create chicken recipe: %v", err)
	}
}

// GetKitchenState retrieves the current state of the kitchen
func GetKitchenState() Kitchen {
	db := database.GetDB()
	var kitchen Kitchen
	db.First(&kitchen)
	return kitchen
}

// UpdateKitchenState updates the state of the kitchen
func UpdateKitchenState(kitchen Kitchen) {
	db := database.GetDB()
	db.Save(&kitchen)
}

// PerformKitchenAction performs a transactional kitchen action
func PerformKitchenAction(action func()) {
	db := database.GetDB()
	tx := db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()
	action()
	tx.Commit()
}

// InitDB initializes the database connection
func InitDB(dbPath string) error {
	var err error
	db, err = gorm.Open("sqlite3", dbPath)
	if err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}

	// Enable GORM logging in development
	db.LogMode(true)

	// Configure connection pool
	db.DB().SetMaxIdleConns(10)
	db.DB().SetMaxOpenConns(100)
	db.DB().SetConnMaxLifetime(time.Hour)

	return nil
}

// GetDB returns the database instance
func GetDB() *gorm.DB {
	return db
}

// CloseDB closes the database connection
func CloseDB() error {
	if db != nil {
		return db.Close()
	}
	return nil
}
