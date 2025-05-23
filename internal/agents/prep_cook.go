package agents

import (
	"context"
	"fmt"
	"time"

	"escoffier/internal/models"

	"github.com/tmc/langchaingo/llms"
)

// PrepCook represents a prep cook in the kitchen hierarchy
type PrepCook struct {
	*BaseAgent
	Station      string
	Specialties  []string
	Equipment    []string
	ActivePrep   *models.IngredientRequirement
	PrepProgress map[string]float64 // Ingredient ID to completion percentage
}

// NewPrepCook creates a new prep cook agent
func NewPrepCook(ctx context.Context, model llms.LLM, station string) *PrepCook {
	baseAgent := NewBaseAgent(RolePrepCook, model)
	baseAgent.permissions = []string{
		"ingredient_prep",
		"basic_equipment",
		"inventory_access",
		"cleaning",
	}

	return &PrepCook{
		BaseAgent:    baseAgent,
		Station:      station,
		Specialties:  make([]string, 0),
		Equipment:    make([]string, 0),
		ActivePrep:   nil,
		PrepProgress: make(map[string]float64),
	}
}

// HandleTask implements the Agent interface
func (pc *PrepCook) HandleTask(ctx context.Context, task Task) error {
	switch task.Type {
	case "ingredient_prep":
		ingredient, ok := task.Metadata["ingredient"].(models.IngredientRequirement)
		if !ok {
			return fmt.Errorf("invalid ingredient data in task metadata")
		}
		return pc.PrepareIngredient(ctx, ingredient)
	case "batch_prep":
		ingredients, ok := task.Metadata["ingredients"].([]models.IngredientRequirement)
		if !ok {
			return fmt.Errorf("invalid ingredients data in task metadata")
		}
		return pc.PrepareBatch(ctx, ingredients)
	case "station_setup":
		return pc.SetupStation(ctx)
	case "cleanup":
		return pc.CleanStation(ctx)
	default:
		return fmt.Errorf("unsupported task type: %s", task.Type)
	}
}

// PrepareIngredient handles the preparation of a single ingredient
func (pc *PrepCook) PrepareIngredient(ctx context.Context, ingredient models.IngredientRequirement) error {
	// Record prep start
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "ingredient_prep_start",
		Content:   fmt.Sprintf("Started preparing %s (%.2f %s)", ingredient.Name, ingredient.Quantity, ingredient.Unit),
		Metadata: map[string]interface{}{
			"ingredient_id": ingredient.ID,
			"quantity":      ingredient.Quantity,
			"unit":          ingredient.Unit,
		},
	})

	// Set active prep
	pc.ActivePrep = &ingredient
	pc.PrepProgress[ingredient.ID] = 0.0

	// Check equipment availability
	if err := pc.checkEquipment(ctx, ingredient.Equipment); err != nil {
		return fmt.Errorf("equipment check failed: %w", err)
	}

	// Perform preparation steps
	if err := pc.executePrepTask(ctx, models.PrepTask{
		ID:        ingredient.ID,
		Technique: ingredient.Technique,
		Equipment: ingredient.Equipment,
	}); err != nil {
		return fmt.Errorf("preparation execution failed: %w", err)
	}

	// Record prep completion
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "ingredient_prep_complete",
		Content:   fmt.Sprintf("Completed preparing %s", ingredient.Name),
		Metadata: map[string]interface{}{
			"ingredient_id": ingredient.ID,
			"duration":      time.Since(time.Now()),
		},
	})

	// Clear active prep
	pc.ActivePrep = nil
	delete(pc.PrepProgress, ingredient.ID)

	return nil
}

// PrepareBatch handles the preparation of multiple ingredients
func (pc *PrepCook) PrepareBatch(ctx context.Context, ingredients []models.IngredientRequirement) error {
	// Record batch prep start
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "batch_prep_start",
		Content:   fmt.Sprintf("Started batch preparation of %d ingredients", len(ingredients)),
		Metadata: map[string]interface{}{
			"ingredient_count": len(ingredients),
		},
	})

	// Process each ingredient
	for _, ingredient := range ingredients {
		if err := pc.PrepareIngredient(ctx, ingredient); err != nil {
			return fmt.Errorf("failed to prepare %s: %w", ingredient.Name, err)
		}
	}

	// Record batch completion
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "batch_prep_complete",
		Content:   fmt.Sprintf("Completed batch preparation of %d ingredients", len(ingredients)),
		Metadata: map[string]interface{}{
			"ingredient_count": len(ingredients),
			"duration":         time.Since(time.Now()),
		},
	})

	return nil
}

