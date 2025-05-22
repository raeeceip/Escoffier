package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log"
	"masterchef/internal/agents"
	"masterchef/internal/api"
	"masterchef/internal/models"
	"masterchef/internal/playground"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/gin-gonic/gin"
	"github.com/jinzhu/gorm"
	_ "github.com/mattn/go-sqlite3"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/openai"
)

var (
	port             = flag.Int("port", 8080, "API server port")
	metricsPort      = flag.Int("metrics-port", 9090, "Metrics server port")
	playgroundPort   = flag.Int("playground-port", 8090, "Playground server port")
	configFile       = flag.String("config", "configs/config.yaml", "Path to configuration file")
	enablePlayground = flag.Bool("enable-playground", true, "Enable LLM playground server")
)

// Database represents the application's database connection
type Database struct {
	*gorm.DB
}

// GetInventory returns the current inventory state
func (db *Database) GetInventory(ctx context.Context) (map[string]float64, error) {
	var items []struct {
		Name     string
		Quantity float64
	}
	if err := db.Table("inventory_items").Select("name, quantity").Scan(&items).Error; err != nil {
		return nil, err
	}

	inventory := make(map[string]float64)
	for _, item := range items {
		inventory[item.Name] = item.Quantity
	}
	return inventory, nil
}

// GetOrder retrieves an order by ID
func (db *Database) GetOrder(ctx context.Context, id string) (*models.Order, error) {
	var order models.Order
	if err := db.Where("id = ?", id).First(&order).Error; err != nil {
		return nil, err
	}
	return &order, nil
}

// SaveOrder saves an order to the database
func (db *Database) SaveOrder(ctx context.Context, order *models.Order) error {
	return db.Save(order).Error
}

// UpdateInventory updates the inventory levels
func (db *Database) UpdateInventory(ctx context.Context, inventory map[string]float64) error {
	tx := db.Begin()
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	for item, quantity := range inventory {
		if err := tx.Table("inventory_items").Where("name = ?", item).Update("quantity", quantity).Error; err != nil {
			tx.Rollback()
			return err
		}
	}

	return tx.Commit().Error
}

func main() {
	flag.Parse()

	// Initialize context
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Load configuration
	config, err := loadConfig(*configFile)
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Initialize LLM
	model, err := initializeLLM(config)
	if err != nil {
		log.Fatalf("Failed to initialize LLM: %v", err)
	}

	// Initialize database
	db, err := initializeDB(config)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}

	// Initialize API server
	api := api.NewKitchenAPI(model, db)

	// Initialize agents
	if err := initializeAgents(ctx, api, model); err != nil {
		log.Fatalf("Failed to initialize agents: %v", err)
	}

	// Start metrics server if enabled
	if config.MetricsConfig.Enabled {
		go startMetricsServer(*metricsPort)
	}

	// Start playground server if enabled
	if *enablePlayground {
		go startPlaygroundServer(*playgroundPort)
	}

	// Start API server
	server := &http.Server{
		Addr:    fmt.Sprintf(":%d", *port),
		Handler: api.Router,
	}

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan

		log.Println("Shutting down servers...")

		// Shutdown API server
		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer shutdownCancel()

		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("API server shutdown error: %v", err)
		}

		cancel() // Cancel main context
	}()

	// Start server
	log.Printf("Starting API server on port %d", *port)
	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		log.Fatalf("API server error: %v", err)
	}
}

func loadConfig(path string) (*Config, error) {
	cfg := defaultConfig()
	// read file if exists
	if f, err := os.Open(path); err == nil {
		defer f.Close()
		decoder := yaml.NewDecoder(f)
		_ = decoder.Decode(&cfg) // ignore error if partial
	}
	// env overrides
	if v := os.Getenv("DATABASE_URL"); v != "" {
		cfg.DatabaseURL = v
	}
	if v := os.Getenv("LOG_LEVEL"); v != "" {
		cfg.LogLevel = v
	}
	return cfg, nil
}

