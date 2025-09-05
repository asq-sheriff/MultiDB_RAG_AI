// Package main provides comprehensive tests for the User Subscription Service
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

// Mock implementations for testing

// MockDatabaseManager mocks the database manager
type MockDatabaseManager struct {
	mock.Mock
	subscriptions map[uuid.UUID]*Subscription
	usage         []Usage
	DB            *gorm.DB
	RedisClient   *redis.Client
}

// NewMockDatabaseManager creates a new mock database manager
func NewMockDatabaseManager() *MockDatabaseManager {
	// Create in-memory SQLite database for testing
	db, _ := gorm.Open(sqlite.Open(":memory:"), &gorm.Config{})
	
	// Auto-migrate tables
	db.AutoMigrate(&Subscription{}, &Usage{}, &SubscriptionEvent{}, &WebhookEvent{})

	return &MockDatabaseManager{
		subscriptions: make(map[uuid.UUID]*Subscription),
		usage:         make([]Usage, 0),
		DB:            db,
	}
}

func (m *MockDatabaseManager) GetSubscriptionByUserID(userID uuid.UUID) (*Subscription, error) {
	args := m.Called(userID)
	
	if sub, exists := m.subscriptions[userID]; exists {
		return sub, nil
	}
	
	return args.Get(0).(*Subscription), args.Error(1)
}

func (m *MockDatabaseManager) CreateSubscription(subscription *Subscription) error {
	args := m.Called(subscription)
	
	if subscription.ID == uuid.Nil {
		subscription.ID = uuid.New()
	}
	
	m.subscriptions[subscription.UserID] = subscription
	
	return args.Error(0)
}

func (m *MockDatabaseManager) UpdateSubscription(subscription *Subscription) error {
	args := m.Called(subscription)
	
	m.subscriptions[subscription.UserID] = subscription
	
	return args.Error(0)
}

func (m *MockDatabaseManager) CancelSubscription(userID uuid.UUID, reason string) error {
	args := m.Called(userID, reason)
	
	if sub, exists := m.subscriptions[userID]; exists {
		sub.Status = StatusCanceled
		now := time.Now().UTC()
		sub.CanceledAt = &now
	}
	
	return args.Error(0)
}

func (m *MockDatabaseManager) RecordUsage(userID uuid.UUID, resourceType ResourceType, quantity int, metadata map[string]interface{}) error {
	args := m.Called(userID, resourceType, quantity, metadata)
	
	usage := Usage{
		ID:           uuid.New(),
		UserID:       userID,
		ResourceType: resourceType,
		Quantity:     quantity,
		RecordedAt:   time.Now().UTC(),
	}
	
	m.usage = append(m.usage, usage)
	
	return args.Error(0)
}

func (m *MockDatabaseManager) CheckUserQuota(userID uuid.UUID, resourceType ResourceType) (*QuotaInfo, error) {
	args := m.Called(userID, resourceType)
	
	// Calculate usage for this user and resource type
	var totalUsage int
	for _, u := range m.usage {
		if u.UserID == userID && u.ResourceType == resourceType {
			totalUsage += u.Quantity
		}
	}
	
	// Get subscription or default to free
	var maxAllowed int
	if sub, exists := m.subscriptions[userID]; exists {
		maxAllowed = sub.GetLimit(resourceType)
	} else {
		maxAllowed = GetPlanDefaults(PlanFree)[string(resourceType)]
	}
	
	quotaInfo := &QuotaInfo{
		UserID:       userID,
		ResourceType: resourceType,
		CurrentUsage: totalUsage,
		MaxAllowed:   maxAllowed,
		Remaining:    maxAllowed - totalUsage,
		HasQuota:     totalUsage < maxAllowed,
		PlanType:     string(PlanFree),
	}
	
	if result := args.Get(0); result != nil {
		return result.(*QuotaInfo), args.Error(1)
	}
	
	return quotaInfo, args.Error(1)
}

func (m *MockDatabaseManager) GetUsageSummary(userID uuid.UUID, days int) (map[string]interface{}, error) {
	args := m.Called(userID, days)
	
	summary := map[string]interface{}{
		"user_id":     userID,
		"plan_type":   PlanFree,
		"total_usage": len(m.usage),
	}
	
	return summary, args.Error(1)
}

func (m *MockDatabaseManager) HealthCheck() map[string]interface{} {
	return map[string]interface{}{
		"postgresql": "healthy",
		"redis":      "healthy",
		"timestamp":  time.Now().UTC(),
	}
}

