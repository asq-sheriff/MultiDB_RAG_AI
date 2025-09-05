package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/shopspring/decimal"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap/zaptest"
)

var (
	testDB    *DatabaseManager
	testCache *RedisCache
	testApp   *gin.Engine
)

func TestMain(m *testing.M) {
	setup()
	code := m.Run()
	teardown()
	os.Exit(code)
}

func setup() {
	// Initialize test logger
	logger := zaptest.NewLogger(&testing.T{})

	// Initialize test database connection (using SQLite for testing)
	databaseURL := os.Getenv("TEST_DATABASE_URL")
	if databaseURL == "" {
		databaseURL = ":memory:" // Use in-memory SQLite database for testing
	}

	var err error
	testDB, err = NewDatabaseManager(databaseURL, logger)
	if err != nil {
		panic(fmt.Sprintf("Failed to connect to test database: %v", err))
	}

	// Initialize database tables for testing
	if err := testDB.InitializeTables(); err != nil {
		panic(fmt.Sprintf("Failed to initialize test database tables: %v", err))
	}

	// Initialize test Redis connection
	redisURL := os.Getenv("TEST_REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379/1" // Use database 1 for tests
	}

	testCache, err = NewRedisCache(redisURL, logger)
	if err != nil {
		panic(fmt.Sprintf("Failed to connect to test Redis: %v", err))
	}

	// Initialize test app
	gin.SetMode(gin.TestMode)
	handlers := NewBillingHandlers(testDB, testCache, logger)
	
	config := Config{
		Environment:   "test",
		EnableMetrics: false,
	}
	
	testApp = setupRouter(handlers, logger, config)
}

func teardown() {
	if testDB != nil {
		testDB.Close()
	}
	if testCache != nil {
		testCache.Close()
	}
}

func cleanupTestData() {
	// Clean up test data between tests
	ctx := context.Background()
	
	// Clear Redis test database
	testCache.client.FlushDB(ctx)
	
	// Clean up database tables (in dependency order) - SQLite compatible
	tables := []string{"usage_records", "subscriptions", "users"}
	for _, table := range tables {
		// For testing, we'll clean all test data (or you could use a more specific condition)
		testDB.db.Exec(fmt.Sprintf("DELETE FROM %s WHERE id LIKE 'test-%%'", table))
	}
}

func createTestUser(t *testing.T) uuid.UUID {
	userID := uuid.New()
	
	query := `
		INSERT INTO users (id, email, subscription_plan, created_at, updated_at)
		VALUES ($1, $2, $3, NOW(), NOW())
	`
	_, err := testDB.db.Exec(testDB.ConvertQuery(query), userID, fmt.Sprintf("test-%s@example.com", userID.String()[:8]), "free")
	
	require.NoError(t, err)
	return userID
}

// Test Plan Definitions
func TestGetPlanDefinitions(t *testing.T) {
	plans := GetPlanDefinitions()
	
	assert.Len(t, plans, 4, "Should have 4 plan definitions")
	
	planIDs := make([]string, len(plans))
	for i, plan := range plans {
		planIDs[i] = plan.ID
	}
	
	expectedPlans := []string{"free", "basic", "premium", "enterprise"}
	for _, expectedPlan := range expectedPlans {
		assert.Contains(t, planIDs, expectedPlan, "Should contain plan: %s", expectedPlan)
	}
}

func TestGetPlanDefinition(t *testing.T) {
	// Test valid plan
	freePlan := GetPlanDefinition("free")
	require.NotNil(t, freePlan)
	assert.Equal(t, "free", freePlan.ID)
	assert.Equal(t, "Free Plan", freePlan.Name)
	
	// Test invalid plan
	invalidPlan := GetPlanDefinition("nonexistent")
	assert.Nil(t, invalidPlan)
}

// Test API Endpoints
func TestHealthCheck(t *testing.T) {
	cleanupTestData()
	
	req, _ := http.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, "healthy", response["status"])
	assert.Equal(t, "billing-service-go", response["service"])
}

