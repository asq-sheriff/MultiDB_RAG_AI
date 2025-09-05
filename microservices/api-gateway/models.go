// Package main provides comprehensive models for the API Gateway service
package main

import (
	"time"

	"github.com/google/uuid"
)

// Configuration structures

// ServiceConfig holds all configuration for the API Gateway
type ServiceConfig struct {
	Port                     string
	Environment              string
	SecretKey               string
	AccessTokenExpireMinutes int
	DebugMode               bool
	
	// Database connections
	PostgresURL    string
	RedisURL       string
	MongoURL       string
	ScyllaHosts    []string
	
	// Microservice URLs
	SearchServiceURL                 string
	EmbeddingServiceURL              string
	GenerationServiceURL             string
	ContentSafetyServiceURL          string
	ChatHistoryServiceURL            string
	ConsentServiceURL                string
	AuditLoggingServiceURL           string
	AuthRBACServiceURL               string
	BillingServiceURL                string
	SubscriptionServiceURL           string
	BackgroundTasksURL               string
	EmergencyAccessServiceURL        string
	RelationshipManagementServiceURL string
	
	// Session & Rate Limiting
	SessionTTL                int
	RateLimitTTL             int
	MaxRequestsPerHour       int
	MaxRequestsPerMinute     int
	MaxRequestsPerSecond     int
	
	// Performance settings
	MaxConcurrentRequests    int
	RequestTimeout           time.Duration
	HealthCheckTimeout       time.Duration
	DatabaseTimeout          time.Duration
}

// Authentication models

// LoginRequest represents user login credentials
type LoginRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required,min=6"`
}

// RegisterRequest represents user registration data
type RegisterRequest struct {
	Email     string `json:"email" validate:"required,email"`
	Password  string `json:"password" validate:"required,min=8"`
	FirstName string `json:"first_name" validate:"required"`
	LastName  string `json:"last_name" validate:"required"`
	Phone     string `json:"phone,omitempty"`
}

// TokenResponse represents authentication token response
type TokenResponse struct {
	AccessToken  string    `json:"access_token"`
	TokenType    string    `json:"token_type"`
	ExpiresIn    int       `json:"expires_in"`
	ExpiresAt    time.Time `json:"expires_at"`
	RefreshToken string    `json:"refresh_token,omitempty"`
}

// User represents authenticated user information
type User struct {
	ID           uuid.UUID `json:"id"`
	Email        string    `json:"email"`
	FirstName    string    `json:"first_name"`
	LastName     string    `json:"last_name"`
	Phone        string    `json:"phone,omitempty"`
	IsActive     bool      `json:"is_active"`
	IsSuperuser  bool      `json:"is_superuser"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	LastLoginAt  *time.Time `json:"last_login_at,omitempty"`
}

// Chat models

// ChatMessageRequest represents incoming chat message
type ChatMessageRequest struct {
	Message     string                 `json:"message" validate:"required,min=1,max=2000"`
	SessionID   string                 `json:"session_id,omitempty"`
	UserID      string                 `json:"user_id,omitempty"`
	EnableRAG   bool                   `json:"enable_rag"`
	Route       string                 `json:"route,omitempty"`
	TopK        int                    `json:"top_k,omitempty"`
	Filters     map[string]interface{} `json:"filters,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
	Temperature float64                `json:"temperature,omitempty"`
}

