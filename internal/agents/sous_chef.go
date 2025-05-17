package agents

import (
	"context"
	"fmt"
	"math/rand"
	"sort"
	"strings"
	"time"

	"masterchef/internal/models"

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
		Content:   fmt.Sprintf("Started handling order %d", order.ID),
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
		Content:   fmt.Sprintf("Supervised preparation of order %d", order.ID),
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
		// Gather station information from various sources
		// 1. Check equipment status
		equipmentStatus := make(map[string]string)
		equipmentList := []string{"stove", "oven", "grill", "fryer", "mixer"}

		for _, eq := range equipmentList {
			// In a real system, this would query equipment sensors or status API
			status := "operational"
			if rand.Float64() < 0.05 { // 5% chance of maintenance needed
				status = "needs_maintenance"
			} else if rand.Float64() < 0.02 { // 2% chance of being out of service
				status = "out_of_service"
			}
			equipmentStatus[eq] = status
		}

		// 2. Analyze current workload
		currentLoad := len(sc.ActiveOrders)

		// 3. Check staff availability and skills
		availableStaff := 0
		for _, staff := range sc.StaffMembers {
			if sc.calculateWorkload(staff) < 0.8 { // Staff member has capacity
				availableStaff++
			}
		}

		// 4. Determine overall station status
		stationStatus := "operational"
		if currentLoad > 15 {
			stationStatus = "high_capacity"
		} else if currentLoad < 3 {
			stationStatus = "low_capacity"
		}

		// Check for critical equipment issues
		criticalEquipment := 0
		for _, status := range equipmentStatus {
			if status == "out_of_service" {
				criticalEquipment++
			}
		}

		if criticalEquipment > 1 {
			stationStatus = "limited_capacity"
		}

		if availableStaff < 2 {
			stationStatus = "understaffed"
		}

		// 5. Create equipment list that is operational
		operationalEquipment := []string{}
		for eq, status := range equipmentStatus {
			if status == "operational" {
				operationalEquipment = append(operationalEquipment, eq)
			}
		}

		// Create and return the status
		status := &StationStatus{
			Name:           sc.Station,
			Capacity:       10,
			CurrentLoad:    currentLoad,
			AvailableStaff: availableStaff,
			Equipment:      operationalEquipment,
			Status:         stationStatus,
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
			return fmt.Errorf("quality check failed for order %d: %w", order.ID, err)
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
		return fmt.Errorf("insufficient staff for order %d", order.ID)
	}

	// Check equipment availability
	if !sc.hasRequiredEquipment(order) {
		return fmt.Errorf("required equipment not available for order %d", order.ID)
	}

	// Check ingredient availability
	if !sc.hasRequiredIngredients(order) {
		return fmt.Errorf("required ingredients not available for order %d", order.ID)
	}

	// Check timing feasibility
	if !sc.isTimingFeasible(order) {
		return fmt.Errorf("timing not feasible for order %d", order.ID)
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
			Content:   fmt.Sprintf("Assigned task %s to staff member %d", task.ID, assignee.ID),
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
			Content:   fmt.Sprintf("Monitored task %s for order %d", task.ID, order.ID),
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
	// Record staff request
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "staff_request",
		Content:   fmt.Sprintf("Requested %d additional staff members", count),
		Metadata: map[string]interface{}{
			"count":   count,
			"station": sc.Station,
		},
	})

	// Implement actual staff request logic through HR system
	hr := &HRSystem{
		RequestID:   fmt.Sprintf("staff_req_%d", time.Now().Unix()),
		RequestType: "additional_staff",
		Station:     sc.Station,
		Quantity:    count,
		Urgency:     sc.calculateStaffingUrgency(),
		Skills:      sc.getRequiredSkills(),
	}

	// Send the request to HR system
	if err := hr.SubmitStaffRequest(ctx); err != nil {
		return fmt.Errorf("failed to submit staff request: %w", err)
	}

	// Set a timer to follow up if no response
	go func() {
		timer := time.NewTimer(30 * time.Minute)
		<-timer.C

		// Check if request is still pending
		status, err := hr.CheckRequestStatus(ctx)
		if err != nil || status == "pending" {
			// Follow up on request
			hr.EscalateRequest(ctx)

			// Record follow-up
			sc.AddMemory(ctx, Event{
				Timestamp: time.Now(),
				Type:      "staff_request_followup",
				Content:   fmt.Sprintf("Followed up on staff request for %d members", count),
				Metadata: map[string]interface{}{
					"request_id": hr.RequestID,
					"station":    sc.Station,
				},
			})
		}
	}()

	return nil
}

