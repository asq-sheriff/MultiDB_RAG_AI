package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/kelseyhightower/envconfig"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"github.com/MultiDB-Chatbot/microservices/shared/models"
	"github.com/MultiDB-Chatbot/microservices/shared/middleware"
	"github.com/MultiDB-Chatbot/microservices/shared/utils"
)

// Config represents the main service configuration
type Config struct {
	Port                    string        `envconfig:"PORT" default:"8010"`
	Environment             string        `envconfig:"ENVIRONMENT" default:"development"`
	LogLevel                string        `envconfig:"LOG_LEVEL" default:"info"`
	EnableMetrics           bool          `envconfig:"ENABLE_METRICS" default:"true"`
	GracefulTimeout         int           `envconfig:"GRACEFUL_TIMEOUT" default:"30"`
	
	// Database Configuration
	PostgresURL             string        `envconfig:"DATABASE_URL" default:"postgresql://chatbot_user:secure_password@localhost:5432/chatbot_app"`
	ScyllaHosts             []string      `envconfig:"SCYLLA_HOSTS" default:"127.0.0.1"`
	ScyllaKeyspace          string        `envconfig:"SCYLLA_KEYSPACE" default:"chatbot_keyspace"`
	MongoURL                string        `envconfig:"MONGODB_URL" default:"mongodb://root:example@localhost:27017/chatbot_app?authSource=admin"`
	MongoDatabase           string        `envconfig:"MONGO_DATABASE" default:"chatbot_app"`
	RedisURL                string        `envconfig:"REDIS_URL" default:"localhost:6379"`
	RedisDB                 int           `envconfig:"REDIS_DB" default:"0"`
	MaxConnections          int           `envconfig:"MAX_CONNECTIONS" default:"50"`
	ConnectionTimeout       time.Duration `envconfig:"CONNECTION_TIMEOUT" default:"30s"`
	
	// Service Integration URLs
	EmbeddingServiceURL     string        `envconfig:"EMBEDDING_SERVICE_URL" default:"http://localhost:8005"`
	GenerationServiceURL    string        `envconfig:"GENERATION_SERVICE_URL" default:"http://localhost:8006"`
	SafetyServiceURL        string        `envconfig:"CONTENT_SAFETY_SERVICE_URL" default:"http://localhost:8007"`
	
	// Service Configuration
	ServiceConfig           models.ServiceConfig
}

