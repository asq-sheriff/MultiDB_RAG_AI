// Package main provides database management for user subscription service
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// DatabaseInterface defines the interface for database operations
type DatabaseInterface interface {
	GetSubscriptionByUserID(userID uuid.UUID) (*Subscription, error)
	CreateSubscription(subscription *Subscription) error
	UpdateSubscription(subscription *Subscription) error
	CancelSubscription(userID uuid.UUID, reason string) error
	RecordUsage(userID uuid.UUID, resourceType ResourceType, quantity int, metadata map[string]interface{}) error
	CheckUserQuota(userID uuid.UUID, resourceType ResourceType) (*QuotaInfo, error)
	GetUsageSummary(userID uuid.UUID, days int) (map[string]interface{}, error)
	HealthCheck() map[string]interface{}
	Close() error
	// Cache operations
	GetCacheMetrics() map[string]*CacheStats
	FlushCache() error
	WarmupCache() error
	SetCacheEnabled(enabled bool)
	GetCache() *RedisCache
	// Database operations
	CreateEvent(event interface{}) error
	GetDB() *gorm.DB
}

// DatabaseManager handles all database operations for the subscription service
type DatabaseManager struct {
	DB          *gorm.DB
	RedisClient *redis.Client
	Cache       *RedisCache
	ctx         context.Context
	logger      logger.Interface
}

// NewDatabaseManager creates a new database manager with PostgreSQL and Redis connections
func NewDatabaseManager() (*DatabaseManager, error) {
	// Initialize database connections
	db, err := connectToPostgreSQL()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to PostgreSQL: %w", err)
	}

	redisClient, err := connectToRedis()
	if err != nil {
		log.Printf("Warning: Failed to connect to Redis: %v", err)
		// Continue without Redis for caching
	}

	// Configure GORM logger
	gormLogger := logger.New(
		log.New(os.Stdout, "\r\n", log.LstdFlags),
		logger.Config{
			SlowThreshold:             time.Second,
			LogLevel:                  logger.Warn,
			IgnoreRecordNotFoundError: true,
			Colorful:                  false,
		},
	)

	// Initialize cache if Redis is available
	var cache *RedisCache
	if redisClient != nil {
		redisURL := fmt.Sprintf("redis://%s:%s", 
			getEnv("REDIS_HOST", "localhost"),
			getEnv("REDIS_PORT", "6379"))
		
		// Create zap logger for cache
		zapLogger, _ := zap.NewProduction()
		if zapLogger == nil {
			zapLogger, _ = zap.NewDevelopment()
		}
		
		cache, err = NewRedisCache(redisURL, zapLogger)
		if err != nil {
			log.Printf("Warning: Failed to initialize Redis cache: %v", err)
			cache = nil
		}
	}

	dm := &DatabaseManager{
		DB:          db,
		RedisClient: redisClient,
		Cache:       cache,
		ctx:         context.Background(),
		logger:      gormLogger,
	}

	// Auto-migrate database schema
	if err := dm.autoMigrate(); err != nil {
		return nil, fmt.Errorf("failed to migrate database: %w", err)
	}

	return dm, nil
}

// connectToPostgreSQL establishes PostgreSQL connection using GORM
func connectToPostgreSQL() (*gorm.DB, error) {
	// Build DSN from environment variables
	dsn := fmt.Sprintf(
		"host=%s user=%s password=%s dbname=%s port=%s sslmode=%s TimeZone=UTC",
		getEnv("POSTGRES_HOST", "localhost"),
		getEnv("POSTGRES_USER", "chatbot_user"),
		getEnv("POSTGRES_PASSWORD", "secure_password"),
		getEnv("POSTGRES_DB", "chatbot_app"),
		getEnv("POSTGRES_PORT", "5432"),
		getEnv("POSTGRES_SSLMODE", "disable"),
	)

	// Configure GORM
	config := &gorm.Config{
		Logger: logger.Default.LogMode(logger.Info),
		NowFunc: func() time.Time {
			return time.Now().UTC()
		},
	}

	db, err := gorm.Open(postgres.Open(dsn), config)
	if err != nil {
		return nil, err
	}

	// Configure connection pool
	sqlDB, err := db.DB()
	if err != nil {
		return nil, err
	}

	sqlDB.SetMaxOpenConns(25)
	sqlDB.SetMaxIdleConns(5)
	sqlDB.SetConnMaxLifetime(5 * time.Minute)

	return db, nil
}

