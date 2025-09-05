package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"
	"strings"

	"github.com/google/uuid"
	_ "github.com/lib/pq"
	_ "github.com/mattn/go-sqlite3" // SQLite support for testing
	"go.uber.org/zap"
)

type DatabaseManager struct {
	db     *sql.DB
	logger *zap.Logger
	ctx    context.Context
	driver string
}

func NewDatabaseManager(databaseURL string, logger *zap.Logger) (*DatabaseManager, error) {
	// Determine database driver based on URL
	var driver string
	if strings.HasPrefix(databaseURL, "postgres://") || strings.HasPrefix(databaseURL, "postgresql://") {
		driver = "postgres"
	} else if strings.HasPrefix(databaseURL, "sqlite://") || strings.HasSuffix(databaseURL, ".db") || databaseURL == ":memory:" {
		driver = "sqlite3"
		// Remove sqlite:// prefix if present
		databaseURL = strings.TrimPrefix(databaseURL, "sqlite://")
	} else {
		driver = "postgres" // Default to postgres
	}

	db, err := sql.Open(driver, databaseURL)
	if err != nil {
		return nil, fmt.Errorf("failed to open database connection: %w", err)
	}

	// Test connection
	ctx := context.Background()
	if err := db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	// Configure connection pool
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)

	dm := &DatabaseManager{
		db:     db,
		logger: logger,
		ctx:    ctx,
		driver: driver,
	}

	return dm, nil
}

// InitializeTables creates the necessary tables for testing (SQLite compatible)
func (db *DatabaseManager) InitializeTables() error {
	createTables := []string{
		`CREATE TABLE IF NOT EXISTS users (
			id TEXT PRIMARY KEY,
			email TEXT UNIQUE NOT NULL,
			subscription_plan TEXT DEFAULT 'free',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS subscriptions (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL,
			plan_type TEXT NOT NULL,
			status TEXT NOT NULL,
			billing_cycle TEXT NOT NULL,
			amount_cents INTEGER NOT NULL,
			currency TEXT DEFAULT 'USD',
			started_at DATETIME NOT NULL,
			ends_at DATETIME,
			auto_renew BOOLEAN DEFAULT true,
			limits TEXT DEFAULT '{}',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users (id)
		)`,
		`CREATE TABLE IF NOT EXISTS usage_records (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL,
			resource_type TEXT NOT NULL,
			quantity INTEGER NOT NULL,
			billing_period_start DATETIME NOT NULL,
			billing_period_end DATETIME NOT NULL,
			extra_data TEXT,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users (id)
		)`,
	}

	for _, createSQL := range createTables {
		if _, err := db.db.ExecContext(db.ctx, createSQL); err != nil {
			return fmt.Errorf("failed to create table: %w", err)
		}
	}

	return nil
}

// ConvertQuery converts PostgreSQL queries to be compatible with SQLite
func (db *DatabaseManager) ConvertQuery(query string) string {
	if db.driver == "sqlite3" {
		// Convert PostgreSQL placeholders ($1, $2) to SQLite placeholders (?)
		converted := query
		for i := 1; i <= 20; i++ { // Increased to handle more placeholders
			placeholder := fmt.Sprintf("$%d", i)
			if strings.Contains(converted, placeholder) {
				converted = strings.Replace(converted, placeholder, "?", 1)
			}
		}
		// Convert NOW() to CURRENT_TIMESTAMP
		converted = strings.ReplaceAll(converted, "NOW()", "CURRENT_TIMESTAMP")
		// Convert PostgreSQL schema references
		converted = strings.ReplaceAll(converted, "auth.subscriptions", "subscriptions")
		converted = strings.ReplaceAll(converted, "auth.users", "users")
		converted = strings.ReplaceAll(converted, "auth.usage_records", "usage_records")
		return converted
	}
	return query
}

func (db *DatabaseManager) Close() error {
	return db.db.Close()
}

func (db *DatabaseManager) Ping() error {
	return db.db.PingContext(db.ctx)
}

func (db *DatabaseManager) GetUser(userID uuid.UUID) (*User, error) {
	query := `
		SELECT id, email, subscription_plan, created_at, updated_at 
		FROM users 
		WHERE id = $1`

	var user User
	err := db.db.QueryRowContext(db.ctx, db.ConvertQuery(query), userID).Scan(
		&user.ID,
		&user.Email,
		&user.SubscriptionPlan,
		&user.CreatedAt,
		&user.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("user not found: %s", userID)
		}
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	return &user, nil
}

