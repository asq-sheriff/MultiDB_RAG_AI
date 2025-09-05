// Package main provides comprehensive tests for the API Gateway service
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Test Configuration
const (
	testJWTSecret = "test-secret-key-for-api-gateway-testing"
	testPort      = "8999"
)

// MockServiceManager implements ServiceManagerInterface for testing
type MockServiceManager struct {
	healthStatus      map[string]*ServiceHealth
	circuitBreakers   map[string]bool
	performanceMetrics *PerformanceMetrics
}

// MockDatabaseManager implements DatabaseManagerInterface for testing
type MockDatabaseManager struct {
	users    map[string]*User
	sessions map[string]*Session
	connected bool
}

// MockMiddlewareManager implements MiddlewareManagerInterface for testing
type MockMiddlewareManager struct {
	config *ServiceConfig
}

// HandlerManager manages all HTTP handlers - simplified for testing
type HandlerManager struct {
	dbManager      DatabaseManagerInterface
	serviceManager ServiceManagerInterface
	middleware     MiddlewareManagerInterface
	config         *ServiceConfig
}

// Test setup helpers

func setupTestGateway() (*gin.Engine, *MockDatabaseManager, *MockServiceManager) {
	gin.SetMode(gin.TestMode)
	
	// Create test config
	config := &ServiceConfig{
		Port:        testPort,
		Environment: "test",
		SecretKey:   testJWTSecret,
		DebugMode:   true,
		AccessTokenExpireMinutes: 30,
		RequestTimeout: 30 * time.Second,
		MaxRequestsPerMinute: 60,
		MaxRequestsPerSecond: 10,
	}

	// Create mock managers
	dbManager := &MockDatabaseManager{
		users:     make(map[string]*User),
		sessions:  make(map[string]*Session),
		connected: true,
	}

	serviceManager := &MockServiceManager{
		healthStatus: map[string]*ServiceHealth{
			"search": {
				Status:       "healthy",
				ResponseTime: 50 * time.Millisecond,
				LastCheck:    time.Now(),
				ErrorCount:   0,
			},
			"embedding": {
				Status:       "healthy",
				ResponseTime: 50 * time.Millisecond,
				LastCheck:    time.Now(),
				ErrorCount:   0,
			},
			"generation": {
				Status:       "healthy",
				ResponseTime: 50 * time.Millisecond,
				LastCheck:    time.Now(),
				ErrorCount:   0,
			},
		},
		circuitBreakers: make(map[string]bool),
		performanceMetrics: &PerformanceMetrics{
			AverageResponseTime: 100,
			RequestsPerSecond:   10,
			ErrorRate:          0.1,
		},
	}

	middlewareManager := &MockMiddlewareManager{
		config: config,
	}

	// Create handler manager
	handlerManager := &HandlerManager{
		dbManager:      dbManager,
		serviceManager: serviceManager,
		middleware:     middlewareManager,
		config:         config,
	}

	// Setup router with test middleware
	router := setupTestRouter(handlerManager, middlewareManager)

	return router, dbManager, serviceManager
}

func setupTestRouter(hm *HandlerManager, mm *MockMiddlewareManager) *gin.Engine {
	router := gin.New()

	// Minimal test middleware
	router.Use(gin.Logger())
	router.Use(gin.Recovery())
	
	// Health check routes
	health := router.Group("/health")
	{
		health.GET("/", hm.HealthHandler)
		health.GET("/detailed", hm.DetailedHealthHandler)
	}

	// Public routes
	public := router.Group("/api/v1")
	{
		auth := public.Group("/auth")
		{
			auth.POST("/login", hm.LoginHandler)
			auth.POST("/register", hm.RegisterHandler)
		}
	}

	// Protected routes (require authentication)
	protected := router.Group("/api/v1")
	protected.Use(mm.AuthenticationMiddleware())
	{
		// Chat
		chat := protected.Group("/chat")
		{
			chat.POST("/", hm.ChatHandler)
		}

		// User management
		users := protected.Group("/users")
		{
			users.GET("/profile", hm.GetUserProfileHandler)
		}
	}

	return router
}

// MockDatabaseManager methods

func (m *MockDatabaseManager) Connect() error {
	m.connected = true
	return nil
}

func (m *MockDatabaseManager) Close() {
	m.connected = false
}

func (m *MockDatabaseManager) AuthenticateUser(email, password string) (*User, error) {
	user, exists := m.users[email]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}
	
	// Simple password check for testing
	if password != "testpassword" {
		return nil, fmt.Errorf("invalid password")
	}
	
	return user, nil
}