func TestGetAvailablePlans(t *testing.T) {
	cleanupTestData()
	
	req, _ := http.NewRequest("GET", "/api/v1/plans", nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify response structure
	responseData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	
	plans, ok := responseData["plans"].([]interface{})
	require.True(t, ok)
	assert.Len(t, plans, 4)
}

func TestCreateSubscription(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	requestBody := SubscriptionCreateRequest{
		PlanType:     "basic",
		BillingCycle: "monthly",
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", fmt.Sprintf("/api/v1/users/%s/subscription", userID), bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	assert.Equal(t, "Subscription created successfully", response.Message)
}

func TestGetUserSubscription(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// First create a subscription
	_, err := testDB.CreateSubscription(userID, "premium", "yearly")
	require.NoError(t, err)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/subscription", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify subscription data
	subscriptionData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Equal(t, "premium", subscriptionData["plan_type"])
	assert.Equal(t, "yearly", subscriptionData["billing_cycle"])
}

func TestUpdateSubscription(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Create initial subscription
	_, err := testDB.CreateSubscription(userID, "basic", "monthly")
	require.NoError(t, err)
	
	// Update subscription
	requestBody := SubscriptionUpdateRequest{
		PlanType:     "premium",
		BillingCycle: "yearly",
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("PUT", fmt.Sprintf("/api/v1/users/%s/subscription", userID), bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	assert.Equal(t, "Subscription updated successfully", response.Message)
}

func TestRecordUsage(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	requestBody := UsageRecordRequest{
		ResourceType: "messages",
		Quantity:     5,
		ExtraData: map[string]interface{}{
			"endpoint": "chat",
			"model":    "gpt-3.5-turbo",
		},
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", fmt.Sprintf("/api/v1/users/%s/usage", userID), bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	assert.Equal(t, "Usage recorded successfully", response.Message)
}

func TestCheckQuota(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Create a subscription first
	_, err := testDB.CreateSubscription(userID, "basic", "monthly")
	require.NoError(t, err)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/quota/messages", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify quota data structure
	quotaData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Contains(t, quotaData, "has_quota")
	assert.Contains(t, quotaData, "max_allowed")
	assert.Contains(t, quotaData, "current_usage")
}

func TestGetUsageSummary(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Create subscription and record some usage
	_, err := testDB.CreateSubscription(userID, "premium", "monthly")
	require.NoError(t, err)
	
	err = testDB.RecordUsage(userID, "messages", 10, nil)
	require.NoError(t, err)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/usage/summary", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify usage summary structure
	summaryData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Contains(t, summaryData, "messages_this_month")
	assert.Contains(t, summaryData, "plan_type")
}

// Test Database Operations
func TestDatabaseOperations(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	t.Run("CreateSubscription", func(t *testing.T) {
		subscription, err := testDB.CreateSubscription(userID, "basic", "monthly")
		require.NoError(t, err)
		assert.Equal(t, userID, subscription.UserID)
		assert.Equal(t, "basic", subscription.PlanType)
		assert.Equal(t, "monthly", subscription.BillingCycle)
		assert.Equal(t, "active", subscription.Status)
	})
	
	t.Run("GetActiveSubscription", func(t *testing.T) {
		subscription, err := testDB.GetActiveSubscription(userID)
		require.NoError(t, err)
		require.NotNil(t, subscription)
		assert.Equal(t, "basic", subscription.PlanType)
	})
	
	t.Run("RecordUsage", func(t *testing.T) {
		err := testDB.RecordUsage(userID, "messages", 5, map[string]interface{}{
			"test": "data",
		})
		require.NoError(t, err)
	})
	
	t.Run("CheckQuota", func(t *testing.T) {
		quota, err := testDB.CheckQuota(userID, "messages")
		require.NoError(t, err)
		require.NotNil(t, quota)
		assert.True(t, quota.HasQuota)
		assert.Equal(t, 1000, quota.MaxAllowed) // Basic plan limit
		assert.Equal(t, 5, quota.CurrentUsage)  // From recorded usage
	})
}

// Test Cache Operations
func TestCacheOperations(t *testing.T) {
	cleanupTestData()
	userID := uuid.New()
	
	subscription := &Subscription{
		ID:           uuid.New(),
		UserID:       userID,
		PlanType:     "premium",
		Status:       "active",
		BillingCycle: "monthly",
		AmountCents:  2999,
		Currency:     "USD",
		StartedAt:    time.Now(),
		AutoRenew:    true,
		Limits:       map[string]int{"messages": 5000},
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}
	
	t.Run("CacheSubscription", func(t *testing.T) {
		err := testCache.CacheSubscription(userID, subscription, 10*time.Minute)
		require.NoError(t, err)
	})
	
	t.Run("GetCachedSubscription", func(t *testing.T) {
		cached, err := testCache.GetCachedSubscription(userID)
		require.NoError(t, err)
		require.NotNil(t, cached)
		assert.Equal(t, subscription.PlanType, cached.PlanType)
		assert.Equal(t, subscription.UserID, cached.UserID)
	})
	
	t.Run("InvalidateSubscriptionCache", func(t *testing.T) {
		err := testCache.InvalidateSubscriptionCache(userID)
		require.NoError(t, err)
		
		// Verify cache is cleared
		cached, err := testCache.GetCachedSubscription(userID)
		require.NoError(t, err)
		assert.Nil(t, cached)
	})
	
	t.Run("RateLimit", func(t *testing.T) {
		key := fmt.Sprintf("test_rate_limit_%s", uuid.New().String()[:8])
		
		// First request should be allowed
		allowed, err := testCache.CheckRateLimit(key, 2, time.Minute)
		require.NoError(t, err)
		assert.True(t, allowed)
		
		// Second request should be allowed
		allowed, err = testCache.CheckRateLimit(key, 2, time.Minute)
		require.NoError(t, err)
		assert.True(t, allowed)
		
		// Third request should be rate limited
		allowed, err = testCache.CheckRateLimit(key, 2, time.Minute)
		require.NoError(t, err)
		assert.False(t, allowed)
	})
}

// Test Error Handling
func TestErrorHandling(t *testing.T) {
	cleanupTestData()
	
	t.Run("InvalidUserID", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/users/invalid-uuid/subscription", nil)
		w := httptest.NewRecorder()
		testApp.ServeHTTP(w, req)
		
		assert.Equal(t, http.StatusBadRequest, w.Code)
		
		var response APIResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.False(t, response.Success)
		assert.Equal(t, "Invalid user ID format", response.Error)
	})
	
	t.Run("NonexistentUser", func(t *testing.T) {
		nonexistentUserID := uuid.New()
		req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/subscription", nonexistentUserID), nil)
		w := httptest.NewRecorder()
		testApp.ServeHTTP(w, req)
		
		assert.Equal(t, http.StatusNotFound, w.Code)
	})
	
	t.Run("InvalidPlanType", func(t *testing.T) {
		userID := createTestUser(t)
		
		requestBody := SubscriptionCreateRequest{
			PlanType:     "nonexistent",
			BillingCycle: "monthly",
		}
		
		requestJSON, _ := json.Marshal(requestBody)
		req, _ := http.NewRequest("POST", fmt.Sprintf("/api/v1/users/%s/subscription", userID), bytes.NewBuffer(requestJSON))
		req.Header.Set("Content-Type", "application/json")
		
		w := httptest.NewRecorder()
		testApp.ServeHTTP(w, req)
		
		assert.Equal(t, http.StatusBadRequest, w.Code)
		
		var response APIResponse
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.False(t, response.Success)
		assert.Equal(t, "Invalid plan type", response.Error)
	})
}

// Benchmark tests
func BenchmarkGetSubscription(b *testing.B) {
	cleanupTestData()
	userID := createTestUser(&testing.T{})
	_, err := testDB.CreateSubscription(userID, "basic", "monthly")
	require.NoError(&testing.T{}, err)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/subscription", userID), nil)
		w := httptest.NewRecorder()
		testApp.ServeHTTP(w, req)
		
		if w.Code != http.StatusOK {
			b.Fatalf("Expected status 200, got %d", w.Code)
		}
	}
}

func BenchmarkRecordUsage(b *testing.B) {
	cleanupTestData()
	userID := createTestUser(&testing.T{})
	
	requestBody := UsageRecordRequest{
		ResourceType: "messages",
		Quantity:     1,
	}
	requestJSON, _ := json.Marshal(requestBody)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("POST", fmt.Sprintf("/api/v1/users/%s/usage", userID), bytes.NewBuffer(requestJSON))
		req.Header.Set("Content-Type", "application/json")
		
		w := httptest.NewRecorder()
		testApp.ServeHTTP(w, req)
		
		if w.Code != http.StatusOK {
			b.Fatalf("Expected status 200, got %d", w.Code)
		}
	}
}

// Additional tests to boost coverage

func TestGetDetailedUsage(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Create subscription and record some usage
	_, err := testDB.CreateSubscription(userID, "premium", "monthly")
	require.NoError(t, err)
	
	// Record multiple usage entries
	for i := 0; i < 5; i++ {
		err = testDB.RecordUsage(userID, "messages", 2, map[string]interface{}{
			"batch": i,
			"type": "conversation",
		})
		require.NoError(t, err)
	}
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/usage/detailed", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify detailed usage structure
	detailedData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Contains(t, detailedData, "usage_by_type")
	assert.Contains(t, detailedData, "total_records")
	assert.Equal(t, float64(5), detailedData["total_records"])
}

func TestGetDetailedUsageWithDateRange(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Record usage
	err := testDB.RecordUsage(userID, "api_calls", 3, nil)
	require.NoError(t, err)
	
	// Test with date parameters
	now := time.Now()
	startDate := now.AddDate(0, 0, -7).Format(time.RFC3339)
	endDate := now.Format(time.RFC3339)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/usage/detailed?start_date=%s&end_date=%s&limit=10", 
		userID, startDate, endDate), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
}

func TestGetBillingHistory(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Create multiple subscriptions to generate billing history
	_, err := testDB.CreateSubscription(userID, "basic", "monthly")
	require.NoError(t, err)
	
	_, err = testDB.CreateSubscription(userID, "premium", "yearly")
	require.NoError(t, err)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/billing/history", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	
	// Verify billing history structure
	historyData, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.Contains(t, historyData, "total")
	assert.Contains(t, historyData, "items")
}

func TestGetBillingHistoryWithLimit(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Create subscription
	_, err := testDB.CreateSubscription(userID, "enterprise", "monthly")
	require.NoError(t, err)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/users/%s/billing/history?limit=5", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
}

func TestCancelSubscription(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// First create a subscription
	_, err := testDB.CreateSubscription(userID, "premium", "monthly")
	require.NoError(t, err)
	
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("/api/v1/users/%s/subscription", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response.Success)
	assert.Equal(t, "Subscription cancelled successfully", response.Message)
}

func TestCancelSubscription_NoActiveSubscription(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("/api/v1/users/%s/subscription", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusInternalServerError, w.Code)
	
	var response APIResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.False(t, response.Success)
	assert.Equal(t, "Failed to cancel subscription", response.Error)
}

func TestCancelFreePlan(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Create free subscription
	_, err := testDB.CreateSubscription(userID, "free", "monthly")
	require.NoError(t, err)
	
	req, _ := http.NewRequest("DELETE", fmt.Sprintf("/api/v1/users/%s/subscription", userID), nil)
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusInternalServerError, w.Code)
	
	var response APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.False(t, response.Success)
	assert.Equal(t, "Failed to cancel subscription", response.Error)
}

