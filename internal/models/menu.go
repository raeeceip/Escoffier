package models

import (
	"fmt"
	"time"
)

// MenuItem represents a dish on the menu
type MenuItem struct {
	ID                string
	Name              string
	Description       string
	Category          string
	Price             float64
	PrepTime          time.Duration
	CookTime          time.Duration
	Ingredients       []string
	RequiredEquipment []string
	Allergens         []string
	Difficulty        int
	IsSpecialty       bool
	Notes             string
}

// MenuCategory represents the category of a menu item
type MenuCategory string

const (
	// Menu categories
	MenuCategoryAppetizer MenuCategory = "appetizer"
	MenuCategoryEntree    MenuCategory = "entree"
	MenuCategorySide      MenuCategory = "side"
	MenuCategoryDessert   MenuCategory = "dessert"
	MenuCategoryBeverage  MenuCategory = "beverage"
	MenuCategorySpecialty MenuCategory = "specialty"
)

// Allergen represents a food allergen
type Allergen string

const (
	// Common allergens
	AllergenMilk      Allergen = "milk"
	AllergenEggs      Allergen = "eggs"
	AllergenFish      Allergen = "fish"
	AllergenShellfish Allergen = "shellfish"
	AllergenTreeNuts  Allergen = "tree_nuts"
	AllergenPeanuts   Allergen = "peanuts"
	AllergenWheat     Allergen = "wheat"
	AllergenSoy       Allergen = "soy"
	AllergenSesame    Allergen = "sesame"
)

// ValidateMenuItem validates a menu item
func ValidateMenuItem(item *MenuItem) error {
	if item.Name == "" {
		return fmt.Errorf("menu item name is required")
	}
	if item.Price <= 0 {
		return fmt.Errorf("menu item price must be greater than 0")
	}
	if item.PrepTime <= 0 {
		return fmt.Errorf("menu item prep time must be greater than 0")
	}
	if item.CookTime <= 0 {
		return fmt.Errorf("menu item cook time must be greater than 0")
	}
	if len(item.Ingredients) == 0 {
		return fmt.Errorf("menu item must have at least one ingredient")
	}
	return nil
}

// GetTotalTime returns the total time needed to prepare the item
func (mi *MenuItem) GetTotalTime() time.Duration {
	return mi.PrepTime + mi.CookTime
}

// HasIngredient checks if the item contains a specific ingredient
func (mi *MenuItem) HasIngredient(ingredient string) bool {
	for _, ing := range mi.Ingredients {
		if ing == ingredient {
			return true
		}
	}
	return false
}

// HasAllergen checks if the item contains a specific allergen
func (mi *MenuItem) HasAllergen(allergen string) bool {
	for _, alg := range mi.Allergens {
		if alg == allergen {
			return true
		}
	}
	return false
}

// IsInCategory checks if the item belongs to a specific category
func (mi *MenuItem) IsInCategory(category MenuCategory) bool {
	return mi.Category == string(category)
}
