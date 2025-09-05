package main

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"bytes"
	"time"

	"github.com/gocql/gocql"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// ChatHistoryService provides chat history management functionality
type ChatHistoryService struct {
	db     *DatabaseManager
	logger *zap.Logger
	config ServiceConfig
	
	// Service URLs for external integrations
	embeddingServiceURL string
	generationServiceURL string
	safetyServiceURL     string
	
	// Metrics
	startTime time.Time
}

// ServiceConfig represents service configuration
type ServiceConfig struct {
	MaxMessageLength      int           `envconfig:"MAX_MESSAGE_LENGTH" default:"10000"`
	MaxHistoryLimit       int           `envconfig:"MAX_HISTORY_LIMIT" default:"100"`
	DefaultHistoryLimit   int           `envconfig:"DEFAULT_HISTORY_LIMIT" default:"50"`
	CacheSessionTTL       time.Duration `envconfig:"CACHE_SESSION_TTL" default:"24h"`
	RateLimitPerHour      int           `envconfig:"RATE_LIMIT_PER_HOUR" default:"1000"`
	EnableSafetyAnalysis  bool          `envconfig:"ENABLE_SAFETY_ANALYSIS" default:"true"`
	EnableEmotionAnalysis bool          `envconfig:"ENABLE_EMOTION_ANALYSIS" default:"true"`
	EnableRAG             bool          `envconfig:"ENABLE_RAG" default:"true"`
}

// NewChatHistoryService creates a new chat history service
func NewChatHistoryService(db *DatabaseManager, logger *zap.Logger, config ServiceConfig, 
	embeddingURL, generationURL, safetyURL string) *ChatHistoryService {
	
	return &ChatHistoryService{
		db:                   db,
		logger:               logger,
		config:               config,
		embeddingServiceURL:  embeddingURL,
		generationServiceURL: generationURL,
		safetyServiceURL:     safetyURL,
		startTime:           time.Now(),
	}
}

// ========================================
// Core Chat Message Processing
// ========================================