func (db *DatabaseManager) GetActiveSubscription(userID uuid.UUID) (*Subscription, error) {
	query := `
		SELECT id, user_id, plan_type, status, billing_cycle, amount_cents, 
		       currency, started_at, ends_at, auto_renew, limits, created_at, updated_at
		FROM subscriptions 
		WHERE user_id = $1 AND status IN ('active', 'trialing')
		ORDER BY created_at DESC 
		LIMIT 1`

	var subscription Subscription
	var limitsJSON []byte
	var endsAt sql.NullTime

	err := db.db.QueryRowContext(db.ctx, db.ConvertQuery(query), userID).Scan(
		&subscription.ID,
		&subscription.UserID,
		&subscription.PlanType,
		&subscription.Status,
		&subscription.BillingCycle,
		&subscription.AmountCents,
		&subscription.Currency,
		&subscription.StartedAt,
		&endsAt,
		&subscription.AutoRenew,
		&limitsJSON,
		&subscription.CreatedAt,
		&subscription.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil // No active subscription
		}
		return nil, fmt.Errorf("failed to get active subscription: %w", err)
	}

	// Handle nullable ends_at
	if endsAt.Valid {
		subscription.EndsAt = &endsAt.Time
	}

	// Parse limits JSON
	if limitsJSON != nil {
		if db.driver == "sqlite3" {
			// SQLite stores as TEXT, convert to JSON
			err = json.Unmarshal([]byte(string(limitsJSON)), &subscription.Limits)
		} else {
			err = json.Unmarshal(limitsJSON, &subscription.Limits)
		}
		if err != nil {
			db.logger.Error("Failed to unmarshal subscription limits", zap.Error(err))
			subscription.Limits = map[string]int{}
		}
	} else {
		subscription.Limits = map[string]int{}
	}

	return &subscription, nil
}

func (db *DatabaseManager) CreateSubscription(userID uuid.UUID, planType, billingCycle string) (*Subscription, error) {
	// Get plan definition to determine pricing and limits
	planDef := GetPlanDefinition(planType)
	if planDef == nil {
		return nil, fmt.Errorf("invalid plan type: %s", planType)
	}
	
	pricing := GetPlanPricing(planType, billingCycle)
	amountCents := int64(pricing.IntPart() * 100)
	limits := GetPlanLimits(planType)

	limitsJSON, err := json.Marshal(limits)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal limits: %w", err)
	}

	subscription := &Subscription{
		ID:           uuid.New(),
		UserID:       userID,
		PlanType:     planType,
		Status:       "active",
		BillingCycle: billingCycle,
		AmountCents:  amountCents,
		Currency:     "USD",
		StartedAt:    time.Now().UTC(),
		AutoRenew:    true,
		Limits:       limits,
		CreatedAt:    time.Now().UTC(),
		UpdatedAt:    time.Now().UTC(),
	}

	query := `
		INSERT INTO subscriptions (id, user_id, plan_type, status, billing_cycle, 
		                          amount_cents, currency, started_at, auto_renew, 
		                          limits, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`

	if db.driver == "sqlite3" {
		_, err = db.db.ExecContext(db.ctx, db.ConvertQuery(query),
			subscription.ID,
			subscription.UserID,
			subscription.PlanType,
			subscription.Status,
			subscription.BillingCycle,
			subscription.AmountCents,
			subscription.Currency,
			subscription.StartedAt,
			subscription.AutoRenew,
			string(limitsJSON),
			subscription.CreatedAt,
			subscription.UpdatedAt,
		)
	} else {
		err = db.db.QueryRowContext(db.ctx, query+" RETURNING id, created_at, updated_at",
			subscription.ID,
			subscription.UserID,
			subscription.PlanType,
			subscription.Status,
			subscription.BillingCycle,
			subscription.AmountCents,
			subscription.Currency,
			subscription.StartedAt,
			subscription.AutoRenew,
			limitsJSON,
			subscription.CreatedAt,
			subscription.UpdatedAt,
		).Scan(&subscription.ID, &subscription.CreatedAt, &subscription.UpdatedAt)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to create subscription: %w", err)
	}

	db.logger.Info("Created subscription", 
		zap.String("user_id", userID.String()),
		zap.String("plan_type", planType))

	return subscription, nil
}

