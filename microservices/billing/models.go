package main

import (
	"time"

	"github.com/google/uuid"
	"github.com/shopspring/decimal"
)

// User represents a user from the database
type User struct {
	ID               uuid.UUID `json:"id" db:"id"`
	Email            string    `json:"email" db:"email"`
	SubscriptionPlan string    `json:"subscription_plan" db:"subscription_plan"`
	CreatedAt        time.Time `json:"created_at" db:"created_at"`
	UpdatedAt        time.Time `json:"updated_at" db:"updated_at"`
}

// Subscription represents a user's subscription
type Subscription struct {
	ID             uuid.UUID       `json:"id" db:"id"`
	UserID         uuid.UUID       `json:"user_id" db:"user_id"`
	PlanType       string          `json:"plan_type" db:"plan_type"`
	Status         string          `json:"status" db:"status"`
	BillingCycle   string          `json:"billing_cycle" db:"billing_cycle"`
	AmountCents    int64           `json:"amount_cents" db:"amount_cents"`
	Currency       string          `json:"currency" db:"currency"`
	StartedAt      time.Time       `json:"started_at" db:"started_at"`
	EndsAt         *time.Time      `json:"ends_at,omitempty" db:"ends_at"`
	AutoRenew      bool            `json:"auto_renew" db:"auto_renew"`
	Limits         map[string]int  `json:"limits" db:"limits"`
	CreatedAt      time.Time       `json:"created_at" db:"created_at"`
	UpdatedAt      time.Time       `json:"updated_at" db:"updated_at"`
}

// UsageRecord represents a usage record for billing
type UsageRecord struct {
	ID                   uuid.UUID              `json:"id" db:"id"`
	UserID               uuid.UUID              `json:"user_id" db:"user_id"`
	ResourceType         string                 `json:"resource_type" db:"resource_type"`
	Quantity             int                    `json:"quantity" db:"quantity"`
	BillingPeriodStart   time.Time              `json:"billing_period_start" db:"billing_period_start"`
	BillingPeriodEnd     time.Time              `json:"billing_period_end" db:"billing_period_end"`
	ExtraData            map[string]interface{} `json:"extra_data" db:"extra_data"`
	CreatedAt            time.Time              `json:"created_at" db:"created_at"`
}

// PlanDefinition represents a subscription plan definition
type PlanDefinition struct {
	ID       string                     `json:"id"`
	Name     string                     `json:"name"`
	Limits   map[string]int             `json:"limits"`
	Features []string                   `json:"features"`
	Pricing  map[string]decimal.Decimal `json:"pricing"`
}

// QuotaInfo represents current usage and quota information
type QuotaInfo struct {
	HasQuota     bool      `json:"has_quota"`
	CurrentUsage int       `json:"current_usage"`
	MaxAllowed   int       `json:"max_allowed"`
	Remaining    int       `json:"remaining"`
	PeriodStart  time.Time `json:"period_start"`
	PeriodEnd    time.Time `json:"period_end"`
}

// UsageSummary represents usage summary for a user
type UsageSummary struct {
	MessagesThisMonth       int            `json:"messages_this_month"`
	BackgroundTasksThisMonth int           `json:"background_tasks_this_month"`
	APICallsThisMonth       int            `json:"api_calls_this_month"`
	QuotaRemaining          int            `json:"quota_remaining"`
	Limits                  map[string]int `json:"limits"`
	PeriodStart             time.Time      `json:"period_start"`
	PeriodEnd               time.Time      `json:"period_end"`
	PlanType                string         `json:"plan_type"`
}

// BillingHistoryItem represents a billing history item
type BillingHistoryItem struct {
	Date        time.Time `json:"date"`
	Description string    `json:"description"`
	AmountCents int64     `json:"amount_cents"`
	Currency    string    `json:"currency"`
	Status      string    `json:"status"`
	InvoiceURL  *string   `json:"invoice_url,omitempty"`
}

// BillingHistory represents complete billing history
type BillingHistory struct {
	Total int                  `json:"total"`
	Items []BillingHistoryItem `json:"items"`
}

// DetailedUsage represents detailed usage breakdown
type DetailedUsage struct {
	StartDate     time.Time                           `json:"start_date"`
	EndDate       time.Time                           `json:"end_date"`
	UsageByType   map[string]ResourceUsageBreakdown   `json:"usage_by_type"`
	TotalRecords  int                                 `json:"total_records"`
}

// ResourceUsageBreakdown represents usage breakdown for a resource type
type ResourceUsageBreakdown struct {
	Total   int            `json:"total"`
	Records []UsageRecordItem `json:"records"`
}

// UsageRecordItem represents individual usage record item
type UsageRecordItem struct {
	Timestamp time.Time              `json:"timestamp"`
	Quantity  int                    `json:"quantity"`
	Metadata  map[string]interface{} `json:"metadata"`
}

// Response types for API endpoints
type APIResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

type SubscriptionCreateRequest struct {
	PlanType     string `json:"plan_type" binding:"required"`
	BillingCycle string `json:"billing_cycle" binding:"required"`
}

type SubscriptionUpdateRequest struct {
	PlanType     string `json:"plan_type" binding:"required"`
	BillingCycle string `json:"billing_cycle" binding:"required"`
}

type UsageRecordRequest struct {
	ResourceType string                 `json:"resource_type" binding:"required"`
	Quantity     int                    `json:"quantity" binding:"min=1"`
	ExtraData    map[string]interface{} `json:"extra_data,omitempty"`
}

type AvailablePlansResponse struct {
	Plans    []PlanDefinition `json:"plans"`
	Currency string           `json:"currency"`
}