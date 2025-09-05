// Auth-RBAC Service - Centralized Authentication and Role-Based Access Control
// Provides secure authentication, authorization, and HIPAA-compliant access control
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/joho/godotenv"
	
	"auth-rbac-service/auth"
	"auth-rbac-service/database"
	"auth-rbac-service/handlers"
	"auth-rbac-service/models"
	"auth-rbac-service/rbac"
)

// ServiceConfig holds the configuration for the auth-rbac service
type ServiceConfig struct {
	Port                 string        `envconfig:"PORT" default:"8080"`
	Environment          string        `envconfig:"ENVIRONMENT" default:"development"`
	DatabaseURL          string        `envconfig:"DATABASE_URL" default:"postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_app"`
	JWTSecret            string        `envconfig:"JWT_SECRET" required:"true"`
	AccessTokenDuration  time.Duration `envconfig:"ACCESS_TOKEN_DURATION" default:"15m"`
	RefreshTokenDuration time.Duration `envconfig:"REFRESH_TOKEN_DURATION" default:"7d"`
	JWTIssuer           string        `envconfig:"JWT_ISSUER" default:"auth-rbac-service"`
	HIPAAMode           bool          `envconfig:"HIPAA_MODE" default:"true"`
	LogLevel            string        `envconfig:"LOG_LEVEL" default:"info"`
}

// ServiceManager manages all service dependencies
type ServiceManager struct {
	Config          *ServiceConfig
	DB              *database.Manager
	PasswordHasher  *auth.PasswordHasher
	JWTManager      *auth.JWTManager
	PermissionChecker *rbac.PermissionChecker
}

// NewServiceManager creates a new service manager with all dependencies
func NewServiceManager(config *ServiceConfig) (*ServiceManager, error) {
	// Initialize database
	dbManager, err := database.NewManager(config.DatabaseURL)
	if err != nil {
		return nil, err
	}

	// Initialize password hasher
	passwordHasher := auth.NewPasswordHasher()

	// Initialize JWT manager
	jwtManager := auth.NewJWTManager(
		config.JWTSecret,
		config.AccessTokenDuration,
		config.RefreshTokenDuration,
		config.JWTIssuer,
	)

	// Initialize permission checker
	permissionChecker := rbac.NewPermissionChecker()

	return &ServiceManager{
		Config:            config,
		DB:                dbManager,
		PasswordHasher:    passwordHasher,
		JWTManager:        jwtManager,
		PermissionChecker: permissionChecker,
	}, nil
}

// Interface methods for ServiceManager to satisfy auth.ServiceManager interface

// GetPasswordHasher returns the password hasher
func (sm *ServiceManager) GetPasswordHasher() *auth.PasswordHasher {
	return sm.PasswordHasher
}

// GetJWTManager returns the JWT manager
func (sm *ServiceManager) GetJWTManager() *auth.JWTManager {
	return sm.JWTManager
}

// GetPermissionChecker returns the permission checker
func (sm *ServiceManager) GetPermissionChecker() *rbac.PermissionChecker {
	return sm.PermissionChecker
}

// GetDB returns the database manager
func (sm *ServiceManager) GetDB() auth.DatabaseManager {
	return sm.DB
}

