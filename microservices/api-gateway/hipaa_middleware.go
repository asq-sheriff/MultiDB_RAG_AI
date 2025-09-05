package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"regexp"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// PHIType represents different types of Protected Health Information
type PHIType string

const (
	PHI_SSN           PHIType = "SSN"
	PHI_DOB           PHIType = "DOB"
	PHI_PHONE         PHIType = "PHONE"
	PHI_EMAIL         PHIType = "EMAIL"
	PHI_ADDRESS       PHIType = "ADDRESS"
	PHI_MEDICAL_ID    PHIType = "MEDICAL_ID"
	PHI_MENTAL_HEALTH PHIType = "MENTAL_HEALTH"
	PHI_NAME          PHIType = "NAME"
	PHI_ZIP           PHIType = "ZIP"
)

// RiskLevel represents HIPAA compliance risk levels
type RiskLevel string

const (
	RISK_MINIMAL  RiskLevel = "minimal"
	RISK_MODERATE RiskLevel = "moderate"
	RISK_HIGH     RiskLevel = "high"
	RISK_CRITICAL RiskLevel = "critical"
)

// PHIDetectionResult represents the result of PHI detection
type PHIDetectionResult struct {
	PHIDetected   bool        `json:"phi_detected"`
	PHITypes      []PHIType   `json:"phi_types"`
	RiskLevel     RiskLevel   `json:"risk_level"`
	MaskedContent string      `json:"masked_content"`
	RiskScore     float64     `json:"risk_score"`
}

// HIPAAComplianceResult represents comprehensive HIPAA compliance check
type HIPAAComplianceResult struct {
	AuditID          string                `json:"audit_id"`
	Timestamp        time.Time             `json:"timestamp"`
	UserID           string                `json:"user_id"`
	SessionID        string                `json:"session_id"`
	Endpoint         string                `json:"endpoint"`
	Method           string                `json:"method"`
	ClientIP         string                `json:"client_ip"`
	PHIDetection     PHIDetectionResult    `json:"phi_detection"`
	AccessApproved   bool                  `json:"access_approved"`
	ComplianceStatus string                `json:"compliance_status"`
	ContentHash      string                `json:"content_hash"`
	UserAgent        string                `json:"user_agent"`
	RequestHeaders   map[string]string     `json:"request_headers"`
}

// HIPAAMiddleware provides comprehensive HIPAA compliance for Go API Gateway
type HIPAAMiddleware struct {
	AuditTrail       []HIPAAComplianceResult `json:"audit_trail"`
	PHIPatterns      map[PHIType]*regexp.Regexp
	RequireAuth      bool
	MaxAuditEntries  int
}

// NewHIPAAMiddleware creates a new HIPAA compliance middleware instance
func NewHIPAAMiddleware() *HIPAAMiddleware {
	middleware := &HIPAAMiddleware{
		AuditTrail:      make([]HIPAAComplianceResult, 0),
		PHIPatterns:     make(map[PHIType]*regexp.Regexp),
		RequireAuth:     true,
		MaxAuditEntries: 10000,
	}
	
	// Initialize PHI detection patterns
	middleware.initializePHIPatterns()
	
	log.Println("🔒 HIPAA Compliance Middleware initialized for Go API Gateway")
	return middleware
}

// initializePHIPatterns sets up regex patterns for PHI detection
func (h *HIPAAMiddleware) initializePHIPatterns() {
	patterns := map[PHIType]string{
		PHI_SSN:           `\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b`,
		PHI_DOB:           `\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b`,
		PHI_PHONE:         `\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b`,
		PHI_EMAIL:         `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`,
		PHI_ZIP:           `\b\d{5}(-\d{4})?\b`,
		PHI_MEDICAL_ID:    `\b(MRN|ID|PATIENT)\s*:?\s*\d+\b`,
		PHI_MENTAL_HEALTH: `\b(depression|anxiety|suicide|self.?harm|bipolar|schizophrenia|ptsd|trauma|therapy|counseling|psychiatrist|psychologist)\b`,
		PHI_NAME:          `\b(patient|mr|mrs|ms|dr)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b`,
	}
	
	for phiType, pattern := range patterns {
		compiled, err := regexp.Compile("(?i)" + pattern)
		if err != nil {
			log.Printf("❌ Failed to compile PHI pattern for %s: %v", phiType, err)
			continue
		}
		h.PHIPatterns[phiType] = compiled
	}
	
	log.Printf("✅ HIPAA PHI detection patterns initialized: %d patterns", len(h.PHIPatterns))
}

