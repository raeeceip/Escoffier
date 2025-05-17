package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"time"
)

const baseURL = "http://localhost:8080"

// ApiClient handles API requests to the MasterChef-Bench API
type ApiClient struct {
	httpClient *http.Client
}

// NewApiClient creates a new API client
func NewApiClient() *ApiClient {
	return &ApiClient{
		httpClient: &http.Client{
			Timeout: time.Second * 10,
		},
	}
}

// CheckHealth checks if the API is up and running
func (c *ApiClient) CheckHealth() (bool, error) {
	resp, err := c.httpClient.Get(baseURL + "/health")
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
	resp, err := c.httpClient.Get(baseURL + "/kitchen")
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

	req, err := http.NewRequest("POST", baseURL+"/kitchen", bytes.NewBuffer(data))
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
	resp, err := c.httpClient.Get(baseURL + "/agents")
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

	req, err := http.NewRequest("POST", baseURL+"/agents", bytes.NewBuffer(data))
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
	url := baseURL + "/orders"
	if status != "" {
		url += fmt.Sprintf("?status=%s", status)
	}

	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get orders with status code: %d", resp.StatusCode)
	}

	var orders []Order
	if err := json.NewDecoder(resp.Body).Decode(&orders); err != nil {
		return nil, err
	}

	return orders, nil
}

// GetOrder retrieves a specific order by ID
func (c *ApiClient) GetOrder(id uint) (*Order, error) {
	resp, err := c.httpClient.Get(fmt.Sprintf("%s/orders/%d", baseURL, id))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get order with status code: %d", resp.StatusCode)
	}

	var order Order
	if err := json.NewDecoder(resp.Body).Decode(&order); err != nil {
		return nil, err
	}

	return &order, nil
}

// CreateOrder creates a new order
func (c *ApiClient) CreateOrder(order *Order) (*Order, error) {
	data, err := json.Marshal(order)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", baseURL+"/orders", bytes.NewBuffer(data))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("failed to create order: %s", string(body))
	}

	var createdOrder Order
	if err := json.NewDecoder(resp.Body).Decode(&createdOrder); err != nil {
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

	req, err := http.NewRequest("PUT", fmt.Sprintf("%s/orders/%d", baseURL, order.ID), bytes.NewBuffer(data))
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
	req, err := http.NewRequest("DELETE", fmt.Sprintf("%s/orders/%d", baseURL, id), nil)
	if err != nil {
		return err
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("failed to cancel order: %s", string(body))
	}

	return nil
}
