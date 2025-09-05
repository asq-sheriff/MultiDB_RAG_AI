// Package main provides user subscription service models for multi-database healthcare platform
package main

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

// SubscriptionPlan represents the available subscription tiers
type SubscriptionPlan string

const (
	PlanFree       SubscriptionPlan = "free"
	PlanPro        SubscriptionPlan = "pro"
	PlanEnterprise SubscriptionPlan = "enterprise"
)

// SubscriptionStatus represents the current status of a subscription
type SubscriptionStatus string

const (
	StatusActive    SubscriptionStatus = "active"
	StatusInactive  SubscriptionStatus = "inactive"
	StatusCanceled  SubscriptionStatus = "canceled"
	StatusExpired   SubscriptionStatus = "expired"
	StatusSuspended SubscriptionStatus = "suspended"
	StatusTrialing  SubscriptionStatus = "trialing"
)

// BillingCycle represents how frequently billing occurs
type BillingCycle string

const (
	CycleMonthly BillingCycle = "monthly"
	CycleYearly  BillingCycle = "yearly"
	CycleWeekly  BillingCycle = "weekly"
)

// ResourceType represents different types of resources that can be limited
type ResourceType string

const (
	ResourceMessages        ResourceType = "messages"
	ResourceAPICalls        ResourceType = "api_calls"
	ResourceBackgroundTasks ResourceType = "background_tasks"
	ResourceStorage         ResourceType = "storage"
	ResourceUsers           ResourceType = "users"
	ResourceRAGSearches     ResourceType = "rag_searches"
	ResourceEmbeddings      ResourceType = "embeddings"
)

// JSONMap is a custom type for storing JSON data in PostgreSQL
type JSONMap map[string]interface{}

// Value implements driver.Valuer for database storage
func (j JSONMap) Value() (driver.Value, error) {
	return json.Marshal(j)
}

// Scan implements sql.Scanner for database retrieval
func (j *JSONMap) Scan(value interface{}) error {
	if value == nil {
		*j = make(JSONMap)
		return nil
	}

	bytes, ok := value.([]byte)
	if !ok {
		return fmt.Errorf("cannot scan %T into JSONMap", value)
	}

	return json.Unmarshal(bytes, j)
}

// Subscription represents a user's subscription in PostgreSQL
type Subscription struct {
	ID             uuid.UUID          `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	UserID         uuid.UUID          `gorm:"type:uuid;not null;index" json:"user_id"`
	PlanType       SubscriptionPlan   `gorm:"type:varchar(20);not null;index" json:"plan_type"`
	Status         SubscriptionStatus `gorm:"type:varchar(20);not null;index" json:"status"`
	BillingCycle   BillingCycle       `gorm:"type:varchar(20);not null" json:"billing_cycle"`
	StartedAt      time.Time          `gorm:"not null" json:"started_at"`
	EndsAt         *time.Time         `json:"ends_at"`
	AutoRenew      bool               `gorm:"default:true" json:"auto_renew"`
	Limits         JSONMap            `gorm:"type:jsonb" json:"limits"`
	AmountCents    int                `gorm:"not null" json:"amount_cents"`
	Currency       string             `gorm:"type:varchar(3);default:'USD'" json:"currency"`
	StripeID       string             `gorm:"type:varchar(255);index" json:"stripe_id,omitempty"`
	TrialEndsAt    *time.Time         `json:"trial_ends_at"`
	CanceledAt     *time.Time         `json:"canceled_at"`
	PausedAt       *time.Time         `json:"paused_at"`
	ResumedAt      *time.Time         `json:"resumed_at"`
	NextBillingAt  *time.Time         `json:"next_billing_at"`
	CreatedAt      time.Time          `gorm:"default:CURRENT_TIMESTAMP" json:"created_at"`
	UpdatedAt      time.Time          `gorm:"default:CURRENT_TIMESTAMP" json:"updated_at"`
	DeletedAt      gorm.DeletedAt     `gorm:"index" json:"deleted_at,omitempty"`
}

// TableName specifies the table name for GORM
func (Subscription) TableName() string {
	return "subscriptions"
}

// GetLimit returns the limit for a specific resource type
func (s *Subscription) GetLimit(resourceType ResourceType) int {
	if s.Limits == nil {
		return 0
	}
	
	if limit, exists := s.Limits[string(resourceType)]; exists {
		if limitInt, ok := limit.(float64); ok {
			return int(limitInt)
		}
	}
	
	// Return default limits based on plan
	return GetPlanDefaults(s.PlanType)[string(resourceType)]
}

// IsActive checks if subscription is currently active
func (s *Subscription) IsActive() bool {
	now := time.Now()
	
	// Check status
	if s.Status != StatusActive && s.Status != StatusTrialing {
		return false
	}
	
	// Check expiration
	if s.EndsAt != nil && s.EndsAt.Before(now) {
		return false
	}
	
	// Check trial period
	if s.Status == StatusTrialing && s.TrialEndsAt != nil && s.TrialEndsAt.Before(now) {
		return false
	}
	
	return true
}

// DaysUntilExpiry returns days until subscription expires
func (s *Subscription) DaysUntilExpiry() *int {
	if s.EndsAt == nil {
		return nil
	}
	
	days := int(time.Until(*s.EndsAt).Hours() / 24)
	return &days
}

// Usage represents usage tracking for a user's subscription
type Usage struct {
	ID           uuid.UUID    `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	UserID       uuid.UUID    `gorm:"type:uuid;not null;index" json:"user_id"`
	ResourceType ResourceType `gorm:"type:varchar(50);not null;index" json:"resource_type"`
	Quantity     int          `gorm:"not null" json:"quantity"`
	PeriodStart  time.Time    `gorm:"not null;index" json:"period_start"`
	PeriodEnd    time.Time    `gorm:"not null;index" json:"period_end"`
	Metadata     JSONMap      `gorm:"type:jsonb" json:"metadata"`
	RecordedAt   time.Time    `gorm:"default:CURRENT_TIMESTAMP" json:"recorded_at"`
	CreatedAt    time.Time    `gorm:"default:CURRENT_TIMESTAMP" json:"created_at"`
}

