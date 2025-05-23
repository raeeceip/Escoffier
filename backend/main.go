package main

import (
	"context"
	"fmt"
	"log"
	"escoffier/backend/handlers"
	"escoffier/internal/database"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/dgrijalva/jwt-go"
	"github.com/gin-gonic/gin"
	_ "github.com/mattn/go-sqlite3" // SQLite driver
)

func main() {
	// Initialize database
	if err := database.InitDB("escoffier.db"); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer database.CloseDB()

	// Initialize database schema
	InitializeDatabase()

	// Create router
	router := gin.Default()

	// Setup routes
	setupRoutes(router)

	// Create server
	srv := &http.Server{
		Addr:    ":8080",
		Handler: router,
	}

	// Start server in a goroutine
	go func() {
		fmt.Println("Starting server on :8080...")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	fmt.Println("Shutting down server...")

	// Create a deadline for server shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	fmt.Println("Server exited gracefully")
}

// setupRoutes configures all the API routes
func setupRoutes(router *gin.Engine) {
	fmt.Println("Setting up routes...")

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "ok",
			"message": "Escoffier-Bench API is running",
		})
	})

	// Kitchen routes
	router.GET("/kitchen", handlers.GetKitchenStateHandler)
	router.POST("/kitchen", handlers.UpdateKitchenStateHandler)

	// Agent routes
	InitializeAgentRoutes(router)

	// Order routes
	InitializeOrderRoutes(router)

	// Evaluation routes
	InitializeEvaluationRoutes(router)
}

// AuthMiddleware handles JWT authentication
func AuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		tokenString := c.GetHeader("Authorization")
		if tokenString == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Authorization header required"})
			c.Abort()
			return
		}

		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (any, error) {
			return []byte("your_secret_key"), nil
		})

		if err != nil || !token.Valid {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid token"})
			c.Abort()
			return
		}

		c.Next()
	}
}
