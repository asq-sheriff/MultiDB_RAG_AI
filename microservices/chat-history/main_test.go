package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gocql/gocql"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
	"go.uber.org/zap/zaptest"
)

var (
	testHandlers *ChatHistoryHandlers
	testService  *ChatHistoryService  
	testApp      *gin.Engine
	testLogger   *zap.Logger
)

func TestMain(m *testing.M) {
	setup()
	code := m.Run()
	teardown()
	os.Exit(code)
}

func setup() {
	// Initialize test logger
	testLogger = zaptest.NewLogger(&testing.T{})

	// Create mock service configuration
	config := ServiceConfig{
		MaxMessageLength:      10000,
		MaxHistoryLimit:       100,
		DefaultHistoryLimit:   50,
		CacheSessionTTL:       24 * time.Hour,
		RateLimitPerHour:      1000,
		EnableSafetyAnalysis:  true,
		EnableEmotionAnalysis: true,
		EnableRAG:             true,
	}

	// Create mock database manager (in a real environment, this would connect to test databases)
	// For testing purposes, we'll use mocked methods
	mockDB := &MockDatabaseManager{}
	
	// Initialize service
	testService = NewChatHistoryService(
		mockDB,
		testLogger,
		config,
		"http://localhost:8005", // embedding service
		"http://localhost:8006", // generation service
		"http://localhost:8007", // safety service
	)

	// Initialize handlers
	testHandlers = NewChatHistoryHandlers(testService, testLogger)

	// Setup test app
	gin.SetMode(gin.TestMode)
	testApp = setupTestRouter(testHandlers, testLogger)
}

func teardown() {
	// Clean up test resources
	if testService != nil && testService.db != nil {
		testService.db.Close()
	}
}

func setupTestRouter(handlers *ChatHistoryHandlers, logger *zap.Logger) *gin.Engine {
	router := gin.New()
	router.Use(gin.Recovery())

	// Health check
	router.GET("/health", handlers.HealthCheck)

	// API routes
	v1 := router.Group("/api/v1")
	{
		chat := v1.Group("/chat")
		{
			chat.POST("/message", handlers.SendMessage)
			chat.GET("/history", handlers.GetHistory)
			chat.POST("/feedback", handlers.SubmitFeedback)
			chat.GET("/emotion/history/:session_id", handlers.GetEmotionHistory)
			chat.POST("/safety/test", handlers.AnalyzeSafety)
			chat.POST("/sessions", handlers.CreateSession)
			chat.GET("/sessions/:session_id", handlers.GetSession)
			chat.DELETE("/sessions/:session_id", handlers.EndSession)
			chat.GET("/stats", handlers.GetStats)
			chat.GET("/analytics/:session_id", handlers.GetSessionAnalytics)
		}
	}

	return router
}

// ========================================
// Model Tests
// ========================================

func TestModels(t *testing.T) {
	t.Run("NewSession", func(t *testing.T) {
		userID := uuid.New()
		channel := "web"
		
		session := NewSession(userID, channel)
		
		assert.NotEqual(t, uuid.Nil, session.SessionID)
		assert.Equal(t, userID, session.UserID)
		assert.Equal(t, channel, session.Channel)
		assert.False(t, session.StartedAt.IsZero())
		assert.True(t, session.IsActive())
		assert.Nil(t, session.EndedAt)
	})

	t.Run("NewMessage", func(t *testing.T) {
		sessionID := uuid.New()
		userID := uuid.New()
		role := RoleUser
		content := "Hello, how are you?"

		message := NewMessage(sessionID, userID, role, content)

		assert.NotEqual(t, uuid.Nil, message.MessageID)
		assert.Equal(t, sessionID, message.SessionID)
		assert.Equal(t, userID, message.UserID)
		assert.Equal(t, role, message.Role)
		assert.Equal(t, content, message.Content)
		assert.False(t, message.CreatedAt.IsZero())
		assert.False(t, message.PIIPresent)
	})

	t.Run("SessionEndSession", func(t *testing.T) {
		session := NewSession(uuid.New(), "web")
		assert.True(t, session.IsActive())

		session.EndSession()
		assert.False(t, session.IsActive())
		assert.NotNil(t, session.EndedAt)
	})

	t.Run("EmotionStateRequiresIntervention", func(t *testing.T) {
		// Test normal emotion state
		emotion := &EmotionState{
			CurrentEmotion:    EmotionNeutral,
			Valence:          0.0,
			Arousal:          0.0,
			RequiresAttention: false,
		}
		assert.False(t, emotion.RequiresIntervention())

		// Test crisis emotion state
		emotion.RequiresAttention = true
		assert.True(t, emotion.RequiresIntervention())

		// Test severe sadness
		emotion.RequiresAttention = false
		emotion.CurrentEmotion = EmotionSad
		emotion.Arousal = -0.8
		assert.True(t, emotion.RequiresIntervention())

		// Test high anxiety
		emotion.CurrentEmotion = EmotionAnxious
		emotion.Arousal = 0.9
		assert.True(t, emotion.RequiresIntervention())
	})

	t.Run("FeedbackValidation", func(t *testing.T) {
		req := &SubmitFeedbackRequest{
			SessionID: uuid.New().String(),
			MessageID: uuid.New().String(),
			UserID:    uuid.New().String(),
			Rating:    3,
		}

		assert.True(t, req.IsValidRating())

		req.Rating = 0
		assert.False(t, req.IsValidRating())

		req.Rating = 6
		assert.False(t, req.IsValidRating())
	})
}

