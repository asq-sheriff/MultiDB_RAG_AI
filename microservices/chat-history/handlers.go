package main

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// ChatHistoryHandlers provides HTTP handlers for chat history service
type ChatHistoryHandlers struct {
	service *ChatHistoryService
	logger  *zap.Logger
}

// NewChatHistoryHandlers creates new handlers
func NewChatHistoryHandlers(service *ChatHistoryService, logger *zap.Logger) *ChatHistoryHandlers {
	return &ChatHistoryHandlers{
		service: service,
		logger:  logger,
	}
}

// ========================================
// Core Chat Message Endpoints
// ========================================

// SendMessage handles POST /api/v1/chat/message
func (h *ChatHistoryHandlers) SendMessage(c *gin.Context) {
	var req SendMessageRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		h.logger.Error("Invalid request body", zap.Error(err))
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid request format",
			"details": err.Error(),
		})
		return
	}

	// Add request context
	ctx := c.Request.Context()

	// Process the message
	response, err := h.service.ProcessMessage(ctx, &req)
	if err != nil {
		h.logger.Error("Failed to process message", zap.Error(err))
		
		// Determine appropriate status code based on error type
		statusCode := http.StatusInternalServerError
		if contains(err.Error(), []string{"invalid", "validation", "required"}) {
			statusCode = http.StatusBadRequest
		} else if contains(err.Error(), []string{"rate limit", "exceeded"}) {
			statusCode = http.StatusTooManyRequests
		}
		
		c.JSON(statusCode, gin.H{
			"error": "Failed to process message",
			"details": err.Error(),
		})
		return
	}

	// Log successful processing
	h.logger.Info("Message processed successfully",
		zap.String("session_id", req.SessionID),
		zap.String("user_id", req.UserID),
		zap.Int("response_time_ms", response.ResponseTimeMs))

	c.JSON(http.StatusOK, response)
}

// GetHistory handles GET /api/v1/chat/history
func (h *ChatHistoryHandlers) GetHistory(c *gin.Context) {
	var req GetHistoryRequest
	
	// Bind query parameters
	if err := c.ShouldBindQuery(&req); err != nil {
		h.logger.Error("Invalid query parameters", zap.Error(err))
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid query parameters",
			"details": err.Error(),
		})
		return
	}

	// Parse optional time parameters
	if startTimeStr := c.Query("start_time"); startTimeStr != "" {
		if startTime, err := time.Parse(time.RFC3339, startTimeStr); err == nil {
			req.StartTime = &startTime
		}
	}

	if endTimeStr := c.Query("end_time"); endTimeStr != "" {
		if endTime, err := time.Parse(time.RFC3339, endTimeStr); err == nil {
			req.EndTime = &endTime
		}
	}

	// Add request context
	ctx := c.Request.Context()

	// Get conversation history
	response, err := h.service.GetConversationHistory(ctx, &req)
	if err != nil {
		h.logger.Error("Failed to get conversation history", zap.Error(err))
		
		statusCode := http.StatusInternalServerError
		if contains(err.Error(), []string{"invalid", "required"}) {
			statusCode = http.StatusBadRequest
		} else if contains(err.Error(), []string{"not found"}) {
			statusCode = http.StatusNotFound
		}
		
		c.JSON(statusCode, gin.H{
			"error":   "Failed to get conversation history",
			"details": err.Error(),
		})
		return
	}

	h.logger.Info("Conversation history retrieved",
		zap.String("session_id", req.SessionID),
		zap.Int("message_count", len(response.Messages)))

	c.JSON(http.StatusOK, response)
}

// SubmitFeedback handles POST /api/v1/chat/feedback
func (h *ChatHistoryHandlers) SubmitFeedback(c *gin.Context) {
	var req SubmitFeedbackRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		h.logger.Error("Invalid feedback request", zap.Error(err))
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid request format",
			"details": err.Error(),
		})
		return
	}

	// Add request context
	ctx := c.Request.Context()

	// Submit feedback
	response, err := h.service.SubmitFeedback(ctx, &req)
	if err != nil {
		h.logger.Error("Failed to submit feedback", zap.Error(err))
		
		statusCode := http.StatusInternalServerError
		if contains(err.Error(), []string{"invalid", "rating"}) {
			statusCode = http.StatusBadRequest
		}
		
		c.JSON(statusCode, gin.H{
			"error":   "Failed to submit feedback",
			"details": err.Error(),
		})
		return
	}

	h.logger.Info("Feedback submitted successfully",
		zap.String("feedback_id", response.FeedbackID),
		zap.String("session_id", req.SessionID),
		zap.Int("rating", req.Rating))

	c.JSON(http.StatusCreated, response)
}