// Test comprehensive plan definitions
func TestPlanDefinitions(t *testing.T) {
	plans := GetPlanDefinitions()
	
	// Verify each plan has required fields
	for _, plan := range plans {
		assert.NotEmpty(t, plan.ID)
		assert.NotEmpty(t, plan.Name)
		assert.NotNil(t, plan.Limits)
		assert.NotEmpty(t, plan.Features)
		assert.NotNil(t, plan.Pricing)
		
		// Verify limits structure
		assert.Contains(t, plan.Limits, "messages")
		assert.Contains(t, plan.Limits, "api_calls")
		assert.Contains(t, plan.Limits, "background_tasks")
		
		// Verify pricing structure
		assert.Contains(t, plan.Pricing, "monthly")
		assert.Contains(t, plan.Pricing, "yearly")
	}
}

func TestPlanPricing(t *testing.T) {
	testCases := []struct {
		planType    string
		cycle       string
		expectValid bool
	}{
		{"free", "monthly", true},
		{"free", "yearly", true},
		{"basic", "monthly", true},
		{"basic", "yearly", true},
		{"premium", "monthly", true},
		{"premium", "yearly", true},
		{"enterprise", "monthly", true},
		{"enterprise", "yearly", true},
		{"invalid", "monthly", false},
		{"basic", "invalid", false},
	}
	
	for _, tc := range testCases {
		t.Run(fmt.Sprintf("%s_%s", tc.planType, tc.cycle), func(t *testing.T) {
			pricing := GetPlanPricing(tc.planType, tc.cycle)
			if tc.expectValid {
				assert.True(t, pricing.GreaterThanOrEqual(decimal.Zero))
			} else {
				assert.True(t, pricing.IsZero())
			}
		})
	}
}

