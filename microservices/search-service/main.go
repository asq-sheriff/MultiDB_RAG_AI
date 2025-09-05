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

type Config struct {
	Port                    string        `envconfig:"PORT" default:"8001"`
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
	KnowledgeServiceURL     string        `envconfig:"KNOWLEDGE_SERVICE_URL" default:"http://localhost:8000"`
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
	var config Config
	if err := envconfig.Process("", &config); err != nil {
		fmt.Printf("Failed to load configuration: %v\n", err)
		os.Exit(1)
	}

	logger, err := initLogger(config.LogLevel, config.Environment)
	if err != nil {
		fmt.Printf("Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	logger.Info("Starting Search Service",
		zap.String("port", config.Port),
		zap.String("environment", config.Environment),
		zap.Bool("metrics_enabled", config.EnableMetrics),
		zap.Strings("scylla_hosts", config.ScyllaHosts),
		zap.String("postgres_url", maskURL(config.PostgresURL)),
		zap.String("mongo_url", maskURL(config.MongoURL)))

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

	if err := envconfig.Process("", &config.ServiceConfig); err != nil {
		logger.Fatal("Failed to load service configuration", zap.Error(err))
	}

	serviceConfig := ServiceConfig{
		MaxQueryLength:        500,
		MaxResultsLimit:       50,
		DefaultResultsLimit:   5,
		CacheResultsTTL:       1 * time.Hour,
		RateLimitPerMinute:    60,
		EnableSafetyAnalysis:  true,
		EnableQuotaCheck:      true,
	}
	
	searchService := NewSearchService(
		db, 
		logger, 
		serviceConfig,
		config.KnowledgeServiceURL,
		config.EmbeddingServiceURL,
		config.GenerationServiceURL,
		config.SafetyServiceURL,
	)

	handlers := NewSearchHandlers(searchService, logger)

	router := setupRouter(handlers, logger, config)

	srv := &http.Server{
		Addr:         ":" + config.Port,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		logger.Info("Server starting", zap.String("address", srv.Addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Server failed to start", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Server shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(config.GracefulTimeout)*time.Second)
	defer cancel()

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

func setupRouter(handlers *SearchHandlers, logger *zap.Logger, config Config) *gin.Engine {
	if config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	} else {
		gin.SetMode(gin.DebugMode)
	}

	router := gin.New()

	router.Use(gin.Recovery())
	router.Use(middleware.LoggingMiddleware())
	router.Use(middleware.CORSMiddleware())
	router.Use(middleware.RequestTimingMiddleware())

	router.GET("/health", handlers.HealthCheck)

	if config.EnableMetrics {
		router.GET("/metrics", gin.WrapH(promhttp.Handler()))
	}

	// Handle both direct API calls and API Gateway proxy calls
	v1 := router.Group("/api/v1")
	{
		search := v1.Group("/search")
		{
			search.POST("/", handlers.Search)
			search.POST("/semantic", handlers.SemanticSearch)
			search.GET("/suggestions", handlers.GetSearchSuggestions)
		}
	}
	
	// Handle API Gateway proxy calls (path rewritten to remove /api/v1/search prefix)
	router.POST("/", handlers.Search)
	router.POST("/semantic", handlers.SemanticSearch)
	router.GET("/suggestions", handlers.GetSearchSuggestions)

	// Service info endpoint (only for GET requests, POST handled by search handler)
	router.GET("/info", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "Search Service",
			"version": "1.0.0",
			"status":  "running",
			"endpoints": map[string][]string{
				"core": {
					"POST /api/v1/search/",
					"POST /api/v1/search/semantic",
					"GET /api/v1/search/suggestions",
				},
				"utility": {
					"GET /health",
				},
			},
		})
	})

	return router
}

func maskURL(url string) string {
	if len(url) == 0 {
		return url
	}
	
	masked := url
	if len(url) > 20 {
		start := url[:10]
		end := url[len(url)-10:]
		masked = start + "***" + end
	}
	
	return masked
}