func (db *DatabaseManager) UpdateSubscription(userID uuid.UUID, planType, billingCycle string) (*Subscription, error) {
	// First get the existing subscription
	subscription, err := db.GetActiveSubscription(userID)
	if err != nil {
		return nil, err
	}

	if subscription == nil {
		return nil, fmt.Errorf("no active subscription found for user %s", userID)
	}

	// Get new plan details
	pricing := GetPlanPricing(planType, billingCycle)
	amountCents := int64(pricing.IntPart() * 100)
	limits := GetPlanLimits(planType)

	limitsJSON, err := json.Marshal(limits)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal limits: %w", err)
	}

	baseQuery := `
		UPDATE subscriptions 
		SET plan_type = $1, billing_cycle = $2, amount_cents = $3, limits = $4, updated_at = $5
		WHERE id = $6`

	var updatedSubscription Subscription
	var limitsResult []byte
	var endsAt sql.NullTime

	if db.driver == "sqlite3" {
		_, err = db.db.ExecContext(db.ctx, db.ConvertQuery(baseQuery),
			planType,
			billingCycle,
			amountCents,
			string(limitsJSON),
			time.Now().UTC(),
			subscription.ID,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to update subscription: %w", err)
		}

		// Get the updated subscription for SQLite
		return db.GetActiveSubscription(userID)
	} else {
		query := baseQuery + ` RETURNING id, user_id, plan_type, status, billing_cycle, amount_cents, 
		          currency, started_at, ends_at, auto_renew, limits, created_at, updated_at`

		err = db.db.QueryRowContext(db.ctx, query,
			planType,
			billingCycle,
			amountCents,
			limitsJSON,
			time.Now().UTC(),
			subscription.ID,
		).Scan(
			&updatedSubscription.ID,
			&updatedSubscription.UserID,
			&updatedSubscription.PlanType,
			&updatedSubscription.Status,
			&updatedSubscription.BillingCycle,
			&updatedSubscription.AmountCents,
			&updatedSubscription.Currency,
			&updatedSubscription.StartedAt,
			&endsAt,
			&updatedSubscription.AutoRenew,
			&limitsResult,
			&updatedSubscription.CreatedAt,
			&updatedSubscription.UpdatedAt,
		)

		if err != nil {
			return nil, fmt.Errorf("failed to update subscription: %w", err)
		}

		// Handle nullable ends_at
		if endsAt.Valid {
			updatedSubscription.EndsAt = &endsAt.Time
		}

		// Parse limits JSON
		err = json.Unmarshal(limitsResult, &updatedSubscription.Limits)
		if err != nil {
			db.logger.Error("Failed to unmarshal updated subscription limits", zap.Error(err))
			updatedSubscription.Limits = limits // fallback to input
		}

		db.logger.Info("Updated subscription", 
			zap.String("user_id", userID.String()),
			zap.String("plan_type", planType))

		return &updatedSubscription, nil
	}
}

func (db *DatabaseManager) CancelSubscription(userID uuid.UUID) error {
	subscription, err := db.GetActiveSubscription(userID)
	if err != nil {
		return err
	}

	if subscription == nil {
		return fmt.Errorf("no active subscription found")
	}

	if subscription.PlanType == "free" {
		return fmt.Errorf("cannot cancel free plan")
	}

	// Calculate end date if not set
	var endsAt time.Time
	if subscription.EndsAt != nil {
		endsAt = *subscription.EndsAt
	} else {
		if subscription.BillingCycle == "monthly" {
			endsAt = subscription.StartedAt.AddDate(0, 1, 0)
		} else {
			endsAt = subscription.StartedAt.AddDate(1, 0, 0)
		}
	}

	_, err = db.db.ExecContext(db.ctx, db.ConvertQuery(
		"UPDATE subscriptions SET status = 'pending_cancellation', auto_renew = false, ends_at = $1, updated_at = $2 WHERE id = $3"),
		endsAt, time.Now().UTC(), subscription.ID)

	if err != nil {
		return fmt.Errorf("failed to cancel subscription: %w", err)
	}

	db.logger.Info("Cancelled subscription", 
		zap.String("user_id", userID.String()),
		zap.Time("ends_at", endsAt))

	return nil
}

func (db *DatabaseManager) RecordUsage(userID uuid.UUID, resourceType string, quantity int, extraData map[string]interface{}) error {
	// Calculate billing period (current month)
	now := time.Now().UTC()
	periodStart := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
	periodEnd := periodStart.AddDate(0, 1, 0).Add(-time.Nanosecond)

	extraDataJSON, err := json.Marshal(extraData)
	if err != nil {
		return fmt.Errorf("failed to marshal extra data: %w", err)
	}

	query := `
		INSERT INTO usage_records (id, user_id, resource_type, quantity, billing_period_start, 
		                          billing_period_end, extra_data, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`

	_, err = db.db.ExecContext(db.ctx, db.ConvertQuery(query),
		uuid.New(),
		userID,
		resourceType,
		quantity,
		periodStart,
		periodEnd,
		extraDataJSON,
		time.Now().UTC(),
	)

	if err != nil {
		return fmt.Errorf("failed to record usage: %w", err)
	}

	db.logger.Debug("Recorded usage", 
		zap.String("user_id", userID.String()),
		zap.String("resource_type", resourceType),
		zap.Int("quantity", quantity))

	return nil
}

