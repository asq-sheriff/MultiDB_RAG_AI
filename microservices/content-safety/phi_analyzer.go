package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"io"
	"regexp"
	"strings"
	"time"

	"go.uber.org/zap"
)

// PHIAnalyzer handles HIPAA PHI detection and protection
type PHIAnalyzer struct {
	logger           *zap.Logger
	identifierPatterns map[string][]*regexp.Regexp
	encryptionKey    []byte
}

// NewPHIAnalyzer creates a new PHI analyzer
func NewPHIAnalyzer(logger *zap.Logger) *PHIAnalyzer {
	pa := &PHIAnalyzer{
		logger: logger,
	}
	
	pa.loadIdentifierPatterns()
	pa.generateEncryptionKey()
	
	logger.Info("✅ PHI Analyzer initialized")
	return pa
}

// loadIdentifierPatterns loads HIPAA identifier detection patterns
func (pa *PHIAnalyzer) loadIdentifierPatterns() {
	pa.identifierPatterns = map[string][]*regexp.Regexp{
		"name": {
			regexp.MustCompile(`\b[A-Z][a-z]+\s+[A-Z][a-z]+\b`), // First Last
			regexp.MustCompile(`\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+\b`), // Title Name
		},
		"ssn": {
			regexp.MustCompile(`\b\d{3}-\d{2}-\d{4}\b`), // 123-45-6789
			regexp.MustCompile(`\b\d{9}\b`), // 123456789
		},
		"date_of_birth": {
			regexp.MustCompile(`\b(?:0[1-9]|1[0-2])[\/\-](?:0[1-9]|[12]\d|3[01])[\/\-](?:19|20)\d{2}\b`), // MM/DD/YYYY
			regexp.MustCompile(`\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+(?:19|20)\d{2}\b`), // Month DD, YYYY
		},
		"phone": {
			regexp.MustCompile(`\b(?:\+?1[\s\-]?)?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}\b`), // Phone numbers
		},
		"email": {
			regexp.MustCompile(`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`), // Email addresses
		},
		"medical_record": {
			regexp.MustCompile(`\b(?:MRN|MR|Record|ID)[\s:#-]*[A-Z0-9]{6,12}\b`), // Medical record numbers
		},
		"account_number": {
			regexp.MustCompile(`\b(?:Account|Acct)[\s:#-]*[0-9]{6,12}\b`), // Account numbers
		},
		"certificate": {
			regexp.MustCompile(`\b(?:Certificate|Cert)[\s:#-]*[A-Z0-9]{6,15}\b`), // Certificate numbers
		},
		"url": {
			regexp.MustCompile(`\bhttps?://[^\s]+\b`), // Web URLs
		},
		"ip_address": {
			regexp.MustCompile(`\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b`), // IP addresses
		},
		"device_id": {
			regexp.MustCompile(`\b[A-Z0-9]{8,20}\b`), // Device identifiers
		},
		"biometric": {
			regexp.MustCompile(`\b(?:fingerprint|retina|iris|face)\s+(?:scan|id|data)\b`), // Biometric references
		},
		"full_face_photo": {
			regexp.MustCompile(`\b(?:photo|picture|image)\s+(?:of|showing)\s+(?:face|person)\b`), // Face photo references
		},
		"vehicle_id": {
			regexp.MustCompile(`\b[A-Z0-9]{17}\b`), // VIN numbers
			regexp.MustCompile(`\b[A-Z]{2,3}[\s\-]?\d{3,4}\b`), // License plates
		},
	}
}

// generateEncryptionKey generates a random encryption key for PHI protection
func (pa *PHIAnalyzer) generateEncryptionKey() {
	pa.encryptionKey = make([]byte, 32) // 256-bit key for AES-256
	if _, err := io.ReadFull(rand.Reader, pa.encryptionKey); err != nil {
		pa.logger.Error("Failed to generate encryption key", zap.Error(err))
		// Fallback to deterministic key (not secure for production!)
		copy(pa.encryptionKey, []byte("demo-key-not-for-production-use!"))
	}
}

