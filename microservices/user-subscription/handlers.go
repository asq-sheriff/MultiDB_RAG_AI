// Package main provides HTTP handlers for user subscription service
package main

import (
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// SubscriptionHandlers contains all HTTP handlers for subscription management
type SubscriptionHandlers struct {
	service *SubscriptionService
}

// NewSubscriptionHandlers creates new subscription handlers
func NewSubscriptionHandlers(service *SubscriptionService) *SubscriptionHandlers {
	return &SubscriptionHandlers{
		service: service,
	}
}

// RegisterRoutes registers all subscription routes
func (h *SubscriptionHandlers) RegisterRoutes(r *gin.Engine) {
	// API versioning
	v1 := r.Group("/api/v1")
	
	// Subscription management
	subscriptions := v1.Group("/subscriptions")
	{
		subscriptions.POST("/", h.CreateSubscription)
		subscriptions.GET("/user/:user_id", h.GetUserSubscription)
		subscriptions.PUT("/user/:user_id/upgrade", h.UpgradeSubscription)
		subscriptions.PUT("/user/:user_id/downgrade", h.DowngradeSubscription)
		subscriptions.DELETE("/user/:user_id/cancel", h.CancelSubscription)
		subscriptions.POST("/user/:user_id/reactivate", h.ReactivateSubscription)
		subscriptions.POST("/user/:user_id/pause", h.PauseSubscription)
		subscriptions.POST("/user/:user_id/resume", h.ResumeSubscription)
	}

	// Usage and quota management
	usage := v1.Group("/usage")
	{
		usage.POST("/record", h.RecordUsage)
		usage.GET("/user/:user_id/quota/:resource_type", h.CheckQuota)
		usage.GET("/user/:user_id/summary", h.GetUsageSummary)
	}

	// Plan information
	plans := v1.Group("/plans")
	{
		plans.GET("/", h.ListPlans)
		plans.GET("/:plan_type/features", h.GetPlanFeatures)
	}

	// Admin endpoints
	admin := v1.Group("/admin")
	{
		admin.GET("/metrics", h.GetSubscriptionMetrics)
		admin.GET("/cache/metrics", h.GetCacheMetrics)
		admin.GET("/cache/health", h.GetCacheHealth)
		admin.POST("/cache/warmup", h.WarmupCache)
		admin.POST("/renewals/process", h.ProcessRenewals)
		admin.POST("/expired/process", h.ProcessExpired)
	}

	// Health check
	r.GET("/health", h.HealthCheck)
}

// Request/Response models for API

type CreateSubscriptionRequest struct {
	UserID       string `json:"user_id" binding:"required"`
	PlanType     string `json:"plan_type" binding:"required"`
	BillingCycle string `json:"billing_cycle" binding:"required"`
}

type UpgradeSubscriptionRequest struct {
	PlanType     string `json:"plan_type" binding:"required"`
	BillingCycle string `json:"billing_cycle" binding:"required"`
}

type DowngradeSubscriptionRequest struct {
	PlanType string `json:"plan_type" binding:"required"`
}

type CancelSubscriptionRequest struct {
	Reason string `json:"reason"`
}

type PauseSubscriptionRequest struct {
	DurationDays int `json:"duration_days" binding:"required,min=1,max=365"`
}

type RecordUsageRequest struct {
	UserID       string                 `json:"user_id" binding:"required"`
	ResourceType string                 `json:"resource_type" binding:"required"`
	Quantity     int                    `json:"quantity" binding:"required,min=1"`
	Metadata     map[string]interface{} `json:"metadata"`
}

type APIResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
	Message string      `json:"message,omitempty"`
}

// Handler implementations

// CreateSubscription creates a new subscription for a user
func (h *SubscriptionHandlers) CreateSubscription(c *gin.Context) {
	var req CreateSubscriptionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	// Parse user ID
	userID, err := uuid.Parse(req.UserID)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	// Validate plan type
	planType := SubscriptionPlan(req.PlanType)
	if planType != PlanFree && planType != PlanPro && planType != PlanEnterprise {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid plan type",
		})
		return
	}

	// Validate billing cycle
	billingCycle := BillingCycle(req.BillingCycle)
	if billingCycle != CycleMonthly && billingCycle != CycleYearly && billingCycle != CycleWeekly {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid billing cycle",
		})
		return
	}

	// Create subscription
	subscription, err := h.service.CreateUserSubscription(userID, planType, billingCycle)
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusCreated, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription created successfully",
	})
}

// GetUserSubscription returns a user's current subscription
func (h *SubscriptionHandlers) GetUserSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	subscription, err := h.service.GetUserSubscription(userID)
	if err != nil {
		c.JSON(http.StatusNotFound, APIResponse{
			Success: false,
			Error:   "Subscription not found",
		})
		return
	}

	// Add plan features to response
	features := GetPlanFeatures(subscription.PlanType)
	response := map[string]interface{}{
		"subscription": subscription,
		"features":     features,
		"is_active":    subscription.IsActive(),
	}

	if days := subscription.DaysUntilExpiry(); days != nil {
		response["days_until_expiry"] = *days
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    response,
	})
}

