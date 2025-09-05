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
)

// Config represents the service configuration
type Config struct {
	Port               string `envconfig:"PORT" default:"8080"`
	Environment        string `envconfig:"ENVIRONMENT" default:"development"`
	RedisURL           string `envconfig:"REDIS_URL" default:"redis://localhost:6379"`
	LogLevel           string `envconfig:"LOG_LEVEL" default:"info"`
	WorkerCount        int    `envconfig:"WORKER_COUNT" default:"3"`
	EnableMetrics      bool   `envconfig:"ENABLE_METRICS" default:"true"`
	GracefulTimeout    int    `envconfig:"GRACEFUL_TIMEOUT" default:"30"`
	TaskPurgeInterval  int    `envconfig:"TASK_PURGE_INTERVAL_HOURS" default:"24"`
}

func main() {
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

	logger.Info("Starting background tasks service",
		zap.String("port", config.Port),
		zap.String("environment", config.Environment),
		zap.Int("worker_count", config.WorkerCount),
		zap.Bool("metrics_enabled", config.EnableMetrics))

	// Initialize task queue
	queue, err := NewTaskQueue(config.RedisURL, logger)
	if err != nil {
		logger.Fatal("Failed to initialize task queue", zap.Error(err))
	}
	defer queue.Close()

	// Initialize notification service
	notificationSvc, err := NewNotificationService(config.RedisURL, logger)
	if err != nil {
		logger.Fatal("Failed to initialize notification service", zap.Error(err))
	}
	defer notificationSvc.Close()

	// Initialize worker pool
	workerPool := NewWorkerPool(config.WorkerCount, queue, notificationSvc, logger)

	// Start worker pool
	workerPool.Start()
	defer workerPool.Stop()

	// Initialize handlers
	handlers := NewBackgroundTaskHandlers(queue, workerPool, notificationSvc, logger)

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

	// Start periodic task purging
	go startTaskPurging(queue, logger, config.TaskPurgeInterval)

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

// initLogger initializes the logger
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

// setupRouter sets up the HTTP router
func setupRouter(handlers *BackgroundTaskHandlers, logger *zap.Logger, config Config) *gin.Engine {
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
	router.Use(RequestTimingMiddleware())

	// Health check endpoint
	router.GET("/health", handlers.HealthCheck)

	// Metrics endpoint (if enabled)
	if config.EnableMetrics {
		router.GET("/metrics", gin.WrapH(promhttp.Handler()))
	}

	// API routes
	v1 := router.Group("/api/v1")
	{
		// Task submission endpoints
		v1.POST("/tasks", handlers.SubmitTask)
		v1.POST("/tasks/data-analysis", handlers.SubmitDataAnalysisTask)
		v1.POST("/tasks/research", handlers.SubmitResearchTask)

		// Task status endpoints
		v1.GET("/tasks/:task_id", handlers.GetTaskStatus)
		v1.GET("/users/:user_id/tasks", handlers.GetUserTasks)

		// Notification endpoints
		v1.GET("/users/:user_id/notifications", handlers.GetNotifications)
		v1.DELETE("/users/:user_id/notifications", handlers.ClearNotifications)

		// Statistics and monitoring endpoints
		v1.GET("/stats", handlers.GetServiceStats)
		v1.GET("/workers", handlers.GetWorkerStats)
		v1.GET("/workers/:worker_id", handlers.GetWorkerStats)
		v1.GET("/analytics", handlers.GetAnalytics)

		// Administrative endpoints
		v1.DELETE("/tasks/purge", handlers.PurgeTasks)
	}

	return router
}

// requestLoggerMiddleware logs HTTP requests
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

// corsMiddleware adds CORS headers
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

// startTaskPurging starts periodic task purging
func startTaskPurging(queue *TaskQueue, logger *zap.Logger, intervalHours int) {
	ticker := time.NewTicker(time.Duration(intervalHours) * time.Hour)
	defer ticker.Stop()

	logger.Info("Started task purging", 
		zap.Int("interval_hours", intervalHours))

	for {
		select {
		case <-ticker.C:
			// Purge tasks older than 48 hours
			deleted, err := queue.PurgeCompletedTasks(48 * time.Hour)
			if err != nil {
				logger.Error("Failed to purge tasks", zap.Error(err))
			} else if deleted > 0 {
				logger.Info("Purged old completed tasks", zap.Int("count", deleted))
			}
		}
	}
}