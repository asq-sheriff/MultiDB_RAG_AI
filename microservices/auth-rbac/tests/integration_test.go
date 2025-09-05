// Package tests provides integration tests for the auth-rbac service
package tests

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
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"auth-rbac-service/auth"
	"auth-rbac-service/models"
	"auth-rbac-service/rbac"
	"github.com/google/uuid"
)

// MockDatabaseManager implements the DatabaseManager interface for testing
type MockDatabaseManager struct {
	users     map[string]*models.User
	sessions  map[string]*models.Session
	auditLogs []*models.AuditLog
}

// MockServiceManager implements the ServiceManager interface for testing
type MockServiceManager struct {
	passwordHasher    *auth.PasswordHasher
	jwtManager        *auth.JWTManager
	permissionChecker *rbac.PermissionChecker
	db                *MockDatabaseManager
}

// NewMockServiceManager creates a new mock service manager for testing
func NewMockServiceManager() *MockServiceManager {
	db := &MockDatabaseManager{
		users:     make(map[string]*models.User),
		sessions:  make(map[string]*models.Session),
		auditLogs: make([]*models.AuditLog, 0),
	}
	
	return &MockServiceManager{
		passwordHasher:    auth.NewPasswordHasher(),
		jwtManager:        auth.NewJWTManager("test-secret-key", 15*time.Minute, 7*24*time.Hour, "test-issuer"),
		permissionChecker: rbac.NewPermissionChecker(),
		db:                db,
	}
}

func (m *MockServiceManager) GetPasswordHasher() *auth.PasswordHasher {
	return m.passwordHasher
}

func (m *MockServiceManager) GetJWTManager() *auth.JWTManager {
	return m.jwtManager
}

func (m *MockServiceManager) GetPermissionChecker() *rbac.PermissionChecker {
	return m.permissionChecker
}

func (m *MockServiceManager) GetDB() auth.DatabaseManager {
	return m.db
}

// ServiceManager interface implementation  
func (m *MockServiceManager) LogAuditEvent(ctx context.Context, userID *uuid.UUID, action, resourceType, resourceID string, oldValues, newValues map[string]interface{}, ipAddress, userAgent string, purpose rbac.AccessPurpose, justification string) error {
	// Mock audit logging - create event and call DB method
	event := &models.AuditLog{
		ID:            uuid.New(),
		UserID:        userID,
		Action:        action,
		ResourceType:  resourceType,
		ResourceID:    resourceID,
		OldValues:     oldValues,
		NewValues:     newValues,
		IPAddress:     ipAddress,
		UserAgent:     userAgent,
		AccessPurpose: purpose,
		Justification: justification,
		CreatedAt:     time.Now(),
	}
	return m.GetDB().LogAuditEvent(ctx, event)
}

// DatabaseManager mock implementations
func (m *MockDatabaseManager) CreateUser(ctx context.Context, user *models.CreateUser, passwordHash string) (*models.User, error) {
	// Check if user already exists
	if _, exists := m.users[user.Email]; exists {
		return nil, fmt.Errorf("user already exists")
	}

	newUser := &models.User{
		ID:               uuid.New(),
		Email:            user.Email,
		PasswordHash:     passwordHash,
		FirstName:        user.FirstName,
		LastName:         user.LastName,
		Phone:            user.Phone,
		HealthcareRole:   user.HealthcareRole,
		SubscriptionPlan: user.SubscriptionPlan,
		IsActive:         true,
		IsVerified:       false,
		IsSuperuser:      false,
		CreatedAt:        time.Now(),
		UpdatedAt:        time.Now(),
	}

	m.users[user.Email] = newUser
	return newUser, nil
}

func (m *MockDatabaseManager) GetUserByEmail(ctx context.Context, email string) (*models.User, error) {
	user, exists := m.users[email]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}
	return user, nil
}

// Implement other required DatabaseManager methods as no-ops for testing
func (m *MockDatabaseManager) GetUserByID(ctx context.Context, userID uuid.UUID) (*models.User, error) {
	return nil, fmt.Errorf("not implemented")
}
func (m *MockDatabaseManager) UpdateUserLastLogin(ctx context.Context, userID uuid.UUID) error {
	return nil
}
func (m *MockDatabaseManager) CreateSession(ctx context.Context, session *models.Session) error {
	m.sessions[session.ID] = session
	return nil
}
func (m *MockDatabaseManager) GetSessionByID(ctx context.Context, sessionID string) (*models.Session, error) {
	session, exists := m.sessions[sessionID]
	if !exists {
		return nil, fmt.Errorf("session not found")
	}
	return session, nil
}
func (m *MockDatabaseManager) UpdateSessionActivity(ctx context.Context, sessionID string) error {
	return nil
}
func (m *MockDatabaseManager) DeactivateSession(ctx context.Context, sessionID string) error {
	if session, exists := m.sessions[sessionID]; exists {
		session.IsActive = false
	}
	return nil
}
func (m *MockDatabaseManager) GetUserSessions(ctx context.Context, userID uuid.UUID) ([]*models.Session, error) {
	return nil, nil
}
func (m *MockDatabaseManager) LogAuditEvent(ctx context.Context, event *models.AuditLog) error {
	m.auditLogs = append(m.auditLogs, event)
	return nil
}
func (m *MockDatabaseManager) GetAuditLogs(ctx context.Context, userID *uuid.UUID, action string, limit, offset int) ([]*models.AuditLog, error) {
	return m.auditLogs, nil
}
func (m *MockDatabaseManager) Ping(ctx context.Context) error {
	return nil
}