// TableName specifies the table name for GORM
func (Usage) TableName() string {
	return "usage_records"
}

// QuotaInfo represents current quota information for a user
type QuotaInfo struct {
	UserID         uuid.UUID    `json:"user_id"`
	ResourceType   ResourceType `json:"resource_type"`
	CurrentUsage   int          `json:"current_usage"`
	MaxAllowed     int          `json:"max_allowed"`
	Remaining      int          `json:"remaining"`
	HasQuota       bool         `json:"has_quota"`
	PeriodStart    time.Time    `json:"period_start"`
	PeriodEnd      time.Time    `json:"period_end"`
	ResetAt        time.Time    `json:"reset_at"`
	PlanType       string       `json:"plan_type"`
	OverageAllowed bool         `json:"overage_allowed"`
	OverageCost    int          `json:"overage_cost_cents"`
}

// SubscriptionEvent represents events in the subscription lifecycle
type SubscriptionEvent struct {
	ID             uuid.UUID          `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	SubscriptionID uuid.UUID          `gorm:"type:uuid;not null;index" json:"subscription_id"`
	UserID         uuid.UUID          `gorm:"type:uuid;not null;index" json:"user_id"`
	EventType      string             `gorm:"type:varchar(50);not null" json:"event_type"`
	OldStatus      SubscriptionStatus `gorm:"type:varchar(20)" json:"old_status,omitempty"`
	NewStatus      SubscriptionStatus `gorm:"type:varchar(20)" json:"new_status,omitempty"`
	OldPlan        SubscriptionPlan   `gorm:"type:varchar(20)" json:"old_plan,omitempty"`
	NewPlan        SubscriptionPlan   `gorm:"type:varchar(20)" json:"new_plan,omitempty"`
	Metadata       JSONMap            `gorm:"type:jsonb" json:"metadata"`
	ProcessedAt    *time.Time         `json:"processed_at"`
	CreatedAt      time.Time          `gorm:"default:CURRENT_TIMESTAMP" json:"created_at"`
}

// TableName specifies the table name for GORM
func (SubscriptionEvent) TableName() string {
	return "subscription_events"
}

// PlanFeatures represents features available to each plan
type PlanFeatures struct {
	Plan                SubscriptionPlan `json:"plan"`
	DisplayName         string           `json:"display_name"`
	Description         string           `json:"description"`
	MonthlyPriceCents   int              `json:"monthly_price_cents"`
	YearlyPriceCents    int              `json:"yearly_price_cents"`
	Features            []string         `json:"features"`
	Limits              JSONMap          `json:"limits"`
	AdvancedFeatures    bool             `json:"advanced_features"`
	PrioritySupport     bool             `json:"priority_support"`
	CustomIntegrations  bool             `json:"custom_integrations"`
	MultiUserAccess     bool             `json:"multi_user_access"`
	AdvancedAnalytics   bool             `json:"advanced_analytics"`
	APIRateLimit        int              `json:"api_rate_limit"`
	StorageGB           int              `json:"storage_gb"`
	MaxTeamMembers      int              `json:"max_team_members"`
	SLAGuarantee        string           `json:"sla_guarantee"`
	DedicatedSupport    bool             `json:"dedicated_support"`
}

// GetPlanDefaults returns default resource limits for each plan
func GetPlanDefaults(plan SubscriptionPlan) map[string]int {
	switch plan {
	case PlanFree:
		return map[string]int{
			string(ResourceMessages):        100,
			string(ResourceAPICalls):        500,
			string(ResourceBackgroundTasks): 10,
			string(ResourceStorage):         1024, // 1GB in MB
			string(ResourceUsers):           1,
			string(ResourceRAGSearches):     50,
			string(ResourceEmbeddings):      100,
		}
	case PlanPro:
		return map[string]int{
			string(ResourceMessages):        5000,
			string(ResourceAPICalls):        10000,
			string(ResourceBackgroundTasks): 100,
			string(ResourceStorage):         10240, // 10GB in MB
			string(ResourceUsers):           5,
			string(ResourceRAGSearches):     1000,
			string(ResourceEmbeddings):      2500,
		}
	case PlanEnterprise:
		return map[string]int{
			string(ResourceMessages):        50000,
			string(ResourceAPICalls):        100000,
			string(ResourceBackgroundTasks): 1000,
			string(ResourceStorage):         102400, // 100GB in MB
			string(ResourceUsers):           50,
			string(ResourceRAGSearches):     10000,
			string(ResourceEmbeddings):      25000,
		}
	default:
		return GetPlanDefaults(PlanFree)
	}
}

// GetPlanFeatures returns complete feature set for a plan
func GetPlanFeatures(plan SubscriptionPlan) PlanFeatures {
	limits := GetPlanDefaults(plan)
	jsonLimits := make(JSONMap)
	for k, v := range limits {
		jsonLimits[k] = v
	}

	switch plan {
	case PlanFree:
		return PlanFeatures{
			Plan:                plan,
			DisplayName:         "Free Tier",
			Description:         "Perfect for trying out our therapeutic AI platform",
			MonthlyPriceCents:   0,
			YearlyPriceCents:    0,
			Features: []string{
				"Basic therapeutic chat",
				"Emotion analysis",
				"Safety monitoring",
				"Basic knowledge base access",
				"Community support",
			},
			Limits:              jsonLimits,
			AdvancedFeatures:    false,
			PrioritySupport:     false,
			CustomIntegrations:  false,
			MultiUserAccess:     false,
			AdvancedAnalytics:   false,
			APIRateLimit:        10, // requests per minute
			StorageGB:           1,
			MaxTeamMembers:      1,
			SLAGuarantee:        "Best effort",
			DedicatedSupport:    false,
		}
	case PlanPro:
		return PlanFeatures{
			Plan:                plan,
			DisplayName:         "Professional",
			Description:         "Advanced therapeutic AI for healthcare professionals",
			MonthlyPriceCents:   4999, // $49.99
			YearlyPriceCents:    47988, // $479.88 (20% discount)
			Features: []string{
				"Advanced therapeutic chat",
				"Comprehensive emotion analysis",
				"Crisis intervention protocols",
				"RAG-enhanced knowledge base",
				"Custom therapeutic protocols",
				"Advanced safety filtering",
				"Progress tracking",
				"Email support",
				"Basic integrations",
			},
			Limits:              jsonLimits,
			AdvancedFeatures:    true,
			PrioritySupport:     true,
			CustomIntegrations:  true,
			MultiUserAccess:     true,
			AdvancedAnalytics:   true,
			APIRateLimit:        100, // requests per minute
			StorageGB:           10,
			MaxTeamMembers:      5,
			SLAGuarantee:        "99.5% uptime",
			DedicatedSupport:    false,
		}
	case PlanEnterprise:
		return PlanFeatures{
			Plan:                plan,
			DisplayName:         "Enterprise",
			Description:         "Full-scale therapeutic AI for healthcare organizations",
			MonthlyPriceCents:   19999, // $199.99
			YearlyPriceCents:    191988, // $1919.88 (20% discount)
			Features: []string{
				"Enterprise therapeutic AI platform",
				"Advanced crisis management",
				"Multi-tenant architecture",
				"Custom model training",
				"HIPAA compliance reporting",
				"Advanced audit trails",
				"Custom integrations",
				"Dedicated account manager",
				"24/7 phone support",
				"Custom SLAs",
				"Advanced analytics & reporting",
				"White-label options",
			},
			Limits:              jsonLimits,
			AdvancedFeatures:    true,
			PrioritySupport:     true,
			CustomIntegrations:  true,
			MultiUserAccess:     true,
			AdvancedAnalytics:   true,
			APIRateLimit:        1000, // requests per minute
			StorageGB:           100,
			MaxTeamMembers:      50,
			SLAGuarantee:        "99.9% uptime with dedicated support",
			DedicatedSupport:    true,
		}
	default:
		return GetPlanFeatures(PlanFree)
	}
}

// RedisUsageKey represents a Redis key for usage tracking
type RedisUsageKey struct {
	UserID       uuid.UUID
	ResourceType ResourceType
	Period       string // e.g., "2024-01" for monthly tracking
}

// String returns the Redis key string
func (r RedisUsageKey) String() string {
	return fmt.Sprintf("usage:%s:%s:%s", r.UserID, r.ResourceType, r.Period)
}

// RateLimitKey represents a Redis key for rate limiting
type RateLimitKey struct {
	UserID       uuid.UUID
	ResourceType ResourceType
	Window       string // e.g., "2024-01-15-14" for hourly windows
}

// String returns the rate limit Redis key
func (r RateLimitKey) String() string {
	return fmt.Sprintf("rate_limit:%s:%s:%s", r.UserID, r.ResourceType, r.Window)
}

// SubscriptionCache represents cached subscription data in Redis
type SubscriptionCache struct {
	UserID        uuid.UUID          `json:"user_id"`
	SubscriptionID uuid.UUID         `json:"subscription_id"`
	PlanType      SubscriptionPlan   `json:"plan_type"`
	Status        SubscriptionStatus `json:"status"`
	Limits        JSONMap            `json:"limits"`
	ExpiresAt     time.Time          `json:"expires_at"`
	IsActive      bool               `json:"is_active"`
	CachedAt      time.Time          `json:"cached_at"`
}

// QuotaCache represents cached quota information in Redis
type QuotaCache struct {
	UserID       uuid.UUID    `json:"user_id"`
	ResourceType ResourceType `json:"resource_type"`
	CurrentUsage int          `json:"current_usage"`
	MaxAllowed   int          `json:"max_allowed"`
	PeriodStart  time.Time    `json:"period_start"`
	PeriodEnd    time.Time    `json:"period_end"`
	CachedAt     time.Time    `json:"cached_at"`
}

// BillingPeriod represents different billing period calculations
type BillingPeriod struct {
	Start time.Time `json:"start"`
	End   time.Time `json:"end"`
	Type  string    `json:"type"` // monthly, yearly, weekly
}

// GetCurrentBillingPeriod returns the current billing period for a subscription
func GetCurrentBillingPeriod(subscription *Subscription) BillingPeriod {
	now := time.Now()
	
	switch subscription.BillingCycle {
	case CycleMonthly:
		start := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
		end := start.AddDate(0, 1, 0).Add(-time.Second)
		return BillingPeriod{Start: start, End: end, Type: "monthly"}
		
	case CycleYearly:
		start := time.Date(now.Year(), 1, 1, 0, 0, 0, 0, time.UTC)
		end := start.AddDate(1, 0, 0).Add(-time.Second)
		return BillingPeriod{Start: start, End: end, Type: "yearly"}
		
	case CycleWeekly:
		// Start from Monday of current week
		weekday := now.Weekday()
		if weekday == time.Sunday {
			weekday = 7
		}
		start := now.AddDate(0, 0, -int(weekday-1))
		start = time.Date(start.Year(), start.Month(), start.Day(), 0, 0, 0, 0, time.UTC)
		end := start.AddDate(0, 0, 7).Add(-time.Second)
		return BillingPeriod{Start: start, End: end, Type: "weekly"}
		
	default:
		// Default to monthly
		start := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
		end := start.AddDate(0, 1, 0).Add(-time.Second)
		return BillingPeriod{Start: start, End: end, Type: "monthly"}
	}
}

// WebhookEvent represents Stripe webhook events
type WebhookEvent struct {
	ID         uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	StripeID   string    `gorm:"type:varchar(255);not null;unique;index" json:"stripe_id"`
	EventType  string    `gorm:"type:varchar(100);not null;index" json:"event_type"`
	ObjectType string    `gorm:"type:varchar(50);not null" json:"object_type"`
	ObjectID   string    `gorm:"type:varchar(255);not null" json:"object_id"`
	Data       JSONMap   `gorm:"type:jsonb" json:"data"`
	Processed  bool      `gorm:"default:false;index" json:"processed"`
	ProcessedAt *time.Time `json:"processed_at"`
	CreatedAt  time.Time `gorm:"default:CURRENT_TIMESTAMP" json:"created_at"`
}

// TableName specifies the table name for GORM
func (WebhookEvent) TableName() string {
	return "webhook_events"
}