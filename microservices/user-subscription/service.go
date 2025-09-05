// Package main provides business logic for user subscription management
package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
)

// SubscriptionService handles all subscription-related business logic
type SubscriptionService struct {
	db  DatabaseInterface
	ctx context.Context
}

// NewSubscriptionService creates a new subscription service
func NewSubscriptionService(db DatabaseInterface) *SubscriptionService {
	return &SubscriptionService{
		db:  db,
		ctx: context.Background(),
	}
}

// CreateUserSubscription creates a new subscription for a user
func (s *SubscriptionService) CreateUserSubscription(userID uuid.UUID, planType SubscriptionPlan, billingCycle BillingCycle) (*Subscription, error) {
	// Check if user already has an active subscription
	existingSub, err := s.db.GetSubscriptionByUserID(userID)
	if err == nil && existingSub.IsActive() {
		return nil, fmt.Errorf("user already has an active subscription")
	}

	// Get plan features
	features := GetPlanFeatures(planType)

	// Calculate subscription period
	startTime := time.Now().UTC()
	var endTime *time.Time
	var nextBilling *time.Time

	if planType != PlanFree {
		switch billingCycle {
		case CycleMonthly:
			end := startTime.AddDate(0, 1, 0)
			endTime = &end
			nextBilling = &end
		case CycleYearly:
			end := startTime.AddDate(1, 0, 0)
			endTime = &end
			nextBilling = &end
		case CycleWeekly:
			end := startTime.AddDate(0, 0, 7)
			endTime = &end
			nextBilling = &end
		}
	}

	// Determine pricing
	var amountCents int
	if billingCycle == CycleYearly {
		amountCents = features.YearlyPriceCents
	} else {
		amountCents = features.MonthlyPriceCents
	}

	// Create subscription
	subscription := &Subscription{
		UserID:        userID,
		PlanType:      planType,
		Status:        StatusActive,
		BillingCycle:  billingCycle,
		StartedAt:     startTime,
		EndsAt:        endTime,
		AutoRenew:     true,
		AmountCents:   amountCents,
		Currency:      "USD",
		NextBillingAt: nextBilling,
	}

	// Set plan limits
	subscription.Limits = features.Limits

	// For free plans, set trial period
	if planType == PlanFree {
		subscription.Status = StatusActive
	}

	err = s.db.CreateSubscription(subscription)
	if err != nil {
		return nil, fmt.Errorf("failed to create subscription: %w", err)
	}

	log.Printf("Created subscription for user %s: plan=%s, cycle=%s", userID, planType, billingCycle)

	return subscription, nil
}

// UpgradeSubscription upgrades a user's subscription to a higher tier
func (s *SubscriptionService) UpgradeSubscription(userID uuid.UUID, newPlanType SubscriptionPlan, billingCycle BillingCycle) (*Subscription, error) {
	// Get current subscription
	currentSub, err := s.db.GetSubscriptionByUserID(userID)
	if err != nil {
		return nil, fmt.Errorf("no active subscription found for user")
	}

	// Validate upgrade path
	if !s.isValidUpgrade(currentSub.PlanType, newPlanType) {
		return nil, fmt.Errorf("invalid upgrade from %s to %s", currentSub.PlanType, newPlanType)
	}

	// Calculate prorated amount
	proratedAmount, err := s.calculateProratedAmount(currentSub, newPlanType, billingCycle)
	if err != nil {
		return nil, fmt.Errorf("failed to calculate prorated amount: %w", err)
	}

	// Update subscription
	newFeatures := GetPlanFeatures(newPlanType)
	currentSub.PlanType = newPlanType
	currentSub.BillingCycle = billingCycle
	currentSub.AmountCents = proratedAmount
	currentSub.Limits = newFeatures.Limits

	// Recalculate end date if changing billing cycle
	if billingCycle != currentSub.BillingCycle {
		now := time.Now().UTC()
		switch billingCycle {
		case CycleMonthly:
			end := now.AddDate(0, 1, 0)
			currentSub.EndsAt = &end
			currentSub.NextBillingAt = &end
		case CycleYearly:
			end := now.AddDate(1, 0, 0)
			currentSub.EndsAt = &end
			currentSub.NextBillingAt = &end
		}
	}

	err = s.db.UpdateSubscription(currentSub)
	if err != nil {
		return nil, fmt.Errorf("failed to update subscription: %w", err)
	}

	log.Printf("Upgraded subscription for user %s: %s -> %s", userID, currentSub.PlanType, newPlanType)

	return currentSub, nil
}