// DetectPHI performs comprehensive PHI detection and protection
func (pa *PHIAnalyzer) DetectPHI(content string, analysisMode string, ctx *RequestContext) (*PHIDetectionResult, error) {
	pa.logger.Info("Detecting PHI",
		zap.String("request_id", ctx.RequestID),
		zap.String("user_id", ctx.UserID),
		zap.String("analysis_mode", analysisMode),
		zap.Int("content_length", len(content)),
	)

	startTime := time.Now()
	identifiers := []PHIIdentifier{}

	// Detect all HIPAA identifiers
	for identifierType, patterns := range pa.identifierPatterns {
		for _, pattern := range patterns {
			matches := pattern.FindAllStringSubmatchIndex(content, -1)
			for _, match := range matches {
				if len(match) >= 2 {
					matchedText := content[match[0]:match[1]]
					confidence := pa.calculatePHIConfidence(identifierType, matchedText)
					
					identifier := PHIIdentifier{
						Type:       identifierType,
						Value:      matchedText,
						StartPos:   match[0],
						EndPos:     match[1],
						Confidence: confidence,
						HIPAAClass: pa.getHIPAAClass(identifierType),
					}
					identifiers = append(identifiers, identifier)
				}
			}
		}
	}

	// Determine overall PHI detection status
	phiDetected := len(identifiers) > 0
	riskLevel := pa.calculatePHIRiskLevel(identifiers)

	// Generate redacted/encrypted content based on analysis mode
	redactedContent := ""
	encryptedContent := ""
	
	if phiDetected {
		switch analysisMode {
		case "redact":
			redactedContent = pa.redactPHI(content, identifiers)
		case "encrypt":
			var err error
			encryptedContent, err = pa.encryptPHI(content, identifiers)
			if err != nil {
				pa.logger.Error("PHI encryption failed", zap.Error(err))
			}
		}
	}

	// Determine compliance status
	complianceStatus := pa.assessComplianceStatus(identifiers, riskLevel)

	processingTime := float64(time.Since(startTime).Nanoseconds()) / 1e6

	result := &PHIDetectionResult{
		PHIDetected:      phiDetected,
		Identifiers:      identifiers,
		RedactedContent:  redactedContent,
		EncryptedContent: encryptedContent,
		RiskLevel:        riskLevel,
		ProcessingTimeMS: processingTime,
		ComplianceStatus: complianceStatus,
	}

	pa.logger.Info("PHI detection completed",
		zap.String("request_id", ctx.RequestID),
		zap.Bool("phi_detected", phiDetected),
		zap.String("risk_level", string(riskLevel)),
		zap.Int("identifiers_count", len(identifiers)),
		zap.Float64("processing_time_ms", processingTime),
	)

	return result, nil
}

// calculatePHIConfidence calculates confidence score for PHI detection
func (pa *PHIAnalyzer) calculatePHIConfidence(identifierType, matchedText string) float64 {
	confidenceMap := map[string]float64{
		"ssn":             0.95, // SSN patterns are very specific
		"phone":           0.85, // Phone patterns fairly specific
		"email":           0.90, // Email patterns specific
		"date_of_birth":   0.75, // Could be other dates
		"medical_record":  0.85, // Medical context makes it specific
		"account_number":  0.80, // Account context specific
		"certificate":     0.75, // Could be other certificates
		"url":             0.70, // URLs could contain PHI
		"ip_address":      0.60, // IP addresses somewhat identifiable
		"device_id":       0.55, // Device IDs potentially identifiable
		"biometric":       0.95, // Biometric references are clearly PHI
		"full_face_photo": 0.90, // Face photos are clearly PHI
		"vehicle_id":      0.80, // Vehicle identifiers fairly specific
		"name":            0.40, // Name patterns have many false positives
	}

	baseConfidence, exists := confidenceMap[identifierType]
	if !exists {
		baseConfidence = 0.5
	}

	// Adjust confidence based on context and length
	lengthBonus := 0.0
	if len(matchedText) > 10 {
		lengthBonus = 0.1
	}

	// Check for medical context keywords
	medicalContext := strings.Contains(strings.ToLower(matchedText), "patient") ||
		strings.Contains(strings.ToLower(matchedText), "medical") ||
		strings.Contains(strings.ToLower(matchedText), "doctor")
	
	contextBonus := 0.0
	if medicalContext {
		contextBonus = 0.1
	}

	finalConfidence := baseConfidence + lengthBonus + contextBonus
	if finalConfidence > 1.0 {
		return 1.0
	}
	return finalConfidence
}

