// Package main provides the User Subscription Service for managing subscription tiers and usage quotas
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
)

// ServiceConfig holds configuration for the subscription service
type ServiceConfig struct {
	Port                string
	Environment         string
	PostgreSQLHost      string
	PostgreSQLPort      string
	PostgreSQLUser      string
	PostgreSQLPassword  string
	PostgreSQLDB        string
	RedisHost          string
	RedisPort          string
	RedisPassword      string
	RedisDB            int
	LogLevel           string
	EnableMetrics      bool
	EnableDebug        bool
	GracefulTimeout    time.Duration
	ReadTimeout        time.Duration
	WriteTimeout       time.Duration
}

// loadConfig loads configuration from environment variables
func loadConfig() *ServiceConfig {
	// Parse Redis DB
	redisDB, err := strconv.Atoi(getEnvVar("REDIS_DB", "0"))
	if err != nil {
		redisDB = 0
	}

	// Parse timeouts
	gracefulTimeout, _ := time.ParseDuration(getEnvVar("GRACEFUL_SHUTDOWN_TIMEOUT", "30s"))
	readTimeout, _ := time.ParseDuration(getEnvVar("HTTP_READ_TIMEOUT", "30s"))
	writeTimeout, _ := time.ParseDuration(getEnvVar("HTTP_WRITE_TIMEOUT", "30s"))

	return &ServiceConfig{
		Port:                getEnvVar("PORT", "8010"),
		Environment:         getEnvVar("ENVIRONMENT", "development"),
		PostgreSQLHost:      getEnvVar("POSTGRES_HOST", "localhost"),
		PostgreSQLPort:      getEnvVar("POSTGRES_PORT", "5432"),
		PostgreSQLUser:      getEnvVar("POSTGRES_USER", "chatbot_user"),
		PostgreSQLPassword:  getEnvVar("POSTGRES_PASSWORD", "secure_password"),
		PostgreSQLDB:        getEnvVar("POSTGRES_DB", "chatbot_app"),
		RedisHost:          getEnvVar("REDIS_HOST", "localhost"),
		RedisPort:          getEnvVar("REDIS_PORT", "6379"),
		RedisPassword:      getEnvVar("REDIS_PASSWORD", ""),
		RedisDB:            redisDB,
		LogLevel:           getEnvVar("LOG_LEVEL", "info"),
		EnableMetrics:      getEnvVar("ENABLE_METRICS", "true") == "true",
		EnableDebug:        getEnvVar("ENABLE_DEBUG", "false") == "true",
		GracefulTimeout:    gracefulTimeout,
		ReadTimeout:        readTimeout,
		WriteTimeout:       writeTimeout,
	}
}

func main() {
	// Load configuration
	config := loadConfig()

	// Set Gin mode based on environment
	if config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	} else if config.EnableDebug {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.TestMode)
	}

	// Initialize database manager
	log.Println("🗄️ Initializing database connections...")
	db, err := NewDatabaseManager()
	if err != nil {
		log.Fatalf("❌ Failed to initialize database manager: %v", err)
	}
	defer db.Close()

	// Test database connections
	health := db.HealthCheck()
	log.Printf("📊 Database health check: %+v", health)

	// Initialize subscription service
	log.Println("🔧 Initializing subscription service...")
	subscriptionService := NewSubscriptionService(db)

	// Initialize HTTP handlers
	handlers := NewSubscriptionHandlers(subscriptionService)

	// Create Gin router
	r := gin.New()

	// Setup middleware
	handlers.SetupMiddleware(r)

	// Register routes
	handlers.RegisterRoutes(r)

	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + config.Port,
		Handler:      r,
		ReadTimeout:  config.ReadTimeout,
		WriteTimeout: config.WriteTimeout,
	}

	// Start server in a goroutine
	go func() {
		log.Printf("🚀 User Subscription Service starting on port %s", config.Port)
		log.Printf("🌐 Environment: %s", config.Environment)
		log.Printf("🔗 Health check: http://localhost:%s/health", config.Port)
		log.Printf("📖 API docs: http://localhost:%s/api/v1/plans", config.Port)

		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("❌ Failed to start server: %v", err)
		}
	}()

	// Start background processes
	go startBackgroundProcesses(subscriptionService, config)

	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("🛑 Shutting down User Subscription Service...")

	// Create a deadline for shutdown
	ctx, cancel := context.WithTimeout(context.Background(), config.GracefulTimeout)
	defer cancel()

	// Gracefully shutdown the server
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("❌ Server forced to shutdown: %v", err)
	}

	log.Println("✅ User Subscription Service stopped")
}