// DowngradeSubscription downgrades a user's subscription
func (s *SubscriptionService) DowngradeSubscription(userID uuid.UUID, newPlanType SubscriptionPlan) (*Subscription, error) {
	// Get current subscription
	currentSub, err := s.db.GetSubscriptionByUserID(userID)
	if err != nil {
		return nil, fmt.Errorf("no active subscription found for user")
	}

	// Validate downgrade
	if !s.isValidDowngrade(currentSub.PlanType, newPlanType) {
		return nil, fmt.Errorf("invalid downgrade from %s to %s", currentSub.PlanType, newPlanType)
	}

	// For downgrades, apply at next billing cycle to be fair
	now := time.Now().UTC()
	
	// Create pending downgrade event
	event := &SubscriptionEvent{
		SubscriptionID: currentSub.ID,
		UserID:         userID,
		EventType:      "downgrade_scheduled",
		OldPlan:        currentSub.PlanType,
		NewPlan:        newPlanType,
		Metadata: JSONMap{
			"effective_date": currentSub.EndsAt,
			"reason":         "user_requested",
		},
		CreatedAt: now,
	}
	
	s.db.CreateEvent(event)

	log.Printf("Scheduled downgrade for user %s: %s -> %s (effective %s)", 
		userID, currentSub.PlanType, newPlanType, currentSub.EndsAt.Format("2006-01-02"))

	return currentSub, nil
}

// CancelSubscription cancels a user's subscription
func (s *SubscriptionService) CancelSubscription(userID uuid.UUID, reason string) error {
	return s.db.CancelSubscription(userID, reason)
}

// ReactivateSubscription reactivates a canceled subscription
func (s *SubscriptionService) ReactivateSubscription(userID uuid.UUID) (*Subscription, error) {
	var subscription Subscription
	err := s.db.GetDB().Where("user_id = ? AND status = ?", userID, StatusCanceled).
		Order("created_at DESC").
		First(&subscription).Error
	
	if err != nil {
		return nil, fmt.Errorf("no canceled subscription found for user")
	}

	// Reactivate subscription
	now := time.Now().UTC()
	subscription.Status = StatusActive
	subscription.CanceledAt = nil
	subscription.AutoRenew = true
	
	// Extend end date by one billing cycle from now
	switch subscription.BillingCycle {
	case CycleMonthly:
		end := now.AddDate(0, 1, 0)
		subscription.EndsAt = &end
		subscription.NextBillingAt = &end
	case CycleYearly:
		end := now.AddDate(1, 0, 0)
		subscription.EndsAt = &end
		subscription.NextBillingAt = &end
	}

	err = s.db.UpdateSubscription(&subscription)
	if err != nil {
		return nil, fmt.Errorf("failed to reactivate subscription: %w", err)
	}

	log.Printf("Reactivated subscription for user %s", userID)

	return &subscription, nil
}

// PauseSubscription pauses a subscription temporarily
func (s *SubscriptionService) PauseSubscription(userID uuid.UUID, duration time.Duration) (*Subscription, error) {
	subscription, err := s.db.GetSubscriptionByUserID(userID)
	if err != nil {
		return nil, fmt.Errorf("no active subscription found for user")
	}

	if subscription.Status != StatusActive {
		return nil, fmt.Errorf("can only pause active subscriptions")
	}

	// Pause subscription
	now := time.Now().UTC()
	subscription.Status = StatusSuspended
	subscription.PausedAt = &now

	// Extend end date by pause duration
	if subscription.EndsAt != nil {
		newEndDate := subscription.EndsAt.Add(duration)
		subscription.EndsAt = &newEndDate
		subscription.NextBillingAt = &newEndDate
	}

	err = s.db.UpdateSubscription(subscription)
	if err != nil {
		return nil, fmt.Errorf("failed to pause subscription: %w", err)
	}

	log.Printf("Paused subscription for user %s for %s", userID, duration)

	return subscription, nil
}

// ResumeSubscription resumes a paused subscription
func (s *SubscriptionService) ResumeSubscription(userID uuid.UUID) (*Subscription, error) {
	subscription, err := s.db.GetSubscriptionByUserID(userID)
	if err != nil {
		return nil, fmt.Errorf("no subscription found for user")
	}

	if subscription.Status != StatusSuspended {
		return nil, fmt.Errorf("can only resume suspended subscriptions")
	}

	// Resume subscription
	now := time.Now().UTC()
	subscription.Status = StatusActive
	subscription.ResumedAt = &now
	subscription.PausedAt = nil

	err = s.db.UpdateSubscription(subscription)
	if err != nil {
		return nil, fmt.Errorf("failed to resume subscription: %w", err)
	}

	log.Printf("Resumed subscription for user %s", userID)

	return subscription, nil
}

