package main

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

type RedisCache struct {
	client *redis.Client
	logger *zap.Logger
	ctx    context.Context
}

func NewRedisCache(redisURL string, logger *zap.Logger) (*RedisCache, error) {
	// Parse Redis URL properly for production
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		// Fallback to localhost if URL parsing fails
		opt = &redis.Options{
			Addr:     "localhost:6379",
			Password: "",
			DB:       0,
		}
		logger.Warn("Failed to parse Redis URL, using localhost", zap.Error(err))
	}

	// Set production-ready timeouts
	opt.DialTimeout = 5 * time.Second
	opt.ReadTimeout = 3 * time.Second
	opt.WriteTimeout = 3 * time.Second
	opt.PoolTimeout = 10 * time.Second
	opt.MinIdleConns = 5
	opt.PoolSize = 20

	client := redis.NewClient(opt)
	ctx := context.Background()

	// Test connection with timeout
	testCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	
	_, err = client.Ping(testCtx).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	logger.Info("Redis cache initialized for billing service", 
		zap.String("addr", opt.Addr),
		zap.Int("pool_size", opt.PoolSize))

	return &RedisCache{
		client: client,
		logger: logger,
		ctx:    ctx,
	}, nil
}

func (c *RedisCache) Close() error {
	return c.client.Close()
}

func (c *RedisCache) Ping() error {
	return c.client.Ping(c.ctx).Err()
}

// Subscription caching
func (c *RedisCache) CacheSubscription(userID uuid.UUID, subscription *Subscription, ttl time.Duration) error {
	key := fmt.Sprintf("subscription:%s", userID.String())
	
	data, err := json.Marshal(subscription)
	if err != nil {
		return fmt.Errorf("failed to marshal subscription: %w", err)
	}

	err = c.client.Set(c.ctx, key, data, ttl).Err()
	if err != nil {
		c.logger.Error("Failed to cache subscription", 
			zap.String("user_id", userID.String()), 
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cached subscription", zap.String("user_id", userID.String()))
	return nil
}

func (c *RedisCache) GetCachedSubscription(userID uuid.UUID) (*Subscription, error) {
	key := fmt.Sprintf("subscription:%s", userID.String())
	
	data, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Cache miss
		}
		return nil, err
	}

	var subscription Subscription
	err = json.Unmarshal([]byte(data), &subscription)
	if err != nil {
		c.logger.Error("Failed to unmarshal cached subscription", zap.Error(err))
		return nil, err
	}

	c.logger.Debug("Cache hit for subscription", zap.String("user_id", userID.String()))
	return &subscription, nil
}

func (c *RedisCache) InvalidateSubscriptionCache(userID uuid.UUID) error {
	key := fmt.Sprintf("subscription:%s", userID.String())
	
	err := c.client.Del(c.ctx, key).Err()
	if err != nil {
		c.logger.Error("Failed to invalidate subscription cache", 
			zap.String("user_id", userID.String()), 
			zap.Error(err))
		return err
	}

	c.logger.Debug("Invalidated subscription cache", zap.String("user_id", userID.String()))
	return nil
}

// Quota caching
func (c *RedisCache) CacheQuota(userID uuid.UUID, resourceType string, quotaInfo *QuotaInfo, ttl time.Duration) error {
	key := fmt.Sprintf("quota:%s:%s", userID.String(), resourceType)
	
	data, err := json.Marshal(quotaInfo)
	if err != nil {
		return fmt.Errorf("failed to marshal quota info: %w", err)
	}

	err = c.client.Set(c.ctx, key, data, ttl).Err()
	if err != nil {
		c.logger.Error("Failed to cache quota", 
			zap.String("user_id", userID.String()), 
			zap.String("resource_type", resourceType),
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cached quota", 
		zap.String("user_id", userID.String()), 
		zap.String("resource_type", resourceType))
	return nil
}

func (c *RedisCache) GetCachedQuota(userID uuid.UUID, resourceType string) (*QuotaInfo, error) {
	key := fmt.Sprintf("quota:%s:%s", userID.String(), resourceType)
	
	data, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Cache miss
		}
		return nil, err
	}

	var quotaInfo QuotaInfo
	err = json.Unmarshal([]byte(data), &quotaInfo)
	if err != nil {
		c.logger.Error("Failed to unmarshal cached quota", zap.Error(err))
		return nil, err
	}

	c.logger.Debug("Cache hit for quota", 
		zap.String("user_id", userID.String()), 
		zap.String("resource_type", resourceType))
	return &quotaInfo, nil
}

