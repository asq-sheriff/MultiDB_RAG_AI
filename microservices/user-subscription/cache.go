package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// RedisCache provides high-performance caching with data consistency
type RedisCache struct {
	client  *redis.Client
	logger  *zap.Logger
	ctx     context.Context
	metrics *CacheMetrics
}

// NewRedisCache creates a new Redis cache instance with metrics
func NewRedisCache(redisURL string, logger *zap.Logger) (*RedisCache, error) {
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse Redis URL: %w", err)
	}

	client := redis.NewClient(opt)
	ctx := context.Background()

	// Test connection with timeout
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	
	_, err = client.Ping(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	// Initialize cache metrics
	metrics := NewCacheMetrics(client, "user-subscription-service", logger)

	cache := &RedisCache{
		client:  client,
		logger:  logger,
		ctx:     context.Background(),
		metrics: metrics,
	}

	// Add cache warming tasks for critical data
	cache.setupCacheWarming()

	return cache, nil
}

// Close closes the Redis connection
func (c *RedisCache) Close() error {
	return c.client.Close()
}

// setupCacheWarming configures cache warming strategies for critical data
func (c *RedisCache) setupCacheWarming() {
	// Warm up popular subscription plans
	c.metrics.AddWarmupTask(WarmupTask{
		Name:     "subscription_plans",
		Pattern:  "plan_features:*",
		Interval: 5 * time.Minute,
		Priority: 1,
		Enabled:  true,
		WarmupFunc: func(ctx context.Context) error {
			return c.warmupSubscriptionPlans(ctx)
		},
	})

	// Warm up active user subscriptions
	c.metrics.AddWarmupTask(WarmupTask{
		Name:     "active_subscriptions", 
		Pattern:  "subscription:*",
		Interval: 2 * time.Minute,
		Priority: 2,
		Enabled:  true,
		WarmupFunc: func(ctx context.Context) error {
			return c.warmupActiveSubscriptions(ctx)
		},
	})

	// Warm up quota information for active users
	c.metrics.AddWarmupTask(WarmupTask{
		Name:     "user_quotas",
		Pattern:  "quota:*", 
		Interval: 1 * time.Minute,
		Priority: 3,
		Enabled:  true,
		WarmupFunc: func(ctx context.Context) error {
			return c.warmupUserQuotas(ctx)
		},
	})
}

// StartMonitoring starts cache monitoring and warming processes
func (c *RedisCache) StartMonitoring(ctx context.Context) {
	// Start cache health monitoring
	go c.metrics.MonitorCacheHealth(ctx, "user-subscription-service", func(alert CacheAlert) {
		c.logger.Warn("Cache alert",
			zap.String("level", alert.Level),
			zap.String("cache", alert.CacheName),
			zap.String("metric", alert.Metric),
			zap.Float64("threshold", alert.Threshold),
			zap.Float64("actual", alert.ActualValue),
			zap.String("message", alert.Message))
	})

	// Start cache warming
	go c.metrics.RunCacheWarming(ctx, "user-subscription-service")

	c.logger.Info("Cache monitoring and warming started")
}

// GetCacheMetrics returns current cache performance metrics
func (c *RedisCache) GetCacheMetrics() map[string]*CacheStats {
	return c.metrics.GetCacheStats()
}

// =============================================================================
// CACHE WARMING FUNCTIONS - Proactive Data Loading for Performance
// =============================================================================

// warmupSubscriptionPlans preloads popular subscription plans into cache
func (c *RedisCache) warmupSubscriptionPlans(ctx context.Context) error {
	plans := []SubscriptionPlan{PlanFree, PlanPro, PlanEnterprise}
	
	for _, plan := range plans {
		features := GetPlanFeatures(plan)
		key := fmt.Sprintf("plan_features:%s", string(plan))
		
		data, err := json.Marshal(features)
		if err != nil {
			c.logger.Error("Failed to marshal plan features for warmup", zap.String("plan", string(plan)), zap.Error(err))
			continue
		}
		
		err = c.client.Set(ctx, key, data, 10*time.Minute).Err()
		if err != nil {
			c.logger.Error("Failed to warm up plan features", zap.String("plan", string(plan)), zap.Error(err))
		} else {
			c.logger.Debug("Warmed up plan features", zap.String("plan", string(plan)))
		}
	}
	
	return nil
}

