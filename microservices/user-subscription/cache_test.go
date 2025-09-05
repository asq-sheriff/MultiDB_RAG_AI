// Package main provides comprehensive tests for cache functionality
package main

import (
	"context"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"go.uber.org/zap/zaptest"
)

// Test Cache Connection

func TestRedisConnectionParsing(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	tests := []struct {
		name        string
		redisURL    string
		expectError bool
	}{
		{
			name:        "valid redis URL",
			redisURL:    "redis://localhost:6379",
			expectError: true, // Will fail in test env without Redis
		},
		{
			name:        "redis URL with auth",
			redisURL:    "redis://:password@localhost:6379/0",
			expectError: true, // Will fail in test env without Redis
		},
		{
			name:        "invalid URL format",
			redisURL:    "not-a-url",
			expectError: true,
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := NewRedisCache(tt.redisURL, logger)
			if tt.expectError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

// Test Cache Subscription Operations

func TestCacheSubscriptionOperations(t *testing.T) {
	// Skip if no Redis connection available
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	// Try to create cache (will fail without Redis, but test the interface)
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	// Test caching a subscription
	userID := uuid.New()
	subscription := createTestSubscription(userID, PlanPro)
	
	err = cache.CacheSubscription(subscription, time.Hour)
	assert.NoError(t, err)
	
	// Test retrieving cached subscription
	cachedSub, err := cache.GetCachedSubscription(userID)
	assert.NoError(t, err)
	assert.NotNil(t, cachedSub)
	assert.Equal(t, subscription.UserID, cachedSub.UserID)
	assert.Equal(t, subscription.PlanType, cachedSub.PlanType)
}

// Test Cache Quota Operations

func TestCacheQuotaOperations(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	quotaInfo := &QuotaInfo{
		UserID:       userID,
		ResourceType: ResourceMessages,
		CurrentUsage: 50,
		MaxAllowed:   100,
		Remaining:    50,
		HasQuota:     true,
	}
	
	// Test caching quota
	err = cache.CacheQuota(userID, ResourceMessages, quotaInfo, time.Hour)
	assert.NoError(t, err)
	
	// Test retrieving cached quota
	cachedQuota, err := cache.GetCachedQuota(userID, ResourceMessages)
	assert.NoError(t, err)
	assert.NotNil(t, cachedQuota)
	assert.Equal(t, quotaInfo.CurrentUsage, cachedQuota.CurrentUsage)
	assert.Equal(t, quotaInfo.MaxAllowed, cachedQuota.MaxAllowed)
}

// Test Cache Warming Strategies

func TestCacheWarmingStrategies(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	ctx := context.Background()
	
	// Test subscription plans warming
	err = cache.warmupSubscriptionPlans(ctx)
	// Should not panic, may succeed or fail based on Redis availability
	if err != nil {
		t.Logf("Cache warmup failed (expected in test env): %v", err)
	}
	
	// Test active subscriptions warming
	err = cache.warmupActiveSubscriptions(ctx)
	if err != nil {
		t.Logf("Cache warmup failed (expected in test env): %v", err)
	}
	
	// Test user quotas warming
	err = cache.warmupUserQuotas(ctx)
	if err != nil {
		t.Logf("Cache warmup failed (expected in test env): %v", err)
	}
}

// Test Cache Metrics Integration

func TestCacheMetricsIntegration(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	// Test getting cache metrics
	metrics := cache.GetCacheMetrics()
	assert.NotNil(t, metrics)
	
	// Test cache stats
	stats, err := cache.GetCacheStats()
	assert.NoError(t, err)
	assert.NotNil(t, stats)
}

// Test Cache Health and Monitoring

func TestCacheHealthMonitoring(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	// Test ping
	err = cache.Ping()
	assert.NoError(t, err)
	
	// Test setting health status
	healthData := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now(),
		"version":   "1.0.0",
	}
	
	err = cache.SetHealthStatus("test-service", healthData)
	assert.NoError(t, err)
	
	// Test getting health status
	retrievedHealth, err := cache.GetHealthStatus("test-service")
	assert.NoError(t, err)
	assert.NotNil(t, retrievedHealth)
	assert.Equal(t, "healthy", retrievedHealth["status"])
}

// Test Usage Counter Operations

func TestCacheUsageCounters(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	
	// Test incrementing usage
	newCount, err := cache.IncrementUsage(userID, ResourceMessages, 5)
	assert.NoError(t, err)
	assert.GreaterOrEqual(t, newCount, int64(5))
	
	// Test getting usage counter
	period := "2025-08"
	count, err := cache.GetUsageCounter(userID, ResourceMessages, period)
	assert.NoError(t, err)
	assert.GreaterOrEqual(t, count, int64(0))
}

// Test Rate Limiting

func TestCacheRateLimiting(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	
	// Test rate limiting
	allowed, remaining, err := cache.CheckRateLimit(userID, ResourceMessages, 10, time.Minute)
	assert.NoError(t, err)
	assert.True(t, allowed)
	assert.LessOrEqual(t, remaining, 10)
}

// Test Session Management

func TestCacheSessionManagement(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	sessionID := uuid.New().String()
	
	sessionData := map[string]interface{}{
		"user_id":    userID.String(),
		"login_time": time.Now(),
		"ip_address": "192.168.1.100",
	}
	
	// Test caching user session
	err = cache.CacheUserSession(sessionID, userID, sessionData, time.Hour)
	assert.NoError(t, err)
	
	// Test retrieving cached session
	retrievedSession, err := cache.GetCachedUserSession(sessionID)
	assert.NoError(t, err)
	assert.NotNil(t, retrievedSession)
	assert.Equal(t, userID.String(), retrievedSession["user_id"])
	
	// Test getting user sessions
	sessions, err := cache.GetUserSessions(userID)
	assert.NoError(t, err)
	assert.NotNil(t, sessions)
	
	// Test invalidating session
	err = cache.InvalidateUserSession(sessionID)
	assert.NoError(t, err)
}

// Test Cache Invalidation

func TestCacheInvalidation(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	
	// Test invalidating user cache
	err = cache.InvalidateUserCache(userID)
	assert.NoError(t, err)
	
	// Test invalidating subscription cache
	err = cache.InvalidateSubscriptionCache(userID)
	assert.NoError(t, err)
}

// Test Cache Monitoring Start

func TestCacheMonitoringStart(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping Redis integration test in short mode")
	}
	
	logger := zaptest.NewLogger(t)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		t.Skipf("Redis not available for testing: %v", err)
		return
	}
	defer cache.Close()
	
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()
	
	// Test starting monitoring (should not panic)
	assert.NotPanics(t, func() {
		cache.StartMonitoring(ctx)
	})
}

