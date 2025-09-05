package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

type SimpleConfig struct {
	Port                         string
	AuthRBACServiceURL           string
	ConsentServiceURL            string
	ChatHistoryServiceURL        string
	AuditLoggingServiceURL       string
	BillingServiceURL            string
	SearchServiceURL             string
	EmbeddingServiceURL          string
	GenerationServiceURL         string
	ContentSafetyServiceURL      string
	EmergencyAccessServiceURL    string
	RelationshipManagementServiceURL string
	UserSubscriptionServiceURL   string
	BackgroundTasksServiceURL    string
	ChatServiceURL               string
}

func loadSimpleConfig() *SimpleConfig {
	return &SimpleConfig{
		Port:                         getEnvSimple("PORT", "8090"),
		AuthRBACServiceURL:           getEnvSimple("AUTH_RBAC_SERVICE_URL", "http://localhost:8081"),
		ConsentServiceURL:            getEnvSimple("CONSENT_SERVICE_URL", "http://localhost:8083"),
		ChatHistoryServiceURL:        getEnvSimple("CHAT_HISTORY_SERVICE_URL", "http://localhost:8010"),
		AuditLoggingServiceURL:       getEnvSimple("AUDIT_LOGGING_SERVICE_URL", "http://localhost:8084"),
		BillingServiceURL:            getEnvSimple("BILLING_SERVICE_URL", "http://localhost:8085"),
		SearchServiceURL:             getEnvSimple("SEARCH_SERVICE_URL", "http://localhost:8001"),
		EmbeddingServiceURL:          getEnvSimple("EMBEDDING_SERVICE_URL", "http://localhost:8005"),
		GenerationServiceURL:         getEnvSimple("GENERATION_SERVICE_URL", "http://localhost:8006"),
		ContentSafetyServiceURL:      getEnvSimple("CONTENT_SAFETY_SERVICE_URL", "http://localhost:8007"),
		EmergencyAccessServiceURL:    getEnvSimple("EMERGENCY_ACCESS_SERVICE_URL", "http://localhost:8082"),
		RelationshipManagementServiceURL: getEnvSimple("RELATIONSHIP_MANAGEMENT_SERVICE_URL", "http://localhost:8087"),
		UserSubscriptionServiceURL:   getEnvSimple("USER_SUBSCRIPTION_SERVICE_URL", "http://localhost:8010"),
		BackgroundTasksServiceURL:    getEnvSimple("BACKGROUND_TASKS_SERVICE_URL", "http://localhost:8086"),
		ChatServiceURL:               getEnvSimple("CHAT_SERVICE_URL", "http://localhost:8002"),
	}
}

func getEnvSimple(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func createSimpleProxyHandler(targetURL string) gin.HandlerFunc {
	target, err := url.Parse(targetURL)
	if err != nil {
		log.Printf("❌ Failed to parse target URL %s: %v", targetURL, err)
		return func(c *gin.Context) {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Service configuration error",
			})
		}
	}

	proxy := httputil.NewSingleHostReverseProxy(target)
	
	// Custom director to handle path rewriting
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)
		// Remove /api/v1/{service} prefix to get the actual path
		// e.g., /api/v1/auth/health -> /health
		parts := strings.Split(req.URL.Path, "/")
		if len(parts) >= 4 && parts[1] == "api" && parts[2] == "v1" {
			// Reconstruct path without /api/v1/{service}
			newPath := "/" + strings.Join(parts[4:], "/")
			if newPath == "/" && len(parts) == 4 {
				// If no path after service name, default to "/"
				newPath = "/"
			}
			req.URL.Path = newPath
		}
	}

	// Custom error handler
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		log.Printf("⚠️ Proxy error for %s: %v", targetURL, err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway)
		w.Write([]byte(`{"error": "Service unavailable", "service": "` + targetURL + `"}`))
	}

	return gin.WrapH(proxy)
}

