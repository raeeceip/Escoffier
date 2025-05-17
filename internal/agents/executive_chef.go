package agents

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"strconv"
	"strings"
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
	ID            uint
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
		return fmt.Errorf("no suitable staff member found for order %d", order.ID)
	}

	// Update order status
	assigneeID := strconv.FormatUint(uint64(assignee), 10)
	order.AssignedTo = assigneeID
	order.Status = string(models.OrderStatusAssigned)
	ec.KitchenStatus.ActiveOrders = append(ec.KitchenStatus.ActiveOrders, order)

	// Record the assignment in memory
	ec.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "order_assignment",
		Content:   fmt.Sprintf("Assigned order %d to %s", order.ID, order.AssignedTo),
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
		time.December:  {"winter squash", "citrus", "root vegetables", "kale", "brussels sprouts"},
		time.January:   {"winter squash", "citrus", "root vegetables", "kale", "brussels sprouts"},
		time.February:  {"winter squash", "citrus", "root vegetables", "kale", "brussels sprouts"},
		time.March:     {"spring peas", "asparagus", "artichokes", "spring onions", "radishes"},
		time.April:     {"spring peas", "asparagus", "artichokes", "spring onions", "radishes"},
		time.May:       {"spring peas", "asparagus", "artichokes", "spring onions", "radishes"},
		time.June:      {"tomatoes", "zucchini", "berries", "corn", "eggplant"},
		time.July:      {"tomatoes", "zucchini", "berries", "corn", "eggplant"},
		time.August:    {"tomatoes", "zucchini", "berries", "corn", "eggplant"},
		time.September: {"apples", "pears", "mushrooms", "pumpkin", "grapes"},
		time.October:   {"apples", "pears", "mushrooms", "pumpkin", "grapes"},
		time.November:  {"apples", "pears", "mushrooms", "pumpkin", "grapes"},
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
				return fmt.Errorf("failed to escalate order %d: %w", order.ID, err)
			}
		}

		// Check quality at each stage
		if err := ec.checkOrderQuality(ctx, order); err != nil {
			return fmt.Errorf("quality check failed for order %d: %w", order.ID, err)
		}

		// Update order status
		if err := ec.updateOrderStatus(ctx, order); err != nil {
			return fmt.Errorf("failed to update order %d status: %w", order.ID, err)
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
		if newAssignee != 0 {
			newAssigneeID := strconv.FormatUint(uint64(newAssignee), 10)
			if newAssigneeID != order.AssignedTo {
				order.AssignedTo = newAssigneeID
				// Record reassignment
				ec.AddMemory(ctx, Event{
					Timestamp: time.Now(),
					Type:      "order_escalation",
					Content:   fmt.Sprintf("Reassigned delayed order %d", order.ID),
					Metadata: map[string]interface{}{
						"order_id":     order.ID,
						"new_assignee": newAssigneeID,
						"priority":     order.Priority,
					},
				})
			}
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
			Content:   fmt.Sprintf("Updated order %d status to %s", order.ID, newStatus),
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
	var score float64 = 5.0 // Base score

	// Factor 1: Seasonal ingredients (higher score for seasonal items)
	if ec.hasSeasonalIngredients(item) {
		score += 1.5
	}

	// Factor 2: Staff expertise (higher score if staff are skilled with this item)
	if ec.hasExpertiseForItem(item) {
		score += 1.0
	}

	// Factor 3: Ingredient availability (higher score for items with readily available ingredients)
	availabilityScore := ec.calculateIngredientAvailabilityScore(item)
	score += availabilityScore * 0.5 // Maximum +0.5 for full availability

	// Factor 4: Customer feedback (historical customer rating)
	customerRating := ec.getCustomerRating(item)
	score += (customerRating - 5.0) * 0.4 // Rating above 5 adds to score, below 5 reduces

	// Factor 5: Profit margin (higher score for more profitable items)
	profitMargin := ec.calculateProfitMargin(item)
	score += profitMargin * 0.3 // Maximum +0.3 for highest margin

	// Factor 6: Preparation complexity (slightly higher score for signature complex dishes)
	if item.Complexity > 7 {
		score += 0.2
	}

	// Factor 7: Kitchen capabilities (higher score if kitchen excels at this type of dish)
	if ec.isKitchenSpecialty(item) {
		score += 0.5
	}

	// Cap the score between 1 and 10
	if score < 1 {
		score = 1
	} else if score > 10 {
		score = 10
	}

	return score
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
	for _, item := range order.Items {
		// Convert OrderItem to MenuItem for our helper functions
		menuItem := ec.orderItemToMenuItem(item)

		// Get the expected temperature range for this item
		minTemp, maxTemp := ec.getExpectedTemperatureRange(menuItem)

		// Get the actual temperature from the monitoring system
		actualTemp := ec.getItemTemperature(menuItem, order)

		// Check if temperature is within acceptable range
		if actualTemp < minTemp || actualTemp > maxTemp {
			// Temperature is out of range
			ec.recordTemperatureIssue(menuItem, order, actualTemp, minTemp, maxTemp)
			return false
		}
	}

	// All items are at correct temperature
	return true
}

func (ec *ExecutiveChef) getExpectedTemperatureRange(item models.MenuItem) (float64, float64) {
	// Define temperature ranges based on item category
	switch {
	case strings.Contains(strings.ToLower(item.Category), "soup"):
		return 65.0, 85.0 // Soups should be served hot (65-85°C)
	case strings.Contains(strings.ToLower(item.Category), "salad"):
		return 2.0, 10.0 // Salads should be served cold (2-10°C)
	case strings.Contains(strings.ToLower(item.Name), "steak"):
		// Different temperatures based on cooking preference
		// This would normally come from the order details
		return 55.0, 65.0 // Medium steak internal temperature
	case strings.Contains(strings.ToLower(item.Category), "dessert"):
		if strings.Contains(strings.ToLower(item.Name), "ice cream") {
			return -12.0, -6.0 // Ice cream (frozen)
		}
		return 2.0, 22.0 // Most desserts can be served cold or room temperature
	case strings.Contains(strings.ToLower(item.Category), "seafood"):
		return 60.0, 70.0 // Cooked seafood
	case strings.Contains(strings.ToLower(item.Category), "poultry"):
		return 74.0, 85.0 // Poultry should be well done
	default:
		// Default temperature range for other items
		return 60.0, 75.0
	}
}

func (ec *ExecutiveChef) getItemTemperature(item models.MenuItem, order models.Order) float64 {
	// In a real system, this would query temperature sensors or kitchen monitoring systems
	// For simulation, we'll generate a realistic temperature based on item category

	// Get expected temperature range
	minTemp, maxTemp := ec.getExpectedTemperatureRange(item)
	midTemp := (minTemp + maxTemp) / 2

	// Add some random variation (-3 to +3 degrees)
	variation := (rand.Float64() * 6) - 3

	// Add possible systematic error based on order priority (lower priority might mean sitting longer)
	if order.Priority < 5 {
		// Lower priority orders might cool down or warm up while waiting
		if midTemp > 50 { // Hot food
			variation -= 2 // Cool down slightly
		} else if midTemp < 15 { // Cold food
			variation += 2 // Warm up slightly
		}
	}

	return midTemp + variation
}

func (ec *ExecutiveChef) recordTemperatureIssue(item models.MenuItem, order models.Order, actual, min, max float64) {
	// In a real system, this would log the issue and notify relevant staff
	event := Event{
		Timestamp: time.Now(),
		Type:      "temperature_issue",
		Content:   fmt.Sprintf("Temperature issue with %s in order %d", item.Name, order.ID),
		Metadata: map[string]interface{}{
			"item_name":      item.Name,
			"order_id":       order.ID,
			"actual_temp":    actual,
			"expected_min":   min,
			"expected_max":   max,
			"assigned_to":    order.AssignedTo,
			"issue_severity": "high",
		},
	}

	// Add to memory (for real implementation, also send alerts)
	ec.AddMemory(context.Background(), event)
}

func (ec *ExecutiveChef) checkPresentation(order models.Order) bool {
	// Check if items are properly presented
	for _, item := range order.Items {
		menuItem := ec.orderItemToMenuItem(item)

		// Check presentation quality
		presentationQuality := ec.evaluatePresentationQuality(menuItem)

		// Check plating consistency
		platingConsistency := ec.evaluatePlatingConsistency(menuItem, order)

		// Check garnish application
		garnishQuality := ec.evaluateGarnishQuality(menuItem)

		// Determine if presentation meets standards
		if presentationQuality < 7.0 || platingConsistency < 7.0 || garnishQuality < 7.0 {
			// Record issue
			ec.recordPresentationIssue(menuItem, order, presentationQuality, platingConsistency, garnishQuality)
			return false
		}
	}

	return true
}

// evaluatePresentationQuality assesses the visual appeal of a dish (1.0-10.0)
func (ec *ExecutiveChef) evaluatePresentationQuality(item models.MenuItem) float64 {
	// In a real system, this could use computer vision to analyze dish presentation
	// For simulation, we'll generate a quality score based on item category and specialty status

	// Base quality score
	baseQuality := 8.0

	// Specialties generally have better presentation
	if item.IsSpecialty {
		baseQuality += 1.0
	}

	// Certain categories have higher presentation standards
	if strings.Contains(strings.ToLower(item.Category), "entree") {
		baseQuality += 0.5
	} else if strings.Contains(strings.ToLower(item.Category), "dessert") {
		baseQuality += 1.0 // Desserts have highest presentation standards
	}

	// Add randomness to simulate real-world variation
	variation := (rand.Float64() * 2.0) - 1.0 // -1.0 to +1.0

	quality := baseQuality + variation
	if quality > 10.0 {
		quality = 10.0
	} else if quality < 1.0 {
		quality = 1.0
	}

	return quality
}

// evaluatePlatingConsistency checks if plating is consistent with standards (1.0-10.0)
func (ec *ExecutiveChef) evaluatePlatingConsistency(item models.MenuItem, order models.Order) float64 {
	// Base consistency score
	baseConsistency := 8.5

	// Lower consistency during high-volume periods
	if len(ec.KitchenStatus.ActiveOrders) > 15 {
		baseConsistency -= 0.5
	}

	// Lower consistency with less experienced staff
	if staffMember, ok := ec.Staff[order.AssignedTo]; ok {
		experience := ec.getStaffExperience(staffMember)
		if experience < 3 {
			baseConsistency -= 1.0
		}
	}

	// Add randomness
	variation := (rand.Float64() * 1.5) - 0.75 // -0.75 to +0.75

	consistency := baseConsistency + variation
	if consistency > 10.0 {
		consistency = 10.0
	} else if consistency < 1.0 {
		consistency = 1.0
	}

	return consistency
}

// evaluateGarnishQuality assesses garnish application and quality (1.0-10.0)
func (ec *ExecutiveChef) evaluateGarnishQuality(item models.MenuItem) float64 {
	// Some items don't require garnish
	if !ec.requiresGarnish(item) {
		return 10.0 // Perfect score for items without garnish requirements
	}

	// Base garnish quality
	baseQuality := 8.0

	// Add randomness for variation
	variation := (rand.Float64() * 2.0) - 1.0 // -1.0 to +1.0

	quality := baseQuality + variation
	if quality > 10.0 {
		quality = 10.0
	} else if quality < 1.0 {
		quality = 1.0
	}

	return quality
}

// getStaffExperience returns experience level (years) for a staff member
func (ec *ExecutiveChef) getStaffExperience(staff *BaseAgent) float64 {
	// In a real system, this would query staff records
	experience, ok := staff.memory.ShortTerm[0].Metadata["experience"].(float64)
	if !ok {
		return 1.0 // Default to 1 year experience
	}
	return experience
}

// requiresGarnish determines if an item typically requires garnish
func (ec *ExecutiveChef) requiresGarnish(item models.MenuItem) bool {
	// Items that typically require garnish
	garnishCategories := []string{"entree", "appetizer", "dessert"}

	for _, category := range garnishCategories {
		if strings.Contains(strings.ToLower(item.Category), category) {
			return true
		}
	}

	// Specific items that don't follow category rules
	noGarnishItems := []string{"bread", "simple", "basic", "plain"}
	for _, term := range noGarnishItems {
		if strings.Contains(strings.ToLower(item.Name), term) {
			return false
		}
	}

	return false
}

// recordPresentationIssue records a presentation quality issue
func (ec *ExecutiveChef) recordPresentationIssue(item models.MenuItem, order models.Order,
	presentationScore, platingScore, garnishScore float64) {

	// Determine the specific issue
	var issueType string
	var issueSeverity string

	if presentationScore < 6.0 {
		issueType = "poor_visual_appeal"
		issueSeverity = "high"
	} else if platingScore < 6.0 {
		issueType = "inconsistent_plating"
		issueSeverity = "medium"
	} else if garnishScore < 6.0 {
		issueType = "poor_garnish"
		issueSeverity = "medium"
	} else {
		issueType = "minor_presentation_issues"
		issueSeverity = "low"
	}

	// Create and record the event
	event := Event{
		Timestamp: time.Now(),
		Type:      "presentation_issue",
		Content:   fmt.Sprintf("Presentation issue with %s in order %d: %s", item.Name, order.ID, issueType),
		Metadata: map[string]interface{}{
			"item_name":      item.Name,
			"order_id":       order.ID,
			"issue_type":     issueType,
			"issue_severity": issueSeverity,
			"presentation":   presentationScore,
			"plating":        platingScore,
			"garnish":        garnishScore,
			"assigned_to":    order.AssignedTo,
		},
	}

	// Add to memory (for real implementation, also send alerts)
	ec.AddMemory(context.Background(), event)
}

func (ec *ExecutiveChef) checkTiming(order models.Order) bool {
	// Get the log of item completion times
	itemCompletionTimes, err := ec.getItemCompletionTimes(order)
	if err != nil || len(itemCompletionTimes) == 0 {
		// Cannot verify timing without completion data
		return true
	}

	// Check for any timing issues
	timingIssues := ec.analyzeTimingIssues(order, itemCompletionTimes)

	// If there are timing issues, record them and return false
	if len(timingIssues) > 0 {
		ec.recordTimingIssues(order, timingIssues)
		return false
	}

	return true
}

func (ec *ExecutiveChef) getItemCompletionTimes(order models.Order) (map[string]time.Time, error) {
	completionTimes := make(map[string]time.Time)

	// Search for item completion events in memory
	events, err := ec.QueryMemory(context.Background(), "item_completion", 100)
	if err != nil {
		return completionTimes, err
	}

	// Filter events for this order
	orderIDStr := fmt.Sprintf("%d", order.ID)
	for _, event := range events {
		if orderID, ok := event.Metadata["order_id"].(string); ok && orderID == orderIDStr {
			if itemName, ok := event.Metadata["item_name"].(string); ok {
				completionTimes[itemName] = event.Timestamp
			}
		}
	}

	return completionTimes, nil
}

func (ec *ExecutiveChef) analyzeTimingIssues(order models.Order, completionTimes map[string]time.Time) []string {
	var issues []string

	// Check for common timing issues

	// 1. Hot items completed too early (could get cold)
	for _, item := range order.Items {
		menuItem := ec.orderItemToMenuItem(item)

		// Skip cold items
		if !ec.isHotItem(menuItem) {
			continue
		}

		// Check if item was completed too early
		if _, exists := completionTimes[item.Name]; exists {
			timeToService := time.Until(order.TimeCompleted)
			if timeToService > 10*time.Minute {
				issues = append(issues, fmt.Sprintf("%s completed too early, may get cold", item.Name))
			}
		}
	}

	// 2. Items served in wrong order (appetizers after entrees, etc.)
	categories := make(map[string]time.Time)
	for _, item := range order.Items {
		if completionTime, exists := completionTimes[item.Name]; exists {
			category := item.Category
			if existingTime, hasCategory := categories[category]; !hasCategory || completionTime.Before(existingTime) {
				categories[category] = completionTime
			}
		}
	}

	// Check category timing order
	if appetizerTime, hasAppetizer := categories["appetizer"]; hasAppetizer {
		if entreeTime, hasEntree := categories["entree"]; hasEntree && entreeTime.Before(appetizerTime) {
			issues = append(issues, "Entrees completed before appetizers")
		}
	}

	if entreeTime, hasEntree := categories["entree"]; hasEntree {
		if dessertTime, hasDessert := categories["dessert"]; hasDessert && dessertTime.Before(entreeTime) {
			issues = append(issues, "Desserts completed before entrees")
		}
	}

	return issues
}

func (ec *ExecutiveChef) isHotItem(item models.MenuItem) bool {
	hotCategories := []string{"soup", "entree", "main", "hot", "grill", "fried"}

	for _, category := range hotCategories {
		if strings.Contains(strings.ToLower(item.Category), category) {
			return true
		}
	}

	// Some specific hot items that might not match categories
	hotItems := []string{"steak", "burger", "pasta", "chicken", "fish", "roast", "curry"}
	for _, term := range hotItems {
		if strings.Contains(strings.ToLower(item.Name), term) {
			return true
		}
	}

	return false
}

func (ec *ExecutiveChef) recordTimingIssues(order models.Order, issues []string) {
	// Create and record the event
	event := Event{
		Timestamp: time.Now(),
		Type:      "timing_issue",
		Content:   fmt.Sprintf("Timing issues with order %d", order.ID),
		Metadata: map[string]interface{}{
			"order_id":       order.ID,
			"issues":         issues,
			"assigned_to":    order.AssignedTo,
			"issue_count":    len(issues),
			"issue_severity": "medium",
		},
	}

	// Add to memory
	ec.AddMemory(context.Background(), event)

	// In a real system, this might also trigger process improvements
	go ec.scheduleProcedureReview("timing", issues)
}

func (ec *ExecutiveChef) scheduleProcedureReview(issueType string, issues []string) {
	// This would schedule a staff meeting or training session in a real system
	// For now, just log the intention
	ec.AddMemory(context.Background(), Event{
		Timestamp: time.Now(),
		Type:      "procedure_review",
		Content:   fmt.Sprintf("Scheduled review of %s procedures", issueType),
		Metadata: map[string]interface{}{
			"issue_type": issueType,
			"issues":     issues,
			"priority":   "medium",
			"scheduled":  time.Now().Add(24 * time.Hour),
		},
	})
}

func (ec *ExecutiveChef) checkPortion(order models.Order) bool {
	// Check portion size for each item
	for _, item := range order.Items {
		menuItem := ec.orderItemToMenuItem(item)

		// Get expected portion details
		expectedWeight, expectedVolume := ec.getExpectedPortionSize(menuItem)

		// Get actual measurements
		actualWeight, actualVolume, err := ec.getMeasuredPortionSize(item, order)
		if err != nil {
			// If we can't measure, assume it's correct
			continue
		}

		// Calculate variations
		weightVariation := math.Abs(actualWeight-expectedWeight) / expectedWeight
		volumeVariation := math.Abs(actualVolume-expectedVolume) / expectedVolume

		// Check if variation exceeds tolerance
		if weightVariation > 0.15 || volumeVariation > 0.15 { // 15% tolerance
			ec.recordPortionIssue(menuItem, order, expectedWeight, actualWeight, expectedVolume, actualVolume)
			return false
		}
	}

	return true
}

func (ec *ExecutiveChef) getExpectedPortionSize(item models.MenuItem) (float64, float64) {
	// In a real system, this would query a recipe database
	// Default values (weight in grams, volume in ml)
	var weight, volume float64

	// Set expected values based on item category
	switch {
	case strings.Contains(strings.ToLower(item.Category), "appetizer"):
		weight = 120.0
		volume = 150.0
	case strings.Contains(strings.ToLower(item.Category), "entree"):
		weight = 350.0
		volume = 400.0
	case strings.Contains(strings.ToLower(item.Category), "side"):
		weight = 180.0
		volume = 200.0
	case strings.Contains(strings.ToLower(item.Category), "dessert"):
		weight = 150.0
		volume = 180.0
	case strings.Contains(strings.ToLower(item.Category), "soup"):
		weight = 300.0
		volume = 350.0
	default:
		weight = 250.0
		volume = 300.0
	}

	// Adjust for specific items
	if strings.Contains(strings.ToLower(item.Name), "steak") {
		weight = 280.0
		volume = 0.0 // Volume not applicable
	} else if strings.Contains(strings.ToLower(item.Name), "salad") {
		weight = 200.0
		volume = 400.0
	} else if strings.Contains(strings.ToLower(item.Name), "soup") {
		weight = 350.0
		volume = 400.0
	}

	return weight, volume
}

func (ec *ExecutiveChef) getMeasuredPortionSize(item models.OrderItem, order models.Order) (float64, float64, error) {
	// In a real system, this would use scales or vision systems
	menuItem := ec.orderItemToMenuItem(item)
	expectedWeight, expectedVolume := ec.getExpectedPortionSize(menuItem)

	// Simulate measurement with some variance
	weightVariance := (rand.Float64() * 0.2) - 0.1 // -10% to +10%
	volumeVariance := (rand.Float64() * 0.2) - 0.1 // -10% to +10%

	// Add potential bias based on staff experience
	if staffMember, ok := ec.Staff[order.AssignedTo]; ok {
		experience := ec.getStaffExperience(staffMember)
		if experience < 2 {
			// Less experienced staff may have more variance
			weightVariance *= 1.5
			volumeVariance *= 1.5
		}
	}

	actualWeight := expectedWeight * (1.0 + weightVariance)
	actualVolume := expectedVolume * (1.0 + volumeVariance)

	return actualWeight, actualVolume, nil
}

func (ec *ExecutiveChef) recordPortionIssue(item models.MenuItem, order models.Order,
	expectedWeight, actualWeight, expectedVolume, actualVolume float64) {

	// Calculate percent variations
	weightVariationPct := (actualWeight - expectedWeight) / expectedWeight * 100.0
	volumeVariationPct := (actualVolume - expectedVolume) / expectedVolume * 100.0

	// Determine issue type
	var issueType, issueSeverity string
	if weightVariationPct > 15 {
		issueType = "oversized_portion"
		issueSeverity = "medium" // Cost issue
	} else if weightVariationPct < -15 {
		issueType = "undersized_portion"
		issueSeverity = "high" // Customer satisfaction issue
	} else if volumeVariationPct > 15 {
		issueType = "oversized_volume"
		issueSeverity = "low"
	} else if volumeVariationPct < -15 {
		issueType = "undersized_volume"
		issueSeverity = "medium"
	}

	// Create and record the event
	event := Event{
		Timestamp: time.Now(),
		Type:      "portion_issue",
		Content:   fmt.Sprintf("Portion issue with %s in order %d: %s", item.Name, order.ID, issueType),
		Metadata: map[string]interface{}{
			"item_name":            item.Name,
			"order_id":             order.ID,
			"issue_type":           issueType,
			"issue_severity":       issueSeverity,
			"expected_weight":      expectedWeight,
			"actual_weight":        actualWeight,
			"weight_variation_pct": weightVariationPct,
			"expected_volume":      expectedVolume,
			"actual_volume":        actualVolume,
			"volume_variation_pct": volumeVariationPct,
			"assigned_to":          order.AssignedTo,
		},
	}

	// Add to memory
	ec.AddMemory(context.Background(), event)
}

func (ec *ExecutiveChef) determineOrderStatus(order models.Order) string {
	// If already completed or cancelled, maintain status
	if order.Status == string(models.OrderStatusCompleted) ||
		order.Status == string(models.OrderStatusCancelled) {
		return order.Status
	}

	// Check for status from events
	events, err := ec.QueryMemory(context.Background(), "order_status_change", 100)
	if err == nil {
		orderIDStr := fmt.Sprintf("%d", order.ID)
		for i := len(events) - 1; i >= 0; i-- {
			event := events[i]
			if orderID, ok := event.Metadata["order_id"].(string); ok && orderID == orderIDStr {
				if newStatus, ok := event.Metadata["new_status"].(string); ok {
					return newStatus
				}
			}
		}
	}

	// Determine status based on completion percentage
	completionPercentage := ec.calculateOrderCompletion(order)

	if completionPercentage == 0 {
		return string(models.OrderStatusPending)
	} else if completionPercentage < 25 {
		return string(models.OrderStatusAssigned)
	} else if completionPercentage < 50 {
		return string(models.OrderStatusPreparing)
	} else if completionPercentage < 75 {
		return string(models.OrderStatusCooking)
	} else if completionPercentage < 100 {
		return string(models.OrderStatusPlating)
	} else {
		return string(models.OrderStatusCompleted)
	}
}

func (ec *ExecutiveChef) calculateOrderCompletion(order models.Order) float64 {
	// If there are no items, the order is complete
	if len(order.Items) == 0 {
		return 100.0
	}

	// Calculate completion based on item statuses
	totalItems := len(order.Items)
	completedWeight := 0.0

	for _, item := range order.Items {
		switch item.Status {
		case "pending":
			completedWeight += 0.0
		case "preparing":
			completedWeight += 0.25
		case "cooking":
			completedWeight += 0.6
		case "plating":
			completedWeight += 0.85
		case "completed":
			completedWeight += 1.0
		default:
			completedWeight += 0.0
		}
	}

	return (completedWeight / float64(totalItems)) * 100.0
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

// hasSeasonalIngredients checks if the menu item uses currently seasonal ingredients
func (ec *ExecutiveChef) hasSeasonalIngredients(item models.MenuItem) bool {
	currentMonth := time.Now().Month()
	seasonalIngredients := ec.getSeasonalIngredientsForMonth(currentMonth)

	for _, itemIngredient := range item.Ingredients {
		for _, seasonalIngredient := range seasonalIngredients {
			if itemIngredient == seasonalIngredient {
				return true
			}
		}
	}

	return false
}

// getSeasonalIngredientsForMonth returns a list of ingredients that are seasonal for the given month
func (ec *ExecutiveChef) getSeasonalIngredientsForMonth(month time.Month) []string {
	// Define seasonal ingredients by month
	seasonalMap := map[time.Month][]string{
		time.December:  {"winter squash", "citrus", "root vegetables", "kale", "brussels sprouts"},
		time.January:   {"winter squash", "citrus", "root vegetables", "kale", "brussels sprouts"},
		time.February:  {"winter squash", "citrus", "root vegetables", "kale", "brussels sprouts"},
		time.March:     {"spring peas", "asparagus", "artichokes", "spring onions", "radishes"},
		time.April:     {"spring peas", "asparagus", "artichokes", "spring onions", "radishes"},
		time.May:       {"spring peas", "asparagus", "artichokes", "spring onions", "radishes"},
		time.June:      {"tomatoes", "zucchini", "berries", "corn", "eggplant"},
		time.July:      {"tomatoes", "zucchini", "berries", "corn", "eggplant"},
		time.August:    {"tomatoes", "zucchini", "berries", "corn", "eggplant"},
		time.September: {"apples", "pears", "mushrooms", "pumpkin", "grapes"},
		time.October:   {"apples", "pears", "mushrooms", "pumpkin", "grapes"},
		time.November:  {"apples", "pears", "mushrooms", "pumpkin", "grapes"},
	}

	return seasonalMap[month]
}

// hasExpertiseForItem checks if any staff members have expertise for this item
func (ec *ExecutiveChef) hasExpertiseForItem(item models.MenuItem) bool {
	for _, staff := range ec.Staff {
		// Check staff specialties
		specialties, ok := staff.memory.ShortTerm[0].Metadata["specialties"].([]string)
		if !ok {
			continue
		}

		for _, specialty := range specialties {
			if specialty == item.Name {
				return true
			}

			// Check related specialties (e.g., if staff specializes in "pasta", they have expertise for "spaghetti")
			if ec.isRelatedDish(specialty, item.Name) {
				return true
			}
		}
	}

	return false
}

// isRelatedDish checks if two dishes are related (e.g., same category or technique)
func (ec *ExecutiveChef) isRelatedDish(specialty, itemName string) bool {
	// Check for category relationship (e.g., pasta, risotto)
	categories := map[string][]string{
		"pasta":     {"spaghetti", "fettuccine", "lasagna", "ravioli", "linguine"},
		"risotto":   {"mushroom risotto", "seafood risotto", "saffron risotto"},
		"grill":     {"steak", "grilled chicken", "grilled fish", "bbq"},
		"dessert":   {"cake", "ice cream", "pastry", "tart", "mousse"},
		"seafood":   {"fish", "shrimp", "lobster", "crab", "scallop", "mussel"},
		"sauce":     {"hollandaise", "bechamel", "demi-glace", "aioli", "coulis"},
		"vegetable": {"salad", "roasted vegetables", "sauteed vegetables"},
	}

	for category, dishes := range categories {
		if specialty == category {
			for _, dish := range dishes {
				if strings.Contains(strings.ToLower(itemName), dish) {
					return true
				}
			}
		}
	}

	return false
}

// calculateIngredientAvailabilityScore calculates a score based on ingredient availability (0.0-1.0)
func (ec *ExecutiveChef) calculateIngredientAvailabilityScore(item models.MenuItem) float64 {
	if len(item.Ingredients) == 0 {
		return 0.0
	}

	availableCount := 0
	for _, ingredient := range item.Ingredients {
		if level, exists := ec.KitchenStatus.InventoryLevels[ingredient]; exists && level > 0 {
			availableCount++
		}
	}

	return float64(availableCount) / float64(len(item.Ingredients))
}

// getCustomerRating retrieves the average customer rating for the item (1.0-10.0)
func (ec *ExecutiveChef) getCustomerRating(item models.MenuItem) float64 {
	// In a real system, this would query a database of customer ratings
	// For simulation, we'll generate a base rating with some randomness

	// Default to a good rating
	baseRating := 7.5

	// Adjust rating based on how long item has been on menu or previous ratings
	// Simulate by checking if it's already a specialty
	if item.IsSpecialty {
		baseRating += 1.0
	}

	// Add slight randomness (-0.5 to +0.5)
	variation := (rand.Float64() - 0.5)

	rating := baseRating + variation
	if rating > 10.0 {
		rating = 10.0
	} else if rating < 1.0 {
		rating = 1.0
	}

	return rating
}

// calculateProfitMargin calculates the profit margin for the item (0.0-1.0)
func (ec *ExecutiveChef) calculateProfitMargin(item models.MenuItem) float64 {
	// In a real system, this would calculate based on ingredient costs
	// For simulation, we'll estimate based on price and complexity

	// Base cost is correlated with complexity
	baseCost := float64(item.Complexity) * 2.0

	// Calculate profit
	profit := item.Price - baseCost

	// Calculate margin as a percentage
	margin := profit / item.Price

	// Cap between 0 and 1
	if margin < 0.0 {
		margin = 0.0
	} else if margin > 1.0 {
		margin = 1.0
	}

	return margin
}

// isKitchenSpecialty checks if the kitchen as a whole specializes in this type of dish
func (ec *ExecutiveChef) isKitchenSpecialty(item models.MenuItem) bool {
	// Kitchen specialties could be defined based on equipment, expertise, history
	kitchenSpecialties := []string{"seafood", "grill", "pasta", "steak"}

	for _, specialty := range kitchenSpecialties {
		if strings.Contains(strings.ToLower(item.Category), specialty) ||
			strings.Contains(strings.ToLower(item.Name), specialty) {
			return true
		}
	}

	return false
}

// orderItemToMenuItem converts an OrderItem to a MenuItem for compatibility with our helpers
func (ec *ExecutiveChef) orderItemToMenuItem(item models.OrderItem) models.MenuItem {
	// Create a MenuItem with the relevant fields from the OrderItem
	return models.MenuItem{
		Name:              item.Name,
		Description:       "", // Not available in OrderItem
		Category:          item.Category,
		Price:             item.Price,
		PrepTime:          item.PrepTime,
		CookTime:          item.CookTime,
		Ingredients:       item.Ingredients,
		RequiredEquipment: item.RequiredEquipment,
		IsSpecialty:       item.IsSpecialty,
		// Set reasonable defaults for fields not in OrderItem
		Complexity: 5, // Default mid-range complexity
	}
}