// ProcessMessage handles incoming chat messages with full processing pipeline
func (chs *ChatHistoryService) ProcessMessage(ctx context.Context, req *SendMessageRequest) (*SendMessageResponse, error) {
	start := time.Now()
	
	// Validate request
	if err := chs.validateMessageRequest(req); err != nil {
		return nil, fmt.Errorf("invalid request: %w", err)
	}
	
	// Parse UUIDs
	sessionUUID, err := uuid.Parse(req.SessionID)
	if err != nil {
		return nil, fmt.Errorf("invalid session ID: %w", err)
	}
	
	userUUID, err := uuid.Parse(req.UserID)
	if err != nil {
		return nil, fmt.Errorf("invalid user ID: %w", err)
	}
	
	// Check or create session
	session, err := chs.ensureSession(ctx, sessionUUID, userUUID, req.Channel)
	if err != nil {
		return nil, fmt.Errorf("failed to ensure session: %w", err)
	}
	
	// Check rate limiting
	if err := chs.checkRateLimit(ctx, req.SessionID, req.UserID); err != nil {
		return nil, fmt.Errorf("rate limit exceeded: %w", err)
	}
	
	// Create user message
	userMessage := NewMessage(sessionUUID, userUUID, RoleUser, req.Message)
	userMessage.ContentHash = chs.hashContent(req.Message)
	
	// Store user message in PostgreSQL
	if err := chs.db.CreateMessage(ctx, userMessage); err != nil {
		return nil, fmt.Errorf("failed to store user message: %w", err)
	}
	
	// Store user message in ScyllaDB for conversation history
	scyllaSessionUUID, err := gocql.ParseUUID(req.SessionID)
	if err != nil {
		chs.logger.Error("Failed to parse session UUID", zap.Error(err))
		return nil, fmt.Errorf("invalid session UUID: %w", err)
	}
	scyllaMessageUUID, err := gocql.ParseUUID(userMessage.MessageID.String())
	if err != nil {
		chs.logger.Error("Failed to parse message UUID", zap.Error(err))
		return nil, fmt.Errorf("invalid message UUID: %w", err)
	}
	scyllaUserMsg := &ConversationMessage{
		SessionID:        scyllaSessionUUID,
		Timestamp:        userMessage.CreatedAt,
		MessageID:        scyllaMessageUUID,
		Actor:            string(ActorUser),
		Message:          req.Message,
		Cached:           &[]bool{false}[0],
		ResponseTimeMs:   &[]int{0}[0],
		Metadata:         make(map[string]string),
	}
	
	if err := chs.db.StoreConversationMessage(ctx, scyllaUserMsg); err != nil {
		chs.logger.Error("Failed to store user message in ScyllaDB", zap.Error(err))
		// Don't fail the request, continue processing
	}
	
	// Perform safety analysis if enabled
	var safetyResult *SafetyAnalysisResult
	if chs.config.EnableSafetyAnalysis && req.SafetyAnalysis {
		safetyResult, err = chs.performSafetyAnalysis(ctx, req.Message)
		if err != nil {
			chs.logger.Error("Safety analysis failed", zap.Error(err))
			// Continue processing with default safe response if analysis fails
		}
	}
	
	// Perform emotion analysis if enabled
	var emotionState *EmotionState
	if chs.config.EnableEmotionAnalysis {
		emotionState, err = chs.analyzeEmotion(ctx, req.Message, userMessage.MessageID)
		if err != nil {
			chs.logger.Error("Emotion analysis failed", zap.Error(err))
			// Continue processing without emotion data
		}
	}
	
	// Generate response
	assistantResponse, confidence, routeUsed, cached, err := chs.generateResponse(ctx, req, session, safetyResult, emotionState)
	if err != nil {
		return nil, fmt.Errorf("failed to generate response: %w", err)
	}
	
	// Create assistant message
	assistantMessage := NewMessage(sessionUUID, userUUID, RoleAssistant, assistantResponse)
	assistantMessage.ContentHash = chs.hashContent(assistantResponse)
	
	// Store assistant message in PostgreSQL
	if err := chs.db.CreateMessage(ctx, assistantMessage); err != nil {
		return nil, fmt.Errorf("failed to store assistant message: %w", err)
	}
	
	// Calculate response time
	responseTime := int(time.Since(start).Milliseconds())
	
	// Store assistant message in ScyllaDB
	scyllaAssistantSessionUUID, err := gocql.ParseUUID(req.SessionID)
	if err != nil {
		chs.logger.Error("Failed to parse session UUID for assistant message", zap.Error(err))
		return nil, fmt.Errorf("invalid session UUID: %w", err)
	}
	scyllaAssistantMessageUUID, err := gocql.ParseUUID(assistantMessage.MessageID.String())
	if err != nil {
		chs.logger.Error("Failed to parse assistant message UUID", zap.Error(err))
		return nil, fmt.Errorf("invalid assistant message UUID: %w", err)
	}
	scyllaAssistantMsg := &ConversationMessage{
		SessionID:        scyllaAssistantSessionUUID,
		Timestamp:        assistantMessage.CreatedAt,
		MessageID:        scyllaAssistantMessageUUID,
		Actor:            string(ActorAssistant),
		Message:          assistantResponse,
		Confidence:       &confidence,
		Cached:           &cached,
		ResponseTimeMs:   &responseTime,
		RouteUsed:        &routeUsed,
		GenerationUsed:   &[]bool{!cached}[0],
		Metadata:         make(map[string]string),
	}
	
	if err := chs.db.StoreConversationMessage(ctx, scyllaAssistantMsg); err != nil {
		chs.logger.Error("Failed to store assistant message in ScyllaDB", zap.Error(err))
	}
	
	// Update session cache
	if err := chs.updateSessionCache(ctx, req.SessionID, req.UserID, emotionState); err != nil {
		chs.logger.Error("Failed to update session cache", zap.Error(err))
	}
	
	// Update analytics
	chs.updateAnalytics(ctx, routeUsed, cached, responseTime, safetyResult != nil)
	
	// Build response
	response := &SendMessageResponse{
		MessageID:      assistantMessage.MessageID.String(),
		SessionID:      req.SessionID,
		Response:       assistantResponse,
		Confidence:     confidence,
		SafetyAnalysis: safetyResult,
		EmotionState:   emotionState,
		RouteUsed:      routeUsed,
		Cached:         cached,
		ResponseTimeMs: responseTime,
		Metadata:       make(map[string]interface{}),
	}
	
	if emotionState != nil {
		label := string(emotionState.CurrentEmotion)
		response.EmotionLabel = &label
	}
	
	chs.logger.Info("Message processed successfully",
		zap.String("session_id", req.SessionID),
		zap.String("user_id", req.UserID),
		zap.Int("response_time_ms", responseTime),
		zap.Bool("cached", cached),
		zap.String("route_used", routeUsed))
	
	return response, nil
}