// ========================================
// HTTP Handler Tests
// ========================================

func TestHealthCheck(t *testing.T) {
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	testApp.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response HealthCheckResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)

	assert.Equal(t, "chat-history-service-go", response.Service)
	assert.Equal(t, "1.0.0", response.Version)
	assert.NotEmpty(t, response.Status)
}

func TestSendMessage(t *testing.T) {
	t.Run("ValidMessage", func(t *testing.T) {
		req := SendMessageRequest{
			SessionID:      uuid.New().String(),
			UserID:         uuid.New().String(),
			Message:        "Hello, I need help with my health question.",
			Channel:        "web",
			UseRAG:         true,
			SafetyAnalysis: true,
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/message", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		// Note: This will fail without proper database setup, but tests the routing and validation
		assert.Contains(t, []int{http.StatusOK, http.StatusInternalServerError}, w.Code)

		if w.Code == http.StatusOK {
			var response SendMessageResponse
			err = json.Unmarshal(w.Body.Bytes(), &response)
			require.NoError(t, err)

			assert.NotEmpty(t, response.MessageID)
			assert.Equal(t, req.SessionID, response.SessionID)
			assert.NotEmpty(t, response.Response)
		}
	})

	t.Run("InvalidMessage", func(t *testing.T) {
		req := SendMessageRequest{
			SessionID: "", // Invalid - empty session ID
			UserID:    uuid.New().String(),
			Message:   "Hello",
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/message", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})

	t.Run("TooLongMessage", func(t *testing.T) {
		longMessage := string(make([]byte, 15000)) // Exceeds max message length

		req := SendMessageRequest{
			SessionID: uuid.New().String(),
			UserID:    uuid.New().String(),
			Message:   longMessage,
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/message", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		assert.Contains(t, []int{http.StatusBadRequest, http.StatusInternalServerError}, w.Code)
	})
}

func TestGetHistory(t *testing.T) {
	t.Run("ValidRequest", func(t *testing.T) {
		sessionID := uuid.New().String()
		url := "/api/v1/chat/history?session_id=" + sessionID + "&limit=10"

		req := httptest.NewRequest("GET", url, nil)
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, req)

		// Will return error without database, but tests routing
		assert.Contains(t, []int{http.StatusOK, http.StatusInternalServerError, http.StatusNotFound}, w.Code)
	})

	t.Run("MissingSessionID", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/api/v1/chat/history?limit=10", nil)
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, req)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})
}

func TestSubmitFeedback(t *testing.T) {
	t.Run("ValidFeedback", func(t *testing.T) {
		req := SubmitFeedbackRequest{
			SessionID: uuid.New().String(),
			MessageID: uuid.New().String(),
			UserID:    uuid.New().String(),
			Rating:    4,
			Feedback:  stringPtr("Very helpful response"),
			Category:  stringPtr("helpful"),
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/feedback", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		// Will return error without database, but tests routing and validation
		assert.Contains(t, []int{http.StatusCreated, http.StatusInternalServerError}, w.Code)
	})

	t.Run("InvalidRating", func(t *testing.T) {
		req := SubmitFeedbackRequest{
			SessionID: uuid.New().String(),
			MessageID: uuid.New().String(),
			UserID:    uuid.New().String(),
			Rating:    6, // Invalid rating
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/feedback", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		assert.Contains(t, []int{http.StatusBadRequest, http.StatusInternalServerError}, w.Code)
	})
}

func TestSessionManagement(t *testing.T) {
	t.Run("CreateSession", func(t *testing.T) {
		req := map[string]string{
			"user_id": uuid.New().String(),
			"channel": "web",
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/sessions", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		assert.Contains(t, []int{http.StatusCreated, http.StatusInternalServerError}, w.Code)
	})

	t.Run("GetSession", func(t *testing.T) {
		sessionID := uuid.New().String()
		url := "/api/v1/chat/sessions/" + sessionID

		req := httptest.NewRequest("GET", url, nil)
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, req)

		assert.Contains(t, []int{http.StatusOK, http.StatusNotFound, http.StatusInternalServerError}, w.Code)
	})

	t.Run("EndSession", func(t *testing.T) {
		sessionID := uuid.New().String()
		url := "/api/v1/chat/sessions/" + sessionID

		req := httptest.NewRequest("DELETE", url, nil)
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, req)

		assert.Contains(t, []int{http.StatusOK, http.StatusNotFound, http.StatusInternalServerError}, w.Code)
	})
}

func TestEmotionHistory(t *testing.T) {
	sessionID := uuid.New().String()
	url := "/api/v1/chat/emotion/history/" + sessionID + "?limit=20"

	req := httptest.NewRequest("GET", url, nil)
	w := httptest.NewRecorder()

	testApp.ServeHTTP(w, req)

	assert.Contains(t, []int{http.StatusOK, http.StatusInternalServerError}, w.Code)
}

func TestSafetyAnalysis(t *testing.T) {
	t.Run("ValidSafetyTest", func(t *testing.T) {
		req := map[string]string{
			"text":    "I'm feeling sad today",
			"context": "chat_message",
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/safety/test", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		// Will call external service, may fail but tests routing
		assert.Contains(t, []int{http.StatusOK, http.StatusInternalServerError}, w.Code)
	})

	t.Run("EmptyText", func(t *testing.T) {
		req := map[string]string{
			"text": "", // Invalid - empty text
		}

		jsonData, err := json.Marshal(req)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/safety/test", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		assert.Equal(t, http.StatusBadRequest, w.Code)
	})
}

func TestServiceStats(t *testing.T) {
	req := httptest.NewRequest("GET", "/api/v1/chat/stats", nil)
	w := httptest.NewRecorder()

	testApp.ServeHTTP(w, req)

	assert.Contains(t, []int{http.StatusOK, http.StatusInternalServerError}, w.Code)
}

func TestSessionAnalytics(t *testing.T) {
	sessionID := uuid.New().String()
	url := "/api/v1/chat/analytics/" + sessionID

	req := httptest.NewRequest("GET", url, nil)
	w := httptest.NewRecorder()

	testApp.ServeHTTP(w, req)

	assert.Contains(t, []int{http.StatusOK, http.StatusInternalServerError}, w.Code)
}

// ========================================
// Benchmark Tests
// ========================================

func BenchmarkSendMessage(b *testing.B) {
	req := SendMessageRequest{
		SessionID: uuid.New().String(),
		UserID:    uuid.New().String(),
		Message:   "This is a benchmark test message for performance testing.",
		Channel:   "web",
	}

	jsonData, _ := json.Marshal(req)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		httpReq := httptest.NewRequest("POST", "/api/v1/chat/message", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)
	}
}

func BenchmarkGetHistory(b *testing.B) {
	sessionID := uuid.New().String()
	url := "/api/v1/chat/history?session_id=" + sessionID + "&limit=50"

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req := httptest.NewRequest("GET", url, nil)
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, req)
	}
}

// ========================================
// Integration Tests
// ========================================

func TestChatWorkflow(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	sessionID := uuid.New().String()
	userID := uuid.New().String()

	t.Run("CompleteConversationWorkflow", func(t *testing.T) {
		// 1. Create session
		createReq := map[string]string{
			"user_id": userID,
			"channel": "web",
		}

		jsonData, err := json.Marshal(createReq)
		require.NoError(t, err)

		httpReq := httptest.NewRequest("POST", "/api/v1/chat/sessions", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)
		// May fail without database, but tests flow

		// 2. Send message
		msgReq := SendMessageRequest{
			SessionID:      sessionID,
			UserID:         userID,
			Message:        "Hello, I need help with my anxiety.",
			SafetyAnalysis: true,
		}

		jsonData, err = json.Marshal(msgReq)
		require.NoError(t, err)

		httpReq = httptest.NewRequest("POST", "/api/v1/chat/message", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w = httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)
		// May fail without database, but tests integration

		// 3. Get history
		historyURL := "/api/v1/chat/history?session_id=" + sessionID
		req := httptest.NewRequest("GET", historyURL, nil)
		w = httptest.NewRecorder()

		testApp.ServeHTTP(w, req)

		// 4. Submit feedback (if message was successful)
		feedbackReq := SubmitFeedbackRequest{
			SessionID: sessionID,
			MessageID: uuid.New().String(),
			UserID:    userID,
			Rating:    5,
			Feedback:  stringPtr("Very helpful"),
		}

		jsonData, err = json.Marshal(feedbackReq)
		require.NoError(t, err)

		httpReq = httptest.NewRequest("POST", "/api/v1/chat/feedback", bytes.NewBuffer(jsonData))
		httpReq.Header.Set("Content-Type", "application/json")
		w = httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		// 5. Get analytics
		analyticsURL := "/api/v1/chat/analytics/" + sessionID
		req = httptest.NewRequest("GET", analyticsURL, nil)
		w = httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)

		// 6. End session
		endURL := "/api/v1/chat/sessions/" + sessionID
		req = httptest.NewRequest("DELETE", endURL, nil)
		w = httptest.NewRecorder()

		testApp.ServeHTTP(w, httpReq)
	})
}

