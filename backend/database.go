package main

import (
	"fmt"
	"masterchef/internal/database"
	"masterchef/internal/models"
	"time"

	"github.com/jinzhu/gorm"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

var db *gorm.DB

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

// InitializeDatabase initializes the database schema
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
	)
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
