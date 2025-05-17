package models

import "time"

// InventoryItem represents an item in the kitchen inventory
type InventoryItem struct {
	ID          string
	Name        string
	Category    string
	Quantity    float64
	Unit        string
	ExpiryDate  *time.Time
	MinLevel    float64
	MaxLevel    float64
	ReorderAt   float64
	LastOrdered *time.Time
	Location    string
	Status      string
	Notes       string
}

// InventoryCategory represents the category of an inventory item
type InventoryCategory string

const (
	// Inventory categories
	CategoryProtein     InventoryCategory = "protein"
	CategoryProduce     InventoryCategory = "produce"
	CategoryDairy       InventoryCategory = "dairy"
	CategoryDryGoods    InventoryCategory = "dry_goods"
	CategorySpices      InventoryCategory = "spices"
	CategoryCondiments  InventoryCategory = "condiments"
	CategoryBeverages   InventoryCategory = "beverages"
	CategoryDisposables InventoryCategory = "disposables"
	CategoryCleaning    InventoryCategory = "cleaning"
)

// InventoryStatus represents the status of an inventory item
type InventoryStatus string

const (
	// Inventory statuses
	StatusInStock     InventoryStatus = "in_stock"
	StatusLow         InventoryStatus = "low"
	StatusOutOfStock  InventoryStatus = "out_of_stock"
	StatusOrdered     InventoryStatus = "ordered"
	StatusExpired     InventoryStatus = "expired"
	StatusQuarantined InventoryStatus = "quarantined"
)

// InventoryUnit represents the unit of measurement for an inventory item
type InventoryUnit string

const (
	// Weight units
	UnitGram     InventoryUnit = "g"
	UnitKilogram InventoryUnit = "kg"
	UnitOunce    InventoryUnit = "oz"
	UnitPound    InventoryUnit = "lb"

	// Volume units
	UnitMilliliter InventoryUnit = "ml"
	UnitLiter      InventoryUnit = "l"
	UnitFluidOunce InventoryUnit = "fl_oz"
	UnitGallon     InventoryUnit = "gal"

	// Count units
	UnitPiece     InventoryUnit = "pc"
	UnitBox       InventoryUnit = "box"
	UnitCase      InventoryUnit = "case"
	UnitContainer InventoryUnit = "container"
)

// InventoryLocation represents the storage location of an inventory item
type InventoryLocation string

const (
	// Storage locations
	LocationDryStorage   InventoryLocation = "dry_storage"
	LocationRefrigerator InventoryLocation = "refrigerator"
	LocationFreezer      InventoryLocation = "freezer"
	LocationSpiceRack    InventoryLocation = "spice_rack"
	LocationWalkIn       InventoryLocation = "walk_in"
	LocationSupplyCloset InventoryLocation = "supply_closet"
)
