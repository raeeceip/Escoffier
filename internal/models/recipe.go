package models

import (
	"database/sql/driver"
	"encoding/json"
	"errors"
	"time"

	"github.com/jinzhu/gorm"
)

// StringSlice represents a slice of strings that can be stored in the database
type StringSlice []string

// Value converts the slice to a JSON string for storage
func (s StringSlice) Value() (driver.Value, error) {
	if len(s) == 0 {
		return "[]", nil
	}
	return json.Marshal(s)
}

// Scan converts the database value back to a slice
func (s *StringSlice) Scan(value interface{}) error {
	if value == nil {
		*s = StringSlice{}
		return nil
	}

	switch v := value.(type) {
	case []byte:
		return json.Unmarshal(v, s)
	case string:
		return json.Unmarshal([]byte(v), s)
	default:
		return errors.New("unsupported type for StringSlice")
	}
}

// Recipe represents a cooking recipe in the kitchen
type Recipe struct {
	gorm.Model
	RecipeID        string `gorm:"column:id"`
	Name            string
	Description     string
	Category        string
	Complexity      int
	PrepTime        time.Duration
	CookTime        time.Duration
	EstimatedTime   time.Duration
	Servings        int
	IngredientsJSON string      `gorm:"type:text"`
	StepsJSON       string      `gorm:"type:text"`
	Equipment       StringSlice `gorm:"type:text"`
	Notes           string
	Tags            StringSlice `gorm:"type:text"`
	// Transient fields (ignored by GORM)
	Ingredients []IngredientRequirement `gorm:"-"`
	Steps       []CookingStep           `gorm:"-"`
}

// TableName sets the table name for Recipe
func (Recipe) TableName() string {
	return "recipes"
}

// GetIngredients returns the deserialized ingredients
func (r *Recipe) GetIngredients() ([]IngredientRequirement, error) {
	if len(r.Ingredients) > 0 {
		return r.Ingredients, nil
	}
	var ingredients []IngredientRequirement
	if r.IngredientsJSON == "" {
		return ingredients, nil
	}
	if err := json.Unmarshal([]byte(r.IngredientsJSON), &ingredients); err != nil {
		return nil, err
	}
	r.Ingredients = ingredients
	return ingredients, nil
}

// SetIngredients serializes the ingredients for storage
func (r *Recipe) SetIngredients(ingredients []IngredientRequirement) error {
	data, err := json.Marshal(ingredients)
	if err != nil {
		return err
	}
	r.IngredientsJSON = string(data)
	r.Ingredients = ingredients
	return nil
}

// GetSteps returns the deserialized cooking steps
func (r *Recipe) GetSteps() ([]CookingStep, error) {
	if len(r.Steps) > 0 {
		return r.Steps, nil
	}
	var steps []CookingStep
	if r.StepsJSON == "" {
		return steps, nil
	}
	if err := json.Unmarshal([]byte(r.StepsJSON), &steps); err != nil {
		return nil, err
	}
	r.Steps = steps
	return steps, nil
}

// SetSteps serializes the cooking steps for storage
func (r *Recipe) SetSteps(steps []CookingStep) error {
	data, err := json.Marshal(steps)
	if err != nil {
		return err
	}
	r.StepsJSON = string(data)
	r.Steps = steps
	return nil
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
	Sequence          int // Order in the recipe sequence
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