func (m *MockDatabaseManager) Close() error {
	return nil
}

func (m *MockDatabaseManager) GetCacheMetrics() map[string]*CacheStats {
	return make(map[string]*CacheStats)
}

func (m *MockDatabaseManager) FlushCache() error {
	return nil
}

func (m *MockDatabaseManager) WarmupCache() error {
	return nil
}

func (m *MockDatabaseManager) SetCacheEnabled(enabled bool) {
}

func (m *MockDatabaseManager) GetCache() *RedisCache {
	return nil
}

func (m *MockDatabaseManager) CreateEvent(event interface{}) error {
	return nil
}

func (m *MockDatabaseManager) GetDB() *gorm.DB {
	return m.DB
}

// Test Setup and Helpers

func setupTestRouter() (*gin.Engine, *MockDatabaseManager, *SubscriptionService) {
	gin.SetMode(gin.TestMode)
	
	mockDB := NewMockDatabaseManager()
	service := NewSubscriptionService(mockDB)
	handlers := NewSubscriptionHandlers(service)
	
	r := gin.New()
	handlers.RegisterRoutes(r)
	
	return r, mockDB, service
}

func createTestSubscription(userID uuid.UUID, planType SubscriptionPlan) *Subscription {
	return &Subscription{
		ID:           uuid.New(),
		UserID:       userID,
		PlanType:     planType,
		Status:       StatusActive,
		BillingCycle: CycleMonthly,
		StartedAt:    time.Now().UTC(),
		AmountCents:  4999,
		Currency:     "USD",
		AutoRenew:    true,
		Limits:       GetPlanFeatures(planType).Limits,
	}
}

// Unit Tests

func TestMain(m *testing.M) {
	// Setup test environment
	os.Setenv("ENVIRONMENT", "test")
	os.Setenv("POSTGRES_HOST", "localhost")
	os.Setenv("REDIS_HOST", "localhost")
	
	// Run tests
	code := m.Run()
	
	// Cleanup
	os.Exit(code)
}

func TestGetPlanDefaults(t *testing.T) {
	tests := []struct {
		plan     SubscriptionPlan
		expected map[string]int
	}{
		{
			plan: PlanFree,
			expected: map[string]int{
				"messages":         100,
				"api_calls":        500,
				"background_tasks": 10,
				"storage":          1024,
				"users":            1,
				"rag_searches":     50,
				"embeddings":       100,
			},
		},
		{
			plan: PlanPro,
			expected: map[string]int{
				"messages":         5000,
				"api_calls":        10000,
				"background_tasks": 100,
				"storage":          10240,
				"users":            5,
				"rag_searches":     1000,
				"embeddings":       2500,
			},
		},
		{
			plan: PlanEnterprise,
			expected: map[string]int{
				"messages":         50000,
				"api_calls":        100000,
				"background_tasks": 1000,
				"storage":          102400,
				"users":            50,
				"rag_searches":     10000,
				"embeddings":       25000,
			},
		},
	}

	for _, tt := range tests {
		t.Run(string(tt.plan), func(t *testing.T) {
			defaults := GetPlanDefaults(tt.plan)
			assert.Equal(t, tt.expected, defaults)
		})
	}
}

func TestSubscriptionIsActive(t *testing.T) {
	tests := []struct {
		name         string
		subscription *Subscription
		expected     bool
	}{
		{
			name: "Active subscription",
			subscription: &Subscription{
				Status:  StatusActive,
				EndsAt:  nil,
			},
			expected: true,
		},
		{
			name: "Expired subscription",
			subscription: &Subscription{
				Status:  StatusActive,
				EndsAt:  &[]time.Time{time.Now().UTC().Add(-24 * time.Hour)}[0],
			},
			expected: false,
		},
		{
			name: "Canceled subscription",
			subscription: &Subscription{
				Status:  StatusCanceled,
			},
			expected: false,
		},
		{
			name: "Trialing subscription",
			subscription: &Subscription{
				Status:      StatusTrialing,
				TrialEndsAt: &[]time.Time{time.Now().UTC().Add(24 * time.Hour)}[0],
			},
			expected: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.expected, tt.subscription.IsActive())
		})
	}
}

