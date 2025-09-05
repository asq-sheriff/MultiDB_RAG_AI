package main

import (
	"time"

	"github.com/google/uuid"
	"github.com/gocql/gocql"
)

// EmotionLabel represents emotion categories for healthcare context
type EmotionLabel string

const (
	EmotionNeutral  EmotionLabel = "neutral"
	EmotionCalm     EmotionLabel = "calm"
	EmotionSad      EmotionLabel = "sad"
	EmotionAnxious  EmotionLabel = "anxious"
	EmotionHappy    EmotionLabel = "happy"
	EmotionAngry    EmotionLabel = "angry"
	EmotionFear     EmotionLabel = "fear"
	EmotionDisgust  EmotionLabel = "disgust"
	EmotionSurprise EmotionLabel = "surprise"
)

// ActorType represents message actors
type ActorType string

const (
	ActorUser      ActorType = "user"
	ActorAssistant ActorType = "assistant"
	ActorSystem    ActorType = "system"
)

// MessageRole represents message roles in conversation
type MessageRole string

const (
	RoleUser      MessageRole = "user"
	RoleAssistant MessageRole = "assistant"
	RoleSystem    MessageRole = "system"
)

// SessionStats represents session statistics
type SessionStats struct {
	SessionID     uuid.UUID `json:"session_id"`
	MessageCount  int       `json:"message_count"`
	Duration      int       `json:"duration_seconds"`
	LastActivity  time.Time `json:"last_activity"`
}

// AnalyticRecord represents analytics data
type AnalyticRecord struct {
	ID        uuid.UUID `json:"id"`
	SessionID uuid.UUID `json:"session_id"`
	Event     string    `json:"event"`
	Data      map[string]interface{} `json:"data"`
	CreatedAt time.Time `json:"created_at"`
}

// ========================================
// PostgreSQL Models (Structured Data)
// ========================================

// Session represents a chat session in PostgreSQL
type Session struct {
	SessionID uuid.UUID  `db:"session_id" json:"session_id"`
	UserID    uuid.UUID  `db:"user_id" json:"user_id"`
	Channel   string     `db:"channel" json:"channel"`
	StartedAt time.Time  `db:"started_at" json:"started_at"`
	EndedAt   *time.Time `db:"ended_at" json:"ended_at,omitempty"`
	CreatedAt time.Time  `db:"created_at" json:"created_at"`
	UpdatedAt time.Time  `db:"updated_at" json:"updated_at"`
}

// Message represents a chat message in PostgreSQL
type Message struct {
	MessageID   uuid.UUID   `db:"message_id" json:"message_id"`
	SessionID   uuid.UUID   `db:"session_id" json:"session_id"`
	UserID      uuid.UUID   `db:"user_id" json:"user_id"`
	Role        MessageRole `db:"role" json:"role"`
	Content     string      `db:"content" json:"content"`
	ContentHash []byte      `db:"content_hash" json:"content_hash,omitempty"`
	CreatedAt   time.Time   `db:"created_at" json:"created_at"`
	UpdatedAt   time.Time   `db:"updated_at" json:"updated_at"`
	PIIPresent  bool        `db:"pii_present" json:"pii_present"`
}

// MessageEmotion represents emotion analysis for messages in PostgreSQL
type MessageEmotion struct {
	MessageID        uuid.UUID               `db:"message_id" json:"message_id"`
	Valence          float64                 `db:"valence" json:"valence"`           // -1 to 1
	Arousal          float64                 `db:"arousal" json:"arousal"`           // -1 to 1
	Label            EmotionLabel            `db:"label" json:"label"`
	Confidence       float64                 `db:"confidence" json:"confidence"`
	ProsodyFeatures  map[string]interface{}  `db:"prosody_features" json:"prosody_features,omitempty"`
	InferredAt       time.Time               `db:"inferred_at" json:"inferred_at"`
}

// ========================================
// ScyllaDB Models (High-Performance Storage)
// ========================================

// ConversationMessage represents a conversation message in ScyllaDB
type ConversationMessage struct {
	SessionID        gocql.UUID        `cql:"session_id"`
	Timestamp        time.Time         `cql:"timestamp"`
	MessageID        gocql.UUID        `cql:"message_id"`
	Actor            string            `cql:"actor"`
	Message          string            `cql:"message"`
	Confidence       *float64          `cql:"confidence"`
	Cached           *bool             `cql:"cached"`
	ResponseTimeMs   *int              `cql:"response_time_ms"`
	RouteUsed        *string           `cql:"route_used"`
	GenerationUsed   *bool             `cql:"generation_used"`
	Metadata         map[string]string `cql:"metadata"`
}