// UpgradeSubscription upgrades a user's subscription
func (h *SubscriptionHandlers) UpgradeSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	var req UpgradeSubscriptionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	planType := SubscriptionPlan(req.PlanType)
	billingCycle := BillingCycle(req.BillingCycle)

	subscription, err := h.service.UpgradeSubscription(userID, planType, billingCycle)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription upgraded successfully",
	})
}

// DowngradeSubscription downgrades a user's subscription
func (h *SubscriptionHandlers) DowngradeSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	var req DowngradeSubscriptionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	planType := SubscriptionPlan(req.PlanType)

	subscription, err := h.service.DowngradeSubscription(userID, planType)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription downgrade scheduled",
	})
}

// CancelSubscription cancels a user's subscription
func (h *SubscriptionHandlers) CancelSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	var req CancelSubscriptionRequest
	c.ShouldBindJSON(&req)

	reason := req.Reason
	if reason == "" {
		reason = "User requested cancellation"
	}

	err = h.service.CancelSubscription(userID, reason)
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Message: "Subscription canceled successfully",
	})
}

// ReactivateSubscription reactivates a canceled subscription
func (h *SubscriptionHandlers) ReactivateSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	subscription, err := h.service.ReactivateSubscription(userID)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription reactivated successfully",
	})
}

// PauseSubscription pauses a subscription temporarily
func (h *SubscriptionHandlers) PauseSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	var req PauseSubscriptionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	duration := time.Duration(req.DurationDays) * 24 * time.Hour

	subscription, err := h.service.PauseSubscription(userID, duration)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription paused successfully",
	})
}

// ResumeSubscription resumes a paused subscription
func (h *SubscriptionHandlers) ResumeSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	subscription, err := h.service.ResumeSubscription(userID)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription resumed successfully",
	})
}

// RecordUsage records usage for a user and resource type
func (h *SubscriptionHandlers) RecordUsage(c *gin.Context) {
	var req RecordUsageRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	userID, err := uuid.Parse(req.UserID)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	resourceType := ResourceType(req.ResourceType)

	quota, err := h.service.CheckAndRecordUsage(userID, resourceType, req.Quantity, req.Metadata)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    quota,
		Message: "Usage recorded successfully",
	})
}

// CheckQuota checks quota for a user and resource type
func (h *SubscriptionHandlers) CheckQuota(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	resourceType := ResourceType(c.Param("resource_type"))

	quota, err := h.service.db.CheckUserQuota(userID, resourceType)
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    quota,
	})
}

// GetUsageSummary returns usage summary for a user
func (h *SubscriptionHandlers) GetUsageSummary(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID",
		})
		return
	}

	// Get days parameter (default 30)
	daysStr := c.DefaultQuery("days", "30")
	days, err := strconv.Atoi(daysStr)
	if err != nil || days < 1 {
		days = 30
	}

	summary, err := h.service.GetUsageSummary(userID, days)
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    summary,
	})
}

// ListPlans returns all available subscription plans
func (h *SubscriptionHandlers) ListPlans(c *gin.Context) {
	plans := h.service.ListAvailablePlans()

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    plans,
	})
}

// GetPlanFeatures returns features for a specific plan
func (h *SubscriptionHandlers) GetPlanFeatures(c *gin.Context) {
	planTypeStr := c.Param("plan_type")
	planType := SubscriptionPlan(planTypeStr)

	if planType != PlanFree && planType != PlanPro && planType != PlanEnterprise {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid plan type",
		})
		return
	}

	features := GetPlanFeatures(planType)

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    features,
	})
}

// GetSubscriptionMetrics returns subscription metrics (admin endpoint)
func (h *SubscriptionHandlers) GetSubscriptionMetrics(c *gin.Context) {
	metrics, err := h.service.GetSubscriptionMetrics()
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    metrics,
	})
}

// ProcessRenewals processes subscription renewals (admin endpoint)
func (h *SubscriptionHandlers) ProcessRenewals(c *gin.Context) {
	err := h.service.ProcessSubscriptionRenewals()
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Message: "Subscription renewals processed",
	})
}

// ProcessExpired processes expired subscriptions (admin endpoint)
func (h *SubscriptionHandlers) ProcessExpired(c *gin.Context) {
	err := h.service.ProcessExpiredSubscriptions()
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Message: "Expired subscriptions processed",
	})
}

