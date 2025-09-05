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
		healthStatus: make(map[string]*ServiceHealth),
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
	handlerManager := NewHandlerManager(dbManager, serviceManager, middlewareManager, config)

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
		
		public.POST("/search", hm.SearchHandler)
	}

	// Protected routes
	protected := router.Group("/api/v1")
	protected.Use(mm.AuthenticationMiddleware())
	{
		auth := protected.Group("/auth")
		{
			auth.POST("/logout", hm.LogoutHandler)
		}
		
		chat := protected.Group("/chat")
		{
			chat.POST("/", hm.ChatHandler)
			chat.GET("/history/:session_id", hm.GetConversationHistoryHandler)
		}
		
		users := protected.Group("/users")
		{
			users.GET("/profile", hm.GetUserProfileHandler)
			users.GET("/subscription", hm.GetUserSubscriptionHandler)
		}
		
		protected.GET("/rate-limit", hm.GetRateLimitInfoHandler)
	}

	return router
}

// Mock implementations

// MockDatabaseManager methods
func (m *MockDatabaseManager) Connect() error {
	m.connected = true
	return nil
}

func (m *MockDatabaseManager) Close() {
	m.connected = false
}

func (m *MockDatabaseManager) Ping() error {
	if !m.connected {
		return fmt.Errorf("database not connected")
	}
	return nil
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

func (m *MockDatabaseManager) CreateUserSimple(email, hashedPassword, firstName, lastName, phone string) (*User, error) {
	if _, exists := m.users[email]; exists {
		return nil, fmt.Errorf("user already exists")
	}

	user := &User{
		ID:        uuid.New(),
		Email:     email,
		FirstName: firstName,
		LastName:  lastName,
		Phone:     phone,
		IsActive:  true,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	m.users[email] = user
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
	// Legacy compatibility - redirect to GetUserByID
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

func (m *MockDatabaseManager) InvalidateSession(sessionID string) error {
	session, exists := m.sessions[sessionID]
	if !exists {
		return fmt.Errorf("session not found")
	}
	session.IsActive = false
	return nil
}

func (m *MockDatabaseManager) StoreAnalyticsEvent(event *AnalyticsEvent) error {
	// Mock implementation - just return success
	return nil
}

func (m *MockDatabaseManager) CheckRateLimit(key string, limit int, window time.Duration) (bool, *RateLimitInfo, error) {
	// Mock implementation - always allow for testing
	return true, &RateLimitInfo{
		Limit:     limit,
		Remaining: limit - 1,
		Reset:     time.Now().Add(window),
	}, nil
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

func (m *MockDatabaseManager) DeleteSession(sessionID string) error {
	_, exists := m.sessions[sessionID]
	if !exists {
		return fmt.Errorf("session not found")
	}
	delete(m.sessions, sessionID)
	return nil
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

// MockServiceManager methods
func (m *MockServiceManager) InitializeCircuitBreakers() {
	m.circuitBreakers = map[string]bool{
		"search":      true,
		"embedding":   true,
		"generation":  true,
		"content_safety": true,
		"chat_history": true,
	}
}

func (m *MockServiceManager) PerformHealthCheck(ctx context.Context) *DetailedHealthStatus {
	services := make(map[string]ServiceHealth)
	
	for name := range m.circuitBreakers {
		services[name] = ServiceHealth{
			Status:       "healthy",
			ResponseTime: 50 * time.Millisecond,
			LastCheck:    time.Now(),
			ErrorCount:   0,
		}
	}
	
	return &DetailedHealthStatus{
		Overall:   "healthy",
		Services:  services,
		Timestamp: time.Now(),
		Performance: *m.performanceMetrics,
	}
}

func (m *MockServiceManager) ProxySearch(ctx context.Context, req *SearchRequest) (*SearchResponse, error) {
	// Mock search response
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

func (m *MockServiceManager) ProxyChat(ctx context.Context, req *ChatMessageRequest) (*ChatMessageResponse, error) {
	// Mock chat response
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

func (m *MockServiceManager) CheckUsageLimits(userID string) error {
	// Mock implementation - always allow for testing
	return nil
}

func (m *MockServiceManager) AnalyzeSafety(ctx context.Context, req *SafetyAnalysisRequest) (*SafetyAnalysisResult, error) {
	// Mock safety analysis - always safe for testing
	return &SafetyAnalysisResult{
		IsSafe:             true,
		RiskLevel:          "low",
		RiskScore:          0.1,
		RequiresEscalation: false,
		ProcessedAt:        time.Now(),
	}, nil
}

func (m *MockServiceManager) AnalyzeEmotion(ctx context.Context, content string) (*EmotionAnalysisResult, error) {
	// Mock emotion analysis
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

func (m *MockServiceManager) SearchDocuments(ctx context.Context, req *SearchRequest) (*SearchResponse, error) {
	// Return the ProxySearch result for compatibility
	return m.ProxySearch(ctx, req)
}

func (m *MockServiceManager) SendChatMessage(ctx context.Context, req *ChatMessageRequest) (*ChatMessageResponse, error) {
	// Return the ProxyChat result for compatibility
	return m.ProxyChat(ctx, req)
}

func (m *MockServiceManager) PerformSearch(ctx context.Context, req *SearchRequest) (*SearchResponse, error) {
	// Return the ProxySearch result for compatibility
	return m.ProxySearch(ctx, req)
}

func (m *MockServiceManager) GetServiceHealth() map[string]*ServiceHealth {
	return m.healthStatus
}

func (m *MockServiceManager) GetPerformanceMetrics() *PerformanceMetrics {
	return m.performanceMetrics
}

func (m *MockServiceManager) GenerateResponse(ctx context.Context, req *ChatMessageRequest) (*ChatMessageResponse, error) {
	// Return the ProxyChat result for compatibility
	return m.ProxyChat(ctx, req)
}

func (m *MockServiceManager) SaveConversationMessage(ctx context.Context, message *ConversationMessage) error {
	// Mock implementation - just return success
	return nil
}



func (m *MockServiceManager) GetConversationHistory(ctx context.Context, sessionID, userID string) (*ConversationHistory, error) {
	// Mock conversation history
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
	// Mock subscription data
	return map[string]interface{}{
		"plan":        "free",
		"status":      "active",
		"expires_at":  time.Now().Add(30 * 24 * time.Hour),
		"features": []string{"basic_chat", "basic_search"},
	}, nil
}

func (m *MockServiceManager) GetAllServiceHealth() map[string]ServiceHealth {
	// Return the health status from the mock
	result := make(map[string]ServiceHealth)
	for name, health := range m.healthStatus {
		result[name] = *health
	}
	return result
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
	// Mock JWT generation
	return "mock-jwt-token-" + user.ID.String(), nil
}

func (m *MockMiddlewareManager) GetUserFromContext(c *gin.Context) (*User, error) {
	_, exists := c.Get("user_id")
	if !exists {
		return nil, fmt.Errorf("user not found in context")
	}
	
	// Return mock user
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
		// Set superuser flag for testing
		c.Set("is_superuser", true)
		c.Next()
	}
}

func (m *MockMiddlewareManager) SafetyMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) { c.Next() }
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
		assert.Equal(t, "api-gateway", response.Service)
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
		assert.NotEmpty(t, response.Services)
		assert.NotNil(t, response.Performance)
	})
}

func TestAuthenticationFlow(t *testing.T) {
	router, dbManager, _ := setupTestGateway()

	// Create a test user
	req := &RegisterRequest{
		Email:     "test@example.com",
		Password:  "hashedpassword",
		FirstName: "Test",
		LastName:  "User",
		Phone:     "123-456-7890",
	}
	testUser, err := dbManager.CreateUser(req)
	require.NoError(t, err)

	t.Run("UserRegistration", func(t *testing.T) {
		regReq := RegisterRequest{
			Email:     "newuser@example.com",
			Password:  "newpassword123",
			FirstName: "New",
			LastName:  "User",
			Phone:     "098-765-4321",
		}

		body, _ := json.Marshal(regReq)
		req, _ := http.NewRequest("POST", "/api/v1/auth/register", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusCreated, w.Code)
		
		var response APIResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.True(t, response.Success)
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
		
		var response APIResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.True(t, response.Success)
		
		// Check token response structure
		tokenData, ok := response.Data.(map[string]interface{})
		require.True(t, ok)
		assert.NotEmpty(t, tokenData["access_token"])
		assert.Equal(t, "Bearer", tokenData["token_type"])
	})

	t.Run("InvalidLogin", func(t *testing.T) {
		loginReq := LoginRequest{
			Email:    "invalid@example.com",
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
	router, _, _ := setupTestGateway()

	t.Run("AuthenticationRequired", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/users/profile", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusUnauthorized, w.Code)
	})

	t.Run("AuthenticatedAccess", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/users/profile", nil)
		req.Header.Set("Authorization", "Bearer test-token")
		
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("RateLimitInfo", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/rate-limit", nil)
		req.Header.Set("Authorization", "Bearer test-token")
		
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var rateLimitInfo RateLimitInfo
		err := json.Unmarshal(w.Body.Bytes(), &rateLimitInfo)
		require.NoError(t, err)
		assert.Greater(t, rateLimitInfo.Limit, 0)
	})
}

func TestSearchEndpoint(t *testing.T) {
	router, _, _ := setupTestGateway()

	t.Run("PublicSearch", func(t *testing.T) {
		searchReq := SearchRequest{
			Query: "test query",
			TopK:  5,
			Route: "semantic",
		}

		body, _ := json.Marshal(searchReq)
		req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response SearchResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.NotEmpty(t, response.Results)
		assert.Equal(t, "semantic", response.Route)
	})

	t.Run("InvalidSearchRequest", func(t *testing.T) {
		// Empty query
		searchReq := SearchRequest{
			Query: "",
		}

		body, _ := json.Marshal(searchReq)
		req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})
}

func TestChatEndpoint(t *testing.T) {
	router, _, _ := setupTestGateway()

	t.Run("ChatMessage", func(t *testing.T) {
		chatReq := ChatMessageRequest{
			Message:   "Hello, how are you?",
			SessionID: "test-session-id",
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
		assert.NotEmpty(t, response.Answer)
		assert.NotEmpty(t, response.MessageID)
		assert.Greater(t, response.Confidence, 0.0)
		assert.NotNil(t, response.SafetyAnalysis)
		assert.True(t, response.SafetyAnalysis.IsSafe)
	})

	t.Run("InvalidChatMessage", func(t *testing.T) {
		// Empty message
		chatReq := ChatMessageRequest{
			Message: "",
		}

		body, _ := json.Marshal(chatReq)
		req, _ := http.NewRequest("POST", "/api/v1/chat/", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer test-token")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})
}

func TestUserProfileEndpoints(t *testing.T) {
	router, dbManager, _ := setupTestGateway()

	// Create test user
	req := &RegisterRequest{
		Email:     "profile@example.com",
		Password:  "hashedpassword",
		FirstName: "Profile",
		LastName:  "User",
		Phone:     "555-1234",
	}
	testUser, err := dbManager.CreateUser(req)
	require.NoError(t, err)

	t.Run("GetUserProfile", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/users/profile", nil)
		req.Header.Set("Authorization", "Bearer test-token")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response APIResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.True(t, response.Success)
		
		// Verify user data structure
		userData, ok := response.Data.(map[string]interface{})
		require.True(t, ok)
		assert.Equal(t, testUser.ID.String(), userData["id"])
	})

	t.Run("GetUserSubscription", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/users/subscription", nil)
		req.Header.Set("Authorization", "Bearer test-token")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})
}

func TestConversationHistory(t *testing.T) {
	router, _, _ := setupTestGateway()

	t.Run("GetConversationHistory", func(t *testing.T) {
		sessionID := "test-session-123"
		req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/chat/history/%s", sessionID), nil)
		req.Header.Set("Authorization", "Bearer test-token")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var history ConversationHistory
		err := json.Unmarshal(w.Body.Bytes(), &history)
		require.NoError(t, err)
		assert.Equal(t, sessionID, history.SessionID)
	})
}

func TestErrorHandling(t *testing.T) {
	router, _, _ := setupTestGateway()

	t.Run("InvalidJSONRequest", func(t *testing.T) {
		req, _ := http.NewRequest("POST", "/api/v1/auth/login", bytes.NewBuffer([]byte("invalid json")))
		req.Header.Set("Content-Type", "application/json")

		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
		
		var errorResp ErrorResponse
		err := json.Unmarshal(w.Body.Bytes(), &errorResp)
		require.NoError(t, err)
		assert.Equal(t, "Invalid request", errorResp.Error)
	})

	t.Run("NotFoundRoute", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/nonexistent", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusNotFound, w.Code)
	})
}

func TestConcurrentRequests(t *testing.T) {
	router, _, _ := setupTestGateway()
	
	t.Run("ConcurrentHealthChecks", func(t *testing.T) {
		const numRequests = 10
		results := make(chan int, numRequests)

		for i := 0; i < numRequests; i++ {
			go func() {
				req, _ := http.NewRequest("GET", "/health/", nil)
				w := httptest.NewRecorder()
				router.ServeHTTP(w, req)
				results <- w.Code
			}()
		}

		// Collect all results
		for i := 0; i < numRequests; i++ {
			statusCode := <-results
			assert.Equal(t, http.StatusOK, statusCode)
		}
	})
}

// Benchmark tests
func BenchmarkHealthEndpoint(b *testing.B) {
	router, _, _ := setupTestGateway()
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("GET", "/health/", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}

func BenchmarkSearchEndpoint(b *testing.B) {
	router, _, _ := setupTestGateway()
	
	searchReq := SearchRequest{
		Query: "benchmark test query",
		TopK:  3,
	}
	body, _ := json.Marshal(searchReq)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("POST", "/api/v1/search", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}

// Test helper function
func createTestUser(dbManager *MockDatabaseManager) *User {
	req := &RegisterRequest{
		Email:     "testuser@example.com",
		Password:  "hashedpass",
		FirstName: "Test",
		LastName:  "User",
		Phone:     "123-456-7890",
	}
	user, _ := dbManager.CreateUser(req)
	return user
}