func TestUserRegistration(t *testing.T) {
	gin.SetMode(gin.TestMode)
	
	sm := NewMockServiceManager()
	router := gin.New()
	
	// Setup registration endpoint
	router.POST("/register", auth.RegisterHandler(sm))

	// Test user registration
	registerReq := models.RegisterRequest{
		Email:           "test@example.com",
		Password:        "SecurePassword123!",
		ConfirmPassword: "SecurePassword123!",
		FirstName:       "Test",
		LastName:        "User",
		Phone:           "+1234567890",
		HealthcareRole:  rbac.RoleCareStaff,
	}

	body, err := json.Marshal(registerReq)
	require.NoError(t, err)

	req, err := http.NewRequest("POST", "/register", bytes.NewBuffer(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)

	var response models.APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.True(t, response.Success)
}

func TestUserLogin(t *testing.T) {
	gin.SetMode(gin.TestMode)
	
	sm := NewMockServiceManager()
	router := gin.New()
	
	// Setup endpoints
	router.POST("/register", auth.RegisterHandler(sm))
	router.POST("/login", auth.LoginHandler(sm))

	// First, register a user
	registerReq := models.RegisterRequest{
		Email:           "login@example.com",
		Password:        "SecurePassword123!",
		ConfirmPassword: "SecurePassword123!",
		FirstName:       "Login",
		LastName:        "Test",
		HealthcareRole:  rbac.RoleCareStaff,
	}

	body, err := json.Marshal(registerReq)
	require.NoError(t, err)

	req, err := http.NewRequest("POST", "/register", bytes.NewBuffer(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)

	// Now test login
	loginReq := models.LoginRequest{
		Email:    "login@example.com",
		Password: "SecurePassword123!",
	}

	body, err = json.Marshal(loginReq)
	require.NoError(t, err)

	req, err = http.NewRequest("POST", "/login", bytes.NewBuffer(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var response models.APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	assert.True(t, response.Success)

	// Check that login response contains access token
	loginResp, ok := response.Data.(map[string]interface{})
	require.True(t, ok)
	assert.NotEmpty(t, loginResp["access_token"])
	assert.NotEmpty(t, loginResp["refresh_token"])
	assert.Equal(t, "Bearer", loginResp["token_type"])
}

func TestPasswordValidation(t *testing.T) {
	tests := []struct {
		password string
		valid    bool
	}{
		{"weak", false},                   // Too short
		{"weakpassword", false},           // No uppercase, numbers, or special chars
		{"WeakPassword", false},           // No numbers or special chars
		{"WeakPassword123", false},        // No special chars
		{"WeakPassword!", false},          // No numbers
		{"weakpassword123!", false},       // No uppercase
		{"WeakPassword123!", true},        // Valid password
		{"SecureP@ssw0rd", true},         // Valid password
		{"MySecure123!", true},           // Valid password
	}

	for _, tt := range tests {
		t.Run(fmt.Sprintf("password_%s", tt.password), func(t *testing.T) {
			err := auth.ValidatePasswordStrength(tt.password)
			if tt.valid {
				assert.NoError(t, err, "Password should be valid: %s", tt.password)
			} else {
				assert.Error(t, err, "Password should be invalid: %s", tt.password)
			}
		})
	}
}

func TestRBACPermissions(t *testing.T) {
	pc := rbac.NewPermissionChecker()

	// Test resident permissions
	assert.True(t, pc.HasPermission(rbac.RoleResident, rbac.PermCanAccessOwnData))
	assert.False(t, pc.HasPermission(rbac.RoleResident, rbac.PermCanAccessOthersData))
	assert.False(t, pc.HasPermission(rbac.RoleResident, rbac.PermCanModifySystemSettings))

	// Test admin permissions
	assert.True(t, pc.HasPermission(rbac.RoleAdmin, rbac.PermCanAccessOwnData))
	assert.True(t, pc.HasPermission(rbac.RoleAdmin, rbac.PermCanAccessOthersData))
	assert.True(t, pc.HasPermission(rbac.RoleAdmin, rbac.PermCanModifySystemSettings))

	// Test care staff permissions
	assert.True(t, pc.HasPermission(rbac.RoleCareStaff, rbac.PermCanAccessAssignedPatients))
	assert.False(t, pc.HasPermission(rbac.RoleCareStaff, rbac.PermCanModifySystemSettings))
	assert.True(t, pc.HasPermission(rbac.RoleCareStaff, rbac.PermCanEscalateCrisis))
}

func TestJWTTokenGeneration(t *testing.T) {
	jwtManager := auth.NewJWTManager("test-secret", 15*time.Minute, 7*24*time.Hour, "test-issuer")
	
	user := &models.User{
		ID:             uuid.New(),
		Email:          "test@example.com",
		HealthcareRole: rbac.RoleCareStaff,
		IsActive:       true,
		IsSuperuser:    false,
	}

	loginResponse, err := jwtManager.GenerateTokenPair(user, "test-session-id")
	require.NoError(t, err)

	assert.NotEmpty(t, loginResponse.AccessToken)
	assert.NotEmpty(t, loginResponse.RefreshToken)
	assert.Equal(t, "Bearer", loginResponse.TokenType)
	assert.Greater(t, loginResponse.ExpiresIn, int64(0))

	// Test token validation
	claims, err := jwtManager.ValidateToken(loginResponse.AccessToken)
	require.NoError(t, err)

	assert.Equal(t, user.Email, claims.Email)
	assert.Equal(t, user.HealthcareRole, claims.HealthcareRole)
	assert.Equal(t, user.IsActive, claims.IsActive)
	assert.Equal(t, user.IsSuperuser, claims.IsSuperuser)
}

func TestHealthcareRoleValidation(t *testing.T) {
	validRoles := []rbac.HealthcareRole{
		rbac.RoleResident,
		rbac.RoleFamilyMember,
		rbac.RoleHealthPlanMember,
		rbac.RoleCareStaff,
		rbac.RoleCaseManager,
		rbac.RoleCareManager,
		rbac.RoleAdmin,
	}

	for _, role := range validRoles {
		assert.True(t, role.IsValid(), "Role should be valid: %s", role)
	}

	// Test invalid role
	invalidRole := rbac.HealthcareRole("invalid_role")
	assert.False(t, invalidRole.IsValid(), "Invalid role should not be valid")
}

func TestPasswordHashing(t *testing.T) {
	hasher := auth.NewPasswordHasher()
	password := "TestPassword123!"

	// Test password hashing
	hash, err := hasher.HashPassword(password)
	require.NoError(t, err)
	assert.NotEmpty(t, hash)
	assert.NotEqual(t, password, hash)

	// Test password verification
	valid, err := hasher.VerifyPassword(password, hash)
	require.NoError(t, err)
	assert.True(t, valid)

	// Test invalid password verification
	valid, err = hasher.VerifyPassword("WrongPassword", hash)
	require.NoError(t, err)
	assert.False(t, valid)
}

// Integration test that combines multiple components
func TestCompleteUserFlow(t *testing.T) {
	gin.SetMode(gin.TestMode)
	
	sm := NewMockServiceManager()
	router := gin.New()
	
	// Setup all endpoints
	auth_group := router.Group("/auth")
	auth_group.POST("/register", auth.RegisterHandler(sm))
	auth_group.POST("/login", auth.LoginHandler(sm))
	auth_group.POST("/verify", auth.VerifyTokenHandler(sm))

	// 1. Register a user
	registerReq := models.RegisterRequest{
		Email:           "flow@example.com",
		Password:        "FlowPassword123!",
		ConfirmPassword: "FlowPassword123!",
		FirstName:       "Flow",
		LastName:        "Test",
		HealthcareRole:  rbac.RoleCareManager,
	}

	body, err := json.Marshal(registerReq)
	require.NoError(t, err)

	req, err := http.NewRequest("POST", "/auth/register", bytes.NewBuffer(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusCreated, w.Code)

	// 2. Login
	loginReq := models.LoginRequest{
		Email:    "flow@example.com",
		Password: "FlowPassword123!",
	}

	body, err = json.Marshal(loginReq)
	require.NoError(t, err)

	req, err = http.NewRequest("POST", "/auth/login", bytes.NewBuffer(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	var loginResponse models.APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &loginResponse)
	require.NoError(t, err)
	assert.True(t, loginResponse.Success)

	loginData, ok := loginResponse.Data.(map[string]interface{})
	require.True(t, ok)
	accessToken := loginData["access_token"].(string)

	// 3. Verify token
	verifyReq := models.VerifyTokenRequest{
		Token: accessToken,
	}

	body, err = json.Marshal(verifyReq)
	require.NoError(t, err)

	req, err = http.NewRequest("POST", "/auth/verify", bytes.NewBuffer(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)

	var verifyResponse models.APIResponse
	err = json.Unmarshal(w.Body.Bytes(), &verifyResponse)
	require.NoError(t, err)
	assert.True(t, verifyResponse.Success)

	verifyData, ok := verifyResponse.Data.(map[string]interface{})
	require.True(t, ok)
	assert.True(t, verifyData["valid"].(bool))
	assert.Equal(t, "flow@example.com", verifyData["email"])
	assert.Equal(t, string(rbac.RoleCareManager), verifyData["role"])
}