// HealthCheck returns service health status
func (h *SubscriptionHandlers) HealthCheck(c *gin.Context) {
	health := h.service.db.HealthCheck()

	// Determine overall status
	status := "healthy"
	for _, v := range health {
		if v == "unhealthy" {
			status = "unhealthy"
			break
		}
		if v == "unavailable" && status == "healthy" {
			status = "degraded"
		}
	}

	health["status"] = status
	health["service"] = "user-subscription-service"
	health["version"] = "1.0.0"

	httpStatus := http.StatusOK
	if status == "unhealthy" {
		httpStatus = http.StatusServiceUnavailable
	} else if status == "degraded" {
		httpStatus = http.StatusPartialContent
	}

	c.JSON(httpStatus, health)
}

// Middleware for authentication and authorization would go here
// For now, these are placeholder implementations

func (h *SubscriptionHandlers) requireAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		// TODO: Implement JWT token validation
		// For now, allow all requests
		c.Next()
	}
}

func (h *SubscriptionHandlers) requireAdmin() gin.HandlerFunc {
	return func(c *gin.Context) {
		// TODO: Implement admin role validation
		// For now, allow all requests
		c.Next()
	}
}

// CORS middleware for cross-origin requests
func (h *SubscriptionHandlers) corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

// Rate limiting middleware
func (h *SubscriptionHandlers) rateLimitMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// TODO: Implement rate limiting using Redis
		// For now, allow all requests
		c.Next()
	}
}

// Logging middleware for request/response logging
func (h *SubscriptionHandlers) loggingMiddleware() gin.HandlerFunc {
	return gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		return fmt.Sprintf("%s - [%s] \"%s %s %s %d %s \"%s\" %s\"\n",
			param.ClientIP,
			param.TimeStamp.Format("02/Jan/2006:15:04:05 -0700"),
			param.Method,
			param.Path,
			param.Request.Proto,
			param.StatusCode,
			param.Latency,
			param.Request.UserAgent(),
			param.ErrorMessage,
		)
	})
}

// setupMiddleware configures all middleware for the service
func (h *SubscriptionHandlers) SetupMiddleware(r *gin.Engine) {
	r.Use(h.loggingMiddleware())
	r.Use(gin.Recovery())
	r.Use(h.corsMiddleware())
	r.Use(h.rateLimitMiddleware())
}

// =============================================================================
// CACHE MONITORING AND MANAGEMENT ENDPOINTS
// =============================================================================

// GetCacheMetrics returns cache performance metrics
func (h *SubscriptionHandlers) GetCacheMetrics(c *gin.Context) {
	metrics := h.service.db.GetCacheMetrics()
	if metrics != nil {
		
		c.JSON(http.StatusOK, gin.H{
			"success": true,
			"data": gin.H{
				"cache_stats": metrics,
				"timestamp":   time.Now().UTC(),
				"service":     "user-subscription-service",
			},
		})
		return
	}
	
	c.JSON(http.StatusServiceUnavailable, gin.H{
		"success": false,
		"error":   "Cache metrics not available",
	})
}

// GetCacheHealth returns Redis health information
func (h *SubscriptionHandlers) GetCacheHealth(c *gin.Context) {
	if h.service.db.GetCache() != nil {
		// Test Redis connection
		err := h.service.db.GetCache().Ping()
		if err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"success": false,
				"error":   "Redis connection failed",
				"details": err.Error(),
			})
			return
		}
		
		// Get Redis info
		ctx := c.Request.Context()
		redisInfo, err := h.service.db.GetCache().metrics.GetRedisInfo(ctx)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"success": false,
				"error":   "Failed to get Redis info",
				"details": err.Error(),
			})
			return
		}
		
		// Get memory usage for common cache patterns
		memoryUsage, _ := h.service.db.GetCache().metrics.GetCacheMemoryUsage(ctx, []string{
			"subscription:*",
			"quota:*", 
			"plan_features:*",
			"usage:*",
		})
		
		c.JSON(http.StatusOK, gin.H{
			"success": true,
			"data": gin.H{
				"status":        "healthy",
				"redis_info":    redisInfo,
				"memory_usage":  memoryUsage,
				"timestamp":     time.Now().UTC(),
			},
		})
		return
	}
	
	c.JSON(http.StatusServiceUnavailable, gin.H{
		"success": false,
		"error":   "Cache not available",
	})
}

// WarmupCache manually triggers cache warming
func (h *SubscriptionHandlers) WarmupCache(c *gin.Context) {
	if h.service.db.GetCache() != nil {
		ctx := c.Request.Context()
		
		// Run all warmup tasks
		go func() {
			h.service.db.GetCache().warmupSubscriptionPlans(ctx)
			h.service.db.GetCache().warmupActiveSubscriptions(ctx)
			h.service.db.GetCache().warmupUserQuotas(ctx)
		}()
		
		c.JSON(http.StatusOK, gin.H{
			"success": true,
			"message": "Cache warmup initiated",
			"timestamp": time.Now().UTC(),
		})
		return
	}
	
	c.JSON(http.StatusServiceUnavailable, gin.H{
		"success": false,
		"error":   "Cache not available",
	})
}