package main

import (
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// HandlerManager manages all HTTP handlers
type HandlerManager struct {
	dbManager      DatabaseManagerInterface
	serviceManager ServiceManagerInterface
	middleware     MiddlewareManagerInterface
	config         *ServiceConfig
}

// NewHandlerManager creates a new handler manager
func NewHandlerManager(dbManager DatabaseManagerInterface, serviceManager ServiceManagerInterface, middleware MiddlewareManagerInterface, config *ServiceConfig) *HandlerManager {
	return &HandlerManager{
		dbManager:      dbManager,
		serviceManager: serviceManager,
		middleware:     middleware,
		config:         config,
	}
}

// Authentication Handlers

// LoginHandler handles user login
func (hm *HandlerManager) LoginHandler(c *gin.Context) {
	var req LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "Invalid request",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	// Authenticate user via database
	user, err := hm.dbManager.AuthenticateUser(req.Email, req.Password)
	if err != nil {
		c.JSON(http.StatusUnauthorized, ErrorResponse{
			Error:     "Authentication failed",
			Message:   "Invalid email or password",
			Timestamp: time.Now(),
		})
		return
	}

	// Generate JWT token
	tokenString, err := hm.middleware.GenerateJWT(user)
	expiresAt := time.Now().Add(time.Duration(hm.config.AccessTokenExpireMinutes) * time.Minute)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Token generation failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	// Update last login
	if err := hm.dbManager.UpdateLastLogin(user.ID.String()); err != nil {
		// Log error but don't fail the request
		fmt.Printf("Failed to update last login for user %s: %v\n", user.ID.String(), err)
	}

	// Create session
	session := &Session{
		ID:           uuid.New().String(),
		UserID:       user.ID.String(),
		IPAddress:    c.ClientIP(),
		UserAgent:    c.GetHeader("User-Agent"),
		CreatedAt:    time.Now(),
		LastActivity: time.Now(),
		IsActive:     true,
		RequestCount: 1,
		ExpiresAt:    expiresAt,
	}

	sessionReq := &SessionCreateRequest{
		UserID:    session.UserID,
		IPAddress: session.IPAddress,
		UserAgent: session.UserAgent,
	}
	if _, err := hm.dbManager.CreateSession(sessionReq); err != nil {
		// Log error but don't fail the request
		fmt.Printf("Failed to create session for user %s: %v\n", user.ID.String(), err)
	}

	response := TokenResponse{
		AccessToken: tokenString,
		TokenType:   "Bearer",
		ExpiresIn:   hm.config.AccessTokenExpireMinutes * 60,
		ExpiresAt:   expiresAt,
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      response,
		Timestamp: time.Now(),
	})
}

