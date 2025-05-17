package agents

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"masterchef/internal/models"

	"github.com/tmc/langchaingo/llms"
)

// ExecutiveChef represents the highest-level agent in the kitchen hierarchy
type ExecutiveChef struct {
	*BaseAgent
	MenuPlanner   *MenuPlanner
	KitchenStatus *KitchenStatus
	Staff         map[string]*BaseAgent
}

// KitchenStatus tracks the overall state of the kitchen
type KitchenStatus struct {
	ActiveOrders    []models.Order
	CompletedOrders []models.Order
	InventoryLevels map[string]float64
	StaffStatus     map[string]string
}

// MenuPlanner handles menu-related operations
type MenuPlanner struct {
	CurrentMenu  []models.MenuItem
	Specialties  []models.MenuItem
	Restrictions []string
}

// MenuItem represents a dish on the menu
type MenuItem struct {
	Name        string
	Description string
	Ingredients []string
	PrepTime    time.Duration
	CookTime    time.Duration
	Difficulty  int
	Category    string
	Price       float64
}

// Order represents a customer order
type Order struct {
	ID            string
	Items         []MenuItem
	Status        string
	Priority      int
	TimeReceived  time.Time
	TimeCompleted time.Time
	AssignedTo    string
}

// NewExecutiveChef creates a new executive chef agent
func NewExecutiveChef(ctx context.Context, model llms.LLM) *ExecutiveChef {
	baseAgent := NewBaseAgent(RoleExecutiveChef, model)
	baseAgent.permissions = []string{
		"menu_planning",
		"staff_management",
		"inventory_control",
		"quality_control",
		"kitchen_supervision",
	}

	return &ExecutiveChef{
		BaseAgent: baseAgent,
		MenuPlanner: &MenuPlanner{
			CurrentMenu:  make([]models.MenuItem, 0),
			Specialties:  make([]models.MenuItem, 0),
			Restrictions: make([]string, 0),
		},
		KitchenStatus: &KitchenStatus{
			ActiveOrders:    make([]models.Order, 0),
			CompletedOrders: make([]models.Order, 0),
			InventoryLevels: make(map[string]float64),
			StaffStatus:     make(map[string]string),
		},
		Staff: make(map[string]*BaseAgent),
	}
}

// HandleTask implements the Agent interface
func (ec *ExecutiveChef) HandleTask(ctx context.Context, task Task) error {
	switch task.Type {
	case "menu_planning":
		return ec.PlanMenu(ctx)
	case "kitchen_supervision":
		return ec.SuperviseKitchen(ctx)
	case "order_assignment":
		order, ok := task.Metadata["order"].(models.Order)
		if !ok {
			return fmt.Errorf("invalid order data in task metadata")
		}
		return ec.AssignOrder(ctx, order)
	default:
		return fmt.Errorf("unsupported task type: %s", task.Type)
	}
}

// PlanMenu creates or updates the menu based on various factors
func (ec *ExecutiveChef) PlanMenu(ctx context.Context) error {
	// Analyze current inventory
	if err := ec.checkInventory(ctx); err != nil {
		return fmt.Errorf("inventory check failed: %w", err)
	}

	// Consider seasonal ingredients
	seasonalItems := ec.getSeasonalIngredients(ctx)

	// Update menu items
	return ec.updateMenu(ctx, seasonalItems)
}

// SuperviseKitchen manages overall kitchen operations
func (ec *ExecutiveChef) SuperviseKitchen(ctx context.Context) error {
	// Monitor active orders
	if err := ec.monitorOrders(ctx); err != nil {
		return fmt.Errorf("order monitoring failed: %w", err)
	}

	// Check staff performance
	if err := ec.evaluateStaff(ctx); err != nil {
		return fmt.Errorf("staff evaluation failed: %w", err)
	}

	// Manage inventory
	if err := ec.manageInventory(ctx); err != nil {
		return fmt.Errorf("inventory management failed: %w", err)
	}

	return nil
}

// AssignOrder delegates an order to appropriate staff
func (ec *ExecutiveChef) AssignOrder(ctx context.Context, order models.Order) error {
	// Determine best staff member for the order
	assignee := ec.selectAssignee(ctx, order)
	if assignee == 0 {
		return fmt.Errorf("no suitable staff member found for order %s", order.ID)
	}

	// Update order status
	order.AssignedTo = ec.Staff[strconv.FormatUint(uint64(assignee), 10)].ID
	order.Status = string(models.OrderStatusAssigned)
	ec.KitchenStatus.ActiveOrders = append(ec.KitchenStatus.ActiveOrders, order)

	// Record the assignment in memory
	ec.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "order_assignment",
		Content:   fmt.Sprintf("Assigned order %s to %s", order.ID, order.AssignedTo),
		Metadata: map[string]interface{}{
			"order_id": order.ID,
			"assignee": order.AssignedTo,
			"priority": order.Priority,
		},
	})

	return nil
}