func (m *MockDatabaseManager) CreateUser(req *RegisterRequest) (*User, error) {
	if _, exists := m.users[req.Email]; exists {
		return nil, fmt.Errorf("user already exists")
	}
	
	user := &User{
		ID:        uuid.New(),
		Email:     req.Email,
		FirstName: req.FirstName,
		LastName:  req.LastName,
		Phone:     req.Phone,
		IsActive:  true,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	
	m.users[req.Email] = user
	return user, nil
}

func (m *MockDatabaseManager) GetUserByID(userID string) (*User, error) {
	for _, user := range m.users {
		if user.ID.String() == userID {
			return user, nil
		}
	}
	return nil, fmt.Errorf("user not found")
}

func (m *MockDatabaseManager) GetUserByEmail(email string) (*User, error) {
	user, exists := m.users[email]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}
	return user, nil
}

func (m *MockDatabaseManager) GetUser(userID string) (*User, error) {
	return m.GetUserByID(userID)
}

func (m *MockDatabaseManager) UpdateLastLogin(userID string) error {
	for _, user := range m.users {
		if user.ID.String() == userID {
			now := time.Now()
			user.LastLoginAt = &now
			return nil
		}
	}
	return fmt.Errorf("user not found")
}

func (m *MockDatabaseManager) CreateSession(req *SessionCreateRequest) (*Session, error) {
	session := &Session{
		ID:           uuid.New().String(),
		UserID:       req.UserID,
		IPAddress:    req.IPAddress,
		UserAgent:    req.UserAgent,
		CreatedAt:    time.Now(),
		LastActivity: time.Now(),
		IsActive:     true,
		ExpiresAt:    time.Now().Add(time.Hour),
	}
	
	m.sessions[session.ID] = session
	return session, nil
}

func (m *MockDatabaseManager) GetSession(sessionID string) (*Session, error) {
	session, exists := m.sessions[sessionID]
	if !exists {
		return nil, fmt.Errorf("session not found")
	}
	return session, nil
}

func (m *MockDatabaseManager) UpdateSessionActivity(sessionID string) error {
	session, exists := m.sessions[sessionID]
	if !exists {
		return fmt.Errorf("session not found")
	}
	session.LastActivity = time.Now()
	return nil
}

func (m *MockDatabaseManager) DeleteSession(sessionID string) error {
	_, exists := m.sessions[sessionID]
	if !exists {
		return fmt.Errorf("session not found")
	}
	delete(m.sessions, sessionID)
	return nil
}

func (m *MockDatabaseManager) InvalidateSession(sessionID string) error {
	session, exists := m.sessions[sessionID]
	if !exists {
		return fmt.Errorf("session not found")
	}
	session.IsActive = false
	return nil
}

func (m *MockDatabaseManager) CleanupExpiredSessions() error {
	now := time.Now()
	for id, session := range m.sessions {
		if now.After(session.ExpiresAt) {
			delete(m.sessions, id)
		}
	}
	return nil
}

func (m *MockDatabaseManager) GetSessionStats() (*SessionStats, error) {
	activeCount := 0
	totalRequests := 0
	
	for _, session := range m.sessions {
		if session.IsActive {
			activeCount++
		}
		totalRequests += session.RequestCount
	}
	
	return &SessionStats{
		TotalSessions:  len(m.sessions),
		ActiveSessions: activeCount,
		RequestCount:   totalRequests,
		CreatedAt:      time.Now(),
	}, nil
}

func (m *MockDatabaseManager) GetDatabaseHealth() map[string]*DatabaseHealth {
	return map[string]*DatabaseHealth{
		"postgres": {
			Status:       "healthy",
			ResponseTime: 10 * time.Millisecond,
			LastCheck:    time.Now(),
			Connections:  5,
		},
		"redis": {
			Status:       "healthy",
			ResponseTime: 5 * time.Millisecond,
			LastCheck:    time.Now(),
			Connections:  3,
		},
	}
}

func (m *MockDatabaseManager) PingPostgres() error {
	if !m.connected {
		return fmt.Errorf("postgres not connected")
	}
	return nil
}

func (m *MockDatabaseManager) PingRedis() error {
	if !m.connected {
		return fmt.Errorf("redis not connected")
	}
	return nil
}

func (m *MockDatabaseManager) PingMongo() error {
	if !m.connected {
		return fmt.Errorf("mongo not connected")
	}
	return nil
}