func TestSubscriptionGetLimit(t *testing.T) {
	subscription := &Subscription{
		PlanType: PlanPro,
		Limits: JSONMap{
			"messages": 5000.0,
			"api_calls": 10000.0,
		},
	}

	// Test getting limit from subscription
	assert.Equal(t, 5000, subscription.GetLimit(ResourceMessages))
	assert.Equal(t, 10000, subscription.GetLimit(ResourceAPICalls))
	
	// Test getting default limit when not in subscription
	assert.Equal(t, 100, subscription.GetLimit(ResourceBackgroundTasks))
}

// Integration Tests

func TestCreateSubscriptionAPI(t *testing.T) {
	router, mockDB, _ := setupTestRouter()
	
	userID := uuid.New()
	
	// Mock expectations
	mockDB.On("CreateSubscription", mock.AnythingOfType("*main.Subscription")).Return(nil)
	
	reqBody := CreateSubscriptionRequest{
		UserID:       userID.String(),
		PlanType:     string(PlanPro),
		BillingCycle: string(CycleMonthly),
	}
	
	body, _ := json.Marshal(reqBody)
	
	req, _ := http.NewRequest("POST", "/api/v1/subscriptions/", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response APIResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.True(t, response.Success)
	assert.Equal(t, "Subscription created successfully", response.Message)
	
	mockDB.AssertExpectations(t)
}

func TestGetUserSubscriptionAPI(t *testing.T) {
	router, mockDB, _ := setupTestRouter()
	
	userID := uuid.New()
	subscription := createTestSubscription(userID, PlanPro)
	
	// Mock expectations
	mockDB.On("GetSubscriptionByUserID", userID).Return(subscription, nil)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/subscriptions/user/%s", userID), nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.True(t, response.Success)
	
	responseData := response.Data.(map[string]interface{})
	subscriptionData := responseData["subscription"].(map[string]interface{})
	assert.Equal(t, string(PlanPro), subscriptionData["plan_type"])
	
	mockDB.AssertExpectations(t)
}

func TestRecordUsageAPI(t *testing.T) {
	router, mockDB, _ := setupTestRouter()
	
	userID := uuid.New()
	
	// Mock expectations
	quotaInfo := &QuotaInfo{
		UserID:       userID,
		ResourceType: ResourceMessages,
		CurrentUsage: 1,
		MaxAllowed:   100,
		Remaining:    99,
		HasQuota:     true,
	}
	
	mockDB.On("CheckUserQuota", userID, ResourceMessages).Return(quotaInfo, nil)
	mockDB.On("RecordUsage", userID, ResourceMessages, 1, mock.AnythingOfType("map[string]interface {}")).Return(nil)
	
	reqBody := RecordUsageRequest{
		UserID:       userID.String(),
		ResourceType: string(ResourceMessages),
		Quantity:     1,
		Metadata:     map[string]interface{}{"session_id": "test-session"},
	}
	
	body, _ := json.Marshal(reqBody)
	
	req, _ := http.NewRequest("POST", "/api/v1/usage/record", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.True(t, response.Success)
	
	mockDB.AssertExpectations(t)
}

func TestCheckQuotaAPI(t *testing.T) {
	router, mockDB, _ := setupTestRouter()
	
	userID := uuid.New()
	
	quotaInfo := &QuotaInfo{
		UserID:       userID,
		ResourceType: ResourceMessages,
		CurrentUsage: 50,
		MaxAllowed:   100,
		Remaining:    50,
		HasQuota:     true,
	}
	
	mockDB.On("CheckUserQuota", userID, ResourceMessages).Return(quotaInfo, nil)
	
	req, _ := http.NewRequest("GET", fmt.Sprintf("/api/v1/usage/user/%s/quota/%s", userID, ResourceMessages), nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.True(t, response.Success)
	
	responseData := response.Data.(map[string]interface{})
	assert.Equal(t, float64(50), responseData["current_usage"])
	assert.Equal(t, float64(100), responseData["max_allowed"])
	assert.Equal(t, true, responseData["has_quota"])
	
	mockDB.AssertExpectations(t)
}

func TestListPlansAPI(t *testing.T) {
	router, _, _ := setupTestRouter()
	
	req, _ := http.NewRequest("GET", "/api/v1/plans/", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response APIResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.True(t, response.Success)
	
	plans := response.Data.([]interface{})
	assert.Equal(t, 3, len(plans))
	
	// Verify plan structure
	freePlan := plans[0].(map[string]interface{})
	assert.Equal(t, string(PlanFree), freePlan["plan"])
	assert.Equal(t, "Free Tier", freePlan["display_name"])
	assert.Equal(t, float64(0), freePlan["monthly_price_cents"])
}

func TestHealthCheckAPI(t *testing.T) {
	router, _, _ := setupTestRouter()
	
	req, _ := http.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	
	assert.Equal(t, "healthy", response["status"])
	assert.Equal(t, "user-subscription-service", response["service"])
	assert.Equal(t, "1.0.0", response["version"])
}

// Service Logic Tests

func TestCreateUserSubscription(t *testing.T) {
	mockDB := NewMockDatabaseManager()
	service := NewSubscriptionService(mockDB)
	
	userID := uuid.New()
	
	mockDB.On("GetSubscriptionByUserID", userID).Return((*Subscription)(nil), fmt.Errorf("not found"))
	mockDB.On("CreateSubscription", mock.AnythingOfType("*main.Subscription")).Return(nil)
	
	subscription, err := service.CreateUserSubscription(userID, PlanPro, CycleMonthly)
	
	require.NoError(t, err)
	assert.Equal(t, userID, subscription.UserID)
	assert.Equal(t, PlanPro, subscription.PlanType)
	assert.Equal(t, CycleMonthly, subscription.BillingCycle)
	assert.Equal(t, StatusActive, subscription.Status)
	
	mockDB.AssertExpectations(t)
}

func TestUpgradeSubscription(t *testing.T) {
	mockDB := NewMockDatabaseManager()
	service := NewSubscriptionService(mockDB)
	
	userID := uuid.New()
	currentSub := createTestSubscription(userID, PlanFree)
	
	mockDB.On("GetSubscriptionByUserID", userID).Return(currentSub, nil)
	mockDB.On("UpdateSubscription", mock.AnythingOfType("*main.Subscription")).Return(nil)
	
	upgradedSub, err := service.UpgradeSubscription(userID, PlanPro, CycleMonthly)
	
	require.NoError(t, err)
	assert.Equal(t, PlanPro, upgradedSub.PlanType)
	
	mockDB.AssertExpectations(t)
}

func TestDowngradeSubscription(t *testing.T) {
	mockDB := NewMockDatabaseManager()
	service := NewSubscriptionService(mockDB)
	
	userID := uuid.New()
	currentSub := createTestSubscription(userID, PlanPro)
	
	mockDB.On("GetSubscriptionByUserID", userID).Return(currentSub, nil)
	
	// Note: DB operations are mocked through the interface methods
	
	result, err := service.DowngradeSubscription(userID, PlanFree)
	
	require.NoError(t, err)
	assert.Equal(t, PlanPro, result.PlanType) // Should still be Pro until next billing cycle
	
	mockDB.AssertExpectations(t)
}

func TestCheckAndRecordUsage(t *testing.T) {
	mockDB := NewMockDatabaseManager()
	service := NewSubscriptionService(mockDB)
	
	userID := uuid.New()
	
	quotaInfo := &QuotaInfo{
		UserID:       userID,
		ResourceType: ResourceMessages,
		CurrentUsage: 50,
		MaxAllowed:   100,
		Remaining:    50,
		HasQuota:     true,
	}
	
	mockDB.On("CheckUserQuota", userID, ResourceMessages).Return(quotaInfo, nil)
	mockDB.On("RecordUsage", userID, ResourceMessages, 1, mock.AnythingOfType("map[string]interface {}")).Return(nil)
	
	result, err := service.CheckAndRecordUsage(userID, ResourceMessages, 1, map[string]interface{}{"test": "data"})
	
	require.NoError(t, err)
	assert.Equal(t, userID, result.UserID)
	assert.Equal(t, ResourceMessages, result.ResourceType)
	
	mockDB.AssertExpectations(t)
}

// Benchmark Tests

func BenchmarkGetPlanDefaults(b *testing.B) {
	for i := 0; i < b.N; i++ {
		GetPlanDefaults(PlanPro)
	}
}

func BenchmarkGetPlanFeatures(b *testing.B) {
	for i := 0; i < b.N; i++ {
		GetPlanFeatures(PlanEnterprise)
	}
}

func BenchmarkSubscriptionIsActive(b *testing.B) {
	subscription := &Subscription{
		Status: StatusActive,
		EndsAt: nil,
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		subscription.IsActive()
	}
}

func BenchmarkCreateSubscriptionAPI(b *testing.B) {
	router, mockDB, _ := setupTestRouter()
	
	userID := uuid.New()
	mockDB.On("CreateSubscription", mock.AnythingOfType("*main.Subscription")).Return(nil)
	
	reqBody := CreateSubscriptionRequest{
		UserID:       userID.String(),
		PlanType:     string(PlanPro),
		BillingCycle: string(CycleMonthly),
	}
	
	body, _ := json.Marshal(reqBody)
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("POST", "/api/v1/subscriptions/", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}

// Error Handling Tests

func TestInvalidPlanTypeAPI(t *testing.T) {
	router, _, _ := setupTestRouter()
	
	userID := uuid.New()
	
	reqBody := CreateSubscriptionRequest{
		UserID:       userID.String(),
		PlanType:     "invalid_plan",
		BillingCycle: string(CycleMonthly),
	}
	
	body, _ := json.Marshal(reqBody)
	
	req, _ := http.NewRequest("POST", "/api/v1/subscriptions/", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
	
	var response APIResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.False(t, response.Success)
	assert.Contains(t, response.Error, "Invalid plan type")
}

func TestInvalidUserIDAPI(t *testing.T) {
	router, _, _ := setupTestRouter()
	
	req, _ := http.NewRequest("GET", "/api/v1/subscriptions/user/invalid-uuid", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
	
	var response APIResponse
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.False(t, response.Success)
	assert.Equal(t, "Invalid user ID", response.Error)
}

func TestQuotaExceeded(t *testing.T) {
	mockDB := NewMockDatabaseManager()
	service := NewSubscriptionService(mockDB)
	
	userID := uuid.New()
	
	quotaInfo := &QuotaInfo{
		UserID:       userID,
		ResourceType: ResourceMessages,
		CurrentUsage: 100,
		MaxAllowed:   100,
		Remaining:    0,
		HasQuota:     false,
		PlanType:     string(PlanFree),
	}
	
	mockDB.On("CheckUserQuota", userID, ResourceMessages).Return(quotaInfo, nil)
	
	_, err := service.CheckAndRecordUsage(userID, ResourceMessages, 1, nil)
	
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "quota exceeded")
	
	mockDB.AssertExpectations(t)
}

// Configuration Tests

func TestLoadConfig(t *testing.T) {
	// Set environment variables
	os.Setenv("PORT", "8080")
	os.Setenv("ENVIRONMENT", "production")
	os.Setenv("POSTGRES_HOST", "db.example.com")
	
	defer func() {
		os.Unsetenv("PORT")
		os.Unsetenv("ENVIRONMENT")
		os.Unsetenv("POSTGRES_HOST")
	}()
	
	config := loadConfig()
	
	assert.Equal(t, "8080", config.Port)
	assert.Equal(t, "production", config.Environment)
	assert.Equal(t, "db.example.com", config.PostgreSQLHost)
	assert.Equal(t, "5432", config.PostgreSQLPort) // default value
}

// Utility function tests

func TestGetCurrentBillingPeriod(t *testing.T) {
	subscription := &Subscription{
		BillingCycle: CycleMonthly,
	}
	
	period := GetCurrentBillingPeriod(subscription)
	
	assert.Equal(t, "monthly", period.Type)
	assert.True(t, period.Start.Before(period.End))
	
	// Test yearly billing
	subscription.BillingCycle = CycleYearly
	yearlyPeriod := GetCurrentBillingPeriod(subscription)
	assert.Equal(t, "yearly", yearlyPeriod.Type)
}

// Integration test with real database (optional, requires test database)
func TestIntegrationWithRealDB(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}
	
	// This test would require a real database connection
	// Skip if no test database is available
	t.Skip("Integration test requires test database setup")
}

// Test helper functions

func TestHelperGetEnv(t *testing.T) {
	os.Setenv("TEST_VAR", "test_value")
	defer os.Unsetenv("TEST_VAR")
	
	assert.Equal(t, "test_value", getEnv("TEST_VAR", "default"))
	assert.Equal(t, "default", getEnv("NON_EXISTENT_VAR", "default"))
}

// Test data validation

func TestJSONMapSerialization(t *testing.T) {
	jsonMap := JSONMap{
		"key1": "value1",
		"key2": 123,
		"key3": true,
	}
	
	value, err := jsonMap.Value()
	require.NoError(t, err)
	
	var newMap JSONMap
	err = newMap.Scan(value)
	require.NoError(t, err)
	
	assert.Equal(t, "value1", newMap["key1"])
	assert.Equal(t, float64(123), newMap["key2"]) // JSON numbers become float64
	assert.Equal(t, true, newMap["key3"])
}