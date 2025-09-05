// Package cache_metrics provides comprehensive cache monitoring and metrics
package main

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"
)

// CacheMetrics tracks cache performance and provides monitoring
type CacheMetrics struct {
	redis  *redis.Client
	logger *zap.Logger
	
	// Prometheus metrics
	cacheHits     *prometheus.CounterVec
	cacheMisses   *prometheus.CounterVec
	cacheLatency  *prometheus.HistogramVec
	cacheSize     *prometheus.GaugeVec
	cacheErrors   *prometheus.CounterVec
	
	// Internal tracking
	stats       map[string]*CacheStats
	statsLock   sync.RWMutex
	warmupTasks map[string]WarmupTask
}

// CacheStats represents cache statistics for a specific cache type
type CacheStats struct {
	Name         string    `json:"name"`
	Hits         int64     `json:"hits"`
	Misses       int64     `json:"misses"`
	Errors       int64     `json:"errors"`
	TotalRequests int64    `json:"total_requests"`
	HitRatio     float64   `json:"hit_ratio"`
	LastAccess   time.Time `json:"last_access"`
	AvgLatency   float64   `json:"avg_latency_ms"`
}

// WarmupTask defines a cache warming strategy
type WarmupTask struct {
	Name        string
	Pattern     string
	Interval    time.Duration
	Priority    int
	WarmupFunc  func(ctx context.Context) error
	LastRun     time.Time
	NextRun     time.Time
	Enabled     bool
}

// CacheAlert represents a cache monitoring alert
type CacheAlert struct {
	Level       string    `json:"level"`       // info, warning, critical
	Service     string    `json:"service"`
	CacheName   string    `json:"cache_name"`
	Metric      string    `json:"metric"`
	Threshold   float64   `json:"threshold"`
	ActualValue float64   `json:"actual_value"`
	Message     string    `json:"message"`
	Timestamp   time.Time `json:"timestamp"`
}

// NewCacheMetrics creates a new cache metrics instance
func NewCacheMetrics(redis *redis.Client, serviceName string, logger *zap.Logger) *CacheMetrics {
	return &CacheMetrics{
		redis:  redis,
		logger: logger,
		stats:  make(map[string]*CacheStats),
		warmupTasks: make(map[string]WarmupTask),
		
		cacheHits: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "cache_hits_total",
				Help: "The total number of cache hits",
			},
			[]string{"service", "cache_name", "operation"},
		),
		
		cacheMisses: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "cache_misses_total", 
				Help: "The total number of cache misses",
			},
			[]string{"service", "cache_name", "operation"},
		),
		
		cacheLatency: promauto.NewHistogramVec(
			prometheus.HistogramOpts{
				Name: "cache_operation_duration_seconds",
				Help: "The duration of cache operations",
				Buckets: []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0},
			},
			[]string{"service", "cache_name", "operation", "status"},
		),
		
		cacheSize: promauto.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "cache_size_bytes",
				Help: "The current size of cache in bytes",
			},
			[]string{"service", "cache_name"},
		),
		
		cacheErrors: promauto.NewCounterVec(
			prometheus.CounterOpts{
				Name: "cache_errors_total",
				Help: "The total number of cache errors",
			},
			[]string{"service", "cache_name", "error_type"},
		),
	}
}

// RecordCacheHit records a cache hit with latency
func (cm *CacheMetrics) RecordCacheHit(serviceName, cacheName, operation string, latency time.Duration) {
	cm.cacheHits.WithLabelValues(serviceName, cacheName, operation).Inc()
	cm.cacheLatency.WithLabelValues(serviceName, cacheName, operation, "hit").Observe(latency.Seconds())
	
	cm.updateStats(cacheName, true, latency)
}

// RecordCacheMiss records a cache miss with latency
func (cm *CacheMetrics) RecordCacheMiss(serviceName, cacheName, operation string, latency time.Duration) {
	cm.cacheMisses.WithLabelValues(serviceName, cacheName, operation).Inc()
	cm.cacheLatency.WithLabelValues(serviceName, cacheName, operation, "miss").Observe(latency.Seconds())
	
	cm.updateStats(cacheName, false, latency)
}

