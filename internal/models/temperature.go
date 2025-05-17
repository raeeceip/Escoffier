package models

import (
	"github.com/jinzhu/gorm"
)

// TemperatureMonitor represents a temperature monitoring configuration
type TemperatureMonitor struct {
	gorm.Model
	Current       float64 `gorm:"column:current_temp"`   // Current temperature in Celsius
	MinTemp       float64 `gorm:"column:min_temp"`       // Minimum acceptable temperature
	MaxTemp       float64 `gorm:"column:max_temp"`       // Maximum acceptable temperature
	CheckInterval int     `gorm:"column:check_interval"` // Interval between checks in seconds
	Unit          string  `gorm:"column:unit"`           // Temperature unit (e.g., "C" or "F")
}

// NewTemperature creates a new temperature monitoring configuration
func NewTemperature(min, max float64, interval int) *TemperatureMonitor {
	return &TemperatureMonitor{
		MinTemp:       min,
		MaxTemp:       max,
		CheckInterval: interval,
		Unit:          "C", // Default to Celsius
	}
}

// NewTemperatureFromCooking creates a Temperature from a CookingTemperature
func NewTemperatureFromCooking(ct *CookingTemperature) *TemperatureMonitor {
	// Default interval of 10 seconds for critical temperatures, 30 seconds otherwise
	interval := 30
	if ct.Critical {
		interval = 10
	}

	// Use the target temperature as both min and max if critical,
	// otherwise add a small tolerance range
	min := ct.Value
	max := ct.Value
	if !ct.Critical {
		tolerance := ct.Value * 0.05 // 5% tolerance
		min -= tolerance
		max += tolerance
	}

	return &TemperatureMonitor{
		MinTemp:       min,
		MaxTemp:       max,
		CheckInterval: interval,
		Unit:          ct.Unit,
	}
}

// SetCurrent updates the current temperature
func (t *TemperatureMonitor) SetCurrent(temp float64) {
	t.Current = temp
}

// IsWithinRange checks if the current temperature is within acceptable range
func (t *TemperatureMonitor) IsWithinRange() bool {
	return t.Current >= t.MinTemp && t.Current <= t.MaxTemp
}

// GetAdjustment calculates the needed temperature adjustment
func (t *TemperatureMonitor) GetAdjustment() float64 {
	if t.Current < t.MinTemp {
		return t.MinTemp - t.Current
	}
	if t.Current > t.MaxTemp {
		return t.MaxTemp - t.Current
	}
	return 0
}

// GetMin returns the minimum temperature
func (t *TemperatureMonitor) GetMin() float64 {
	return t.MinTemp
}

// GetMax returns the maximum temperature
func (t *TemperatureMonitor) GetMax() float64 {
	return t.MaxTemp
}

// GetInterval returns the check interval
func (t *TemperatureMonitor) GetInterval() int {
	return t.CheckInterval
}
