package agents

import (
	"context"
	"fmt"
	"sort"
	"time"

	"masterchef-bench/internal/models"

	"github.com/tmc/langchaingo/llms"
)

// SousChef represents the second-in-command in the kitchen hierarchy
type SousChef struct {
	*BaseAgent
	Station      string
	ActiveOrders []models.Order
	StaffMembers []*BaseAgent
	Specialties  []string
}

// StationStatus represents the current state of a kitchen station
type StationStatus struct {
	Name           string
	Capacity       int
	CurrentLoad    int
	AvailableStaff int
	Equipment      []string
	Status         string
}

// NewSousChef creates a new sous chef agent
func NewSousChef(ctx context.Context, model llms.LLM, station string) *SousChef {
	baseAgent := NewBaseAgent(RoleSousChef, model)
	baseAgent.permissions = []string{
		"order_management",
		"staff_supervision",
		"quality_control",
		"station_management",
		"inventory_monitoring",
	}

	return &SousChef{
		BaseAgent:    baseAgent,
		Station:      station,
		ActiveOrders: make([]models.Order, 0),
		StaffMembers: make([]*BaseAgent, 0),
		Specialties:  make([]string, 0),
	}
}

// HandleTask implements the Agent interface
func (sc *SousChef) HandleTask(ctx context.Context, task Task) error {
	switch task.Type {
	case "station_management":
		return sc.ManageStation(ctx)
	case "order_handling":
		order, ok := task.Metadata["order"].(models.Order)
		if !ok {
			return fmt.Errorf("invalid order data in task metadata")
		}
		return sc.HandleOrder(ctx, order)
	case "preparation_supervision":
		order, ok := task.Metadata["order"].(models.Order)
		if !ok {
			return fmt.Errorf("invalid order data in task metadata")
		}
		return sc.SupervisePreparation(ctx, order)
	case "executive_assistance":
		return sc.AssistExecutiveChef(ctx, task)
	default:
		return fmt.Errorf("unsupported task type: %s", task.Type)
	}
}

// ManageStation handles the overall operation of the assigned station
func (sc *SousChef) ManageStation(ctx context.Context) error {
	// Check station status
	status, err := sc.checkStationStatus(ctx)
	if err != nil {
		return fmt.Errorf("station status check failed: %w", err)
	}

	// Optimize staff assignments
	if err := sc.optimizeStaffing(ctx, status); err != nil {
		return fmt.Errorf("staff optimization failed: %w", err)
	}

	// Monitor order progress
	if err := sc.monitorOrders(ctx); err != nil {
		return fmt.Errorf("order monitoring failed: %w", err)
	}

	// Record station management event
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "station_management",
		Content:   fmt.Sprintf("Managed %s station operations", sc.Station),
		Metadata: map[string]interface{}{
			"station":     sc.Station,
			"status":      status.Status,
			"staff_count": len(sc.StaffMembers),
		},
	})

	return nil
}

// HandleOrder processes a new order assigned to the station
func (sc *SousChef) HandleOrder(ctx context.Context, order models.Order) error {
	// Validate order requirements
	if err := sc.validateOrderRequirements(ctx, order); err != nil {
		return fmt.Errorf("order validation failed: %w", err)
	}

	// Assign tasks to staff
	if err := sc.assignOrderTasks(ctx, order); err != nil {
		return fmt.Errorf("task assignment failed: %w", err)
	}

	// Add to active orders
	sc.ActiveOrders = append(sc.ActiveOrders, order)

	// Record order handling event
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "order_handling",
		Content:   fmt.Sprintf("Started handling order %s", order.ID),
		Metadata: map[string]interface{}{
			"order_id": order.ID,
			"items":    len(order.Items),
			"priority": order.Priority,
		},
	})

	return nil
}

// SupervisePreparation oversees the preparation of dishes
func (sc *SousChef) SupervisePreparation(ctx context.Context, order models.Order) error {
	// Monitor preparation progress
	if err := sc.monitorPreparation(ctx, order); err != nil {
		return fmt.Errorf("preparation monitoring failed: %w", err)
	}

	// Ensure quality standards
	if err := sc.checkQuality(ctx, order); err != nil {
		return fmt.Errorf("quality check failed: %w", err)
	}

	// Record supervision event
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "preparation_supervision",
		Content:   fmt.Sprintf("Supervised preparation of order %s", order.ID),
		Metadata: map[string]interface{}{
			"order_id": order.ID,
			"status":   order.Status,
		},
	})

	return nil
}