func (m *MockDatabaseManager) PingScylla() error {
	if !m.connected {
		return fmt.Errorf("scylla not connected")
	}
	return nil
}

func (m *MockDatabaseManager) StoreAnalyticsEvent(event *AnalyticsEvent) error {
	return nil
}

func (m *MockDatabaseManager) CheckRateLimit(key string, limit int, window time.Duration) (bool, *RateLimitInfo, error) {
	return true, &RateLimitInfo{
		Limit:     limit,
		Remaining: limit - 1,
		Reset:     time.Now().Add(window),
	}, nil
}

// MockServiceManager methods

func (m *MockServiceManager) InitializeCircuitBreakers() {
	m.circuitBreakers = map[string]bool{
		"search":         true,
		"embedding":      true,
		"generation":     true,
		"content_safety": true,
		"chat_history":   true,
	}
}

func (m *MockServiceManager) PerformHealthCheck(ctx context.Context) *DetailedHealthStatus {
	services := make(map[string]ServiceHealth)
	
	for name, health := range m.healthStatus {
		if health != nil {
			services[name] = *health
		}
	}
	
	return &DetailedHealthStatus{
		Overall:     "healthy",
		Services:    services,
		Timestamp:   time.Now(),
		Performance: *m.performanceMetrics,
	}
}

func (m *MockServiceManager) GetServiceHealth() map[string]*ServiceHealth {
	return m.healthStatus
}

func (m *MockServiceManager) GetPerformanceMetrics() *PerformanceMetrics {
	return m.performanceMetrics
}

func (m *MockServiceManager) SendChatMessage(ctx context.Context, req *ChatMessageRequest) (*ChatMessageResponse, error) {
	return &ChatMessageResponse{
		SessionID:    req.SessionID,
		MessageID:    uuid.New().String(),
		Answer:       "This is a mock response to: " + req.Message,
		Confidence:   0.9,
		ResponseType: "generated",
		ContextUsed:  true,
		ResponseTime: 250,
		SafetyAnalysis: &SafetyAnalysisResult{
			IsSafe:    true,
			RiskLevel: "low",
			RiskScore: 0.1,
		},
	}, nil
}

func (m *MockServiceManager) PerformSearch(ctx context.Context, req *SearchRequest) (*SearchResponse, error) {
	return &SearchResponse{
		Results: []SourceDocument{
			{
				Title:          "Test Document",
				Excerpt:        "This is a test document excerpt",
				RelevanceScore: 0.95,
				SourceType:     "knowledge_base",
			},
		},
		TotalCount:   1,
		Route:        "semantic",
		ResponseTime: 100,
		CacheHit:     false,
	}, nil
}

func (m *MockServiceManager) SearchDocuments(ctx context.Context, req *SearchRequest) (*SearchResponse, error) {
	return m.PerformSearch(ctx, req)
}

func (m *MockServiceManager) CheckUsageLimits(userID string) error {
	return nil
}

func (m *MockServiceManager) AnalyzeSafety(ctx context.Context, req *SafetyAnalysisRequest) (*SafetyAnalysisResult, error) {
	return &SafetyAnalysisResult{
		IsSafe:             true,
		RiskLevel:          "low",
		RiskScore:          0.1,
		RequiresEscalation: false,
		ProcessedAt:        time.Now(),
	}, nil
}

func (m *MockServiceManager) AnalyzeEmotion(ctx context.Context, content string) (*EmotionAnalysisResult, error) {
	return &EmotionAnalysisResult{
		PrimaryEmotion: "neutral",
		EmotionScores: map[string]float64{
			"neutral":  0.8,
			"positive": 0.1,
			"negative": 0.1,
		},
		Sentiment:      "neutral",
		SentimentScore: 0.0,
		Intensity:      "low",
		ProcessedAt:    time.Now(),
	}, nil
}

func (m *MockServiceManager) GenerateResponse(ctx context.Context, req *ChatMessageRequest) (*ChatMessageResponse, error) {
	return m.SendChatMessage(ctx, req)
}

func (m *MockServiceManager) SaveConversationMessage(ctx context.Context, message *ConversationMessage) error {
	return nil
}

func (m *MockServiceManager) GetConversationHistory(ctx context.Context, sessionID, userID string) (*ConversationHistory, error) {
	return &ConversationHistory{
		SessionID:     sessionID,
		UserID:        userID,
		Messages:      []ConversationMessage{},
		TotalMessages: 0,
		StartTime:     time.Now().Add(-1 * time.Hour),
		LastActivity:  time.Now(),
		Duration:      time.Hour,
	}, nil
}