// RegisterHandler handles user registration
func (hm *HandlerManager) RegisterHandler(c *gin.Context) {
	var req RegisterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "Invalid request",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	// Create user via database
	user, err := hm.dbManager.CreateUser(&req)
	if err != nil {
		status := http.StatusInternalServerError
		if err.Error() == "user already exists" {
			status = http.StatusConflict
		}
		c.JSON(status, ErrorResponse{
			Error:     "Registration failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	// Generate JWT token
	tokenString, err := hm.middleware.GenerateJWT(user)
	expiresAt := time.Now().Add(time.Duration(hm.config.AccessTokenExpireMinutes) * time.Minute)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Token generation failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	response := TokenResponse{
		AccessToken: tokenString,
		TokenType:   "Bearer",
		ExpiresIn:   hm.config.AccessTokenExpireMinutes * 60,
		ExpiresAt:   expiresAt,
	}

	c.JSON(http.StatusCreated, APIResponse{
		Success:   true,
		Data:      response,
		Timestamp: time.Now(),
	})
}

// LogoutHandler handles user logout
func (hm *HandlerManager) LogoutHandler(c *gin.Context) {
	sessionID := c.GetString("session_id")

	if sessionID != "" {
		if err := hm.dbManager.InvalidateSession(sessionID); err != nil {
			fmt.Printf("Failed to invalidate session %s: %v\n", sessionID, err)
		}
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      gin.H{"message": "Logged out successfully"},
		Timestamp: time.Now(),
	})
}

// Chat Handlers

// ChatHandler handles chat messages
func (hm *HandlerManager) ChatHandler(c *gin.Context) {
	var req ChatMessageRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "Invalid request",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	userID := c.GetString("user_id")
	sessionID := c.GetString("session_id")

	// Set user ID and session ID if not provided
	if req.UserID == "" && userID != "" {
		req.UserID = userID
	}
	if req.SessionID == "" && sessionID != "" {
		req.SessionID = sessionID
	}

	startTime := time.Now()

	// Check usage limits
	if userID != "" {
		err := hm.serviceManager.CheckUsageLimits(userID)
		if err != nil {
			fmt.Printf("Failed to check usage limits for user %s: %v\n", userID, err)
			c.JSON(http.StatusTooManyRequests, ErrorResponse{
				Error:     "Usage limit exceeded",
				Message:   err.Error(),
				Timestamp: time.Now(),
			})
			return
		}
	}

	// Perform safety analysis
	safetyReq := &SafetyAnalysisRequest{
		Content:   req.Message,
		UserID:    req.UserID,
		SessionID: req.SessionID,
	}

	safetyResult, err := hm.serviceManager.AnalyzeSafety(c.Request.Context(), safetyReq)
	if err != nil {
		fmt.Printf("Safety analysis failed: %v\n", err)
	}

	// Check if content is safe
	if safetyResult != nil && !safetyResult.IsSafe {
		if safetyResult.RequiresEscalation {
			// Log critical safety issue
			fmt.Printf("CRITICAL SAFETY ALERT: User %s, Session %s, Content: %s\n", userID, sessionID, req.Message)
		}

		response := &ChatMessageResponse{
			SessionID:       req.SessionID,
			MessageID:       uuid.New().String(),
			Answer:          safetyResult.SafeResponse,
			ResponseType:    "safety_filtered",
			ContextUsed:     false,
			ResponseTime:    float64(time.Since(startTime).Nanoseconds()) / 1e6,
			SafetyAnalysis:  safetyResult,
		}

		c.JSON(http.StatusOK, APIResponse{
			Success:   true,
			Data:      response,
			Timestamp: time.Now(),
		})
		return
	}

	// Perform emotion analysis
	emotionResult, err := hm.serviceManager.AnalyzeEmotion(c.Request.Context(), req.Message)
	if err != nil {
		fmt.Printf("Emotion analysis failed: %v\n", err)
	}

	// Perform RAG search if enabled
	var sources []SourceDocument
	if req.EnableRAG {
		searchReq := &SearchRequest{
			Query:     req.Message,
			TopK:      req.TopK,
			Route:     req.Route,
			Filters:   req.Filters,
			UserID:    req.UserID,
			SessionID: req.SessionID,
			Metadata:  req.Metadata,
		}

		if searchReq.TopK == 0 {
			searchReq.TopK = 5
		}

		searchResponse, err := hm.serviceManager.SearchDocuments(c.Request.Context(), searchReq)
		if err != nil {
			fmt.Printf("Search failed: %v\n", err)
		} else if searchResponse != nil {
			sources = searchResponse.Results
		}
	}

	// Generate AI response
	response, err := hm.serviceManager.GenerateResponse(c.Request.Context(), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Generation failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	// Enrich response with analysis results and sources
	response.ResponseTime = float64(time.Since(startTime).Nanoseconds()) / 1e6
	response.SafetyAnalysis = safetyResult
	response.EmotionAnalysis = emotionResult
	if len(sources) > 0 {
		response.Sources = sources
		response.ContextUsed = true
	}

	// Save conversation message
	userMessage := &ConversationMessage{
		ID:              uuid.New().String(),
		SessionID:       response.SessionID,
		UserID:          userID,
		Content:         req.Message,
		Type:            "user",
		Timestamp:       time.Now(),
		SafetyAnalysis:  safetyResult,
		EmotionAnalysis: emotionResult,
	}

	assistantMessage := &ConversationMessage{
		ID:              response.MessageID,
		SessionID:       response.SessionID,
		UserID:          userID,
		Content:         response.Answer,
		Type:            "assistant",
		Timestamp:       time.Now(),
		Sources:         response.Sources,
	}

	// Save messages asynchronously
	go func() {
		if err := hm.serviceManager.SaveConversationMessage(c.Request.Context(), userMessage); err != nil {
			fmt.Printf("Failed to save user message: %v\n", err)
		}
		if err := hm.serviceManager.SaveConversationMessage(c.Request.Context(), assistantMessage); err != nil {
			fmt.Printf("Failed to save assistant message: %v\n", err)
		}
	}()

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      response,
		Timestamp: time.Now(),
	})
}

// Search Handlers

// SearchHandler handles search requests
func (hm *HandlerManager) SearchHandler(c *gin.Context) {
	var req SearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "Invalid request",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	userID := c.GetString("user_id")
	sessionID := c.GetString("session_id")

	// Set user ID and session ID if not provided
	if req.UserID == "" && userID != "" {
		req.UserID = userID
	}
	if req.SessionID == "" && sessionID != "" {
		req.SessionID = sessionID
	}

	// Check usage limits
	if userID != "" {
		err := hm.serviceManager.CheckUsageLimits(userID)
		if err != nil {
			fmt.Printf("Failed to check usage limits for user %s: %v\n", userID, err)
			c.JSON(http.StatusTooManyRequests, ErrorResponse{
				Error:     "Usage limit exceeded",
				Message:   err.Error(),
				Timestamp: time.Now(),
			})
			return
		}
	}

	// Perform search
	response, err := hm.serviceManager.SearchDocuments(c.Request.Context(), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Search failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      response,
		Timestamp: time.Now(),
	})
}