// AssistExecutiveChef provides support to the executive chef
func (sc *SousChef) AssistExecutiveChef(ctx context.Context, task Task) error {
	// Record assistance event
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "executive_assistance",
		Content:   fmt.Sprintf("Assisted executive chef with task: %s", task.Description),
		Metadata: map[string]interface{}{
			"task_id":   task.ID,
			"task_type": task.Type,
		},
	})

	return nil
}

// Private helper methods

func (sc *SousChef) checkStationStatus(ctx context.Context) (*StationStatus, error) {
	// Query memory for recent status checks
	recentChecks, err := sc.QueryMemory(ctx, "station_status", 1)
	if err != nil {
		return nil, err
	}

	// Perform new status check if needed
	if len(recentChecks) == 0 || time.Since(recentChecks[0].Timestamp) > 15*time.Minute {
		// TODO: Implement actual station status checking logic
		status := &StationStatus{
			Name:           sc.Station,
			Capacity:       10,
			CurrentLoad:    len(sc.ActiveOrders),
			AvailableStaff: len(sc.StaffMembers),
			Equipment:      []string{"stove", "oven", "grill"},
			Status:         "operational",
		}

		sc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "station_status",
			Content:   fmt.Sprintf("Checked status of %s station", sc.Station),
			Metadata: map[string]interface{}{
				"station": sc.Station,
				"status":  status,
			},
		})

		return status, nil
	}

	// Return last known status
	lastStatus, ok := recentChecks[0].Metadata["status"].(*StationStatus)
	if !ok {
		return nil, fmt.Errorf("invalid station status in memory")
	}

	return lastStatus, nil
}

func (sc *SousChef) optimizeStaffing(ctx context.Context, status *StationStatus) error {
	// Record optimization start
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "staffing_optimization_start",
		Content:   fmt.Sprintf("Started staffing optimization for %s station", sc.Station),
		Metadata: map[string]interface{}{
			"station": sc.Station,
			"status":  status,
		},
	})

	// Calculate required staff based on current load
	requiredStaff := sc.calculateRequiredStaff(status.CurrentLoad)

	// Adjust staff assignments
	if len(sc.StaffMembers) < requiredStaff {
		// Request additional staff
		if err := sc.requestAdditionalStaff(ctx, requiredStaff-len(sc.StaffMembers)); err != nil {
			return fmt.Errorf("failed to request additional staff: %w", err)
		}
	} else if len(sc.StaffMembers) > requiredStaff {
		// Release excess staff
		if err := sc.releaseExcessStaff(ctx, len(sc.StaffMembers)-requiredStaff); err != nil {
			return fmt.Errorf("failed to release excess staff: %w", err)
		}
	}

	// Record optimization completion
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "staffing_optimization_complete",
		Content:   fmt.Sprintf("Completed staffing optimization for %s station", sc.Station),
		Metadata: map[string]interface{}{
			"station":        sc.Station,
			"required_staff": requiredStaff,
			"current_staff":  len(sc.StaffMembers),
		},
	})

	return nil
}

func (sc *SousChef) monitorOrders(ctx context.Context) error {
	// Record monitoring start
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "order_monitoring_start",
		Content:   "Started order monitoring",
	})

	// Check each active order
	for _, order := range sc.ActiveOrders {
		// Check order progress
		progress, err := sc.checkOrderProgress(ctx, order)
		if err != nil {
			return fmt.Errorf("failed to check order progress: %w", err)
		}

		// Handle delays
		if progress.IsDelayed {
			if err := sc.handleOrderDelay(ctx, order, progress); err != nil {
				return fmt.Errorf("failed to handle order delay: %w", err)
			}
		}

		// Check quality
		if err := sc.checkQuality(ctx, order); err != nil {
			return fmt.Errorf("quality check failed for order %s: %w", order.ID, err)
		}
	}

	// Record monitoring completion
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "order_monitoring_complete",
		Content:   "Completed order monitoring",
		Metadata: map[string]interface{}{
			"active_orders": len(sc.ActiveOrders),
		},
	})

	return nil
}