// Private helper methods

// checkInventory performs a thorough inventory check
func (ec *ExecutiveChef) checkInventory(ctx context.Context) error {
	// Get current inventory levels
	for item, level := range ec.KitchenStatus.InventoryLevels {
		// Check against minimum required levels
		minLevel := ec.getMinimumLevel(item)
		if level < minLevel {
			// Record low inventory alert
			ec.AddMemory(ctx, Event{
				Timestamp: time.Now(),
				Type:      "inventory_alert",
				Content:   fmt.Sprintf("Low inventory for %s: %.2f units", item, level),
				Metadata: map[string]interface{}{
					"item":     item,
					"current":  level,
					"minimum":  minLevel,
					"priority": "high",
				},
			})

			// Order more if needed
			if err := ec.orderInventory(ctx, item, minLevel-level); err != nil {
				return fmt.Errorf("failed to order %s: %w", item, err)
			}
		}
	}
	return nil
}

// getSeasonalIngredients identifies currently seasonal ingredients
func (ec *ExecutiveChef) getSeasonalIngredients(ctx context.Context) []models.MenuItem {
	currentMonth := time.Now().Month()
	var seasonalItems []models.MenuItem

	// Define seasonal ingredients by month
	seasonalMap := map[time.Month][]string{
		time.December:  {"winter squash", "citrus", "root vegetables"},
		time.January:   {"winter squash", "citrus", "root vegetables"},
		time.February:  {"winter squash", "citrus", "root vegetables"},
		time.March:     {"spring peas", "asparagus", "artichokes"},
		time.April:     {"spring peas", "asparagus", "artichokes"},
		time.May:       {"spring peas", "asparagus", "artichokes"},
		time.June:      {"tomatoes", "zucchini", "berries"},
		time.July:      {"tomatoes", "zucchini", "berries"},
		time.August:    {"tomatoes", "zucchini", "berries"},
		time.September: {"apples", "pears", "mushrooms"},
		time.October:   {"apples", "pears", "mushrooms"},
		time.November:  {"apples", "pears", "mushrooms"},
	}

	// Get seasonal ingredients for current month
	currentSeasonalIngredients := seasonalMap[currentMonth]

	// Create menu items using seasonal ingredients
	for _, ingredient := range currentSeasonalIngredients {
		items := ec.createMenuItemsWithIngredient(ingredient)
		seasonalItems = append(seasonalItems, items...)
	}

	return seasonalItems
}

// updateMenu updates the menu based on seasonal ingredients
func (ec *ExecutiveChef) updateMenu(ctx context.Context, seasonalItems []models.MenuItem) error {
	// Remove out-of-season items
	ec.MenuPlanner.CurrentMenu = ec.filterOutOfSeasonItems(ec.MenuPlanner.CurrentMenu)

	// Add new seasonal items
	for _, item := range seasonalItems {
		// Check if we can support this item
		if ec.canSupportMenuItem(item) {
			ec.MenuPlanner.CurrentMenu = append(ec.MenuPlanner.CurrentMenu, item)

			// Record menu update
			ec.AddMemory(ctx, Event{
				Timestamp: time.Now(),
				Type:      "menu_update",
				Content:   fmt.Sprintf("Added seasonal item to menu: %s", item.Name),
				Metadata: map[string]interface{}{
					"item":     item.Name,
					"seasonal": true,
				},
			})
		}
	}

	// Update specialties based on current ingredients and staff skills
	ec.updateSpecialties(ctx)

	return nil
}

// monitorOrders tracks and manages active orders
func (ec *ExecutiveChef) monitorOrders(ctx context.Context) error {
	for _, order := range ec.KitchenStatus.ActiveOrders {
		// Check order status and timing
		if ec.isOrderDelayed(order) {
			// Escalate delayed orders
			if err := ec.escalateOrder(ctx, order); err != nil {
				return fmt.Errorf("failed to escalate order %s: %w", order.ID, err)
			}
		}

		// Check quality at each stage
		if err := ec.checkOrderQuality(ctx, order); err != nil {
			return fmt.Errorf("quality check failed for order %s: %w", order.ID, err)
		}

		// Update order status
		if err := ec.updateOrderStatus(ctx, order); err != nil {
			return fmt.Errorf("failed to update order %s status: %w", order.ID, err)
		}
	}
	return nil
}

