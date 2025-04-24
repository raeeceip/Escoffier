package main

import (
	"github.com/jinzhu/gorm"
	_ "github.com/jinzhu/gorm/dialects/postgres"
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

// InitializeDatabase initializes the database schema
func InitializeDatabase() {
	db.AutoMigrate(&Kitchen{}, &InventoryItem{}, &EquipmentItem{})
}

// GetKitchenState retrieves the current state of the kitchen
func GetKitchenState() Kitchen {
	var kitchen Kitchen
	db.First(&kitchen)
	db.Model(&kitchen).Related(&kitchen.Inventory)
	db.Model(&kitchen).Related(&kitchen.Equipment)
	return kitchen
}

// UpdateKitchenState updates the state of the kitchen
func UpdateKitchenState(kitchen Kitchen) {
	db.Save(&kitchen)
}

// PerformKitchenAction performs a transactional kitchen action
func PerformKitchenAction(action func()) {
	tx := db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()
	action()
	tx.Commit()
}
