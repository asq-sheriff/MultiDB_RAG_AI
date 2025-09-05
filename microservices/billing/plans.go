package main

import (
	"github.com/shopspring/decimal"
)

// GetPlanDefinitions returns all available subscription plans
func GetPlanDefinitions() []PlanDefinition {
	return []PlanDefinition{
		{
			ID:   "free",
			Name: "Free Plan",
			Limits: map[string]int{
				"messages":         100,
				"background_tasks": 5,
				"api_calls":        50,
			},
			Features: []string{
				"Basic chat functionality",
				"Limited message history",
				"Standard support",
			},
			Pricing: map[string]decimal.Decimal{
				"monthly": decimal.NewFromFloat(0),
				"yearly":  decimal.NewFromFloat(0),
			},
		},
		{
			ID:   "basic",
			Name: "Basic Plan",
			Limits: map[string]int{
				"messages":         1000,
				"background_tasks": 25,
				"api_calls":        500,
			},
			Features: []string{
				"Enhanced chat functionality",
				"Extended message history",
				"Priority support",
				"Basic analytics",
			},
			Pricing: map[string]decimal.Decimal{
				"monthly": decimal.NewFromFloat(9.99),
				"yearly":  decimal.NewFromFloat(99.99),
			},
		},
		{
			ID:   "premium",
			Name: "Premium Plan",
			Limits: map[string]int{
				"messages":         5000,
				"background_tasks": 100,
				"api_calls":        2500,
			},
			Features: []string{
				"Advanced chat functionality",
				"Full message history",
				"Premium support",
				"Advanced analytics",
				"Custom integrations",
			},
			Pricing: map[string]decimal.Decimal{
				"monthly": decimal.NewFromFloat(29.99),
				"yearly":  decimal.NewFromFloat(299.99),
			},
		},
		{
			ID:   "enterprise",
			Name: "Enterprise Plan",
			Limits: map[string]int{
				"messages":         -1, // Unlimited
				"background_tasks": -1, // Unlimited
				"api_calls":        -1, // Unlimited
			},
			Features: []string{
				"All premium features",
				"Unlimited usage",
				"Dedicated support",
				"Custom development",
				"SLA guarantees",
				"On-premise deployment options",
			},
			Pricing: map[string]decimal.Decimal{
				"monthly": decimal.NewFromFloat(99.99),
				"yearly":  decimal.NewFromFloat(999.99),
			},
		},
	}
}

// GetPlanDefinition returns a specific plan definition by ID
func GetPlanDefinition(planID string) *PlanDefinition {
	plans := GetPlanDefinitions()
	for _, plan := range plans {
		if plan.ID == planID {
			return &plan
		}
	}
	return nil
}

// ValidatePlanType checks if a plan type is valid
func ValidatePlanType(planType string) bool {
	return GetPlanDefinition(planType) != nil
}

// GetPlanLimits returns the limits for a specific plan
func GetPlanLimits(planType string) map[string]int {
	plan := GetPlanDefinition(planType)
	if plan == nil {
		// Return free plan limits as default
		return GetPlanDefinition("free").Limits
	}
	return plan.Limits
}

// GetPlanFeatures returns the features for a specific plan
func GetPlanFeatures(planType string) []string {
	plan := GetPlanDefinition(planType)
	if plan == nil {
		// Return free plan features as default
		return GetPlanDefinition("free").Features
	}
	return plan.Features
}

// GetPlanPricing returns the pricing for a specific plan and billing cycle
func GetPlanPricing(planType, billingCycle string) decimal.Decimal {
	plan := GetPlanDefinition(planType)
	if plan == nil {
		return decimal.NewFromFloat(0)
	}
	
	if price, exists := plan.Pricing[billingCycle]; exists {
		return price
	}
	
	return decimal.NewFromFloat(0)
}