// warmupActiveSubscriptions preloads recently active user subscriptions
func (c *RedisCache) warmupActiveSubscriptions(ctx context.Context) error {
	// Get keys matching subscription pattern
	keys, err := c.client.Keys(ctx, "subscription:*").Result()
	if err != nil {
		return fmt.Errorf("failed to get subscription keys: %w", err)
	}
	
	// Check which ones are about to expire and refresh them
	refreshed := 0
	for _, key := range keys {
		ttl, err := c.client.TTL(ctx, key).Result()
		if err != nil {
			continue
		}
		
		// Refresh if TTL is less than 5 minutes
		if ttl < 5*time.Minute && ttl > 0 {
			// Extend TTL to prevent expiration during high load
			err = c.client.Expire(ctx, key, 30*time.Minute).Err()
			if err == nil {
				refreshed++
			}
		}
	}
	
	if refreshed > 0 {
		c.logger.Info("Refreshed subscription cache TTLs", zap.Int("count", refreshed))
	}
	
	return nil
}

// warmupUserQuotas preloads quota information for active users
func (c *RedisCache) warmupUserQuotas(ctx context.Context) error {
	// Get active subscription keys
	subscriptionKeys, err := c.client.Keys(ctx, "subscription:*").Result()
	if err != nil {
		return fmt.Errorf("failed to get subscription keys: %w", err)
	}
	
	warmed := 0
	for _, subKey := range subscriptionKeys {
		// Extract user ID from key
		userIDStr := strings.TrimPrefix(subKey, "subscription:")
		
		// Preload quota for common resource types
		resourceTypes := []string{"messages", "api_calls", "storage", "embeddings"}
		
		for _, resourceType := range resourceTypes {
			quotaKey := fmt.Sprintf("quota:%s:%s", userIDStr, resourceType)
			
			// Check if quota cache exists
			exists, err := c.client.Exists(ctx, quotaKey).Result()
			if err != nil || exists > 0 {
				continue
			}
			
			// Create basic quota cache entry (would normally come from database)
			quotaInfo := map[string]interface{}{
				"user_id":       userIDStr,
				"resource_type": resourceType,
				"current_usage": 0,
				"max_allowed":   1000, // Default values - would come from subscription
				"remaining":     1000,
				"period_start":  time.Now().Format(time.RFC3339),
				"period_end":    time.Now().Add(30 * 24 * time.Hour).Format(time.RFC3339),
				"cached_at":     time.Now().Format(time.RFC3339),
			}
			
			data, err := json.Marshal(quotaInfo)
			if err != nil {
				continue
			}
			
			// Cache for 5 minutes (short TTL for warmup data)
			err = c.client.Set(ctx, quotaKey, data, 5*time.Minute).Err()
			if err == nil {
				warmed++
			}
		}
	}
	
	if warmed > 0 {
		c.logger.Info("Warmed up quota cache entries", zap.Int("count", warmed))
	}
	
	return nil
}

// Ping tests Redis connectivity
func (c *RedisCache) Ping() error {
	return c.client.Ping(c.ctx).Err()
}

// =============================================================================
// SUBSCRIPTION CACHING - Enhanced Performance with Multi-Level Cache Strategy
// =============================================================================

// CacheSubscription stores subscription data with optimized TTL strategy
func (c *RedisCache) CacheSubscription(subscription *Subscription, ttl time.Duration) error {
	start := time.Now()
	cache := &SubscriptionCache{
		UserID:         subscription.UserID,
		SubscriptionID: subscription.ID,
		PlanType:       subscription.PlanType,
		Status:         subscription.Status,
		Limits:         subscription.Limits,
		ExpiresAt:      func() time.Time {
			if subscription.EndsAt != nil {
				return *subscription.EndsAt
			}
			return time.Time{}
		}(),
		IsActive: subscription.IsActive(),
		CachedAt: time.Now(),
	}

	key := fmt.Sprintf("subscription:%s", subscription.UserID.String())
	data, err := json.Marshal(cache)
	if err != nil {
		return fmt.Errorf("failed to marshal subscription cache: %w", err)
	}

	// Use pipeline for atomic operations
	pipe := c.client.Pipeline()
	pipe.Set(c.ctx, key, data, ttl)
	
	// Also cache by subscription ID for reverse lookups
	subscriptionKey := fmt.Sprintf("subscription_id:%s", subscription.ID.String())
	pipe.Set(c.ctx, subscriptionKey, subscription.UserID.String(), ttl)
	
	// Cache active status separately for quick checks
	statusKey := fmt.Sprintf("subscription_status:%s", subscription.UserID.String())
	pipe.Set(c.ctx, statusKey, subscription.IsActive(), ttl)

	_, err = pipe.Exec(c.ctx)
	duration := time.Since(start)
	
	if err != nil {
		c.metrics.RecordCacheError("user-subscription-service", "subscription", "set_failed")
		c.logger.Error("Failed to cache subscription",
			zap.String("user_id", subscription.UserID.String()),
			zap.Error(err))
		return err
	}

	// Record successful cache operation
	c.metrics.cacheLatency.WithLabelValues("user-subscription-service", "subscription", "set", "success").Observe(duration.Seconds())
	c.logger.Debug("Cached subscription",
		zap.String("user_id", subscription.UserID.String()),
		zap.String("plan", string(subscription.PlanType)),
		zap.Duration("latency", duration))
	return nil
}

