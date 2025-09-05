// Package handlers provides additional HTTP handlers for the auth-rbac service
package handlers

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	
	"auth-rbac-service/auth"
	"auth-rbac-service/models"
	"auth-rbac-service/rbac"
)

// RefreshTokenHandler handles refresh token requests
func RefreshTokenHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.RefreshTokenRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Invalid request",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		if req.RefreshToken == "" {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Refresh token required",
				Message:   "Refresh token is required",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Parse refresh token to get user ID
		jwtManager := sm.GetJWTManager()
		claims, err := jwtManager.ValidateToken(req.RefreshToken)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Invalid refresh token",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Get user from database
		user, err := sm.GetDB().GetUserByID(context.Background(), claims.UserID)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "User not found",
				Message:   "User associated with refresh token not found",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// Generate new access token
		refreshResponse, err := jwtManager.RefreshAccessToken(req.RefreshToken, user)
		if err != nil {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "Token refresh failed",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		c.JSON(http.StatusOK, models.APIResponse{
			Success:   true,
			Data:      refreshResponse,
			Timestamp: time.Now(),
		})
	}
}

// ResetPasswordHandler handles password reset requests
func ResetPasswordHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.ResetPasswordRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Invalid request",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		// In a real implementation, this would:
		// 1. Verify the reset token
		// 2. Update the user's password
		// 3. Invalidate all existing sessions
		// For now, return a placeholder response
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Password reset functionality not yet implemented",
			},
			Timestamp: time.Now(),
		})
	}
}

// GetProfileHandler returns the current user's profile
func GetProfileHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		user, exists := c.Get("user")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "User not found in context",
				Message:   "Authentication required",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		u, ok := user.(*models.User)
		if !ok {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Invalid user type",
				Message:   "User type assertion failed",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		c.JSON(http.StatusOK, models.APIResponse{
			Success:   true,
			Data:      u.ToProfile(),
			Timestamp: time.Now(),
		})
	}
}

// UpdateProfileHandler updates the current user's profile
func UpdateProfileHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Profile update functionality not yet implemented",
			},
			Timestamp: time.Now(),
		})
	}
}

// ChangePasswordHandler handles password change requests
func ChangePasswordHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Change password functionality not yet implemented",
			},
			Timestamp: time.Now(),
		})
	}
}

// GetSessionsHandler returns all active sessions for the current user
func GetSessionsHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID, exists := c.Get("user_id")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "User ID not found",
				Message:   "Authentication required",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		uid, ok := userID.(uuid.UUID)
		if !ok {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Invalid user ID type",
				Message:   "User ID type assertion failed",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		sessions, err := sm.GetDB().GetUserSessions(context.Background(), uid)
		if err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Failed to get sessions",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		c.JSON(http.StatusOK, models.APIResponse{
			Success:   true,
			Data:      sessions,
			Timestamp: time.Now(),
		})
	}
}

// DeleteSessionHandler deactivates a specific session
func DeleteSessionHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		sessionID := c.Param("session_id")
		if sessionID == "" {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Session ID required",
				Message:   "Session ID is required in URL path",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		err := sm.GetDB().DeactivateSession(context.Background(), sessionID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Failed to deactivate session",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Session deactivated successfully",
			},
			Timestamp: time.Now(),
		})
	}
}

// GetPermissionsHandler returns available permissions
func GetPermissionsHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		permissions := rbac.AllPermissions()
		c.JSON(http.StatusOK, models.APIResponse{
			Success:   true,
			Data:      permissions,
			Timestamp: time.Now(),
		})
	}
}

// GetRolesHandler returns available healthcare roles
func GetRolesHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		roles := rbac.AllHealthcareRoles()
		c.JSON(http.StatusOK, models.APIResponse{
			Success:   true,
			Data:      roles,
			Timestamp: time.Now(),
		})
	}
}

