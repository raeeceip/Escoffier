package agents

import (
	"context"
	"fmt"
	"hash/fnv"
	"math"
	"math/rand"
	"sort"
	"strings"
	"time"

	"github.com/tmc/langchaingo/llms"
)

// AgentRole represents the role of an agent in the kitchen
type AgentRole string

const (
	RoleExecutiveChef AgentRole = "executive_chef"
	RoleSousChef      AgentRole = "sous_chef"
	RoleChefDePartie  AgentRole = "chef_de_partie"
	RoleLineCook      AgentRole = "line_cook"
	RolePrepCook      AgentRole = "prep_cook"
	RoleKitchenPorter AgentRole = "kitchen_porter"
)

// Agent represents the base interface for all kitchen agents
type Agent interface {
	GetRole() AgentRole
	GetModel() llms.LLM
	GetMemory() *Memory
	GetPermissions() []string
	HandleTask(ctx context.Context, task Task) error
	AddMemory(ctx context.Context, event Event) error
	QueryMemory(ctx context.Context, query string, k int) ([]Event, error)
}

// BaseAgent provides common functionality for all agents
type BaseAgent struct {
	ID          uint
	role        AgentRole
	model       llms.LLM
	memory      *Memory
	permissions []string
}

// Memory represents the agent's memory system
type Memory struct {
	ShortTerm []Event
	LongTerm  *VectorStore
	TaskQueue []Task
}

// Event represents a single event in the agent's memory
type Event struct {
	Timestamp time.Time
	Type      string
	Content   string
	Metadata  map[string]interface{}
}

// Task represents a single task in the agent's queue
type Task struct {
	ID           string
	Type         string
	Description  string
	Priority     int
	Status       string
	StartTime    time.Time
	EndTime      time.Time
	Dependencies []string
	Metadata     map[string]interface{}
}

// VectorStore represents the interface for vector storage
type VectorStore struct {
	embeddings map[string][]float32
	metadata   map[string]interface{}
}

// NewBaseAgent creates a new base agent with the specified role and model
func NewBaseAgent(role AgentRole, model llms.LLM) *BaseAgent {
	return &BaseAgent{
		role:  role,
		model: model,
		memory: &Memory{
			ShortTerm: make([]Event, 0),
			LongTerm:  NewVectorStore(),
			TaskQueue: make([]Task, 0),
		},
		permissions: make([]string, 0),
	}
}

// NewVectorStore creates a new vector store for long-term memory
func NewVectorStore() *VectorStore {
	return &VectorStore{
		embeddings: make(map[string][]float32),
		metadata:   make(map[string]interface{}),
	}
}

// GetRole returns the agent's role
func (a *BaseAgent) GetRole() AgentRole {
	return a.role
}

// GetModel returns the agent's LLM model
func (a *BaseAgent) GetModel() llms.LLM {
	return a.model
}

// GetMemory returns the agent's memory system
func (a *BaseAgent) GetMemory() *Memory {
	return a.memory
}

// GetPermissions returns the agent's permissions
func (a *BaseAgent) GetPermissions() []string {
	return a.permissions
}

// AddMemory adds a new memory event to both short-term and long-term storage
func (a *BaseAgent) AddMemory(ctx context.Context, event Event) error {
	// Add to short-term memory
	a.memory.ShortTerm = append(a.memory.ShortTerm, event)

	// Add to long-term memory if significant
	if isSignificant(event) {
		return a.memory.LongTerm.Add(ctx, event)
	}

	return nil
}

// QueryMemory searches for similar memories in the vector store
func (a *BaseAgent) QueryMemory(ctx context.Context, query string, k int) ([]Event, error) {
	return a.memory.LongTerm.Query(ctx, query, k)
}

// Add adds a new memory to the vector store
func (vs *VectorStore) Add(ctx context.Context, event Event) error {
	// Generate a unique key for the event
	key := fmt.Sprintf("%s-%d", event.Type, event.Timestamp.UnixNano())

	// Convert event content to vector embedding
	embedding, err := generateEmbedding(event.Content)
	if err != nil {
		return fmt.Errorf("failed to generate embedding: %w", err)
	}

	// Store the embedding and metadata
	vs.embeddings[key] = embedding
	vs.metadata[key] = event

	return nil
}