// getHIPAAClass returns the HIPAA identifier class for the given type
func (pa *PHIAnalyzer) getHIPAAClass(identifierType string) string {
	hipaaClasses := map[string]string{
		"name":            "Individual names",
		"ssn":             "Social Security numbers", 
		"date_of_birth":   "Dates related to an individual",
		"phone":           "Telephone numbers",
		"email":           "Electronic mail addresses",
		"medical_record":  "Medical record numbers",
		"account_number":  "Account numbers",
		"certificate":     "Certificate/license numbers", 
		"url":             "Web Universal Resource Locators (URLs)",
		"ip_address":      "Internet Protocol (IP) address numbers",
		"device_id":       "Device identifiers and serial numbers",
		"biometric":       "Biometric identifiers",
		"full_face_photo": "Full face photographic images",
		"vehicle_id":      "Vehicle identifiers and serial numbers",
	}

	if class, exists := hipaaClasses[identifierType]; exists {
		return class
	}
	return "Other identifying information"
}

// calculatePHIRiskLevel determines overall risk level based on detected PHI
func (pa *PHIAnalyzer) calculatePHIRiskLevel(identifiers []PHIIdentifier) RiskLevel {
	if len(identifiers) == 0 {
		return RiskNone
	}

	// High-risk identifiers
	highRiskTypes := map[string]bool{
		"ssn":             true,
		"medical_record":  true,
		"biometric":       true,
		"full_face_photo": true,
	}

	// Medium-risk identifiers
	mediumRiskTypes := map[string]bool{
		"date_of_birth":  true,
		"account_number": true,
		"phone":          true,
		"email":          true,
	}

	criticalCount := 0
	highCount := 0
	mediumCount := 0

	for _, identifier := range identifiers {
		if highRiskTypes[identifier.Type] && identifier.Confidence > 0.8 {
			criticalCount++
		} else if mediumRiskTypes[identifier.Type] && identifier.Confidence > 0.7 {
			highCount++
		} else if identifier.Confidence > 0.6 {
			mediumCount++
		}
	}

	// Determine risk level based on counts and severity
	if criticalCount > 0 {
		return RiskCritical
	}
	if highCount >= 2 || (highCount >= 1 && mediumCount >= 2) {
		return RiskHigh
	}
	if highCount >= 1 || mediumCount >= 2 {
		return RiskMedium
	}
	if mediumCount >= 1 {
		return RiskLow
	}

	return RiskNone
}

// redactPHI redacts PHI from content
func (pa *PHIAnalyzer) redactPHI(content string, identifiers []PHIIdentifier) string {
	redacted := content
	
	// Sort identifiers by position (reverse order to maintain positions)
	sortedIdentifiers := make([]PHIIdentifier, len(identifiers))
	copy(sortedIdentifiers, identifiers)
	
	// Simple reverse sort by start position
	for i := 0; i < len(sortedIdentifiers)-1; i++ {
		for j := i + 1; j < len(sortedIdentifiers); j++ {
			if sortedIdentifiers[i].StartPos < sortedIdentifiers[j].StartPos {
				sortedIdentifiers[i], sortedIdentifiers[j] = sortedIdentifiers[j], sortedIdentifiers[i]
			}
		}
	}

	for _, identifier := range sortedIdentifiers {
		if identifier.Confidence > 0.6 { // Only redact high-confidence identifiers
			redactionText := pa.getRedactionText(identifier.Type)
			redacted = redacted[:identifier.StartPos] + redactionText + redacted[identifier.EndPos:]
		}
	}

	return redacted
}

