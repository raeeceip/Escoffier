package models

import (
	"github.com/jinzhu/gorm"
)

// Agent represents a kitchen agent
type Agent struct {
	gorm.Model
	Name        string
	Role        string
	State       string
	Status      string
	Permissions []string `gorm:"type:json"`
}

// AgentActionLog represents a log of agent actions
type AgentActionLog struct {
	gorm.Model
	AgentID   uint
	Action    string
	Timestamp string
	Status    string
	Details   string `gorm:"type:text"`
}

// EvaluationMetrics represents performance metrics
type EvaluationMetrics struct {
	gorm.Model
	AgentID     uint
	MetricName  string
	MetricValue float64
	Timestamp   string
}
