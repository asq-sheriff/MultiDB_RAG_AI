package main

import (
	"fmt"
	"regexp"
	"time"

	"go.uber.org/zap"
)

// SafetyAnalyzer handles content safety analysis
type SafetyAnalyzer struct {
	logger          *zap.Logger
	crisisPatterns  map[string][]*regexp.Regexp
	riskPatterns    map[RiskLevel][]*regexp.Regexp
	guidelines      map[string][]string
}

// NewSafetyAnalyzer creates a new safety analyzer
func NewSafetyAnalyzer(logger *zap.Logger) *SafetyAnalyzer {
	sa := &SafetyAnalyzer{
		logger: logger,
	}
	
	sa.loadCrisisPatterns()
	sa.loadRiskPatterns()
	sa.loadSafetyGuidelines()
	
	logger.Info("✅ Safety Analyzer initialized")
	return sa
}

// loadCrisisPatterns loads crisis detection patterns
func (sa *SafetyAnalyzer) loadCrisisPatterns() {
	sa.crisisPatterns = map[string][]*regexp.Regexp{
		"suicidal_ideation": {
			regexp.MustCompile(`(?i)\b(?:want to|going to|plan to)\s+(?:kill|end|hurt)\s+myself\b`),
			regexp.MustCompile(`(?i)\b(?:suicide|suicidal|end my life|take my own life)\b`),
			regexp.MustCompile(`(?i)\b(?:no point|no reason)\s+(?:in\s+)?living\b`),
			regexp.MustCompile(`(?i)\bbetter off dead\b`),
			regexp.MustCompile(`(?i)\bwant to die\b`),
		},
		"self_harm": {
			regexp.MustCompile(`(?i)\b(?:cut|cutting|harm|hurt)\s+myself\b`),
			regexp.MustCompile(`(?i)\bself[\s-]harm`),
			regexp.MustCompile(`(?i)\b(?:razors?|blades?|knives?)\s+(?:to|for)\s+(?:cut|harm)`),
		},
		"violence": {
			regexp.MustCompile(`(?i)\b(?:want to|going to)\s+(?:kill|hurt|harm)\s+(?:someone|others?)\b`),
			regexp.MustCompile(`(?i)\b(?:violent|dangerous)\s+thoughts?\b`),
			regexp.MustCompile(`(?i)\bmake them pay\b`),
		},
		"emergency": {
			regexp.MustCompile(`(?i)\bemergency\b`),
			regexp.MustCompile(`(?i)\bcall\s+(?:911|ambulance|police)\b`),
			regexp.MustCompile(`(?i)\b(?:overdose|overdosed)\b`),
			regexp.MustCompile(`(?i)\bcan'?t breathe\b`),
		},
	}
}

// loadRiskPatterns loads risk level assessment patterns
func (sa *SafetyAnalyzer) loadRiskPatterns() {
	sa.riskPatterns = map[RiskLevel][]*regexp.Regexp{
		RiskHigh: {
			regexp.MustCompile(`(?i)\b(?:severe|extreme|unbearable)\s+(?:depression|anxiety|pain)\b`),
			regexp.MustCompile(`(?i)\bcan'?t\s+(?:go on|take it|handle it)\b`),
			regexp.MustCompile(`(?i)\bhopeless|helpless|worthless\b`),
			regexp.MustCompile(`(?i)\bisolated|abandoned|alone\b`),
		},
		RiskMedium: {
			regexp.MustCompile(`(?i)\b(?:worried|anxious|stressed|depressed)\b`),
			regexp.MustCompile(`(?i)\bfeeling\s+(?:down|low|sad|blue)\b`),
			regexp.MustCompile(`(?i)\btrouble\s+(?:sleeping|eating|concentrating)\b`),
			regexp.MustCompile(`(?i)\boverwhelmed\b`),
		},
		RiskLow: {
			regexp.MustCompile(`(?i)\ba\s+(?:little|bit)\s+(?:sad|worried|anxious)\b`),
			regexp.MustCompile(`(?i)\bslightly\s+(?:concerned|troubled)\b`),
			regexp.MustCompile(`(?i)\bnot\s+feeling\s+(?:great|good)\b`),
		},
	}
}