// DetectPHI analyzes content for Protected Health Information
func (h *HIPAAMiddleware) DetectPHI(content string) PHIDetectionResult {
	detectedTypes := make([]PHIType, 0)
	riskScore := 0.0
	maskedContent := content
	
	// Check for each PHI type
	for phiType, pattern := range h.PHIPatterns {
		if pattern.MatchString(content) {
			detectedTypes = append(detectedTypes, phiType)
			
			// Calculate risk score based on PHI type
			switch phiType {
			case PHI_SSN, PHI_MEDICAL_ID:
				riskScore += 0.4
			case PHI_MENTAL_HEALTH:
				riskScore += 0.5 // Mental health PHI is critical
			case PHI_DOB, PHI_PHONE, PHI_EMAIL:
				riskScore += 0.3
			case PHI_NAME, PHI_ADDRESS:
				riskScore += 0.2
			default:
				riskScore += 0.1
			}
			
			// Mask the PHI in content
			maskedContent = pattern.ReplaceAllString(maskedContent, "[REDACTED_"+string(phiType)+"]")
		}
	}
	
	// Determine overall risk level
	var riskLevel RiskLevel
	switch {
	case riskScore >= 0.8:
		riskLevel = RISK_CRITICAL
	case riskScore >= 0.5:
		riskLevel = RISK_HIGH
	case riskScore >= 0.3:
		riskLevel = RISK_MODERATE
	default:
		riskLevel = RISK_MINIMAL
	}
	
	return PHIDetectionResult{
		PHIDetected:   len(detectedTypes) > 0,
		PHITypes:      detectedTypes,
		RiskLevel:     riskLevel,
		MaskedContent: maskedContent,
		RiskScore:     riskScore,
	}
}

// generateContentHash creates SHA256 hash of content for audit trail
func (h *HIPAAMiddleware) generateContentHash(content string) string {
	hash := sha256.Sum256([]byte(content))
	return fmt.Sprintf("%x", hash)
}

// extractRequestContent safely extracts content from request body
func (h *HIPAAMiddleware) extractRequestContent(c *gin.Context) string {
	// Read the request body
	bodyBytes, err := io.ReadAll(c.Request.Body)
	if err != nil {
		log.Printf("❌ HIPAA: Failed to read request body: %v", err)
		return ""
	}
	
	// Restore the request body for downstream handlers
	c.Request.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
	
	// Try to extract content from JSON
	var requestData map[string]interface{}
	if err := json.Unmarshal(bodyBytes, &requestData); err == nil {
		// Look for common content fields
		contentFields := []string{"content", "text", "message", "input", "prompt"}
		for _, field := range contentFields {
			if content, exists := requestData[field]; exists {
				if contentStr, ok := content.(string); ok {
					return contentStr
				}
			}
		}
	}
	
	// Return the raw body as fallback
	return string(bodyBytes)
}

// createAuditEntry generates a comprehensive HIPAA audit entry
func (h *HIPAAMiddleware) createAuditEntry(c *gin.Context, content string, phiResult PHIDetectionResult, accessApproved bool) HIPAAComplianceResult {
	auditID := uuid.New().String()
	
	// Extract request metadata
	userID := c.GetHeader("X-User-ID")
	sessionID := c.GetHeader("X-Session-ID")
	clientIP := c.ClientIP()
	userAgent := c.GetHeader("User-Agent")
	
	// Create filtered headers (exclude sensitive data)
	requestHeaders := make(map[string]string)
	allowedHeaders := []string{"Content-Type", "Accept", "X-User-ID", "X-Session-ID", "Authorization"}
	for _, header := range allowedHeaders {
		if value := c.GetHeader(header); value != "" {
			if header == "Authorization" {
				requestHeaders[header] = "Bearer [REDACTED]"
			} else {
				requestHeaders[header] = value
			}
		}
	}
	
	// Determine compliance status
	complianceStatus := "compliant"
	if phiResult.PHIDetected && !accessApproved {
		complianceStatus = "violation"
	} else if phiResult.PHIDetected {
		complianceStatus = "monitored"
	}
	
	return HIPAAComplianceResult{
		AuditID:          auditID,
		Timestamp:        time.Now().UTC(),
		UserID:           userID,
		SessionID:        sessionID,
		Endpoint:         c.Request.URL.Path,
		Method:           c.Request.Method,
		ClientIP:         clientIP,
		PHIDetection:     phiResult,
		AccessApproved:   accessApproved,
		ComplianceStatus: complianceStatus,
		ContentHash:      h.generateContentHash(content),
		UserAgent:        userAgent,
		RequestHeaders:   requestHeaders,
	}
}

