package agents

import (
	"context"
	"fmt"
	"time"

	"masterchef/internal/models"

	"github.com/tmc/langchaingo/llms"
)

// LineCook represents a line cook in the kitchen hierarchy
type LineCook struct {
	*BaseAgent
	Station     string
	Specialties []string
	Equipment   []string
	ActiveStep  *models.CookingStep
}

// NewLineCook creates a new line cook agent
func NewLineCook(ctx context.Context, model llms.LLM, station string) *LineCook {
	baseAgent := NewBaseAgent(RoleLineCook, model)
	baseAgent.permissions = []string{
		"cooking",
		"equipment_operation",
		"recipe_following",
		"basic_prep",
	}

	return &LineCook{
		BaseAgent:   baseAgent,
		Station:     station,
		Specialties: make([]string, 0),
		Equipment:   make([]string, 0),
		ActiveStep:  nil,
	}
}

// HandleTask implements the Agent interface
func (lc *LineCook) HandleTask(ctx context.Context, task Task) error {
	switch task.Type {
	case "cooking_step":
		step, ok := task.Metadata["step"].(models.CookingStep)
		if !ok {
			return fmt.Errorf("invalid cooking step data in task metadata")
		}
		return lc.ExecuteStep(ctx, step)
	case "equipment_prep":
		equipment, ok := task.Metadata["equipment"].(string)
		if !ok {
			return fmt.Errorf("invalid equipment data in task metadata")
		}
		return lc.PrepareEquipment(ctx, equipment)
	case "cleanup":
		return lc.CleanStation(ctx)
	default:
		return fmt.Errorf("unsupported task type: %s", task.Type)
	}
}

// ExecuteStep performs a single cooking step
func (lc *LineCook) ExecuteStep(ctx context.Context, step models.CookingStep) error {
	// Record step start
	lc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "step_start",
		Content:   fmt.Sprintf("Started cooking step: %s", step.Description),
		Metadata: map[string]interface{}{
			"step_id":   step.ID,
			"technique": step.Technique,
		},
	})

	// Set active step
	lc.ActiveStep = &step

	// Check equipment availability
	if err := lc.checkEquipment(ctx, step.Equipment); err != nil {
		return fmt.Errorf("equipment check failed: %w", err)
	}

	// Execute technique
	if err := lc.applyTechnique(ctx, step); err != nil {
		return fmt.Errorf("technique application failed: %w", err)
	}

	// Monitor temperature if required
	if step.Temperature != nil {
		temp := models.NewTemperatureFromCooking(step.Temperature)
		if err := lc.monitorTemperature(ctx, temp); err != nil {
			return fmt.Errorf("temperature monitoring failed: %w", err)
		}
	}

	// Record step completion
	lc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "step_completion",
		Content:   fmt.Sprintf("Completed cooking step: %s", step.Description),
		Metadata: map[string]interface{}{
			"step_id":  step.ID,
			"duration": time.Since(time.Now()),
		},
	})

	// Clear active step
	lc.ActiveStep = nil

	return nil
}

// PrepareEquipment sets up and checks equipment for use
func (lc *LineCook) PrepareEquipment(ctx context.Context, equipment string) error {
	// Record equipment preparation start
	lc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "equipment_prep_start",
		Content:   fmt.Sprintf("Started preparing equipment: %s", equipment),
		Metadata: map[string]interface{}{
			"equipment": equipment,
			"station":   lc.Station,
		},
	})

	// Check equipment condition
	if err := lc.checkEquipmentCondition(ctx, equipment); err != nil {
		return fmt.Errorf("equipment condition check failed: %w", err)
	}

	// Clean equipment if necessary
	if err := lc.cleanEquipment(ctx, equipment); err != nil {
		return fmt.Errorf("equipment cleaning failed: %w", err)
	}

	// Record equipment ready
	lc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "equipment_ready",
		Content:   fmt.Sprintf("Equipment ready: %s", equipment),
		Metadata: map[string]interface{}{
			"equipment": equipment,
			"status":    "ready",
		},
	})

	return nil
}