// ========================================
// Enhanced Chat Endpoints (Gateway-style)
// ========================================

// GetEmotionHistory handles GET /api/v1/chat/emotion/history/:session_id
func (h *ChatHistoryHandlers) GetEmotionHistory(c *gin.Context) {
	sessionID := c.Param("session_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Session ID is required",
		})
		return
	}

	// Validate session ID format
	if _, err := uuid.Parse(sessionID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid session ID format",
		})
		return
	}

	limit := 50
	if limitStr := c.Query("limit"); limitStr != "" {
		if parsedLimit, err := strconv.Atoi(limitStr); err == nil && parsedLimit > 0 {
			limit = parsedLimit
			if limit > 200 {
				limit = 200 // Maximum limit
			}
		}
	}

	ctx := c.Request.Context()

	// Get conversation history with emotion data
	historyReq := &GetHistoryRequest{
		SessionID: sessionID,
		Limit:     limit,
	}

	history, err := h.service.GetConversationHistory(ctx, historyReq)
	if err != nil {
		h.logger.Error("Failed to get emotion history", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to retrieve emotion history",
			"details": err.Error(),
		})
		return
	}

	// Extract emotion data from messages
	emotionHistory := make([]map[string]interface{}, 0)
	for _, msg := range history.Messages {
		if msg.EmotionLabel != nil {
			emotionEntry := map[string]interface{}{
				"message_id":      msg.MessageID,
				"timestamp":       msg.Timestamp,
				"actor":           msg.Actor,
				"emotion_label":   *msg.EmotionLabel,
				"emotion_valence": msg.EmotionValence,
				"emotion_arousal": msg.EmotionArousal,
			}
			emotionHistory = append(emotionHistory, emotionEntry)
		}
	}

	response := map[string]interface{}{
		"session_id":      sessionID,
		"emotion_history": emotionHistory,
		"total":          len(emotionHistory),
		"message_count":  len(history.Messages),
	}

	c.JSON(http.StatusOK, response)
}

// AnalyzeSafety handles POST /api/v1/chat/safety/test
func (h *ChatHistoryHandlers) AnalyzeSafety(c *gin.Context) {
	var req struct {
		Text    string `json:"text" binding:"required"`
		Context string `json:"context,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request format",
			"details": err.Error(),
		})
		return
	}

	ctx := c.Request.Context()

	// Perform safety analysis
	safetyResult, err := h.service.performSafetyAnalysis(ctx, req.Text)
	if err != nil {
		h.logger.Error("Safety analysis failed", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Safety analysis failed",
			"details": err.Error(),
		})
		return
	}

	if safetyResult == nil {
		// Return default safe response if analysis is not available
		safetyResult = &SafetyAnalysisResult{
			Safe:         true,
			RiskLevel:    "low",
			Categories:   []string{},
			Confidence:   0.5,
			RequiresHuman: false,
			CrisisLevel:  false,
		}
	}

	c.JSON(http.StatusOK, safetyResult)
}

// ========================================
// Session Management Endpoints
// ========================================

// CreateSession handles POST /api/v1/chat/sessions
func (h *ChatHistoryHandlers) CreateSession(c *gin.Context) {
	var req struct {
		UserID  string `json:"user_id" binding:"required"`
		Channel string `json:"channel,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request format",
			"details": err.Error(),
		})
		return
	}

	userUUID, err := uuid.Parse(req.UserID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid user ID format",
		})
		return
	}

	if req.Channel == "" {
		req.Channel = "web"
	}

	ctx := c.Request.Context()

	// Create new session
	session := NewSession(userUUID, req.Channel)
	err = h.service.db.CreateSession(ctx, session)
	if err != nil {
		h.logger.Error("Failed to create session", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create session",
			"details": err.Error(),
		})
		return
	}

	response := map[string]interface{}{
		"session_id": session.SessionID.String(),
		"user_id":    session.UserID.String(),
		"channel":    session.Channel,
		"started_at": session.StartedAt,
		"created_at": session.CreatedAt,
	}

	h.logger.Info("Session created",
		zap.String("session_id", session.SessionID.String()),
		zap.String("user_id", req.UserID),
		zap.String("channel", req.Channel))

	c.JSON(http.StatusCreated, response)
}

