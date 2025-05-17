package models

import (
	"fmt"
	"time"

	"github.com/jinzhu/gorm"
)

// PrepTask represents a food preparation task
type PrepTask struct {
	gorm.Model
	ID          string
	Description string
	Technique   string
	Equipment   []string `gorm:"type:json"`
	Duration    time.Duration
	Status      string
	Priority    int
	Notes       string
	Ingredients []IngredientRequirement `gorm:"foreignkey:PrepTaskID"`
}

// PrepTechnique represents a food preparation technique
type PrepTechnique string

const (
	PrepTechniqueChop     PrepTechnique = "chop"
	PrepTechniqueDice     PrepTechnique = "dice"
	PrepTechniqueSlice    PrepTechnique = "slice"
	PrepTechniqueMarinate PrepTechnique = "marinate"
	PrepTechniqueMix      PrepTechnique = "mix"
	PrepTechniquePeel     PrepTechnique = "peel"
	PrepTechniqueGrate    PrepTechnique = "grate"
	PrepTechniquePuree    PrepTechnique = "puree"
)

// PrepStatus represents the status of a preparation task
type PrepStatus string

const (
	PrepStatusPending    PrepStatus = "pending"
	PrepStatusInProgress PrepStatus = "in_progress"
	PrepStatusCompleted  PrepStatus = "completed"
	PrepStatusCancelled  PrepStatus = "cancelled"
)

// ValidatePrepTask validates a preparation task
func ValidatePrepTask(task *PrepTask) error {
	if task.ID == "" {
		return fmt.Errorf("prep task ID is required")
	}
	if task.Description == "" {
		return fmt.Errorf("prep task description is required")
	}
	if task.Technique == "" {
		return fmt.Errorf("prep task technique is required")
	}
	if len(task.Equipment) == 0 {
		return fmt.Errorf("prep task must have at least one piece of equipment")
	}
	if len(task.Ingredients) == 0 {
		return fmt.Errorf("prep task must have at least one ingredient")
	}
	return nil
}

// IsTechniqueValid checks if a preparation technique is valid
func IsTechniqueValid(technique string) bool {
	validTechniques := map[PrepTechnique]bool{
		PrepTechniqueChop:     true,
		PrepTechniqueDice:     true,
		PrepTechniqueSlice:    true,
		PrepTechniqueMarinate: true,
		PrepTechniqueMix:      true,
		PrepTechniquePeel:     true,
		PrepTechniqueGrate:    true,
		PrepTechniquePuree:    true,
	}
	return validTechniques[PrepTechnique(technique)]
}

// IsStatusValid checks if a preparation status is valid
func IsStatusValid(status string) bool {
	validStatuses := map[PrepStatus]bool{
		PrepStatusPending:    true,
		PrepStatusInProgress: true,
		PrepStatusCompleted:  true,
		PrepStatusCancelled:  true,
	}
	return validStatuses[PrepStatus(status)]
}

// GetEstimatedDuration calculates the estimated duration for the task
func (pt *PrepTask) GetEstimatedDuration() time.Duration {
	// Base duration for the technique
	baseDuration := map[PrepTechnique]time.Duration{
		PrepTechniqueChop:     5 * time.Minute,
		PrepTechniqueDice:     8 * time.Minute,
		PrepTechniqueSlice:    5 * time.Minute,
		PrepTechniqueMarinate: 30 * time.Minute,
		PrepTechniqueMix:      3 * time.Minute,
		PrepTechniquePeel:     4 * time.Minute,
		PrepTechniqueGrate:    4 * time.Minute,
		PrepTechniquePuree:    6 * time.Minute,
	}

	// Get base duration for the technique
	duration := baseDuration[PrepTechnique(pt.Technique)]

	// Adjust for quantity of ingredients
	duration *= time.Duration(len(pt.Ingredients))

	// Add setup and cleanup time
	duration += 5 * time.Minute

	return duration
}

// IsComplete checks if the task is completed
func (pt *PrepTask) IsComplete() bool {
	return pt.Status == string(PrepStatusCompleted)
}

// CanStart checks if the task can be started
func (pt *PrepTask) CanStart() bool {
	return pt.Status == string(PrepStatusPending)
}

// Start marks the task as in progress
func (pt *PrepTask) Start() {
	pt.Status = string(PrepStatusInProgress)
}

// Complete marks the task as completed
func (pt *PrepTask) Complete() {
	pt.Status = string(PrepStatusCompleted)
}

// Cancel marks the task as cancelled
func (pt *PrepTask) Cancel() {
	pt.Status = string(PrepStatusCancelled)
}
