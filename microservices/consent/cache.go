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

func NewRedisCache(redisURL string) (*RedisCache, error) {
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse Redis URL: %w", err)
	}

	client := redis.NewClient(opt)
	ctx := context.Background()

	// Test connection
	_, err = client.Ping(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	logger, _ := zap.NewProduction()

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

// Generic cache operations
func (c *RedisCache) Set(key, value string, expiration time.Duration) error {
	err := c.client.Set(c.ctx, key, value, expiration).Err()
	if err != nil {
		c.logger.Error("Failed to set cache key",
			zap.String("key", key),
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cache set", zap.String("key", key))
	return nil
}

// Legacy Set method for backwards compatibility with internal methods
func (c *RedisCache) SetObject(key string, value interface{}, expiration time.Duration) error {
	jsonData, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("failed to marshal value: %w", err)
	}

	err = c.client.Set(c.ctx, key, jsonData, expiration).Err()
	if err != nil {
		c.logger.Error("Failed to set cache key", 
			zap.String("key", key), 
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cache set", zap.String("key", key))
	return nil
}

func (c *RedisCache) Get(key string) (string, error) {
	val, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return "", nil // Key does not exist
		}
		c.logger.Error("Failed to get cache key", 
			zap.String("key", key), 
			zap.Error(err))
		return "", err
	}

	c.logger.Debug("Cache hit", zap.String("key", key))
	return val, nil
}

// Legacy GetObject method for backwards compatibility
func (c *RedisCache) GetObject(key string) (interface{}, error) {
	val, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Key does not exist
		}
		c.logger.Error("Failed to get cache key", 
			zap.String("key", key), 
			zap.Error(err))
		return nil, err
	}

	var result interface{}
	err = json.Unmarshal([]byte(val), &result)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal cached value: %w", err)
	}

	c.logger.Debug("Cache hit", zap.String("key", key))
	return result, nil
}

func (c *RedisCache) Delete(key string) error {
	err := c.client.Del(c.ctx, key).Err()
	if err != nil {
		c.logger.Error("Failed to delete cache key", 
			zap.String("key", key), 
			zap.Error(err))
		return err
	}

	c.logger.Debug("Cache deleted", zap.String("key", key))
	return nil
}