// connectToRedis establishes Redis connection
func connectToRedis() (*redis.Client, error) {
	redisDB, _ := strconv.Atoi(getEnv("REDIS_DB", "0"))
	
	client := redis.NewClient(&redis.Options{
		Addr:         getEnv("REDIS_HOST", "localhost") + ":" + getEnv("REDIS_PORT", "6379"),
		Password:     getEnv("REDIS_PASSWORD", ""),
		DB:           redisDB,
		DialTimeout:  10 * time.Second,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		PoolSize:     10,
		PoolTimeout:  30 * time.Second,
	})

	// Test connection
	ctx := context.Background()
	_, err := client.Ping(ctx).Result()
	if err != nil {
		return nil, err
	}

	return client, nil
}

// autoMigrate runs database migrations
func (dm *DatabaseManager) autoMigrate() error {
	// Enable UUID extension
	if err := dm.DB.Exec("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"").Error; err != nil {
		log.Printf("Warning: Could not create uuid-ossp extension: %v", err)
	}

	// Migrate all models
	return dm.DB.AutoMigrate(
		&Subscription{},
		&Usage{},
		&SubscriptionEvent{},
		&WebhookEvent{},
	)
}

// GetSubscriptionByUserID retrieves a user's active subscription
func (dm *DatabaseManager) GetSubscriptionByUserID(userID uuid.UUID) (*Subscription, error) {
	var subscription Subscription
	
	// Try Redis cache first
	if dm.RedisClient != nil {
		cacheKey := fmt.Sprintf("subscription:user:%s", userID)
		cached, err := dm.RedisClient.Get(dm.ctx, cacheKey).Result()
		if err == nil {
			var cachedSub SubscriptionCache
			if json.Unmarshal([]byte(cached), &cachedSub) == nil && cachedSub.IsActive {
				// Convert cached data back to subscription
				subscription = Subscription{
					ID:           cachedSub.SubscriptionID,
					UserID:       cachedSub.UserID,
					PlanType:     cachedSub.PlanType,
					Status:       cachedSub.Status,
					Limits:       cachedSub.Limits,
					EndsAt:       &cachedSub.ExpiresAt,
				}
				return &subscription, nil
			}
		}
	}

	// Query database
	err := dm.DB.Where("user_id = ? AND status IN ?", userID, []SubscriptionStatus{StatusActive, StatusTrialing}).
		Order("created_at DESC").
		First(&subscription).Error
	
	if err != nil {
		return nil, err
	}

	// Cache the result
	dm.cacheSubscription(&subscription)

	return &subscription, nil
}

// CreateSubscription creates a new subscription
func (dm *DatabaseManager) CreateSubscription(subscription *Subscription) error {
	// Set defaults
	if subscription.ID == uuid.Nil {
		subscription.ID = uuid.New()
	}
	subscription.CreatedAt = time.Now().UTC()
	subscription.UpdatedAt = time.Now().UTC()

	// Set plan limits if not provided
	if subscription.Limits == nil {
		limits := GetPlanDefaults(subscription.PlanType)
		subscription.Limits = make(JSONMap)
		for k, v := range limits {
			subscription.Limits[k] = v
		}
	}

	// Create subscription in database
	err := dm.DB.Create(subscription).Error
	if err != nil {
		return err
	}

	// Create subscription event
	event := &SubscriptionEvent{
		SubscriptionID: subscription.ID,
		UserID:         subscription.UserID,
		EventType:      "created",
		NewStatus:      subscription.Status,
		NewPlan:        subscription.PlanType,
		Metadata: JSONMap{
			"billing_cycle": subscription.BillingCycle,
			"amount_cents":  subscription.AmountCents,
		},
		CreatedAt: time.Now().UTC(),
	}
	
	dm.DB.Create(event)

	// Invalidate user cache
	dm.invalidateUserCache(subscription.UserID)

	return nil
}

// UpdateSubscription updates an existing subscription
func (dm *DatabaseManager) UpdateSubscription(subscription *Subscription) error {
	// Get old subscription for event tracking
	var oldSub Subscription
	dm.DB.First(&oldSub, subscription.ID)

	subscription.UpdatedAt = time.Now().UTC()

	err := dm.DB.Save(subscription).Error
	if err != nil {
		return err
	}

	// Create update event
	event := &SubscriptionEvent{
		SubscriptionID: subscription.ID,
		UserID:         subscription.UserID,
		EventType:      "updated",
		OldStatus:      oldSub.Status,
		NewStatus:      subscription.Status,
		OldPlan:        oldSub.PlanType,
		NewPlan:        subscription.PlanType,
		CreatedAt:      time.Now().UTC(),
	}
	
	dm.DB.Create(event)

	// Invalidate user cache
	dm.invalidateUserCache(subscription.UserID)

	return nil
}

