package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/suite"
	"go.uber.org/zap"
)

// Mock database for testing - implements DatabaseInterface
type MockPostgresDB struct {
	mock.Mock
}

func (m *MockPostgresDB) Close() error {
	args := m.Called()
	return args.Error(0)
}

func (m *MockPostgresDB) Ping() error {
	args := m.Called()
	return args.Error(0)
}

func (m *MockPostgresDB) CreatePatientConsent(params CreatePatientConsentParams) (*PatientConsent, error) {
	args := m.Called(params)
	if consent := args.Get(0); consent != nil {
		return consent.(*PatientConsent), args.Error(1)
	}
	return nil, args.Error(1)
}

func (m *MockPostgresDB) RevokeConsent(params RevokeConsentParams) (bool, error) {
	args := m.Called(params)
	return args.Bool(0), args.Error(1)
}

func (m *MockPostgresDB) GetPatientConsents(params GetPatientConsentsParams) ([]PatientConsent, error) {
	args := m.Called(params)
	if consents := args.Get(0); consents != nil {
		return consents.([]PatientConsent), args.Error(1)
	}
	return nil, args.Error(1)
}

func (m *MockPostgresDB) GetPatientConsent(params GetPatientConsentParams) (*PatientConsent, error) {
	args := m.Called(params)
	if consent := args.Get(0); consent != nil {
		return consent.(*PatientConsent), args.Error(1)
	}
	return nil, args.Error(1)
}

func (m *MockPostgresDB) GetAllPatientConsents(params GetAllPatientConsentsParams) ([]PatientConsent, error) {
	args := m.Called(params)
	if consents := args.Get(0); consents != nil {
		return consents.([]PatientConsent), args.Error(1)
	}
	return nil, args.Error(1)
}

func (m *MockPostgresDB) UpdateConsentStatus(params UpdateConsentStatusParams) (bool, error) {
	args := m.Called(params)
	return args.Bool(0), args.Error(1)
}

func (m *MockPostgresDB) checkDataAccess(params CheckDataAccessParams) (*AccessDecision, error) {
	args := m.Called(params)
	if decision := args.Get(0); decision != nil {
		return decision.(*AccessDecision), args.Error(1)
	}
	return nil, args.Error(1)
}

func (m *MockPostgresDB) LogConsentAction(params LogConsentActionParams) error {
	args := m.Called(params)
	return args.Error(0)
}

// Mock cache for testing - implements CacheInterface
type MockRedisCache struct {
	mock.Mock
}

func (m *MockRedisCache) Close() error {
	args := m.Called()
	return args.Error(0)
}

func (m *MockRedisCache) Set(key, value string, expiration time.Duration) error {
	args := m.Called(key, value, expiration)
	return args.Error(0)
}

func (m *MockRedisCache) Get(key string) (string, error) {
	args := m.Called(key)
	if args.Get(0) == nil {
		return "", args.Error(1)
	}
	return args.String(0), args.Error(1)
}

func (m *MockRedisCache) Delete(key string) error {
	args := m.Called(key)
	return args.Error(0)
}

func (m *MockRedisCache) Exists(key string) (bool, error) {
	args := m.Called(key)
	return args.Bool(0), args.Error(1)
}

func (m *MockRedisCache) InvalidatePatientConsents(patientID uuid.UUID) error {
	args := m.Called(patientID)
	return args.Error(0)
}

func (m *MockRedisCache) CheckRateLimit(key string, limit int, window time.Duration) (bool, error) {
	args := m.Called(key, limit, window)
	return args.Bool(0), args.Error(1)
}

// Test Suite
type ConsentServiceTestSuite struct {
	suite.Suite
	service    *ConsentService
	mockDB     *MockPostgresDB
	mockCache  *MockRedisCache
	router     *gin.Engine
}

