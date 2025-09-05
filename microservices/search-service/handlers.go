package main

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type SearchHandlers struct {
	service *SearchService
	logger  *zap.Logger
}

func NewSearchHandlers(service *SearchService, logger *zap.Logger) *SearchHandlers {
	return &SearchHandlers{
		service: service,
		logger:  logger,
	}
}

func (h *SearchHandlers) HealthCheck(c *gin.Context) {
	health := h.service.checkServiceHealth(c.Request.Context())
	
	status := "healthy"
	if dbHealth, ok := health["databases"].(map[string]interface{}); ok {
		if overall, exists := dbHealth["overall_status"]; exists && overall != "healthy" {
			status = "degraded"
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"status":    status,
		"service":   "search-service",
		"timestamp": time.Now(),
		"version":   "1.0.0",
		"health":    health,
	})
}

func (h *SearchHandlers) Search(c *gin.Context) {
	var request SearchRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		h.logger.Error("Invalid search request", zap.Error(err))
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid request format",
			"details": err.Error(),
		})
		return
	}

	// Get user information from headers (set by API Gateway or auth middleware)
	userID := c.GetHeader("X-User-ID")
	subscriptionPlan := c.GetHeader("X-Subscription-Plan")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "User authentication required",
		})
		return
	}
	if subscriptionPlan == "" {
		subscriptionPlan = "free"
	}

	// Perform search
	response, err := h.service.performSearch(c.Request.Context(), request, userID, subscriptionPlan)
	if err != nil {
		h.logger.Error("Search failed", 
			zap.String("user_id", userID),
			zap.String("query", request.Query),
			zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Search failed",
		})
		return
	}

	h.logger.Info("Search completed successfully",
		zap.String("user_id", userID),
		zap.String("route_used", response.RouteUsed),
		zap.Int("results_count", response.TotalResults),
		zap.Float64("processing_time_ms", response.ProcessingTimeMs))

	c.JSON(http.StatusOK, response)
}

func (h *SearchHandlers) SemanticSearch(c *gin.Context) {
	var request SearchRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		h.logger.Error("Invalid semantic search request", zap.Error(err))
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid request format",
			"details": err.Error(),
		})
		return
	}

	// Get user information from headers
	userID := c.GetHeader("X-User-ID")
	subscriptionPlan := c.GetHeader("X-Subscription-Plan")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "User authentication required",
		})
		return
	}
	if subscriptionPlan == "" {
		subscriptionPlan = "free"
	}

	// Check if user has access to semantic search
	if subscriptionPlan == "free" {
		c.JSON(http.StatusForbidden, gin.H{
			"error":      "Semantic search is not available for free plan",
			"upgrade_to": "pro",
			"upgrade_url": "/billing/plans",
		})
		return
	}

	// Force semantic route
	request.Route = "semantic"

	// Perform search
	response, err := h.service.performSearch(c.Request.Context(), request, userID, subscriptionPlan)
	if err != nil {
		h.logger.Error("Semantic search failed", 
			zap.String("user_id", userID),
			zap.String("query", request.Query),
			zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Semantic search failed",
		})
		return
	}

	h.logger.Info("Semantic search completed successfully",
		zap.String("user_id", userID),
		zap.Int("results_count", response.TotalResults),
		zap.Float64("processing_time_ms", response.ProcessingTimeMs))

	c.JSON(http.StatusOK, response)
}

func (h *SearchHandlers) GetSearchSuggestions(c *gin.Context) {
	query := c.Query("query")
	if query == "" || len(query) < 2 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Query parameter must be at least 2 characters",
		})
		return
	}

	limitStr := c.DefaultQuery("limit", "5")
	limit, err := strconv.Atoi(limitStr)
	if err != nil || limit < 1 || limit > 10 {
		limit = 5
	}

	// Get user information from headers
	userID := c.GetHeader("X-User-ID")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "User authentication required",
		})
		return
	}

	suggestions, err := h.service.generateSuggestions(c.Request.Context(), query, limit)
	if err != nil {
		h.logger.Error("Failed to generate suggestions", 
			zap.String("user_id", userID),
			zap.String("query", query),
			zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to generate suggestions",
		})
		return
	}

	h.logger.Info("Search suggestions generated",
		zap.String("user_id", userID),
		zap.String("query", query),
		zap.Int("suggestions_count", len(suggestions)))

	c.JSON(http.StatusOK, suggestions)
}