package evaluation

import (
	"time"

	"escoffier/internal/models"
)

// Agent represents an agent being evaluated
type Agent struct {
	ID          string
	Role        string
	Memory      *Memory
	TaskQueue   []Task
	Performance map[string]float64
}

// Memory represents an agent's memory system
type Memory struct {
	ShortTerm []Event
	LongTerm  *VectorStore
	TaskQueue []Task
}

// Event represents a recorded event in the agent's memory
type Event struct {
	Timestamp time.Time
	Type      string
	Content   string
	Metadata  map[string]interface{}
}

// Task represents a task assigned to an agent
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

// Order represents a kitchen order being evaluated
type Order struct {
	ID            string
	Type          string
	Complexity    int
	TimeReceived  time.Time
	TimeCompleted time.Time
	Items         []models.MenuItem
	Status        string
}

// VectorStore represents a store for vector embeddings
type VectorStore struct {
	embeddings map[string][]float32
	metadata   map[string]interface{}
}

// Scenario represents an evaluation scenario
type Scenario struct {
	ID          string
	Name        string
	Description string
	Duration    time.Duration
	Difficulty  int
	Tasks       []Task
	Metrics     map[string]float64
}

// NewVectorStore creates a new vector store
func NewVectorStore() *VectorStore {
	return &VectorStore{
		embeddings: make(map[string][]float32),
		metadata:   make(map[string]interface{}),
	}
}

// NewAgent creates a new agent for evaluation
func NewAgent(id, role string) *Agent {
	return &Agent{
		ID:   id,
		Role: role,
		Memory: &Memory{
			ShortTerm: make([]Event, 0),
			LongTerm:  NewVectorStore(),
			TaskQueue: make([]Task, 0),
		},
		TaskQueue:   make([]Task, 0),
		Performance: make(map[string]float64),
	}
}

// NewScenario creates a new evaluation scenario
func NewScenario(id, name string, duration time.Duration) *Scenario {
	return &Scenario{
		ID:       id,
		Name:     name,
		Duration: duration,
		Tasks:    make([]Task, 0),
		Metrics:  make(map[string]float64),
	}
}
