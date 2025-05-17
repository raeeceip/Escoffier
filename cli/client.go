package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"masterchef/internal/models"
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
func (c *ApiClient) GetAgents() ([]models.Agent, error) {
	resp, err := c.httpClient.Get(baseURL + "/agents")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("failed to get agents with status code: %d", resp.StatusCode)
	}

	var agents []models.Agent
	if err := json.NewDecoder(resp.Body).Decode(&agents); err != nil {
		return nil, err
	}

	return agents, nil
}

// CreateAgent creates a new agent
func (c *ApiClient) CreateAgent(agent *models.Agent) error {
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