// ========================================
// Conversation History Retrieval
// ========================================

// GetConversationHistory retrieves conversation history for a session
func (chs *ChatHistoryService) GetConversationHistory(ctx context.Context, req *GetHistoryRequest) (*GetHistoryResponse, error) {
	// Validate request
	if req.SessionID == "" {
		return nil, fmt.Errorf("session ID is required")
	}
	
	// Set default limit
	if req.Limit <= 0 || req.Limit > chs.config.MaxHistoryLimit {
		req.Limit = chs.config.DefaultHistoryLimit
	}
	
	sessionUUID, err := gocql.ParseUUID(req.SessionID)
	if err != nil {
		return nil, fmt.Errorf("invalid session ID: %w", err)
	}
	
	// Get conversation history from ScyllaDB (high-performance access)
	messages, err := chs.db.GetConversationHistory(ctx, sessionUUID, req.Limit, req.StartTime)
	if err != nil {
		return nil, fmt.Errorf("failed to get conversation history: %w", err)
	}
	
	// Convert to response format
	historyMessages := make([]HistoryMessage, len(messages))
	for i, msg := range messages {
		histMsg := HistoryMessage{
			MessageID:      msg.MessageID.String(),
			Actor:          ActorType(msg.Actor),
			Content:        msg.Message,
			Timestamp:      msg.Timestamp,
			Confidence:     msg.Confidence,
			RouteUsed:      msg.RouteUsed,
			ResponseTimeMs: msg.ResponseTimeMs,
			GenerationUsed: msg.GenerationUsed,
			Metadata:       make(map[string]interface{}),
		}
		
		// Convert metadata
		if msg.Metadata != nil {
			for k, v := range msg.Metadata {
				histMsg.Metadata[k] = v
			}
		}
		
		historyMessages[i] = histMsg
	}
	
	// Get emotion data for messages if available
	if chs.config.EnableEmotionAnalysis {
		if err := chs.enrichWithEmotionData(ctx, historyMessages); err != nil {
			chs.logger.Error("Failed to enrich with emotion data", zap.Error(err))
			// Don't fail the request, continue without emotion data
		}
	}
	
	response := &GetHistoryResponse{
		SessionID: req.SessionID,
		Messages:  historyMessages,
		Total:     len(historyMessages),
		HasMore:   len(historyMessages) == req.Limit,
		Metadata:  make(map[string]interface{}),
	}
	
	chs.logger.Info("Conversation history retrieved",
		zap.String("session_id", req.SessionID),
		zap.Int("message_count", len(historyMessages)))
	
	return response, nil
}

// ========================================
// Feedback Submission
// ========================================