func TestPlanLimits(t *testing.T) {
	testCases := []string{"free", "basic", "premium", "enterprise"}
	
	for _, planType := range testCases {
		t.Run(planType, func(t *testing.T) {
			limits := GetPlanLimits(planType)
			
			assert.Contains(t, limits, "messages")
			assert.Contains(t, limits, "api_calls")
			assert.Contains(t, limits, "background_tasks")
			
			// Verify limits are reasonable for free plan
			if planType == "free" {
				// Free plan should have limited messages
				assert.True(t, limits["messages"] > 0 && limits["messages"] <= 1000)
			}
			if planType == "enterprise" {
				// Enterprise should have unlimited or very high limits
				assert.True(t, limits["messages"] == -1 || limits["messages"] >= 50000)
			}
		})
	}
}

// Test middleware and handlers edge cases
func TestRateLimitMiddleware(t *testing.T) {
	cleanupTestData()
	
	// Create test router with rate limiting
	gin.SetMode(gin.TestMode)
	router := gin.New()
	handlers := NewBillingHandlers(testDB, testCache, zaptest.NewLogger(t))
	
	router.Use(handlers.RateLimitMiddleware())
	router.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"message": "success"})
	})
	
	// Make multiple requests to test rate limiting
	for i := 0; i < 5; i++ {
		req, _ := http.NewRequest("GET", "/test", nil)
		req.Header.Set("X-User-ID", "test-user")
		
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
		
		if i < 4 {
			assert.Equal(t, http.StatusOK, w.Code)
		}
	}
}