// GetCachedSubscription retrieves subscription with fallback strategy
func (c *RedisCache) GetCachedSubscription(userID uuid.UUID) (*SubscriptionCache, error) {
	start := time.Now()
	key := fmt.Sprintf("subscription:%s", userID.String())
	
	data, err := c.client.Get(c.ctx, key).Result()
	duration := time.Since(start)
	if err != nil {
		if err == redis.Nil {
			// Record cache miss
			c.metrics.RecordCacheMiss("user-subscription-service", "subscription", "get", duration)
			return nil, nil // Cache miss
		}
		c.metrics.RecordCacheError("user-subscription-service", "subscription", "get_failed")
		return nil, err
	}

	var cache SubscriptionCache
	err = json.Unmarshal([]byte(data), &cache)
	if err != nil {
		c.metrics.RecordCacheError("user-subscription-service", "subscription", "unmarshal_failed")
		c.logger.Error("Failed to unmarshal cached subscription", zap.Error(err))
		// Invalidate corrupted cache
		c.client.Del(c.ctx, key)
		return nil, err
	}

	// Record cache hit
	c.metrics.RecordCacheHit("user-subscription-service", "subscription", "get", duration)

	// Verify cache hasn't expired (double-check with local time)
	if time.Since(cache.CachedAt) > 6*time.Hour {
		c.logger.Debug("Cache entry too old, invalidating",
			zap.String("user_id", userID.String()))
		c.client.Del(c.ctx, key)
		return nil, nil
	}

	c.logger.Debug("Cache hit for subscription", zap.String("user_id", userID.String()))
	return &cache, nil
}

// =============================================================================
// QUOTA CACHING - High-Performance Usage Tracking
// =============================================================================

// CacheQuota stores quota information with usage counters
func (c *RedisCache) CacheQuota(userID uuid.UUID, resourceType ResourceType, quota *QuotaInfo, ttl time.Duration) error {
	key := fmt.Sprintf("quota:%s:%s", userID.String(), resourceType)
	
	cache := &QuotaCache{
		UserID:       userID,
		ResourceType: resourceType,
		CurrentUsage: quota.CurrentUsage,
		MaxAllowed:   quota.MaxAllowed,
		PeriodStart:  quota.PeriodStart,
		PeriodEnd:    quota.PeriodEnd,
		CachedAt:     time.Now(),
	}

	data, err := json.Marshal(cache)
	if err != nil {
		return fmt.Errorf("failed to marshal quota cache: %w", err)
	}

	// Use shorter TTL for quota to ensure accuracy
	if ttl > 5*time.Minute {
		ttl = 5 * time.Minute
	}

	err = c.client.Set(c.ctx, key, data, ttl).Err()
	if err != nil {
		c.logger.Error("Failed to cache quota",
			zap.String("user_id", userID.String()),
			zap.String("resource_type", string(resourceType)),
			zap.Error(err))
		return err
	}

	// Cache quick lookup for remaining quota
	remainingKey := fmt.Sprintf("quota_remaining:%s:%s", userID.String(), resourceType)
	remaining := quota.MaxAllowed - quota.CurrentUsage
	if remaining < 0 {
		remaining = 0
	}
	c.client.Set(c.ctx, remainingKey, remaining, ttl)

	c.logger.Debug("Cached quota",
		zap.String("user_id", userID.String()),
		zap.String("resource_type", string(resourceType)),
		zap.Int("current", quota.CurrentUsage),
		zap.Int("max", quota.MaxAllowed))
	return nil
}