// evaluateStaff assesses staff performance
func (ec *ExecutiveChef) evaluateStaff(ctx context.Context) error {
	for id, staff := range ec.Staff {
		// Calculate performance metrics
		metrics := ec.calculateStaffMetrics(staff)

		// Record evaluation
		ec.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "staff_evaluation",
			Content:   fmt.Sprintf("Evaluated staff member %s", id),
			Metadata: map[string]interface{}{
				"staff_id":   id,
				"metrics":    metrics,
				"evaluation": time.Now(),
			},
		})

		// Provide feedback and training if needed
		if metrics.NeedsImprovement {
			if err := ec.provideFeedback(ctx, id, metrics); err != nil {
				return fmt.Errorf("failed to provide feedback to %s: %w", id, err)
			}
		}

		// Update staff assignments based on performance
		if err := ec.optimizeStaffAssignments(ctx, id, metrics); err != nil {
			return fmt.Errorf("failed to optimize assignments for %s: %w", id, err)
		}
	}
	return nil
}

// manageInventory handles inventory control
func (ec *ExecutiveChef) manageInventory(ctx context.Context) error {
	// Check current inventory levels
	if err := ec.checkInventory(ctx); err != nil {
		return fmt.Errorf("inventory check failed: %w", err)
	}

	// Optimize inventory based on menu and orders
	if err := ec.optimizeInventory(ctx); err != nil {
		return fmt.Errorf("inventory optimization failed: %w", err)
	}

	// Track waste and adjust ordering
	if err := ec.trackWaste(ctx); err != nil {
		return fmt.Errorf("waste tracking failed: %w", err)
	}

	// Update inventory records
	if err := ec.updateInventoryRecords(ctx); err != nil {
		return fmt.Errorf("inventory record update failed: %w", err)
	}

	return nil
}

// Helper functions

func (ec *ExecutiveChef) getMinimumLevel(item string) float64 {
	// Calculate minimum level based on historical usage and menu requirements
	baseLevel := 10.0 // Base minimum level

	// Adjust based on menu items using this ingredient
	menuUsage := ec.calculateMenuUsage(item)
	baseLevel += menuUsage * 1.5

	// Adjust based on historical order volume
	orderVolume := ec.calculateOrderVolume(item)
	baseLevel += orderVolume * 1.2

	// Add safety margin
	baseLevel *= 1.2

	return baseLevel
}

func (ec *ExecutiveChef) orderInventory(ctx context.Context, item string, amount float64) error {
	// Create order request
	order := struct {
		Item     string
		Amount   float64
		Priority string
		DueDate  time.Time
	}{
		Item:     item,
		Amount:   amount,
		Priority: "normal",
		DueDate:  time.Now().Add(24 * time.Hour),
	}

	// Record order request
	ec.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "inventory_order",
		Content:   fmt.Sprintf("Ordered %.2f units of %s", amount, item),
		Metadata: map[string]interface{}{
			"item":     item,
			"amount":   amount,
			"priority": order.Priority,
			"due_date": order.DueDate,
		},
	})

	return nil
}

func (ec *ExecutiveChef) createMenuItemsWithIngredient(ingredient string) []models.MenuItem {
	var items []models.MenuItem

	// Create menu items based on ingredient type
	switch ingredient {
	case "winter squash":
		items = append(items, models.MenuItem{
			Name:        "Roasted Butternut Squash Soup",
			Description: "Creamy soup with roasted butternut squash and sage",
			Category:    string(models.MenuCategoryAppetizer),
			Price:       12.99,
			PrepTime:    30 * time.Minute,
			CookTime:    45 * time.Minute,
			Ingredients: []string{ingredient, "sage", "cream", "onion", "garlic"},
			IsSpecialty: true,
		})
	case "citrus":
		items = append(items, models.MenuItem{
			Name:        "Citrus Glazed Salmon",
			Description: "Fresh salmon with citrus glaze",
			Category:    string(models.MenuCategoryEntree),
			Price:       24.99,
			PrepTime:    20 * time.Minute,
			CookTime:    15 * time.Minute,
			Ingredients: []string{ingredient, "salmon", "honey", "ginger"},
			IsSpecialty: true,
		})
		// Add more cases for other ingredients
	}

	return items
}