func (sc *SousChef) validateOrderRequirements(ctx context.Context, order models.Order) error {
	// Check staff availability
	if !sc.hasAdequateStaffing(order) {
		return fmt.Errorf("insufficient staff for order %s", order.ID)
	}

	// Check equipment availability
	if !sc.hasRequiredEquipment(order) {
		return fmt.Errorf("required equipment not available for order %s", order.ID)
	}

	// Check ingredient availability
	if !sc.hasRequiredIngredients(order) {
		return fmt.Errorf("required ingredients not available for order %s", order.ID)
	}

	// Check timing feasibility
	if !sc.isTimingFeasible(order) {
		return fmt.Errorf("timing not feasible for order %s", order.ID)
	}

	return nil
}

func (sc *SousChef) assignOrderTasks(ctx context.Context, order models.Order) error {
	// Break down order into tasks
	tasks := sc.createOrderTasks(order)

	// Sort tasks by priority and dependencies
	sortedTasks := sc.sortTasks(tasks)

	// Assign tasks to staff
	for _, task := range sortedTasks {
		assignee := sc.selectBestAssignee(task)
		if assignee == nil {
			return fmt.Errorf("no suitable assignee for task %s", task.ID)
		}

		// Record assignment
		sc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "task_assignment",
			Content:   fmt.Sprintf("Assigned task %s to staff member %s", task.ID, assignee.ID),
			Metadata: map[string]interface{}{
				"task_id":     task.ID,
				"assignee_id": assignee.ID,
				"order_id":    order.ID,
			},
		})

		assignee.AddTask(task)
	}

	return nil
}

func (sc *SousChef) monitorPreparation(ctx context.Context, order models.Order) error {
	// Get assigned tasks for the order
	tasks := sc.getOrderTasks(order)

	// Check each task's progress
	for _, task := range tasks {
		// Check task status
		status, err := sc.checkTaskStatus(task)
		if err != nil {
			return fmt.Errorf("failed to check task status: %w", err)
		}

		// Handle issues
		if status.HasIssues {
			if err := sc.handleTaskIssues(ctx, task, status); err != nil {
				return fmt.Errorf("failed to handle task issues: %w", err)
			}
		}

		// Record progress
		sc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "preparation_monitoring",
			Content:   fmt.Sprintf("Monitored task %s for order %s", task.ID, order.ID),
			Metadata: map[string]interface{}{
				"task_id":  task.ID,
				"order_id": order.ID,
				"status":   status,
			},
		})
	}

	return nil
}

