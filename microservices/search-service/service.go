package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"go.uber.org/zap"
)

type ServiceConfig struct {
	MaxQueryLength        int
	MaxResultsLimit       int
	DefaultResultsLimit   int
	CacheResultsTTL       time.Duration
	RateLimitPerMinute    int
	EnableSafetyAnalysis  bool
	EnableQuotaCheck      bool
}

type SearchRequest struct {
	Query           string                 `json:"query" binding:"required,min=1,max=500"`
	Route           string                 `json:"route,omitempty"`
	TopK            int                    `json:"top_k,omitempty"`
	Filters         map[string]interface{} `json:"filters,omitempty"`
	IncludeMetadata bool                   `json:"include_metadata,omitempty"`
}

type SearchResult struct {
	DocumentID string                 `json:"document_id,omitempty"`
	Title      string                 `json:"title"`
	Content    string                 `json:"content"`
	Score      float64                `json:"score"`
	Source     string                 `json:"source"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

type SearchResponse struct {
	Query              string                 `json:"query"`
	Results            []SearchResult         `json:"results"`
	TotalResults       int                    `json:"total_results"`
	RouteUsed          string                 `json:"route_used"`
	ProcessingTimeMs   float64                `json:"processing_time_ms"`
	SubscriptionPlan   string                 `json:"subscription_plan"`
	UsageInfo          map[string]interface{} `json:"usage_info"`
	SearchQuality      string                 `json:"search_quality,omitempty"`
}

type SearchService struct {
	db                   *DatabaseManager
	logger               *zap.Logger
	config               ServiceConfig
	knowledgeServiceURL  string
	embeddingServiceURL  string
	generationServiceURL string
	safetyServiceURL     string
	httpClient           *http.Client
}

func NewSearchService(
	db *DatabaseManager,
	logger *zap.Logger,
	config ServiceConfig,
	knowledgeServiceURL, embeddingServiceURL, generationServiceURL, safetyServiceURL string,
) *SearchService {
	return &SearchService{
		db:                   db,
		logger:               logger,
		config:               config,
		knowledgeServiceURL:  knowledgeServiceURL,
		embeddingServiceURL:  embeddingServiceURL,
		generationServiceURL: generationServiceURL,
		safetyServiceURL:     safetyServiceURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (ss *SearchService) performSearch(ctx context.Context, request SearchRequest, userID string, subscriptionPlan string) (*SearchResponse, error) {
	startTime := time.Now()

	// Validate and adjust route based on subscription plan
	allowedRoutes := map[string][]string{
		"free":       {"exact", "auto"},
		"pro":        {"exact", "semantic", "hybrid", "auto"},
		"enterprise": {"exact", "semantic", "hybrid", "auto"},
	}

	userAllowedRoutes, exists := allowedRoutes[subscriptionPlan]
	if !exists {
		userAllowedRoutes = []string{"exact"}
	}

	route := request.Route
	if route == "" {
		route = "auto"
	}

	// Check if route is allowed for user's subscription
	isAllowed := false
	for _, allowedRoute := range userAllowedRoutes {
		if route == allowedRoute {
			isAllowed = true
			break
		}
	}

	if !isAllowed {
		if subscriptionPlan == "free" {
			route = "exact"
			ss.logger.Info("User requested premium route, using exact search instead",
				zap.String("user_id", userID),
				zap.String("requested_route", request.Route),
				zap.String("used_route", route))
		}
	}

	// Call Python knowledge service
	searchResults, err := ss.callKnowledgeService(ctx, request, route)
	if err != nil {
		return nil, fmt.Errorf("knowledge service call failed: %w", err)
	}

	// Process results
	results := make([]SearchResult, 0)
	for _, r := range searchResults.Results {
		result := SearchResult{
			DocumentID: r.DocumentID,
			Title:      truncateString(r.Title, 100),
			Content:    truncateString(r.Content, 500),
			Score:      r.Score,
			Source:     r.Source,
		}

		// Add metadata based on subscription
		if request.IncludeMetadata && subscriptionPlan != "free" {
			result.Metadata = r.Metadata
		}

		results = append(results, result)
	}

	processingTime := time.Since(startTime).Seconds() * 1000

	// Determine search quality
	searchQuality := "needs_improvement"
	if len(results) > 0 {
		if results[0].Score > 0.8 {
			searchQuality = "excellent"
		} else if results[0].Score > 0.5 {
			searchQuality = "good"
		}
	}

	// Record usage in background
	go ss.recordSearchUsage(userID, request.Query, len(results), searchResults.RouteUsed)

	return &SearchResponse{
		Query:            request.Query,
		Results:          results,
		TotalResults:     len(results),
		RouteUsed:        searchResults.RouteUsed,
		ProcessingTimeMs: processingTime,
		SubscriptionPlan: subscriptionPlan,
		UsageInfo: map[string]interface{}{
			"note": "Usage tracking handled by Go billing service",
		},
		SearchQuality: searchQuality,
	}, nil
}

type KnowledgeServiceRequest struct {
	Query           string                 `json:"query"`
	TopK            int                    `json:"top_k"`
	Route           string                 `json:"route"`
	Filters         map[string]interface{} `json:"filters,omitempty"`
	IncludeMetadata bool                   `json:"include_metadata"`
}

type KnowledgeServiceResult struct {
	DocumentID string                 `json:"document_id,omitempty"`
	Title      string                 `json:"title"`
	Content    string                 `json:"content"`
	Score      float64                `json:"score"`
	Source     string                 `json:"source"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

type KnowledgeServiceResponse struct {
	Query              string                   `json:"query"`
	Results            []KnowledgeServiceResult `json:"results"`
	TotalResults       int                      `json:"total_results"`
	RouteUsed          string                   `json:"route_used"`
	ProcessingTimeMs   float64                  `json:"processing_time_ms"`
}

func (ss *SearchService) callKnowledgeService(ctx context.Context, request SearchRequest, route string) (*KnowledgeServiceResponse, error) {
	// Prepare request for Python knowledge service
	topK := request.TopK
	if topK == 0 {
		topK = ss.config.DefaultResultsLimit
	}
	if topK > ss.config.MaxResultsLimit {
		topK = ss.config.MaxResultsLimit
	}

	knowledgeRequest := KnowledgeServiceRequest{
		Query:           request.Query,
		TopK:            topK,
		Route:           route,
		Filters:         request.Filters,
		IncludeMetadata: request.IncludeMetadata,
	}

	jsonData, err := json.Marshal(knowledgeRequest)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal search request: %w", err)
	}

	// Make HTTP request to Python internal search endpoint
	url := fmt.Sprintf("%s/internal/search", ss.knowledgeServiceURL)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := ss.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to call knowledge service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("knowledge service returned status %d: %s", resp.StatusCode, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	var knowledgeResponse KnowledgeServiceResponse
	if err := json.Unmarshal(body, &knowledgeResponse); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &knowledgeResponse, nil
}

func (ss *SearchService) generateSuggestions(ctx context.Context, query string, limit int) ([]string, error) {
	// For now, generate simple suggestions based on query
	// In production, this could call an AI service or use historical data
	suggestions := []string{
		fmt.Sprintf("%s in MongoDB", query),
		fmt.Sprintf("%s with Redis", query),
		fmt.Sprintf("%s using PostgreSQL", query),
		fmt.Sprintf("How to %s", query),
		fmt.Sprintf("What is %s", query),
	}

	if limit > len(suggestions) {
		limit = len(suggestions)
	}

	return suggestions[:limit], nil
}

func (ss *SearchService) recordSearchUsage(userID, query string, resultsCount int, searchType string) {
	// Record search usage for analytics (similar to billing)
	ss.logger.Info("Search performed",
		zap.String("user_id", userID),
		zap.String("query_hash", hashString(query)),
		zap.Int("results_count", resultsCount),
		zap.String("search_type", searchType))
}

func (ss *SearchService) checkServiceHealth(ctx context.Context) map[string]interface{} {
	health := map[string]interface{}{
		"timestamp": time.Now(),
		"databases": ss.db.GetHealthStatus(),
	}

	// Check knowledge service health
	knowledgeHealth := "unhealthy"
	if resp, err := http.Get(ss.knowledgeServiceURL + "/health"); err == nil {
		if resp.StatusCode == 200 {
			knowledgeHealth = "healthy"
		}
		resp.Body.Close()
	}

	health["knowledge_service"] = knowledgeHealth
	return health
}

func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen]
}

func hashString(s string) string {
	// Simple hash for logging (don't log actual queries for privacy)
	return fmt.Sprintf("hash_%d", len(s))
}