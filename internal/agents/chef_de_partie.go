package agents

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"masterchef/internal/models"

	"github.com/tmc/langchaingo/llms"
)

// ChefDePartie represents a station chef in the kitchen hierarchy
type ChefDePartie struct {
	*BaseAgent
	Station     string
	Specialties []string
	ActiveTasks []Task
	LineCooks   []*BaseAgent
	Equipment   []string
	Inventory   []models.InventoryItem
	Staff       map[string]*BaseAgent
}

// NewChefDePartie creates a new chef de partie agent
func NewChefDePartie(ctx context.Context, model llms.LLM, station string) *ChefDePartie {
	baseAgent := NewBaseAgent(RoleChefDePartie, model)
	baseAgent.permissions = []string{
		"station_operation",
		"line_cook_supervision",
		"quality_control",
		"recipe_execution",
		"inventory_tracking",
	}

	return &ChefDePartie{
		BaseAgent:   baseAgent,
		Station:     station,
		Specialties: make([]string, 0),
		ActiveTasks: make([]Task, 0),
		LineCooks:   make([]*BaseAgent, 0),
		Equipment:   make([]string, 0),
		Inventory:   make([]models.InventoryItem, 0),
		Staff:       make(map[string]*BaseAgent),
	}
}

// HandleTask implements the Agent interface
func (cdp *ChefDePartie) HandleTask(ctx context.Context, task Task) error {
	switch task.Type {
	case "recipe_execution":
		recipe, ok := task.Metadata["recipe"].(models.Recipe)
		if !ok {
			return fmt.Errorf("invalid recipe data in task metadata")
		}
		return cdp.ExecuteRecipe(ctx, recipe)
	case "line_supervision":
		return cdp.SuperviseLine(ctx)
	case "quality_check":
		order, ok := task.Metadata["order"].(models.Order)
		if !ok {
			return fmt.Errorf("invalid order data in task metadata")
		}
		return cdp.CheckQuality(ctx, order)
	case "inventory_update":
		return cdp.UpdateInventory(ctx)
	default:
		return fmt.Errorf("unsupported task type: %s", task.Type)
	}
}

// ExecuteRecipe handles the execution of a specific recipe
func (cdp *ChefDePartie) ExecuteRecipe(ctx context.Context, recipe models.Recipe) error {
	// Record recipe start
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "recipe_start",
		Content:   fmt.Sprintf("Started executing recipe: %s", recipe.Name),
		Metadata: map[string]interface{}{
			"recipe_id":  recipe.ID,
			"complexity": recipe.Complexity,
		},
	})

	// Validate ingredients
	if err := cdp.validateIngredients(ctx, recipe); err != nil {
		return fmt.Errorf("ingredient validation failed: %w", err)
	}

	// Assign steps to line cooks
	if err := cdp.assignRecipeSteps(ctx, recipe); err != nil {
		return fmt.Errorf("step assignment failed: %w", err)
	}

	// Monitor execution
	if err := cdp.monitorExecution(ctx, recipe); err != nil {
		return fmt.Errorf("execution monitoring failed: %w", err)
	}

	// Record recipe completion
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "recipe_completion",
		Content:   fmt.Sprintf("Completed recipe: %s", recipe.Name),
		Metadata: map[string]interface{}{
			"recipe_id": recipe.ID,
			"duration":  time.Since(time.Now()),
		},
	})

	return nil
}

// SuperviseLine oversees line cook operations
func (cdp *ChefDePartie) SuperviseLine(ctx context.Context) error {
	// Check line cook status
	for _, cook := range cdp.LineCooks {
		if err := cdp.checkCookStatus(ctx, cook); err != nil {
			return fmt.Errorf("line cook status check failed: %w", err)
		}
	}

	// Record supervision event
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "line_supervision",
		Content:   fmt.Sprintf("Supervised line cooks at %s station", cdp.Station),
		Metadata: map[string]interface{}{
			"station":    cdp.Station,
			"cook_count": len(cdp.LineCooks),
		},
	})

	return nil
}