// logAuditEntry writes audit entry to log and stores in audit trail
func (h *HIPAAMiddleware) logAuditEntry(entry HIPAAComplianceResult) {
	// Add to audit trail (with size management)
	h.AuditTrail = append(h.AuditTrail, entry)
	if len(h.AuditTrail) > h.MaxAuditEntries {
		// Keep only the most recent entries
		h.AuditTrail = h.AuditTrail[len(h.AuditTrail)-h.MaxAuditEntries:]
	}
	
	// Log to system log
	auditJSON, _ := json.Marshal(entry)
	log.Printf("🔒 HIPAA_AUDIT: %s", string(auditJSON))
	
	// Enhanced logging for high-risk scenarios
	if entry.PHIDetection.RiskLevel == RISK_CRITICAL || entry.PHIDetection.RiskLevel == RISK_HIGH {
		log.Printf("🚨 HIPAA HIGH-RISK DETECTED: User: %s, Endpoint: %s, PHI Types: %v, Risk: %s", 
			entry.UserID, entry.Endpoint, entry.PHIDetection.PHITypes, entry.PHIDetection.RiskLevel)
	}
}

// HIPAACompliantHandler creates a HIPAA-compliant middleware handler
func (h *HIPAAMiddleware) HIPAACompliantHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		startTime := time.Now()
		
		// Extract request content for PHI analysis
		content := h.extractRequestContent(c)
		
		// Perform PHI detection
		phiResult := h.DetectPHI(content)
		
		// Check authentication for PHI-containing requests
		accessApproved := true
		if phiResult.PHIDetected && h.RequireAuth {
			authHeader := c.GetHeader("Authorization")
			userID := c.GetHeader("X-User-ID")
			
			// Basic authentication check (can be enhanced with JWT validation)
			if authHeader == "" || userID == "" {
				accessApproved = false
				
				// Create audit entry for denied access
				auditEntry := h.createAuditEntry(c, content, phiResult, false)
				h.logAuditEntry(auditEntry)
				
				c.JSON(http.StatusUnauthorized, gin.H{
					"error": "Authentication required for PHI access",
					"hipaa_compliance": gin.H{
						"phi_detected": true,
						"access_denied": true,
						"audit_id": auditEntry.AuditID,
					},
				})
				c.Abort()
				return
			}
		}
		
		// Create and log audit entry for approved access
		auditEntry := h.createAuditEntry(c, content, phiResult, accessApproved)
		h.logAuditEntry(auditEntry)
		
		// Add HIPAA compliance metadata to context
		c.Set("hipaa_audit_id", auditEntry.AuditID)
		c.Set("hipaa_phi_detected", phiResult.PHIDetected)
		c.Set("hipaa_risk_level", phiResult.RiskLevel)
		
		// Add HIPAA headers to response
		c.Header("X-HIPAA-Compliant", "true")
		c.Header("X-HIPAA-Audit-ID", auditEntry.AuditID)
		if phiResult.PHIDetected {
			c.Header("X-HIPAA-PHI-Detected", "true")
			c.Header("X-HIPAA-Risk-Level", string(phiResult.RiskLevel))
		}
		
		// Continue to next handler
		c.Next()
		
		// Log completion
		duration := time.Since(startTime)
		log.Printf("✅ HIPAA request processed: %s %s (Duration: %v, PHI: %t, Risk: %s)", 
			c.Request.Method, c.Request.URL.Path, duration, phiResult.PHIDetected, phiResult.RiskLevel)
	}
}

// HIPAAStatsHandler returns HIPAA compliance statistics
func (h *HIPAAMiddleware) HIPAAStatsHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Calculate statistics
		totalRequests := len(h.AuditTrail)
		phiRequests := 0
		riskDistribution := make(map[RiskLevel]int)
		phiTypeDistribution := make(map[PHIType]int)
		
		for _, entry := range h.AuditTrail {
			if entry.PHIDetection.PHIDetected {
				phiRequests++
			}
			riskDistribution[entry.PHIDetection.RiskLevel]++
			
			for _, phiType := range entry.PHIDetection.PHITypes {
				phiTypeDistribution[phiType]++
			}
		}
		
		c.JSON(http.StatusOK, gin.H{
			"hipaa_compliance_stats": gin.H{
				"total_requests":         totalRequests,
				"phi_requests":          phiRequests,
				"phi_percentage":        float64(phiRequests) / float64(totalRequests) * 100,
				"risk_distribution":     riskDistribution,
				"phi_type_distribution": phiTypeDistribution,
				"audit_trail_size":      len(h.AuditTrail),
				"compliance_active":     true,
			},
			"privacy_notice": "All statistics are aggregated and anonymized per HIPAA requirements",
			"timestamp":      time.Now().UTC(),
		})
	}
}

// GetAuditTrail returns recent audit entries (for authorized access only)
func (h *HIPAAMiddleware) GetAuditTrail(limit int) []HIPAAComplianceResult {
	if limit <= 0 || limit > len(h.AuditTrail) {
		limit = len(h.AuditTrail)
	}
	
	// Return the most recent entries
	start := len(h.AuditTrail) - limit
	if start < 0 {
		start = 0
	}
	
	return h.AuditTrail[start:]
}