// Session Handlers

// GetSessionHandler retrieves session information
func (hm *HandlerManager) GetSessionHandler(c *gin.Context) {
	sessionID := c.Param("session_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "Invalid request",
			Message:   "Session ID is required",
			Timestamp: time.Now(),
		})
		return
	}

	session, err := hm.dbManager.GetSession(sessionID)
	if err != nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Error:     "Session not found",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      session,
		Timestamp: time.Now(),
	})
}

// GetSessionStatsHandler retrieves session statistics
func (hm *HandlerManager) GetSessionStatsHandler(c *gin.Context) {
	stats, err := hm.dbManager.GetSessionStats()
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Failed to get session stats",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      stats,
		Timestamp: time.Now(),
	})
}

// Conversation History Handlers

// GetConversationHistoryHandler retrieves conversation history
func (hm *HandlerManager) GetConversationHistoryHandler(c *gin.Context) {
	sessionID := c.Param("session_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "Invalid request",
			Message:   "Session ID is required",
			Timestamp: time.Now(),
		})
		return
	}

	userID := c.GetString("user_id")
	history, err := hm.serviceManager.GetConversationHistory(c.Request.Context(), sessionID, userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Failed to get conversation history",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	if history == nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Error:     "Conversation not found",
			Message:   "No conversation history found for this session",
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      history,
		Timestamp: time.Now(),
	})
}

// User Management Handlers

// GetUserProfileHandler retrieves user profile
func (hm *HandlerManager) GetUserProfileHandler(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, ErrorResponse{
			Error:     "Unauthorized",
			Message:   "User ID not found in context",
			Timestamp: time.Now(),
		})
		return
	}

	user, err := hm.dbManager.GetUser(userID)
	if err != nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Error:     "User not found",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      user,
		Timestamp: time.Now(),
	})
}

// GetUserSubscriptionHandler retrieves user subscription
func (hm *HandlerManager) GetUserSubscriptionHandler(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, ErrorResponse{
			Error:     "Unauthorized",
			Message:   "User ID not found in context",
			Timestamp: time.Now(),
		})
		return
	}

	subscription, err := hm.serviceManager.GetUserSubscription(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Failed to get subscription",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      subscription,
		Timestamp: time.Now(),
	})
}

// Health Check Handlers

// HealthHandler provides basic health check
func (hm *HandlerManager) HealthHandler(c *gin.Context) {
	health := &HealthStatus{
		Service:     "api-gateway",
		Status:      "healthy",
		Version:     "1.0.0",
		Timestamp:   time.Now(),
		Environment: hm.config.Environment,
	}

	c.JSON(http.StatusOK, health)
}