func defaultConfig() *Config {
	return &Config{
		DatabaseURL: filepath.Join("data", "masterchef.db"),
		MetricsConfig: struct {
			Enabled bool   `yaml:"enabled"`
			Port    int    `yaml:"port"`
			Path    string `yaml:"path"`
		}{Enabled: true, Port: 9090, Path: "/metrics"},
	}
}

func initializeLLM(config *Config) (llms.LLM, error) {
	// Check if OpenAI API key is set
	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		// Use dummy API key for development
		log.Println("Warning: OPENAI_API_KEY not set, using mock key for development")
		apiKey = "sk-mock-development-key"
	}

	// Initialize OpenAI client with the provided API key
	llm, err := openai.New(
		openai.WithModel("gpt-4-turbo-preview"),
		openai.WithToken(apiKey),
		// Add option to not validate API key for local development
		openai.WithHTTPClient(&http.Client{
			Transport: &mockTransport{},
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize OpenAI client: %w", err)
	}

	return llm, nil
}

// mockTransport is a simple mock transport that returns fake responses
type mockTransport struct{}

func (t *mockTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	// Only intercept OpenAI API calls
	if req.URL.Host == "api.openai.com" {
		// Create a mock response
		mockResp := &http.Response{
			StatusCode: 200,
			Body: io.NopCloser(strings.NewReader(`{
				"id": "mock-response-id",
				"object": "chat.completion",
				"created": 1677858242,
				"model": "gpt-4-turbo-preview",
				"choices": [
					{
						"message": {
							"role": "assistant",
							"content": "This is a mock response for development without an OpenAI API key."
						},
						"finish_reason": "stop",
						"index": 0
					}
				],
				"usage": {
					"prompt_tokens": 10,
					"completion_tokens": 20,
					"total_tokens": 30
				}
			}`)),
			Header: make(http.Header),
		}
		mockResp.Header.Set("Content-Type", "application/json")
		return mockResp, nil
	}

	// For other requests, use the default transport
	return http.DefaultTransport.RoundTrip(req)
}

func initializeDB(config *Config) (*Database, error) {
	absPath, _ := filepath.Abs(config.DatabaseURL)
	// ensure directory exists
	dir := filepath.Dir(absPath)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, fmt.Errorf("failed to create data dir: %w", err)
	}
	// open sqlite
	db, err := gorm.Open("sqlite3", absPath)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}
	// Enable GORM logging in development
	db.LogMode(true)

	// Configure connection pool
	db.DB().SetMaxIdleConns(10)
	db.DB().SetMaxOpenConns(100)
	db.DB().SetConnMaxLifetime(time.Hour)

	return &Database{DB: db}, nil
}

func initializeAgents(ctx context.Context, api *api.KitchenAPI, model llms.LLM) error {
	// Initialize executive chef
	executiveChef := agents.NewExecutiveChef(ctx, model)
	api.ExecutiveChef = executiveChef

	// Initialize sous chefs for different stations
	stations := []string{"hot", "cold", "pastry", "grill"}
	for _, station := range stations {
		sousChef := agents.NewSousChef(ctx, model, station)
		api.SousChefs[station] = sousChef
	}

	return nil
}

func startMetricsServer(port int) {
	metricsRouter := gin.Default()
	metricsRouter.GET("/metrics", gin.WrapH(promhttp.Handler()))

	metricsServer := &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: metricsRouter,
	}

	log.Printf("Starting metrics server on port %d", port)
	if err := metricsServer.ListenAndServe(); err != http.ErrServerClosed {
		log.Printf("Metrics server error: %v", err)
	}
}

func startPlaygroundServer(port int) {
	playgroundServer := playground.NewPlaygroundServer()

	server := &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: playgroundServer.Router(),
	}

	log.Printf("Starting LLM playground server on port %d", port)
	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		log.Printf("Playground server error: %v", err)
	}
}

// Config represents the application configuration
type Config struct {
	OpenAIKey     string `yaml:"openai_key"`
	DatabaseURL   string `yaml:"database_url"`
	LogLevel      string `yaml:"log_level"`
	MetricsConfig struct {
		Enabled bool   `yaml:"enabled"`
		Port    int    `yaml:"port"`
		Path    string `yaml:"path"`
	} `yaml:"metrics"`
}