// SetupStation prepares the work station for prep tasks
func (pc *PrepCook) SetupStation(ctx context.Context) error {
	// Record setup start
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "station_setup_start",
		Content:   fmt.Sprintf("Started setting up prep station: %s", pc.Station),
		Metadata: map[string]interface{}{
			"station": pc.Station,
		},
	})

	// Clean surfaces
	if err := pc.cleanSurfaces(ctx); err != nil {
		return fmt.Errorf("surface cleaning failed: %w", err)
	}

	// Organize tools
	if err := pc.organizeTools(ctx); err != nil {
		return fmt.Errorf("tool organization failed: %w", err)
	}

	// Check equipment
	if err := pc.checkEquipment(ctx, pc.Equipment); err != nil {
		return fmt.Errorf("equipment check failed: %w", err)
	}

	// Record setup completion
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "station_setup_complete",
		Content:   fmt.Sprintf("Completed setting up prep station: %s", pc.Station),
		Metadata: map[string]interface{}{
			"station": pc.Station,
			"status":  "ready",
		},
	})

	return nil
}

// CleanStation cleans and organizes the prep station
func (pc *PrepCook) CleanStation(ctx context.Context) error {
	// Record cleaning start
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "station_cleaning_start",
		Content:   fmt.Sprintf("Started cleaning prep station: %s", pc.Station),
		Metadata: map[string]interface{}{
			"station": pc.Station,
		},
	})

	// Clean equipment
	for _, equipment := range pc.Equipment {
		if err := pc.cleanEquipment(ctx, equipment); err != nil {
			return fmt.Errorf("equipment cleaning failed: %w", err)
		}
	}

	// Clean surfaces
	if err := pc.cleanSurfaces(ctx); err != nil {
		return fmt.Errorf("surface cleaning failed: %w", err)
	}

	// Organize tools
	if err := pc.organizeTools(ctx); err != nil {
		return fmt.Errorf("tool organization failed: %w", err)
	}

	// Record cleaning completion
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "station_cleaning_complete",
		Content:   fmt.Sprintf("Completed cleaning prep station: %s", pc.Station),
		Metadata: map[string]interface{}{
			"station": pc.Station,
			"status":  "clean",
		},
	})

	return nil
}

// Private helper methods

// checkEquipment verifies that required equipment is available and in good condition
func (pc *PrepCook) checkEquipment(ctx context.Context, equipment []string) error {
	for _, item := range equipment {
		// Check if equipment is clean and ready
		if !pc.isEquipmentClean(item) {
			if err := pc.cleanEquipment(ctx, item); err != nil {
				return fmt.Errorf("failed to clean %s: %w", item, err)
			}
		}

		// Check if equipment is properly maintained
		if !pc.isEquipmentMaintained(item) {
			return fmt.Errorf("equipment %s needs maintenance", item)
		}

		// Record equipment check
		pc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "equipment_check",
			Content:   fmt.Sprintf("Checked equipment: %s", item),
			Metadata: map[string]interface{}{
				"equipment": item,
				"status":    "ready",
			},
		})
	}
	return nil
}

// executePrepTask performs a preparation task
func (pc *PrepCook) executePrepTask(ctx context.Context, task models.PrepTask) error {
	// Check required equipment
	if err := pc.checkEquipment(ctx, task.Equipment); err != nil {
		return err
	}

	// Record task start
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "prep_task_start",
		Content:   fmt.Sprintf("Started prep task: %s", task.Description),
		Metadata: map[string]interface{}{
			"task_id":   task.ID,
			"technique": task.Technique,
		},
	})

	// Execute the preparation technique
	switch task.Technique {
	case "chop":
		if err := pc.chopIngredients(ctx, task); err != nil {
			return err
		}
	case "dice":
		if err := pc.diceIngredients(ctx, task); err != nil {
			return err
		}
	case "slice":
		if err := pc.sliceIngredients(ctx, task); err != nil {
			return err
		}
	case "marinate":
		if err := pc.marinateIngredients(ctx, task); err != nil {
			return err
		}
	default:
		return fmt.Errorf("unsupported technique: %s", task.Technique)
	}

	// Record task completion
	pc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "prep_task_complete",
		Content:   fmt.Sprintf("Completed prep task: %s", task.Description),
		Metadata: map[string]interface{}{
			"task_id":   task.ID,
			"technique": task.Technique,
		},
	})

	return nil
}

