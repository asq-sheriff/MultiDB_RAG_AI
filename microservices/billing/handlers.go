package main

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

type BillingHandlers struct {
	db     *DatabaseManager
	cache  *RedisCache
	logger *zap.Logger
}

func NewBillingHandlers(db *DatabaseManager, cache *RedisCache, logger *zap.Logger) *BillingHandlers {
	return &BillingHandlers{
		db:     db,
		cache:  cache,
		logger: logger,
	}
}

// GetAvailablePlans returns available subscription plans
func (h *BillingHandlers) GetAvailablePlans(c *gin.Context) {
	plans := GetPlanDefinitions()
	
	response := AvailablePlansResponse{
		Plans:    plans,
		Currency: "USD",
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    response,
	})
}

// GetUserSubscription gets user's current subscription
func (h *BillingHandlers) GetUserSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	// Check cache first
	subscription, err := h.cache.GetCachedSubscription(userID)
	if err != nil {
		h.logger.Error("Cache error", zap.Error(err))
	}

	if subscription == nil {
		// Get from database
		subscription, err = h.db.GetActiveSubscription(userID)
		if err != nil {
			h.logger.Error("Database error", zap.Error(err))
			c.JSON(http.StatusInternalServerError, APIResponse{
				Success: false,
				Error:   "Failed to get subscription",
			})
			return
		}

		// Cache the result
		if subscription != nil {
			_ = h.cache.CacheSubscription(userID, subscription, 15*time.Minute)
		}
	}

	if subscription == nil {
		c.JSON(http.StatusNotFound, APIResponse{
			Success: false,
			Error:   "No active subscription found",
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    subscription,
	})
}

// CreateSubscription creates a new subscription
func (h *BillingHandlers) CreateSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	var req SubscriptionCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid request body",
		})
		return
	}

	// Validate plan type
	planDef := GetPlanDefinition(req.PlanType)
	if planDef == nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid plan type",
		})
		return
	}

	// Create subscription
	subscription, err := h.db.CreateSubscription(userID, req.PlanType, req.BillingCycle)
	if err != nil {
		h.logger.Error("Failed to create subscription", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to create subscription",
		})
		return
	}

	// Invalidate cache
	_ = h.cache.InvalidateSubscriptionCache(userID)

	c.JSON(http.StatusCreated, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription created successfully",
	})
}

// UpdateSubscription updates an existing subscription
func (h *BillingHandlers) UpdateSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	var req SubscriptionUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid request body",
		})
		return
	}

	// Validate plan type
	planDef := GetPlanDefinition(req.PlanType)
	if planDef == nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid plan type",
		})
		return
	}

	// Update subscription
	subscription, err := h.db.UpdateSubscription(userID, req.PlanType, req.BillingCycle)
	if err != nil {
		h.logger.Error("Failed to update subscription", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to update subscription",
		})
		return
	}

	// Invalidate cache
	_ = h.cache.InvalidateUserCaches(userID)

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    subscription,
		Message: "Subscription updated successfully",
	})
}

// CancelSubscription cancels a user's subscription
func (h *BillingHandlers) CancelSubscription(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	err = h.db.CancelSubscription(userID)
	if err != nil {
		h.logger.Error("Failed to cancel subscription", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to cancel subscription",
		})
		return
	}

	// Invalidate cache
	_ = h.cache.InvalidateUserCaches(userID)

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Message: "Subscription cancelled successfully",
	})
}

// RecordUsage records usage for billing
func (h *BillingHandlers) RecordUsage(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	var req UsageRecordRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid request body",
		})
		return
	}

	err = h.db.RecordUsage(userID, req.ResourceType, req.Quantity, req.ExtraData)
	if err != nil {
		h.logger.Error("Failed to record usage", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to record usage",
		})
		return
	}

	// Invalidate quota cache
	_ = h.cache.InvalidateQuotaCache(userID, req.ResourceType)

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Message: "Usage recorded successfully",
	})
}