// loadSafetyGuidelines loads therapeutic safety guidelines
func (sa *SafetyAnalyzer) loadSafetyGuidelines() {
	sa.guidelines = map[string][]string{
		"do": {
			"Listen actively and validate emotions",
			"Provide supportive and empathetic responses",
			"Offer coping strategies and self-care suggestions", 
			"Encourage professional help when appropriate",
			"Maintain appropriate boundaries",
			"Respect cultural sensitivity",
			"Focus on strengths and resilience",
		},
		"dont": {
			"Provide medical diagnoses or treatment advice",
			"Make assumptions about mental health conditions",
			"Dismiss or minimize emotions",
			"Share personal information inappropriately",
			"Encourage harmful behaviors",
			"Make promises you cannot keep",
			"Use judgmental language",
		},
		"escalate": {
			"Expressions of suicidal ideation",
			"Threats of self-harm or violence",
			"Severe crisis situations",
			"Requests for emergency medical intervention",
			"Child abuse or neglect disclosures",
			"Elder abuse indicators",
			"Immediate safety concerns",
		},
	}
}

// AnalyzeContent performs comprehensive safety analysis
func (sa *SafetyAnalyzer) AnalyzeContent(content string, ctx *RequestContext) (*SafetyAnalysisResult, error) {
	sa.logger.Info("Analyzing content safety",
		zap.String("request_id", ctx.RequestID),
		zap.String("user_id", ctx.UserID),
		zap.Int("content_length", len(content)),
	)

	startTime := time.Now()
	violations := []SafetyViolation{}

	// 1. Crisis detection (highest priority)
	crisisViolations := sa.detectCrisisIndicators(content)
	violations = append(violations, crisisViolations...)

	// 2. Risk level assessment
	riskViolations := sa.assessRiskLevel(content)
	violations = append(violations, riskViolations...)

	// 3. Safety guideline violations
	guidelineViolations := sa.checkSafetyGuidelines(content)
	violations = append(violations, guidelineViolations...)

	// Calculate overall metrics
	overallConfidence := sa.calculateOverallConfidence(violations)
	riskLevel := sa.determineRiskLevel(violations)
	riskScore := sa.calculateRiskScore(violations)

	// Generate recommendations
	recommendations := sa.generateRecommendations(violations, riskLevel)

	// Determine intervention needs
	requiresIntervention := riskLevel == RiskHigh || riskLevel == RiskCritical
	escalationNeeded := sa.hasEscalationViolations(violations)

	// Safety determination
	isSafe := (riskLevel == RiskNone || riskLevel == RiskLow) && !escalationNeeded

	processingTime := float64(time.Since(startTime).Nanoseconds()) / 1e6

	result := &SafetyAnalysisResult{
		IsSafe:                isSafe,
		RiskLevel:            riskLevel,
		Violations:           violations,
		OverallConfidence:    overallConfidence,
		RiskScore:            riskScore,
		Recommendations:      recommendations,
		RequiresIntervention: requiresIntervention,
		EscalationNeeded:     escalationNeeded,
		ProcessingTimeMS:     processingTime,
	}

	sa.logger.Info("Safety analysis completed",
		zap.String("request_id", ctx.RequestID),
		zap.Bool("is_safe", isSafe),
		zap.String("risk_level", string(riskLevel)),
		zap.Int("violations_count", len(violations)),
		zap.Float64("processing_time_ms", processingTime),
	)

	return result, nil
}

// detectCrisisIndicators detects crisis patterns requiring immediate attention
func (sa *SafetyAnalyzer) detectCrisisIndicators(content string) []SafetyViolation {
	violations := []SafetyViolation{}

	for crisisType, patterns := range sa.crisisPatterns {
		for _, pattern := range patterns {
			matches := pattern.FindAllStringIndex(content, -1)
			for _, match := range matches {
				violation := SafetyViolation{
					Type:        "crisis",
					Description: fmt.Sprintf("Crisis indicator detected: %s", crisisType),
					Severity:    RiskCritical,
					StartPos:    match[0],
					EndPos:      match[1],
					Confidence:  0.9,
				}
				violations = append(violations, violation)
			}
		}
	}

	return violations
}