// CheckAndRecordUsage checks quota and records usage for a resource
func (s *SubscriptionService) CheckAndRecordUsage(userID uuid.UUID, resourceType ResourceType, quantity int, metadata map[string]interface{}) (*QuotaInfo, error) {
	// Check current quota
	quota, err := s.db.CheckUserQuota(userID, resourceType)
	if err != nil {
		return nil, fmt.Errorf("failed to check quota: %w", err)
	}

	// Check if user has enough quota
	if !quota.HasQuota && quantity > 0 {
		// For enterprise customers, allow overage
		if quota.PlanType == string(PlanEnterprise) {
			quota.OverageAllowed = true
		} else {
			return quota, fmt.Errorf("quota exceeded for resource %s", resourceType)
		}
	}

	// Record usage
	err = s.db.RecordUsage(userID, resourceType, quantity, metadata)
	if err != nil {
		return nil, fmt.Errorf("failed to record usage: %w", err)
	}

	// Return updated quota
	return s.db.CheckUserQuota(userID, resourceType)
}

// GetUserSubscription returns a user's current subscription
func (s *SubscriptionService) GetUserSubscription(userID uuid.UUID) (*Subscription, error) {
	return s.db.GetSubscriptionByUserID(userID)
}

// GetUsageSummary returns usage summary for a user
func (s *SubscriptionService) GetUsageSummary(userID uuid.UUID, days int) (map[string]interface{}, error) {
	return s.db.GetUsageSummary(userID, days)
}

// ListAvailablePlans returns all available subscription plans
func (s *SubscriptionService) ListAvailablePlans() []PlanFeatures {
	return []PlanFeatures{
		GetPlanFeatures(PlanFree),
		GetPlanFeatures(PlanPro),
		GetPlanFeatures(PlanEnterprise),
	}
}

// ProcessSubscriptionRenewals processes subscription renewals
func (s *SubscriptionService) ProcessSubscriptionRenewals() error {
	now := time.Now().UTC()
	
	// Find subscriptions that need renewal
	var subscriptions []Subscription
	err := s.db.GetDB().Where("auto_renew = ? AND status = ? AND next_billing_at <= ?", 
		true, StatusActive, now).Find(&subscriptions).Error
	
	if err != nil {
		return fmt.Errorf("failed to find subscriptions for renewal: %w", err)
	}

	for _, subscription := range subscriptions {
		err := s.renewSubscription(&subscription)
		if err != nil {
			log.Printf("Failed to renew subscription %s: %v", subscription.ID, err)
		}
	}

	return nil
}

// ProcessExpiredSubscriptions processes expired subscriptions
func (s *SubscriptionService) ProcessExpiredSubscriptions() error {
	now := time.Now().UTC()
	
	// Find expired subscriptions
	var subscriptions []Subscription
	err := s.db.GetDB().Where("status = ? AND ends_at <= ?", StatusActive, now).Find(&subscriptions).Error
	
	if err != nil {
		return fmt.Errorf("failed to find expired subscriptions: %w", err)
	}

	for _, subscription := range subscriptions {
		if !subscription.AutoRenew {
			// Mark as expired
			subscription.Status = StatusExpired
			s.db.UpdateSubscription(&subscription)
			log.Printf("Expired subscription %s for user %s", subscription.ID, subscription.UserID)
		}
	}

	return nil
}

// Private helper methods

func (s *SubscriptionService) isValidUpgrade(currentPlan, newPlan SubscriptionPlan) bool {
	upgradeMatrix := map[SubscriptionPlan][]SubscriptionPlan{
		PlanFree:       {PlanPro, PlanEnterprise},
		PlanPro:        {PlanEnterprise},
		PlanEnterprise: {}, // No upgrades from enterprise
	}
	
	validUpgrades := upgradeMatrix[currentPlan]
	for _, validPlan := range validUpgrades {
		if validPlan == newPlan {
			return true
		}
	}
	
	return false
}

func (s *SubscriptionService) isValidDowngrade(currentPlan, newPlan SubscriptionPlan) bool {
	downgradeMatrix := map[SubscriptionPlan][]SubscriptionPlan{
		PlanFree:       {}, // No downgrades from free
		PlanPro:        {PlanFree},
		PlanEnterprise: {PlanFree, PlanPro},
	}
	
	validDowngrades := downgradeMatrix[currentPlan]
	for _, validPlan := range validDowngrades {
		if validPlan == newPlan {
			return true
		}
	}
	
	return false
}

func (s *SubscriptionService) calculateProratedAmount(currentSub *Subscription, newPlan SubscriptionPlan, billingCycle BillingCycle) (int, error) {
	newFeatures := GetPlanFeatures(newPlan)
	
	// Calculate new amount based on billing cycle
	var newAmount int
	if billingCycle == CycleYearly {
		newAmount = newFeatures.YearlyPriceCents
	} else {
		newAmount = newFeatures.MonthlyPriceCents
	}

	// For simplicity, return full amount for upgrades
	// In production, you'd calculate prorated amount based on remaining time
	return newAmount, nil
}