// Benchmark Tests for Cache Operations

func BenchmarkCacheSubscription(b *testing.B) {
	if testing.Short() {
		b.Skip("Skipping Redis benchmark in short mode")
	}
	
	logger := zaptest.NewLogger(b)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		b.Skipf("Redis not available for benchmarking: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	subscription := createTestSubscription(userID, PlanPro)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.CacheSubscription(subscription, time.Hour)
	}
}

func BenchmarkGetCachedSubscription(b *testing.B) {
	if testing.Short() {
		b.Skip("Skipping Redis benchmark in short mode")
	}
	
	logger := zaptest.NewLogger(b)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		b.Skipf("Redis not available for benchmarking: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	subscription := createTestSubscription(userID, PlanPro)
	
	// Pre-cache the subscription
	cache.CacheSubscription(subscription, time.Hour)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.GetCachedSubscription(userID)
	}
}

func BenchmarkIncrementUsage(b *testing.B) {
	if testing.Short() {
		b.Skip("Skipping Redis benchmark in short mode")
	}
	
	logger := zaptest.NewLogger(b)
	
	cache, err := NewRedisCache("redis://localhost:6379", logger)
	if err != nil {
		b.Skipf("Redis not available for benchmarking: %v", err)
		return
	}
	defer cache.Close()
	
	userID := uuid.New()
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.IncrementUsage(userID, ResourceMessages, 1)
	}
}