// ConversationSummary represents aggregated conversation analytics in ScyllaDB
type ConversationSummary struct {
	SessionID      gocql.UUID `cql:"session_id"`
	Date           time.Time  `cql:"date"`
	MessageCount   int        `cql:"message_count"`
	UserMessages   int        `cql:"user_messages"`
	BotMessages    int        `cql:"bot_messages"`
	AvgResponseMs  *float64   `cql:"avg_response_ms"`
	CachedResponses int       `cql:"cached_responses"`
	TotalDurationMs *int64    `cql:"total_duration_ms"`
}

// UserFeedback represents user feedback in ScyllaDB
type UserFeedback struct {
	FeedbackID  gocql.UUID `cql:"feedback_id"`
	SessionID   gocql.UUID `cql:"session_id"`
	MessageID   gocql.UUID `cql:"message_id"`
	UserID      gocql.UUID `cql:"user_id"`
	Rating      int        `cql:"rating"`      // 1-5 scale
	Feedback    *string    `cql:"feedback"`    // Optional text feedback
	Category    *string    `cql:"category"`    // helpful, unhelpful, inappropriate, etc.
	CreatedAt   time.Time  `cql:"created_at"`
}

// ========================================
// Redis Models (Caching & Session Data)
// ========================================

// SessionCache represents cached session data in Redis
type SessionCache struct {
	SessionID         string                 `json:"session_id"`
	UserID            string                 `json:"user_id"`
	Channel           string                 `json:"channel"`
	LastActivity      time.Time              `json:"last_activity"`
	MessageCount      int                    `json:"message_count"`
	RateLimitCount    int                    `json:"rate_limit_count"`
	RateLimitReset    time.Time              `json:"rate_limit_reset"`
	Context           map[string]interface{} `json:"context,omitempty"`
	EmotionState      *EmotionState          `json:"emotion_state,omitempty"`
}

// EmotionState represents user's current emotional state
type EmotionState struct {
	CurrentEmotion    EmotionLabel `json:"current_emotion"`
	Valence           float64      `json:"valence"`
	Arousal           float64      `json:"arousal"`
	Confidence        float64      `json:"confidence"`
	LastUpdated       time.Time    `json:"last_updated"`
	RequiresAttention bool         `json:"requires_attention"` // For crisis intervention
}