func (c *RedisCache) InvalidateQuotaCache(userID uuid.UUID, resourceType string) error {
	key := fmt.Sprintf("quota:%s:%s", userID.String(), resourceType)
	
	err := c.client.Del(c.ctx, key).Err()
	if err != nil {
		c.logger.Error("Failed to invalidate quota cache", 
			zap.String("user_id", userID.String()), 
			zap.String("resource_type", resourceType),
			zap.Error(err))
		return err
	}

	c.logger.Debug("Invalidated quota cache", 
		zap.String("user_id", userID.String()), 
		zap.String("resource_type", resourceType))
	return nil
}

func (c *RedisCache) InvalidateUserCaches(userID uuid.UUID) error {
	// Get all keys for this user
	patterns := []string{
		fmt.Sprintf("subscription:%s", userID.String()),
		fmt.Sprintf("quota:%s:*", userID.String()),
		fmt.Sprintf("usage_summary:%s", userID.String()),
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

	// Delete all keys
	err := c.client.Del(c.ctx, allKeys...).Err()
	if err != nil {
		c.logger.Error("Failed to invalidate user caches", 
			zap.String("user_id", userID.String()), 
			zap.Error(err))
		return err
	}

	c.logger.Debug("Invalidated user caches", 
		zap.String("user_id", userID.String()), 
		zap.Int("keys_deleted", len(allKeys)))
	return nil
}

// Usage summary caching
func (c *RedisCache) CacheUsageSummary(userID uuid.UUID, summary *UsageSummary, ttl time.Duration) error {
	key := fmt.Sprintf("usage_summary:%s", userID.String())
	
	data, err := json.Marshal(summary)
	if err != nil {
		return fmt.Errorf("failed to marshal usage summary: %w", err)
	}

	err = c.client.Set(c.ctx, key, data, ttl).Err()
	if err != nil {
		c.logger.Error("Failed to cache usage summary", 
			zap.String("user_id", userID.String()), 
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cached usage summary", zap.String("user_id", userID.String()))
	return nil
}

func (c *RedisCache) GetCachedUsageSummary(userID uuid.UUID) (*UsageSummary, error) {
	key := fmt.Sprintf("usage_summary:%s", userID.String())
	
	data, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Cache miss
		}
		return nil, err
	}

	var summary UsageSummary
	err = json.Unmarshal([]byte(data), &summary)
	if err != nil {
		c.logger.Error("Failed to unmarshal cached usage summary", zap.Error(err))
		return nil, err
	}

	c.logger.Debug("Cache hit for usage summary", zap.String("user_id", userID.String()))
	return &summary, nil
}

// Rate limiting
func (c *RedisCache) CheckRateLimit(key string, limit int, window time.Duration) (bool, error) {
	pipe := c.client.Pipeline()
	
	// Increment the counter
	pipe.Incr(c.ctx, key)
	pipe.Expire(c.ctx, key, window)
	
	results, err := pipe.Exec(c.ctx)
	if err != nil {
		return false, err
	}

	// Get the count from the first command
	count := results[0].(*redis.IntCmd).Val()
	
	if count > int64(limit) {
		c.logger.Warn("Rate limit exceeded", 
			zap.String("key", key), 
			zap.Int64("count", count),
			zap.Int("limit", limit))
		return false, nil
	}

	return true, nil
}

// Health check specific cache operations
func (c *RedisCache) SetHealthStatus(service string, status map[string]interface{}) error {
	key := fmt.Sprintf("health:%s", service)
	
	data, err := json.Marshal(status)
	if err != nil {
		return fmt.Errorf("failed to marshal health status: %w", err)
	}

	return c.client.Set(c.ctx, key, data, 30*time.Second).Err()
}

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

// =============================================================================
// PERFORMANCE ENHANCEMENTS - Advanced Caching Strategies
// =============================================================================

// BatchGetSubscriptions retrieves multiple subscriptions in one operation
func (c *RedisCache) BatchGetSubscriptions(userIDs []uuid.UUID) (map[uuid.UUID]*Subscription, error) {
	if len(userIDs) == 0 {
		return make(map[uuid.UUID]*Subscription), nil
	}

	keys := make([]string, len(userIDs))
	for i, userID := range userIDs {
		keys[i] = fmt.Sprintf("subscription:%s", userID.String())
	}

	// Use pipeline for batch retrieval
	pipe := c.client.Pipeline()
	cmds := make([]*redis.StringCmd, len(keys))
	for i, key := range keys {
		cmds[i] = pipe.Get(c.ctx, key)
	}

	_, err := pipe.Exec(c.ctx)
	if err != nil && err != redis.Nil {
		return nil, err
	}

	result := make(map[uuid.UUID]*Subscription)
	for i, cmd := range cmds {
		if cmd.Err() == redis.Nil {
			continue // Cache miss
		}
		if cmd.Err() != nil {
			c.logger.Warn("Error retrieving subscription from cache", 
				zap.String("user_id", userIDs[i].String()),
				zap.Error(cmd.Err()))
			continue
		}

		var subscription Subscription
		err = json.Unmarshal([]byte(cmd.Val()), &subscription)
		if err != nil {
			c.logger.Error("Failed to unmarshal cached subscription", 
				zap.String("user_id", userIDs[i].String()),
				zap.Error(err))
			continue
		}

		result[userIDs[i]] = &subscription
	}

	c.logger.Debug("Batch retrieved subscriptions", 
		zap.Int("requested", len(userIDs)),
		zap.Int("cache_hits", len(result)))
	return result, nil
}

// CacheSubscriptionWithWriteThrough implements write-through caching
func (c *RedisCache) CacheSubscriptionWithWriteThrough(userID uuid.UUID, subscription *Subscription, ttl time.Duration) error {
	// Set main cache
	if err := c.CacheSubscription(userID, subscription, ttl); err != nil {
		return err
	}

	// Cache derived data for quick lookups
	pipe := c.client.Pipeline()
	
	// Cache plan type for quick plan-based queries
	planKey := fmt.Sprintf("user_plan:%s", userID.String())
	pipe.Set(c.ctx, planKey, string(subscription.PlanType), ttl)
	
	// Cache active status for authorization checks
	statusKey := fmt.Sprintf("subscription_active:%s", userID.String())
	pipe.Set(c.ctx, statusKey, subscription.Status == "active", ttl)
	
	// Cache expiration for proactive renewal notifications
	if subscription.EndsAt != nil {
		expiryKey := fmt.Sprintf("subscription_expires:%s", userID.String())
		pipe.Set(c.ctx, expiryKey, subscription.EndsAt.Unix(), ttl)
	}

	_, err := pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to cache subscription metadata",
			zap.String("user_id", userID.String()),
			zap.Error(err))
		// Don't fail the main operation for metadata caching errors
	}

	return nil
}