func (suite *ConsentServiceTestSuite) SetupTest() {
	gin.SetMode(gin.TestMode)
	logger, _ := zap.NewDevelopment()

	suite.mockDB = &MockPostgresDB{}
	suite.mockCache = &MockRedisCache{}

	suite.service = &ConsentService{
		logger: logger,
		config: &Config{
			Port:        "8080",
			Environment: "test",
			HIPAAMode:   true,
		},
	}

	// Override the database and cache with mocks
	suite.service.db = suite.mockDB
	suite.service.cache = suite.mockCache

	suite.router = setupRoutes(suite.service)
}

func (suite *ConsentServiceTestSuite) TestHealthCheck() {
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "healthy", response["status"])
	assert.Equal(suite.T(), "consent-service-go", response["service"])
}

func (suite *ConsentServiceTestSuite) TestReadinessCheck() {
	suite.mockDB.On("Ping").Return(nil)
	suite.mockCache.On("Ping").Return(nil)
	suite.mockCache.On("Exists", mock.AnythingOfType("string")).Return(false, nil)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/ready", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "ready", response["status"])

	suite.mockDB.AssertExpectations(suite.T())
	suite.mockCache.AssertExpectations(suite.T())
}

func (suite *ConsentServiceTestSuite) TestReadinessCheckDatabaseDown() {
	suite.mockDB.On("Ping").Return(sql.ErrConnDone)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/ready", nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusServiceUnavailable, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "not_ready", response["status"])
	assert.Equal(suite.T(), "database_unavailable", response["reason"])

	suite.mockDB.AssertExpectations(suite.T())
}

func (suite *ConsentServiceTestSuite) TestCreateConsentSuccess() {
	patientID := uuid.New()
	grantorID := uuid.New()
	granteeID := uuid.New()
	userID := uuid.New()

	requestData := CreateConsentRequest{
		PatientID: patientID,
		GrantorID: grantorID,
		GranteeID: granteeID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations", "care_notes"},
	}

	expectedConsent := &PatientConsent{
		ConsentID: uuid.New(),
		PatientID: patientID,
		GrantorID: grantorID,
		GranteeID: granteeID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations", "care_notes"},
		Status:    "active",
		GrantedAt: time.Now(),
	}

	suite.mockDB.On("CreatePatientConsent", mock.AnythingOfType("CreatePatientConsentParams")).Return(expectedConsent, nil)
	suite.mockDB.On("LogConsentAction", mock.AnythingOfType("LogConsentActionParams")).Return(nil)
	suite.mockCache.On("InvalidatePatientConsents", patientID).Return(nil)

	jsonData, _ := json.Marshal(requestData)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/consent/create", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	
	// Create a router with authentication middleware for this test
	testRouter := gin.New()
	testRouter.Use(func(c *gin.Context) {
		c.Set("user_id", userID)
		c.Next()
	})
	testRouter.POST("/v1/consent/create", suite.service.createConsent)
	
	testRouter.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusCreated, w.Code)

	var response ConsentResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), expectedConsent.ConsentID, response.ConsentID)
	assert.Equal(suite.T(), expectedConsent.Purpose, response.Purpose)
	assert.Equal(suite.T(), expectedConsent.Status, response.Status)

	suite.mockDB.AssertExpectations(suite.T())
	suite.mockCache.AssertExpectations(suite.T())
}

func (suite *ConsentServiceTestSuite) TestCreateConsentInvalidRequest() {
	invalidRequest := map[string]interface{}{
		"patient_id": "invalid-uuid",
		"purpose":    "treatment",
	}

	jsonData, _ := json.Marshal(invalidRequest)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/consent/create", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusBadRequest, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "Invalid request format", response["error"])
}