// DetailedHealthHandler provides comprehensive health check
func (hm *HandlerManager) DetailedHealthHandler(c *gin.Context) {
	// Get database health
	databases := make(map[string]DatabaseHealth)
	
	err := hm.dbManager.PingPostgres()
	status := "healthy"
	if err != nil {
		status = "unhealthy"
	}
	databases["postgres"] = DatabaseHealth{
		Status:    status,
		LastCheck: time.Now(),
	}
	
	err = hm.dbManager.PingRedis()
	status = "healthy"
	if err != nil {
		status = "unhealthy"
	}
	databases["redis"] = DatabaseHealth{
		Status:    status,
		LastCheck: time.Now(),
	}

	// Get service health from service manager
	servicesPtr := hm.serviceManager.GetServiceHealth()
	
	// Convert to non-pointer map
	services := make(map[string]ServiceHealth)
	for name, healthPtr := range servicesPtr {
		if healthPtr != nil {
			services[name] = *healthPtr
		}
	}
	
	// Determine overall status
	overall := "healthy"
	for _, dbHealth := range databases {
		if dbHealth.Status == "unhealthy" {
			overall = "unhealthy"
			break
		} else if dbHealth.Status == "degraded" && overall == "healthy" {
			overall = "degraded"
		}
	}
	
	for _, serviceHealth := range services {
		if serviceHealth.Status == "unhealthy" {
			overall = "unhealthy"
			break
		} else if serviceHealth.Status == "degraded" && overall == "healthy" {
			overall = "degraded"
		}
	}

	health := &DetailedHealthStatus{
		Overall:   overall,
		Services:  services,
		Databases: databases,
		Timestamp: time.Now(),
	}

	statusCode := http.StatusOK
	if overall == "unhealthy" {
		statusCode = http.StatusServiceUnavailable
	} else if overall == "degraded" {
		statusCode = http.StatusOK // Still OK but with warnings
	}

	c.JSON(statusCode, health)
}

// Analytics Handlers

// TrackEventHandler tracks analytics events
func (hm *HandlerManager) TrackEventHandler(c *gin.Context) {
	var event AnalyticsEvent
	if err := c.ShouldBindJSON(&event); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "Invalid request",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	// Enrich event with context
	event.ID = uuid.New().String()
	event.Timestamp = time.Now()
	event.IPAddress = c.ClientIP()
	event.UserAgent = c.GetHeader("User-Agent")
	
	if userID := c.GetString("user_id"); userID != "" {
		event.UserID = userID
	}
	if sessionID := c.GetString("session_id"); sessionID != "" {
		event.SessionID = sessionID
	}

	// Store event (you would typically send this to an analytics service)
	if err := hm.dbManager.StoreAnalyticsEvent(&event); err != nil {
		fmt.Printf("Failed to store analytics event: %v\n", err)
		// Don't return error to client for analytics failures
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      gin.H{"event_id": event.ID},
		Timestamp: time.Now(),
	})
}

// Rate Limit Info Handler

// GetRateLimitInfoHandler returns current rate limit status for user
func (hm *HandlerManager) GetRateLimitInfoHandler(c *gin.Context) {
	userID := c.GetString("user_id")
	if userID == "" {
		c.JSON(http.StatusUnauthorized, ErrorResponse{
			Error:     "Unauthorized",
			Message:   "User ID not found in context",
			Timestamp: time.Now(),
		})
		return
	}

	// Get rate limit info for different windows
	rateLimits := make(map[string]*RateLimitInfo)
	
	windows := map[string]time.Duration{
		"second": time.Second,
		"minute": time.Minute,
		"hour":   time.Hour,
	}
	
	limits := map[string]int{
		"second": hm.config.MaxRequestsPerSecond,
		"minute": hm.config.MaxRequestsPerMinute,
		"hour":   hm.config.MaxRequestsPerHour,
	}

	for window, duration := range windows {
		key := fmt.Sprintf("user:%s", userID)
		allowed, info, err := hm.dbManager.CheckRateLimit(key, limits[window], duration)
		if err != nil {
			fmt.Printf("Failed to check rate limit for %s: %v\n", window, err)
			continue
		}
		
		if info != nil {
			info.Window = window
			rateLimits[window] = info
		} else if allowed {
			rateLimits[window] = &RateLimitInfo{
				Limit:     limits[window],
				Remaining: limits[window],
				Reset:     time.Now().Add(duration),
				Window:    window,
			}
		}
	}

	c.JSON(http.StatusOK, APIResponse{
		Success:   true,
		Data:      rateLimits,
		Timestamp: time.Now(),
	})
}