// GetQuotaRemaining provides ultra-fast quota remaining check
func (c *RedisCache) GetQuotaRemaining(userID uuid.UUID, resourceType string) (int, error) {
	key := fmt.Sprintf("quota_remaining:%s:%s", userID.String(), resourceType)
	
	remaining, err := c.client.Get(c.ctx, key).Int()
	if err != nil {
		if err == redis.Nil {
			return -1, nil // Not cached
		}
		return 0, err
	}

	return remaining, nil
}

// UpdateQuotaAtomic atomically updates quota with consistency guarantees
func (c *RedisCache) UpdateQuotaAtomic(userID uuid.UUID, resourceType string, usageIncrement int, maxAllowed int, ttl time.Duration) (int, bool, error) {
	quotaKey := fmt.Sprintf("quota:%s:%s", userID.String(), resourceType)
	remainingKey := fmt.Sprintf("quota_remaining:%s:%s", userID.String(), resourceType)
	
	// Lua script for atomic quota update with overflow protection
	luaScript := `
		local quota_key = KEYS[1]
		local remaining_key = KEYS[2]
		local increment = tonumber(ARGV[1])
		local max_allowed = tonumber(ARGV[2])
		local ttl = tonumber(ARGV[3])
		
		-- Get current usage or initialize to 0
		local current_usage = redis.call('HGET', quota_key, 'current_usage') or 0
		current_usage = tonumber(current_usage)
		
		-- Check if increment would exceed limit
		local new_usage = current_usage + increment
		if new_usage > max_allowed then
			return {current_usage, max_allowed - current_usage, 0} -- usage, remaining, allowed (0=false)
		end
		
		-- Update usage atomically
		redis.call('HSET', quota_key, 'current_usage', new_usage)
		redis.call('HSET', quota_key, 'max_allowed', max_allowed)
		redis.call('HSET', quota_key, 'updated_at', ARGV[4])
		redis.call('EXPIRE', quota_key, ttl)
		
		-- Update remaining count
		local remaining = max_allowed - new_usage
		redis.call('SET', remaining_key, remaining, 'EX', ttl)
		
		return {new_usage, remaining, 1} -- usage, remaining, allowed (1=true)
	`

	result, err := c.client.Eval(c.ctx, luaScript, []string{quotaKey, remainingKey}, 
		usageIncrement, maxAllowed, int(ttl.Seconds()), time.Now().Unix()).Result()
	
	if err != nil {
		return 0, false, fmt.Errorf("failed to update quota atomically: %w", err)
	}

	resultSlice, ok := result.([]interface{})
	if !ok || len(resultSlice) != 3 {
		return 0, false, fmt.Errorf("unexpected script result format")
	}

	currentUsage := int(resultSlice[0].(int64))
	remaining := int(resultSlice[1].(int64))
	allowed := resultSlice[2].(int64) == 1

	if !allowed {
		c.logger.Warn("Quota exceeded",
			zap.String("user_id", userID.String()),
			zap.String("resource_type", resourceType),
			zap.Int("current_usage", currentUsage),
			zap.Int("increment", usageIncrement),
			zap.Int("max_allowed", maxAllowed))
	}

	return remaining, allowed, nil
}

