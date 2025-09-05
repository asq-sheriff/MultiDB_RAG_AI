// Package main provides comprehensive tests for cache metrics functionality
package main

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"go.uber.org/zap"
	"go.uber.org/zap/zaptest"
)

// Test Cache Metrics Initialization

func TestCacheMetricsNew(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	tests := []struct {
		name        string
		serviceName string
	}{
		{
			name:        "valid service name",
			serviceName: "test-service",
		},
		{
			name:        "empty service name",
			serviceName: "",
		},
		{
			name:        "service name with special chars",
			serviceName: "test-service-123",
		},
	}
	
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			metrics := NewCacheMetrics(nil, tt.serviceName, logger)
			assert.NotNil(t, metrics)
			assert.NotNil(t, metrics.stats)
			assert.NotNil(t, metrics.warmupTasks)
		})
	}
}

// Test Prometheus Metrics Registration

func TestPrometheusMetricsRegistration(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	// Create metrics
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Test that metrics are properly initialized
	assert.NotNil(t, metrics.cacheHits)
	assert.NotNil(t, metrics.cacheMisses)
	assert.NotNil(t, metrics.cacheLatency)
	assert.NotNil(t, metrics.cacheSize)
	assert.NotNil(t, metrics.cacheErrors)
}

// Test Cache Hit/Miss Metrics

func TestCacheHitMissMetrics(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Record cache hits
	metrics.RecordCacheHit("test-service", "subscription", "get", time.Millisecond)
	metrics.RecordCacheHit("test-service", "quota", "get", 2*time.Millisecond)
	
	// Record cache misses
	metrics.RecordCacheMiss("test-service", "subscription", "get", 500*time.Microsecond)
	metrics.RecordCacheMiss("test-service", "plan", "get", time.Millisecond)
	
	// Get statistics
	stats := metrics.GetCacheStats()
	assert.NotNil(t, stats)
	assert.NotEmpty(t, stats)
	
	// Verify statistics are being tracked
	if subscriptionStats, exists := stats["subscription"]; exists {
		assert.Greater(t, subscriptionStats.Hits+subscriptionStats.Misses, int64(0))
	}
}

// Test Cache Error Metrics

func TestCacheErrorMetrics(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Record various types of errors
	metrics.RecordCacheError("test-service", "subscription", "connection_failed")
	metrics.RecordCacheError("test-service", "quota", "timeout")
	metrics.RecordCacheError("test-service", "subscription", "connection_failed") // duplicate
	
	// Verify error tracking doesn't panic
	stats := metrics.GetCacheStats()
	assert.NotNil(t, stats)
}

// Test Cache Size Tracking

func TestCacheSizeTracking(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Update cache sizes
	metrics.UpdateCacheSize("test-service", "subscription", 150)
	metrics.UpdateCacheSize("test-service", "quota", 300)
	metrics.UpdateCacheSize("test-service", "plan", 50)
	
	// Verify size tracking doesn't panic
	stats := metrics.GetCacheStats()
	assert.NotNil(t, stats)
}

// Test Cache Warmup Task Management

func TestCacheWarmupTasks(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Add warmup tasks
	taskFunc := func(ctx context.Context) error { return nil }
	
	task1 := WarmupTask{
		Name:       "subscriptions",
		Pattern:    "subscription:*",
		Interval:   5 * time.Minute,
		Priority:   1,
		WarmupFunc: taskFunc,
		Enabled:    true,
	}
	
	task2 := WarmupTask{
		Name:       "quotas",
		Pattern:    "quota:*",
		Interval:   10 * time.Minute,
		Priority:   2,
		WarmupFunc: taskFunc,
		Enabled:    true,
	}
	
	metrics.AddWarmupTask(task1)
	metrics.AddWarmupTask(task2)
	
	// Verify tasks are registered
	assert.Len(t, metrics.warmupTasks, 2)
	assert.Contains(t, metrics.warmupTasks, "subscriptions")
	assert.Contains(t, metrics.warmupTasks, "quotas")
}

// Test Cache Health Monitoring

func TestCacheMetricsHealthMonitoring(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Test Redis info with nil client (should not panic)
	ctx := context.Background()
	_, err := metrics.GetRedisInfo(ctx)
	
	// With nil client, should return an error
	assert.Error(t, err)
}

// Test Cache Statistics Aggregation