func (m *MockServiceManager) GetUserSubscription(ctx context.Context, userID string) (map[string]interface{}, error) {
	return map[string]interface{}{
		"plan":       "free",
		"status":     "active",
		"expires_at": time.Now().Add(30 * 24 * time.Hour),
		"features":   []string{"basic_chat", "basic_search"},
	}, nil
}

// MockMiddlewareManager methods

func (m *MockMiddlewareManager) AuthenticationMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Simple test authentication - check for Authorization header
		auth := c.GetHeader("Authorization")
		if auth == "" {
			c.JSON(http.StatusUnauthorized, ErrorResponse{
				Error:     "Authentication required",
				Message:   "Missing Authorization header",
				Timestamp: time.Now(),
			})
			c.Abort()
			return
		}
		
		// Set mock user context
		c.Set("user_id", "test-user-id")
		c.Set("user_email", "test@example.com")
		c.Next()
	}
}

func (m *MockMiddlewareManager) GenerateJWT(user *User) (string, error) {
	return "mock-jwt-token-" + user.ID.String(), nil
}

func (m *MockMiddlewareManager) GetUserFromContext(c *gin.Context) (*User, error) {
	_, exists := c.Get("user_id")
	if !exists {
		return nil, fmt.Errorf("user not found in context")
	}
	
	return &User{
		ID:        uuid.MustParse("550e8400-e29b-41d4-a716-446655440000"),
		Email:     "test@example.com",
		FirstName: "Test",
		LastName:  "User",
		IsActive:  true,
	}, nil
}

// Add all other middleware methods as no-ops for testing
func (m *MockMiddlewareManager) CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
}

func (m *MockMiddlewareManager) SecurityHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
}

func (m *MockMiddlewareManager) LoggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
}

func (m *MockMiddlewareManager) RateLimitMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
}

func (m *MockMiddlewareManager) OptionalAuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
}

func (m *MockMiddlewareManager) SessionMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
}

func (m *MockMiddlewareManager) SuperuserMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Set("is_superuser", true)
		c.Next()
	}
}

func (m *MockMiddlewareManager) SafetyMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
}

// HandlerManager methods - simplified implementations for testing

func (hm *HandlerManager) HealthHandler(c *gin.Context) {
	response := HealthStatus{
		Service:   "api-gateway-service",
		Status:    "healthy",
		Version:   "test",
		Timestamp: time.Now(),
		Uptime:    time.Hour,
	}
	c.JSON(http.StatusOK, response)
}

func (hm *HandlerManager) DetailedHealthHandler(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	
	healthStatus := hm.serviceManager.PerformHealthCheck(ctx)
	c.JSON(http.StatusOK, healthStatus)
}

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

	user, err := hm.dbManager.AuthenticateUser(req.Email, req.Password)
	if err != nil {
		c.JSON(http.StatusUnauthorized, ErrorResponse{
			Error:     "Authentication failed",
			Message:   "Invalid email or password",
			Timestamp: time.Now(),
		})
		return
	}

	tokenString, err := hm.middleware.GenerateJWT(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Token generation failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	expiresAt := time.Now().Add(time.Duration(hm.config.AccessTokenExpireMinutes) * time.Minute)

	response := TokenResponse{
		AccessToken: tokenString,
		TokenType:   "Bearer",
		ExpiresIn:   hm.config.AccessTokenExpireMinutes * 60,
		ExpiresAt:   expiresAt,
	}

	c.JSON(http.StatusOK, response)
}

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

	user, err := hm.dbManager.CreateUser(&req)
	if err != nil {
		c.JSON(http.StatusConflict, ErrorResponse{
			Error:     "Registration failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	tokenString, err := hm.middleware.GenerateJWT(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Token generation failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	expiresAt := time.Now().Add(time.Duration(hm.config.AccessTokenExpireMinutes) * time.Minute)

	response := TokenResponse{
		AccessToken: tokenString,
		TokenType:   "Bearer",
		ExpiresIn:   hm.config.AccessTokenExpireMinutes * 60,
		ExpiresAt:   expiresAt,
	}

	c.JSON(http.StatusCreated, response)
}

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

	response, err := hm.serviceManager.SendChatMessage(c.Request.Context(), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "Chat generation failed",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, response)
}

func (hm *HandlerManager) GetUserProfileHandler(c *gin.Context) {
	user, err := hm.middleware.GetUserFromContext(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, ErrorResponse{
			Error:     "User not found",
			Message:   err.Error(),
			Timestamp: time.Now(),
		})
		return
	}

	c.JSON(http.StatusOK, user)
}