// SubmitFeedback handles feedback submission for chat responses
func (chs *ChatHistoryService) SubmitFeedback(ctx context.Context, req *SubmitFeedbackRequest) (*SubmitFeedbackResponse, error) {
	// Validate request
	if !req.IsValidRating() {
		return nil, fmt.Errorf("invalid rating: must be between 1 and 5")
	}
	
	sessionUUID, err := gocql.ParseUUID(req.SessionID)
	if err != nil {
		return nil, fmt.Errorf("invalid session ID: %w", err)
	}
	
	messageUUID, err := gocql.ParseUUID(req.MessageID)
	if err != nil {
		return nil, fmt.Errorf("invalid message ID: %w", err)
	}
	
	userUUID, err := gocql.ParseUUID(req.UserID)
	if err != nil {
		return nil, fmt.Errorf("invalid user ID: %w", err)
	}
	
	// Create feedback record
	feedback := &UserFeedback{
		FeedbackID: gocql.TimeUUID(),
		SessionID:  sessionUUID,
		MessageID:  messageUUID,
		UserID:     userUUID,
		Rating:     req.Rating,
		Feedback:   req.Feedback,
		Category:   req.Category,
		CreatedAt:  time.Now(),
	}
	
	// Store feedback in ScyllaDB
	if err := chs.db.StoreFeedback(ctx, feedback); err != nil {
		return nil, fmt.Errorf("failed to store feedback: %w", err)
	}
	
	// Update analytics
	tags := map[string]string{
		"rating":   fmt.Sprintf("%d", req.Rating),
		"category": "",
	}
	if req.Category != nil {
		tags["category"] = *req.Category
	}
	
	if err := chs.db.IncrementAnalyticsCounter(ctx, "feedback_submitted", tags); err != nil {
		chs.logger.Error("Failed to update feedback analytics", zap.Error(err))
	}
	
	response := &SubmitFeedbackResponse{
		FeedbackID: feedback.FeedbackID.String(),
		Success:    true,
		Message:    "Feedback submitted successfully",
	}
	
	chs.logger.Info("Feedback submitted",
		zap.String("feedback_id", feedback.FeedbackID.String()),
		zap.String("session_id", req.SessionID),
		zap.Int("rating", req.Rating))
	
	return response, nil
}

// ========================================
// Private Helper Methods
// ========================================

// validateMessageRequest validates incoming message request
func (chs *ChatHistoryService) validateMessageRequest(req *SendMessageRequest) error {
	if req.SessionID == "" {
		return fmt.Errorf("session ID is required")
	}
	
	if req.UserID == "" {
		return fmt.Errorf("user ID is required")
	}
	
	if req.Message == "" {
		return fmt.Errorf("message is required")
	}
	
	if len(req.Message) > chs.config.MaxMessageLength {
		return fmt.Errorf("message too long: maximum %d characters", chs.config.MaxMessageLength)
	}
	
	return nil
}

// ensureSession creates or retrieves an existing session
func (chs *ChatHistoryService) ensureSession(ctx context.Context, sessionID, userID uuid.UUID, channel string) (*Session, error) {
	// Try to get existing session
	session, err := chs.db.GetSession(ctx, sessionID)
	if err == nil {
		return session, nil
	}
	
	// Session doesn't exist, create new one
	if channel == "" {
		channel = "web" // Default channel
	}
	
	newSession := NewSession(userID, channel)
	newSession.SessionID = sessionID // Use provided session ID
	
	if err := chs.db.CreateSession(ctx, newSession); err != nil {
		return nil, fmt.Errorf("failed to create new session: %w", err)
	}
	
	chs.logger.Info("New session created",
		zap.String("session_id", sessionID.String()),
		zap.String("user_id", userID.String()),
		zap.String("channel", channel))
	
	return newSession, nil
}

// checkRateLimit checks if user has exceeded rate limit
func (chs *ChatHistoryService) checkRateLimit(ctx context.Context, sessionID, userID string) error {
	// Get cached session to check rate limiting
	cachedSession, err := chs.db.GetCachedSession(ctx, sessionID)
	if err != nil {
		// If cache miss, allow request (rate limit will be established)
		return nil
	}
	
	if cachedSession == nil {
		// No cached session, allow request
		return nil
	}
	
	// Check if rate limit reset time has passed
	if time.Now().After(cachedSession.RateLimitReset) {
		// Reset rate limit counter
		cachedSession.RateLimitCount = 0
		cachedSession.RateLimitReset = time.Now().Add(time.Hour)
	}
	
	// Check rate limit
	if cachedSession.RateLimitCount >= chs.config.RateLimitPerHour {
		return fmt.Errorf("rate limit exceeded: %d requests per hour", chs.config.RateLimitPerHour)
	}
	
	return nil
}

// hashContent creates a hash of message content for deduplication
func (chs *ChatHistoryService) hashContent(content string) []byte {
	hash := sha256.Sum256([]byte(content))
	return hash[:]
}

