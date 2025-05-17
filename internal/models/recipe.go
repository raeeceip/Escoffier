package models

import "time"

// Recipe represents a cooking recipe in the kitchen
type Recipe struct {
	ID          string
	Name        string
	Description string
	Category    string
	Complexity  int
	PrepTime    time.Duration
	CookTime    time.Duration
	Servings    int
	Ingredients []IngredientRequirement
	Steps       []CookingStep
	Equipment   []string
	Notes       string
	Tags        []string
}

// IngredientRequirement represents a required ingredient for a recipe
type IngredientRequirement struct {
	ID          string
	Name        string
	Quantity    float64
	Unit        string
	Notes       string
	Equipment   []string
	Technique   string
	Temperature *CookingTemperature
}

// CookingStep represents a single step in a recipe
type CookingStep struct {
	ID                string
	Name              string
	Description       string
	Duration          time.Duration
	Equipment         []string
	RequiredEquipment []string
	Technique         string
	Temperature       *CookingTemperature
	Notes             string
	Priority          int
	Status            string
	Dependencies      []string
}

// CookingTemperature represents a cooking temperature requirement
type CookingTemperature struct {
	Value    float64
	Unit     string // "C" or "F"
	Critical bool   // Whether precise temperature is critical
}

// CookingStepStatus represents the status of a cooking step
type CookingStepStatus string

const (
	// Cooking step statuses
	StepStatusPending    CookingStepStatus = "pending"
	StepStatusInProgress CookingStepStatus = "in_progress"
	StepStatusCompleted  CookingStepStatus = "completed"
	StepStatusFailed     CookingStepStatus = "failed"
	StepStatusPaused     CookingStepStatus = "paused"
)
