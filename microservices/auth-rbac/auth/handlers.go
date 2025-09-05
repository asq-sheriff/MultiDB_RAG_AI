// Package auth provides HTTP handlers for authentication operations
package auth

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	
	"auth-rbac-service/models"
	"auth-rbac-service/rbac"
)

// ServiceManager interface for dependency injection
type ServiceManager interface {
	GetPasswordHasher() *PasswordHasher
	GetJWTManager() *JWTManager
	GetPermissionChecker() *rbac.PermissionChecker
	GetDB() DatabaseManager
	LogAuditEvent(ctx context.Context, userID *uuid.UUID, action, resourceType, resourceID string, oldValues, newValues map[string]interface{}, ipAddress, userAgent string, purpose rbac.AccessPurpose, justification string) error
}

// DatabaseManager interface for database operations
type DatabaseManager interface {
	CreateUser(ctx context.Context, user *models.CreateUser, passwordHash string) (*models.User, error)
	GetUserByEmail(ctx context.Context, email string) (*models.User, error)
	GetUserByID(ctx context.Context, userID uuid.UUID) (*models.User, error)
	UpdateUserLastLogin(ctx context.Context, userID uuid.UUID) error
	CreateSession(ctx context.Context, session *models.Session) error
	GetSessionByID(ctx context.Context, sessionID string) (*models.Session, error)
	UpdateSessionActivity(ctx context.Context, sessionID string) error
	DeactivateSession(ctx context.Context, sessionID string) error
	GetUserSessions(ctx context.Context, userID uuid.UUID) ([]*models.Session, error)
	LogAuditEvent(ctx context.Context, event *models.AuditLog) error
	GetAuditLogs(ctx context.Context, userID *uuid.UUID, action string, limit, offset int) ([]*models.AuditLog, error)
	Ping(ctx context.Context) error
}

// RegisterHandler handles user registration
func RegisterHandler(sm ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.RegisterRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Invalid request",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Validate request
		if err := req.Validate(); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Validation failed",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Validate password strength
		if err := ValidatePasswordStrength(req.Password); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Password validation failed",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Hash password
		hasher := sm.GetPasswordHasher()
		passwordHash, err := hasher.HashPassword(req.Password)
		if err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Password hashing failed",
				Message:   "Failed to secure password",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Create user
		createUser := &models.CreateUser{
			Email:            req.Email,
			Password:         req.Password, // This won't be stored
			FirstName:        req.FirstName,
			LastName:         req.LastName,
			Phone:            req.Phone,
			HealthcareRole:   req.HealthcareRole,
			SubscriptionPlan: req.SubscriptionPlan,
		}

		if createUser.SubscriptionPlan == "" {
			createUser.SubscriptionPlan = "free"
		}

		user, err := sm.GetDB().CreateUser(context.Background(), createUser, passwordHash)
		if err != nil {
			if strings.Contains(err.Error(), "duplicate") || strings.Contains(err.Error(), "already exists") {
				c.JSON(http.StatusConflict, models.ErrorResponse{
					Error:     "User already exists",
					Message:   "A user with this email address already exists",
					Timestamp: time.Now(),
					RequestID: c.GetString("request_id"),
				})
				return
			}
			
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "User creation failed",
				Message:   "Failed to create user account",
				Details:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Log audit event
		sm.LogAuditEvent(
			context.Background(),
			&user.ID,
			"user_registered",
			"user",
			user.ID.String(),
			nil,
			map[string]interface{}{
				"email":           user.Email,
				"healthcare_role": user.HealthcareRole,
				"subscription_plan": user.SubscriptionPlan,
			},
			c.ClientIP(),
			c.GetHeader("User-Agent"),
			rbac.PurposeOperations,
			"New user registration",
		)

		c.JSON(http.StatusCreated, models.APIResponse{
			Success: true,
			Data: models.RegisterResponse{
				User:    user.ToProfile(),
				Message: "User registered successfully. Please verify your email address.",
			},
			Timestamp: time.Now(),
		})
	}
}

