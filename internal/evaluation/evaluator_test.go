package evaluation

import (
	"testing"
)

func TestNewEvaluator(t *testing.T) {
	evaluator := NewEvaluator()

	if evaluator == nil {
		t.Fatal("NewEvaluator() returned nil")
	}

	if len(evaluator.scenarios) == 0 {
		t.Error("NewEvaluator() created an evaluator with no scenarios")
	}
}

func TestHasScenario(t *testing.T) {
	evaluator := NewEvaluator()

	// Test existing scenarios
	existingScenarios := []string{
		"busy_night",
		"overstocked",
		"slow_business",
		"low_inventory",
		"high_labor",
		"quality_control",
	}

	for _, scenario := range existingScenarios {
		if !evaluator.HasScenario(scenario) {
			t.Errorf("HasScenario(%q) = false, want true", scenario)
		}
	}

	// Test non-existing scenario
	if evaluator.HasScenario("non_existent_scenario") {
		t.Error("HasScenario(\"non_existent_scenario\") = true, want false")
	}
}

func TestEvaluateModel(t *testing.T) {
	evaluator := NewEvaluator()

	// Test with valid scenario
	result := evaluator.EvaluateModel("test_model", "busy_night")

	if result == nil {
		t.Fatal("EvaluateModel() returned nil for valid scenario")
	}

	if result.Model != "test_model" {
		t.Errorf("EvaluateModel() result.Model = %q, want %q", result.Model, "test_model")
	}

	if result.Scenario != "busy_night" {
		t.Errorf("EvaluateModel() result.Scenario = %q, want %q", result.Scenario, "busy_night")
	}

	if len(result.Metrics) == 0 {
		t.Error("EvaluateModel() returned no metrics")
	}

	if len(result.Events) == 0 {
		t.Error("EvaluateModel() returned no events")
	}

	// Test with invalid scenario
	result = evaluator.EvaluateModel("test_model", "non_existent_scenario")
	if result != nil {
		t.Error("EvaluateModel() returned non-nil result for invalid scenario")
	}
}