// CancelSubscription cancels a user's subscription
func (dm *DatabaseManager) CancelSubscription(userID uuid.UUID, reason string) error {
	var subscription Subscription
	err := dm.DB.Where("user_id = ? AND status = ?", userID, StatusActive).First(&subscription).Error
	if err != nil {
		return err
	}

	// Update subscription
	now := time.Now().UTC()
	subscription.Status = StatusCanceled
	subscription.CanceledAt = &now
	subscription.AutoRenew = false
	subscription.UpdatedAt = now

	err = dm.DB.Save(&subscription).Error
	if err != nil {
		return err
	}

	// Create cancellation event
	event := &SubscriptionEvent{
		SubscriptionID: subscription.ID,
		UserID:         userID,
		EventType:      "canceled",
		OldStatus:      StatusActive,
		NewStatus:      StatusCanceled,
		Metadata: JSONMap{
			"reason":      reason,
			"canceled_at": now.Format(time.RFC3339),
		},
		CreatedAt: now,
	}
	
	dm.DB.Create(event)

	// Invalidate user cache
	dm.invalidateUserCache(userID)

	return nil
}

// RecordUsage records usage for a user and resource type
func (dm *DatabaseManager) RecordUsage(userID uuid.UUID, resourceType ResourceType, quantity int, metadata map[string]interface{}) error {
	subscription, err := dm.GetSubscriptionByUserID(userID)
	if err != nil {
		// Create default free subscription if none exists
		subscription = &Subscription{
			UserID:       userID,
			PlanType:     PlanFree,
			Status:       StatusActive,
			BillingCycle: CycleMonthly,
			StartedAt:    time.Now().UTC(),
			AmountCents:  0,
			Currency:     "USD",
			AutoRenew:    true,
		}
		if err := dm.CreateSubscription(subscription); err != nil {
			log.Printf("Failed to create default subscription: %v", err)
		}
	}

	period := GetCurrentBillingPeriod(subscription)

	// Create usage record
	usage := &Usage{
		UserID:       userID,
		ResourceType: resourceType,
		Quantity:     quantity,
		PeriodStart:  period.Start,
		PeriodEnd:    period.End,
		RecordedAt:   time.Now().UTC(),
		CreatedAt:    time.Now().UTC(),
	}

	if metadata != nil {
		usage.Metadata = make(JSONMap)
		for k, v := range metadata {
			usage.Metadata[k] = v
		}
	}

	err = dm.DB.Create(usage).Error
	if err != nil {
		return err
	}

	// Update Redis counters
	if dm.RedisClient != nil {
		dm.updateUsageCounters(userID, resourceType, quantity, period)
	}

	// Invalidate quota cache
	dm.invalidateQuotaCache(userID, resourceType)

	return nil
}

// CheckUserQuota checks if user has quota remaining for a resource
func (dm *DatabaseManager) CheckUserQuota(userID uuid.UUID, resourceType ResourceType) (*QuotaInfo, error) {
	// Check Redis cache first
	if dm.RedisClient != nil {
		if cached := dm.getCachedQuota(userID, resourceType); cached != nil {
			return cached, nil
		}
	}

	subscription, err := dm.GetSubscriptionByUserID(userID)
	if err != nil {
		// Return free tier limits if no subscription
		return &QuotaInfo{
			UserID:       userID,
			ResourceType: resourceType,
			CurrentUsage: 0,
			MaxAllowed:   GetPlanDefaults(PlanFree)[string(resourceType)],
			Remaining:    GetPlanDefaults(PlanFree)[string(resourceType)],
			HasQuota:     true,
			PlanType:     string(PlanFree),
		}, nil
	}

	period := GetCurrentBillingPeriod(subscription)
	maxAllowed := subscription.GetLimit(resourceType)

	// Get current usage from database
	var currentUsage int64
	dm.DB.Model(&Usage{}).
		Where("user_id = ? AND resource_type = ? AND period_start = ? AND period_end = ?",
			userID, resourceType, period.Start, period.End).
		Select("COALESCE(SUM(quantity), 0)").
		Scan(&currentUsage)

	quotaInfo := &QuotaInfo{
		UserID:         userID,
		ResourceType:   resourceType,
		CurrentUsage:   int(currentUsage),
		MaxAllowed:     maxAllowed,
		Remaining:      maxAllowed - int(currentUsage),
		HasQuota:       int(currentUsage) < maxAllowed,
		PeriodStart:    period.Start,
		PeriodEnd:      period.End,
		ResetAt:        period.End,
		PlanType:       string(subscription.PlanType),
		OverageAllowed: subscription.PlanType == PlanEnterprise,
		OverageCost:    0, // TODO: Implement overage pricing
	}

	// Cache the result
	if dm.RedisClient != nil {
		dm.cacheQuota(quotaInfo)
	}

	return quotaInfo, nil
}