// ChatHistoryCache represents cached conversation data
type ChatHistoryCache struct {
	SessionID string                 `json:"session_id"`
	Messages  []CachedMessage        `json:"messages"`
	TTL       time.Duration          `json:"ttl"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// CachedMessage represents a simplified message for caching
type CachedMessage struct {
	MessageID     string    `json:"message_id"`
	Actor         ActorType `json:"actor"`
	Content       string    `json:"content"`
	Timestamp     time.Time `json:"timestamp"`
	Confidence    *float64  `json:"confidence,omitempty"`
	EmotionLabel  *string   `json:"emotion_label,omitempty"`
}

// AnalyticsCounter represents real-time analytics counters
type AnalyticsCounter struct {
	Metric    string    `json:"metric"`
	Value     int64     `json:"value"`
	Timestamp time.Time `json:"timestamp"`
	Tags      map[string]string `json:"tags,omitempty"`
}

// ========================================
// MongoDB Models (Knowledge Base & Vector Search)
// ========================================

// KnowledgeDocument represents documents in MongoDB knowledge base
type KnowledgeDocument struct {
	ID                string                 `bson:"_id,omitempty" json:"id,omitempty"`
	Title             string                 `bson:"title" json:"title"`
	Content           string                 `bson:"content" json:"content"`
	DocumentType      string                 `bson:"document_type" json:"document_type"`
	CareContext       []string               `bson:"care_context" json:"care_context"`
	Keywords          []string               `bson:"keywords" json:"keywords"`
	EmbeddingVector   []float64              `bson:"embedding_vector,omitempty" json:"embedding_vector,omitempty"`
	Metadata          map[string]interface{} `bson:"metadata,omitempty" json:"metadata,omitempty"`
	CreatedAt         time.Time              `bson:"created_at" json:"created_at"`
	UpdatedAt         time.Time              `bson:"updated_at" json:"updated_at"`
	Version           int                    `bson:"version" json:"version"`
}

// ========================================
// HTTP Request/Response Models
// ========================================

// SendMessageRequest represents incoming chat message request
type SendMessageRequest struct {
	SessionID      string                 `json:"session_id" binding:"required"`
	UserID         string                 `json:"user_id" binding:"required"`
	Message        string                 `json:"message" binding:"required"`
	Channel        string                 `json:"channel"`
	UseRAG         bool                   `json:"use_rag"`
	SafetyAnalysis bool                   `json:"safety_analysis"`
	Context        map[string]interface{} `json:"context,omitempty"`
}

// SendMessageResponse represents chat message response
type SendMessageResponse struct {
	MessageID      string                 `json:"message_id"`
	SessionID      string                 `json:"session_id"`
	Response       string                 `json:"response"`
	Confidence     float64                `json:"confidence"`
	EmotionLabel   *string                `json:"emotion_label,omitempty"`
	EmotionState   *EmotionState          `json:"emotion_state,omitempty"`
	SafetyAnalysis *SafetyAnalysisResult  `json:"safety_analysis,omitempty"`
	RouteUsed      string                 `json:"route_used"`
	Cached         bool                   `json:"cached"`
	ResponseTimeMs int                    `json:"response_time_ms"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// GetHistoryRequest represents chat history request
type GetHistoryRequest struct {
	SessionID string     `json:"session_id" form:"session_id" binding:"required"`
	Limit     int        `json:"limit" form:"limit"`
	StartTime *time.Time `json:"start_time,omitempty" form:"start_time,omitempty"`
	EndTime   *time.Time `json:"end_time,omitempty" form:"end_time,omitempty"`
}

// GetHistoryResponse represents chat history response
type GetHistoryResponse struct {
	SessionID string            `json:"session_id"`
	Messages  []HistoryMessage  `json:"messages"`
	Total     int               `json:"total"`
	HasMore   bool              `json:"has_more"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// HistoryMessage represents a message in history response
type HistoryMessage struct {
	MessageID       string                 `json:"message_id"`
	Actor           ActorType              `json:"actor"`
	Content         string                 `json:"content"`
	Timestamp       time.Time              `json:"timestamp"`
	Confidence      *float64               `json:"confidence,omitempty"`
	EmotionLabel    *EmotionLabel          `json:"emotion_label,omitempty"`
	EmotionValence  *float64               `json:"emotion_valence,omitempty"`
	EmotionArousal  *float64               `json:"emotion_arousal,omitempty"`
	RouteUsed       *string                `json:"route_used,omitempty"`
	ResponseTimeMs  *int                   `json:"response_time_ms,omitempty"`
	GenerationUsed  *bool                  `json:"generation_used,omitempty"`
	PIIPresent      bool                   `json:"pii_present"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

// SubmitFeedbackRequest represents feedback submission
type SubmitFeedbackRequest struct {
	SessionID string  `json:"session_id" binding:"required"`
	MessageID string  `json:"message_id" binding:"required"`
	UserID    string  `json:"user_id" binding:"required"`
	Rating    int     `json:"rating" binding:"required,min=1,max=5"`
	Feedback  *string `json:"feedback,omitempty"`
	Category  *string `json:"category,omitempty"`
}

// SubmitFeedbackResponse represents feedback submission response
type SubmitFeedbackResponse struct {
	FeedbackID string `json:"feedback_id"`
	Success    bool   `json:"success"`
	Message    string `json:"message"`
}

// ========================================
// Service Integration Models
// ========================================

// SafetyAnalysisResult represents safety analysis from content safety service
type SafetyAnalysisResult struct {
	Safe           bool     `json:"safe"`
	RiskLevel      string   `json:"risk_level"`    // low, medium, high, crisis
	Categories     []string `json:"categories"`    // depression, anxiety, suicidal, etc.
	Confidence     float64  `json:"confidence"`
	RequiresHuman  bool     `json:"requires_human"`
	CrisisLevel    bool     `json:"crisis_level"`
	Interventions  []string `json:"interventions,omitempty"`
}

// EmbeddingRequest represents request to embedding service
type EmbeddingRequest struct {
	Text  string `json:"text"`
	Model string `json:"model,omitempty"`
}

// EmbeddingResponse represents response from embedding service
type EmbeddingResponse struct {
	Embedding []float64 `json:"embedding"`
	Model     string    `json:"model"`
	Dimension int       `json:"dimension"`
}

// GenerationRequest represents request to generation service
type GenerationRequest struct {
	Message        string                 `json:"message"`
	Context        []HistoryMessage       `json:"context,omitempty"`
	SystemPrompt   string                 `json:"system_prompt,omitempty"`
	SafetyContext  *SafetyAnalysisResult  `json:"safety_context,omitempty"`
	EmotionContext *EmotionState          `json:"emotion_context,omitempty"`
	Parameters     map[string]interface{} `json:"parameters,omitempty"`
}

// GenerationResponse represents response from generation service
type GenerationResponse struct {
	Response   string  `json:"response"`
	Confidence float64 `json:"confidence"`
	Model      string  `json:"model"`
	TokensUsed int     `json:"tokens_used,omitempty"`
	Cached     bool    `json:"cached"`
}

// ========================================
// Analytics and Monitoring Models
// ========================================

// ConversationAnalytics represents conversation analytics
type ConversationAnalytics struct {
	SessionID          string                 `json:"session_id"`
	TotalMessages      int                    `json:"total_messages"`
	UserMessages       int                    `json:"user_messages"`
	AssistantMessages  int                    `json:"assistant_messages"`
	AverageResponseMs  float64                `json:"average_response_ms"`
	CachedResponses    int                    `json:"cached_responses"`
	EmotionDistribution map[EmotionLabel]int  `json:"emotion_distribution"`
	SafetyFlags        []string               `json:"safety_flags,omitempty"`
	DominantEmotion    *EmotionLabel          `json:"dominant_emotion,omitempty"`
	SessionDurationMs  int64                  `json:"session_duration_ms"`
	Metadata           map[string]interface{} `json:"metadata,omitempty"`
}

// ServiceStats represents overall service statistics
type ServiceStats struct {
	TotalSessions       int64         `json:"total_sessions"`
	ActiveSessions      int64         `json:"active_sessions"`
	TotalMessages       int64         `json:"total_messages"`
	MessagesPerSecond   float64       `json:"messages_per_second"`
	AverageResponseMs   float64       `json:"average_response_ms"`
	CacheHitRate        float64       `json:"cache_hit_rate"`
	DatabaseHealth      DatabaseHealth `json:"database_health"`
	Uptime              time.Duration `json:"uptime"`
	LastUpdated         time.Time     `json:"last_updated"`
}

// DatabaseHealth represents health status of databases
type DatabaseHealth struct {
	PostgreSQL bool `json:"postgresql"`
	ScyllaDB   bool `json:"scylladb"`
	MongoDB    bool `json:"mongodb"`
	Redis      bool `json:"redis"`
}

// HealthCheckResponse represents health check response
type HealthCheckResponse struct {
	Status      string                 `json:"status"`
	Timestamp   time.Time              `json:"timestamp"`
	Service     string                 `json:"service"`
	Version     string                 `json:"version"`
	Databases   DatabaseHealth         `json:"databases"`
	Uptime      time.Duration          `json:"uptime"`
	Details     map[string]interface{} `json:"details,omitempty"`
}

// ========================================
// Utility Functions for Models
// ========================================

// NewSession creates a new session with default values
func NewSession(userID uuid.UUID, channel string) *Session {
	now := time.Now()
	return &Session{
		SessionID: uuid.New(),
		UserID:    userID,
		Channel:   channel,
		StartedAt: now,
		CreatedAt: now,
		UpdatedAt: now,
	}
}

// NewMessage creates a new message with default values
func NewMessage(sessionID, userID uuid.UUID, role MessageRole, content string) *Message {
	now := time.Now()
	return &Message{
		MessageID: uuid.New(),
		SessionID: sessionID,
		UserID:    userID,
		Role:      role,
		Content:    content,
		CreatedAt:  now,
		UpdatedAt:  now,
		PIIPresent: false,
	}
}

// IsActive checks if session is currently active
func (s *Session) IsActive() bool {
	return s.EndedAt == nil
}

// EndSession marks the session as ended
func (s *Session) EndSession() {
	now := time.Now()
	s.EndedAt = &now
	s.UpdatedAt = now
}

// RequiresIntervention checks if emotion state requires human intervention
func (es *EmotionState) RequiresIntervention() bool {
	return es.RequiresAttention || 
		   (es.CurrentEmotion == EmotionSad && es.Arousal < -0.7) ||
		   (es.CurrentEmotion == EmotionAnxious && es.Arousal > 0.8)
}

// IsValidRating checks if feedback rating is valid
func (req *SubmitFeedbackRequest) IsValidRating() bool {
	return req.Rating >= 1 && req.Rating <= 5
}