// CheckQuota checks user's quota for a resource type
func (h *BillingHandlers) CheckQuota(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	resourceType := c.Param("resource_type")
	if resourceType == "" {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Resource type is required",
		})
		return
	}

	// Check cache first
	quotaInfo, err := h.cache.GetCachedQuota(userID, resourceType)
	if err != nil {
		h.logger.Error("Cache error", zap.Error(err))
	}

	if quotaInfo == nil {
		// Get from database
		quotaInfo, err = h.db.CheckQuota(userID, resourceType)
		if err != nil {
			h.logger.Error("Database error", zap.Error(err))
			c.JSON(http.StatusInternalServerError, APIResponse{
				Success: false,
				Error:   "Failed to check quota",
			})
			return
		}

		// Cache the result
		if quotaInfo != nil {
			_ = h.cache.CacheQuota(userID, resourceType, quotaInfo, 5*time.Minute)
		}
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    quotaInfo,
	})
}

// GetUsageSummary gets user's usage summary
func (h *BillingHandlers) GetUsageSummary(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	// Check cache first
	summary, err := h.cache.GetCachedUsageSummary(userID)
	if err != nil {
		h.logger.Error("Cache error", zap.Error(err))
	}

	if summary == nil {
		// Get from database
		summary, err = h.db.GetUsageSummary(userID)
		if err != nil {
			h.logger.Error("Database error", zap.Error(err))
			c.JSON(http.StatusInternalServerError, APIResponse{
				Success: false,
				Error:   "Failed to get usage summary",
			})
			return
		}

		// Cache the result
		if summary != nil {
			_ = h.cache.CacheUsageSummary(userID, summary, 10*time.Minute)
		}
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    summary,
	})
}

// GetDetailedUsage gets detailed usage breakdown
func (h *BillingHandlers) GetDetailedUsage(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	// Parse query parameters
	startDateStr := c.Query("start_date")
	endDateStr := c.Query("end_date")
	limitStr := c.DefaultQuery("limit", "100")

	var startDate, endDate time.Time
	var err1, err2 error

	if startDateStr != "" {
		startDate, err1 = time.Parse(time.RFC3339, startDateStr)
	}
	if endDateStr != "" {
		endDate, err2 = time.Parse(time.RFC3339, endDateStr)
	}

	if err1 != nil || err2 != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid date format. Use RFC3339 format",
		})
		return
	}

	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 100
	}

	detailedUsage, err := h.db.GetDetailedUsage(userID, startDate, endDate, limit)
	if err != nil {
		h.logger.Error("Database error", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to get detailed usage",
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    detailedUsage,
	})
}

// GetBillingHistory gets user's billing history
func (h *BillingHandlers) GetBillingHistory(c *gin.Context) {
	userIDStr := c.Param("user_id")
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, APIResponse{
			Success: false,
			Error:   "Invalid user ID format",
		})
		return
	}

	limitStr := c.DefaultQuery("limit", "50")
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit <= 0 {
		limit = 50
	}

	billingHistory, err := h.db.GetBillingHistory(userID, limit)
	if err != nil {
		h.logger.Error("Database error", zap.Error(err))
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   "Failed to get billing history",
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success: true,
		Data:    billingHistory,
	})
}

// HealthCheck endpoint
func (h *BillingHandlers) HealthCheck(c *gin.Context) {
	health := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().UTC(),
		"service":   "billing-service-go",
	}

	// Check database
	if err := h.db.Ping(); err != nil {
		health["status"] = "unhealthy"
		health["database_error"] = err.Error()
	}

	// Check cache
	if err := h.cache.Ping(); err != nil {
		health["status"] = "unhealthy"
		health["cache_error"] = err.Error()
	}

	statusCode := http.StatusOK
	if health["status"] == "unhealthy" {
		statusCode = http.StatusServiceUnavailable
	}

	c.JSON(statusCode, health)
}

// Rate limiting middleware
func (h *BillingHandlers) RateLimitMiddleware() gin.HandlerFunc {
	return gin.HandlerFunc(func(c *gin.Context) {
		// Extract user ID or IP for rate limiting
		userID := c.GetHeader("X-User-ID")
		if userID == "" {
			userID = c.ClientIP()
		}

		key := "rate_limit:" + userID
		allowed, err := h.cache.CheckRateLimit(key, 100, time.Minute) // 100 requests per minute

		if err != nil {
			h.logger.Error("Rate limit check failed", zap.Error(err))
			// Continue on error to not block legitimate requests
			c.Next()
			return
		}

		if !allowed {
			c.JSON(http.StatusTooManyRequests, APIResponse{
				Success: false,
				Error:   "Rate limit exceeded. Please try again later.",
			})
			c.Abort()
			return
		}

		c.Next()
	})
}