// startBackgroundProcesses starts background tasks for subscription management
func startBackgroundProcesses(service *SubscriptionService, config *ServiceConfig) {
	log.Println("🔄 Starting background processes...")

	// Start cache monitoring and warming
	ctx := context.Background()
	if cache := service.db.GetCache(); cache != nil {
		go cache.StartMonitoring(ctx)
		log.Println("📊 Cache monitoring and warming started")
	}

	// Process subscription renewals every hour
	renewalTicker := time.NewTicker(1 * time.Hour)
	defer renewalTicker.Stop()

	// Process expired subscriptions every 30 minutes
	expiredTicker := time.NewTicker(30 * time.Minute)
	defer expiredTicker.Stop()

	// Health check ticker (every 5 minutes)
	healthTicker := time.NewTicker(5 * time.Minute)
	defer healthTicker.Stop()

	for {
		select {
		case <-renewalTicker.C:
			log.Println("🔄 Processing subscription renewals...")
			if err := service.ProcessSubscriptionRenewals(); err != nil {
				log.Printf("❌ Error processing renewals: %v", err)
			} else {
				log.Println("✅ Subscription renewals processed")
			}

		case <-expiredTicker.C:
			log.Println("⏰ Processing expired subscriptions...")
			if err := service.ProcessExpiredSubscriptions(); err != nil {
				log.Printf("❌ Error processing expired subscriptions: %v", err)
			} else {
				log.Println("✅ Expired subscriptions processed")
			}

		case <-healthTicker.C:
			health := service.db.HealthCheck()
			status := "healthy"
			for _, v := range health {
				if v == "unhealthy" {
					status = "unhealthy"
					break
				}
			}
			if status == "unhealthy" {
				log.Printf("⚠️ Service health check failed: %+v", health)
			}
		}
	}
}

// getEnvVar gets an environment variable with a fallback default value
func getEnvVar(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// printServiceInfo prints service information and available endpoints
func printServiceInfo(config *ServiceConfig) {
	fmt.Printf(`
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        🏥 User Subscription Service                           ║
║                       Healthcare AI Platform - v1.0.0                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ 🌐 Port:           %s                                                    ║
║ 🏃 Environment:    %s                                            ║
║ 💾 PostgreSQL:     %s:%s                                        ║
║ 🔴 Redis:          %s:%s                                        ║
║ 📊 Metrics:        %v                                               ║
║ 🐛 Debug:          %v                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                              📡 API Endpoints                                ║
║                                                                               ║
║ 🔍 Health Check:          GET  /health                                       ║
║ 📋 List Plans:            GET  /api/v1/plans                                 ║
║ 📊 Plan Features:         GET  /api/v1/plans/{plan}/features                 ║
║                                                                               ║
║ 👤 User Subscription:     GET  /api/v1/subscriptions/user/{user_id}          ║
║ ➕ Create Subscription:   POST /api/v1/subscriptions                         ║
║ ⬆️ Upgrade Plan:          PUT  /api/v1/subscriptions/user/{user_id}/upgrade  ║
║ ⬇️ Downgrade Plan:        PUT  /api/v1/subscriptions/user/{user_id}/downgrade║
║ ❌ Cancel Subscription:   DEL  /api/v1/subscriptions/user/{user_id}/cancel   ║
║ 🔄 Reactivate:            POST /api/v1/subscriptions/user/{user_id}/reactivate║
║ ⏸️ Pause:                 POST /api/v1/subscriptions/user/{user_id}/pause    ║
║ ▶️ Resume:                POST /api/v1/subscriptions/user/{user_id}/resume   ║
║                                                                               ║
║ 📈 Record Usage:          POST /api/v1/usage/record                          ║
║ 🔢 Check Quota:           GET  /api/v1/usage/user/{user_id}/quota/{resource} ║
║ 📊 Usage Summary:         GET  /api/v1/usage/user/{user_id}/summary          ║
║                                                                               ║
║ 🔐 Admin Metrics:         GET  /api/v1/admin/metrics                         ║
║ 🔄 Process Renewals:      POST /api/v1/admin/renewals/process                ║
║ ⏰ Process Expired:       POST /api/v1/admin/expired/process                 ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                             📦 Subscription Tiers                            ║
║                                                                               ║
║ 🆓 Free:        100 msgs,    500 API calls,    1GB storage                  ║
║ 💼 Pro:       5,000 msgs, 10,000 API calls,   10GB storage - $49.99/month   ║
║ 🏢 Enterprise: 50k msgs,   100k API calls,   100GB storage - $199.99/month  ║
║                                                                               ║
║ Features: RAG search, emotion analysis, crisis intervention, HIPAA compliance║
╚═══════════════════════════════════════════════════════════════════════════════╝

`,
		config.Port,
		config.Environment,
		config.PostgreSQLHost, config.PostgreSQLPort,
		config.RedisHost, config.RedisPort,
		config.EnableMetrics,
		config.EnableDebug,
	)
}

// init function runs before main()
func init() {
	// Set up logging
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.SetPrefix("[SUBSCRIPTION-SERVICE] ")
	
	// Print startup banner
	config := loadConfig()
	printServiceInfo(config)
}