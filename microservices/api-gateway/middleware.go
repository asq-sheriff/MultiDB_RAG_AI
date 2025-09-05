// Package main provides middleware stack for API Gateway
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

// MiddlewareManager manages all middleware for the API Gateway
type MiddlewareManager struct {
	config   *ServiceConfig
	db       *DatabaseManager
	services *ServiceManager
}

// NewMiddlewareManager creates a new middleware manager
func NewMiddlewareManager(config *ServiceConfig, db *DatabaseManager, services *ServiceManager) *MiddlewareManager {
	return &MiddlewareManager{
		config:   config,
		db:       db,
		services: services,
	}
}

// SetupMiddleware configures all middleware in the correct order
func (m *MiddlewareManager) SetupMiddleware(r *gin.Engine) {
	// Recovery middleware (should be first)
	r.Use(gin.Recovery())
	
	// Request ID middleware for tracing
	r.Use(m.RequestIDMiddleware())
	
	// CORS middleware
	r.Use(m.CORSMiddleware())
	
	// Logging middleware
	r.Use(m.LoggingMiddleware())
	
	// Rate limiting middleware
	r.Use(m.RateLimitMiddleware())
	
	// Session middleware
	r.Use(m.SessionMiddleware())
	
	// Authentication middleware (applied selectively)
	// Applied per route group as needed
}

// RequestIDMiddleware adds unique request ID for tracing
func (m *MiddlewareManager) RequestIDMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := c.GetHeader("X-Request-ID")
		if requestID == "" {
			requestID = uuid.New().String()
		}
		
		c.Header("X-Request-ID", requestID)
		c.Set("request_id", requestID)
		c.Next()
	}
}

// CORSMiddleware handles cross-origin requests
func (m *MiddlewareManager) CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		
		// Allow specific origins
		allowedOrigins := []string{
			"http://localhost:3000",
			"http://localhost:8000",
			"http://localhost:8080",
			"http://127.0.0.1:3000",
			"http://127.0.0.1:8000",
			"http://127.0.0.1:8080",
		}
		
		allowed := false
		for _, allowedOrigin := range allowedOrigins {
			if origin == allowedOrigin {
				allowed = true
				break
			}
		}
		
		if allowed {
			c.Header("Access-Control-Allow-Origin", origin)
		}
		
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, X-Request-ID")
		c.Header("Access-Control-Allow-Credentials", "true")
		c.Header("Access-Control-Expose-Headers", "X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		
		c.Next()
	}
}

// LoggingMiddleware logs HTTP requests and responses
func (m *MiddlewareManager) LoggingMiddleware() gin.HandlerFunc {
	return gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		var statusColor, methodColor, resetColor string
		if param.IsOutputColor() {
			statusColor = param.StatusCodeColor()
			methodColor = param.MethodColor()
			resetColor = param.ResetColor()
		}

		return fmt.Sprintf("%s[GATEWAY]%s %v | %s%3d%s | %13v | %15s | %s%-7s%s %#v %s\n",
			"\033[97m", resetColor,
			param.TimeStamp.Format("2006/01/02 - 15:04:05"),
			statusColor, param.StatusCode, resetColor,
			param.Latency,
			param.ClientIP,
			methodColor, param.Method, resetColor,
			param.Path,
			param.ErrorMessage,
		)
	})
}

// RateLimitMiddleware implements rate limiting with sliding window
type RateLimitMiddleware struct {
	config *ServiceConfig
	db     *DatabaseManager
	
	// In-memory backup when Redis is unavailable
	memoryLimits map[string]*rateLimitEntry
	mutex        sync.RWMutex
}

type rateLimitEntry struct {
	requests  []time.Time
	lastReset time.Time
}

// RateLimitMiddleware creates rate limiting middleware
func (m *MiddlewareManager) RateLimitMiddleware() gin.HandlerFunc {
	rateLimiter := &RateLimitMiddleware{
		config:       m.config,
		db:           m.db,
		memoryLimits: make(map[string]*rateLimitEntry),
	}
	
	return rateLimiter.Handle()
}