// CheckPermissionHandler checks if the current user has a specific permission
func CheckPermissionHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.CheckPermissionRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Invalid request",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		userRole, exists := c.Get("user_role")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "User role not found",
				Message:   "Authentication required",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		role, ok := userRole.(rbac.HealthcareRole)
		if !ok {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Invalid role type",
				Message:   "Role type assertion failed",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		permissionChecker := sm.GetPermissionChecker()
		hasPermission := permissionChecker.HasPermission(role, req.Permission)

		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: models.CheckPermissionResponse{
				Permission:    req.Permission,
				HasPermission: hasPermission,
				Role:          role,
			},
			Timestamp: time.Now(),
		})
	}
}

// CheckAccessHandler performs comprehensive access checks
func CheckAccessHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req models.CheckAccessRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, models.ErrorResponse{
				Error:     "Invalid request",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		userRole, exists := c.Get("user_role")
		if !exists {
			c.JSON(http.StatusUnauthorized, models.ErrorResponse{
				Error:     "User role not found",
				Message:   "Authentication required",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		role, ok := userRole.(rbac.HealthcareRole)
		if !ok {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Invalid role type",
				Message:   "Role type assertion failed",
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		permissionChecker := sm.GetPermissionChecker()
		accessDetails := permissionChecker.CheckAccess(role, req.ResourceType, req.Action, req.Purpose)

		c.JSON(http.StatusOK, models.APIResponse{
			Success:   true,
			Data:      accessDetails,
			Timestamp: time.Now(),
		})
	}
}

// Admin Handlers

// ListUsersHandler returns a list of users (admin only)
func ListUsersHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "List users functionality not yet implemented",
			},
			Timestamp: time.Now(),
		})
	}
}

// GetUserHandler returns a specific user (admin only)
func GetUserHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID := c.Param("user_id")
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Get user functionality not yet implemented",
				"user_id": userID,
			},
			Timestamp: time.Now(),
		})
	}
}

// UpdateUserHandler updates a specific user (admin only)
func UpdateUserHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID := c.Param("user_id")
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Update user functionality not yet implemented",
				"user_id": userID,
			},
			Timestamp: time.Now(),
		})
	}
}

// DeleteUserHandler deletes a specific user (admin only)
func DeleteUserHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID := c.Param("user_id")
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Delete user functionality not yet implemented",
				"user_id": userID,
			},
			Timestamp: time.Now(),
		})
	}
}

// GetAuditLogsHandler returns audit logs (admin only)
func GetAuditLogsHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Parse query parameters
		limitStr := c.DefaultQuery("limit", "50")
		offsetStr := c.DefaultQuery("offset", "0")
		action := c.Query("action")
		userIDStr := c.Query("user_id")

		limit, err := strconv.Atoi(limitStr)
		if err != nil {
			limit = 50
		}

		offset, err := strconv.Atoi(offsetStr)
		if err != nil {
			offset = 0
		}

		var userID *uuid.UUID
		if userIDStr != "" {
			if parsed, err := uuid.Parse(userIDStr); err == nil {
				userID = &parsed
			}
		}

		logs, err := sm.GetDB().GetAuditLogs(context.Background(), userID, action, limit, offset)
		if err != nil {
			c.JSON(http.StatusInternalServerError, models.ErrorResponse{
				Error:     "Failed to get audit logs",
				Message:   err.Error(),
				Timestamp: time.Now(),
				RequestID: c.GetString("request_id"),
			})
			return
		}

		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: models.AuditLogResponse{
				Logs:   logs,
				Limit:  limit,
				Offset: offset,
			},
			Timestamp: time.Now(),
		})
	}
}

// GetStatsHandler returns service statistics (admin only)
func GetStatsHandler(sm auth.ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, models.APIResponse{
			Success: true,
			Data: gin.H{
				"message": "Statistics functionality not yet implemented",
			},
			Timestamp: time.Now(),
		})
	}
}