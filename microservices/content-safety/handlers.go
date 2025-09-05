package main

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

// analyzeSafety handles POST /safety/analyze
func (css *ContentSafetyService) analyzeSafety(c *gin.Context) {
	var request SafetyAnalysisRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		css.logger.Error("Invalid safety analysis request", zap.Error(err))
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "invalid_request",
			Message:   "Invalid request format: " + err.Error(),
			RequestID: c.GetHeader("X-Request-ID"),
			Timestamp: time.Now(),
		})
		return
	}

	// Create request context
	ctx := NewRequestContext(request.UserID, request.SessionID)
	if requestID := c.GetHeader("X-Request-ID"); requestID != "" {
		ctx.RequestID = requestID
	}
	ctx.UserContext = request.UserContext

	// Perform safety analysis
	result, err := css.safetyAnalyzer.AnalyzeContent(request.Content, ctx)
	if err != nil {
		css.logger.Error("Safety analysis failed", 
			zap.Error(err),
			zap.String("request_id", ctx.RequestID),
		)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "analysis_failed",
			Message:   "Safety analysis failed: " + err.Error(),
			RequestID: ctx.RequestID,
			Timestamp: time.Now(),
		})
		return
	}

	// Log result for audit trail
	css.logger.Info("Safety analysis result",
		zap.String("request_id", ctx.RequestID),
		zap.String("user_id", ctx.UserID),
		zap.Bool("is_safe", result.IsSafe),
		zap.String("risk_level", string(result.RiskLevel)),
		zap.Bool("escalation_needed", result.EscalationNeeded),
	)

	c.JSON(http.StatusOK, result)
}

// analyzeEmotion handles POST /emotion/analyze
func (css *ContentSafetyService) analyzeEmotion(c *gin.Context) {
	var request EmotionAnalysisRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		css.logger.Error("Invalid emotion analysis request", zap.Error(err))
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "invalid_request",
			Message:   "Invalid request format: " + err.Error(),
			RequestID: c.GetHeader("X-Request-ID"),
			Timestamp: time.Now(),
		})
		return
	}

	// Create request context
	ctx := NewRequestContext(request.UserID, request.SessionID)
	if requestID := c.GetHeader("X-Request-ID"); requestID != "" {
		ctx.RequestID = requestID
	}
	ctx.UserContext = request.UserContext

	// Perform emotion analysis
	result, err := css.emotionAnalyzer.AnalyzeEmotion(request.Content, ctx)
	if err != nil {
		css.logger.Error("Emotion analysis failed",
			zap.Error(err),
			zap.String("request_id", ctx.RequestID),
		)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "analysis_failed",
			Message:   "Emotion analysis failed: " + err.Error(),
			RequestID: ctx.RequestID,
			Timestamp: time.Now(),
		})
		return
	}

	// Log result for audit trail
	css.logger.Info("Emotion analysis result",
		zap.String("request_id", ctx.RequestID),
		zap.String("user_id", ctx.UserID),
		zap.String("primary_emotion", string(result.Label)),
		zap.Float64("valence", result.Valence),
		zap.Bool("is_crisis", result.IsCrisis),
	)

	c.JSON(http.StatusOK, result)
}

// detectPHI handles POST /phi/detect
func (css *ContentSafetyService) detectPHI(c *gin.Context) {
	var request PHIDetectionRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		css.logger.Error("Invalid PHI detection request", zap.Error(err))
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "invalid_request",
			Message:   "Invalid request format: " + err.Error(),
			RequestID: c.GetHeader("X-Request-ID"),
			Timestamp: time.Now(),
		})
		return
	}

	// Create request context
	ctx := NewRequestContext(request.UserID, request.SessionID)
	if requestID := c.GetHeader("X-Request-ID"); requestID != "" {
		ctx.RequestID = requestID
	}
	ctx.UserContext = request.UserContext

	// Default analysis mode if not specified
	analysisMode := request.AnalysisMode
	if analysisMode == "" {
		analysisMode = "detect"
	}

	// Validate analysis mode
	validModes := map[string]bool{"detect": true, "redact": true, "encrypt": true}
	if !validModes[analysisMode] {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "invalid_analysis_mode",
			Message:   "Analysis mode must be 'detect', 'redact', or 'encrypt'",
			RequestID: ctx.RequestID,
			Timestamp: time.Now(),
		})
		return
	}

	// Perform PHI detection
	result, err := css.phiAnalyzer.DetectPHI(request.Content, analysisMode, ctx)
	if err != nil {
		css.logger.Error("PHI detection failed",
			zap.Error(err),
			zap.String("request_id", ctx.RequestID),
		)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "detection_failed",
			Message:   "PHI detection failed: " + err.Error(),
			RequestID: ctx.RequestID,
			Timestamp: time.Now(),
		})
		return
	}

	// Log result for HIPAA audit trail
	css.logger.Info("PHI detection result",
		zap.String("request_id", ctx.RequestID),
		zap.String("user_id", ctx.UserID),
		zap.Bool("phi_detected", result.PHIDetected),
		zap.String("risk_level", string(result.RiskLevel)),
		zap.String("analysis_mode", analysisMode),
		zap.Bool("audit_required", result.ComplianceStatus.AuditRequired),
	)

	// HIPAA audit logging for any PHI detection
	if result.PHIDetected && css.config.HIPAAMode {
		css.logger.Warn("HIPAA PHI detected in content",
			zap.String("request_id", ctx.RequestID),
			zap.String("user_id", ctx.UserID),
			zap.Int("phi_count", len(result.Identifiers)),
			zap.Bool("compliance_violation", !result.ComplianceStatus.IsCompliant),
		)
	}

	c.JSON(http.StatusOK, result)
}

