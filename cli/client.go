package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"time"
)

const baseURL = "http://localhost:8080"

// ApiClient handles API requests to the Escoffier-Bench API
type ApiClient struct {
	httpClient *http.Client
	BaseURL    string
	UseMock    bool
}

// NewApiClient creates a new API client
func NewApiClient() *ApiClient {
	baseURL := os.Getenv("ESCOFFIER_API_URL")
	if baseURL == "" {
		baseURL = "http://localhost:8080"
	}

	client := &ApiClient{
		httpClient: &http.Client{
			Timeout: time.Second * 10,
		},
		BaseURL: baseURL,
		UseMock: false, // Default to trying the real server first
	}

	// Verify connectivity - if server is not available, use mock data
	if !client.ping() {
		fmt.Printf("Warning: API server at %s is not available. Using mock data.\n", baseURL)
		client.UseMock = true
	}

	return client
}

// ping checks if the API server is available
func (c *ApiClient) ping() bool {
	url := fmt.Sprintf("%s/health", c.BaseURL)
	resp, err := http.Get(url)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

// CheckHealth checks if the API is up and running
func (c *ApiClient) CheckHealth() (bool, error) {
	resp, err := c.httpClient.Get(c.BaseURL + "/health")
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("API health check failed with status code: %d", resp.StatusCode)
	}

	return true, nil
}

// Kitchen represents the kitchen state
type Kitchen struct {
	ID        uint            `json:"id"`
	Inventory []InventoryItem `json:"inventory"`
	Equipment []EquipmentItem `json:"equipment"`
	Status    string          `json:"status"`
}

// InventoryItem represents an item in the kitchen inventory
type InventoryItem struct {
	ID       uint   `json:"id"`
	Name     string `json:"name"`
	Quantity int    `json:"quantity"`
}

// EquipmentItem represents an item of equipment in the kitchen
type EquipmentItem struct {
	ID     uint   `json:"id"`
	Name   string `json:"name"`
	Status string `json:"status"`
}

// Agent represents a kitchen agent
type Agent struct {
	ID          uint     `json:"id"`
	Name        string   `json:"name"`
	Role        string   `json:"role"`
	Station     string   `json:"station"`
	Status      string   `json:"status"`
	Skills      []string `json:"skills"`
	Performance float64  `json:"performance"`
}

// Order represents a customer order
type Order struct {
	ID            uint        `json:"id"`
	Type          string      `json:"type"`
	Items         []OrderItem `json:"items"`
	Status        string      `json:"status"`
	Priority      int         `json:"priority"`
	TimeReceived  time.Time   `json:"time_received"`
	TimeCompleted time.Time   `json:"time_completed,omitempty"`
	AssignedTo    string      `json:"assigned_to,omitempty"`
	EstimatedTime int         `json:"estimated_time"`
	Notes         string      `json:"notes,omitempty"`
}

// OrderItem represents an item in an order
type OrderItem struct {
	ID                uint     `json:"id"`
	OrderID           uint     `json:"order_id"`
	Name              string   `json:"name"`
	Quantity          int      `json:"quantity"`
	Notes             string   `json:"notes,omitempty"`
	Status            string   `json:"status"`
	PrepTime          int      `json:"prep_time"`
	CookTime          int      `json:"cook_time"`
	RequiredEquipment []string `json:"required_equipment"`
	Ingredients       []string `json:"ingredients"`
	Category          string   `json:"category"`
	Price             float64  `json:"price"`
	IsSpecialty       bool     `json:"is_specialty"`
}

// GetKitchenState retrieves the current kitchen state
func (c *ApiClient) GetKitchenState() (*Kitchen, error) {
	resp, err := c.httpClient.Get(c.BaseURL + "/kitchen")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get kitchen state with status code: %d", resp.StatusCode)
	}

	var kitchen Kitchen
	if err := json.NewDecoder(resp.Body).Decode(&kitchen); err != nil {
		return nil, err
	}

	return &kitchen, nil
}

// UpdateKitchenState updates the kitchen state
func (c *ApiClient) UpdateKitchenState(kitchen *Kitchen) error {
	data, err := json.Marshal(kitchen)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", c.BaseURL+"/kitchen", bytes.NewBuffer(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("failed to update kitchen state: %s", string(body))
	}

	return nil
}

// GetAgents retrieves all agents
func (c *ApiClient) GetAgents() ([]Agent, error) {
	resp, err := c.httpClient.Get(c.BaseURL + "/agents")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get agents with status code: %d", resp.StatusCode)
	}

	var agents []Agent
	if err := json.NewDecoder(resp.Body).Decode(&agents); err != nil {
		return nil, err
	}

	return agents, nil
}

// CreateAgent creates a new agent
func (c *ApiClient) CreateAgent(agent *Agent) error {
	data, err := json.Marshal(agent)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", c.BaseURL+"/agents", bytes.NewBuffer(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("failed to create agent: %s", string(body))
	}

	return nil
}

