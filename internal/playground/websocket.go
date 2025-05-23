package playground

import (
	"encoding/json"
	"log"
	"escoffier/internal/evaluation"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

// WebSocket upgrader configuration
var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins for development
	},
}

// WSConnection maintains the WebSocket connection with the client
type WSConnection struct {
	conn      *websocket.Conn
	send      chan []byte
	mu        sync.Mutex
	evaluator *evaluation.Evaluator
	server    *PlaygroundServer
}

// Result represents an evaluation result to be sent via WebSocket
type Result struct {
	Model    string                 `json:"model"`
	Scenario string                 `json:"scenario"`
	Metrics  map[string]interface{} `json:"metrics"`
	Events   []interface{}          `json:"events,omitempty"`
}

// handleWebSocket handles WebSocket connections
func (s *PlaygroundServer) handleWebSocket(c *gin.Context) {
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("Failed to upgrade connection: %v", err)
		return
	}

	wsConn := &WSConnection{
		conn:      conn,
		send:      make(chan []byte, 256),
		evaluator: s.evaluator,
		server:    s,
	}

	// Start the read and write pumps
	go wsConn.writePump()
	go wsConn.readPump()
}

// readPump pumps messages from the WebSocket connection to the handler
func (c *WSConnection) readPump() {
	defer func() {
		c.conn.Close()
	}()

	c.conn.SetReadLimit(512 * 1024) // 512KB
	c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	c.conn.SetPongHandler(func(string) error {
		c.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}

		// Handle the message
		c.handleMessage(message)
	}
}

// writePump pumps messages from the server to the WebSocket connection
func (c *WSConnection) writePump() {
	ticker := time.NewTicker(30 * time.Second)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				// The channel was closed
				c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)

			if err := w.Close(); err != nil {
				return
			}
		case <-ticker.C:
			c.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// handleMessage processes incoming messages
func (c *WSConnection) handleMessage(message []byte) {
	var req EvaluationRequest
	if err := json.Unmarshal(message, &req); err != nil {
		log.Printf("Error unmarshaling message: %v", err)
		return
	}

	// Start evaluation in background
	go func() {
		// Get model
		_, err := c.server.registry.GetModel(req.Model)
		if err != nil {
			c.sendError("Invalid model: " + req.Model)
			return
		}

		// Check if scenario exists
		if !c.evaluator.HasScenario(req.Scenario) {
			c.sendError("Invalid scenario: " + req.Scenario)
			return
		}

		// Start evaluation
		results := c.evaluator.EvaluateModel(req.Model, req.Scenario)
		c.sendResults(results)
	}()
}

// sendResults sends evaluation results to the client
func (c *WSConnection) sendResults(results interface{}) {
	data, err := json.Marshal(results)
	if err != nil {
		log.Printf("Error marshaling results: %v", err)
		return
	}

	c.mu.Lock()
	defer c.mu.Unlock()

	select {
	case c.send <- data:
	default:
		log.Println("WebSocket buffer full, dropping message")
	}
}

// sendError sends an error message to the client
func (c *WSConnection) sendError(message string) {
	response := map[string]string{"error": message}
	data, _ := json.Marshal(response)

	c.mu.Lock()
	defer c.mu.Unlock()

	select {
	case c.send <- data:
	default:
		log.Println("WebSocket buffer full, dropping error message")
	}
}