func (c *RedisCache) Exists(key string) (bool, error) {
	count, err := c.client.Exists(c.ctx, key).Result()
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

// HIPAA-specific cache operations with automatic invalidation
func (c *RedisCache) InvalidatePatientConsents(patientID uuid.UUID) error {
	// Invalidate both active and all consents caches
	keys := []string{
		fmt.Sprintf("patient_consents:%s:true", patientID.String()),
		fmt.Sprintf("patient_consents:%s:false", patientID.String()),
	}

	pipe := c.client.Pipeline()
	for _, key := range keys {
		pipe.Del(c.ctx, key)
	}
	_, err := pipe.Exec(c.ctx)

	if err != nil {
		c.logger.Error("Failed to invalidate patient consents cache", 
			zap.String("patient_id", patientID.String()), 
			zap.Error(err))
		return err
	}

	c.logger.Info("Invalidated patient consents cache", 
		zap.String("patient_id", patientID.String()))
	return nil
}

func (c *RedisCache) CacheConsentValidation(userID, patientID uuid.UUID, purpose string, dataTypes []string, decision *AccessDecision) error {
	// Create a hash of the request for caching
	key := fmt.Sprintf("consent_validation:%s:%s:%s", 
		userID.String(), patientID.String(), purpose)
	
	// Cache for a short time only (1 minute) due to security sensitivity
	expiration := 1 * time.Minute
	
	err := c.SetObject(key, decision, expiration)
	if err != nil {
		c.logger.Error("Failed to cache consent validation", 
			zap.String("key", key), 
			zap.Error(err))
		return err
	}

	return nil
}

func (c *RedisCache) GetCachedConsentValidation(userID, patientID uuid.UUID, purpose string, dataTypes []string) (*AccessDecision, error) {
	key := fmt.Sprintf("consent_validation:%s:%s:%s", 
		userID.String(), patientID.String(), purpose)
	
	cached, err := c.GetObject(key)
	if err != nil || cached == nil {
		return nil, err
	}

	// Convert back to AccessDecision struct
	jsonData, err := json.Marshal(cached)
	if err != nil {
		return nil, err
	}

	var decision AccessDecision
	err = json.Unmarshal(jsonData, &decision)
	if err != nil {
		return nil, err
	}

	c.logger.Debug("Consent validation cache hit", zap.String("key", key))
	return &decision, nil
}

// Session management for user authentication
func (c *RedisCache) SetUserSession(sessionID string, userID uuid.UUID, expiration time.Duration) error {
	key := fmt.Sprintf("session:%s", sessionID)
	sessionData := map[string]interface{}{
		"user_id":    userID.String(),
		"created_at": time.Now().Unix(),
	}

	return c.SetObject(key, sessionData, expiration)
}

func (c *RedisCache) GetUserSession(sessionID string) (uuid.UUID, error) {
	key := fmt.Sprintf("session:%s", sessionID)
	cached, err := c.GetObject(key)
	if err != nil || cached == nil {
		return uuid.Nil, err
	}

	// Convert to map
	jsonData, err := json.Marshal(cached)
	if err != nil {
		return uuid.Nil, err
	}

	var sessionData map[string]interface{}
	err = json.Unmarshal(jsonData, &sessionData)
	if err != nil {
		return uuid.Nil, err
	}

	userIDStr, ok := sessionData["user_id"].(string)
	if !ok {
		return uuid.Nil, fmt.Errorf("invalid session data")
	}

	return uuid.Parse(userIDStr)
}

func (c *RedisCache) DeleteUserSession(sessionID string) error {
	key := fmt.Sprintf("session:%s", sessionID)
	return c.Delete(key)
}

// Rate limiting for security
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

// Audit trail caching (for performance in high-volume scenarios)
func (c *RedisCache) CacheAuditEntry(patientID uuid.UUID, entry interface{}, expiration time.Duration) error {
	key := fmt.Sprintf("audit:%s:%d", patientID.String(), time.Now().Unix())
	return c.SetObject(key, entry, expiration)
}

// Emergency access tracking
func (c *RedisCache) TrackEmergencyAccess(userID, patientID uuid.UUID) error {
	key := fmt.Sprintf("emergency_access:%s", userID.String())
	
	// Track emergency access events
	pipe := c.client.Pipeline()
	pipe.SAdd(c.ctx, key, patientID.String())
	pipe.Expire(c.ctx, key, 24*time.Hour) // Track for 24 hours
	
	_, err := pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to track emergency access", 
			zap.String("user_id", userID.String()),
			zap.String("patient_id", patientID.String()),
			zap.Error(err))
		return err
	}

	c.logger.Info("Emergency access tracked", 
		zap.String("user_id", userID.String()),
		zap.String("patient_id", patientID.String()))
	return nil
}

func (c *RedisCache) GetEmergencyAccessCount(userID uuid.UUID) (int64, error) {
	key := fmt.Sprintf("emergency_access:%s", userID.String())
	count, err := c.client.SCard(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return 0, nil
		}
		return 0, err
	}
	return count, nil
}

// Health check specific cache operations
func (c *RedisCache) SetHealthStatus(service string, status map[string]interface{}) error {
	key := fmt.Sprintf("health:%s", service)
	return c.SetObject(key, status, 30*time.Second)
}

func (c *RedisCache) GetHealthStatus(service string) (map[string]interface{}, error) {
	key := fmt.Sprintf("health:%s", service)
	cached, err := c.GetObject(key)
	if err != nil || cached == nil {
		return nil, err
	}

	// Convert to map
	jsonData, err := json.Marshal(cached)
	if err != nil {
		return nil, err
	}

	var status map[string]interface{}
	err = json.Unmarshal(jsonData, &status)
	if err != nil {
		return nil, err
	}

	return status, nil
}

// Configuration caching for performance
func (c *RedisCache) CacheHIPAAConfig(config map[string]interface{}) error {
	key := "hipaa_config"
	return c.SetObject(key, config, 10*time.Minute)
}

func (c *RedisCache) GetHIPAAConfig() (map[string]interface{}, error) {
	key := "hipaa_config"
	cached, err := c.GetObject(key)
	if err != nil || cached == nil {
		return nil, err
	}

	// Convert to map
	jsonData, err := json.Marshal(cached)
	if err != nil {
		return nil, err
	}

	var config map[string]interface{}
	err = json.Unmarshal(jsonData, &config)
	if err != nil {
		return nil, err
	}

	return config, nil
}

// =============================================================================
// PERFORMANCE ENHANCEMENTS - HIPAA-Compliant High-Performance Caching
// =============================================================================