// GetOrders retrieves all orders with optional filter
func (c *ApiClient) GetOrders(status string) ([]Order, error) {
	if c.UseMock {
		return c.getMockOrders(status), nil
	}

	url := c.BaseURL + "/orders"
	if status != "" {
		url += fmt.Sprintf("?status=%s", status)
	}

	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var orders []Order
	err = json.Unmarshal(body, &orders)
	if err != nil {
		return nil, err
	}

	return orders, nil
}

// GetOrder retrieves a specific order by ID
func (c *ApiClient) GetOrder(id uint) (*Order, error) {
	if c.UseMock {
		return c.getMockOrder(id), nil
	}

	resp, err := c.httpClient.Get(fmt.Sprintf("%s/orders/%d", c.BaseURL, id))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var order Order
	err = json.Unmarshal(body, &order)
	if err != nil {
		return nil, err
	}

	return &order, nil
}

// CreateOrder creates a new order
func (c *ApiClient) CreateOrder(order *Order) (*Order, error) {
	if c.UseMock {
		return c.createMockOrder(order), nil
	}

	data, err := json.Marshal(order)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", c.BaseURL+"/orders", bytes.NewBuffer(data))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var createdOrder Order
	err = json.Unmarshal(body, &createdOrder)
	if err != nil {
		return nil, err
	}

	return &createdOrder, nil
}

// UpdateOrder updates an existing order
func (c *ApiClient) UpdateOrder(order *Order) error {
	data, err := json.Marshal(order)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("PUT", fmt.Sprintf("%s/orders/%d", c.BaseURL, order.ID), bytes.NewBuffer(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("failed to update order: %s", string(body))
	}

	return nil
}

// CancelOrder cancels an order by ID
func (c *ApiClient) CancelOrder(id uint) error {
	if c.UseMock {
		// Just pretend it worked
		return nil
	}

	req, err := http.NewRequest("DELETE", fmt.Sprintf("%s/orders/%d", c.BaseURL, id), nil)
	if err != nil {
		return err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return nil
}

// Mock data generators
// getMockOrders generates mock order data
func (c *ApiClient) getMockOrders(status string) []Order {
	orders := []Order{
		{
			ID:            1,
			Type:          "dine_in",
			Status:        "active",
			Priority:      2,
			TimeReceived:  time.Now().Add(-30 * time.Minute),
			TimeCompleted: time.Time{},
			AssignedTo:    "sous_chef_1",
			Items: []OrderItem{
				{Name: "Pasta Carbonara", Quantity: 2, Status: "in_progress", Notes: "Extra cheese"},
				{Name: "Caesar Salad", Quantity: 1, Status: "completed", Notes: "No croutons"},
			},
		},
		{
			ID:            2,
			Type:          "takeout",
			Status:        "pending",
			Priority:      1,
			TimeReceived:  time.Now().Add(-15 * time.Minute),
			TimeCompleted: time.Time{},
			AssignedTo:    "",
			Items: []OrderItem{
				{Name: "Margherita Pizza", Quantity: 1, Status: "pending", Notes: ""},
				{Name: "Tiramisu", Quantity: 2, Status: "pending", Notes: ""},
			},
		},
		{
			ID:            3,
			Type:          "dine_in",
			Status:        "completed",
			Priority:      2,
			TimeReceived:  time.Now().Add(-60 * time.Minute),
			TimeCompleted: time.Now().Add(-15 * time.Minute),
			AssignedTo:    "sous_chef_2",
			Items: []OrderItem{
				{Name: "Steak", Quantity: 1, Status: "completed", Notes: "Medium rare"},
				{Name: "Mashed Potatoes", Quantity: 1, Status: "completed", Notes: ""},
				{Name: "Red Wine", Quantity: 1, Status: "completed", Notes: "House red"},
			},
		},
	}

	// Filter by status if specified
	if status != "" {
		var filtered []Order
		for _, order := range orders {
			if order.Status == status {
				filtered = append(filtered, order)
			}
		}
		return filtered
	}

	return orders
}

// getMockOrder returns a mock order by ID
func (c *ApiClient) getMockOrder(id uint) *Order {
	orders := c.getMockOrders("")
	for _, order := range orders {
		if order.ID == id {
			return &order
		}
	}
	return nil
}

// createMockOrder simulates creating a new order
func (c *ApiClient) createMockOrder(order *Order) *Order {
	// Make a deep copy
	newOrder := *order

	// Set mock values
	newOrder.ID = uint(time.Now().Unix() % 1000) // Random-ish ID
	newOrder.TimeReceived = time.Now()
	newOrder.Status = "pending"

	// Set item statuses
	for i := range newOrder.Items {
		newOrder.Items[i].Status = "pending"
	}

	return &newOrder
}
