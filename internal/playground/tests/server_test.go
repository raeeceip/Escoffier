package tests

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"masterchef/internal/playground"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestHandleListModels(t *testing.T) {
	// Set Gin to test mode
	gin.SetMode(gin.TestMode)

	// Create a new server
	server := playground.NewPlaygroundServer()

	// Create a response recorder
	w := httptest.NewRecorder()

	// Create a request
	req, _ := http.NewRequest("GET", "/api/models", nil)

	// Perform the request
	server.Router().ServeHTTP(w, req)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)

	// Parse response body
	var response []map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)

	// Assert there was no error in parsing
	assert.NoError(t, err)

	// Assert there are models in the response
	assert.NotEmpty(t, response)

	// Check that each model has the expected fields
	for _, model := range response {
		assert.Contains(t, model, "id")
		assert.Contains(t, model, "name")
		assert.Contains(t, model, "type")
		assert.Contains(t, model, "maxTokens")
	}
}

func TestHandleListScenarios(t *testing.T) {
	// Set Gin to test mode
	gin.SetMode(gin.TestMode)

	// Create a new server
	server := playground.NewPlaygroundServer()

	// Create a response recorder
	w := httptest.NewRecorder()

	// Create a request
	req, _ := http.NewRequest("GET", "/api/scenarios", nil)

	// Perform the request
	server.Router().ServeHTTP(w, req)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)

	// Parse response body
	var response []map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)

	// Assert there was no error in parsing
	assert.NoError(t, err)

	// Assert there are scenarios in the response
	assert.NotEmpty(t, response)

	// Check that each scenario has the expected fields
	for _, scenario := range response {
		assert.Contains(t, scenario, "id")
		assert.Contains(t, scenario, "name")
		assert.Contains(t, scenario, "type")
		assert.Contains(t, scenario, "description")
	}
}

func TestHandleMetrics(t *testing.T) {
	// Set Gin to test mode
	gin.SetMode(gin.TestMode)

	// Create a new server
	server := playground.NewPlaygroundServer()

	// Create a response recorder
	w := httptest.NewRecorder()

	// Create a request
	req, _ := http.NewRequest("GET", "/api/metrics", nil)

	// Perform the request
	server.Router().ServeHTTP(w, req)

	// Assert response
	assert.Equal(t, http.StatusOK, w.Code)

	// Parse response body
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)

	// Assert there was no error in parsing
	assert.NoError(t, err)

	// Uptime should be present
	assert.Contains(t, response, "uptime_seconds")
}
