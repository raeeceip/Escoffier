package models

import (
	"time"

	"github.com/jinzhu/gorm"
)

// Order represents a kitchen order
type Order struct {
	gorm.Model
	Items         []OrderItem `gorm:"foreignkey:OrderID"`
	Status        string
	Priority      int
	TimeReceived  time.Time
	TimeCompleted time.Time
	AssignedTo    uint // References Agent ID
}

// OrderItem represents an item in an order
type OrderItem struct {
	gorm.Model
	OrderID     uint
	Name        string
	Quantity    int
	Notes       string
	Status      string
	PrepTime    time.Duration
	CookTime    time.Duration
	Temperature *float64
}

// OrderStatus represents the possible states of an order
type OrderStatus string

const (
	OrderStatusReceived  OrderStatus = "received"
	OrderStatusAssigned  OrderStatus = "assigned"
	OrderStatusPreparing OrderStatus = "preparing"
	OrderStatusCooking   OrderStatus = "cooking"
	OrderStatusPlating   OrderStatus = "plating"
	OrderStatusCompleted OrderStatus = "completed"
	OrderStatusCancelled OrderStatus = "cancelled"
)