// performSafetyAnalysis calls the safety analysis service
func (chs *ChatHistoryService) performSafetyAnalysis(ctx context.Context, message string) (*SafetyAnalysisResult, error) {
	if chs.safetyServiceURL == "" {
		return nil, fmt.Errorf("safety service URL not configured")
	}
	
	// Prepare request
	reqData := map[string]interface{}{
		"text": message,
		"context": "chat_message",
	}
	
	jsonData, err := json.Marshal(reqData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal safety request: %w", err)
	}
	
	// Make HTTP request
	resp, err := http.Post(
		chs.safetyServiceURL+"/analyze/safety",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to call safety service: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("safety service returned status: %d", resp.StatusCode)
	}
	
	var result SafetyAnalysisResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode safety response: %w", err)
	}
	
	return &result, nil
}

// analyzeEmotion performs emotion analysis on the message
func (chs *ChatHistoryService) analyzeEmotion(ctx context.Context, message string, messageID uuid.UUID) (*EmotionState, error) {
	// This would call an emotion analysis service
	// For now, implement basic keyword-based emotion detection
	
	emotionState := &EmotionState{
		CurrentEmotion: EmotionNeutral,
		Valence:        0.0,
		Arousal:        0.0,
		Confidence:     0.5,
		LastUpdated:    time.Now(),
		RequiresAttention: false,
	}
	
	// Simple keyword-based analysis (would be replaced with ML service call)
	content := message
	
	// Check for emotional keywords
	switch {
	case contains(content, []string{"sad", "depressed", "down", "unhappy"}):
		emotionState.CurrentEmotion = EmotionSad
		emotionState.Valence = -0.6
		emotionState.Arousal = -0.3
		emotionState.Confidence = 0.7
	case contains(content, []string{"anxious", "worried", "nervous", "stressed"}):
		emotionState.CurrentEmotion = EmotionAnxious
		emotionState.Valence = -0.4
		emotionState.Arousal = 0.6
		emotionState.Confidence = 0.7
	case contains(content, []string{"happy", "good", "great", "wonderful"}):
		emotionState.CurrentEmotion = EmotionHappy
		emotionState.Valence = 0.7
		emotionState.Arousal = 0.4
		emotionState.Confidence = 0.6
	case contains(content, []string{"angry", "mad", "furious", "irritated"}):
		emotionState.CurrentEmotion = EmotionAngry
		emotionState.Valence = -0.7
		emotionState.Arousal = 0.8
		emotionState.Confidence = 0.7
	}
	
	// Check if requires attention (crisis keywords)
	crisisKeywords := []string{"suicide", "kill myself", "end it all", "can't go on"}
	if contains(content, crisisKeywords) {
		emotionState.RequiresAttention = true
		emotionState.Confidence = 0.9
	}
	
	// Store emotion analysis in PostgreSQL
	emotion := &MessageEmotion{
		MessageID:       messageID,
		Valence:         emotionState.Valence,
		Arousal:         emotionState.Arousal,
		Label:           emotionState.CurrentEmotion,
		Confidence:      emotionState.Confidence,
		ProsodyFeatures: make(map[string]interface{}),
		InferredAt:      time.Now(),
	}
	
	if err := chs.db.StoreMessageEmotion(ctx, emotion); err != nil {
		chs.logger.Error("Failed to store emotion analysis", zap.Error(err))
		// Don't fail the request
	}
	
	return emotionState, nil
}

// generateResponse generates a response using various strategies
func (chs *ChatHistoryService) generateResponse(ctx context.Context, req *SendMessageRequest, 
	session *Session, safety *SafetyAnalysisResult, emotion *EmotionState) (string, float64, string, bool, error) {
	
	// Check for crisis situation
	if safety != nil && safety.CrisisLevel {
		return chs.getCrisisResponse(), 1.0, "crisis_template", false, nil
	}
	
	// Check for cached response first
	if cachedResponse, found := chs.getCachedResponse(ctx, req.Message); found {
		return cachedResponse, 0.9, "cache", true, nil
	}
	
	// Use RAG if enabled and requested
	if chs.config.EnableRAG && req.UseRAG {
		response, confidence, err := chs.generateRAGResponseWithSession(ctx, req.Message, req.SessionID, emotion)
		if err == nil {
			return response, confidence, "rag", false, nil
		}
		chs.logger.Error("RAG generation failed, falling back", zap.Error(err))
	}
	
	// Use generation service
	response, confidence, err := chs.generateLLMResponse(ctx, req.Message, safety, emotion)
	if err != nil {
		chs.logger.Error("LLM generation failed, using fallback", zap.Error(err))
		return chs.getFallbackResponse(emotion), 0.5, "fallback", false, nil
	}
	
	return response, confidence, "llm", false, nil
}

