package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/kelseyhightower/envconfig"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

type Config struct {
	Port           string `envconfig:"PORT" default:"8081"`
	Environment    string `envconfig:"ENVIRONMENT" default:"development"`
	DatabaseURL    string `envconfig:"DATABASE_URL"`
	RedisURL       string `envconfig:"REDIS_URL"`
	LogLevel       string `envconfig:"LOG_LEVEL" default:"info"`
	EnableMetrics  bool   `envconfig:"ENABLE_METRICS" default:"true"`
	GracefulTimeout int   `envconfig:"GRACEFUL_TIMEOUT" default:"30"`
}

// detectEnvironment detects which environment we should be running in
func detectEnvironment() string {
	// Highest priority: explicit override flags
	if os.Getenv("DEMO_MODE") == "1" {
		return "demo"
	}
	if os.Getenv("CI") == "true" {
		return "testing"
	}
	
	// Medium priority: explicit environment variables
	if appEnv := os.Getenv("APP_ENVIRONMENT"); appEnv != "" {
		return strings.ToLower(appEnv)
	}
	
	// Lowest priority: general environment variable
	if env := strings.ToLower(os.Getenv("ENVIRONMENT")); env != "" {
		switch env {
		case "demo_v1", "demo":
			return "demo"
		case "development", "dev":
			return "development"
		case "production", "prod":
			return "production"
		case "testing", "test":
			return "testing"
		default:
			return env
		}
	}
	
	return "development"
}

// loadEnvironment loads the appropriate environment configuration
func loadEnvironment() error {
	envType := detectEnvironment()
	fmt.Printf("🔧 Billing service detected environment: %s\n", envType)
	
	var envFilePath string
	switch envType {
	case "demo":
		envFilePath = "demo/config/.env.demo_v1"
	case "development":
		envFilePath = ".env"
	case "testing":
		envFilePath = "config/testing.env"
	case "production":
		fmt.Printf("✅ %s environment - using system variables\n", envType)
		return nil
	default:
		fmt.Printf("⚠️ Unknown environment: %s, using development\n", envType)
		envFilePath = ".env"
	}
	
	// Find actual file path
	searchPaths := []string{
		envFilePath,
		fmt.Sprintf("../../%s", envFilePath),
		fmt.Sprintf("../../../%s", envFilePath),
		fmt.Sprintf("/Users/asqmac/git-repos/MultiDB-Chatbot/%s", envFilePath),
	}
	
	var actualPath string
	for _, path := range searchPaths {
		if _, err := os.Stat(path); err == nil {
			actualPath = path
			break
		}
	}
	
	if actualPath == "" {
		fmt.Printf("⚠️ Environment file %s not found, using defaults\n", envFilePath)
		return nil
	}
	
	if err := godotenv.Overload(actualPath); err != nil {
		return fmt.Errorf("failed to load %s environment: %v", envType, err)
	}
	
	fmt.Printf("✅ Loaded %s environment from %s\n", envType, filepath.Base(actualPath))
	return nil
}

// getEnvironmentDatabaseURL returns appropriate database URL for current environment
func getEnvironmentDatabaseURL(dbType string) string {
	envType := detectEnvironment()
	
	switch envType {
	case "demo":
		switch dbType {
		case "postgres":
			return "postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app"
		case "redis":
			return "redis://localhost:6380/10"
		}
	case "development":
		switch dbType {
		case "postgres":
			return "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_app"
		case "redis":
			return "redis://localhost:6379/0"
		}
	}
	
	// Fallback to environment variables
	switch dbType {
	case "postgres":
		return os.Getenv("DATABASE_URL")
	case "redis":
		return os.Getenv("REDIS_URL") 
	default:
		return ""
	}
}

// LoadConfigWithEnvironment loads configuration with environment-aware database URLs
func LoadConfigWithEnvironment() (*Config, error) {
	var config Config
	
	// Set environment-aware database URLs before processing envconfig
	if dbURL := getEnvironmentDatabaseURL("postgres"); dbURL != "" {
		os.Setenv("DATABASE_URL", dbURL)
	}
	if redisURL := getEnvironmentDatabaseURL("redis"); redisURL != "" {
		os.Setenv("REDIS_URL", redisURL)
	}
	
	// Now process environment variables into config struct
	if err := envconfig.Process("", &config); err != nil {
		return nil, fmt.Errorf("failed to load configuration: %v", err)
	}
	
	// Apply final fallbacks if still empty
	if config.DatabaseURL == "" {
		config.DatabaseURL = "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_app"
	}
	if config.RedisURL == "" {
		config.RedisURL = "redis://localhost:6379"
	}
	
	return &config, nil
}