func (ec *ExecutiveChef) filterOutOfSeasonItems(menu []models.MenuItem) []models.MenuItem {
	currentMonth := time.Now().Month()
	var filtered []models.MenuItem

	for _, item := range menu {
		// Check if all ingredients are in season
		allInSeason := true
		for _, ingredient := range item.Ingredients {
			if !ec.isIngredientInSeason(ingredient, currentMonth) {
				allInSeason = false
				break
			}
		}
		if allInSeason {
			filtered = append(filtered, item)
		}
	}

	return filtered
}

func (ec *ExecutiveChef) canSupportMenuItem(item models.MenuItem) bool {
	// Check if we have the necessary equipment
	if !ec.hasRequiredEquipment(item) {
		return false
	}

	// Check if staff has necessary skills
	if !ec.hasRequiredSkills(item) {
		return false
	}

	// Check if ingredients are available
	if !ec.hasRequiredIngredients(item) {
		return false
	}

	return true
}

func (ec *ExecutiveChef) updateSpecialties(ctx context.Context) {
	// Update menu specialties based on:
	// 1. Seasonal ingredients
	// 2. Staff expertise
	// 3. Customer preferences
	// 4. Historical performance

	for _, item := range ec.MenuPlanner.CurrentMenu {
		score := ec.calculateSpecialtyScore(item)
		if score > 8.0 { // High-performing items become specialties
			item.IsSpecialty = true
			ec.MenuPlanner.Specialties = append(ec.MenuPlanner.Specialties, item)

			// Record specialty update
			ec.AddMemory(ctx, Event{
				Timestamp: time.Now(),
				Type:      "specialty_update",
				Content:   fmt.Sprintf("Added %s to specialties", item.Name),
				Metadata: map[string]interface{}{
					"item":  item.Name,
					"score": score,
				},
			})
		}
	}
}

func (ec *ExecutiveChef) isOrderDelayed(order models.Order) bool {
	expectedDuration := ec.calculateExpectedDuration(order)
	actualDuration := time.Since(order.TimeReceived)
	return actualDuration > time.Duration(float64(expectedDuration)*1.5) // 50% buffer
}

func (ec *ExecutiveChef) escalateOrder(ctx context.Context, order models.Order) error {
	// Increase priority
	order.Priority++

	// Reassign if necessary
	if order.Priority > 8 {
		newAssignee := ec.selectAssignee(ctx, order)
		if newAssignee != order.AssignedTo {
			order.AssignedTo = newAssignee
			// Record reassignment
			ec.AddMemory(ctx, Event{
				Timestamp: time.Now(),
				Type:      "order_escalation",
				Content:   fmt.Sprintf("Reassigned delayed order %s", order.ID),
				Metadata: map[string]interface{}{
					"order_id":     order.ID,
					"new_assignee": newAssignee,
					"priority":     order.Priority,
				},
			})
		}
	}

	return nil
}

func (ec *ExecutiveChef) checkOrderQuality(ctx context.Context, order models.Order) error {
	// Define quality checks
	checks := []struct {
		name     string
		check    func(models.Order) bool
		critical bool
	}{
		{"temperature", ec.checkTemperature, true},
		{"presentation", ec.checkPresentation, true},
		{"timing", ec.checkTiming, false},
		{"portion", ec.checkPortion, true},
	}

	// Perform checks
	for _, check := range checks {
		if !check.check(order) {
			msg := fmt.Sprintf("Quality check failed: %s", check.name)
			if check.critical {
				return fmt.Errorf(msg)
			}
			// Record non-critical issues
			ec.AddMemory(ctx, Event{
				Timestamp: time.Now(),
				Type:      "quality_warning",
				Content:   msg,
				Metadata: map[string]interface{}{
					"order_id": order.ID,
					"check":    check.name,
				},
			})
		}
	}

	return nil
}

func (ec *ExecutiveChef) updateOrderStatus(ctx context.Context, order models.Order) error {
	// Update status based on progress
	newStatus := ec.determineOrderStatus(order)
	if newStatus != order.Status {
		order.Status = newStatus
		// Record status change
		ec.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "order_status_change",
			Content:   fmt.Sprintf("Updated order %s status to %s", order.ID, newStatus),
			Metadata: map[string]interface{}{
				"order_id":     order.ID,
				"new_status":   newStatus,
				"time_in_prev": time.Since(order.TimeReceived),
			},
		})
	}

	return nil
}