func (db *DatabaseManager) CheckQuota(userID uuid.UUID, resourceType string) (*QuotaInfo, error) {
	// Get current subscription
	subscription, err := db.GetActiveSubscription(userID)
	if err != nil {
		return nil, err
	}

	if subscription == nil {
		// Use free plan limits as default
		subscription = &Subscription{
			PlanType: "free",
			Limits:   GetPlanLimits("free"),
		}
	}

	// Get current month usage
	now := time.Now().UTC()
	periodStart := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
	periodEnd := periodStart.AddDate(0, 1, 0).Add(-time.Nanosecond)

	currentUsage, err := db.GetUsageForPeriod(userID, resourceType, periodStart, periodEnd)
	if err != nil {
		return nil, err
	}

	maxAllowed, exists := subscription.Limits[resourceType]
	if !exists {
		maxAllowed = 0
	}

	hasQuota := maxAllowed != -1 // -1 means unlimited
	remaining := 0
	if hasQuota {
		remaining = maxAllowed - currentUsage
		if remaining < 0 {
			remaining = 0
		}
	}

	return &QuotaInfo{
		HasQuota:     hasQuota,
		CurrentUsage: currentUsage,
		MaxAllowed:   maxAllowed,
		Remaining:    remaining,
		PeriodStart:  periodStart,
		PeriodEnd:    periodEnd,
	}, nil
}

func (db *DatabaseManager) GetUsageForPeriod(userID uuid.UUID, resourceType string, periodStart, periodEnd time.Time) (int, error) {
	query := `
		SELECT COALESCE(SUM(quantity), 0) 
		FROM usage_records 
		WHERE user_id = $1 AND resource_type = $2 
		  AND billing_period_start >= $3 AND billing_period_end <= $4`

	var totalUsage int
	err := db.db.QueryRowContext(db.ctx, db.ConvertQuery(query), userID, resourceType, periodStart, periodEnd).Scan(&totalUsage)
	if err != nil {
		return 0, fmt.Errorf("failed to get usage for period: %w", err)
	}

	return totalUsage, nil
}

func (db *DatabaseManager) GetUsageSummary(userID uuid.UUID) (*UsageSummary, error) {
	// Get current subscription
	subscription, err := db.GetActiveSubscription(userID)
	if err != nil {
		return nil, err
	}

	planType := "free"
	limits := GetPlanLimits("free")
	if subscription != nil {
		planType = subscription.PlanType
		limits = subscription.Limits
	}

	// Get current month usage
	now := time.Now().UTC()
	periodStart := time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
	periodEnd := periodStart.AddDate(0, 1, 0).Add(-time.Nanosecond)

	usageMap, err := db.GetUsageSummaryForPeriod(userID, periodStart, periodEnd)
	if err != nil {
		return nil, err
	}

	// Calculate total quota remaining (using messages as primary quota)
	messagesUsed := usageMap["messages"]
	messagesLimit := limits["messages"]
	quotaRemaining := 0
	if messagesLimit > 0 {
		quotaRemaining = messagesLimit - messagesUsed
		if quotaRemaining < 0 {
			quotaRemaining = 0
		}
	}

	return &UsageSummary{
		MessagesThisMonth:       usageMap["messages"],
		BackgroundTasksThisMonth: usageMap["background_tasks"],
		APICallsThisMonth:       usageMap["api_calls"],
		QuotaRemaining:          quotaRemaining,
		Limits:                  limits,
		PeriodStart:             periodStart,
		PeriodEnd:               periodEnd,
		PlanType:                planType,
	}, nil
}