func TestCacheStatsAggregation(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Generate mixed operations
	for i := 0; i < 10; i++ {
		if i%2 == 0 {
			metrics.RecordCacheHit("test-service", "subscription", "get", time.Millisecond)
		} else {
			metrics.RecordCacheMiss("test-service", "subscription", "get", time.Millisecond)
		}
	}
	
	// Record some errors
	metrics.RecordCacheError("test-service", "subscription", "timeout")
	metrics.RecordCacheError("test-service", "subscription", "connection_error")
	
	// Update size
	metrics.UpdateCacheSize("test-service", "subscription", 1000)
	
	stats := metrics.GetCacheStats()
	assert.NotNil(t, stats)
	
	if subscriptionStats, exists := stats["subscription"]; exists {
		// Verify some operations were recorded
		assert.Greater(t, subscriptionStats.Hits+subscriptionStats.Misses, int64(0))
	}
}

// Test Concurrent Access to Metrics

func TestConcurrentMetricsAccess(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Launch multiple goroutines to simulate concurrent access
	done := make(chan bool, 10)
	
	for i := 0; i < 10; i++ {
		go func(id int) {
			// Each goroutine performs various metric operations
			metrics.RecordCacheHit("test-service", "test", "get", time.Millisecond)
			metrics.RecordCacheMiss("test-service", "test", "get", time.Millisecond)
			metrics.RecordCacheError("test-service", "test", "concurrent_error")
			metrics.UpdateCacheSize("test-service", "test", int64(id*10))
			done <- true
		}(i)
	}
	
	// Wait for all goroutines to complete
	for i := 0; i < 10; i++ {
		<-done
	}
	
	// Verify metrics were recorded correctly (no panic)
	stats := metrics.GetCacheStats()
	assert.NotNil(t, stats)
}

// Test Error Handling in Metrics

func TestMetricsErrorHandling(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	// Test with nil Redis client
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Should not panic with nil client
	assert.NotPanics(t, func() {
		metrics.RecordCacheHit("test-service", "test", "get", time.Millisecond)
		metrics.RecordCacheMiss("test-service", "test", "get", time.Millisecond)
		metrics.RecordCacheError("test-service", "test", "error")
		metrics.UpdateCacheSize("test-service", "test", 100)
		
		// These should return empty/default values
		stats := metrics.GetCacheStats()
		assert.NotNil(t, stats)
		
		ctx := context.Background()
		_, err := metrics.GetRedisInfo(ctx)
		assert.Error(t, err) // Should error with nil client
	})
}

// Test Cache Warmup Task Execution

func TestCacheWarmupExecution(t *testing.T) {
	logger := zaptest.NewLogger(t)
	
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	taskFunc := func(ctx context.Context) error {
		return nil
	}
	
	task := WarmupTask{
		Name:       "test-task",
		Pattern:    "test:*",
		Interval:   time.Hour,
		Priority:   1,
		WarmupFunc: taskFunc,
		Enabled:    true,
	}
	
	metrics.AddWarmupTask(task)
	
	// Run cache warming
	ctx := context.Background()
	metrics.RunCacheWarming(ctx, "test-service")
	
	// Give it a moment to execute
	time.Sleep(100 * time.Millisecond)
	
	// Note: This might not execute immediately depending on implementation
	// The test mainly verifies no panic occurs
	assert.NotNil(t, metrics.warmupTasks)
}

// Benchmark Tests for Metrics Operations

func BenchmarkRecordCacheHit(b *testing.B) {
	logger := zap.NewNop()
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics.RecordCacheHit("test-service", "test", "get", time.Millisecond)
	}
}

func BenchmarkRecordCacheMiss(b *testing.B) {
	logger := zap.NewNop()
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics.RecordCacheMiss("test-service", "test", "get", time.Millisecond)
	}
}

func BenchmarkGetStats(b *testing.B) {
	logger := zap.NewNop()
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	// Pre-populate with some data
	for i := 0; i < 1000; i++ {
		metrics.RecordCacheHit("test-service", "test", "get", time.Millisecond)
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		metrics.GetCacheStats()
	}
}

func BenchmarkConcurrentMetrics(b *testing.B) {
	logger := zap.NewNop()
	metrics := NewCacheMetrics(nil, "test-service", logger)
	
	b.ResetTimer()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			metrics.RecordCacheHit("test-service", "test", "get", time.Millisecond)
		}
	})
}