// LogAuditEvent logs an audit event for HIPAA compliance
func (sm *ServiceManager) LogAuditEvent(ctx context.Context, userID *uuid.UUID, action, resourceType, resourceID string, oldValues, newValues map[string]interface{}, ipAddress, userAgent string, purpose rbac.AccessPurpose, justification string) error {
	auditEvent := &models.AuditLog{
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
	
	return sm.DB.LogAuditEvent(ctx, auditEvent)
}

func main() {
	// Load environment variables
	if err := godotenv.Load("../../.env"); err != nil {
		log.Printf("Warning: Could not load .env file: %v", err)
	}

	// Initialize configuration
	config := &ServiceConfig{
		Port:                 getEnv("PORT", "8080"),
		Environment:          getEnv("ENVIRONMENT", "development"),
		DatabaseURL:          getEnv("DATABASE_URL", "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_app"),
		JWTSecret:            getEnv("JWT_SECRET", ""),
		AccessTokenDuration:  parseDuration(getEnv("ACCESS_TOKEN_DURATION", "15m")),
		RefreshTokenDuration: parseDuration(getEnv("REFRESH_TOKEN_DURATION", "7d")),
		JWTIssuer:           getEnv("JWT_ISSUER", "auth-rbac-service"),
		HIPAAMode:           getEnv("HIPAA_MODE", "true") == "true",
		LogLevel:            getEnv("LOG_LEVEL", "info"),
	}

	// Validate JWT secret
	if config.JWTSecret == "" {
		log.Fatal("JWT_SECRET environment variable is required")
	}

	// Initialize service manager
	serviceManager, err := NewServiceManager(config)
	if err != nil {
		log.Fatalf("Failed to initialize service manager: %v", err)
	}
	defer serviceManager.DB.Close()

	// Test database connection
	if err := serviceManager.DB.Ping(context.Background()); err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	// Set Gin mode
	if config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Setup router
	router := setupRoutes(serviceManager)

	// Create HTTP server
	srv := &http.Server{
		Addr:    ":" + config.Port,
		Handler: router,
	}

	// Start server in a goroutine
	go func() {
		log.Printf("🔐 Auth-RBAC Service starting on port %s", config.Port)
		log.Printf("🏥 HIPAA Mode: %v", config.HIPAAMode)
		log.Printf("🌍 Environment: %s", config.Environment)
		log.Printf("📊 Service capabilities:")
		log.Printf("   - JWT Authentication with %v access token duration", config.AccessTokenDuration)
		log.Printf("   - Role-based access control for %d healthcare roles", len(rbac.AllHealthcareRoles()))
		log.Printf("   - HIPAA-compliant audit logging")
		log.Printf("   - Secure password hashing with Argon2")
		
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal to gracefully shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("🛑 Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("✅ Server exited")
}

// setupRoutes configures all API routes
func setupRoutes(sm *ServiceManager) *gin.Engine {
	router := gin.New()
	
	// Middleware
	router.Use(gin.Logger())
	router.Use(gin.Recovery())
	router.Use(corsMiddleware())
	
	// Health check
	router.GET("/health", healthCheckHandler(sm))
	router.GET("/ready", readinessCheckHandler(sm))
	
	// API routes
	api := router.Group("/api/v1")
	
	// Authentication routes (no auth required)
	authGroup := api.Group("/auth")
	{
		authGroup.POST("/register", auth.RegisterHandler(sm))
		authGroup.POST("/login", auth.LoginHandler(sm))
		authGroup.POST("/refresh", handlers.RefreshTokenHandler(sm))
		authGroup.POST("/verify", auth.VerifyTokenHandler(sm))
		authGroup.POST("/logout", auth.LogoutHandler(sm))
		authGroup.POST("/reset-password", handlers.ResetPasswordHandler(sm))
	}
	
	// Protected routes (require authentication)
	protected := api.Group("/")
	protected.Use(auth.AuthMiddleware(sm))
	{
		// User profile routes
		protected.GET("/profile", handlers.GetProfileHandler(sm))
		protected.PUT("/profile", handlers.UpdateProfileHandler(sm))
		protected.POST("/change-password", handlers.ChangePasswordHandler(sm))
		
		// Session management
		protected.GET("/sessions", handlers.GetSessionsHandler(sm))
		protected.DELETE("/sessions/:session_id", handlers.DeleteSessionHandler(sm))
		
		// RBAC routes
		rbacGroup := protected.Group("/rbac")
		{
			rbacGroup.GET("/permissions", handlers.GetPermissionsHandler(sm))
			rbacGroup.GET("/roles", handlers.GetRolesHandler(sm))
			rbacGroup.POST("/check-permission", handlers.CheckPermissionHandler(sm))
			rbacGroup.POST("/check-access", handlers.CheckAccessHandler(sm))
		}
		
		// Admin routes (require admin role)
		admin := protected.Group("/admin")
		admin.Use(auth.RequireRole(sm, rbac.RoleAdmin, rbac.RoleCareManager))
		{
			admin.GET("/users", handlers.ListUsersHandler(sm))
			admin.GET("/users/:user_id", handlers.GetUserHandler(sm))
			admin.PUT("/users/:user_id", handlers.UpdateUserHandler(sm))
			admin.DELETE("/users/:user_id", handlers.DeleteUserHandler(sm))
			admin.GET("/audit-logs", handlers.GetAuditLogsHandler(sm))
			admin.GET("/stats", handlers.GetStatsHandler(sm))
		}
	}
	
	return router
}

// Utility functions
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func parseDuration(s string) time.Duration {
	d, err := time.ParseDuration(s)
	if err != nil {
		log.Printf("Warning: Invalid duration %s, using default", s)
		return 15 * time.Minute
	}
	return d
}

// corsMiddleware adds CORS headers
func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		c.Header("Access-Control-Allow-Credentials", "true")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		
		c.Next()
	}
}

// healthCheckHandler returns basic health status
func healthCheckHandler(sm *ServiceManager) gin.HandlerFunc {
	startTime := time.Now()
	return func(c *gin.Context) {
		c.JSON(http.StatusOK, models.HealthCheckResponse{
			Status:      "healthy",
			Service:     "auth-rbac-service",
			Version:     "1.0.0",
			Timestamp:   time.Now(),
			Database:    "connected",
			Uptime:      time.Since(startTime).String(),
			Environment: sm.Config.Environment,
		})
	}
}

// readinessCheckHandler performs comprehensive readiness checks
func readinessCheckHandler(sm *ServiceManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Check database connection
		if err := sm.DB.Ping(context.Background()); err != nil {
			c.JSON(http.StatusServiceUnavailable, models.ErrorResponse{
				Error:     "Database unavailable",
				Message:   err.Error(),
				Timestamp: time.Now(),
			})
			return
		}
		
		c.JSON(http.StatusOK, gin.H{
			"status":    "ready",
			"service":   "auth-rbac-service", 
			"database":  "connected",
			"timestamp": time.Now(),
		})
	}
}