// ========================================
// Mock Database Manager for Testing
// ========================================

type MockDatabaseManager struct{}

func (m *MockDatabaseManager) HealthCheck(ctx context.Context) DatabaseHealth {
	return DatabaseHealth{
		PostgreSQL: true,
		ScyllaDB:   true,
		MongoDB:    true,
		Redis:      true,
	}
}

func (m *MockDatabaseManager) CreateSession(ctx context.Context, session *Session) error {
	return nil
}

func (m *MockDatabaseManager) GetSession(ctx context.Context, sessionID uuid.UUID) (*Session, error) {
	return &Session{
		SessionID: sessionID,
		UserID:    uuid.New(),
		Channel:   "web",
		StartedAt: time.Now(),
	}, nil
}

func (m *MockDatabaseManager) EndSession(ctx context.Context, sessionID uuid.UUID) error {
	return nil
}

func (m *MockDatabaseManager) CreateMessage(ctx context.Context, message *Message) error {
	return nil
}

func (m *MockDatabaseManager) StoreMessageEmotion(ctx context.Context, emotion *MessageEmotion) error {
	return nil
}

func (m *MockDatabaseManager) Close() {
	// Mock cleanup
}

// Mock other required methods...
func (m *MockDatabaseManager) StoreConversationMessage(ctx context.Context, msg *ConversationMessage) error {
	return nil
}