// Query searches for similar memories in the vector store
func (vs *VectorStore) Query(ctx context.Context, query string, k int) ([]Event, error) {
	// Generate embedding for the query
	queryEmbedding, err := generateEmbedding(query)
	if err != nil {
		return nil, fmt.Errorf("failed to generate query embedding: %w", err)
	}

	// Calculate similarities and find top k matches
	type similarity struct {
		key   string
		score float32
	}
	similarities := make([]similarity, 0, len(vs.embeddings))

	for key, embedding := range vs.embeddings {
		score := cosineSimilarity(queryEmbedding, embedding)
		similarities = append(similarities, similarity{key, score})
	}

	// Sort by similarity score
	sort.Slice(similarities, func(i, j int) bool {
		return similarities[i].score > similarities[j].score
	})

	// Get top k results
	n := min(k, len(similarities))
	results := make([]Event, n)
	for i := 0; i < n; i++ {
		key := similarities[i].key
		results[i] = vs.metadata[key].(Event)
	}

	return results, nil
}

// isSignificant determines if an event should be stored in long-term memory
func isSignificant(event Event) bool {
	// Events are considered significant if they:
	// 1. Involve critical state changes
	criticalTypes := map[string]bool{
		"error":           true,
		"task_completion": true,
		"order_status":    true,
		"equipment_issue": true,
		"safety_concern":  true,
	}
	if criticalTypes[event.Type] {
		return true
	}

	// 2. Have high priority metadata
	if priority, ok := event.Metadata["priority"].(int); ok && priority >= 8 {
		return true
	}

	// 3. Are marked as important
	if important, ok := event.Metadata["important"].(bool); ok && important {
		return true
	}

	// 4. Contain specific keywords
	significantKeywords := []string{
		"urgent", "critical", "emergency", "failure", "success",
		"completed", "error", "warning", "alert",
	}
	for _, keyword := range significantKeywords {
		if strings.Contains(strings.ToLower(event.Content), keyword) {
			return true
		}
	}

	return false
}

// Helper functions for vector operations

func generateEmbedding(text string) ([]float32, error) {
	// For now, using a simple word2vec-style approach
	// In production, this should use a proper embedding model
	words := strings.Fields(strings.ToLower(text))
	embedding := make([]float32, 100) // Using 100-dimensional embeddings

	for _, word := range words {
		// Generate pseudo-random but deterministic values based on the word
		h := fnv.New32a()
		h.Write([]byte(word))
		seed := h.Sum32()
		rand.Seed(int64(seed))

		for i := range embedding {
			embedding[i] += rand.Float32()*2 - 1
		}
	}

	// Normalize the embedding
	normalize(embedding)
	return embedding, nil
}

func cosineSimilarity(a, b []float32) float32 {
	if len(a) != len(b) {
		return 0
	}

	var dotProduct float32
	var normA float32
	var normB float32

	for i := range a {
		dotProduct += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}

	if normA == 0 || normB == 0 {
		return 0
	}

	return dotProduct / float32(math.Sqrt(float64(normA)*float64(normB)))
}

func normalize(v []float32) {
	var norm float32
	for _, x := range v {
		norm += x * x
	}
	norm = float32(math.Sqrt(float64(norm)))

	if norm != 0 {
		for i := range v {
			v[i] /= norm
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// AddTask adds a new task to the agent's task queue
func (a *BaseAgent) AddTask(task Task) {
	a.memory.TaskQueue = append(a.memory.TaskQueue, task)
}

// GetNextTask returns the next task to be executed
func (a *BaseAgent) GetNextTask() *Task {
	if len(a.memory.TaskQueue) == 0 {
		return nil
	}

	// Get highest priority task
	var nextTask *Task
	highestPriority := -1

	for i, task := range a.memory.TaskQueue {
		if task.Status == "pending" && task.Priority > highestPriority {
			highestPriority = task.Priority
			nextTask = &a.memory.TaskQueue[i]
		}
	}

	return nextTask
}

// HasPermission checks if the agent has a specific permission
func (a *BaseAgent) HasPermission(permission string) bool {
	for _, p := range a.permissions {
		if p == permission {
			return true
		}
	}
	return false
}