// Additional helper functions

func (ec *ExecutiveChef) calculateMenuUsage(item string) float64 {
	// Calculate how much of this item is used in menu items
	var usage float64
	for _, menuItem := range ec.MenuPlanner.CurrentMenu {
		if menuItem.HasIngredient(item) {
			usage += 1.0
		}
	}
	return usage
}

func (ec *ExecutiveChef) calculateOrderVolume(item string) float64 {
	// Calculate average daily order volume for this item
	return 5.0 // Placeholder implementation
}

func (ec *ExecutiveChef) isIngredientInSeason(ingredient string, month time.Month) bool {
	// Check if ingredient is in season for the given month
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) hasRequiredEquipment(item models.MenuItem) bool {
	// Check if kitchen has all required equipment
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) hasRequiredSkills(item models.MenuItem) bool {
	// Check if staff has necessary skills
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) hasRequiredIngredients(item models.MenuItem) bool {
	// Check if all ingredients are available
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) calculateSpecialtyScore(item models.MenuItem) float64 {
	// Calculate score based on various factors
	return 9.0 // Placeholder implementation
}

func (ec *ExecutiveChef) calculateExpectedDuration(order models.Order) time.Duration {
	// Calculate expected preparation time
	var total time.Duration
	for _, item := range order.Items {
		total += item.PrepTime + item.CookTime
	}
	return total
}

func (ec *ExecutiveChef) checkTemperature(order models.Order) bool {
	// Check if items are at correct temperature
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) checkPresentation(order models.Order) bool {
	// Check if items are properly presented
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) checkTiming(order models.Order) bool {
	// Check if items are prepared in correct order
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) checkPortion(order models.Order) bool {
	// Check if portions are correct
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) determineOrderStatus(order models.Order) string {
	// Determine current status based on progress
	return string(models.OrderStatusPreparing) // Placeholder implementation
}

func (ec *ExecutiveChef) calculateStaffMetrics(staff *BaseAgent) struct{ NeedsImprovement bool } {
	// Implement staff metrics calculation logic
	return struct{ NeedsImprovement bool }{false}
}

func (ec *ExecutiveChef) provideFeedback(ctx context.Context, staffID string, metrics struct{ NeedsImprovement bool }) error {
	// Implement feedback provision logic
	return nil
}

func (ec *ExecutiveChef) optimizeStaffAssignments(ctx context.Context, staffID string, metrics struct{ NeedsImprovement bool }) error {
	// Implement staff assignment optimization logic
	return nil
}

func (ec *ExecutiveChef) optimizeInventory(ctx context.Context) error {
	// Implement inventory optimization logic
	return nil
}

func (ec *ExecutiveChef) trackWaste(ctx context.Context) error {
	// Implement waste tracking logic
	return nil
}

func (ec *ExecutiveChef) updateInventoryRecords(ctx context.Context) error {
	// Implement inventory record update logic
	return nil
}

func (ec *ExecutiveChef) selectAssignee(ctx context.Context, order models.Order) uint {
	var bestAssignee uint
	var bestScore float64

	// Calculate score for each staff member
	for id, staff := range ec.Staff {
		score := ec.calculateAssignmentScore(staff, order)
		if score > bestScore {
			bestScore = score
			// Convert string ID to uint
			if uid, err := strconv.ParseUint(id, 10, 32); err == nil {
				bestAssignee = uint(uid)
			}
		}
	}

	return bestAssignee
}

func (ec *ExecutiveChef) calculateAssignmentScore(staff *BaseAgent, order models.Order) float64 {
	var score float64

	// Check staff specialties
	for _, item := range order.Items {
		if ec.hasSpecialty(staff, item.Name) {
			score += 2.0
		}
	}

	// Check current workload
	workload := ec.getCurrentWorkload(staff)
	if workload < 0.8 { // Less than 80% capacity
		score += 1.0
	}

	// Check recent performance
	if metrics := ec.calculateStaffMetrics(staff); !metrics.NeedsImprovement {
		score += 1.0
	}

	return score
}

func (ec *ExecutiveChef) hasSpecialty(staff *BaseAgent, itemName string) bool {
	// Check if staff has this item as a specialty
	return true // Placeholder implementation
}

func (ec *ExecutiveChef) getCurrentWorkload(staff *BaseAgent) float64 {
	// Calculate current workload as a percentage of capacity
	return 0.5 // Placeholder implementation
}