func (suite *ConsentServiceTestSuite) TestRevokeConsentSuccess() {
	consentID := uuid.New()
	userID := uuid.New()

	suite.mockDB.On("RevokeConsent", mock.AnythingOfType("RevokeConsentParams")).Return(true, nil)
	suite.mockDB.On("LogConsentAction", mock.AnythingOfType("LogConsentActionParams")).Return(nil)

	requestData := RevokeConsentRequest{
		Reason: stringPtr("Patient requested revocation"),
	}

	jsonData, _ := json.Marshal(requestData)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/v1/consent/"+consentID.String(), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	// Create a router with authentication middleware for this test
	testRouter := gin.New()
	testRouter.Use(func(c *gin.Context) {
		c.Set("user_id", userID)
		c.Next()
	})
	testRouter.DELETE("/v1/consent/:consent_id", suite.service.revokeConsent)
	
	testRouter.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "Consent revoked successfully", response["message"])

	suite.mockDB.AssertExpectations(suite.T())
}

func (suite *ConsentServiceTestSuite) TestRevokeConsentUnauthorized() {
	consentID := uuid.New()
	userID := uuid.New()

	suite.mockDB.On("RevokeConsent", mock.AnythingOfType("RevokeConsentParams")).Return(false, nil)

	requestData := RevokeConsentRequest{
		Reason: stringPtr("Unauthorized attempt"),
	}

	jsonData, _ := json.Marshal(requestData)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/v1/consent/"+consentID.String(), bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	// Create a router with authentication middleware for this test
	testRouter := gin.New()
	testRouter.Use(func(c *gin.Context) {
		c.Set("user_id", userID)
		c.Next()
	})
	testRouter.DELETE("/v1/consent/:consent_id", suite.service.revokeConsent)
	
	testRouter.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusForbidden, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "Not authorized to revoke this consent", response["error"])

	suite.mockDB.AssertExpectations(suite.T())
}

func (suite *ConsentServiceTestSuite) TestGetPatientConsents() {
	patientID := uuid.New()
	
	expectedConsents := []PatientConsent{
		{
			ConsentID: uuid.New(),
			PatientID: patientID,
			GrantorID: uuid.New(),
			GranteeID: uuid.New(),
			Purpose:   "treatment",
			DataTypes: []string{"conversations"},
			Status:    "active",
			GrantedAt: time.Now(),
		},
	}

	// Mock cache miss
	suite.mockCache.On("Get", mock.AnythingOfType("string")).Return(nil, nil)
	suite.mockDB.On("GetPatientConsents", mock.AnythingOfType("GetPatientConsentsParams")).Return(expectedConsents, nil)
	suite.mockCache.On("Set", mock.AnythingOfType("string"), mock.Anything, mock.AnythingOfType("time.Duration")).Return(nil)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/v1/consent/patient/"+patientID.String(), nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)
	assert.Equal(suite.T(), "MISS", w.Header().Get("X-Cache"))

	var response []ConsentResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), response, 1)
	assert.Equal(suite.T(), expectedConsents[0].Purpose, response[0].Purpose)

	suite.mockDB.AssertExpectations(suite.T())
	suite.mockCache.AssertExpectations(suite.T())
}

func (suite *ConsentServiceTestSuite) TestGetPatientConsentsCacheHit() {
	patientID := uuid.New()
	
	cachedResponse := []ConsentResponse{
		{
			ConsentID: uuid.New(),
			PatientID: patientID,
			Purpose:   "treatment",
			Status:    "active",
		},
	}

	// Mock cache hit - cache should return raw data, not JSON string
	suite.mockCache.On("Get", mock.AnythingOfType("string")).Return(cachedResponse, nil)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/v1/consent/patient/"+patientID.String(), nil)
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)
	assert.Equal(suite.T(), "HIT", w.Header().Get("X-Cache"))

	var response []ConsentResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), response, 1)

	suite.mockCache.AssertExpectations(suite.T())
	// Database should not be called for cache hit
	suite.mockDB.AssertNotCalled(suite.T(), "GetPatientConsents")
}