func (rl *RateLimitMiddleware) Handle() gin.HandlerFunc {
	// Exempt paths from rate limiting
	exemptPaths := map[string]bool{
		"/docs":         true,
		"/redoc":        true,
		"/openapi.json": true,
		"/favicon.ico":  true,
		"/health":       true,
	}
	
	return func(c *gin.Context) {
		// Skip rate limiting for exempt paths
		if exemptPaths[c.Request.URL.Path] {
			c.Next()
			return
		}
		
		// Get client identifier (IP address)
		clientIP := getClientIP(c)
		
		// Check per-second limit
		allowed, info, err := rl.checkLimit(clientIP, "second", rl.config.MaxRequestsPerSecond, time.Second)
		if err == nil && info != nil {
			c.Header("X-RateLimit-Limit", strconv.Itoa(info.Limit))
			c.Header("X-RateLimit-Remaining", strconv.Itoa(info.Remaining))
			c.Header("X-RateLimit-Reset", strconv.FormatInt(info.Reset.Unix(), 10))
		}
		
		if !allowed {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "Rate limit exceeded",
				"message":     "Too many requests per second. Limit: " + strconv.Itoa(rl.config.MaxRequestsPerSecond) + "/sec",
				"retry_after": info.RetryAfter,
			})
			c.Abort()
			return
		}
		
		// Check per-minute limit
		allowed, info, err = rl.checkLimit(clientIP, "minute", rl.config.MaxRequestsPerMinute, time.Minute)
		if err == nil && info != nil && info.Remaining < rl.config.MaxRequestsPerMinute {
			c.Header("X-RateLimit-Limit-Minute", strconv.Itoa(info.Limit))
			c.Header("X-RateLimit-Remaining-Minute", strconv.Itoa(info.Remaining))
		}
		
		if !allowed {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "Rate limit exceeded",
				"message":     "Too many requests per minute. Limit: " + strconv.Itoa(rl.config.MaxRequestsPerMinute) + "/min",
				"retry_after": info.RetryAfter,
			})
			c.Abort()
			return
		}
		
		c.Next()
	}
}

func (rl *RateLimitMiddleware) checkLimit(clientIP, window string, limit int, duration time.Duration) (bool, *RateLimitInfo, error) {
	key := fmt.Sprintf("%s_%s", clientIP, window)
	
	// Try Redis first
	if rl.db.RedisClient != nil {
		return rl.db.CheckRateLimit(key, limit, duration)
	}
	
	// Fallback to in-memory rate limiting
	return rl.checkMemoryLimit(key, limit, duration)
}

func (rl *RateLimitMiddleware) checkMemoryLimit(key string, limit int, duration time.Duration) (bool, *RateLimitInfo, error) {
	rl.mutex.Lock()
	defer rl.mutex.Unlock()
	
	now := time.Now()
	
	entry, exists := rl.memoryLimits[key]
	if !exists {
		entry = &rateLimitEntry{
			requests:  make([]time.Time, 0),
			lastReset: now,
		}
		rl.memoryLimits[key] = entry
	}
	
	// Remove old requests outside the window
	cutoff := now.Add(-duration)
	validRequests := entry.requests[:0]
	for _, reqTime := range entry.requests {
		if reqTime.After(cutoff) {
			validRequests = append(validRequests, reqTime)
		}
	}
	entry.requests = validRequests
	
	// Add current request
	entry.requests = append(entry.requests, now)
	
	remaining := limit - len(entry.requests)
	if remaining < 0 {
		remaining = 0
	}
	
	info := &RateLimitInfo{
		Limit:     limit,
		Remaining: remaining,
		Reset:     now.Add(duration),
		Window:    duration.String(),
	}
	
	if len(entry.requests) > limit {
		info.RetryAfter = int(duration.Seconds())
		return false, info, nil
	}
	
	return true, info, nil
}

