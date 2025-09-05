package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

// ServiceManager handles communication with all microservices
type ServiceManager struct {
	config     *ServiceConfig
	httpClient *http.Client
	
	// Service health tracking
	serviceHealth map[string]*ServiceHealth
	healthMutex   sync.RWMutex
	
	// Circuit breaker state
	circuitBreakers map[string]*CircuitBreaker
	breakerMutex    sync.RWMutex
}

// CircuitBreaker implements circuit breaker pattern
type CircuitBreaker struct {
	maxFailures    int
	resetTimeout   time.Duration
	failures       int
	lastFailTime   time.Time
	state          string // closed, open, half-open
	mutex          sync.RWMutex
}

// NewServiceManager creates a new service manager
func NewServiceManager(config *ServiceConfig) *ServiceManager {
	return &ServiceManager{
		config: config,
		httpClient: &http.Client{
			Timeout: config.RequestTimeout,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 10,
				IdleConnTimeout:     90 * time.Second,
			},
		},
		serviceHealth:   make(map[string]*ServiceHealth),
		circuitBreakers: make(map[string]*CircuitBreaker),
	}
}

// InitializeCircuitBreakers sets up circuit breakers for all services
func (sm *ServiceManager) InitializeCircuitBreakers() {
	services := map[string]string{
		"search":         sm.config.SearchServiceURL,
		"embedding":      sm.config.EmbeddingServiceURL,
		"generation":     sm.config.GenerationServiceURL,
		"content_safety": sm.config.ContentSafetyServiceURL,
		"chat_history":   sm.config.ChatHistoryServiceURL,
		"subscription":   sm.config.SubscriptionServiceURL,
		"billing":        sm.config.BillingServiceURL,
		"background_tasks": sm.config.BackgroundTasksURL,
		"consent":        sm.config.ConsentServiceURL,
	}

	sm.breakerMutex.Lock()
	defer sm.breakerMutex.Unlock()
	
	for service := range services {
		sm.circuitBreakers[service] = &CircuitBreaker{
			maxFailures:  5,
			resetTimeout: 60 * time.Second,
			state:        "closed",
		}
	}
}

// getCircuitBreaker gets or creates a circuit breaker for a service
func (sm *ServiceManager) getCircuitBreaker(serviceName string) *CircuitBreaker {
	sm.breakerMutex.RLock()
	breaker, exists := sm.circuitBreakers[serviceName]
	sm.breakerMutex.RUnlock()
	
	if !exists {
		sm.breakerMutex.Lock()
		breaker = &CircuitBreaker{
			maxFailures:  5,
			resetTimeout: 60 * time.Second,
			state:        "closed",
		}
		sm.circuitBreakers[serviceName] = breaker
		sm.breakerMutex.Unlock()
	}
	
	return breaker
}

// CanExecute checks if circuit breaker allows execution
func (cb *CircuitBreaker) CanExecute() bool {
	cb.mutex.Lock()
	defer cb.mutex.Unlock()
	
	switch cb.state {
	case "closed":
		return true
	case "open":
		if time.Since(cb.lastFailTime) > cb.resetTimeout {
			cb.state = "half-open"
			return true
		}
		return false
	case "half-open":
		return true
	default:
		return false
	}
}

// OnSuccess records successful execution
func (cb *CircuitBreaker) OnSuccess() {
	cb.mutex.Lock()
	defer cb.mutex.Unlock()
	
	cb.failures = 0
	cb.state = "closed"
}

// OnFailure records failed execution
func (cb *CircuitBreaker) OnFailure() {
	cb.mutex.Lock()
	defer cb.mutex.Unlock()
	
	cb.failures++
	cb.lastFailTime = time.Now()
	
	if cb.failures >= cb.maxFailures {
		cb.state = "open"
	}
}

// makeServiceRequest makes HTTP request to a microservice with circuit breaker
func (sm *ServiceManager) makeServiceRequest(serviceName, method, endpoint string, body interface{}, headers map[string]string) (*http.Response, error) {
	breaker := sm.getCircuitBreaker(serviceName)
	
	if !breaker.CanExecute() {
		return nil, fmt.Errorf("circuit breaker open for service: %s", serviceName)
	}
	
	var serviceURL string
	switch serviceName {
	case "search":
		serviceURL = sm.config.SearchServiceURL
	case "embedding":
		serviceURL = sm.config.EmbeddingServiceURL
	case "generation":
		serviceURL = sm.config.GenerationServiceURL
	case "content_safety":
		serviceURL = sm.config.ContentSafetyServiceURL
	case "chat_history":
		serviceURL = sm.config.ChatHistoryServiceURL
	case "subscription":
		serviceURL = sm.config.SubscriptionServiceURL
	case "billing":
		serviceURL = sm.config.BillingServiceURL
	case "background_tasks":
		serviceURL = sm.config.BackgroundTasksURL
	case "consent":
		serviceURL = sm.config.ConsentServiceURL
	default:
		return nil, fmt.Errorf("unknown service: %s", serviceName)
	}
	
	url := fmt.Sprintf("%s%s", serviceURL, endpoint)
	
	var reqBody io.Reader
	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			breaker.OnFailure()
			return nil, fmt.Errorf("error marshaling request body: %w", err)
		}
		reqBody = bytes.NewBuffer(jsonBody)
	}
	
	req, err := http.NewRequest(method, url, reqBody)
	if err != nil {
		breaker.OnFailure()
		return nil, fmt.Errorf("error creating request: %w", err)
	}
	
	// Set default headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "API-Gateway-Go/1.0")
	
	// Add custom headers
	for key, value := range headers {
		req.Header.Set(key, value)
	}
	
	startTime := time.Now()
	resp, err := sm.httpClient.Do(req)
	responseTime := time.Since(startTime)
	
	// Update service health
	sm.updateServiceHealth(serviceName, err == nil, responseTime)
	
	if err != nil {
		breaker.OnFailure()
		return nil, fmt.Errorf("error making request to %s: %w", serviceName, err)
	}
	
	if resp.StatusCode >= 500 {
		breaker.OnFailure()
	} else {
		breaker.OnSuccess()
	}
	
	return resp, nil
}

