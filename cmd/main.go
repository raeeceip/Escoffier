package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"masterchef/internal/agents"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/openai"
)

var (
	port        = flag.Int("port", 8080, "API server port")
	metricsPort = flag.Int("metrics-port", 9090, "Metrics server port")
	configFile  = flag.String("config", "configs/config.yaml", "Path to configuration file")
)

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

	// Initialize metrics collector
	metricsCollector := evaluation.NewMetricsCollector()

	// Initialize API server
	api := api.NewKitchenAPI(model, db)

	// Initialize agents
	if err := initializeAgents(ctx, api, model); err != nil {
		log.Fatalf("Failed to initialize agents: %v", err)
	}

	// Start metrics server
	go startMetricsServer(*metricsPort)

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
	// Implement configuration loading
	return &Config{}, nil
}

func initializeLLM(config *Config) (llms.LLM, error) {
	// Initialize OpenAI client
	llm, err := openai.New(
		openai.WithModel("gpt-4-turbo-preview"),
		openai.WithAPIKey(config.OpenAIKey),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize OpenAI client: %w", err)
	}

	return llm, nil
}

func initializeDB(config *Config) (*Database, error) {
	// Implement database initialization
	return &Database{}, nil
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