// EndSession handles DELETE /api/v1/chat/sessions/:session_id
func (h *ChatHistoryHandlers) EndSession(c *gin.Context) {
	sessionID := c.Param("session_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Session ID is required",
		})
		return
	}

	sessionUUID, err := uuid.Parse(sessionID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid session ID format",
		})
		return
	}

	ctx := c.Request.Context()

	// End the session
	err = h.service.db.EndSession(ctx, sessionUUID)
	if err != nil {
		h.logger.Error("Failed to end session", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to end session",
			"details": err.Error(),
		})
		return
	}

	h.logger.Info("Session ended", zap.String("session_id", sessionID))

	c.JSON(http.StatusOK, gin.H{
		"message":    "Session ended successfully",
		"session_id": sessionID,
		"ended_at":   time.Now(),
	})
}

// GetSession handles GET /api/v1/chat/sessions/:session_id
func (h *ChatHistoryHandlers) GetSession(c *gin.Context) {
	sessionID := c.Param("session_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Session ID is required",
		})
		return
	}

	sessionUUID, err := uuid.Parse(sessionID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid session ID format",
		})
		return
	}

	ctx := c.Request.Context()

	// Get session details
	session, err := h.service.db.GetSession(ctx, sessionUUID)
	if err != nil {
		h.logger.Error("Failed to get session", zap.Error(err))
		
		if contains(err.Error(), []string{"no rows"}) {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Session not found",
			})
		} else {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to get session",
				"details": err.Error(),
			})
		}
		return
	}

	response := map[string]interface{}{
		"session_id": session.SessionID.String(),
		"user_id":    session.UserID.String(),
		"channel":    session.Channel,
		"started_at": session.StartedAt,
		"ended_at":   session.EndedAt,
		"is_active":  session.IsActive(),
		"created_at": session.CreatedAt,
		"updated_at": session.UpdatedAt,
	}

	c.JSON(http.StatusOK, response)
}

// ========================================
// Analytics and Monitoring Endpoints
// ========================================

// GetStats handles GET /api/v1/chat/stats
func (h *ChatHistoryHandlers) GetStats(c *gin.Context) {
	ctx := c.Request.Context()

	stats, err := h.service.GetServiceStats(ctx)
	if err != nil {
		h.logger.Error("Failed to get service stats", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to get service statistics",
			"details": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, stats)
}

// GetSessionAnalytics handles GET /api/v1/chat/analytics/:session_id
func (h *ChatHistoryHandlers) GetSessionAnalytics(c *gin.Context) {
	sessionID := c.Param("session_id")
	if sessionID == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Session ID is required",
		})
		return
	}

	// Validate session ID
	if _, err := uuid.Parse(sessionID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid session ID format",
		})
		return
	}

	ctx := c.Request.Context()

	// Get conversation history to analyze
	historyReq := &GetHistoryRequest{
		SessionID: sessionID,
		Limit:     1000, // Get all messages for analytics
	}

	history, err := h.service.GetConversationHistory(ctx, historyReq)
	if err != nil {
		h.logger.Error("Failed to get session history for analytics", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to get session analytics",
			"details": err.Error(),
		})
		return
	}

	// Analyze the conversation
	analytics := h.analyzeConversation(sessionID, history.Messages)

	c.JSON(http.StatusOK, analytics)
}

// ========================================
// Health Check Endpoint
// ========================================