// updateServiceHealth updates health tracking for a service
func (sm *ServiceManager) updateServiceHealth(serviceName string, success bool, responseTime time.Duration) {
	sm.healthMutex.Lock()
	defer sm.healthMutex.Unlock()
	
	health, exists := sm.serviceHealth[serviceName]
	if !exists {
		health = &ServiceHealth{
			Status:       "healthy",
			ResponseTime: responseTime,
			LastCheck:    time.Now(),
			ErrorCount:   0,
		}
		sm.serviceHealth[serviceName] = health
	}
	
	health.LastCheck = time.Now()
	health.ResponseTime = responseTime
	
	if !success {
		health.ErrorCount++
		if health.ErrorCount > 5 {
			health.Status = "unhealthy"
		} else if health.ErrorCount > 2 {
			health.Status = "degraded"
		}
	} else {
		if health.ErrorCount > 0 {
			health.ErrorCount--
		}
		if health.ErrorCount == 0 {
			health.Status = "healthy"
		}
	}
}

// Search Service Methods

// SearchDocuments performs document search via search service
func (sm *ServiceManager) SearchDocuments(ctx context.Context, req *SearchRequest, userID string) (*SearchResponse, error) {
	headers := map[string]string{}
	if userID != "" {
		headers["X-User-ID"] = userID
	}
	
	resp, err := sm.makeServiceRequest("search", "POST", "/search", req, headers)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("search service returned %d: %s", resp.StatusCode, string(body))
	}
	
	var searchResponse SearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&searchResponse); err != nil {
		return nil, fmt.Errorf("error decoding search response: %w", err)
	}
	
	return &searchResponse, nil
}

// Generation Service Methods

// GenerateResponse generates AI response via generation service
func (sm *ServiceManager) GenerateResponse(ctx context.Context, req *ChatMessageRequest, userID string) (*ChatMessageResponse, error) {
	headers := map[string]string{}
	if userID != "" {
		headers["X-User-ID"] = userID
	}
	
	resp, err := sm.makeServiceRequest("generation", "POST", "/generate", req, headers)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("generation service returned %d: %s", resp.StatusCode, string(body))
	}
	
	var chatResponse ChatMessageResponse
	if err := json.NewDecoder(resp.Body).Decode(&chatResponse); err != nil {
		return nil, fmt.Errorf("error decoding generation response: %w", err)
	}
	
	return &chatResponse, nil
}

// Content Safety Service Methods

// AnalyzeSafety performs safety analysis via content safety service
func (sm *ServiceManager) AnalyzeSafety(ctx context.Context, req *SafetyAnalysisRequest, userID string) (*SafetyAnalysisResult, error) {
	headers := map[string]string{}
	if userID != "" {
		headers["X-User-ID"] = userID
	}
	
	resp, err := sm.makeServiceRequest("content_safety", "POST", "/analyze", req, headers)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("content safety service returned %d: %s", resp.StatusCode, string(body))
	}
	
	var safetyResult SafetyAnalysisResult
	if err := json.NewDecoder(resp.Body).Decode(&safetyResult); err != nil {
		return nil, fmt.Errorf("error decoding safety analysis response: %w", err)
	}
	
	return &safetyResult, nil
}

// AnalyzeEmotion performs emotion analysis via content safety service
func (sm *ServiceManager) AnalyzeEmotion(ctx context.Context, content string, userID string) (*EmotionAnalysisResult, error) {
	req := map[string]interface{}{
		"content": content,
		"user_id": userID,
	}
	
	headers := map[string]string{}
	if userID != "" {
		headers["X-User-ID"] = userID
	}
	
	resp, err := sm.makeServiceRequest("content_safety", "POST", "/analyze/emotion", req, headers)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("emotion analysis service returned %d: %s", resp.StatusCode, string(body))
	}
	
	var emotionResult EmotionAnalysisResult
	if err := json.NewDecoder(resp.Body).Decode(&emotionResult); err != nil {
		return nil, fmt.Errorf("error decoding emotion analysis response: %w", err)
	}
	
	return &emotionResult, nil
}

