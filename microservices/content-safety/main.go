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
	"github.com/MultiDB-Chatbot/microservices/shared/utils"
)

// Config represents the content safety service configuration
type Config struct {
	Port            string `envconfig:"PORT" default:"8007"`
	Environment     string `envconfig:"ENVIRONMENT" default:"development"`
	LogLevel        string `envconfig:"LOG_LEVEL" default:"info"`
	EnableMetrics   bool   `envconfig:"ENABLE_METRICS" default:"true"`
	GracefulTimeout int    `envconfig:"GRACEFUL_TIMEOUT" default:"30"`
	HIPAAMode       bool   `envconfig:"HIPAA_MODE" default:"true"`
	CrisisThreshold float64 `envconfig:"CRISIS_THRESHOLD" default:"0.8"`
}

// ContentSafetyService handles all safety analysis operations
type ContentSafetyService struct {
	config          *Config
	logger          *zap.Logger
	safetyAnalyzer  *SafetyAnalyzer
	emotionAnalyzer *EmotionAnalyzer
	phiAnalyzer     *PHIAnalyzer
}

// NewContentSafetyService creates a new content safety service
func NewContentSafetyService(config *Config, logger *zap.Logger) *ContentSafetyService {
	return &ContentSafetyService{
		config:          config,
		logger:          logger,
		safetyAnalyzer:  NewSafetyAnalyzer(logger),
		emotionAnalyzer: NewEmotionAnalyzer(logger),
		phiAnalyzer:     NewPHIAnalyzer(logger),
	}
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status      string                 `json:"status"`
	Service     string                 `json:"service"`
	Timestamp   time.Time              `json:"timestamp"`
	Analyzers   map[string]string      `json:"analyzers"`
	Capabilities []string              `json:"capabilities"`
	Details     map[string]interface{} `json:"details,omitempty"`
}

// setupRouter configures all routes for the content safety service
func (css *ContentSafetyService) setupRouter() *gin.Engine {
	if css.config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()
	
	// Middleware
	router.Use(gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		return fmt.Sprintf("%s - [%s] \"%s %s %s %d %s \"%s\" %s\"\n",
			param.ClientIP,
			param.TimeStamp.Format(time.RFC1123),
			param.Method,
			param.Path,
			param.Request.Proto,
			param.StatusCode,
			param.Latency,
			param.Request.UserAgent(),
			param.ErrorMessage,
		)
	}))
	router.Use(gin.Recovery())

	// Health endpoint
	router.GET("/health", css.healthCheck)
	
	// Metrics endpoint
	if css.config.EnableMetrics {
		router.GET("/metrics", gin.WrapH(promhttp.Handler()))
	}

	// Safety analysis endpoints
	router.POST("/safety/analyze", css.analyzeSafety)
	router.POST("/emotion/analyze", css.analyzeEmotion) 
	router.POST("/phi/detect", css.detectPHI)
	router.POST("/analyze/combined", css.analyzeCombined)
	router.GET("/safety/guidelines", css.getSafetyGuidelines)

	// Service info
	router.GET("/info", css.getServiceInfo)

	return router
}

// healthCheck provides service health status
func (css *ContentSafetyService) healthCheck(c *gin.Context) {
	css.logger.Debug("Health check requested")
	
	analyzers := map[string]string{
		"safety_analyzer":  "ready",
		"emotion_analyzer": "ready", 
		"phi_analyzer":     "ready",
	}

	capabilities := []string{
		"content_safety",
		"emotion_analysis", 
		"phi_detection",
		"crisis_detection",
		"hipaa_compliance",
		"therapeutic_analysis",
	}

	response := HealthResponse{
		Status:       "healthy",
		Service:      "content-safety-microservice-go",
		Timestamp:    time.Now().UTC(),
		Analyzers:    analyzers,
		Capabilities: capabilities,
	}

	c.JSON(http.StatusOK, response)
}

// getServiceInfo provides detailed service information
func (css *ContentSafetyService) getServiceInfo(c *gin.Context) {
	info := map[string]interface{}{
		"service_name":     "Content Safety Microservice",
		"version":          "2.0.0-go",
		"language":         "Go",
		"port":             css.config.Port,
		"environment":      css.config.Environment,
		"hipaa_mode":       css.config.HIPAAMode,
		"crisis_threshold": css.config.CrisisThreshold,
		"capabilities": map[string]interface{}{
			"phi_detection": map[string]interface{}{
				"hipaa_identifiers": 18,
				"detection_methods": []string{"regex", "pattern_matching", "context_analysis"},
				"encryption":        "AES-256-GCM",
			},
			"emotion_analysis": map[string]interface{}{
				"emotions":          []string{"happy", "sad", "angry", "anxious", "calm", "lonely", "frustrated", "excited", "content", "neutral"},
				"valence_range":     []float64{-1.0, 1.0},
				"arousal_range":     []float64{-1.0, 1.0},
				"crisis_detection":  true,
			},
			"safety_analysis": map[string]interface{}{
				"risk_levels":       []string{"none", "low", "medium", "high", "critical"},
				"crisis_patterns":   []string{"suicidal_ideation", "self_harm", "violence", "emergency"},
				"intervention_types": []string{"immediate", "high_priority", "moderate", "supportive"},
			},
		},
	}

	c.JSON(http.StatusOK, info)
}

func main() {
	// Load demo environment if available
	if err := utils.LoadDemoEnvironment(); err != nil {
		fmt.Printf("Warning: Could not load demo environment: %v\n", err)
	}
	
	// Load configuration
	var config Config
	if err := envconfig.Process("", &config); err != nil {
		panic(fmt.Sprintf("Failed to load configuration: %v", err))
	}

	// Initialize logger
	logger, err := initLogger(config.LogLevel, config.Environment)
	if err != nil {
		panic(fmt.Sprintf("Failed to initialize logger: %v", err))
	}

	logger.Info("🛡️ Starting Content Safety Microservice",
		zap.String("port", config.Port),
		zap.String("environment", config.Environment),
		zap.Bool("hipaa_mode", config.HIPAAMode),
	)

	// Create service
	service := NewContentSafetyService(&config, logger)
	
	// Setup router
	router := service.setupRouter()

	// Create HTTP server
	server := &http.Server{
		Addr:         ":" + config.Port,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in goroutine
	go func() {
		logger.Info("🚀 Content Safety service starting", zap.String("address", server.Addr))
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("❌ Failed to start server", zap.Error(err))
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("🛑 Shutting down Content Safety service...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(config.GracefulTimeout)*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		logger.Error("❌ Server forced to shutdown", zap.Error(err))
	}

	logger.Info("✅ Content Safety service stopped")
}

// initLogger initializes the logger with appropriate configuration
func initLogger(logLevel, environment string) (*zap.Logger, error) {
	var config zap.Config

	if environment == "production" {
		config = zap.NewProductionConfig()
	} else {
		config = zap.NewDevelopmentConfig()
		config.EncoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	}

	// Set log level
	switch logLevel {
	case "debug":
		config.Level = zap.NewAtomicLevelAt(zap.DebugLevel)
	case "info":
		config.Level = zap.NewAtomicLevelAt(zap.InfoLevel)
	case "warn":
		config.Level = zap.NewAtomicLevelAt(zap.WarnLevel)
	case "error":
		config.Level = zap.NewAtomicLevelAt(zap.ErrorLevel)
	default:
		config.Level = zap.NewAtomicLevelAt(zap.InfoLevel)
	}

	return config.Build()
}