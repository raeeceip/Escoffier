package models

import (
	"time"

	"github.com/jinzhu/gorm"
)

// Order represents a customer order
type Order struct {
	ID            uint
	Type          string
	Items         []OrderItem
	Status        string
	Priority      int
	TimeReceived  time.Time
	TimeCompleted time.Time
	AssignedTo    string
	EstimatedTime time.Duration
	Notes         string
}

// OrderItem represents an item in an order
type OrderItem struct {
	gorm.Model
	OrderID           uint
	Name              string
	Quantity          int
	Notes             string
	Status            string
	PrepTime          time.Duration
	CookTime          time.Duration
	Temperature       *float64
	RequiredEquipment []string
	Ingredients       []string
	Category          string
	Price             float64
	IsSpecialty       bool
}

// OrderStatus represents the status of an order
type OrderStatus string

const (
	// Order statuses
	OrderStatusPending   OrderStatus = "pending"
	OrderStatusAssigned  OrderStatus = "assigned"
	OrderStatusPreparing OrderStatus = "preparing"
	OrderStatusCooking   OrderStatus = "cooking"
	OrderStatusPlating   OrderStatus = "plating"
	OrderStatusCompleted OrderStatus = "completed"
	OrderStatusCancelled OrderStatus = "cancelled"
	OrderStatusFailed    OrderStatus = "failed"
)

// OrderType represents the type of order
type OrderType string

const (
	// Order types
	OrderTypeDineIn   OrderType = "dine_in"
	OrderTypeTakeOut  OrderType = "take_out"
	OrderTypeDelivery OrderType = "delivery"
	OrderTypeCatering OrderType = "catering"
	OrderTypeSpecial  OrderType = "special"
)