func setupSimpleRouter(config *SimpleConfig) *gin.Engine {
	gin.SetMode(gin.DebugMode)
	router := gin.New()

	// Global middleware
	router.Use(gin.Logger())
	router.Use(gin.Recovery())

	// API Gateway health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":    "healthy",
			"service":   "api-gateway",
			"timestamp": time.Now(),
			"version":   "1.0.0",
		})
	})

	// API routes with proxy to microservices
	api := router.Group("/api/v1")
	{
		// Auth service (login, etc.)
		api.Any("/auth/*path", createSimpleProxyHandler(config.AuthRBACServiceURL))
		
		// HIPAA compliance services
		api.Any("/consent/*path", createSimpleProxyHandler(config.ConsentServiceURL))
		api.Any("/audit/*path", createSimpleProxyHandler(config.AuditLoggingServiceURL))
		api.Any("/history/*path", createSimpleProxyHandler(config.ChatHistoryServiceURL))
		api.Any("/billing/*path", createSimpleProxyHandler(config.BillingServiceURL))
		
		// User-facing microservices
		api.Any("/emergency/*path", createSimpleProxyHandler(config.EmergencyAccessServiceURL))
		api.Any("/relationships/*path", createSimpleProxyHandler(config.RelationshipManagementServiceURL))
		api.Any("/subscriptions/*path", createSimpleProxyHandler(config.UserSubscriptionServiceURL))
		api.Any("/tasks/*path", createSimpleProxyHandler(config.BackgroundTasksServiceURL))
		
		// Interactive chat service (Python FastAPI)
		api.Any("/chat/*path", createSimpleProxyHandler(config.ChatServiceURL))
		
		// AI services
		api.Any("/search/*path", createSimpleProxyHandler(config.SearchServiceURL))
		api.Any("/embedding/*path", createSimpleProxyHandler(config.EmbeddingServiceURL))
		api.Any("/generation/*path", createSimpleProxyHandler(config.GenerationServiceURL))
		api.Any("/safety/*path", createSimpleProxyHandler(config.ContentSafetyServiceURL))
	}

	return router
}

func simpleMain() {
	log.Println("🌐 Starting Simple API Gateway Proxy...")
	
	config := loadSimpleConfig()
	router := setupSimpleRouter(config)

	server := &http.Server{
		Addr:         ":" + config.Port,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	log.Printf("🚀 API Gateway Proxy starting on port %s", config.Port)
	log.Println("📋 Routing configuration:")
	log.Printf("   • /api/v1/auth/* → %s", config.AuthRBACServiceURL)
	log.Printf("   • /api/v1/consent/* → %s", config.ConsentServiceURL)
	log.Printf("   • /api/v1/history/* → %s", config.ChatHistoryServiceURL)
	log.Printf("   • /api/v1/audit/* → %s", config.AuditLoggingServiceURL)
	log.Printf("   • /api/v1/billing/* → %s", config.BillingServiceURL)
	log.Printf("   • /api/v1/emergency/* → %s", config.EmergencyAccessServiceURL)
	log.Printf("   • /api/v1/relationships/* → %s", config.RelationshipManagementServiceURL)
	log.Printf("   • /api/v1/subscriptions/* → %s", config.UserSubscriptionServiceURL)
	log.Printf("   • /api/v1/tasks/* → %s", config.BackgroundTasksServiceURL)
	log.Printf("   • /api/v1/chat/* → %s", config.ChatServiceURL)
	log.Printf("   • /api/v1/search/* → %s", config.SearchServiceURL)
	log.Printf("   • /api/v1/embedding/* → %s", config.EmbeddingServiceURL)
	log.Printf("   • /api/v1/generation/* → %s", config.GenerationServiceURL)
	log.Printf("   • /api/v1/safety/* → %s", config.ContentSafetyServiceURL)

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("❌ Failed to start API Gateway: %v", err)
	}
}