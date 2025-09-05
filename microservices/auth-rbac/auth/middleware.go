// Package auth provides authentication and authorization middleware
package auth

import (
	"context"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	
	"auth-rbac-service/models"
	"auth-rbac-service/rbac"
)

// AuthMiddleware validates JWT tokens and sets user context
func AuthMiddleware(sm ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get token from Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Authorization required",
				Message:   "Missing Authorization header",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		// Validate Bearer token format
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Invalid token format",
				Message:   "Authorization header must be 'Bearer <token>'",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		tokenString := parts[1]

		// Validate JWT token
		jwtManager := sm.GetJWTManager()
		claims, err := jwtManager.ValidateToken(tokenString)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Invalid token",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		// Check if user is still active and exists
		user, err := sm.GetDB().GetUserByID(context.Background(), claims.UserID)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "User not found",
				Message:   "The user associated with this token no longer exists",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		if !user.IsActive {
			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Error:     "Account inactive",
				Message:   "Your account has been deactivated",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		// Verify session is still active
		session, err := sm.GetDB().GetSessionByID(context.Background(), claims.SessionID)
		if err != nil || !session.IsActive || session.IsExpired() {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Session expired",
				Message:   "Your session has expired. Please login again.",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		// Update session activity
		sm.GetDB().UpdateSessionActivity(context.Background(), claims.SessionID)

		// Set user context
		c.Set("user_id", claims.UserID)
		c.Set("user_email", claims.Email)
		c.Set("user_role", claims.HealthcareRole)
		c.Set("user_claims", claims)
		c.Set("user", user)
		c.Set("session_id", claims.SessionID)
		c.Set("is_superuser", claims.IsSuperuser)

		c.Next()
	}
}

// OptionalAuthMiddleware provides optional authentication (doesn't fail if no token)
func OptionalAuthMiddleware(sm ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			// No auth header, continue without authentication
			c.Next()
			return
		}

		// Validate Bearer token format
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			// Invalid format, continue without authentication
			c.Next()
			return
		}

		tokenString := parts[1]

		// Validate JWT token
		jwtManager := sm.GetJWTManager()
		claims, err := jwtManager.ValidateToken(tokenString)
		if err != nil {
			// Invalid token, continue without authentication
			c.Next()
			return
		}

		// Check if user exists and is active
		user, err := sm.GetDB().GetUserByID(context.Background(), claims.UserID)
		if err != nil || !user.IsActive {
			// User not found or inactive, continue without authentication
			c.Next()
			return
		}

		// Verify session
		session, err := sm.GetDB().GetSessionByID(context.Background(), claims.SessionID)
		if err != nil || !session.IsActive || session.IsExpired() {
			// Session invalid, continue without authentication
			c.Next()
			return
		}

		// Set user context if everything is valid
		c.Set("user_id", claims.UserID)
		c.Set("user_email", claims.Email)
		c.Set("user_role", claims.HealthcareRole)
		c.Set("user_claims", claims)
		c.Set("user", user)
		c.Set("session_id", claims.SessionID)
		c.Set("is_authenticated", true)

		c.Next()
	}
}

// RequireRole middleware that requires specific healthcare roles
func RequireRole(sm ServiceManager, allowedRoles ...rbac.HealthcareRole) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get user role from context (set by AuthMiddleware)
		userRole, exists := c.Get("user_role")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Authentication required",
				Message:   "User role not found in context",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		role, ok := userRole.(rbac.HealthcareRole)
		if !ok {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Invalid role type",
				Message:   "User role has invalid type",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		// Check if user has one of the allowed roles
		for _, allowedRole := range allowedRoles {
			if role == allowedRole {
				c.Next()
				return
			}
		}

		// User doesn't have required role
		userID, _ := c.Get("user_id")
		if uid, ok := userID.(uuid.UUID); ok {
			// Log unauthorized access attempt
			sm.LogAuditEvent(
				context.Background(),
				&uid,
				"access_denied",
				"authorization",
				c.FullPath(),
				nil,
				map[string]interface{}{
					"user_role":     role,
					"required_roles": allowedRoles,
					"endpoint":      c.FullPath(),
					"method":        c.Request.Method,
				},
				c.ClientIP(),
				c.GetHeader("User-Agent"),
				rbac.PurposeOperations,
				"Role-based access denied",
			)
		}

		c.JSON(http.StatusForbidden, models.ErrorResponse{
			Error:     "Insufficient privileges",
			Message:   "You don't have permission to access this resource",
			Timestamp: time.Now(),
			RequestID: c.GetString("request_id"),
		})
		c.Abort()
	}
}

// RequirePermission middleware that requires specific permissions
func RequirePermission(sm ServiceManager, permission rbac.Permission) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get user role from context
		userRole, exists := c.Get("user_role")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Authentication required",
				Message:   "User role not found in context",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		role, ok := userRole.(rbac.HealthcareRole)
		if !ok {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Invalid role type",
				Message:   "User role has invalid type",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		// Check permission
		permissionChecker := sm.GetPermissionChecker()
		if !permissionChecker.HasPermission(role, permission) {
			userID, _ := c.Get("user_id")
			if uid, ok := userID.(uuid.UUID); ok {
				// Log unauthorized access attempt
				sm.LogAuditEvent(
					context.Background(),
					&uid,
					"permission_denied",
					"authorization",
					c.FullPath(),
					nil,
					map[string]interface{}{
						"user_role":         role,
						"required_permission": permission,
						"endpoint":          c.FullPath(),
						"method":            c.Request.Method,
					},
					c.ClientIP(),
					c.GetHeader("User-Agent"),
					rbac.PurposeOperations,
					"Permission-based access denied",
				)
			}

			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Error:     "Insufficient permissions",
				Message:   "You don't have the required permission to access this resource",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// RequireSuperuser middleware that requires superuser privileges
func RequireSuperuser(sm ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		isSuperuser, exists := c.Get("is_superuser")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Authentication required",
				Message:   "Superuser status not found in context",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		if superuser, ok := isSuperuser.(bool); !ok || !superuser {
			userID, _ := c.Get("user_id")
			if uid, ok := userID.(uuid.UUID); ok {
				// Log unauthorized access attempt
				sm.LogAuditEvent(
					context.Background(),
					&uid,
					"superuser_access_denied",
					"authorization",
					c.FullPath(),
					nil,
					map[string]interface{}{
						"endpoint": c.FullPath(),
						"method":   c.Request.Method,
					},
					c.ClientIP(),
					c.GetHeader("User-Agent"),
					rbac.PurposeOperations,
					"Superuser access denied",
				)
			}

			c.JSON(http.StatusForbidden, models.ErrorResponse{
				Error:     "Superuser required",
				Message:   "This resource requires superuser privileges",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// RequestIDMiddleware adds a unique request ID to each request
func RequestIDMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := uuid.New().String()
		c.Set("request_id", requestID)
		c.Header("X-Request-ID", requestID)
		c.Next()
	}
}