// Helper functions

func contains(text string, keywords []string) bool {
	for _, keyword := range keywords {
		if len(text) >= len(keyword) {
			for i := 0; i <= len(text)-len(keyword); i++ {
				if text[i:i+len(keyword)] == keyword {
					return true
				}
			}
		}
	}
	return false
}

func (chs *ChatHistoryService) getCrisisResponse() string {
	return "I understand you're going through a difficult time. Your safety and wellbeing are important. Please consider reaching out to a mental health professional or crisis helpline. In the US, you can call 988 for the Suicide & Crisis Lifeline."
}

func (chs *ChatHistoryService) getCachedResponse(ctx context.Context, message string) (string, bool) {
	// Create cache key based on message hash for consistent lookups
	hasher := sha256.New()
	hasher.Write([]byte(message))
	messageHash := fmt.Sprintf("%x", hasher.Sum(nil))
	
	// Try L1 cache first (Redis)
	cacheKey := fmt.Sprintf("response:%s", messageHash[:16]) // Use first 16 chars for key
	
	cached, err := chs.db.GetFromCache(ctx, cacheKey)
	if err == nil {
		chs.logger.Debug("L1 cache hit for response", zap.String("message_hash", messageHash[:8]))
		return cached, true
	}
	
	// L2 cache (MongoDB) lookup is disabled for interface compatibility
	// TODO: Add MongoDB cache methods to DatabaseInterface
	
	return "", false
}