// RecordCacheError records a cache error
func (cm *CacheMetrics) RecordCacheError(serviceName, cacheName, errorType string) {
	cm.cacheErrors.WithLabelValues(serviceName, cacheName, errorType).Inc()
	
	cm.updateStatsError(cacheName)
}

// updateStats updates internal cache statistics
func (cm *CacheMetrics) updateStats(cacheName string, hit bool, latency time.Duration) {
	cm.statsLock.Lock()
	defer cm.statsLock.Unlock()
	
	if _, exists := cm.stats[cacheName]; !exists {
		cm.stats[cacheName] = &CacheStats{
			Name: cacheName,
		}
	}
	
	stats := cm.stats[cacheName]
	stats.TotalRequests++
	stats.LastAccess = time.Now()
	
	if hit {
		stats.Hits++
	} else {
		stats.Misses++
	}
	
	// Update hit ratio
	if stats.TotalRequests > 0 {
		stats.HitRatio = float64(stats.Hits) / float64(stats.TotalRequests)
	}
	
	// Update average latency (simple moving average)
	latencyMs := float64(latency.Nanoseconds()) / 1000000.0
	if stats.AvgLatency == 0 {
		stats.AvgLatency = latencyMs
	} else {
		stats.AvgLatency = (stats.AvgLatency + latencyMs) / 2
	}
}

// updateStatsError updates error statistics
func (cm *CacheMetrics) updateStatsError(cacheName string) {
	cm.statsLock.Lock()
	defer cm.statsLock.Unlock()
	
	if _, exists := cm.stats[cacheName]; !exists {
		cm.stats[cacheName] = &CacheStats{
			Name: cacheName,
		}
	}
	
	cm.stats[cacheName].Errors++
}

// GetCacheStats returns current cache statistics
func (cm *CacheMetrics) GetCacheStats() map[string]*CacheStats {
	cm.statsLock.RLock()
	defer cm.statsLock.RUnlock()
	
	// Create a copy to avoid race conditions
	result := make(map[string]*CacheStats)
	for k, v := range cm.stats {
		statsCopy := *v
		result[k] = &statsCopy
	}
	
	return result
}

// MonitorCacheHealth continuously monitors cache health and generates alerts
func (cm *CacheMetrics) MonitorCacheHealth(ctx context.Context, serviceName string, alertCallback func(CacheAlert)) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			cm.checkCacheHealth(serviceName, alertCallback)
		}
	}
}

// checkCacheHealth evaluates cache performance and generates alerts
func (cm *CacheMetrics) checkCacheHealth(serviceName string, alertCallback func(CacheAlert)) {
	stats := cm.GetCacheStats()
	
	for name, stat := range stats {
		now := time.Now()
		
		// Check hit ratio
		if stat.HitRatio < 0.6 && stat.TotalRequests > 100 {
			alert := CacheAlert{
				Level:       "warning",
				Service:     serviceName,
				CacheName:   name,
				Metric:      "hit_ratio",
				Threshold:   0.6,
				ActualValue: stat.HitRatio,
				Message:     fmt.Sprintf("Low cache hit ratio: %.2f%% (expected >60%%)", stat.HitRatio*100),
				Timestamp:   now,
			}
			alertCallback(alert)
		}
		
		// Check if cache hasn't been accessed recently
		if now.Sub(stat.LastAccess) > 10*time.Minute {
			alert := CacheAlert{
				Level:       "info",
				Service:     serviceName,
				CacheName:   name,
				Metric:      "last_access",
				Threshold:   600, // 10 minutes in seconds
				ActualValue: now.Sub(stat.LastAccess).Seconds(),
				Message:     fmt.Sprintf("Cache hasn't been accessed for %s", now.Sub(stat.LastAccess).String()),
				Timestamp:   now,
			}
			alertCallback(alert)
		}
		
		// Check average latency
		if stat.AvgLatency > 100 && stat.TotalRequests > 10 {
			alert := CacheAlert{
				Level:       "warning",
				Service:     serviceName,
				CacheName:   name,
				Metric:      "latency",
				Threshold:   100,
				ActualValue: stat.AvgLatency,
				Message:     fmt.Sprintf("High cache latency: %.2fms (expected <100ms)", stat.AvgLatency),
				Timestamp:   now,
			}
			alertCallback(alert)
		}
		
		// Check error rate
		if stat.Errors > 0 && float64(stat.Errors)/float64(stat.TotalRequests) > 0.05 {
			errorRate := float64(stat.Errors) / float64(stat.TotalRequests)
			alert := CacheAlert{
				Level:       "critical",
				Service:     serviceName,
				CacheName:   name,
				Metric:      "error_rate",
				Threshold:   0.05,
				ActualValue: errorRate,
				Message:     fmt.Sprintf("High cache error rate: %.2f%% (expected <5%%)", errorRate*100),
				Timestamp:   now,
			}
			alertCallback(alert)
		}
	}
}