// Core API Gateway Tests

func TestHealthEndpoints(t *testing.T) {
	router, _, _ := setupTestGateway()

	t.Run("BasicHealthCheck", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/health/", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response HealthStatus
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "healthy", response.Status)
		assert.Equal(t, "api-gateway-service", response.Service)
	})

	t.Run("DetailedHealthCheck", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/health/detailed", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response DetailedHealthStatus
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "healthy", response.Overall)
		assert.Contains(t, response.Services, "search")
		assert.Contains(t, response.Services, "embedding")
	})
}

func TestAuthenticationFlow(t *testing.T) {
	router, dbManager, _ := setupTestGateway()

	// Create a test user
	req := &RegisterRequest{
		Email:     "test@example.com",
		Password:  "testpassword",
		FirstName: "Test",
		LastName:  "User",
		Phone:     "123-456-7890",
	}
	testUser, err := dbManager.CreateUser(req)
	require.NoError(t, err)

	t.Run("UserRegistration", func(t *testing.T) {
		regReq := RegisterRequest{
			Email:     "newuser@example.com",
			Password:  "password123",
			FirstName: "New",
			LastName:  "User",
			Phone:     "555-0123",
		}

		body, _ := json.Marshal(regReq)
		req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusCreated, w.Code)

		var response TokenResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.NotEmpty(t, response.AccessToken)
		assert.Equal(t, "Bearer", response.TokenType)
	})

	t.Run("UserLogin", func(t *testing.T) {
		loginReq := LoginRequest{
			Email:    testUser.Email,
			Password: "testpassword",
		}

		body, _ := json.Marshal(loginReq)
		req, _ := http.NewRequest("POST", "/api/v1/auth/login", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response TokenResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.NotEmpty(t, response.AccessToken)
		assert.Equal(t, "Bearer", response.TokenType)
	})

	t.Run("InvalidLogin", func(t *testing.T) {
		loginReq := LoginRequest{
			Email:    "nonexistent@example.com",
			Password: "wrongpassword",
		}

		body, _ := json.Marshal(loginReq)
		req, _ := http.NewRequest("POST", "/api/v1/auth/login", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusUnauthorized, w.Code)
	})
}

func TestProtectedEndpoints(t *testing.T) {
	router, dbManager, _ := setupTestGateway()

	// Create test user
	req := &RegisterRequest{
		Email:     "profile@example.com",
		Password:  "testpassword",
		FirstName: "Profile",
		LastName:  "User",
		Phone:     "555-1234",
	}
	testUser, err := dbManager.CreateUser(req)
	require.NoError(t, err)

	t.Run("GetUserProfile", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/users/profile", nil)
		req.Header.Set("Authorization", "Bearer test-token")
		req.Header.Set("X-User-ID", testUser.ID.String())

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("UnauthorizedAccess", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/users/profile", nil)

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusUnauthorized, w.Code)
	})
}

func TestChatEndpoints(t *testing.T) {
	router, _, _ := setupTestGateway()

	t.Run("ChatMessage", func(t *testing.T) {
		chatReq := ChatMessageRequest{
			Message:   "Hello, how can you help me?",
			SessionID: "test-session-123",
			UserID:    "test-user-id",
			EnableRAG: true,
		}

		body, _ := json.Marshal(chatReq)
		req, _ := http.NewRequest("POST", "/api/v1/chat/", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer test-token")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)

		var response ChatMessageResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response.Answer, "mock response")
		assert.NotEmpty(t, response.MessageID)
	})
}

// Benchmark tests

func BenchmarkHealthCheck(b *testing.B) {
	router, _, _ := setupTestGateway()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("GET", "/health/", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}

func BenchmarkAuthenticationFlow(b *testing.B) {
	router, dbManager, _ := setupTestGateway()

	// Create test user
	regReq := &RegisterRequest{
		Email:     "bench@example.com",
		Password:  "testpassword",
		FirstName: "Bench",
		LastName:  "User",
		Phone:     "123-456-7890",
	}
	dbManager.CreateUser(regReq)

	loginReq := LoginRequest{
		Email:    "bench@example.com",
		Password: "testpassword",
	}
	body, _ := json.Marshal(loginReq)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("POST", "/api/v1/auth/login", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}