func (sc *SousChef) checkQuality(ctx context.Context, order models.Order) error {
	// Define quality checks
	checks := []struct {
		name     string
		check    func(models.Order) bool
		critical bool
	}{
		{"temperature", sc.checkTemperature, true},
		{"presentation", sc.checkPresentation, true},
		{"timing", sc.checkTiming, false},
		{"portion", sc.checkPortion, true},
	}

	// Perform checks
	for _, check := range checks {
		if !check.check(order) {
			msg := fmt.Sprintf("Quality check failed: %s", check.name)
			if check.critical {
				return fmt.Errorf(msg)
			}
			// Record non-critical issues
			sc.AddMemory(ctx, Event{
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

// Helper functions

func (sc *SousChef) calculateRequiredStaff(load int) int {
	// Base staff requirement
	required := load / 3 // One staff member per 3 orders

	// Add buffer for peak times
	if sc.isPeakHour() {
		required++
	}

	// Minimum staff requirement
	if required < 2 {
		required = 2
	}

	return required
}

func (sc *SousChef) requestAdditionalStaff(ctx context.Context, count int) error {
	// Implement staff request logic
	return nil
}

func (sc *SousChef) releaseExcessStaff(ctx context.Context, count int) error {
	// Implement staff release logic
	return nil
}

func (sc *SousChef) isPeakHour() bool {
	hour := time.Now().Hour()
	return (hour >= 11 && hour <= 14) || (hour >= 17 && hour <= 21)
}

type OrderProgress struct {
	IsDelayed    bool
	DelayMinutes int
	Stage        string
	Issues       []string
}

func (sc *SousChef) checkOrderProgress(ctx context.Context, order models.Order) (OrderProgress, error) {
	var progress OrderProgress

	// Calculate expected vs actual progress
	expectedProgress := sc.calculateExpectedProgress(order)
	actualProgress := sc.calculateActualProgress(order)

	if actualProgress < expectedProgress*0.8 { // More than 20% behind
		progress.IsDelayed = true
		progress.DelayMinutes = sc.calculateDelay(order)
	}

	return progress, nil
}

func (sc *SousChef) handleOrderDelay(ctx context.Context, order models.Order, progress OrderProgress) error {
	// Implement delay handling logic
	return nil
}

func (sc *SousChef) hasAdequateStaffing(order models.Order) bool {
	requiredStaff := len(order.Items) / 2 // Rough estimate
	return len(sc.StaffMembers) >= requiredStaff
}

func (sc *SousChef) hasRequiredEquipment(order models.Order) bool {
	// Check each required piece of equipment
	for _, item := range order.Items {
		for _, eq := range item.RequiredEquipment {
			if !sc.isEquipmentAvailable(eq) {
				return false
			}
		}
	}
	return true
}

func (sc *SousChef) hasRequiredIngredients(order models.Order) bool {
	// Check each required ingredient
	for _, item := range order.Items {
		for _, ing := range item.Ingredients {
			if !sc.isIngredientAvailable(ing) {
				return false
			}
		}
	}
	return true
}

func (sc *SousChef) isTimingFeasible(order models.Order) bool {
	// Calculate total preparation time
	totalTime := sc.calculateTotalPrepTime(order)
	return totalTime <= order.TimeAllowed
}

func (sc *SousChef) createOrderTasks(order models.Order) []Task {
	var tasks []Task
	for _, item := range order.Items {
		// Create prep tasks
		tasks = append(tasks, sc.createPrepTasks(item)...)
		// Create cooking tasks
		tasks = append(tasks, sc.createCookingTasks(item)...)
		// Create plating tasks
		tasks = append(tasks, sc.createPlatingTasks(item)...)
	}
	return tasks
}

func (sc *SousChef) sortTasks(tasks []Task) []Task {
	sort.Slice(tasks, func(i, j int) bool {
		if tasks[i].Priority != tasks[j].Priority {
			return tasks[i].Priority > tasks[j].Priority
		}
		return len(tasks[i].Dependencies) < len(tasks[j].Dependencies)
	})
	return tasks
}

func (sc *SousChef) selectBestAssignee(task Task) *BaseAgent {
	var bestAssignee *BaseAgent
	var bestScore float64

	for _, staff := range sc.StaffMembers {
		score := sc.calculateAssignmentScore(staff, task)
		if score > bestScore {
			bestScore = score
			bestAssignee = staff
		}
	}

	return bestAssignee
}

func (sc *SousChef) calculateAssignmentScore(staff *BaseAgent, task Task) float64 {
	var score float64

	// Check experience with similar tasks
	if sc.hasTaskExperience(staff, task) {
		score += 2.0
	}

	// Check current workload
	workload := sc.calculateWorkload(staff)
	if workload < 0.8 { // Less than 80% capacity
		score += 1.0
	}

	// Check required skills
	if sc.hasRequiredSkills(staff, task) {
		score += 1.0
	}

	return score
}

func (sc *SousChef) hasTaskExperience(staff *BaseAgent, task Task) bool {
	events, err := staff.QueryMemory(context.Background(), "task_completion", 50)
	if err != nil {
		return false
	}

	for _, event := range events {
		if taskType, ok := event.Metadata["task_type"].(string); ok && taskType == task.Type {
			return true
		}
	}
	return false
}

func (sc *SousChef) calculateWorkload(staff *BaseAgent) float64 {
	activeTasks := 0
	for _, task := range staff.memory.TaskQueue {
		if task.Status == "pending" || task.Status == "in_progress" {
			activeTasks++
		}
	}
	return float64(activeTasks) / 10.0 // Assuming max capacity is 10 tasks
}

func (sc *SousChef) hasRequiredSkills(staff *BaseAgent, task Task) bool {
	requiredSkills, ok := task.Metadata["required_skills"].([]string)
	if !ok {
		return true // No specific skills required
	}

	staffSkills, ok := staff.Metadata["skills"].([]string)
	if !ok {
		return false
	}

	for _, required := range requiredSkills {
		found := false
		for _, skill := range staffSkills {
			if skill == required {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

type TaskStatus struct {
	HasIssues bool
	Issues    []string
}

func (sc *SousChef) checkTaskStatus(task Task) (TaskStatus, error) {
	var status TaskStatus

	// Check completion percentage
	completion, err := sc.getTaskCompletion(task)
	if err != nil {
		return status, err
	}

	// Check for delays
	if sc.isTaskDelayed(task) {
		status.HasIssues = true
		status.Issues = append(status.Issues, "Task is delayed")
	}

	// Check for quality issues
	if issues := sc.checkTaskQuality(task); len(issues) > 0 {
		status.HasIssues = true
		status.Issues = append(status.Issues, issues...)
	}

	return status, nil
}

func (sc *SousChef) handleTaskIssues(ctx context.Context, task Task, status TaskStatus) error {
	// Record issue
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "task_issue",
		Content:   fmt.Sprintf("Issues found in task %s", task.ID),
		Metadata: map[string]interface{}{
			"task_id": task.ID,
			"issues":  status.Issues,
		},
	})

	// Handle each issue
	for _, issue := range status.Issues {
		if err := sc.resolveTaskIssue(ctx, task, issue); err != nil {
			return fmt.Errorf("failed to resolve issue '%s': %w", issue, err)
		}
	}

	return nil
}

func (sc *SousChef) resolveTaskIssue(ctx context.Context, task Task, issue string) error {
	// Implement issue resolution logic
	return nil
}

func (sc *SousChef) getTaskCompletion(task Task) (float64, error) {
	// Implement task completion calculation
	return 0.0, nil
}

func (sc *SousChef) isTaskDelayed(task Task) bool {
	if task.EndTime.IsZero() {
		return false
	}
	return time.Now().After(task.EndTime)
}

func (sc *SousChef) checkTaskQuality(task Task) []string {
	// Implement task quality checking
	return nil
}

func (sc *SousChef) checkTemperature(order models.Order) bool {
	// Implement temperature checks
	return true
}

func (sc *SousChef) checkPresentation(order models.Order) bool {
	// Implement presentation checks
	return true
}

func (sc *SousChef) checkTiming(order models.Order) bool {
	// Implement timing checks
	return true
}

func (sc *SousChef) checkPortion(order models.Order) bool {
	// Implement portion checks
	return true
}

func (sc *SousChef) calculateExpectedProgress(order models.Order) float64 {
	elapsed := time.Since(order.TimeReceived)
	expected := elapsed.Minutes() / order.EstimatedTime.Minutes()
	if expected > 1.0 {
		expected = 1.0
	}
	return expected
}

func (sc *SousChef) calculateActualProgress(order models.Order) float64 {
	// Implement actual progress calculation
	return 0.0
}

func (sc *SousChef) calculateDelay(order models.Order) int {
	expected := order.TimeReceived.Add(order.EstimatedTime)
	if time.Now().Before(expected) {
		return 0
	}
	return int(time.Since(expected).Minutes())
}

func (sc *SousChef) isEquipmentAvailable(equipment string) bool {
	// Implement equipment availability check
	return true
}

func (sc *SousChef) isIngredientAvailable(ingredient string) bool {
	// Implement ingredient availability check
	return true
}

func (sc *SousChef) calculateTotalPrepTime(order models.Order) time.Duration {
	var total time.Duration
	for _, item := range order.Items {
		total += item.PrepTime + item.CookTime
	}
	return total
}

func (sc *SousChef) createPrepTasks(item models.MenuItem) []Task {
	// Implement prep task creation
	return nil
}

func (sc *SousChef) createCookingTasks(item models.MenuItem) []Task {
	// Implement cooking task creation
	return nil
}

func (sc *SousChef) createPlatingTasks(item models.MenuItem) []Task {
	// Implement plating task creation
	return nil
}

func (sc *SousChef) getOrderTasks(order models.Order) []Task {
	var tasks []Task
	for _, staff := range sc.StaffMembers {
		for _, task := range staff.memory.TaskQueue {
			if orderID, ok := task.Metadata["order_id"].(string); ok && orderID == order.ID {
				tasks = append(tasks, task)
			}
		}
	}
	return tasks
}