func (sc *SousChef) releaseExcessStaff(ctx context.Context, count int) error {
	// Record staff release
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "staff_release",
		Content:   fmt.Sprintf("Released %d staff members", count),
		Metadata: map[string]interface{}{
			"count":   count,
			"station": sc.Station,
		},
	})

	// Implement actual staff release logic through HR system
	if count <= 0 {
		return nil // No staff to release
	}

	// Identify staff members that can be released based on workload and priority
	staffToRelease := sc.identifyStaffForRelease(count)
	if len(staffToRelease) == 0 {
		return fmt.Errorf("unable to identify staff members for release")
	}

	// Create HR system release request
	hr := &HRSystem{
		RequestID:   fmt.Sprintf("staff_rel_%d", time.Now().Unix()),
		RequestType: "release_staff",
		Station:     sc.Station,
		Quantity:    len(staffToRelease),
		StaffIDs:    staffToRelease,
	}

	// Ensure tasks are reassigned before releasing staff
	if err := sc.reassignTasksFromReleasedStaff(ctx, staffToRelease); err != nil {
		return fmt.Errorf("failed to reassign tasks: %w", err)
	}

	// Send the release request to HR system
	if err := hr.SubmitStaffRelease(ctx); err != nil {
		return fmt.Errorf("failed to submit staff release request: %w", err)
	}

	// Remove released staff from local roster
	sc.removeReleasedStaffFromRoster(staffToRelease)

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
	// Record delay
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "order_delay",
		Content:   fmt.Sprintf("Order %d is delayed by %d minutes", order.ID, progress.DelayMinutes),
		Metadata: map[string]interface{}{
			"order_id":      order.ID,
			"delay_minutes": progress.DelayMinutes,
			"stage":         progress.Stage,
			"issues":        progress.Issues,
		},
	})

	// Increase priority
	order.Priority++

	// Reassign if necessary
	if order.Priority > 8 {
		newAssignee := sc.selectBestAssignee(Task{
			ID:          fmt.Sprintf("%d", order.ID),
			Type:        "order_recovery",
			Description: "Recover delayed order",
			Priority:    order.Priority,
			Metadata: map[string]interface{}{
				"order_id": order.ID,
			},
		})
		if newAssignee != nil {
			order.AssignedTo = fmt.Sprintf("%d", newAssignee.ID)
		}
	}

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
	expectedTime := order.TimeReceived.Add(totalTime)
	return time.Now().Before(expectedTime)
}

func (sc *SousChef) createOrderTasks(order models.Order) []Task {
	var tasks []Task
	for _, item := range order.Items {
		// Create prep tasks
		prepTasks := sc.createPrepTasks(item)
		tasks = append(tasks, prepTasks...)

		// Create cooking tasks
		cookingTasks := sc.createCookingTasks(item)
		tasks = append(tasks, cookingTasks...)

		// Create plating tasks
		platingTasks := sc.createPlatingTasks(item)
		tasks = append(tasks, platingTasks...)
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

	staffSkills, ok := staff.memory.ShortTerm[0].Metadata["skills"].([]string)
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
	// Record issue resolution attempt
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "issue_resolution",
		Content:   fmt.Sprintf("Attempting to resolve issue '%s' for task %s", issue, task.ID),
		Metadata: map[string]interface{}{
			"task_id": task.ID,
			"issue":   issue,
		},
	})

	// Handle different types of issues
	switch {
	case strings.Contains(issue, "delay"):
		return sc.handleTaskDelay(ctx, task)
	case strings.Contains(issue, "quality"):
		return sc.handleQualityIssue(ctx, task)
	case strings.Contains(issue, "equipment"):
		return sc.handleEquipmentIssue(ctx, task)
	case strings.Contains(issue, "staff"):
		return sc.handleStaffingIssue(ctx, task)
	default:
		return fmt.Errorf("unknown issue type: %s", issue)
	}
}