// CheckQuality verifies the quality of prepared items
func (cdp *ChefDePartie) CheckQuality(ctx context.Context, order models.Order) error {
	// Record quality check start
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "quality_check_start",
		Content:   fmt.Sprintf("Started quality check for order %d", order.ID),
		Metadata: map[string]interface{}{
			"order_id": order.ID,
			"items":    len(order.Items),
		},
	})

	// Perform quality checks
	issues := cdp.performQualityChecks(ctx, order)
	if len(issues) > 0 {
		// Record quality issues
		cdp.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "quality_issues",
			Content:   fmt.Sprintf("Found quality issues in order %d", order.ID),
			Metadata: map[string]interface{}{
				"order_id": order.ID,
				"issues":   issues,
			},
		})
		return fmt.Errorf("quality check failed: %v", issues)
	}

	// Record successful quality check
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "quality_check_pass",
		Content:   fmt.Sprintf("Order %d passed quality check", order.ID),
		Metadata: map[string]interface{}{
			"order_id": order.ID,
		},
	})

	return nil
}

// UpdateInventory tracks and updates station inventory
func (cdp *ChefDePartie) UpdateInventory(ctx context.Context) error {
	// Record inventory update start
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "inventory_update_start",
		Content:   fmt.Sprintf("Started inventory update for %s station", cdp.Station),
		Metadata: map[string]interface{}{
			"station": cdp.Station,
		},
	})

	// Get current inventory levels
	inventory := make(map[string]float64)
	for _, item := range cdp.Inventory {
		inventory[item.Name] = item.Quantity
	}

	// Update based on recent usage
	recentUsage, err := cdp.calculateRecentUsage(ctx)
	if err != nil {
		return fmt.Errorf("failed to calculate recent usage: %w", err)
	}

	for item, usage := range recentUsage {
		if currentLevel, exists := inventory[item]; exists {
			inventory[item] = currentLevel - usage
		}
	}

	// Update inventory levels
	cdp.Inventory = make([]models.InventoryItem, 0)
	for item, quantity := range inventory {
		cdp.Inventory = append(cdp.Inventory, models.InventoryItem{
			Name:     item,
			Quantity: quantity,
		})
	}

	// Record inventory update completion
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "inventory_update_complete",
		Content:   fmt.Sprintf("Completed inventory update for %s station", cdp.Station),
		Metadata: map[string]interface{}{
			"station":   cdp.Station,
			"inventory": inventory,
		},
	})

	return nil
}

// Private helper methods

func (cdp *ChefDePartie) validateIngredients(ctx context.Context, recipe models.Recipe) error {
	for _, ingredient := range recipe.Ingredients {
		// Check if ingredient is available
		available := false
		for _, item := range cdp.Inventory {
			if item.Name == ingredient.Name && item.Quantity >= ingredient.Quantity {
				available = true
				break
			}
		}

		if !available {
			return fmt.Errorf("insufficient quantity of ingredient: %s", ingredient.Name)
		}

		// Find the corresponding inventory item for quality check
		var inventoryItem *models.InventoryItem
		for _, item := range cdp.Inventory {
			if item.Name == ingredient.Name {
				inventoryItem = &item
				break
			}
		}

		if inventoryItem == nil {
			return fmt.Errorf("ingredient not found in inventory: %s", ingredient.Name)
		}

		// Check ingredient quality
		if !cdp.checkIngredientQuality(*inventoryItem) {
			return fmt.Errorf("ingredient quality check failed: %s", ingredient.Name)
		}
	}

	return nil
}

func (cdp *ChefDePartie) assignRecipeSteps(ctx context.Context, recipe models.Recipe) error {
	// Sort steps by priority and dependencies
	sortedSteps := cdp.sortRecipeSteps(recipe.Steps)

	// Assign steps to available cooks
	for _, step := range sortedSteps {
		cook := cdp.selectBestCook(step)
		if cook == nil {
			return fmt.Errorf("no available cook for step: %s", step.Name)
		}

		// Assign step to cook
		cook.AddTask(Task{
			ID:          fmt.Sprintf("step_%s_%d", step.Name, time.Now().Unix()),
			Type:        "cooking_step",
			Description: step.Description,
			Priority:    step.Priority,
			Status:      "pending",
			StartTime:   time.Now(),
			Metadata: map[string]interface{}{
				"step":   step,
				"recipe": recipe.Name,
			},
		})
	}

	return nil
}