// WarmupUserCache preloads frequently accessed user data
func (c *RedisCache) WarmupUserCache(userIDs []uuid.UUID, ttl time.Duration) error {
	if len(userIDs) == 0 {
		return nil
	}

	// This would typically be called with database data
	// Implementation depends on having access to database layer
	c.logger.Info("Cache warmup initiated", zap.Int("user_count", len(userIDs)))
	
	// Pipeline warmup operations
	pipe := c.client.Pipeline()
	
	for _, userID := range userIDs {
		// Warmup common access patterns
		healthKey := fmt.Sprintf("user_health:%s", userID.String())
		pipe.Set(c.ctx, healthKey, `{"warmup": true}`, ttl)
	}
	
	_, err := pipe.Exec(c.ctx)
	return err
}

// GetCacheStats returns comprehensive cache performance metrics
func (c *RedisCache) GetCacheStats() (map[string]interface{}, error) {
	info, err := c.client.Info(c.ctx, "memory", "stats", "keyspace").Result()
	if err != nil {
		return nil, err
	}

	// Get connection pool stats
	poolStats := c.client.PoolStats()
	
	stats := map[string]interface{}{
		"timestamp":       time.Now().Unix(),
		"connected":       c.Ping() == nil,
		"pool_hits":       poolStats.Hits,
		"pool_misses":     poolStats.Misses,
		"pool_timeouts":   poolStats.Timeouts,
		"total_conns":     poolStats.TotalConns,
		"idle_conns":      poolStats.IdleConns,
		"stale_conns":     poolStats.StaleConns,
		"redis_info":      info,
		"service":         "billing-cache",
	}

	return stats, nil
}