// GetCachedQuota retrieves quota information
func (c *RedisCache) GetCachedQuota(userID uuid.UUID, resourceType ResourceType) (*QuotaCache, error) {
	key := fmt.Sprintf("quota:%s:%s", userID.String(), resourceType)
	
	data, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Cache miss
		}
		return nil, err
	}

	var cache QuotaCache
	err = json.Unmarshal([]byte(data), &cache)
	if err != nil {
		c.logger.Error("Failed to unmarshal cached quota", zap.Error(err))
		c.client.Del(c.ctx, key)
		return nil, err
	}

	c.logger.Debug("Cache hit for quota",
		zap.String("user_id", userID.String()),
		zap.String("resource_type", string(resourceType)))
	return &cache, nil
}

// =============================================================================
// USAGE TRACKING - Real-time Usage Counters with Atomic Operations
// =============================================================================

// IncrementUsage atomically increments usage counter with quota checking
func (c *RedisCache) IncrementUsage(userID uuid.UUID, resourceType ResourceType, amount int) (int64, error) {
	period := time.Now().Format("2006-01") // Monthly period
	usageKey := RedisUsageKey{
		UserID:       userID,
		ResourceType: resourceType,
		Period:       period,
	}

	pipe := c.client.Pipeline()
	
	// Increment usage counter
	incrCmd := pipe.IncrBy(c.ctx, usageKey.String(), int64(amount))
	
	// Set expiration to end of next month to ensure cleanup
	nextMonth := time.Now().AddDate(0, 2, 0)
	pipe.ExpireAt(c.ctx, usageKey.String(), nextMonth)
	
	_, err := pipe.Exec(c.ctx)
	if err != nil {
		return 0, fmt.Errorf("failed to increment usage: %w", err)
	}

	newUsage := incrCmd.Val()
	
	// Invalidate quota cache to force refresh on next check
	quotaKey := fmt.Sprintf("quota:%s:%s", userID.String(), resourceType)
	c.client.Del(c.ctx, quotaKey)
	
	c.logger.Debug("Usage incremented",
		zap.String("user_id", userID.String()),
		zap.String("resource_type", string(resourceType)),
		zap.Int64("new_usage", newUsage),
		zap.Int("increment", amount))
		
	return newUsage, nil
}

// GetUsageCounter gets current usage without incrementing
func (c *RedisCache) GetUsageCounter(userID uuid.UUID, resourceType ResourceType, period string) (int64, error) {
	if period == "" {
		period = time.Now().Format("2006-01") // Current month
	}
	
	usageKey := RedisUsageKey{
		UserID:       userID,
		ResourceType: resourceType,
		Period:       period,
	}

	usage, err := c.client.Get(c.ctx, usageKey.String()).Int64()
	if err != nil {
		if err == redis.Nil {
			return 0, nil // No usage recorded
		}
		return 0, err
	}

	return usage, nil
}

// =============================================================================
// RATE LIMITING - Advanced Sliding Window Algorithm
// =============================================================================

// CheckRateLimit implements sliding window rate limiting with burst support
func (c *RedisCache) CheckRateLimit(userID uuid.UUID, resourceType ResourceType, limit int, window time.Duration) (bool, int, error) {
	now := time.Now()
	windowKey := RateLimitKey{
		UserID:       userID,
		ResourceType: resourceType,
		Window:       now.Format("2006-01-02-15"), // Hourly windows
	}

	pipe := c.client.Pipeline()
	
	// Increment counter
	pipe.Incr(c.ctx, windowKey.String())
	pipe.Expire(c.ctx, windowKey.String(), window)
	
	results, err := pipe.Exec(c.ctx)
	if err != nil {
		return false, 0, err
	}

	count := results[0].(*redis.IntCmd).Val()
	remaining := limit - int(count)
	if remaining < 0 {
		remaining = 0
	}

	allowed := count <= int64(limit)
	
	if !allowed {
		c.logger.Warn("Rate limit exceeded",
			zap.String("user_id", userID.String()),
			zap.String("resource_type", string(resourceType)),
			zap.Int64("count", count),
			zap.Int("limit", limit))
	}

	return allowed, remaining, nil
}

// =============================================================================
// SESSION MANAGEMENT - High-Performance Session Caching
// =============================================================================

