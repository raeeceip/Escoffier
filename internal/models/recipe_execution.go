package models

import (
	"time"

	"github.com/jinzhu/gorm"
)

// RecipeExecution represents a single execution of a recipe
type RecipeExecution struct {
	gorm.Model
	RecipeID   uint
	StartTime  time.Time
	EndTime    time.Time
	Status     string
	Notes      string
	ExecutedBy string
}

// ExecutionStatus represents the status of a recipe execution
type ExecutionStatus string

const (
	// Execution statuses
	ExecutionStatusPending    ExecutionStatus = "pending"
	ExecutionStatusInProgress ExecutionStatus = "in_progress"
	ExecutionStatusCompleted  ExecutionStatus = "completed"
	ExecutionStatusFailed     ExecutionStatus = "failed"
	ExecutionStatusCancelled  ExecutionStatus = "cancelled"
)