// BatchValidateConsents validates multiple consent requests atomically
func (c *RedisCache) BatchValidateConsents(requests []ConsentRequest) (map[string]*AccessDecision, error) {
	if len(requests) == 0 {
		return make(map[string]*AccessDecision), nil
	}

	// Use pipeline for batch operations
	pipe := c.client.Pipeline()
	cmds := make(map[string]*redis.StringCmd)
	
	for _, req := range requests {
		key := fmt.Sprintf("consent_validation:%s:%s:%s", 
			req.UserID.String(), req.PatientID.String(), req.Purpose)
		cmds[key] = pipe.Get(c.ctx, key)
	}

	_, err := pipe.Exec(c.ctx)
	if err != nil && err != redis.Nil {
		return nil, err
	}

	results := make(map[string]*AccessDecision)
	for key, cmd := range cmds {
		if cmd.Err() == redis.Nil {
			continue // Cache miss
		}
		if cmd.Err() != nil {
			c.logger.Warn("Error retrieving consent validation", 
				zap.String("key", key),
				zap.Error(cmd.Err()))
			continue
		}

		var decision AccessDecision
		err = json.Unmarshal([]byte(cmd.Val()), &decision)
		if err != nil {
			c.logger.Error("Failed to unmarshal consent decision", 
				zap.String("key", key),
				zap.Error(err))
			continue
		}

		results[key] = &decision
	}

	c.logger.Debug("Batch consent validation completed", 
		zap.Int("requested", len(requests)),
		zap.Int("cache_hits", len(results)))
	
	return results, nil
}

// ConsentRequest represents a consent validation request
type ConsentRequest struct {
	UserID    uuid.UUID
	PatientID uuid.UUID
	Purpose   string
	DataTypes []string
}

// CacheConsentWithHierarchy implements hierarchical consent caching
func (c *RedisCache) CacheConsentWithHierarchy(userID, patientID uuid.UUID, purpose string, decision *AccessDecision) error {
	// Primary cache with full context
	primaryKey := fmt.Sprintf("consent_validation:%s:%s:%s", 
		userID.String(), patientID.String(), purpose)
	
	// Secondary caches for quick lookups
	userPatientKey := fmt.Sprintf("user_patient_access:%s:%s", userID.String(), patientID.String())
	patientAccessKey := fmt.Sprintf("patient_access_list:%s", patientID.String())
	
	pipe := c.client.Pipeline()
	
	// Cache full decision (1 minute for security)
	decisionData, err := json.Marshal(decision)
	if err != nil {
		return fmt.Errorf("failed to marshal access decision: %w", err)
	}
	pipe.Set(c.ctx, primaryKey, decisionData, 1*time.Minute)
	
	// Cache quick access status (30 seconds)
	pipe.Set(c.ctx, userPatientKey, decision.Granted, 30*time.Second)
	
	// Add to patient access list for audit trails
	if decision.Granted {
		pipe.SAdd(c.ctx, patientAccessKey, userID.String())
		pipe.Expire(c.ctx, patientAccessKey, 1*time.Hour)
	}
	
	// Cache access summary for monitoring
	summaryKey := fmt.Sprintf("access_summary:%s:%s", userID.String(), time.Now().Format("2006-01-02-15"))
	pipe.Incr(c.ctx, summaryKey)
	pipe.Expire(c.ctx, summaryKey, 24*time.Hour)

	_, err = pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to cache consent hierarchy",
			zap.String("user_id", userID.String()),
			zap.String("patient_id", patientID.String()),
			zap.Error(err))
		return err
	}

	return nil
}

// QuickAccessCheck provides ultra-fast access validation
func (c *RedisCache) QuickAccessCheck(userID, patientID uuid.UUID) (bool, error) {
	key := fmt.Sprintf("user_patient_access:%s:%s", userID.String(), patientID.String())
	
	result, err := c.client.Get(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return false, nil // Not cached or denied
		}
		return false, err
	}

	return result == "true" || result == "1", nil
}

// GetPatientAccessLog returns users who accessed a patient (for audit)
func (c *RedisCache) GetPatientAccessLog(patientID uuid.UUID) ([]string, error) {
	key := fmt.Sprintf("patient_access_list:%s", patientID.String())
	
	users, err := c.client.SMembers(c.ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			return []string{}, nil
		}
		return nil, err
	}

	return users, nil
}