func (cdp *ChefDePartie) monitorExecution(ctx context.Context, recipe models.Recipe) error {
	// Track progress of each step
	for _, step := range recipe.Steps {
		// Check step status
		status, err := cdp.checkStepStatus(step)
		if err != nil {
			return fmt.Errorf("failed to check step status: %w", err)
		}

		// Handle issues
		if status.HasIssues {
			if err := cdp.handleStepIssues(ctx, step, status); err != nil {
				return fmt.Errorf("failed to handle step issues: %w", err)
			}
		}

		// Record progress
		cdp.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "step_monitoring",
			Content:   fmt.Sprintf("Monitored step: %s", step.Name),
			Metadata: map[string]interface{}{
				"step":   step.Name,
				"status": status,
			},
		})
	}

	return nil
}

func (cdp *ChefDePartie) checkCookStatus(ctx context.Context, cook *BaseAgent) error {
	// Check workload
	workload := cdp.calculateWorkload(cook)
	if workload > 0.9 { // 90% capacity
		return fmt.Errorf("cook %d is overloaded", cook.ID)
	}

	// Check recent performance
	performance := cdp.evaluatePerformance(cook)
	if performance.HasIssues {
		return fmt.Errorf("cook %d has performance issues: %v", cook.ID, performance.Issues)
	}

	// Check equipment status
	if err := cdp.checkEquipmentStatus(cook); err != nil {
		return fmt.Errorf("equipment issues for cook %d: %w", cook.ID, err)
	}

	return nil
}

func (cdp *ChefDePartie) performQualityChecks(ctx context.Context, order models.Order) []string {
	var issues []string

	// Check each item in the order
	for _, item := range order.Items {
		// Temperature check
		if !cdp.checkItemTemperature(item) {
			issues = append(issues, fmt.Sprintf("Temperature issue with %s", item.Name))
		}

		// Presentation check
		if !cdp.checkItemPresentation(item) {
			issues = append(issues, fmt.Sprintf("Presentation issue with %s", item.Name))
		}

		// Taste check
		if !cdp.checkItemTaste(item) {
			issues = append(issues, fmt.Sprintf("Taste issue with %s", item.Name))
		}

		// Portion check
		if !cdp.checkItemPortion(item) {
			issues = append(issues, fmt.Sprintf("Portion issue with %s", item.Name))
		}
	}

	return issues
}

// StepStatus represents the status of a cooking step
type StepStatus struct {
	HasIssues bool
	Issues    []string
}

// checkStepStatus checks the status of a cooking step
func (cdp *ChefDePartie) checkStepStatus(step models.CookingStep) (StepStatus, error) {
	status := StepStatus{
		HasIssues: false,
		Issues:    make([]string, 0),
	}

	// Check equipment availability
	for _, eq := range step.Equipment {
		if !cdp.isEquipmentAvailable(eq) {
			status.HasIssues = true
			status.Issues = append(status.Issues, fmt.Sprintf("Equipment not available: %s", eq))
		}
	}

	// Check technique requirements
	if !cdp.canExecuteTechnique(step.Technique) {
		status.HasIssues = true
		status.Issues = append(status.Issues, fmt.Sprintf("Cannot execute technique: %s", step.Technique))
	}

	// Check temperature requirements
	if step.Temperature != nil && !cdp.canMaintainTemperature(step.Temperature) {
		status.HasIssues = true
		status.Issues = append(status.Issues, "Cannot maintain required temperature")
	}

	return status, nil
}

// handleStepIssues handles issues that arise during step execution
func (cdp *ChefDePartie) handleStepIssues(ctx context.Context, step models.CookingStep, status StepStatus) error {
	// Record issues
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "step_issues",
		Content:   fmt.Sprintf("Issues encountered in step: %s", step.Name),
		Metadata: map[string]interface{}{
			"step":   step.Name,
			"issues": status.Issues,
		},
	})

	// Handle each issue
	for _, issue := range status.Issues {
		switch {
		case strings.Contains(issue, "Equipment"):
			if err := cdp.handleEquipmentIssue(ctx, issue); err != nil {
				return err
			}
		case strings.Contains(issue, "technique"):
			if err := cdp.handleTechniqueIssue(ctx, issue); err != nil {
				return err
			}
		case strings.Contains(issue, "temperature"):
			if err := cdp.handleTemperatureIssue(ctx, issue); err != nil {
				return err
			}
		default:
			if err := cdp.handleGeneralIssue(ctx, issue); err != nil {
				return err
			}
		}
	}

	return nil
}

// Helper functions