// assessRiskLevel assesses overall risk level based on content patterns
func (sa *SafetyAnalyzer) assessRiskLevel(content string) []SafetyViolation {
	violations := []SafetyViolation{}

	for riskLevel, patterns := range sa.riskPatterns {
		for _, pattern := range patterns {
			matches := pattern.FindAllStringIndex(content, -1)
			for _, match := range matches {
				violation := SafetyViolation{
					Type:        "risk_indicator",
					Description: fmt.Sprintf("Risk indicator: %s level", string(riskLevel)),
					Severity:    riskLevel,
					StartPos:    match[0],
					EndPos:      match[1],
					Confidence:  0.7,
				}
				violations = append(violations, violation)
			}
		}
	}

	return violations
}

// checkSafetyGuidelines checks for safety guideline violations
func (sa *SafetyAnalyzer) checkSafetyGuidelines(content string) []SafetyViolation {
	violations := []SafetyViolation{}

	// Check for inappropriate medical advice
	medicalAdvicePatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)\b(?:diagnose|diagnosis|prescribe|medication)\b`),
		regexp.MustCompile(`(?i)\byou\s+(?:have|need)\s+(?:therapy|treatment|medication)\b`),
		regexp.MustCompile(`(?i)\bstop\s+taking\s+your\s+medication\b`),
	}

	for _, pattern := range medicalAdvicePatterns {
		matches := pattern.FindAllStringIndex(content, -1)
		for _, match := range matches {
			violation := SafetyViolation{
				Type:        "guideline_violation",
				Description: "Inappropriate medical advice detected",
				Severity:    RiskMedium,
				StartPos:    match[0],
				EndPos:      match[1],
				Confidence:  0.6,
			}
			violations = append(violations, violation)
		}
	}

	// Check for judgmental language
	judgmentalPatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)\byou\s+(?:should|must|need to)\s+(?:just|simply)`),
		regexp.MustCompile(`(?i)\bstop\s+being\s+(?:dramatic|sensitive|weak)\b`),
		regexp.MustCompile(`(?i)\bget\s+over\s+it\b`),
	}

	for _, pattern := range judgmentalPatterns {
		matches := pattern.FindAllStringIndex(content, -1)
		for _, match := range matches {
			violation := SafetyViolation{
				Type:        "guideline_violation",
				Description: "Judgmental language detected",
				Severity:    RiskLow,
				StartPos:    match[0],
				EndPos:      match[1],
				Confidence:  0.5,
			}
			violations = append(violations, violation)
		}
	}

	return violations
}

// calculateOverallConfidence calculates overall confidence in safety analysis
func (sa *SafetyAnalyzer) calculateOverallConfidence(violations []SafetyViolation) float64 {
	if len(violations) == 0 {
		return 0.8 // High confidence in safe content
	}

	severityWeights := map[RiskLevel]float64{
		RiskCritical: 1.0,
		RiskHigh:     0.8,
		RiskMedium:   0.6,
		RiskLow:      0.4,
		RiskNone:     0.2,
	}

	totalWeight := 0.0
	weightedConfidence := 0.0

	for _, violation := range violations {
		weight := severityWeights[violation.Severity]
		totalWeight += weight
		weightedConfidence += violation.Confidence * weight
	}

	if totalWeight > 0 {
		result := weightedConfidence / totalWeight
		if result > 1.0 {
			return 1.0
		}
		return result
	}
	return 0.5
}

// determineRiskLevel determines overall risk level from violations
func (sa *SafetyAnalyzer) determineRiskLevel(violations []SafetyViolation) RiskLevel {
	if len(violations) == 0 {
		return RiskNone
	}

	// Return highest severity level
	maxRisk := RiskNone
	for _, violation := range violations {
		if sa.isHigherRisk(violation.Severity, maxRisk) {
			maxRisk = violation.Severity
		}
	}

	return maxRisk
}