func main() {
	// Load appropriate environment configuration first
	if err := loadEnvironment(); err != nil {
		fmt.Printf("Warning: Could not load environment: %v\n", err)
	}
	
	// Load configuration with environment-aware database URLs
	config, err := LoadConfigWithEnvironment()
	if err != nil {
		fmt.Printf("Failed to load configuration: %v\n", err)
		os.Exit(1)
	}

	// Initialize logger
	logger, err := initLogger(config.LogLevel, config.Environment)
	if err != nil {
		fmt.Printf("Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	logger.Info("Starting billing service",
		zap.String("port", config.Port),
		zap.String("environment", config.Environment),
		zap.Bool("metrics_enabled", config.EnableMetrics))

	// Initialize database
	db, err := NewDatabaseManager(config.DatabaseURL, logger)
	if err != nil {
		logger.Fatal("Failed to initialize database", zap.Error(err))
	}
	defer db.Close()

	// Initialize Redis cache
	cache, err := NewRedisCache(config.RedisURL, logger)
	if err != nil {
		logger.Fatal("Failed to initialize Redis cache", zap.Error(err))
	}
	defer cache.Close()

	// Initialize handlers
	handlers := NewBillingHandlers(db, cache, logger)

	// Setup Gin router
	router := setupRouter(handlers, logger, config)

	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + config.Port,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in a goroutine
	go func() {
		logger.Info("Server starting", zap.String("address", srv.Addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Server failed to start", zap.Error(err))
		}
	}()

	// Wait for interrupt signal to gracefully shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Server shutting down...")

	// Create context with timeout for graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(config.GracefulTimeout)*time.Second)
	defer cancel()

	// Attempt graceful shutdown
	if err := srv.Shutdown(ctx); err != nil {
		logger.Error("Server forced to shutdown", zap.Error(err))
		os.Exit(1)
	}

	logger.Info("Server exited successfully")
}

func initLogger(logLevel, environment string) (*zap.Logger, error) {
	level, err := zapcore.ParseLevel(logLevel)
	if err != nil {
		return nil, err
	}

	config := zap.NewProductionConfig()
	config.Level.SetLevel(level)

	if environment == "development" {
		config = zap.NewDevelopmentConfig()
		config.Level.SetLevel(level)
	}

	return config.Build()
}

func setupRouter(handlers *BillingHandlers, logger *zap.Logger, config Config) *gin.Engine {
	// Set Gin mode based on environment
	if config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	} else {
		gin.SetMode(gin.DebugMode)
	}

	router := gin.New()

	// Middleware
	router.Use(gin.Recovery())
	router.Use(requestLoggerMiddleware(logger))
	router.Use(corsMiddleware())
	router.Use(handlers.RateLimitMiddleware())

	// Health check endpoint
	router.GET("/health", handlers.HealthCheck)

	// Metrics endpoint (if enabled)
	if config.EnableMetrics {
		router.GET("/metrics", gin.WrapH(promhttp.Handler()))
	}

	// API routes
	v1 := router.Group("/api/v1")
	{
		// Plan management
		v1.GET("/plans", handlers.GetAvailablePlans)

		// User-specific routes
		users := v1.Group("/users/:user_id")
		{
			// Subscription management
			users.GET("/subscription", handlers.GetUserSubscription)
			users.POST("/subscription", handlers.CreateSubscription)
			users.PUT("/subscription", handlers.UpdateSubscription)
			users.DELETE("/subscription", handlers.CancelSubscription)

			// Usage management
			users.POST("/usage", handlers.RecordUsage)
			users.GET("/quota/:resource_type", handlers.CheckQuota)
			users.GET("/usage/summary", handlers.GetUsageSummary)
			users.GET("/usage/detailed", handlers.GetDetailedUsage)

			// Billing history
			users.GET("/billing/history", handlers.GetBillingHistory)
		}
	}

	return router
}

func requestLoggerMiddleware(logger *zap.Logger) gin.HandlerFunc {
	return gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		logger.Info("Request",
			zap.String("method", param.Method),
			zap.String("path", param.Path),
			zap.Int("status", param.StatusCode),
			zap.Duration("latency", param.Latency),
			zap.String("client_ip", param.ClientIP),
			zap.String("user_agent", param.Request.UserAgent()),
		)
		return ""
	})
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, X-User-ID")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}