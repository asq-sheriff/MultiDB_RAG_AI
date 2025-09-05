package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
	"github.com/MultiDB-Chatbot/microservices/shared/models"
	"github.com/MultiDB-Chatbot/microservices/shared/database"
)

// Database interface for testability
type DatabaseInterface interface {
	Close() error
	Ping() error
	CreatePatientConsent(params models.CreatePatientConsentParams) (*models.PatientConsent, error)
	RevokeConsent(params models.RevokeConsentParams) (bool, error)
	GetPatientConsents(params models.GetPatientConsentsParams) ([]models.PatientConsent, error)
	GetPatientConsent(params models.GetPatientConsentParams) (*models.PatientConsent, error)
	GetAllPatientConsents(params models.GetAllPatientConsentsParams) ([]models.PatientConsent, error)
	UpdateConsentStatus(params models.UpdateConsentStatusParams) (bool, error)
	checkDataAccess(params models.CheckDataAccessParams) (*models.AccessDecision, error)
	LogConsentAction(params models.LogConsentActionParams) error
}

// Cache interface for testability
type CacheInterface interface {
	Close() error
	Set(key, value string, expiration time.Duration) error
	Get(key string) (string, error)
	Delete(key string) error
	Exists(key string) (bool, error)
	InvalidatePatientConsents(patientID uuid.UUID) error
	CheckRateLimit(key string, limit int, window time.Duration) (bool, error)
}

type ConsentService struct {
	logger   *zap.Logger
	db       *database.DatabaseManager
	cache    *RedisCache
	config   *Config
}

type Config struct {
	Port           string `env:"PORT" envDefault:"8080"`
	DatabaseURL    string `env:"DATABASE_URL" envDefault:"postgres://chatbot_user:chatbot_password@localhost:5432/chatbot_app"`
	RedisURL       string `env:"REDIS_URL" envDefault:"redis://localhost:6379"`
	LogLevel       string `env:"LOG_LEVEL" envDefault:"info"`
	Environment    string `env:"ENVIRONMENT" envDefault:"development"`
	HIPAAMode      bool   `env:"HIPAA_MODE" envDefault:"true"`
}

func main() {
	// Initialize logger
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// Load configuration
	config := loadConfig()
	
	// Initialize database manager
	dbManager, err := database.NewDatabaseManager(config.DatabaseURL)
	if err != nil {
		logger.Fatal("Failed to initialize database", zap.Error(err))
	}
	
	// Initialize cache
	cache, err := NewRedisCache(config.RedisURL)
	if err != nil {
		logger.Fatal("Failed to initialize cache", zap.Error(err))
	}
	
	// Initialize services
	service := &ConsentService{
		logger: logger,
		config: config,
		db:     dbManager,
		cache:  cache,
	}
	defer service.cleanup()
	
	// Setup HTTP server
	router := setupRoutes(service)
	
	srv := &http.Server{
		Addr:         ":" + config.Port,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
	
	// Graceful shutdown
	go func() {
		sigint := make(chan os.Signal, 1)
		signal.Notify(sigint, os.Interrupt)
		<-sigint
		
		logger.Info("Shutting down server...")
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		
		if err := srv.Shutdown(ctx); err != nil {
			logger.Fatal("Server shutdown failed", zap.Error(err))
		}
	}()
	
	logger.Info("Starting HIPAA-compliant consent service", 
		zap.String("port", config.Port),
		zap.Bool("hipaa_mode", config.HIPAAMode))
	
	if err := srv.ListenAndServe(); err != http.ErrServerClosed {
		logger.Fatal("Server failed to start", zap.Error(err))
	}
}

func setupRoutes(service *ConsentService) *gin.Engine {
	if service.config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}
	
	router := gin.New()
	router.Use(gin.Logger(), gin.Recovery())
	
	// Health checks
	router.GET("/health", service.healthCheck)
	router.GET("/ready", service.readinessCheck)
	
	// Metrics
	router.GET("/metrics", gin.WrapH(promhttp.Handler()))
	
	// API v1 routes
	v1 := router.Group("/v1")
	{
		// HIPAA-compliant consent management
		consent := v1.Group("/consent")
		{
			consent.POST("/create", service.createConsent)
			consent.DELETE("/:consent_id", service.revokeConsent)
			consent.GET("/patient/:patient_id", service.getPatientConsents)
			consent.POST("/validate", service.validateAccess)
		}
		
		// Patient rights management
		rights := v1.Group("/patient-rights")
		{
			rights.GET("/dashboard/:patient_id", service.getPatientRightsDashboard)
			rights.GET("/access-log/:patient_id", service.getAccessLog)
			rights.POST("/family-access", service.grantFamilyAccess)
		}
		
		// Relationship management
		relationships := v1.Group("/relationships")
		{
			relationships.POST("/treatment", service.createTreatmentRelationship)
			relationships.POST("/family", service.createFamilyRelationship)
			relationships.GET("/active/:patient_id", service.getActiveRelationships)
		}
	}
	
	return router
}

func (s *ConsentService) cleanup() {
	if s.db != nil {
		s.db.Close()
	}
	if s.cache != nil {
		s.cache.Close()
	}
}

func loadConfig() *Config {
	// Implementation for loading config from environment
	return &Config{
		Port:        getEnv("PORT", "8080"),
		DatabaseURL: getEnv("DATABASE_URL", "postgres://chatbot_user:chatbot_password@localhost:5432/chatbot_app"),
		RedisURL:    getEnv("REDIS_URL", "redis://localhost:6379"),
		LogLevel:    getEnv("LOG_LEVEL", "info"),
		Environment: getEnv("ENVIRONMENT", "development"),
		HIPAAMode:   getEnv("HIPAA_MODE", "true") == "true",
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}