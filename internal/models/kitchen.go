package models

import (
	"github.com/jinzhu/gorm"
)

// Kitchen represents the state of the kitchen
type Kitchen struct {
	gorm.Model
	Inventory []InventoryItem
	Equipment []EquipmentItem
	Status    string
}

// EquipmentItem represents an item of equipment in the kitchen
type EquipmentItem struct {
	gorm.Model
	Name   string
	Status string
}