func (chs *ChatHistoryService) generateRAGResponseWithSession(ctx context.Context, message string, sessionID string, emotion *EmotionState) (string, float64, error) {
	// Call Python RAG service via main API (port 8000)
	ragRequest := map[string]interface{}{
		"message":        message,
		"session_id":     sessionID,
		"enable_rag":     true,
		"route":          "auto",
		"top_k":          5,
		"response_style": "helpful",
		"include_sources": false, // Keep response clean
		"max_context_length": 2000,
		"temperature":    0.7,
		"debug_mode":     false,
	}
	
	// Add emotion context if available
	if emotion != nil {
		ragRequest["emotion_context"] = map[string]interface{}{
			"emotion":    string(emotion.CurrentEmotion),
			"valence":    emotion.Valence,
			"arousal":    emotion.Arousal,
			"confidence": emotion.Confidence,
		}
	}
	
	jsonData, err := json.Marshal(ragRequest)
	if err != nil {
		return "", 0, fmt.Errorf("failed to marshal RAG request: %w", err)
	}
	
	// Call Python chatbot service
	resp, err := http.Post(
		"http://localhost:8000/chat/message",
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return "", 0, fmt.Errorf("failed to call Python RAG service: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return "", 0, fmt.Errorf("Python RAG service returned status: %d", resp.StatusCode)
	}
	
	var ragResponse struct {
		Answer     string  `json:"answer"`
		Confidence float64 `json:"confidence"`
		RouteUsed  string  `json:"retrieval_route"`
	}
	
	if err := json.NewDecoder(resp.Body).Decode(&ragResponse); err != nil {
		return "", 0, fmt.Errorf("failed to decode RAG response: %w", err)
	}
	
	return ragResponse.Answer, ragResponse.Confidence, nil
}

func (chs *ChatHistoryService) generateLLMResponse(ctx context.Context, message string, safety *SafetyAnalysisResult, emotion *EmotionState) (string, float64, error) {
	// Use ai_services internal chat endpoint for full RAG pipeline
	aiServicesURL := "http://localhost:8000"
	
	// Prepare request for ai_services internal chat
	chatReq := map[string]interface{}{
		"message":    message,
		"session_id": ctx.Value("session_id"),
		"enable_rag": true,
		"route":      "auto",
		"top_k":      5,
	}
	
	jsonData, err := json.Marshal(chatReq)
	if err != nil {
		return "", 0, fmt.Errorf("failed to marshal chat request: %w", err)
	}
	
	// Make HTTP request to ai_services internal endpoint
	resp, err := http.Post(
		aiServicesURL+"/internal/chat",
		"application/json", 
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		return "", 0, fmt.Errorf("failed to call ai_services internal chat: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return "", 0, fmt.Errorf("ai_services internal chat returned status: %d", resp.StatusCode)
	}
	
	var chatResp struct {
		Response   string  `json:"response"`
		Confidence float64 `json:"confidence"`
		RagUsed    bool    `json:"rag_used"`
		Sources    []interface{} `json:"sources"`
	}
	
	if err := json.NewDecoder(resp.Body).Decode(&chatResp); err != nil {
		return "", 0, fmt.Errorf("failed to decode ai_services chat response: %w", err)
	}
	
	if chatResp.Response == "" {
		return "", 0, fmt.Errorf("empty response from ai_services")
	}
	
	return chatResp.Response, chatResp.Confidence, nil
}

func (chs *ChatHistoryService) getFallbackResponse(emotion *EmotionState) string {
	if emotion != nil {
		switch emotion.CurrentEmotion {
		case EmotionSad:
			return "I understand you're feeling down. It's okay to have difficult days. Is there anything specific I can help you with?"
		case EmotionAnxious:
			return "I can sense you might be feeling anxious. Take a deep breath. I'm here to help you through this."
		case EmotionHappy:
			return "I'm glad to hear you're feeling positive! How can I assist you today?"
		}
	}
	
	return "I'm here to help you. Could you please tell me more about what you need assistance with?"
}

func (chs *ChatHistoryService) updateSessionCache(ctx context.Context, sessionID, userID string, emotion *EmotionState) error {
	sessionCache := &SessionCache{
		SessionID:      sessionID,
		UserID:         userID,
		LastActivity:   time.Now(),
		MessageCount:   0, // Would be incremented
		RateLimitCount: 0, // Would be incremented
		RateLimitReset: time.Now().Add(time.Hour),
		EmotionState:   emotion,
	}
	
	return chs.db.CacheSession(ctx, sessionCache)
}

func (chs *ChatHistoryService) updateAnalytics(ctx context.Context, route string, cached bool, responseTimeMs int, safetyAnalyzed bool) {
	// Update various analytics counters
	tags := map[string]string{"route": route}
	
	chs.db.IncrementAnalyticsCounter(ctx, "messages_processed", tags)
	
	if cached {
		chs.db.IncrementAnalyticsCounter(ctx, "cache_hits", tags)
	} else {
		chs.db.IncrementAnalyticsCounter(ctx, "cache_misses", tags)
	}
	
	if safetyAnalyzed {
		chs.db.IncrementAnalyticsCounter(ctx, "safety_analyses", nil)
	}
	
	// Response time metrics could be stored as histograms
}

func (chs *ChatHistoryService) enrichWithEmotionData(ctx context.Context, messages []HistoryMessage) error {
	// This would query PostgreSQL for emotion data and enrich the messages
	// For brevity, not implementing the full query logic here
	return nil
}

// GetServiceStats returns service statistics
func (chs *ChatHistoryService) GetServiceStats(ctx context.Context) (*ServiceStats, error) {
	dbHealth := chs.db.HealthCheck(ctx)
	
	stats := &ServiceStats{
		TotalSessions:      0, // Would query from database
		ActiveSessions:     0, // Would query from cache
		TotalMessages:      0, // Would query from database
		MessagesPerSecond:  0.0, // Would calculate from metrics
		AverageResponseMs:  0.0, // Would calculate from metrics
		CacheHitRate:       0.0, // Would calculate from analytics
		DatabaseHealth:     dbHealth,
		Uptime:            time.Since(chs.startTime),
		LastUpdated:       time.Now(),
	}
	
	return stats, nil
}