// ChatMessageResponse represents chat response
type ChatMessageResponse struct {
	SessionID       string                 `json:"session_id"`
	MessageID       string                 `json:"message_id"`
	Answer          string                 `json:"answer"`
	Confidence      float64                `json:"confidence"`
	ResponseType    string                 `json:"response_type"`
	ContextUsed     bool                   `json:"context_used"`
	Sources         []SourceDocument       `json:"sources,omitempty"`
	RetrievalRoute  string                 `json:"retrieval_route,omitempty"`
	ResponseTime    float64                `json:"response_time_ms"`
	TokensUsed      int                    `json:"tokens_used,omitempty"`
	SafetyAnalysis  *SafetyAnalysisResult  `json:"safety_analysis,omitempty"`
	EmotionAnalysis *EmotionAnalysisResult `json:"emotion_analysis,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

// SourceDocument represents a source document from RAG
type SourceDocument struct {
	DocumentID      string  `json:"document_id,omitempty"`
	Title           string  `json:"title"`
	Excerpt         string  `json:"excerpt"`
	RelevanceScore  float64 `json:"relevance_score"`
	SourceType      string  `json:"source_type"`
	URL             string  `json:"url,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

// Safety analysis models

// SafetyAnalysisRequest for content safety checking
type SafetyAnalysisRequest struct {
	Content   string                 `json:"content" validate:"required"`
	UserID    string                 `json:"user_id,omitempty"`
	SessionID string                 `json:"session_id,omitempty"`
	Context   map[string]interface{} `json:"context,omitempty"`
}

// SafetyAnalysisResult represents safety analysis results
type SafetyAnalysisResult struct {
	IsSafe          bool                   `json:"is_safe"`
	RiskLevel       string                 `json:"risk_level"` // low, medium, high, critical
	RiskScore       float64                `json:"risk_score"`
	Flags           []string               `json:"flags,omitempty"`
	CrisisKeywords  []string               `json:"crisis_keywords,omitempty"`
	RequiresEscalation bool                `json:"requires_escalation"`
	SafeResponse    string                 `json:"safe_response,omitempty"`
	Recommendations []string               `json:"recommendations,omitempty"`
	Categories      map[string]interface{} `json:"categories,omitempty"`
	ProcessedAt     time.Time              `json:"processed_at"`
}

// Emotion analysis models

// EmotionAnalysisResult represents emotion detection results
type EmotionAnalysisResult struct {
	PrimaryEmotion  string                 `json:"primary_emotion"`
	EmotionScores   map[string]float64     `json:"emotion_scores"`
	Sentiment       string                 `json:"sentiment"` // positive, negative, neutral
	SentimentScore  float64                `json:"sentiment_score"`
	Intensity       string                 `json:"intensity"` // low, medium, high
	CrisisIndicators []string              `json:"crisis_indicators,omitempty"`
	Recommendations []string               `json:"recommendations,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
	ProcessedAt     time.Time              `json:"processed_at"`
}

// Session management models

// Session represents a user session
type Session struct {
	ID          string                 `json:"id"`
	UserID      string                 `json:"user_id,omitempty"`
	IPAddress   string                 `json:"ip_address"`
	UserAgent   string                 `json:"user_agent,omitempty"`
	CreatedAt   time.Time              `json:"created_at"`
	LastActivity time.Time             `json:"last_activity"`
	IsActive    bool                   `json:"is_active"`
	RequestCount int                   `json:"request_count"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
	ExpiresAt   time.Time              `json:"expires_at"`
}

// SessionCreateRequest for creating new sessions
type SessionCreateRequest struct {
	UserID    string                 `json:"user_id,omitempty"`
	IPAddress string                 `json:"ip_address,omitempty"`
	UserAgent string                 `json:"user_agent,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// SessionStats represents session statistics
type SessionStats struct {
	TotalSessions   int                    `json:"total_sessions"`
	ActiveSessions  int                    `json:"active_sessions"`
	AverageDuration float64                `json:"average_duration_minutes"`
	RequestCount    int                    `json:"total_requests"`
	MemoryUsage     int64                  `json:"estimated_memory_bytes"`
	TopUserAgents   []map[string]interface{} `json:"top_user_agents,omitempty"`
	CreatedAt       time.Time              `json:"created_at"`
}

// Search models

// SearchRequest represents search query
type SearchRequest struct {
	Query      string                 `json:"query" validate:"required"`
	TopK       int                    `json:"top_k,omitempty"`
	Route      string                 `json:"route,omitempty"` // exact, semantic, hybrid, auto
	Filters    map[string]interface{} `json:"filters,omitempty"`
	UserID     string                 `json:"user_id,omitempty"`
	SessionID  string                 `json:"session_id,omitempty"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

// SearchResponse represents search results
type SearchResponse struct {
	Results      []SourceDocument       `json:"results"`
	TotalCount   int                    `json:"total_count"`
	Route        string                 `json:"route_used"`
	ResponseTime float64                `json:"response_time_ms"`
	CacheHit     bool                   `json:"cache_hit"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// Health check models

// HealthStatus represents service health
type HealthStatus struct {
	Service     string                 `json:"service"`
	Status      string                 `json:"status"` // healthy, degraded, unhealthy
	Version     string                 `json:"version"`
	Timestamp   time.Time              `json:"timestamp"`
	Uptime      time.Duration          `json:"uptime"`
	Environment string                 `json:"environment"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// DetailedHealthStatus represents comprehensive health check
type DetailedHealthStatus struct {
	Overall     string                    `json:"overall_status"`
	Services    map[string]ServiceHealth  `json:"services"`
	Databases   map[string]DatabaseHealth `json:"databases"`
	SystemInfo  SystemInfo                `json:"system_info"`
	Performance PerformanceMetrics        `json:"performance"`
	Timestamp   time.Time                 `json:"timestamp"`
}

// ServiceHealth represents individual service health
type ServiceHealth struct {
	Status       string        `json:"status"`
	ResponseTime time.Duration `json:"response_time_ms"`
	LastCheck    time.Time     `json:"last_check"`
	ErrorCount   int           `json:"error_count"`
	URL          string        `json:"url,omitempty"`
	Version      string        `json:"version,omitempty"`
}

// DatabaseHealth represents database connection health
type DatabaseHealth struct {
	Status       string        `json:"status"`
	ResponseTime time.Duration `json:"response_time_ms"`
	LastCheck    time.Time     `json:"last_check"`
	Connections  int           `json:"active_connections"`
	ErrorCount   int           `json:"error_count"`
	URL          string        `json:"url,omitempty"`
}

// SystemInfo represents system resource information
type SystemInfo struct {
	CPUUsage      float64   `json:"cpu_usage_percent"`
	MemoryUsage   int64     `json:"memory_usage_bytes"`
	MemoryTotal   int64     `json:"memory_total_bytes"`
	DiskUsage     int64     `json:"disk_usage_bytes"`
	DiskTotal     int64     `json:"disk_total_bytes"`
	Goroutines    int       `json:"goroutines"`
	StartTime     time.Time `json:"start_time"`
	RequestCount  int64     `json:"total_requests"`
	ErrorCount    int64     `json:"total_errors"`
}

// PerformanceMetrics represents performance statistics
type PerformanceMetrics struct {
	AverageResponseTime float64                `json:"average_response_time_ms"`
	P95ResponseTime     float64                `json:"p95_response_time_ms"`
	P99ResponseTime     float64                `json:"p99_response_time_ms"`
	RequestsPerSecond   float64                `json:"requests_per_second"`
	ErrorRate          float64                `json:"error_rate_percent"`
	CacheHitRate       float64                `json:"cache_hit_rate_percent"`
	DatabaseMetrics    map[string]interface{} `json:"database_metrics,omitempty"`
}

// Analytics models

// AnalyticsEvent represents a tracked event
type AnalyticsEvent struct {
	ID        string                 `json:"id"`
	EventType string                 `json:"event_type"`
	UserID    string                 `json:"user_id,omitempty"`
	SessionID string                 `json:"session_id,omitempty"`
	Data      map[string]interface{} `json:"data"`
	Timestamp time.Time              `json:"timestamp"`
	IPAddress string                 `json:"ip_address,omitempty"`
	UserAgent string                 `json:"user_agent,omitempty"`
}

// ConversationHistory represents stored conversation data
type ConversationHistory struct {
	SessionID      string                 `json:"session_id"`
	UserID         string                 `json:"user_id,omitempty"`
	Messages       []ConversationMessage  `json:"messages"`
	TotalMessages  int                    `json:"total_messages"`
	StartTime      time.Time              `json:"start_time"`
	LastActivity   time.Time              `json:"last_activity"`
	Duration       time.Duration          `json:"duration_seconds"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// ConversationMessage represents a single conversation message
type ConversationMessage struct {
	ID              string                 `json:"id"`
	SessionID       string                 `json:"session_id"`
	UserID          string                 `json:"user_id,omitempty"`
	Content         string                 `json:"content"`
	Type            string                 `json:"type"` // user, assistant, system
	Timestamp       time.Time              `json:"timestamp"`
	SafetyAnalysis  *SafetyAnalysisResult  `json:"safety_analysis,omitempty"`
	EmotionAnalysis *EmotionAnalysisResult `json:"emotion_analysis,omitempty"`
	Sources         []SourceDocument       `json:"sources,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

// Rate limiting models

// RateLimitInfo represents rate limiting information
type RateLimitInfo struct {
	Limit          int       `json:"limit"`
	Remaining      int       `json:"remaining"`
	Reset          time.Time `json:"reset"`
	RetryAfter     int       `json:"retry_after,omitempty"`
	Window         string    `json:"window"` // second, minute, hour
}

// Error response models

// ErrorResponse represents API error responses
type ErrorResponse struct {
	Error   string                 `json:"error"`
	Message string                 `json:"message"`
	Code    string                 `json:"code,omitempty"`
	Details map[string]interface{} `json:"details,omitempty"`
	TraceID string                 `json:"trace_id,omitempty"`
	Path    string                 `json:"path,omitempty"`
	Method  string                 `json:"method,omitempty"`
	Timestamp time.Time            `json:"timestamp"`
}

// ValidationError represents validation error details
type ValidationError struct {
	Field   string `json:"field"`
	Message string `json:"message"`
	Value   string `json:"value,omitempty"`
}

// APIResponse represents standardized API response wrapper
type APIResponse struct {
	Success   bool        `json:"success"`
	Data      interface{} `json:"data,omitempty"`
	Error     *ErrorResponse `json:"error,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
	Timestamp time.Time   `json:"timestamp"`
}

// Proxy request models for upstream services

// ProxyRequest represents a request to be proxied to upstream services
type ProxyRequest struct {
	Method  string                 `json:"method"`
	URL     string                 `json:"url"`
	Headers map[string]string      `json:"headers,omitempty"`
	Body    interface{}            `json:"body,omitempty"`
	Timeout time.Duration          `json:"timeout,omitempty"`
	Retry   int                    `json:"retry,omitempty"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

// ProxyResponse represents response from upstream services
type ProxyResponse struct {
	StatusCode   int                    `json:"status_code"`
	Headers      map[string]string      `json:"headers,omitempty"`
	Body         interface{}            `json:"body,omitempty"`
	ResponseTime time.Duration          `json:"response_time_ms"`
	FromCache    bool                   `json:"from_cache"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}