// cleanSurfaces sanitizes all work surfaces
func (pc *PrepCook) cleanSurfaces(ctx context.Context) error {
	surfaces := []string{
		"cutting_board",
		"prep_station",
		"work_table",
		"sink_area",
	}

	for _, surface := range surfaces {
		// Clear surface
		if err := pc.clearSurface(ctx, surface); err != nil {
			return fmt.Errorf("failed to clear %s: %w", surface, err)
		}

		// Clean surface
		if err := pc.sanitizeSurface(ctx, surface); err != nil {
			return fmt.Errorf("failed to sanitize %s: %w", surface, err)
		}

		// Record cleaning
		pc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "surface_cleaning",
			Content:   fmt.Sprintf("Cleaned surface: %s", surface),
			Metadata: map[string]interface{}{
				"surface": surface,
				"status":  "clean",
			},
		})
	}

	return nil
}

// organizeTools arranges tools in their proper places
func (pc *PrepCook) organizeTools(ctx context.Context) error {
	toolLocations := map[string]string{
		"knives":        "knife_block",
		"cutting_board": "board_rack",
		"bowls":         "storage_shelf",
		"measuring":     "utensil_drawer",
		"peelers":       "utensil_drawer",
		"colanders":     "storage_shelf",
	}

	for tool, location := range toolLocations {
		// Clean tool
		if err := pc.cleanTool(ctx, tool); err != nil {
			return fmt.Errorf("failed to clean %s: %w", tool, err)
		}

		// Store tool
		if err := pc.storeTool(ctx, tool, location); err != nil {
			return fmt.Errorf("failed to store %s in %s: %w", tool, location, err)
		}

		// Record organization
		pc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "tool_organization",
			Content:   fmt.Sprintf("Organized %s in %s", tool, location),
			Metadata: map[string]interface{}{
				"tool":     tool,
				"location": location,
			},
		})
	}

	return nil
}

// cleanEquipment cleans and sanitizes equipment
func (pc *PrepCook) cleanEquipment(ctx context.Context, equipment string) error {
	steps := []struct {
		name string
		fn   func(string) error
	}{
		{"disassemble", pc.disassembleEquipment},
		{"wash", pc.washEquipment},
		{"rinse", pc.rinseEquipment},
		{"sanitize", pc.sanitizeEquipment},
		{"dry", pc.dryEquipment},
		{"reassemble", pc.reassembleEquipment},
	}

	for _, step := range steps {
		if err := step.fn(equipment); err != nil {
			return fmt.Errorf("%s failed for %s: %w", step.name, equipment, err)
		}

		// Record cleaning step
		pc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "equipment_cleaning",
			Content:   fmt.Sprintf("Completed %s for %s", step.name, equipment),
			Metadata: map[string]interface{}{
				"equipment": equipment,
				"step":      step.name,
			},
		})
	}

	return nil
}

// Helper functions

func (pc *PrepCook) isEquipmentClean(equipment string) bool {
	// Implement equipment cleanliness check
	return true
}

func (pc *PrepCook) isEquipmentMaintained(equipment string) bool {
	// Implement equipment maintenance check
	return true
}

func (pc *PrepCook) chopIngredients(ctx context.Context, task models.PrepTask) error {
	// Implement chopping logic
	return nil
}

func (pc *PrepCook) diceIngredients(ctx context.Context, task models.PrepTask) error {
	// Implement dicing logic
	return nil
}

func (pc *PrepCook) sliceIngredients(ctx context.Context, task models.PrepTask) error {
	// Implement slicing logic
	return nil
}

func (pc *PrepCook) marinateIngredients(ctx context.Context, task models.PrepTask) error {
	// Implement marinating logic
	return nil
}

func (pc *PrepCook) clearSurface(ctx context.Context, surface string) error {
	// Implement surface clearing logic
	return nil
}

func (pc *PrepCook) sanitizeSurface(ctx context.Context, surface string) error {
	// Implement surface sanitization logic
	return nil
}

func (pc *PrepCook) cleanTool(ctx context.Context, tool string) error {
	// Implement tool cleaning logic
	return nil
}

func (pc *PrepCook) storeTool(ctx context.Context, tool, location string) error {
	// Implement tool storage logic
	return nil
}

func (pc *PrepCook) disassembleEquipment(equipment string) error {
	// Implement equipment disassembly logic
	return nil
}

func (pc *PrepCook) washEquipment(equipment string) error {
	// Implement equipment washing logic
	return nil
}

func (pc *PrepCook) rinseEquipment(equipment string) error {
	// Implement equipment rinsing logic
	return nil
}

func (pc *PrepCook) sanitizeEquipment(equipment string) error {
	// Implement equipment sanitization logic
	return nil
}

func (pc *PrepCook) dryEquipment(equipment string) error {
	// Implement equipment drying logic
	return nil
}

func (pc *PrepCook) reassembleEquipment(equipment string) error {
	// Implement equipment reassembly logic
	return nil
}