// HealthCheck handles GET /health
func (h *ChatHistoryHandlers) HealthCheck(c *gin.Context) {
	ctx := c.Request.Context()

	// Check database health
	dbHealth := h.service.db.HealthCheck(ctx)

	// Determine overall health
	healthy := dbHealth.PostgreSQL && dbHealth.ScyllaDB && dbHealth.MongoDB && dbHealth.Redis
	status := "healthy"
	if !healthy {
		status = "degraded"
	}

	response := &HealthCheckResponse{
		Status:    status,
		Timestamp: time.Now(),
		Service:   "chat-history-service-go",
		Version:   "1.0.0",
		Databases: dbHealth,
		Uptime:    time.Since(h.service.startTime),
		Details: map[string]interface{}{
			"postgresql": dbHealth.PostgreSQL,
			"scylladb":   dbHealth.ScyllaDB,
			"mongodb":    dbHealth.MongoDB,
			"redis":      dbHealth.Redis,
		},
	}

	statusCode := http.StatusOK
	if !healthy {
		statusCode = http.StatusServiceUnavailable
	}

	c.JSON(statusCode, response)
}

// ========================================
// Private Helper Methods
// ========================================

// analyzeConversation analyzes conversation messages for analytics
func (h *ChatHistoryHandlers) analyzeConversation(sessionID string, messages []HistoryMessage) *ConversationAnalytics {
	if len(messages) == 0 {
		return &ConversationAnalytics{
			SessionID:           sessionID,
			TotalMessages:       0,
			UserMessages:        0,
			AssistantMessages:   0,
			AverageResponseMs:   0,
			CachedResponses:     0,
			EmotionDistribution: make(map[EmotionLabel]int),
			SafetyFlags:         []string{},
			SessionDurationMs:   0,
			Metadata:            make(map[string]interface{}),
		}
	}

	analytics := &ConversationAnalytics{
		SessionID:           sessionID,
		TotalMessages:       len(messages),
		EmotionDistribution: make(map[EmotionLabel]int),
		SafetyFlags:         []string{},
		Metadata:            make(map[string]interface{}),
	}

	var totalResponseTime int
	var responseCount int
	var firstMessage, lastMessage time.Time

	for i, msg := range messages {
		if i == 0 {
			firstMessage = msg.Timestamp
		}
		if i == len(messages)-1 {
			lastMessage = msg.Timestamp
		}

		// Count message types
		switch msg.Actor {
		case ActorUser:
			analytics.UserMessages++
		case ActorAssistant:
			analytics.AssistantMessages++

			// Count cached responses
			if msg.ResponseTimeMs != nil {
				totalResponseTime += *msg.ResponseTimeMs
				responseCount++
			}
		}

		// Count emotion distribution
		if msg.EmotionLabel != nil {
			emotion := EmotionLabel(*msg.EmotionLabel)
			analytics.EmotionDistribution[emotion]++
		}
	}

	// Calculate averages
	if responseCount > 0 {
		analytics.AverageResponseMs = float64(totalResponseTime) / float64(responseCount)
	}

	// Calculate session duration
	if !firstMessage.IsZero() && !lastMessage.IsZero() {
		analytics.SessionDurationMs = lastMessage.Sub(firstMessage).Milliseconds()
	}

	// Find dominant emotion
	var dominantEmotion EmotionLabel
	var maxCount int
	for emotion, count := range analytics.EmotionDistribution {
		if count > maxCount {
			maxCount = count
			dominantEmotion = emotion
		}
	}
	if maxCount > 0 {
		analytics.DominantEmotion = &dominantEmotion
	}

	return analytics
}

// RequestTimingMiddleware measures request timing
func RequestTimingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		c.Next()
		duration := time.Since(start)
		
		c.Header("X-Response-Time", duration.String())
	}
}

// CORSMiddleware adds CORS headers
func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-User-ID")
		c.Header("Access-Control-Expose-Headers", "X-Response-Time")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

// LoggingMiddleware logs HTTP requests
func LoggingMiddleware(logger *zap.Logger) gin.HandlerFunc {
	return gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		logger.Info("HTTP Request",
			zap.String("method", param.Method),
			zap.String("path", param.Path),
			zap.Int("status", param.StatusCode),
			zap.Duration("latency", param.Latency),
			zap.String("client_ip", param.ClientIP),
			zap.String("user_agent", param.Request.UserAgent()),
		)
		return ""
	})
}