package main

import (
	"time"
	"github.com/google/uuid"
)

// RiskLevel represents the severity level of safety violations
type RiskLevel string

const (
	RiskNone     RiskLevel = "none"
	RiskLow      RiskLevel = "low" 
	RiskMedium   RiskLevel = "medium"
	RiskHigh     RiskLevel = "high"
	RiskCritical RiskLevel = "critical"
)

// EmotionLabel represents different emotional states
type EmotionLabel string

const (
	EmotionHappy      EmotionLabel = "happy"
	EmotionSad        EmotionLabel = "sad"
	EmotionAngry      EmotionLabel = "angry"
	EmotionAnxious    EmotionLabel = "anxious"
	EmotionCalm       EmotionLabel = "calm"
	EmotionLonely     EmotionLabel = "lonely"
	EmotionFrustrated EmotionLabel = "frustrated"
	EmotionExcited    EmotionLabel = "excited"
	EmotionContent    EmotionLabel = "content"
	EmotionNeutral    EmotionLabel = "neutral"
)

// Request/Response Models

// SafetyAnalysisRequest represents a request for content safety analysis
type SafetyAnalysisRequest struct {
	Content     string                 `json:"content" binding:"required"`
	UserID      string                 `json:"user_id,omitempty"`
	SessionID   string                 `json:"session_id,omitempty"`
	UserContext map[string]interface{} `json:"user_context,omitempty"`
}

// SafetyAnalysisResult represents the result of safety analysis
type SafetyAnalysisResult struct {
	IsSafe                bool              `json:"is_safe"`
	RiskLevel            RiskLevel         `json:"risk_level"`
	Violations           []SafetyViolation `json:"violations"`
	OverallConfidence    float64           `json:"overall_confidence"`
	RiskScore            float64           `json:"risk_score"`
	Recommendations      []string          `json:"recommendations"`
	RequiresIntervention bool              `json:"requires_intervention"`
	EscalationNeeded     bool              `json:"escalation_needed"`
	ProcessingTimeMS     float64           `json:"processing_time_ms"`
}

// SafetyViolation represents a specific safety concern
type SafetyViolation struct {
	Type        string    `json:"type"`
	Description string    `json:"description"`
	Severity    RiskLevel `json:"severity"`
	StartPos    int       `json:"start_pos"`
	EndPos      int       `json:"end_pos"`
	Confidence  float64   `json:"confidence"`
}

// EmotionAnalysisRequest represents a request for emotion analysis
type EmotionAnalysisRequest struct {
	Content     string                 `json:"content" binding:"required"`
	UserID      string                 `json:"user_id,omitempty"`
	SessionID   string                 `json:"session_id,omitempty"`
	UserContext map[string]interface{} `json:"user_context,omitempty"`
}

// EmotionAnalysisResult represents the result of emotion analysis
type EmotionAnalysisResult struct {
	Label                   EmotionLabel           `json:"label"`
	Valence                float64                `json:"valence"`  // -1 (negative) to +1 (positive)
	Arousal                float64                `json:"arousal"`  // -1 (low) to +1 (high)
	Confidence             float64                `json:"confidence"`
	EmotionScores          []EmotionScore         `json:"emotion_scores"`
	CrisisIndicators       []CrisisIndicator      `json:"crisis_indicators"`
	SupportRecommendations []SupportRecommendation `json:"support_recommendations"`
	IsCrisis               bool                   `json:"is_crisis"`
	InterventionLevel      RiskLevel              `json:"intervention_level"`
	ProcessingTimeMS       float64                `json:"processing_time_ms"`
}

// EmotionScore represents confidence score for a specific emotion
type EmotionScore struct {
	Emotion    EmotionLabel `json:"emotion"`
	Confidence float64      `json:"confidence"`
}

// CrisisIndicator represents a detected crisis situation
type CrisisIndicator struct {
	Type                        string    `json:"type"`
	Description                 string    `json:"description"`
	Severity                    RiskLevel `json:"severity"`
	Confidence                  float64   `json:"confidence"`
	RequiresImmediateAttention  bool      `json:"requires_immediate_attention"`
}

// SupportRecommendation represents a therapeutic support recommendation
type SupportRecommendation struct {
	Type         string   `json:"type"`
	Description  string   `json:"description"`
	Priority     string   `json:"priority"`
	ResourceLinks []string `json:"resource_links"`
}

// PHIDetectionRequest represents a request for PHI detection
type PHIDetectionRequest struct {
	Content      string                 `json:"content" binding:"required"`
	UserID       string                 `json:"user_id,omitempty"`
	SessionID    string                 `json:"session_id,omitempty"`
	AnalysisMode string                 `json:"analysis_mode,omitempty"` // "detect", "redact", "encrypt"
	UserContext  map[string]interface{} `json:"user_context,omitempty"`
}

// PHIDetectionResult represents the result of PHI detection
type PHIDetectionResult struct {
	PHIDetected      bool              `json:"phi_detected"`
	Identifiers      []PHIIdentifier   `json:"identifiers"`
	RedactedContent  string            `json:"redacted_content,omitempty"`
	EncryptedContent string            `json:"encrypted_content,omitempty"`
	RiskLevel        RiskLevel         `json:"risk_level"`
	ProcessingTimeMS float64           `json:"processing_time_ms"`
	ComplianceStatus ComplianceStatus  `json:"compliance_status"`
}

// PHIIdentifier represents a detected HIPAA identifier
type PHIIdentifier struct {
	Type        string  `json:"type"`        // "name", "ssn", "dob", etc.
	Value       string  `json:"value"`       // Original or redacted value
	StartPos    int     `json:"start_pos"`
	EndPos      int     `json:"end_pos"`
	Confidence  float64 `json:"confidence"`
	HIPAAClass  string  `json:"hipaa_class"` // Which of the 18 HIPAA identifiers
}

// ComplianceStatus represents HIPAA compliance status
type ComplianceStatus struct {
	IsCompliant     bool     `json:"is_compliant"`
	ViolationTypes  []string `json:"violation_types,omitempty"`
	RequiredActions []string `json:"required_actions,omitempty"`
	AuditRequired   bool     `json:"audit_required"`
}

// SafetyGuidelinesResponse represents therapeutic safety guidelines
type SafetyGuidelinesResponse struct {
	Guidelines map[string][]string `json:"guidelines"`
	Version    string              `json:"version"`
	UpdatedAt  time.Time           `json:"updated_at"`
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error     string    `json:"error"`
	Message   string    `json:"message"`
	RequestID string    `json:"request_id"`
	Timestamp time.Time `json:"timestamp"`
}

// RequestContext represents context for processing requests
type RequestContext struct {
	RequestID   string
	UserID      string
	SessionID   string
	StartTime   time.Time
	UserContext map[string]interface{}
}

// NewRequestContext creates a new request context
func NewRequestContext(userID, sessionID string) *RequestContext {
	return &RequestContext{
		RequestID: uuid.New().String(),
		UserID:    userID,
		SessionID: sessionID,
		StartTime: time.Now(),
	}
}

// ElapsedMS returns elapsed time in milliseconds
func (rc *RequestContext) ElapsedMS() float64 {
	return float64(time.Since(rc.StartTime).Nanoseconds()) / 1e6
}