// getRedactionText returns appropriate redaction text for identifier type
func (pa *PHIAnalyzer) getRedactionText(identifierType string) string {
	redactionMap := map[string]string{
		"name":            "[NAME_REDACTED]",
		"ssn":             "[SSN_REDACTED]", 
		"date_of_birth":   "[DOB_REDACTED]",
		"phone":           "[PHONE_REDACTED]",
		"email":           "[EMAIL_REDACTED]",
		"medical_record":  "[MRN_REDACTED]",
		"account_number":  "[ACCOUNT_REDACTED]",
		"certificate":     "[CERT_REDACTED]",
		"url":             "[URL_REDACTED]",
		"ip_address":      "[IP_REDACTED]",
		"device_id":       "[DEVICE_REDACTED]",
		"biometric":       "[BIOMETRIC_REDACTED]",
		"full_face_photo": "[PHOTO_REDACTED]",
		"vehicle_id":      "[VEHICLE_REDACTED]",
	}

	if redaction, exists := redactionMap[identifierType]; exists {
		return redaction
	}
	return "[PHI_REDACTED]"
}

// encryptPHI encrypts PHI in content using AES-256-GCM
func (pa *PHIAnalyzer) encryptPHI(content string, identifiers []PHIIdentifier) (string, error) {
	if len(pa.encryptionKey) != 32 {
		return "", fmt.Errorf("invalid encryption key length: %d", len(pa.encryptionKey))
	}

	block, err := aes.NewCipher(pa.encryptionKey)
	if err != nil {
		return "", fmt.Errorf("failed to create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("failed to create GCM: %w", err)
	}

	// Create nonce
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", fmt.Errorf("failed to generate nonce: %w", err)
	}

	// Encrypt the content
	ciphertext := gcm.Seal(nonce, nonce, []byte(content), nil)
	
	// Encode to base64 for safe transmission
	encoded := base64.StdEncoding.EncodeToString(ciphertext)
	
	return encoded, nil
}

// assessComplianceStatus assesses HIPAA compliance based on detected PHI
func (pa *PHIAnalyzer) assessComplianceStatus(identifiers []PHIIdentifier, riskLevel RiskLevel) ComplianceStatus {
	isCompliant := true
	violationTypes := []string{}
	requiredActions := []string{}
	auditRequired := false

	// Check for high-risk violations
	if riskLevel == RiskCritical || riskLevel == RiskHigh {
		isCompliant = false
		auditRequired = true
		
		// Identify specific violation types
		for _, identifier := range identifiers {
			if identifier.Confidence > 0.8 {
				violationType := fmt.Sprintf("Detected %s with high confidence", identifier.HIPAAClass)
				violationTypes = append(violationTypes, violationType)
			}
		}

		// Required actions based on risk level
		if riskLevel == RiskCritical {
			requiredActions = append(requiredActions,
				"Immediate PHI redaction or encryption required",
				"Escalate to HIPAA compliance officer",
				"Document incident in audit log",
				"Review access controls and permissions",
			)
		} else if riskLevel == RiskHigh {
			requiredActions = append(requiredActions,
				"PHI redaction or encryption recommended", 
				"Review content handling procedures",
				"Update staff training on PHI handling",
			)
		}
	}

	// Medium risk = warning but compliant with monitoring
	if riskLevel == RiskMedium {
		auditRequired = true
		requiredActions = append(requiredActions,
			"Monitor for additional PHI patterns",
			"Consider enhanced content filtering",
		)
	}

	return ComplianceStatus{
		IsCompliant:     isCompliant,
		ViolationTypes:  pa.removeDuplicateStrings(violationTypes),
		RequiredActions: pa.removeDuplicateStrings(requiredActions),
		AuditRequired:   auditRequired,
	}
}

// removeDuplicateStrings removes duplicate strings from slice
func (pa *PHIAnalyzer) removeDuplicateStrings(slice []string) []string {
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