func (sc *SousChef) getTaskCompletion(task Task) (float64, error) {
	// Get completion percentage from task metadata
	if completion, ok := task.Metadata["completion"].(float64); ok {
		return completion, nil
	}

	// Calculate completion based on subtasks
	if subtasks, ok := task.Metadata["subtasks"].([]Task); ok {
		var completed int
		for _, subtask := range subtasks {
			if subtask.Status == "completed" {
				completed++
			}
		}
		return float64(completed) / float64(len(subtasks)), nil
	}

	return 0.0, fmt.Errorf("unable to determine task completion")
}

func (sc *SousChef) handleTaskDelay(ctx context.Context, task Task) error {
	// Increase task priority
	task.Priority++

	// Reassign task if needed
	if task.Priority > 8 {
		newAssignee := sc.selectBestAssignee(task)
		if newAssignee != nil {
			task.Metadata["original_assignee"] = task.Metadata["assignee"]
			task.Metadata["assignee"] = newAssignee.ID
		}
	}

	// Record resolution attempt
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "delay_resolution",
		Content:   fmt.Sprintf("Handled delay for task %s", task.ID),
		Metadata: map[string]interface{}{
			"task_id":  task.ID,
			"priority": task.Priority,
		},
	})

	return nil
}

func (sc *SousChef) handleQualityIssue(ctx context.Context, task Task) error {
	// Record quality issue
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "quality_issue",
		Content:   fmt.Sprintf("Handling quality issue for task %s", task.ID),
		Metadata: map[string]interface{}{
			"task_id": task.ID,
			"issue":   "quality",
		},
	})

	// Assign experienced staff member to review
	reviewer := sc.selectBestAssignee(Task{
		Type:     "quality_review",
		Priority: task.Priority + 1,
	})
	if reviewer != nil {
		task.Metadata["reviewer"] = reviewer.ID
	}

	return nil
}

func (sc *SousChef) handleEquipmentIssue(ctx context.Context, task Task) error {
	// Record equipment issue
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "equipment_issue",
		Content:   fmt.Sprintf("Handling equipment issue for task %s", task.ID),
		Metadata: map[string]interface{}{
			"task_id": task.ID,
			"issue":   "equipment",
		},
	})

	// Request equipment maintenance
	if eq, ok := task.Metadata["equipment"].(string); ok {
		task.Metadata["maintenance_requested"] = true
		task.Metadata["equipment_status"] = "pending_maintenance"
		task.Status = "blocked"
		task.Metadata["equipment"] = eq
	}

	return nil
}

func (sc *SousChef) handleStaffingIssue(ctx context.Context, task Task) error {
	// Record staffing issue
	sc.AddMemory(ctx, Event{
		Timestamp: time.Now(),
		Type:      "staffing_issue",
		Content:   fmt.Sprintf("Handling staffing issue for task %s", task.ID),
		Metadata: map[string]interface{}{
			"task_id": task.ID,
			"issue":   "staffing",
		},
	})

	// Request additional staff if needed
	currentStaff := len(sc.StaffMembers)
	requiredStaff := sc.calculateRequiredStaff(sc.getCurrentLoad())
	if currentStaff < requiredStaff {
		if err := sc.requestAdditionalStaff(ctx, requiredStaff-currentStaff); err != nil {
			return fmt.Errorf("failed to request additional staff: %w", err)
		}
	}

	return nil
}

func (sc *SousChef) getCurrentLoad() int {
	var load int
	for _, order := range sc.ActiveOrders {
		load += len(order.Items)
	}
	return load
}

func (sc *SousChef) createPrepTasks(item models.OrderItem) []Task {
	var tasks []Task

	// Create prep tasks based on item requirements
	if item.Ingredients != nil {
		for i, ingredient := range item.Ingredients {
			tasks = append(tasks, Task{
				ID:          fmt.Sprintf("prep_%s_%d", item.Name, i),
				Type:        "ingredient_prep",
				Description: fmt.Sprintf("Prepare %s for %s", ingredient, item.Name),
				Priority:    1,
				Status:      "pending",
				StartTime:   time.Now(),
				Metadata: map[string]interface{}{
					"ingredient": ingredient,
					"item":       item.Name,
				},
			})
		}
	}

	return tasks
}