// Chat History Service Methods

// SaveConversationMessage saves message via chat history service
func (sm *ServiceManager) SaveConversationMessage(ctx context.Context, message *ConversationMessage, userID string) error {
	headers := map[string]string{}
	if userID != "" {
		headers["X-User-ID"] = userID
	}
	
	resp, err := sm.makeServiceRequest("chat_history", "POST", "/messages", message, headers)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("chat history service returned %d: %s", resp.StatusCode, string(body))
	}
	
	return nil
}

// GetConversationHistory retrieves conversation history
func (sm *ServiceManager) GetConversationHistory(ctx context.Context, sessionID string, userID string) (*ConversationHistory, error) {
	headers := map[string]string{}
	if userID != "" {
		headers["X-User-ID"] = userID
	}
	
	endpoint := fmt.Sprintf("/conversations/%s", sessionID)
	resp, err := sm.makeServiceRequest("chat_history", "GET", endpoint, nil, headers)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode == http.StatusNotFound {
		return nil, nil // No history found
	}
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("chat history service returned %d: %s", resp.StatusCode, string(body))
	}
	
	var history ConversationHistory
	if err := json.NewDecoder(resp.Body).Decode(&history); err != nil {
		return nil, fmt.Errorf("error decoding conversation history: %w", err)
	}
	
	return &history, nil
}

// Subscription Service Methods

// GetUserSubscription retrieves user subscription info
func (sm *ServiceManager) GetUserSubscription(ctx context.Context, userID string) (map[string]interface{}, error) {
	headers := map[string]string{
		"X-User-ID": userID,
	}
	
	endpoint := fmt.Sprintf("/users/%s/subscription", userID)
	resp, err := sm.makeServiceRequest("subscription", "GET", endpoint, nil, headers)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("subscription service returned %d: %s", resp.StatusCode, string(body))
	}
	
	var subscription map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&subscription); err != nil {
		return nil, fmt.Errorf("error decoding subscription response: %w", err)
	}
	
	return subscription, nil
}

// CheckUsageLimits checks if user has exceeded usage limits
func (sm *ServiceManager) CheckUsageLimits(ctx context.Context, userID string, action string) (bool, error) {
	req := map[string]interface{}{
		"user_id": userID,
		"action":  action,
	}
	
	headers := map[string]string{
		"X-User-ID": userID,
	}
	
	resp, err := sm.makeServiceRequest("subscription", "POST", "/usage/check", req, headers)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return false, fmt.Errorf("subscription service returned %d: %s", resp.StatusCode, string(body))
	}
	
	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return false, fmt.Errorf("error decoding usage check response: %w", err)
	}
	
	allowed, ok := result["allowed"].(bool)
	if !ok {
		return false, fmt.Errorf("invalid response format from subscription service")
	}
	
	return allowed, nil
}

// Health Check Methods

// PerformHealthCheck checks health of all services
func (sm *ServiceManager) PerformHealthCheck(ctx context.Context) *DetailedHealthStatus {
	overall := "healthy"
	services := make(map[string]ServiceHealth)
	
	serviceEndpoints := map[string]string{
		"search":           "/health",
		"embedding":        "/health",
		"generation":       "/health",
		"content_safety":   "/health",
		"chat_history":     "/health",
		"subscription":     "/health",
		"billing":          "/health",
		"background_tasks": "/health",
		"consent":          "/health",
	}
	
	for serviceName, endpoint := range serviceEndpoints {
		startTime := time.Now()
		resp, err := sm.makeServiceRequest(serviceName, "GET", endpoint, nil, nil)
		responseTime := time.Since(startTime)
		
		status := "healthy"
		if err != nil || (resp != nil && resp.StatusCode >= 500) {
			status = "unhealthy"
			overall = "degraded"
		} else if resp != nil && resp.StatusCode >= 400 {
			status = "degraded"
			if overall == "healthy" {
				overall = "degraded"
			}
		}
		
		if resp != nil {
			resp.Body.Close()
		}
		
		services[serviceName] = ServiceHealth{
			Status:       status,
			ResponseTime: responseTime,
			LastCheck:    time.Now(),
			ErrorCount:   0,
		}
	}
	
	return &DetailedHealthStatus{
		Overall:   overall,
		Services:  services,
		Timestamp: time.Now(),
	}
}

// GetServiceHealth returns current service health status
func (sm *ServiceManager) GetServiceHealth(serviceName string) *ServiceHealth {
	sm.healthMutex.RLock()
	defer sm.healthMutex.RUnlock()
	
	if health, exists := sm.serviceHealth[serviceName]; exists {
		return health
	}
	
	return &ServiceHealth{
		Status:    "unknown",
		LastCheck: time.Now(),
	}
}

// GetAllServiceHealth returns health status for all services
func (sm *ServiceManager) GetAllServiceHealth() map[string]ServiceHealth {
	sm.healthMutex.RLock()
	defer sm.healthMutex.RUnlock()
	
	result := make(map[string]ServiceHealth)
	for name, health := range sm.serviceHealth {
		result[name] = *health
	}
	
	return result
}