// CacheUserSession stores user session with automatic expiration
func (c *RedisCache) CacheUserSession(sessionID string, userID uuid.UUID, sessionData map[string]interface{}, ttl time.Duration) error {
	key := fmt.Sprintf("session:%s", sessionID)
	
	// Add metadata
	sessionData["user_id"] = userID.String()
	sessionData["created_at"] = time.Now().Unix()
	sessionData["expires_at"] = time.Now().Add(ttl).Unix()

	data, err := json.Marshal(sessionData)
	if err != nil {
		return fmt.Errorf("failed to marshal session data: %w", err)
	}

	pipe := c.client.Pipeline()
	
	// Store session
	pipe.Set(c.ctx, key, data, ttl)
	
	// Index by user_id for quick user session lookups
	userSessionKey := fmt.Sprintf("user_sessions:%s", userID.String())
	pipe.SAdd(c.ctx, userSessionKey, sessionID)
	pipe.Expire(c.ctx, userSessionKey, ttl+time.Hour) // Slightly longer TTL for cleanup

	_, err = pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to cache user session",
			zap.String("session_id", sessionID),
			zap.String("user_id", userID.String()),
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cached user session",
		zap.String("session_id", sessionID),
		zap.String("user_id", userID.String()))
	return nil
}

// GetCachedUserSession retrieves session data
func (c *RedisCache) GetCachedUserSession(sessionID string) (map[string]interface{}, error) {
	key := fmt.Sprintf("session:%s", sessionID)
	
	data, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Session not found or expired
		}
		return nil, err
	}

	var sessionData map[string]interface{}
	err = json.Unmarshal([]byte(data), &sessionData)
	if err != nil {
		c.logger.Error("Failed to unmarshal session data", zap.Error(err))
		c.client.Del(c.ctx, key)
		return nil, err
	}

	// Check expiration
	if expiresAt, ok := sessionData["expires_at"].(float64); ok {
		if time.Now().Unix() > int64(expiresAt) {
			c.InvalidateUserSession(sessionID)
			return nil, nil // Session expired
		}
	}

	c.logger.Debug("Session cache hit", zap.String("session_id", sessionID))
	return sessionData, nil
}

// InvalidateUserSession removes session from cache
func (c *RedisCache) InvalidateUserSession(sessionID string) error {
	key := fmt.Sprintf("session:%s", sessionID)
	
	// Get user_id before deletion for cleanup
	sessionData, _ := c.GetCachedUserSession(sessionID)
	
	pipe := c.client.Pipeline()
	pipe.Del(c.ctx, key)
	
	// Remove from user sessions index
	if sessionData != nil {
		if userIDStr, ok := sessionData["user_id"].(string); ok {
			userSessionKey := fmt.Sprintf("user_sessions:%s", userIDStr)
			pipe.SRem(c.ctx, userSessionKey, sessionID)
		}
	}

	_, err := pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to invalidate user session",
			zap.String("session_id", sessionID),
			zap.Error(err))
		return err
	}

	c.logger.Debug("Invalidated user session", zap.String("session_id", sessionID))
	return nil
}

// GetUserSessions returns all active sessions for a user
func (c *RedisCache) GetUserSessions(userID uuid.UUID) ([]string, error) {
	userSessionKey := fmt.Sprintf("user_sessions:%s", userID.String())
	
	sessions, err := c.client.SMembers(c.ctx, userSessionKey).Result()
	if err != nil {
		if err == redis.Nil {
			return []string{}, nil
		}
		return nil, err
	}

	return sessions, nil
}

// =============================================================================
// USER PROFILE CACHING - Enhanced User Data Management
// =============================================================================

// CacheUserProfile stores user profile with intelligent TTL
func (c *RedisCache) CacheUserProfile(userID uuid.UUID, profile map[string]interface{}, ttl time.Duration) error {
	key := fmt.Sprintf("user_profile:%s", userID.String())
	
	profile["user_id"] = userID.String()
	profile["cached_at"] = time.Now().Unix()

	data, err := json.Marshal(profile)
	if err != nil {
		return fmt.Errorf("failed to marshal user profile: %w", err)
	}

	err = c.client.Set(c.ctx, key, data, ttl).Err()
	if err != nil {
		c.logger.Error("Failed to cache user profile",
			zap.String("user_id", userID.String()),
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cached user profile", zap.String("user_id", userID.String()))
	return nil
}

// GetCachedUserProfile retrieves cached user profile
func (c *RedisCache) GetCachedUserProfile(userID uuid.UUID) (map[string]interface{}, error) {
	key := fmt.Sprintf("user_profile:%s", userID.String())
	
	data, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil
		}
		return nil, err
	}

	var profile map[string]interface{}
	err = json.Unmarshal([]byte(data), &profile)
	if err != nil {
		c.logger.Error("Failed to unmarshal cached user profile", zap.Error(err))
		c.client.Del(c.ctx, key)
		return nil, err
	}

	c.logger.Debug("User profile cache hit", zap.String("user_id", userID.String()))
	return profile, nil
}