// getSafetyGuidelines handles GET /safety/guidelines
func (css *ContentSafetyService) getSafetyGuidelines(c *gin.Context) {
	css.logger.Debug("Safety guidelines requested",
		zap.String("user_agent", c.GetHeader("User-Agent")),
		zap.String("client_ip", c.ClientIP()),
	)

	guidelines := css.safetyAnalyzer.GetGuidelines()
	
	response := SafetyGuidelinesResponse{
		Guidelines: guidelines,
		Version:    "2.0.0-go",
		UpdatedAt:  time.Now().UTC(),
	}

	c.JSON(http.StatusOK, response)
}

// analyzeCombined handles combined safety, emotion, and PHI analysis (bonus endpoint)
func (css *ContentSafetyService) analyzeCombined(c *gin.Context) {
	type CombinedAnalysisRequest struct {
		Content      string                 `json:"content" binding:"required"`
		UserID       string                 `json:"user_id,omitempty"`
		SessionID    string                 `json:"session_id,omitempty"`
		AnalysisMode string                 `json:"analysis_mode,omitempty"`
		UserContext  map[string]interface{} `json:"user_context,omitempty"`
	}

	type CombinedAnalysisResult struct {
		SafetyResult  *SafetyAnalysisResult  `json:"safety_result"`
		EmotionResult *EmotionAnalysisResult `json:"emotion_result"`
		PHIResult     *PHIDetectionResult    `json:"phi_result"`
		OverallSafe   bool                   `json:"overall_safe"`
		ProcessingTimeMS float64             `json:"processing_time_ms"`
	}

	var request CombinedAnalysisRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		css.logger.Error("Invalid combined analysis request", zap.Error(err))
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error:     "invalid_request",
			Message:   "Invalid request format: " + err.Error(),
			RequestID: c.GetHeader("X-Request-ID"),
			Timestamp: time.Now(),
		})
		return
	}

	startTime := time.Now()

	// Create request context
	ctx := NewRequestContext(request.UserID, request.SessionID)
	if requestID := c.GetHeader("X-Request-ID"); requestID != "" {
		ctx.RequestID = requestID
	}
	ctx.UserContext = request.UserContext

	// Default analysis mode
	analysisMode := request.AnalysisMode
	if analysisMode == "" {
		analysisMode = "detect"
	}

	// Perform all analyses concurrently using channels
	type safetyResult struct {
		result *SafetyAnalysisResult
		err    error
	}
	type emotionResult struct {
		result *EmotionAnalysisResult
		err    error
	}
	type phiResult struct {
		result *PHIDetectionResult
		err    error
	}

	safetyChan := make(chan safetyResult, 1)
	emotionChan := make(chan emotionResult, 1)
	phiChan := make(chan phiResult, 1)

	// Run analyses concurrently
	go func() {
		result, err := css.safetyAnalyzer.AnalyzeContent(request.Content, ctx)
		safetyChan <- safetyResult{result, err}
	}()

	go func() {
		result, err := css.emotionAnalyzer.AnalyzeEmotion(request.Content, ctx)
		emotionChan <- emotionResult{result, err}
	}()

	go func() {
		result, err := css.phiAnalyzer.DetectPHI(request.Content, analysisMode, ctx)
		phiChan <- phiResult{result, err}
	}()

	// Collect results
	safetyRes := <-safetyChan
	emotionRes := <-emotionChan
	phiRes := <-phiChan

	// Check for errors
	if safetyRes.err != nil {
		css.logger.Error("Safety analysis failed in combined analysis", zap.Error(safetyRes.err))
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "safety_analysis_failed",
			Message:   safetyRes.err.Error(),
			RequestID: ctx.RequestID,
			Timestamp: time.Now(),
		})
		return
	}

	if emotionRes.err != nil {
		css.logger.Error("Emotion analysis failed in combined analysis", zap.Error(emotionRes.err))
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "emotion_analysis_failed", 
			Message:   emotionRes.err.Error(),
			RequestID: ctx.RequestID,
			Timestamp: time.Now(),
		})
		return
	}

	if phiRes.err != nil {
		css.logger.Error("PHI detection failed in combined analysis", zap.Error(phiRes.err))
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error:     "phi_detection_failed",
			Message:   phiRes.err.Error(),
			RequestID: ctx.RequestID,
			Timestamp: time.Now(),
		})
		return
	}

	// Determine overall safety
	overallSafe := safetyRes.result.IsSafe && 
				   !emotionRes.result.IsCrisis && 
				   phiRes.result.ComplianceStatus.IsCompliant

	processingTime := float64(time.Since(startTime).Nanoseconds()) / 1e6

	result := CombinedAnalysisResult{
		SafetyResult:     safetyRes.result,
		EmotionResult:    emotionRes.result,
		PHIResult:        phiRes.result,
		OverallSafe:      overallSafe,
		ProcessingTimeMS: processingTime,
	}

	// Comprehensive audit logging
	css.logger.Info("Combined analysis completed",
		zap.String("request_id", ctx.RequestID),
		zap.String("user_id", ctx.UserID),
		zap.Bool("overall_safe", overallSafe),
		zap.Bool("safety_safe", safetyRes.result.IsSafe),
		zap.Bool("emotion_crisis", emotionRes.result.IsCrisis),
		zap.Bool("phi_detected", phiRes.result.PHIDetected),
		zap.Float64("total_processing_time_ms", processingTime),
	)

	c.JSON(http.StatusOK, result)
}