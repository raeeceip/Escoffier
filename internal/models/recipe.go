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
	ID       string
	Name     string
	Quantity float64
	Unit     string
	Notes    string
}

// CookingStep represents a single step in a recipe
type CookingStep struct {
	ID          string
	Description string
	Duration    time.Duration
	Equipment   []string
	Technique   string
	Temperature *CookingTemperature
	Notes       string
}

// CookingTemperature represents a cooking temperature requirement
type CookingTemperature struct {
	Value    float64
	Unit     string // "C" or "F"
	Critical bool   // Whether precise temperature is critical
}