func (suite *ConsentServiceTestSuite) TestValidateAccessGranted() {
	userID := uuid.New()
	patientID := uuid.New()

	requestData := ValidateAccessRequest{
		UserID:    userID,
		PatientID: patientID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations"},
	}

	expectedDecision := &AccessDecision{
		Granted:   true,
		Reason:    "Access granted via patient consent",
		ConsentID: uuidPtr(uuid.New()),
		Timestamp: time.Now(),
	}

	suite.mockDB.On("checkDataAccess", mock.AnythingOfType("CheckDataAccessParams")).Return(expectedDecision, nil)

	jsonData, _ := json.Marshal(requestData)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/consent/validate", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response AccessDecisionResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.True(suite.T(), response.Granted)
	assert.Equal(suite.T(), expectedDecision.Reason, response.Reason)

	suite.mockDB.AssertExpectations(suite.T())
}

func (suite *ConsentServiceTestSuite) TestValidateAccessDenied() {
	userID := uuid.New()
	patientID := uuid.New()

	requestData := ValidateAccessRequest{
		UserID:    userID,
		PatientID: patientID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations"},
	}

	expectedDecision := &AccessDecision{
		Granted:   false,
		Reason:    "No valid authorization found",
		Timestamp: time.Now(),
	}

	suite.mockDB.On("checkDataAccess", mock.AnythingOfType("CheckDataAccessParams")).Return(expectedDecision, nil)

	jsonData, _ := json.Marshal(requestData)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/v1/consent/validate", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response AccessDecisionResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.False(suite.T(), response.Granted)
	assert.Equal(suite.T(), expectedDecision.Reason, response.Reason)

	suite.mockDB.AssertExpectations(suite.T())
}

// Benchmark tests for performance validation
func BenchmarkCreateConsent(b *testing.B) {
	gin.SetMode(gin.TestMode)
	logger, _ := zap.NewDevelopment()

	mockDB := &MockPostgresDB{}
	mockCache := &MockRedisCache{}

	service := &ConsentService{
		logger: logger,
		config: &Config{Environment: "test"},
		db:     mockDB,
		cache:  mockCache,
	}

	router := setupRoutes(service)

	patientID := uuid.New()
	grantorID := uuid.New()
	granteeID := uuid.New()

	requestData := CreateConsentRequest{
		PatientID: patientID,
		GrantorID: grantorID,
		GranteeID: granteeID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations", "care_notes"},
	}

	expectedConsent := &PatientConsent{
		ConsentID: uuid.New(),
		PatientID: patientID,
		Purpose:   "treatment",
		Status:    "active",
		GrantedAt: time.Now(),
	}

	mockDB.On("CreatePatientConsent", mock.Anything).Return(expectedConsent, nil)
	mockCache.On("InvalidatePatientConsents", mock.Anything).Return(nil)

	jsonData, _ := json.Marshal(requestData)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("POST", "/v1/consent/create", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		router.ServeHTTP(w, req)
	}
}

func BenchmarkValidateAccess(b *testing.B) {
	gin.SetMode(gin.TestMode)
	logger, _ := zap.NewDevelopment()

	mockDB := &MockPostgresDB{}

	service := &ConsentService{
		logger: logger,
		config: &Config{Environment: "test"},
		db:     mockDB,
	}

	router := setupRoutes(service)

	requestData := ValidateAccessRequest{
		UserID:    uuid.New(),
		PatientID: uuid.New(),
		Purpose:   "treatment",
		DataTypes: []string{"conversations"},
	}

	expectedDecision := &AccessDecision{
		Granted:   true,
		Reason:    "Access granted",
		Timestamp: time.Now(),
	}

	mockDB.On("checkDataAccess", mock.Anything).Return(expectedDecision, nil)

	jsonData, _ := json.Marshal(requestData)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("POST", "/v1/consent/validate", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		router.ServeHTTP(w, req)
	}
}

// Helper functions
func stringPtr(s string) *string {
	return &s
}

func uuidPtr(u uuid.UUID) *uuid.UUID {
	return &u
}

// Run the test suite
func TestConsentServiceTestSuite(t *testing.T) {
	suite.Run(t, new(ConsentServiceTestSuite))
}