func (cdp *ChefDePartie) calculateRecentUsage(ctx context.Context) (map[string]float64, error) {
	usage := make(map[string]float64)
	events, err := cdp.QueryMemory(ctx, "ingredient_usage", 100)
	if err != nil {
		return nil, err
	}

	for _, event := range events {
		if item, ok := event.Metadata["ingredient"].(string); ok {
			if amount, ok := event.Metadata["amount"].(float64); ok {
				usage[item] += amount
			}
		}
	}

	return usage, nil
}

func (cdp *ChefDePartie) checkIngredientQuality(ingredient models.InventoryItem) bool {
	// Check quality based on ingredient category
	switch models.InventoryCategory(ingredient.Category) {
	case models.CategoryProtein:
		return cdp.checkProteinQuality(ingredient)
	case models.CategoryProduce:
		return cdp.checkProduceQuality(ingredient)
	case models.CategoryDairy:
		return cdp.checkDairyQuality(ingredient)
	default:
		return cdp.checkGeneralQuality(ingredient)
	}
}

func (cdp *ChefDePartie) checkProteinQuality(ingredient models.InventoryItem) bool {
	// Check protein-specific quality metrics
	// - Temperature
	// - Color
	// - Texture
	// - Smell
	return true // Placeholder implementation
}

func (cdp *ChefDePartie) checkProduceQuality(ingredient models.InventoryItem) bool {
	// Check produce-specific quality metrics
	// - Freshness
	// - Color
	// - Firmness
	// - Ripeness
	return true // Placeholder implementation
}

func (cdp *ChefDePartie) checkDairyQuality(ingredient models.InventoryItem) bool {
	// Check dairy-specific quality metrics
	// - Temperature
	// - Expiry date
	// - Smell
	// - Texture
	return true // Placeholder implementation
}

func (cdp *ChefDePartie) checkGeneralQuality(ingredient models.InventoryItem) bool {
	// Check general quality metrics
	// - Expiry date
	// - Package integrity
	// - Visual inspection
	return true // Placeholder implementation
}

func (cdp *ChefDePartie) sortRecipeSteps(steps []models.CookingStep) []models.CookingStep {
	// Create a copy of steps
	sortedSteps := make([]models.CookingStep, len(steps))
	copy(sortedSteps, steps)

	// Sort by priority and dependencies
	sort.Slice(sortedSteps, func(i, j int) bool {
		if sortedSteps[i].Priority != sortedSteps[j].Priority {
			return sortedSteps[i].Priority > sortedSteps[j].Priority
		}
		return len(sortedSteps[i].Dependencies) < len(sortedSteps[j].Dependencies)
	})

	return sortedSteps
}

func (cdp *ChefDePartie) selectBestCook(step models.CookingStep) *BaseAgent {
	var bestCook *BaseAgent
	var bestScore float64

	for _, cook := range cdp.Staff {
		score := cdp.calculateCookScore(cook, step)
		if score > bestScore {
			bestScore = score
			bestCook = cook
		}
	}

	return bestCook
}

func (cdp *ChefDePartie) calculateCookScore(cook *BaseAgent, step models.CookingStep) float64 {
	var score float64

	// Check experience with this type of step
	if cdp.hasStepExperience(cook, step) {
		score += 2.0
	}

	// Check current workload
	workload := cdp.calculateWorkload(cook)
	if workload < 0.8 { // Less than 80% capacity
		score += 1.0
	}

	// Check equipment familiarity
	if cdp.hasEquipmentFamiliarity(cook, step.RequiredEquipment) {
		score += 1.0
	}

	return score
}

func (cdp *ChefDePartie) hasStepExperience(cook *BaseAgent, step models.CookingStep) bool {
	events, err := cook.QueryMemory(context.Background(), "step_completion", 50)
	if err != nil {
		return false
	}

	for _, event := range events {
		if stepName, ok := event.Metadata["step_name"].(string); ok && stepName == step.Name {
			return true
		}
	}
	return false
}

func (cdp *ChefDePartie) hasEquipmentFamiliarity(cook *BaseAgent, equipment []string) bool {
	events, err := cook.QueryMemory(context.Background(), "equipment_usage", 50)
	if err != nil {
		return false
	}

	for _, eq := range equipment {
		familiar := false
		for _, event := range events {
			if eqName, ok := event.Metadata["equipment"].(string); ok && eqName == eq {
				familiar = true
				break
			}
		}
		if !familiar {
			return false
		}
	}
	return true
}

