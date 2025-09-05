// Package main provides interfaces for dependency injection and testing
package main

import (
	"context"
	"time"

	"github.com/gin-gonic/gin"
)

// DatabaseManagerInterface defines database operations
type DatabaseManagerInterface interface {
	Connect() error
	Close()
	CreateUser(req *RegisterRequest) (*User, error)
	AuthenticateUser(email, password string) (*User, error)
	GetUserByID(userID string) (*User, error)
	GetUserByEmail(email string) (*User, error)
	GetUser(userID string) (*User, error) // Legacy compatibility
	UpdateLastLogin(userID string) error
	CreateSession(req *SessionCreateRequest) (*Session, error)
	GetSession(sessionID string) (*Session, error)
	UpdateSessionActivity(sessionID string) error
	DeleteSession(sessionID string) error
	InvalidateSession(sessionID string) error
	CleanupExpiredSessions() error
	GetSessionStats() (*SessionStats, error)
	GetDatabaseHealth() map[string]*DatabaseHealth
	PingPostgres() error
	PingRedis() error
	PingMongo() error
	PingScylla() error
	StoreAnalyticsEvent(event *AnalyticsEvent) error
	CheckRateLimit(key string, limit int, window time.Duration) (bool, *RateLimitInfo, error)
}

// ServiceManagerInterface defines service operations
type ServiceManagerInterface interface {
	InitializeCircuitBreakers()
	PerformHealthCheck(ctx context.Context) *DetailedHealthStatus
	GetServiceHealth() map[string]*ServiceHealth
	GetPerformanceMetrics() *PerformanceMetrics
	SendChatMessage(ctx context.Context, req *ChatMessageRequest) (*ChatMessageResponse, error)
	PerformSearch(ctx context.Context, req *SearchRequest) (*SearchResponse, error)
	SearchDocuments(ctx context.Context, req *SearchRequest) (*SearchResponse, error)
	CheckUsageLimits(userID string) error
	AnalyzeSafety(ctx context.Context, req *SafetyAnalysisRequest) (*SafetyAnalysisResult, error)
	AnalyzeEmotion(ctx context.Context, content string) (*EmotionAnalysisResult, error)
	GenerateResponse(ctx context.Context, req *ChatMessageRequest) (*ChatMessageResponse, error)
	SaveConversationMessage(ctx context.Context, message *ConversationMessage) error
	GetConversationHistory(ctx context.Context, sessionID, userID string) (*ConversationHistory, error)
	GetUserSubscription(ctx context.Context, userID string) (map[string]interface{}, error)
}

// MiddlewareManagerInterface defines middleware operations
type MiddlewareManagerInterface interface {
	CORSMiddleware() gin.HandlerFunc
	SecurityHeadersMiddleware() gin.HandlerFunc
	LoggingMiddleware() gin.HandlerFunc
	RateLimitMiddleware() gin.HandlerFunc
	AuthenticationMiddleware() gin.HandlerFunc
	OptionalAuthMiddleware() gin.HandlerFunc
	SessionMiddleware() gin.HandlerFunc
	SuperuserMiddleware() gin.HandlerFunc
	SafetyMiddleware() gin.HandlerFunc
	GenerateJWT(user *User) (string, error)
	GetUserFromContext(c *gin.Context) (*User, error)
}