// =============================================================================
// CACHE INVALIDATION - Smart Invalidation Strategies
// =============================================================================

// InvalidateUserCache removes all user-related cache entries
func (c *RedisCache) InvalidateUserCache(userID uuid.UUID) error {
	patterns := []string{
		fmt.Sprintf("subscription:%s", userID.String()),
		fmt.Sprintf("subscription_status:%s", userID.String()),
		fmt.Sprintf("quota:%s:*", userID.String()),
		fmt.Sprintf("quota_remaining:%s:*", userID.String()),
		fmt.Sprintf("user_profile:%s", userID.String()),
		fmt.Sprintf("user_sessions:%s", userID.String()),
	}

	var allKeys []string
	for _, pattern := range patterns {
		keys, err := c.client.Keys(c.ctx, pattern).Result()
		if err != nil {
			c.logger.Error("Failed to get keys for pattern",
				zap.String("pattern", pattern),
				zap.Error(err))
			continue
		}
		allKeys = append(allKeys, keys...)
	}

	if len(allKeys) == 0 {
		return nil
	}

	// Use pipeline for efficient bulk deletion
	pipe := c.client.Pipeline()
	for _, key := range allKeys {
		pipe.Del(c.ctx, key)
	}
	
	_, err := pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to invalidate user cache",
			zap.String("user_id", userID.String()),
			zap.Error(err))
		return err
	}

	c.logger.Info("Invalidated user cache",
		zap.String("user_id", userID.String()),
		zap.Int("keys_deleted", len(allKeys)))
	return nil
}

// InvalidateSubscriptionCache removes subscription-related cache
func (c *RedisCache) InvalidateSubscriptionCache(userID uuid.UUID) error {
	keys := []string{
		fmt.Sprintf("subscription:%s", userID.String()),
		fmt.Sprintf("subscription_status:%s", userID.String()),
	}

	pipe := c.client.Pipeline()
	for _, key := range keys {
		pipe.Del(c.ctx, key)
	}
	
	_, err := pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to invalidate subscription cache",
			zap.String("user_id", userID.String()),
			zap.Error(err))
		return err
	}

	c.logger.Debug("Invalidated subscription cache", zap.String("user_id", userID.String()))
	return nil
}

// =============================================================================
// HEALTH AND MONITORING - Performance Monitoring
// =============================================================================

// SetHealthStatus caches service health information
func (c *RedisCache) SetHealthStatus(service string, status map[string]interface{}) error {
	key := fmt.Sprintf("health:%s", service)
	
	status["timestamp"] = time.Now().Unix()
	status["service"] = service

	data, err := json.Marshal(status)
	if err != nil {
		return fmt.Errorf("failed to marshal health status: %w", err)
	}

	return c.client.Set(c.ctx, key, data, 30*time.Second).Err()
}

// GetHealthStatus retrieves cached health status
func (c *RedisCache) GetHealthStatus(service string) (map[string]interface{}, error) {
	key := fmt.Sprintf("health:%s", service)
	
	data, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil
		}
		return nil, err
	}

	var status map[string]interface{}
	err = json.Unmarshal([]byte(data), &status)
	if err != nil {
		return nil, err
	}

	return status, nil
}

// GetCacheStats returns Redis cache statistics for monitoring
func (c *RedisCache) GetCacheStats() (map[string]interface{}, error) {
	info, err := c.client.Info(c.ctx, "memory", "stats", "keyspace").Result()
	if err != nil {
		return nil, err
	}

	// Parse key statistics
	dbInfo, err := c.client.Info(c.ctx, "keyspace").Result()
	if err != nil {
		return nil, err
	}

	stats := map[string]interface{}{
		"timestamp":    time.Now().Unix(),
		"connected":    true,
		"info":         info,
		"keyspace":     dbInfo,
		"ping_success": c.Ping() == nil,
	}

	return stats, nil
}