func (s *SubscriptionService) renewSubscription(subscription *Subscription) error {
	// Calculate next billing period
	var nextBilling time.Time
	var endTime time.Time

	switch subscription.BillingCycle {
	case CycleMonthly:
		nextBilling = subscription.NextBillingAt.AddDate(0, 1, 0)
		endTime = nextBilling
	case CycleYearly:
		nextBilling = subscription.NextBillingAt.AddDate(1, 0, 0)
		endTime = nextBilling
	case CycleWeekly:
		nextBilling = subscription.NextBillingAt.AddDate(0, 0, 7)
		endTime = nextBilling
	}

	// Update subscription
	subscription.NextBillingAt = &nextBilling
	subscription.EndsAt = &endTime

	err := s.db.UpdateSubscription(subscription)
	if err != nil {
		return fmt.Errorf("failed to update subscription: %w", err)
	}

	log.Printf("Renewed subscription %s for user %s", subscription.ID, subscription.UserID)

	return nil
}

// ValidateSubscriptionAccess checks if a user has access to a feature based on their subscription
func (s *SubscriptionService) ValidateSubscriptionAccess(userID uuid.UUID, feature string) (bool, error) {
	subscription, err := s.db.GetSubscriptionByUserID(userID)
	if err != nil {
		return false, err
	}

	if !subscription.IsActive() {
		return false, fmt.Errorf("subscription is not active")
	}

	features := GetPlanFeatures(subscription.PlanType)
	
	// Check feature access based on plan
	switch feature {
	case "advanced_features":
		return features.AdvancedFeatures, nil
	case "priority_support":
		return features.PrioritySupport, nil
	case "custom_integrations":
		return features.CustomIntegrations, nil
	case "multi_user_access":
		return features.MultiUserAccess, nil
	case "advanced_analytics":
		return features.AdvancedAnalytics, nil
	case "dedicated_support":
		return features.DedicatedSupport, nil
	default:
		return false, fmt.Errorf("unknown feature: %s", feature)
	}
}

// GetSubscriptionMetrics returns metrics about subscriptions
func (s *SubscriptionService) GetSubscriptionMetrics() (map[string]interface{}, error) {
	var metrics struct {
		TotalSubscriptions int64 `json:"total_subscriptions"`
		ActiveSubscriptions int64 `json:"active_subscriptions"`
		FreeSubscriptions int64 `json:"free_subscriptions"`
		ProSubscriptions int64 `json:"pro_subscriptions"`
		EnterpriseSubscriptions int64 `json:"enterprise_subscriptions"`
		CanceledSubscriptions int64 `json:"canceled_subscriptions"`
		MonthlyRevenue int64 `json:"monthly_revenue_cents"`
		YearlyRevenue int64 `json:"yearly_revenue_cents"`
	}

	// Get subscription counts
	s.db.GetDB().Model(&Subscription{}).Count(&metrics.TotalSubscriptions)
	s.db.GetDB().Model(&Subscription{}).Where("status = ?", StatusActive).Count(&metrics.ActiveSubscriptions)
	s.db.GetDB().Model(&Subscription{}).Where("plan_type = ?", PlanFree).Count(&metrics.FreeSubscriptions)
	s.db.GetDB().Model(&Subscription{}).Where("plan_type = ?", PlanPro).Count(&metrics.ProSubscriptions)
	s.db.GetDB().Model(&Subscription{}).Where("plan_type = ?", PlanEnterprise).Count(&metrics.EnterpriseSubscriptions)
	s.db.GetDB().Model(&Subscription{}).Where("status = ?", StatusCanceled).Count(&metrics.CanceledSubscriptions)

	// Calculate revenue (this is a simplified calculation)
	var monthlyRevenue, yearlyRevenue int64
	s.db.GetDB().Model(&Subscription{}).
		Where("status = ? AND billing_cycle = ?", StatusActive, CycleMonthly).
		Select("COALESCE(SUM(amount_cents), 0)").Scan(&monthlyRevenue)
	
	s.db.GetDB().Model(&Subscription{}).
		Where("status = ? AND billing_cycle = ?", StatusActive, CycleYearly).
		Select("COALESCE(SUM(amount_cents), 0)").Scan(&yearlyRevenue)

	metrics.MonthlyRevenue = monthlyRevenue
	metrics.YearlyRevenue = yearlyRevenue

	return map[string]interface{}{
		"subscription_metrics": metrics,
		"timestamp": time.Now().UTC(),
	}, nil
}