func main() {
	// Load demo environment if available
	if err := utils.LoadDemoEnvironment(); err != nil {
		fmt.Printf("Warning: Could not load demo environment: %v\n", err)
	}
	
	// Load configuration
	var config Config
	if err := envconfig.Process("", &config); err != nil {
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

	logger.Info("Starting Chat History Service",
		zap.String("port", config.Port),
		zap.String("environment", config.Environment),
		zap.Bool("metrics_enabled", config.EnableMetrics),
		zap.Strings("scylla_hosts", config.ScyllaHosts),
		zap.String("scylla_keyspace", config.ScyllaKeyspace),
		zap.String("postgres_url", maskURL(config.PostgresURL)),
		zap.String("mongo_url", maskURL(config.MongoURL)))

	// Initialize database manager
	dbConfig := DatabaseConfig{
		PostgresURL:       config.PostgresURL,
		ScyllaHosts:       config.ScyllaHosts,
		ScyllaKeyspace:    config.ScyllaKeyspace,
		MongoURL:          config.MongoURL,
		MongoDatabase:     config.MongoDatabase,
		RedisURL:          config.RedisURL,
		RedisDB:           config.RedisDB,
		MaxConnections:    config.MaxConnections,
		ConnectionTimeout: config.ConnectionTimeout,
	}

	db, err := NewDatabaseManager(dbConfig, logger)
	if err != nil {
		logger.Fatal("Failed to initialize database manager", zap.Error(err))
	}
	defer db.Close()

	// Load service configuration from environment
	if err := envconfig.Process("", &config.ServiceConfig); err != nil {
		logger.Fatal("Failed to load service configuration", zap.Error(err))
	}

	// Initialize chat history service
	serviceConfig := ServiceConfig{
		MaxMessageLength:      10000,
		MaxHistoryLimit:       100,
		DefaultHistoryLimit:   50,
		CacheSessionTTL:       24 * time.Hour,
		RateLimitPerHour:      1000,
		EnableSafetyAnalysis:  true,
		EnableEmotionAnalysis: true,
		EnableRAG:             true,
	}
	
	chatService := NewChatHistoryService(
		db, 
		logger, 
		serviceConfig,
		config.EmbeddingServiceURL,
		config.GenerationServiceURL,
		config.SafetyServiceURL,
	)

	// Initialize handlers
	handlers := NewChatHistoryHandlers(chatService, logger)

	// Setup HTTP server
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

// initLogger initializes the logger with appropriate configuration
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

// setupRouter sets up the HTTP router with all endpoints
func setupRouter(handlers *ChatHistoryHandlers, logger *zap.Logger, config Config) *gin.Engine {
	// Set Gin mode based on environment
	if config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	} else {
		gin.SetMode(gin.DebugMode)
	}

	router := gin.New()

	// Global middleware
	router.Use(gin.Recovery())
	router.Use(middleware.LoggingMiddleware())
	router.Use(middleware.CORSMiddleware())
	router.Use(middleware.RequestTimingMiddleware())

	// Health check endpoint
	router.GET("/health", handlers.HealthCheck)

	// Metrics endpoint (if enabled)
	if config.EnableMetrics {
		router.GET("/metrics", gin.WrapH(promhttp.Handler()))
	}

	// API routes
	v1 := router.Group("/api/v1")
	{
		// Core chat endpoints
		chat := v1.Group("/chat")
		{
			// Message processing
			chat.POST("/message", handlers.SendMessage)
			chat.GET("/history", handlers.GetHistory)
			chat.POST("/feedback", handlers.SubmitFeedback)

			// Enhanced endpoints (Gateway-style)
			chat.GET("/emotion/history/:session_id", handlers.GetEmotionHistory)
			chat.POST("/safety/test", handlers.AnalyzeSafety)

			// Session management
			chat.POST("/sessions", handlers.CreateSession)
			chat.GET("/sessions/:session_id", handlers.GetSession)
			chat.DELETE("/sessions/:session_id", handlers.EndSession)

			// Analytics and monitoring
			chat.GET("/stats", handlers.GetStats)
			chat.GET("/analytics/:session_id", handlers.GetSessionAnalytics)
		}
	}
	
	// Handle API Gateway proxy calls (path rewritten to remove /api/v1/chat prefix)
	router.POST("/message", handlers.SendMessage)
	router.GET("/history", handlers.GetHistory)
	router.POST("/feedback", handlers.SubmitFeedback)
	router.GET("/emotion/history/:session_id", handlers.GetEmotionHistory)
	router.POST("/safety/test", handlers.AnalyzeSafety)
	router.POST("/sessions", handlers.CreateSession)
	router.GET("/sessions/:session_id", handlers.GetSession)
	router.DELETE("/sessions/:session_id", handlers.EndSession)
	router.GET("/stats", handlers.GetStats)
	router.GET("/analytics/:session_id", handlers.GetSessionAnalytics)

	// Service info endpoint
	router.GET("/info", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "Chat History Service",
			"version": "1.0.0",
			"status":  "running",
			"endpoints": map[string][]string{
				"core": {
					"POST /api/v1/chat/message",
					"GET /api/v1/chat/history",
					"POST /api/v1/chat/feedback",
				},
				"sessions": {
					"POST /api/v1/chat/sessions",
					"GET /api/v1/chat/sessions/:session_id",
					"DELETE /api/v1/chat/sessions/:session_id",
				},
				"analytics": {
					"GET /api/v1/chat/stats",
					"GET /api/v1/chat/analytics/:session_id",
					"GET /api/v1/chat/emotion/history/:session_id",
				},
				"utility": {
					"GET /health",
					"POST /api/v1/chat/safety/test",
				},
			},
		})
	})

	return router
}

// maskURL masks sensitive parts of URLs for logging
func maskURL(url string) string {
	if len(url) == 0 {
		return url
	}
	
	// Simple masking - replace credentials with ***
	// This is a basic implementation; in production, you might want a more robust solution
	masked := url
	if len(url) > 20 {
		start := url[:10]
		end := url[len(url)-10:]
		masked = start + "***" + end
	}
	
	return masked
}