// CacheEmergencyAccessDecision handles crisis scenarios with extended caching
func (c *RedisCache) CacheEmergencyAccessDecision(userID, patientID uuid.UUID, decision *AccessDecision, duration time.Duration) error {
	// Emergency access gets longer cache time but with audit
	emergencyKey := fmt.Sprintf("emergency_consent:%s:%s", userID.String(), patientID.String())
	
	// Add emergency metadata
	emergencyDecision := map[string]interface{}{
		"user_id":        userID.String(),
		"patient_id":     patientID.String(),
		"access_granted": decision.Granted,
		"emergency":      true,
		"granted_at":     time.Now().Unix(),
		"expires_at":     time.Now().Add(duration).Unix(),
		"justification":  decision.Reason, // Repurpose for emergency justification
	}

	data, err := json.Marshal(emergencyDecision)
	if err != nil {
		return fmt.Errorf("failed to marshal emergency decision: %w", err)
	}

	pipe := c.client.Pipeline()
	
	// Cache emergency decision
	pipe.Set(c.ctx, emergencyKey, data, duration)
	
	// Track emergency access for compliance
	c.TrackEmergencyAccess(userID, patientID)
	
	// Alert key for monitoring systems
	alertKey := fmt.Sprintf("emergency_alert:%s", time.Now().Format("2006-01-02-15"))
	pipe.SAdd(c.ctx, alertKey, fmt.Sprintf("%s:%s", userID.String(), patientID.String()))
	pipe.Expire(c.ctx, alertKey, 24*time.Hour)

	_, err = pipe.Exec(c.ctx)
	if err != nil {
		c.logger.Error("Failed to cache emergency access decision",
			zap.String("user_id", userID.String()),
			zap.String("patient_id", patientID.String()),
			zap.Error(err))
		return err
	}

	c.logger.Warn("Emergency access cached",
		zap.String("user_id", userID.String()),
		zap.String("patient_id", patientID.String()),
		zap.Duration("duration", duration))

	return nil
}

// GetAccessSummary provides usage analytics for compliance reporting
func (c *RedisCache) GetAccessSummary(userID uuid.UUID, date string) (int64, error) {
	key := fmt.Sprintf("access_summary:%s:%s", userID.String(), date)
	
	count, err := c.client.Get(c.ctx, key).Int64()
	if err != nil {
		if err == redis.Nil {
			return 0, nil
		}
		return 0, err
	}

	return count, nil
}

// CleanupExpiredConsents removes expired consent cache entries
func (c *RedisCache) CleanupExpiredConsents() error {
	// Get all consent validation keys
	pattern := "consent_validation:*"
	keys, err := c.client.Keys(c.ctx, pattern).Result()
	if err != nil {
		return err
	}

	if len(keys) == 0 {
		return nil
	}

	// Check TTL and remove near-expired entries
	pipe := c.client.Pipeline()
	expiredCount := 0
	
	for _, key := range keys {
		ttl, err := c.client.TTL(c.ctx, key).Result()
		if err != nil {
			continue
		}
		
		// Remove if TTL is less than 10 seconds (cleanup threshold)
		if ttl < 10*time.Second && ttl > 0 {
			pipe.Del(c.ctx, key)
			expiredCount++
		}
	}

	if expiredCount > 0 {
		_, err = pipe.Exec(c.ctx)
		if err != nil {
			return err
		}
		
		c.logger.Info("Cleaned up expired consent cache entries", 
			zap.Int("cleaned", expiredCount),
			zap.Int("total_keys", len(keys)))
	}

	return nil
}

// GetCacheMetrics returns detailed cache performance metrics
func (c *RedisCache) GetCacheMetrics() (map[string]interface{}, error) {
	info, err := c.client.Info(c.ctx, "memory", "stats", "keyspace").Result()
	if err != nil {
		return nil, err
	}

	// Count different types of cached data
	patterns := map[string]string{
		"consent_validations":  "consent_validation:*",
		"user_sessions":        "session:*",
		"patient_consents":     "patient_consents:*",
		"emergency_access":     "emergency_access:*",
		"health_checks":        "health:*",
		"hipaa_config":         "hipaa_config",
	}

	metrics := map[string]interface{}{
		"timestamp": time.Now().Unix(),
		"connected": c.Ping() == nil,
		"redis_info": info,
		"service":   "consent-cache",
	}

	// Count keys by pattern
	for metricName, pattern := range patterns {
		keys, err := c.client.Keys(c.ctx, pattern).Result()
		if err != nil {
			metrics[metricName+"_error"] = err.Error()
		} else {
			metrics[metricName+"_count"] = len(keys)
		}
	}

	return metrics, nil
}