// GetUsageSummary returns usage summary for a user
func (dm *DatabaseManager) GetUsageSummary(userID uuid.UUID, days int) (map[string]interface{}, error) {
	subscription, err := dm.GetSubscriptionByUserID(userID)
	if err != nil {
		return nil, err
	}

	period := GetCurrentBillingPeriod(subscription)
	
	// Get usage breakdown by resource type
	type UsageBreakdown struct {
		ResourceType ResourceType `json:"resource_type"`
		TotalUsage   int64        `json:"total_usage"`
	}

	var breakdown []UsageBreakdown
	dm.DB.Model(&Usage{}).
		Select("resource_type, SUM(quantity) as total_usage").
		Where("user_id = ? AND recorded_at >= ? AND recorded_at <= ?",
			userID, period.Start, period.End).
		Group("resource_type").
		Scan(&breakdown)

	// Build summary
	summary := map[string]interface{}{
		"user_id":       userID,
		"plan_type":     subscription.PlanType,
		"period_start":  period.Start,
		"period_end":    period.End,
		"subscription_id": subscription.ID,
		"usage_breakdown": breakdown,
	}

	// Add quota information for each resource
	quotas := make(map[string]*QuotaInfo)
	for _, resourceType := range []ResourceType{ResourceMessages, ResourceAPICalls, ResourceBackgroundTasks} {
		quota, err := dm.CheckUserQuota(userID, resourceType)
		if err == nil {
			quotas[string(resourceType)] = quota
		}
	}
	summary["quotas"] = quotas

	return summary, nil
}

// HealthCheck performs database health checks
func (dm *DatabaseManager) HealthCheck() map[string]interface{} {
	health := map[string]interface{}{
		"postgresql": "healthy",
		"redis":      "healthy",
		"timestamp":  time.Now().UTC(),
	}

	// Check PostgreSQL
	sqlDB, err := dm.DB.DB()
	if err != nil || sqlDB.Ping() != nil {
		health["postgresql"] = "unhealthy"
	}

	// Check Redis
	if dm.RedisClient != nil {
		if err := dm.RedisClient.Ping(dm.ctx).Err(); err != nil {
			health["redis"] = "unhealthy"
		}
	} else {
		health["redis"] = "unavailable"
	}

	return health
}

// Cache management methods

func (dm *DatabaseManager) cacheSubscription(subscription *Subscription) {
	if dm.RedisClient == nil {
		return
	}

	cache := SubscriptionCache{
		UserID:         subscription.UserID,
		SubscriptionID: subscription.ID,
		PlanType:       subscription.PlanType,
		Status:         subscription.Status,
		Limits:         subscription.Limits,
		IsActive:       subscription.IsActive(),
		CachedAt:       time.Now().UTC(),
	}

	if subscription.EndsAt != nil {
		cache.ExpiresAt = *subscription.EndsAt
	}

	cacheKey := fmt.Sprintf("subscription:user:%s", subscription.UserID)
	data, _ := json.Marshal(cache)
	dm.RedisClient.Set(dm.ctx, cacheKey, data, 5*time.Minute).Err()
}

func (dm *DatabaseManager) cacheQuota(quota *QuotaInfo) {
	if dm.RedisClient == nil {
		return
	}

	cache := QuotaCache{
		UserID:       quota.UserID,
		ResourceType: quota.ResourceType,
		CurrentUsage: quota.CurrentUsage,
		MaxAllowed:   quota.MaxAllowed,
		PeriodStart:  quota.PeriodStart,
		PeriodEnd:    quota.PeriodEnd,
		CachedAt:     time.Now().UTC(),
	}

	cacheKey := fmt.Sprintf("quota:%s:%s", quota.UserID, quota.ResourceType)
	data, _ := json.Marshal(cache)
	dm.RedisClient.Set(dm.ctx, cacheKey, data, 1*time.Minute).Err()
}

