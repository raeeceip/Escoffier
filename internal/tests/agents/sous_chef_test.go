package agents

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestNewSousChef(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Assert basic properties
	assert.NotNil(t, chef)
	assert.Equal(t, "sous_chef", chef.Role)
	assert.Equal(t, "hot", chef.Station)
	assert.NotNil(t, chef.ActiveOrders)
	assert.NotNil(t, chef.StaffMembers)
	assert.NotNil(t, chef.Specialties)

	// Assert permissions
	expectedPermissions := []string{
		"order_management",
		"staff_supervision",
		"quality_control",
		"station_management",
		"inventory_monitoring",
	}
	assert.ElementsMatch(t, expectedPermissions, chef.Permissions)
}

func TestManageStation(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)
	mockLLM.On("Complete", mock.Anything, mock.Anything).Return("station management response", nil)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Test station management
	err := chef.ManageStation(context.Background())
	assert.NoError(t, err)
}

func TestHandleOrder(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Create test order
	order := Order{
		ID:           "test-order-1",
		Items:        []MenuItem{},
		Status:       "assigned",
		Priority:     1,
		TimeReceived: time.Now(),
	}

	// Test order handling
	err := chef.HandleOrder(context.Background(), order)
	assert.NoError(t, err)

	// Verify order was added to active orders
	found := false
	for _, activeOrder := range chef.ActiveOrders {
		if activeOrder.ID == order.ID {
			found = true
			break
		}
	}
	assert.True(t, found, "Order should be in active orders")
}

func TestSupervisePreparation(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)
	mockLLM.On("Complete", mock.Anything, mock.Anything).Return("supervision response", nil)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Create test order
	order := Order{
		ID:           "test-order-1",
		Status:       "preparing",
		TimeReceived: time.Now(),
	}

	// Test preparation supervision
	err := chef.SupervisePreparation(context.Background(), order)
	assert.NoError(t, err)
}

func TestAssistExecutiveChef(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Create test task
	task := Task{
		ID:          "task1",
		Description: "Special preparation request",
		Priority:    2,
		Status:      "pending",
	}

	// Test executive chef assistance
	err := chef.AssistExecutiveChef(context.Background(), task)
	assert.NoError(t, err)
}

func TestCheckStationStatus(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Test station status check
	status, err := chef.checkStationStatus(context.Background())
	assert.NoError(t, err)
	assert.NotNil(t, status)
	assert.Equal(t, "hot", status.Name)
}

func TestOptimizeStaffing(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Create test station status
	status := &StationStatus{
		Name:           "hot",
		Capacity:       5,
		CurrentLoad:    3,
		AvailableStaff: 2,
		Equipment:      []string{"stove", "oven"},
		Status:         "operational",
	}

	// Test staffing optimization
	err := chef.optimizeStaffing(context.Background(), status)
	assert.NoError(t, err)
}

func TestValidateOrderRequirements(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Test cases
	tests := []struct {
		name        string
		order       Order
		shouldError bool
	}{
		{
			name: "Valid order",
			order: Order{
				ID:     "test-order-1",
				Status: "assigned",
				Items: []MenuItem{
					{
						Name:     "Test Dish",
						Category: "hot",
					},
				},
			},
			shouldError: false,
		},
		{
			name: "Invalid station",
			order: Order{
				ID:     "test-order-2",
				Status: "assigned",
				Items: []MenuItem{
					{
						Name:     "Test Dish",
						Category: "cold",
					},
				},
			},
			shouldError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := chef.validateOrderRequirements(context.Background(), tt.order)
			if tt.shouldError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestAssignOrderTasks(t *testing.T) {
	// Create mock LLM
	mockLLM := new(MockLLM)

	// Create sous chef
	chef := NewSousChef(context.Background(), mockLLM, "hot")

	// Add test staff members
	chef.StaffMembers = []*Agent{
		{
			Role: "line_cook",
			Memory: &Memory{
				TaskQueue: make([]Task, 0),
			},
		},
		{
			Role: "prep_cook",
			Memory: &Memory{
				TaskQueue: make([]Task, 0),
			},
		},
	}

	// Create test order
	order := Order{
		ID:     "test-order-1",
		Status: "assigned",
		Items: []MenuItem{
			{
				Name:     "Test Dish",
				Category: "hot",
			},
		},
	}

	// Test task assignment
	err := chef.assignOrderTasks(context.Background(), order)
	assert.NoError(t, err)

	// Verify tasks were assigned
	tasksAssigned := 0
	for _, staff := range chef.StaffMembers {
		tasksAssigned += len(staff.Memory.TaskQueue)
	}
	assert.Greater(t, tasksAssigned, 0, "Tasks should be assigned to staff members")
}