// SessionMiddleware manages user sessions
func (m *MiddlewareManager) SessionMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get session ID from cookie or header
		sessionID := c.GetHeader("X-Session-ID")
		if sessionID == "" {
			if cookie, err := c.Cookie("session_id"); err == nil {
				sessionID = cookie
			}
		}
		
		// If no session ID, create a new one for anonymous users
		if sessionID == "" {
			sessionID = uuid.New().String()
			clientIP := getClientIP(c)
			userAgent := c.GetHeader("User-Agent")
			
			if m.db != nil {
				m.db.CreateSession(sessionID, "", clientIP, userAgent, nil)
			}
			
			// Set session cookie
			c.SetCookie("session_id", sessionID, m.config.SessionTTL, "/", "", false, true)
			c.Header("X-Session-ID", sessionID)
		}
		
		// Store session ID in context
		c.Set("session_id", sessionID)
		
		// Try to get session details
		if m.db != nil {
			if session, err := m.db.GetSession(sessionID); err == nil {
				c.Set("session", session)
				if session.UserID != "" {
					c.Set("user_id", session.UserID)
				}
			}
		}
		
		c.Next()
	}
}

// AuthenticationMiddleware validates JWT tokens and user authentication
func (m *MiddlewareManager) AuthenticationMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get token from Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Authorization required",
				"message": "Missing Authorization header",
			})
			c.Abort()
			return
		}
		
		// Validate Bearer token format
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Invalid token format",
				"message": "Authorization header must be 'Bearer <token>'",
			})
			c.Abort()
			return
		}
		
		tokenString := parts[1]
		
		// Parse and validate JWT token
		token, err := jwt.ParseWithClaims(tokenString, &jwt.RegisteredClaims{}, func(token *jwt.Token) (interface{}, error) {
			// Validate signing method
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return []byte(m.config.SecretKey), nil
		})
		
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Invalid token",
				"message": err.Error(),
			})
			c.Abort()
			return
		}
		
		if !token.Valid {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Invalid token",
				"message": "Token is not valid",
			})
			c.Abort()
			return
		}
		
		// Extract claims
		claims, ok := token.Claims.(*jwt.RegisteredClaims)
		if !ok {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Invalid token claims",
				"message": "Could not parse token claims",
			})
			c.Abort()
			return
		}
		
		// Validate expiration
		if claims.ExpiresAt != nil && claims.ExpiresAt.Before(time.Now()) {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Token expired",
				"message": "Authentication token has expired",
			})
			c.Abort()
			return
		}
		
		// Get user from database
		userID, err := uuid.Parse(claims.Subject)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Invalid user ID",
				"message": "Invalid user ID in token",
			})
			c.Abort()
			return
		}
		
		// Store user information in context
		c.Set("user_id", userID.String())
		c.Set("user_claims", claims)
		
		c.Next()
	}
}

// SafetyMiddleware performs content safety analysis
func (m *MiddlewareManager) SafetyMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Only apply to chat endpoints
		if !strings.HasPrefix(c.Request.URL.Path, "/chat") {
			c.Next()
			return
		}
		
		// Skip GET requests
		if c.Request.Method == "GET" {
			c.Next()
			return
		}
		
		// Read request body
		var bodyBytes []byte
		if c.Request.Body != nil {
			bodyBytes, _ = io.ReadAll(c.Request.Body)
			c.Request.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
		}
		
		// Parse request to extract message content
		var requestData map[string]interface{}
		if len(bodyBytes) > 0 {
			json.Unmarshal(bodyBytes, &requestData)
		}
		
		// Extract message content
		var content string
		if message, ok := requestData["message"].(string); ok {
			content = message
		}
		
		if content == "" {
			c.Next()
			return
		}
		
		// Perform safety analysis
		userID, _ := c.Get("user_id")
		sessionID, _ := c.Get("session_id")
		
		safetyRequest := SafetyAnalysisRequest{
			Content:   content,
			UserID:    userID.(string),
			SessionID: sessionID.(string),
		}
		
		// Note: This would require a service manager instance in middleware
		// For now, skip safety analysis in middleware and handle it in handlers
		// m.services.AnalyzeSafety(&safetyRequest)
		
		// Store request for later processing in handlers
		c.Set("safety_request", safetyRequest)
		
		c.Next()
	}
}