// CleanStation cleans and organizes the work station
func (lc *LineCook) CleanStation(ctx context.Context) error {
	// Record cleaning start
	lc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "station_cleaning_start",
		Content:   fmt.Sprintf("Started cleaning station: %s", lc.Station),
		Metadata: map[string]interface{}{
			"station": lc.Station,
		},
	})

	// Clean equipment
	for _, equipment := range lc.Equipment {
		if err := lc.cleanEquipment(ctx, equipment); err != nil {
			return fmt.Errorf("equipment cleaning failed: %w", err)
		}
	}

	// Sanitize surfaces
	if err := lc.sanitizeSurfaces(ctx); err != nil {
		return fmt.Errorf("surface sanitization failed: %w", err)
	}

	// Organize tools
	if err := lc.organizeTools(ctx); err != nil {
		return fmt.Errorf("tool organization failed: %w", err)
	}

	// Record cleaning completion
	lc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "station_cleaning_complete",
		Content:   fmt.Sprintf("Completed cleaning station: %s", lc.Station),
		Metadata: map[string]interface{}{
			"station": lc.Station,
			"status":  "clean",
		},
	})

	return nil
}

// Private helper methods

func (lc *LineCook) checkEquipment(ctx context.Context, required []string) error {
	for _, item := range required {
		// Check if equipment is assigned to this cook
		hasEquipment := false
		for _, assigned := range lc.Equipment {
			if assigned == item {
				hasEquipment = true
				break
			}
		}
		if !hasEquipment {
			return fmt.Errorf("required equipment not assigned: %s", item)
		}

		// Record equipment check
		lc.AddMemory(ctx, Event{
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

func (lc *LineCook) applyTechnique(ctx context.Context, step models.CookingStep) error {
	// Validate technique is within permissions
	if !lc.HasPermission("cooking") {
		return fmt.Errorf("line cook does not have cooking permission")
	}

	// Apply the technique
	switch step.Technique {
	case "grill":
		return lc.grillItem(ctx, step)
	case "saute":
		return lc.sauteItem(ctx, step)
	case "fry":
		return lc.fryItem(ctx, step)
	case "bake":
		return lc.bakeItem(ctx, step)
	default:
		return fmt.Errorf("unsupported technique: %s", step.Technique)
	}
}

// monitorTemperature monitors and adjusts cooking temperature
func (lc *LineCook) monitorTemperature(ctx context.Context, temp *models.TemperatureMonitor) error {
	// Set up temperature monitoring
	interval := time.Duration(temp.GetInterval()) * time.Second
	timer := time.NewTimer(interval)
	defer timer.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-timer.C:
			// Check current temperature
			currentTemp := temp.Current
			if currentTemp < temp.GetMin() || currentTemp > temp.GetMax() {
				// Record temperature issue
				lc.AddMemory(ctx, Event{
					Timestamp: time.Now(),
					Type:      "temperature_alert",
					Content:   fmt.Sprintf("Temperature out of range: %.1f°C", currentTemp),
					Metadata: map[string]interface{}{
						"current": currentTemp,
						"min":     temp.GetMin(),
						"max":     temp.GetMax(),
					},
				})

				// Adjust temperature
				if err := lc.adjustTemperature(ctx, temp); err != nil {
					return err
				}
			}

			timer.Reset(interval)
		}
	}
}

func (lc *LineCook) checkEquipmentCondition(ctx context.Context, equipment string) error {
	// Check equipment condition
	conditions := map[string]bool{
		"clean":      true,
		"calibrated": true,
		"maintained": true,
		"safe":       true,
	}

	for condition, required := range conditions {
		if !lc.verifyCondition(equipment, condition) {
			if required {
				return fmt.Errorf("equipment %s failed condition check: %s", equipment, condition)
			}
			// Log warning for non-critical issues
			lc.AddMemory(ctx, Event{
				Timestamp: time.Now(),
				Type:      "equipment_warning",
				Content:   fmt.Sprintf("Equipment %s needs attention: %s", equipment, condition),
				Metadata: map[string]interface{}{
					"equipment": equipment,
					"condition": condition,
				},
			})
		}
	}
	return nil
}

func (lc *LineCook) cleanEquipment(ctx context.Context, equipment string) error {
	steps := []struct {
		name string
		fn   func(string) error
	}{
		{"pre_clean", lc.preClean},
		{"wash", lc.wash},
		{"rinse", lc.rinse},
		{"sanitize", lc.sanitize},
		{"dry", lc.dry},
	}

	for _, step := range steps {
		if err := step.fn(equipment); err != nil {
			return fmt.Errorf("%s failed for %s: %w", step.name, equipment, err)
		}

		// Record cleaning step
		lc.AddMemory(ctx, Event{
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

func (lc *LineCook) sanitizeSurfaces(ctx context.Context) error {
	surfaces := []string{"prep_station", "cutting_board", "counter_top"}

	for _, surface := range surfaces {
		// Clean surface
		if err := lc.cleanSurface(surface); err != nil {
			return fmt.Errorf("failed to clean %s: %w", surface, err)
		}

		// Apply sanitizer
		if err := lc.applySanitizer(surface); err != nil {
			return fmt.Errorf("failed to sanitize %s: %w", surface, err)
		}

		// Allow surface to air dry
		if err := lc.waitForDrying(surface); err != nil {
			return fmt.Errorf("failed drying %s: %w", surface, err)
		}

		// Record sanitization
		lc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "surface_sanitization",
			Content:   fmt.Sprintf("Sanitized %s", surface),
			Metadata: map[string]interface{}{
				"surface": surface,
				"status":  "clean",
			},
		})
	}
	return nil
}

func (lc *LineCook) organizeTools(ctx context.Context) error {
	// Define tool organization map
	toolLocations := map[string]string{
		"knives":      "knife_block",
		"spatulas":    "utensil_drawer",
		"tongs":       "utensil_drawer",
		"bowls":       "prep_station",
		"measuring":   "storage_shelf",
		"thermometer": "tool_rack",
	}

	for tool, location := range toolLocations {
		// Clean tool before storing
		if err := lc.cleanTool(tool); err != nil {
			return fmt.Errorf("failed to clean %s: %w", tool, err)
		}

		// Store tool in proper location
		if err := lc.storeTool(tool, location); err != nil {
			return fmt.Errorf("failed to store %s in %s: %w", tool, location, err)
		}

		// Record organization
		lc.AddMemory(ctx, Event{
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

// Helper functions

func (lc *LineCook) verifyCondition(equipment, condition string) bool {
	// Implement actual condition verification logic
	return true
}

func (lc *LineCook) preClean(equipment string) error {
	// Implement pre-cleaning logic
	return nil
}

func (lc *LineCook) wash(equipment string) error {
	// Implement washing logic
	return nil
}

func (lc *LineCook) rinse(equipment string) error {
	// Implement rinsing logic
	return nil
}

func (lc *LineCook) sanitize(equipment string) error {
	// Implement sanitization logic
	return nil
}

func (lc *LineCook) dry(equipment string) error {
	// Implement drying logic
	return nil
}

func (lc *LineCook) cleanSurface(surface string) error {
	// Implement surface cleaning logic
	return nil
}

func (lc *LineCook) applySanitizer(surface string) error {
	// Implement sanitizer application logic
	return nil
}

func (lc *LineCook) waitForDrying(surface string) error {
	// Implement drying wait logic
	return nil
}

func (lc *LineCook) cleanTool(tool string) error {
	// Implement tool cleaning logic
	return nil
}

func (lc *LineCook) storeTool(tool, location string) error {
	// Implement tool storage logic
	return nil
}

func (lc *LineCook) adjustTemperature(ctx context.Context, temp *models.TemperatureMonitor) error {
	// Implement temperature adjustment logic
	return nil
}

func (lc *LineCook) grillItem(ctx context.Context, step models.CookingStep) error {
	// Implement grilling logic
	return nil
}

func (lc *LineCook) sauteItem(ctx context.Context, step models.CookingStep) error {
	// Implement sautéing logic
	return nil
}

func (lc *LineCook) fryItem(ctx context.Context, step models.CookingStep) error {
	// Implement frying logic
	return nil
}

func (lc *LineCook) bakeItem(ctx context.Context, step models.CookingStep) error {
	// Implement baking logic
	return nil
}