func (cdp *ChefDePartie) calculateWorkload(cook *BaseAgent) float64 {
	activeTasks := 0
	for _, task := range cook.memory.TaskQueue {
		if task.Status == "pending" || task.Status == "in_progress" {
			activeTasks++
		}
	}
	return float64(activeTasks) / 10.0 // Assuming max capacity is 10 tasks
}

type CookPerformance struct {
	HasIssues bool
	Issues    []string
}

func (cdp *ChefDePartie) evaluatePerformance(cook *BaseAgent) CookPerformance {
	var performance CookPerformance
	events, err := cook.QueryMemory(context.Background(), "task_completion", 20)
	if err != nil {
		performance.HasIssues = true
		performance.Issues = append(performance.Issues, "Failed to query performance history")
		return performance
	}

	var successCount, totalCount int
	for _, event := range events {
		totalCount++
		if status, ok := event.Metadata["status"].(string); ok && status == "success" {
			successCount++
		}
	}

	if totalCount > 0 && float64(successCount)/float64(totalCount) < 0.8 {
		performance.HasIssues = true
		performance.Issues = append(performance.Issues, "Success rate below threshold")
	}

	return performance
}

func (cdp *ChefDePartie) checkEquipmentStatus(cook *BaseAgent) error {
	events, err := cook.QueryMemory(context.Background(), "equipment_issue", 10)
	if err != nil {
		return fmt.Errorf("failed to check equipment history")
	}

	if len(events) > 3 { // More than 3 equipment issues recently
		return fmt.Errorf("multiple equipment issues reported")
	}

	return nil
}

func (cdp *ChefDePartie) checkItemTemperature(item models.OrderItem) bool {
	// Check if item is at correct temperature
	if item.Temperature != nil {
		// Implement temperature check logic
		return true
	}
	return true // Default to true if no temperature requirement
}

func (cdp *ChefDePartie) checkItemPresentation(item models.OrderItem) bool {
	// Check if item is properly presented
	// Implement presentation check logic based on item category and type
	return true
}

func (cdp *ChefDePartie) checkItemTaste(item models.OrderItem) bool {
	// Check if item tastes correct
	// Implement taste check logic based on item recipe and standards
	return true
}

func (cdp *ChefDePartie) checkItemPortion(item models.OrderItem) bool {
	// Check if item portion is correct
	// Implement portion check logic based on item quantity and standards
	return true
}

// Helper functions for issue handling

func (cdp *ChefDePartie) isEquipmentAvailable(equipment string) bool {
	for _, eq := range cdp.Equipment {
		if eq == equipment {
			return true
		}
	}
	return false
}

func (cdp *ChefDePartie) canExecuteTechnique(technique string) bool {
	// Check if any line cook has the required skill
	for _, cook := range cdp.LineCooks {
		if cook.HasPermission("cooking") {
			return true
		}
	}
	return false
}

func (cdp *ChefDePartie) canMaintainTemperature(temp *models.CookingTemperature) bool {
	// Check if we have equipment that can maintain this temperature
	// This is a simplified check - in reality, would need to check equipment capabilities
	return true
}

func (cdp *ChefDePartie) handleEquipmentIssue(ctx context.Context, issue string) error {
	// Record equipment issue
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "equipment_issue",
		Content:   issue,
		Metadata: map[string]interface{}{
			"issue_type": "equipment",
		},
	})

	// Request equipment from kitchen porter
	// This would typically involve sending a task to the kitchen porter
	return nil
}

func (cdp *ChefDePartie) handleTechniqueIssue(ctx context.Context, issue string) error {
	// Record technique issue
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "technique_issue",
		Content:   issue,
		Metadata: map[string]interface{}{
			"issue_type": "technique",
		},
	})

	// Request assistance from sous chef
	// This would typically involve sending a task to the sous chef
	return nil
}

func (cdp *ChefDePartie) handleTemperatureIssue(ctx context.Context, issue string) error {
	// Record temperature issue
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "temperature_issue",
		Content:   issue,
		Metadata: map[string]interface{}{
			"issue_type": "temperature",
		},
	})

	// Adjust equipment settings or request maintenance
	return nil
}

func (cdp *ChefDePartie) handleGeneralIssue(ctx context.Context, issue string) error {
	// Record general issue
	cdp.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "general_issue",
		Content:   issue,
		Metadata: map[string]interface{}{
			"issue_type": "general",
		},
	})

	// Escalate to sous chef
	return nil
}