// AdminMiddleware checks for admin privileges
func (m *MiddlewareManager) AdminMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// First check authentication
		userID, exists := c.Get("user_id")
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Authentication required",
				"message": "Admin access requires authentication",
			})
			c.Abort()
			return
		}
		
		// Check if user is admin (this would require database lookup)
		// For now, implement a simple check based on user claims
		claims, exists := c.Get("user_claims")
		if !exists {
			c.JSON(http.StatusForbidden, gin.H{
				"error":   "Access denied",
				"message": "Admin privileges required",
			})
			c.Abort()
			return
		}
		
		// In a full implementation, you would check user roles from database
		// For now, allow if user_id is present
		_ = userID
		_ = claims
		
		c.Next()
	}
}

// CompressionMiddleware adds response compression
func (m *MiddlewareManager) CompressionMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Simple compression check - in production use a proper compression library
		if strings.Contains(c.GetHeader("Accept-Encoding"), "gzip") {
			c.Header("Content-Encoding", "gzip")
		}
		c.Next()
	}
}

// SecurityHeadersMiddleware adds security headers
func (m *MiddlewareManager) SecurityHeadersMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("X-Content-Type-Options", "nosniff")
		c.Header("X-Frame-Options", "DENY")
		c.Header("X-XSS-Protection", "1; mode=block")
		c.Header("Referrer-Policy", "strict-origin-when-cross-origin")
		c.Header("Content-Security-Policy", "default-src 'self'")
		c.Next()
	}
}

// JWT token generation and validation

// GenerateJWT generates a JWT token for authenticated user
func (m *MiddlewareManager) GenerateJWT(userID string) (string, time.Time, error) {
	expirationTime := time.Now().Add(time.Duration(m.config.AccessTokenExpireMinutes) * time.Minute)
	
	claims := &jwt.RegisteredClaims{
		Subject:   userID,
		ExpiresAt: jwt.NewNumericDate(expirationTime),
		IssuedAt:  jwt.NewNumericDate(time.Now()),
		Issuer:    "api-gateway-service",
	}
	
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(m.config.SecretKey))
	if err != nil {
		return "", time.Time{}, fmt.Errorf("failed to sign token: %w", err)
	}
	
	return tokenString, expirationTime, nil
}

// OptionalAuthMiddleware provides optional authentication
func (m *MiddlewareManager) OptionalAuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			// No auth header, continue without authentication
			c.Next()
			return
		}

		// If auth header exists, validate it
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			// Invalid format, continue without authentication
			c.Next()
			return
		}
		
		tokenString := parts[1]
		
		// Parse and validate JWT token
		token, err := jwt.ParseWithClaims(tokenString, &jwt.RegisteredClaims{}, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
			}
			return []byte(m.config.SecretKey), nil
		})
		
		if err != nil || !token.Valid {
			// Invalid token, continue without authentication
			c.Next()
			return
		}
		
		// Extract claims and set context
		if claims, ok := token.Claims.(*jwt.RegisteredClaims); ok {
			if claims.ExpiresAt == nil || claims.ExpiresAt.After(time.Now()) {
				c.Set("user_id", claims.Subject)
				c.Set("user_claims", claims)
			}
		}
		
		c.Next()
	}
}

// SuperuserMiddleware checks for superuser privileges
func (m *MiddlewareManager) SuperuserMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		userID, exists := c.Get("user_id")
		if !exists {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "Authentication required",
				"message": "Superuser access requires authentication",
			})
			c.Abort()
			return
		}

		// In production, check user's superuser status from database
		// For now, this is a placeholder
		user, err := m.db.GetUser(userID.(string))
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error":   "Database error",
				"message": "Failed to verify user privileges",
			})
			c.Abort()
			return
		}

		if !user.IsSuperuser {
			c.JSON(http.StatusForbidden, gin.H{
				"error":   "Access denied",
				"message": "Superuser privileges required",
			})
			c.Abort()
			return
		}

		c.Next()
	}
}

// Helper functions

// getClientIP extracts the real client IP address
func getClientIP(c *gin.Context) string {
	// Check X-Forwarded-For header first
	if xff := c.GetHeader("X-Forwarded-For"); xff != "" {
		// X-Forwarded-For can contain multiple IPs, take the first one
		ips := strings.Split(xff, ",")
		return strings.TrimSpace(ips[0])
	}
	
	// Check X-Real-IP header
	if realIP := c.GetHeader("X-Real-IP"); realIP != "" {
		return realIP
	}
	
	// Fallback to RemoteAddr
	return c.ClientIP()
}