func (db *DatabaseManager) GetUsageSummaryForPeriod(userID uuid.UUID, periodStart, periodEnd time.Time) (map[string]int, error) {
	query := `
		SELECT resource_type, COALESCE(SUM(quantity), 0) as total
		FROM usage_records 
		WHERE user_id = $1 AND billing_period_start >= $2 AND billing_period_end <= $3
		GROUP BY resource_type`

	rows, err := db.db.QueryContext(db.ctx, db.ConvertQuery(query), userID, periodStart, periodEnd)
	if err != nil {
		return nil, fmt.Errorf("failed to get usage summary: %w", err)
	}
	defer rows.Close()

	usage := make(map[string]int)
	for rows.Next() {
		var resourceType string
		var total int
		if err := rows.Scan(&resourceType, &total); err != nil {
			return nil, fmt.Errorf("failed to scan usage row: %w", err)
		}
		usage[resourceType] = total
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating usage rows: %w", err)
	}

	// Ensure all resource types are present
	if _, exists := usage["messages"]; !exists {
		usage["messages"] = 0
	}
	if _, exists := usage["background_tasks"]; !exists {
		usage["background_tasks"] = 0
	}
	if _, exists := usage["api_calls"]; !exists {
		usage["api_calls"] = 0
	}

	return usage, nil
}

func (db *DatabaseManager) GetDetailedUsage(userID uuid.UUID, startDate, endDate time.Time, limit int) (*DetailedUsage, error) {
	// Default to current month if dates are zero
	if startDate.IsZero() {
		now := time.Now().UTC()
		startDate = time.Date(now.Year(), now.Month(), 1, 0, 0, 0, 0, time.UTC)
	}
	if endDate.IsZero() {
		endDate = time.Now().UTC()
	}

	query := `
		SELECT resource_type, quantity, extra_data, created_at
		FROM usage_records 
		WHERE user_id = $1 AND created_at >= $2 AND created_at <= $3
		ORDER BY created_at DESC
		LIMIT $4`

	rows, err := db.db.QueryContext(db.ctx, db.ConvertQuery(query), userID, startDate, endDate, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to get detailed usage: %w", err)
	}
	defer rows.Close()

	usageByType := make(map[string]ResourceUsageBreakdown)
	totalRecords := 0

	for rows.Next() {
		var resType string
		var quantity int
		var extraDataJSON []byte
		var createdAt time.Time

		err := rows.Scan(&resType, &quantity, &extraDataJSON, &createdAt)
		if err != nil {
			return nil, fmt.Errorf("failed to scan usage record: %w", err)
		}

		// Parse extra data
		var metadata map[string]interface{}
		if extraDataJSON != nil {
			json.Unmarshal(extraDataJSON, &metadata)
		}
		if metadata == nil {
			metadata = make(map[string]interface{})
		}

		// Add to usage breakdown
		breakdown, exists := usageByType[resType]
		if !exists {
			breakdown = ResourceUsageBreakdown{
				Total:   0,
				Records: []UsageRecordItem{},
			}
		}

		breakdown.Total += quantity
		breakdown.Records = append(breakdown.Records, UsageRecordItem{
			Timestamp: createdAt,
			Quantity:  quantity,
			Metadata:  metadata,
		})

		usageByType[resType] = breakdown
		totalRecords++
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating detailed usage: %w", err)
	}

	return &DetailedUsage{
		StartDate:    startDate,
		EndDate:      endDate,
		UsageByType:  usageByType,
		TotalRecords: totalRecords,
	}, nil
}

func (db *DatabaseManager) GetBillingHistory(userID uuid.UUID, limit int) (*BillingHistory, error) {
	// Get total count
	var total int
	err := db.db.QueryRowContext(db.ctx, db.ConvertQuery(
		"SELECT COUNT(*) FROM subscriptions WHERE user_id = $1"), userID).Scan(&total)
	if err != nil {
		return nil, fmt.Errorf("failed to get billing history count: %w", err)
	}

	// Get subscriptions with pagination
	query := `
		SELECT created_at, plan_type, billing_cycle, amount_cents, currency, status
		FROM subscriptions 
		WHERE user_id = $1 
		ORDER BY created_at DESC 
		LIMIT $2`

	rows, err := db.db.QueryContext(db.ctx, db.ConvertQuery(query), userID, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to get billing history: %w", err)
	}
	defer rows.Close()

	var items []BillingHistoryItem
	for rows.Next() {
		var item BillingHistoryItem
		var planType, billingCycle string
		
		err := rows.Scan(
			&item.Date,
			&planType,
			&billingCycle,
			&item.AmountCents,
			&item.Currency,
			&item.Status,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan billing history item: %w", err)
		}

		item.Description = fmt.Sprintf("%s Plan - %s", 
			capitalizeFirst(planType), 
			capitalizeFirst(billingCycle))
		
		items = append(items, item)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating billing history: %w", err)
	}

	return &BillingHistory{
		Total: total,
		Items: items,
	}, nil
}

func capitalizeFirst(s string) string {
	if len(s) == 0 {
		return s
	}
	return string(s[0]-32) + s[1:]
}