func (sc *SousChef) createCookingTasks(item models.OrderItem) []Task {
	var tasks []Task

	// Create cooking tasks based on item requirements
	tasks = append(tasks, Task{
		ID:          fmt.Sprintf("cook_%s", item.Name),
		Type:        "cooking",
		Description: fmt.Sprintf("Cook %s", item.Name),
		Priority:    2,
		Status:      "pending",
		StartTime:   time.Now(),
		Metadata: map[string]interface{}{
			"item":     item.Name,
			"duration": item.CookTime,
		},
	})

	return tasks
}

func (sc *SousChef) createPlatingTasks(item models.OrderItem) []Task {
	var tasks []Task

	// Create plating tasks based on item requirements
	tasks = append(tasks, Task{
		ID:          fmt.Sprintf("plate_%s", item.Name),
		Type:        "plating",
		Description: fmt.Sprintf("Plate %s", item.Name),
		Priority:    3,
		Status:      "pending",
		StartTime:   time.Now(),
		Metadata: map[string]interface{}{
			"item": item.Name,
		},
	})

	return tasks
}

func (sc *SousChef) getOrderTasks(order models.Order) []Task {
	var tasks []Task
	orderIDStr := fmt.Sprintf("%d", order.ID)
	for _, staff := range sc.StaffMembers {
		for _, task := range staff.memory.TaskQueue {
			if orderID, ok := task.Metadata["order_id"].(string); ok && orderID == orderIDStr {
				tasks = append(tasks, task)
			}
		}
	}
	return tasks
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
	if order.EstimatedTime == 0 {
		// If no estimated time is set, calculate based on items
		order.EstimatedTime = sc.calculateTotalPrepTime(order)
	}
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

func (sc *SousChef) escalateOrder(ctx context.Context, order models.Order) error {
	// Increase priority
	order.Priority++

	// Reassign if necessary
	if order.Priority > 8 {
		newAssignee := sc.selectBestAssignee(Task{
			ID:          fmt.Sprintf("%d", order.ID),
			Type:        "order_recovery",
			Description: "Recover delayed order",
			Priority:    order.Priority,
			Metadata: map[string]interface{}{
				"order_id": order.ID,
			},
		})
		if newAssignee != nil {
			order.AssignedTo = fmt.Sprintf("%d", newAssignee.ID)
		}
	}

	return nil
}

// calculateStaffingUrgency determines how urgent the need for additional staff is
func (sc *SousChef) calculateStaffingUrgency() string {
	// Check current workload
	currentLoad := len(sc.ActiveOrders)
	availableStaff := len(sc.StaffMembers)

	// Calculate ideal staff-to-order ratio
	idealStaff := currentLoad / 2 // Assume 1 staff member can handle 2 orders optimally

	if availableStaff == 0 && currentLoad > 0 {
		return "critical" // No staff but we have orders
	} else if float64(availableStaff) < float64(idealStaff)*0.5 {
		return "high" // Less than 50% of ideal staffing
	} else if float64(availableStaff) < float64(idealStaff)*0.8 {
		return "medium" // Less than 80% of ideal staffing
	}

	// Check if during peak hours
	if sc.isPeakHour() {
		// Increase urgency during peak hours
		if currentLoad > availableStaff*3 {
			return "high"
		}
		return "medium"
	}

	return "low"
}

// getRequiredSkills determines what skills are needed for additional staff
func (sc *SousChef) getRequiredSkills() []string {
	requiredSkills := make([]string, 0)

	// Analyze active orders to determine required skills
	skillsMap := make(map[string]bool)

	for _, order := range sc.ActiveOrders {
		for _, item := range order.Items {
			// Add skills based on item preparation requirements
			if item.RequiresGrilling {
				skillsMap["grilling"] = true
			}
			if item.RequiresSauteing {
				skillsMap["sauteing"] = true
			}
			if item.RequiresBaking {
				skillsMap["baking"] = true
			}
			// Add more specialized skills based on recipe complexity
			if item.Complexity > 7 {
				skillsMap["advanced_cooking"] = true
			}
		}
	}

	// Convert map to slice
	for skill := range skillsMap {
		requiredSkills = append(requiredSkills, skill)
	}

	// Always need basic skills
	if len(requiredSkills) == 0 {
		requiredSkills = append(requiredSkills, "cooking_basics")
	}

	return requiredSkills
}

// identifyStaffForRelease selects staff members that can be released
func (sc *SousChef) identifyStaffForRelease(count int) []string {
	staffIDs := make([]string, 0)

	// Create a list of staff with workload assessment
	type staffWorkload struct {
		ID       string
		Workload float64
		Critical bool // Whether the staff has critical skills
	}

	var staffList []staffWorkload

	// Calculate workload for each staff member
	for _, staff := range sc.StaffMembers {
		workload := sc.calculateWorkload(staff)
		critical := sc.hasUniqueSkills(staff)

		staffList = append(staffList, staffWorkload{
			ID:       fmt.Sprintf("%d", staff.ID),
			Workload: workload,
			Critical: critical,
		})
	}

	// Sort by workload (lowest first) and non-critical first
	sort.Slice(staffList, func(i, j int) bool {
		if staffList[i].Critical != staffList[j].Critical {
			return !staffList[i].Critical // Non-critical first
		}
		return staffList[i].Workload < staffList[j].Workload // Then by lowest workload
	})

	// Select staff to release, limited by count
	for i := 0; i < len(staffList) && len(staffIDs) < count; i++ {
		if staffList[i].Workload < 0.3 && !staffList[i].Critical { // Only release if workload is low
			staffIDs = append(staffIDs, staffList[i].ID)
		}
	}

	return staffIDs
}

// hasUniqueSkills determines if a staff member has unique skills that others don't
func (sc *SousChef) hasUniqueSkills(staff *BaseAgent) bool {
	// Get this staff member's skills
	staffSkills, ok := staff.memory.ShortTerm[0].Metadata["skills"].([]string)
	if !ok {
		return false
	}

	// Check if any skill is unique to this staff member
	for _, skill := range staffSkills {
		unique := true
		for _, other := range sc.StaffMembers {
			if other.ID == staff.ID {
				continue // Skip self
			}

			otherSkills, ok := other.memory.ShortTerm[0].Metadata["skills"].([]string)
			if !ok {
				continue
			}

			for _, otherSkill := range otherSkills {
				if otherSkill == skill {
					unique = false
					break
				}
			}

			if !unique {
				break
			}
		}

		if unique {
			return true
		}
	}

	return false
}

// reassignTasksFromReleasedStaff redistributes tasks from staff being released
func (sc *SousChef) reassignTasksFromReleasedStaff(ctx context.Context, staffIDs []string) error {
	// Convert string IDs to a map for quick lookup
	idMap := make(map[string]bool)
	for _, id := range staffIDs {
		idMap[id] = true
	}

	// Collect all tasks from staff being released
	var tasksToReassign []Task

	for _, staff := range sc.StaffMembers {
		staffID := fmt.Sprintf("%d", staff.ID)
		if _, releasing := idMap[staffID]; releasing {
			// Add tasks to reassignment list
			for _, task := range staff.memory.TaskQueue {
				if task.Status == "pending" || task.Status == "in_progress" {
					tasksToReassign = append(tasksToReassign, task)
				}
			}

			// Clear staff task queue
			staff.memory.TaskQueue = []Task{}
		}
	}

	// Reassign each collected task
	for _, task := range tasksToReassign {
		assignee := sc.selectBestAssignee(task)
		if assignee == nil {
			return fmt.Errorf("no suitable assignee for task %s", task.ID)
		}

		// Record reassignment
		sc.AddMemory(ctx, Event{
			Timestamp: time.Now(),
			Type:      "task_reassignment",
			Content:   fmt.Sprintf("Reassigned task %s to staff member %d", task.ID, assignee.ID),
			Metadata: map[string]interface{}{
				"task_id":     task.ID,
				"assignee_id": assignee.ID,
			},
		})

		assignee.AddTask(task)
	}

	return nil
}

// removeReleasedStaffFromRoster removes released staff from the SousChef's roster
func (sc *SousChef) removeReleasedStaffFromRoster(staffIDs []string) {
	// Convert string IDs to a map for quick lookup
	idMap := make(map[string]bool)
	for _, id := range staffIDs {
		idMap[id] = true
	}

	// Create a new staff list without the released staff
	newStaffList := make([]*BaseAgent, 0)

	for _, staff := range sc.StaffMembers {
		staffID := fmt.Sprintf("%d", staff.ID)
		if _, releasing := idMap[staffID]; !releasing {
			newStaffList = append(newStaffList, staff)
		}
	}

	// Update the SousChef's staff list
	sc.StaffMembers = newStaffList
}