// AddWarmupTask adds a cache warming task
func (cm *CacheMetrics) AddWarmupTask(task WarmupTask) {
	cm.warmupTasks[task.Name] = task
}

// RunCacheWarming starts cache warming processes
func (cm *CacheMetrics) RunCacheWarming(ctx context.Context, serviceName string) {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()
	
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			cm.runWarmupTasks(ctx, serviceName)
		}
	}
}

// runWarmupTasks executes due warmup tasks
func (cm *CacheMetrics) runWarmupTasks(ctx context.Context, serviceName string) {
	now := time.Now()
	
	for name, task := range cm.warmupTasks {
		if !task.Enabled || now.Before(task.NextRun) {
			continue
		}
		
		go func(taskName string, warmupTask WarmupTask) {
			start := time.Now()
			err := warmupTask.WarmupFunc(ctx)
			duration := time.Since(start)
			
			// Update task timing
			warmupTask.LastRun = now
			warmupTask.NextRun = now.Add(warmupTask.Interval)
			cm.warmupTasks[taskName] = warmupTask
			
			if err != nil {
				cm.logger.Error("Cache warmup task failed",
					zap.String("service", serviceName),
					zap.String("task", taskName),
					zap.Error(err),
					zap.Duration("duration", duration))
				cm.RecordCacheError(serviceName, "warmup", "execution_failed")
			} else {
				cm.logger.Info("Cache warmup task completed",
					zap.String("service", serviceName),
					zap.String("task", taskName),
					zap.Duration("duration", duration))
			}
		}(name, task)
	}
}

// UpdateCacheSize updates the cache size metric
func (cm *CacheMetrics) UpdateCacheSize(serviceName, cacheName string, sizeBytes int64) {
	cm.cacheSize.WithLabelValues(serviceName, cacheName).Set(float64(sizeBytes))
}

// GetRedisInfo retrieves Redis server information
func (cm *CacheMetrics) GetRedisInfo(ctx context.Context) (map[string]string, error) {
	info, err := cm.redis.Info(ctx).Result()
	if err != nil {
		return nil, err
	}
	
	result := make(map[string]string)
	lines := strings.Split(info, "\r\n")
	
	for _, line := range lines {
		if strings.Contains(line, ":") && !strings.HasPrefix(line, "#") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				result[parts[0]] = parts[1]
			}
		}
	}
	
	return result, nil
}

// GetCacheMemoryUsage returns memory usage for different cache patterns
func (cm *CacheMetrics) GetCacheMemoryUsage(ctx context.Context, patterns []string) (map[string]int64, error) {
	result := make(map[string]int64)
	
	for _, pattern := range patterns {
		keys, err := cm.redis.Keys(ctx, pattern).Result()
		if err != nil {
			cm.logger.Error("Failed to get keys for pattern", zap.String("pattern", pattern), zap.Error(err))
			continue
		}
		
		var totalSize int64
		for _, key := range keys {
			size, err := cm.redis.MemoryUsage(ctx, key).Result()
			if err == nil {
				totalSize += size
			}
		}
		
		result[pattern] = totalSize
	}
	
	return result, nil
}