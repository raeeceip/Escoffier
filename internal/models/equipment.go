package models

import (
	"time"

	"github.com/jinzhu/gorm"
)

// Equipment represents a piece of kitchen equipment
type Equipment struct {
	gorm.Model
	Name            string
	Type            string
	Status          string
	Station         string
	LastMaintenance time.Time
	NextMaintenance time.Time
	Capacity        float64
	Notes           string
}

// EquipmentStatus represents the status of a piece of equipment
type EquipmentStatus string

const (
	// Equipment statuses
	EquipmentStatusAvailable    EquipmentStatus = "available"
	EquipmentStatusInUse        EquipmentStatus = "in_use"
	EquipmentStatusMaintenance  EquipmentStatus = "maintenance"
	EquipmentStatusOutOfService EquipmentStatus = "out_of_service"
	EquipmentStatusReserved     EquipmentStatus = "reserved"
)

// EquipmentType represents the type of equipment
type EquipmentType string

const (
	// Equipment types
	EquipmentTypeCooking   EquipmentType = "cooking"
	EquipmentTypeStorage   EquipmentType = "storage"
	EquipmentTypePrep      EquipmentType = "prep"
	EquipmentTypeUtensil   EquipmentType = "utensil"
	EquipmentTypeAppliance EquipmentType = "appliance"
)