func TestInvalidJSONRequests(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	testCases := []struct {
		name     string
		method   string
		path     string
		body     string
		expected int
	}{
		{
			name:     "Invalid JSON for subscription creation",
			method:   "POST",
			path:     fmt.Sprintf("/api/v1/users/%s/subscription", userID),
			body:     `{"invalid": json}`,
			expected: http.StatusBadRequest,
		},
		{
			name:     "Invalid JSON for subscription update",
			method:   "PUT",
			path:     fmt.Sprintf("/api/v1/users/%s/subscription", userID),
			body:     `{invalid json`,
			expected: http.StatusBadRequest,
		},
		{
			name:     "Invalid JSON for usage recording",
			method:   "POST",
			path:     fmt.Sprintf("/api/v1/users/%s/usage", userID),
			body:     `{"resource_type":}`,
			expected: http.StatusBadRequest,
		},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			req, _ := http.NewRequest(tc.method, tc.path, strings.NewReader(tc.body))
			req.Header.Set("Content-Type", "application/json")
			
			w := httptest.NewRecorder()
			testApp.ServeHTTP(w, req)
			
			assert.Equal(t, tc.expected, w.Code)
		})
	}
}

func TestDatabaseConnectionHandling(t *testing.T) {
	// Test database ping functionality
	err := testDB.Ping()
	assert.NoError(t, err)
	
	// Test cache ping functionality
	err = testCache.Ping()
	assert.NoError(t, err)
}

func TestUsageRecordingEdgeCases(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Test recording usage with zero quantity
	requestBody := UsageRecordRequest{
		ResourceType: "messages",
		Quantity:     0,
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", fmt.Sprintf("/api/v1/users/%s/usage", userID), bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	// Should fail validation due to min=1 constraint
	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestSubscriptionCreationEdgeCases(t *testing.T) {
	cleanupTestData()
	userID := createTestUser(t)
	
	// Test creating subscription without required fields
	requestBody := SubscriptionCreateRequest{
		PlanType: "", // Missing required field
	}
	
	requestJSON, _ := json.Marshal(requestBody)
	req, _ := http.NewRequest("POST", fmt.Sprintf("/api/v1/users/%s/subscription", userID), bytes.NewBuffer(requestJSON))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	testApp.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
}