// isHigherRisk checks if risk level A is higher than risk level B
func (sa *SafetyAnalyzer) isHigherRisk(a, b RiskLevel) bool {
	riskOrder := map[RiskLevel]int{
		RiskNone:     0,
		RiskLow:      1,
		RiskMedium:   2,
		RiskHigh:     3,
		RiskCritical: 4,
	}
	return riskOrder[a] > riskOrder[b]
}

// calculateRiskScore calculates numerical risk score (0.0 = safe, 1.0 = critical)
func (sa *SafetyAnalyzer) calculateRiskScore(violations []SafetyViolation) float64 {
	if len(violations) == 0 {
		return 0.0
	}

	severityScores := map[RiskLevel]float64{
		RiskCritical: 1.0,
		RiskHigh:     0.8,
		RiskMedium:   0.5,
		RiskLow:      0.2,
		RiskNone:     0.0,
	}

	totalScore := 0.0
	for _, violation := range violations {
		baseScore := severityScores[violation.Severity]
		confidenceWeighted := baseScore * violation.Confidence
		totalScore += confidenceWeighted
	}

	// Normalize by violation count (with diminishing returns)
	normalizedScore := totalScore / float64(len(violations)+1)
	
	if normalizedScore > 1.0 {
		return 1.0
	}
	return normalizedScore
}

// generateRecommendations generates safety recommendations based on analysis
func (sa *SafetyAnalyzer) generateRecommendations(violations []SafetyViolation, riskLevel RiskLevel) []string {
	recommendations := []string{}

	// Crisis-specific recommendations
	crisisViolations := sa.filterViolationsByType(violations, "crisis")
	if len(crisisViolations) > 0 {
		recommendations = append(recommendations,
			"Immediate professional intervention required",
			"Contact crisis support services (988 Suicide & Crisis Lifeline)",
			"Ensure user safety is prioritized",
			"Document and escalate to human supervisors",
		)
	}

	// Risk-level based recommendations
	switch riskLevel {
	case RiskHigh:
		recommendations = append(recommendations,
			"Consider professional mental health support",
			"Monitor conversation closely",
			"Provide crisis resource information",
			"Use supportive, non-judgmental language",
		)
	case RiskMedium:
		recommendations = append(recommendations,
			"Offer emotional support and validation",
			"Suggest coping strategies",
			"Recommend talking to trusted individuals",
			"Provide mental health resources",
		)
	case RiskLow:
		recommendations = append(recommendations,
			"Continue supportive conversation",
			"Validate feelings and experiences",
			"Offer gentle encouragement",
			"Monitor for changes in emotional state",
		)
	}

	// Guideline violation recommendations
	guidelineViolations := sa.filterViolationsByType(violations, "guideline_violation")
	if len(guidelineViolations) > 0 {
		recommendations = append(recommendations,
			"Review therapeutic conversation guidelines",
			"Avoid medical advice or diagnoses",
			"Use empathetic, non-judgmental language",
			"Focus on emotional support rather than solutions",
		)
	}

	return sa.removeDuplicates(recommendations)
}

// hasEscalationViolations checks if any violations require escalation
func (sa *SafetyAnalyzer) hasEscalationViolations(violations []SafetyViolation) bool {
	for _, violation := range violations {
		if violation.Type == "crisis" || violation.Severity == RiskCritical {
			return true
		}
	}
	return false
}

// filterViolationsByType filters violations by type
func (sa *SafetyAnalyzer) filterViolationsByType(violations []SafetyViolation, violationType string) []SafetyViolation {
	filtered := []SafetyViolation{}
	for _, violation := range violations {
		if violation.Type == violationType {
			filtered = append(filtered, violation)
		}
	}
	return filtered
}

// removeDuplicates removes duplicate strings from slice
func (sa *SafetyAnalyzer) removeDuplicates(slice []string) []string {
	keys := make(map[string]bool)
	result := []string{}
	
	for _, item := range slice {
		if !keys[item] {
			keys[item] = true
			result = append(result, item)
		}
	}
	return result
}

// GetGuidelines returns the safety guidelines
func (sa *SafetyAnalyzer) GetGuidelines() map[string][]string {
	return sa.guidelines
}