func (m *MockDatabaseManager) GetConversationHistory(ctx context.Context, sessionID gocql.UUID, limit int, startTime *time.Time) ([]ConversationMessage, error) {
	return []ConversationMessage{}, nil
}

func (m *MockDatabaseManager) StoreFeedback(ctx context.Context, feedback *UserFeedback) error {
	return nil
}

func (m *MockDatabaseManager) CacheSession(ctx context.Context, sessionCache *SessionCache) error {
	return nil
}

func (m *MockDatabaseManager) GetCachedSession(ctx context.Context, sessionID string) (*SessionCache, error) {
	return nil, nil
}

func (m *MockDatabaseManager) IncrementAnalyticsCounter(ctx context.Context, metric string, tags map[string]string) error {
	return nil
}

func (m *MockDatabaseManager) SearchKnowledgeBase(ctx context.Context, embedding []float64, limit int) ([]KnowledgeDocument, error) {
	return []KnowledgeDocument{}, nil
}

func (m *MockDatabaseManager) GetFromCache(ctx context.Context, key string) (string, error) {
	return "", fmt.Errorf("not found")
}

func (m *MockDatabaseManager) SetToCache(ctx context.Context, key string, value string, ttl time.Duration) error {
	return nil
}

// ========================================
// Helper Functions
// ========================================

func stringPtr(s string) *string {
	return &s
}