func (dm *DatabaseManager) getCachedQuota(userID uuid.UUID, resourceType ResourceType) *QuotaInfo {
	if dm.RedisClient == nil {
		return nil
	}

	cacheKey := fmt.Sprintf("quota:%s:%s", userID, resourceType)
	cached, err := dm.RedisClient.Get(dm.ctx, cacheKey).Result()
	if err != nil {
		return nil
	}

	var cache QuotaCache
	if json.Unmarshal([]byte(cached), &cache) != nil {
		return nil
	}

	return &QuotaInfo{
		UserID:       cache.UserID,
		ResourceType: cache.ResourceType,
		CurrentUsage: cache.CurrentUsage,
		MaxAllowed:   cache.MaxAllowed,
		Remaining:    cache.MaxAllowed - cache.CurrentUsage,
		HasQuota:     cache.CurrentUsage < cache.MaxAllowed,
		PeriodStart:  cache.PeriodStart,
		PeriodEnd:    cache.PeriodEnd,
		ResetAt:      cache.PeriodEnd,
	}
}

func (dm *DatabaseManager) updateUsageCounters(userID uuid.UUID, resourceType ResourceType, quantity int, period BillingPeriod) {
	if dm.RedisClient == nil {
		return
	}

	// Update usage counter
	usageKey := RedisUsageKey{
		UserID:       userID,
		ResourceType: resourceType,
		Period:       period.Start.Format("2006-01"),
	}

	dm.RedisClient.IncrBy(dm.ctx, usageKey.String(), int64(quantity)).Err()
	dm.RedisClient.Expire(dm.ctx, usageKey.String(), 24*time.Hour).Err()
}

func (dm *DatabaseManager) invalidateUserCache(userID uuid.UUID) {
	if dm.RedisClient == nil {
		return
	}

	// Invalidate subscription cache
	subscriptionKey := fmt.Sprintf("subscription:user:%s", userID)
	dm.RedisClient.Del(dm.ctx, subscriptionKey).Err()

	// Invalidate quota caches
	for _, resourceType := range []ResourceType{ResourceMessages, ResourceAPICalls, ResourceBackgroundTasks, ResourceStorage, ResourceUsers} {
		quotaKey := fmt.Sprintf("quota:%s:%s", userID, resourceType)
		dm.RedisClient.Del(dm.ctx, quotaKey).Err()
	}
}

func (dm *DatabaseManager) invalidateQuotaCache(userID uuid.UUID, resourceType ResourceType) {
	if dm.RedisClient == nil {
		return
	}

	quotaKey := fmt.Sprintf("quota:%s:%s", userID, resourceType)
	dm.RedisClient.Del(dm.ctx, quotaKey).Err()
}

// getEnv gets environment variable with default value
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// Close closes database connections
func (dm *DatabaseManager) Close() error {
	// Close PostgreSQL connection
	if sqlDB, err := dm.DB.DB(); err == nil {
		sqlDB.Close()
	}

	// Close Redis connection
	if dm.RedisClient != nil {
		return dm.RedisClient.Close()
	}

	return nil
}

// GetCacheMetrics returns cache performance metrics
func (dm *DatabaseManager) GetCacheMetrics() map[string]*CacheStats {
	if dm.Cache != nil {
		return dm.Cache.GetCacheMetrics()
	}
	return make(map[string]*CacheStats)
}

// FlushCache clears all cache data
func (dm *DatabaseManager) FlushCache() error {
	if dm.Cache != nil && dm.RedisClient != nil {
		return dm.RedisClient.FlushAll(context.Background()).Err()
	}
	return nil
}

// WarmupCache preloads frequently accessed data
func (dm *DatabaseManager) WarmupCache() error {
	if dm.Cache != nil {
		ctx := context.Background()
		// Warmup operations
		dm.Cache.warmupSubscriptionPlans(ctx)
		dm.Cache.warmupActiveSubscriptions(ctx)
		dm.Cache.warmupUserQuotas(ctx)
	}
	return nil
}

// SetCacheEnabled enables or disables caching (placeholder implementation)
func (dm *DatabaseManager) SetCacheEnabled(enabled bool) {
	// Implementation would depend on cache configuration
}

// GetCache returns the cache instance
func (dm *DatabaseManager) GetCache() *RedisCache {
	return dm.Cache
}

// CreateEvent creates a new event record
func (dm *DatabaseManager) CreateEvent(event interface{}) error {
	return dm.DB.Create(event).Error
}

// GetDB returns the GORM database instance
func (dm *DatabaseManager) GetDB() *gorm.DB {
	return dm.DB
}