// LoginHandler handles user authentication
func LoginHandler(sm ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.LoginRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Invalid request",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Get user by email
		user, err := sm.GetDB().GetUserByEmail(context.Background(), req.Email)
		if err != nil {
			// Log failed login attempt
			sm.LogAuditEvent(
				context.Background(),
				nil,
				"login_failed",
				"authentication",
				"",
				nil,
				map[string]interface{}{
					"email":  req.Email,
					"reason": "user_not_found",
				},
				c.ClientIP(),
				c.GetHeader("User-Agent"),
				rbac.PurposeOperations,
				"Failed login attempt - user not found",
			)

			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Authentication failed",
				Message:   "Invalid email or password",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Verify password
		hasher := sm.GetPasswordHasher()
		valid, err := hasher.VerifyPassword(req.Password, user.PasswordHash)
		if err != nil || !valid {
			// Log failed login attempt
			sm.LogAuditEvent(
				context.Background(),
				&user.ID,
				"login_failed",
				"authentication",
				"",
				nil,
				map[string]interface{}{
					"email":  req.Email,
					"reason": "invalid_password",
				},
				c.ClientIP(),
				c.GetHeader("User-Agent"),
				rbac.PurposeOperations,
				"Failed login attempt - invalid password",
			)

			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Authentication failed",
				Message:   "Invalid email or password",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Check if user is active
		if !user.IsActive {
			sm.LogAuditEvent(
				context.Background(),
				&user.ID,
				"login_failed",
				"authentication",
				"",
				nil,
				map[string]interface{}{
					"email":  req.Email,
					"reason": "account_inactive",
				},
				c.ClientIP(),
				c.GetHeader("User-Agent"),
				rbac.PurposeOperations,
				"Failed login attempt - account inactive",
			)

			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Error:     "Account inactive",
				Message:   "Your account has been deactivated. Please contact support.",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Create session
		sessionID := uuid.New().String()
		session := &models.Session{
			ID:           sessionID,
			UserID:       user.ID,
			ExpiresAt:    time.Now().Add(7 * 24 * time.Hour), // 7 days
			CreatedAt:    time.Now(),
			LastActivity: time.Now(),
			IPAddress:    c.ClientIP(),
			UserAgent:    c.GetHeader("User-Agent"),
			IsActive:     true,
		}

		if err := sm.GetDB().CreateSession(context.Background(), session); err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Session creation failed",
				Message:   "Failed to create user session",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Generate JWT tokens
		jwtManager := sm.GetJWTManager()
		loginResponse, err := jwtManager.GenerateTokenPair(user, sessionID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Token generation failed",
				Message:   "Failed to generate authentication tokens",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Update last login time
		if err := sm.GetDB().UpdateUserLastLogin(context.Background(), user.ID); err != nil {
			// Log error but don't fail the request
			fmt.Printf("Warning: Failed to update last login for user %s: %v\n", user.ID, err)
		}

		// Log successful login
		sm.LogAuditEvent(
			context.Background(),
			&user.ID,
			"login_success",
			"authentication",
			"",
			nil,
			map[string]interface{}{
				"email":      user.Email,
				"session_id": sessionID,
			},
			c.ClientIP(),
			c.GetHeader("User-Agent"),
			rbac.PurposeOperations,
			"Successful user login",
		)

		c.JSON(http.StatusOK, models.APIResponse{
			Success:   true,
			Data:      loginResponse,
			Timestamp: time.Now(),
		})
	}
}

// VerifyTokenHandler verifies JWT tokens and returns user information
func VerifyTokenHandler(sm ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.VerifyTokenRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Invalid request",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Validate token
		jwtManager := sm.GetJWTManager()
		claims, err := jwtManager.ValidateToken(req.Token)
		if err != nil {
			c.JSON(http.StatusOK, models.APIResponse{
				Success: true,
				Data: models.VerifyTokenResponse{
					Valid:   false,
					Message: err.Error(),
				},
				Timestamp: time.Now(),
			})
			return
		}

		// Get user permissions
		permissionChecker := sm.GetPermissionChecker()
		rolePermissions := permissionChecker.GetRolePermissions(claims.HealthcareRole)
		
		permissions := make([]rbac.Permission, 0)
		for perm, allowed := range rolePermissions {
			if allowed {
				permissions = append(permissions, perm)
			}
		}

		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: models.VerifyTokenResponse{
				Valid:       true,
				UserID:      claims.UserID,
				Email:       claims.Email,
				Role:        claims.HealthcareRole,
				Permissions: permissions,
				ExpiresAt:   claims.ExpiresAt,
			},
			Timestamp: time.Now(),
		})
	}
}

// LogoutHandler handles user logout
func LogoutHandler(sm ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.LogoutRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			// If no body provided, try to get token from header
			authHeader := c.GetHeader("Authorization")
			if authHeader != "" && strings.HasPrefix(authHeader, "Bearer ") {
				req.Token = strings.TrimPrefix(authHeader, "Bearer ")
			}
		}

		if req.Token == "" {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Token required",
				Message:   "Authentication token is required for logout",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Validate token and get session info
		jwtManager := sm.GetJWTManager()
		claims, err := jwtManager.ValidateToken(req.Token)
		if err != nil {
			// Token is invalid, but we'll still return success for security
			c.JSON(http.StatusOK, models.APIResponse{
				Success: true,
				Data: models.LogoutResponse{
					Message: "Logged out successfully",
					Success: true,
				},
				Timestamp: time.Now(),
			})
			return
		}

		// Deactivate session(s)
		if req.All {
			// Deactivate all sessions for the user
			sessions, err := sm.GetDB().GetUserSessions(context.Background(), claims.UserID)
			if err == nil {
				for _, session := range sessions {
					sm.GetDB().DeactivateSession(context.Background(), session.ID)
				}
			}
		} else {
			// Deactivate current session
			sm.GetDB().DeactivateSession(context.Background(), claims.SessionID)
		}

		// Blacklist the token
		jwtManager.BlacklistToken(req.Token)

		// Log logout event
		sm.LogAuditEvent(
			context.Background(),
			&claims.UserID,
			"logout",
			"authentication",
			"",
			nil,
			map[string]interface{}{
				"session_id": claims.SessionID,
				"logout_all": req.All,
			},
			c.ClientIP(),
			c.GetHeader("User-Agent"),
			rbac.PurposeOperations,
			"User logout",
		)

		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: models.LogoutResponse{
				Message: "Logged out successfully",
				Success: true,
			},
			Timestamp: time.Now(),
		})
	}
}