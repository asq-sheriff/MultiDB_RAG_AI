package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"
	"github.com/MultiDB-Chatbot/microservices/shared/models"
)

// Health check endpoints
func (s *ConsentService) healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":    "healthy",
		"timestamp": time.Now().Format(time.RFC3339),
		"service":   "consent-service-go",
		"version":   "1.0.0",
	})
}

func (s *ConsentService) readinessCheck(c *gin.Context) {
	// Check database connection
	if err := s.db.Ping(); err != nil {
		s.logger.Error("Database health check failed", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status": "not_ready",
			"reason": "database_unavailable",
		})
		return
	}
	
	// Check Redis connection with a simple exists check
	if _, err := s.cache.Exists("health_check"); err != nil {
		s.logger.Error("Redis health check failed", zap.Error(err))
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status": "not_ready",
			"reason": "cache_unavailable",
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"status": "ready",
		"checks": gin.H{
			"database": "healthy",
			"cache":    "healthy",
		},
	})
}

// HIPAA-compliant consent management handlers
type CreateConsentRequest struct {
	PatientID          uuid.UUID           `json:"patient_id" binding:"required"`
	GrantorID          uuid.UUID           `json:"grantor_id" binding:"required"`
	GranteeID          uuid.UUID           `json:"grantee_id" binding:"required"`
	Purpose            models.AccessPurpose `json:"purpose" binding:"required"`
	DataTypes          []string            `json:"data_types" binding:"required"`
	ExpiresAt          *time.Time          `json:"expires_at"`
	ConsentDocumentPath *string            `json:"consent_document_path"`
}

type ConsentResponse struct {
	ConsentID           uuid.UUID           `json:"consent_id"`
	PatientID          uuid.UUID           `json:"patient_id"`
	GrantorID          uuid.UUID           `json:"grantor_id"`
	GranteeID          uuid.UUID           `json:"grantee_id"`
	Purpose            models.AccessPurpose `json:"purpose"`
	DataTypes          []string            `json:"data_types"`
	Status             models.ConsentStatus `json:"status"`
	GrantedAt          time.Time           `json:"granted_at"`
	ExpiresAt          *time.Time          `json:"expires_at"`
	RevokedAt          *time.Time          `json:"revoked_at"`
	ConsentDocumentPath *string            `json:"consent_document_path"`
}

func (s *ConsentService) createConsent(c *gin.Context) {
	var req CreateConsentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		s.logger.Error("Invalid consent creation request", zap.Error(err))
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request format",
			"details": err.Error(),
		})
		return
	}
	
	// Validate HIPAA compliance requirements
	if err := s.validateConsentRequirements(req); err != nil {
		s.logger.Error("HIPAA consent validation failed", zap.Error(err))
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "HIPAA compliance violation",
			"details": err.Error(),
		})
		return
	}
	
	// Create consent record
	consent, err := s.db.CreatePatientConsent(models.CreatePatientConsentParams{
		PatientID:           req.PatientID,
		GrantorID:           req.GrantorID,
		GranteeID:           req.GranteeID,
		Purpose:             req.Purpose,
		DataTypes:           req.DataTypes,
		ExpiresAt:           req.ExpiresAt,
		ConsentDocumentPath: req.ConsentDocumentPath,
	})
	
	if err != nil {
		s.logger.Error("Failed to create consent", 
			zap.Error(err),
			zap.String("patient_id", req.PatientID.String()))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create consent",
		})
		return
	}
	
	// Log consent creation for audit trail
	s.logConsentAction("created", consent.ConsentID, req.GrantorID, 
		"Consent created for "+string(req.Purpose)+" access")
	
	// Invalidate related cache
	s.cache.InvalidatePatientConsents(req.PatientID)
	
	response := ConsentResponse{
		ConsentID:           consent.ConsentID,
		PatientID:          consent.PatientID,
		GrantorID:          consent.GrantorID,
		GranteeID:          consent.GranteeID,
		Purpose:            consent.Purpose,
		DataTypes:          consent.DataTypes,
		Status:             consent.Status,
		GrantedAt:          consent.GrantedAt,
		ExpiresAt:          consent.ExpiresAt,
		RevokedAt:          consent.RevokedAt,
		ConsentDocumentPath: consent.ConsentDocumentPath,
	}
	
	c.JSON(http.StatusCreated, response)
}

type RevokeConsentRequest struct {
	Reason *string `json:"reason"`
}

func (s *ConsentService) revokeConsent(c *gin.Context) {
	consentIDStr := c.Param("consent_id")
	consentID, err := uuid.Parse(consentIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid consent ID format",
		})
		return
	}
	
	var req RevokeConsentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		// Reason is optional
		req.Reason = nil
	}
	
	// Get current user from context (set by auth middleware)
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "User authentication required",
		})
		return
	}
	
	// Revoke consent with authorization check
	success, err := s.db.RevokeConsent(models.RevokeConsentParams{
		ConsentID: consentID,
		RevokedBy: userID.(uuid.UUID),
		Reason:    req.Reason,
	})
	
	if err != nil {
		s.logger.Error("Failed to revoke consent", 
			zap.Error(err),
			zap.String("consent_id", consentID.String()))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to revoke consent",
		})
		return
	}
	
	if !success {
		c.JSON(http.StatusForbidden, gin.H{
			"error": "Not authorized to revoke this consent",
		})
		return
	}
	
	// Log revocation
	reason := "Patient requested revocation"
	if req.Reason != nil {
		reason = *req.Reason
	}
	s.logConsentAction("revoked", consentID, userID.(uuid.UUID), reason)
	
	c.JSON(http.StatusOK, gin.H{
		"message": "Consent revoked successfully",
	})
}

func (s *ConsentService) getPatientConsents(c *gin.Context) {
	patientIDStr := c.Param("patient_id")
	patientID, err := uuid.Parse(patientIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid patient ID format",
		})
		return
	}
	
	activeOnly := c.DefaultQuery("active_only", "true") == "true"
	
	// Check cache first
	cacheKey := "patient_consents:" + patientID.String() + ":" + strconv.FormatBool(activeOnly)
	if cached, err := s.cache.Get(cacheKey); err == nil && cached != "" {
		c.Header("X-Cache", "HIT")
		c.JSON(http.StatusOK, cached)
		return
	}
	
	// Get from database
	consents, err := s.db.GetPatientConsents(models.GetPatientConsentsParams{
		PatientID:  patientID,
		ActiveOnly: activeOnly,
	})
	
	if err != nil {
		s.logger.Error("Failed to get patient consents", 
			zap.Error(err),
			zap.String("patient_id", patientID.String()))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to retrieve consents",
		})
		return
	}
	
	// Convert to response format
	response := make([]ConsentResponse, len(consents))
	for i, consent := range consents {
		response[i] = ConsentResponse{
			ConsentID:           consent.ConsentID,
			PatientID:          consent.PatientID,
			GrantorID:          consent.GrantorID,
			GranteeID:          consent.GranteeID,
			Purpose:            consent.Purpose,
			DataTypes:          consent.DataTypes,
			Status:             consent.Status,
			GrantedAt:          consent.GrantedAt,
			ExpiresAt:          consent.ExpiresAt,
			RevokedAt:          consent.RevokedAt,
			ConsentDocumentPath: consent.ConsentDocumentPath,
		}
	}
	
	// Cache the result
	if responseJSON, err := json.Marshal(response); err == nil {
		s.cache.Set(cacheKey, string(responseJSON), 5*time.Minute)
	}
	
	c.Header("X-Cache", "MISS")
	c.JSON(http.StatusOK, response)
}

type ValidateAccessRequest struct {
	UserID         uuid.UUID           `json:"user_id" binding:"required"`
	PatientID      uuid.UUID           `json:"patient_id" binding:"required"`
	Purpose        models.AccessPurpose `json:"purpose" binding:"required"`
	DataTypes      []string            `json:"data_types" binding:"required"`
	EmergencyJustification *string     `json:"emergency_justification"`
}

type AccessDecisionResponse struct {
	Granted             bool       `json:"granted"`
	Reason              string     `json:"reason"`
	ConsentID           *uuid.UUID `json:"consent_id,omitempty"`
	RelationshipID      *uuid.UUID `json:"relationship_id,omitempty"`
	EmergencyAccess     bool       `json:"emergency_access"`
	Timestamp           time.Time  `json:"timestamp"`
}

func (s *ConsentService) validateAccess(c *gin.Context) {
	var req ValidateAccessRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid access validation request",
			"details": err.Error(),
		})
		return
	}
	
	// Perform HIPAA-compliant access validation
	decision, err := s.db.CheckDataAccess(models.CheckDataAccessParams{
		UserID:                 req.UserID,
		PatientID:             req.PatientID,
		Purpose:               req.Purpose,
		DataTypes:             req.DataTypes,
		EmergencyJustification: req.EmergencyJustification,
	})
	
	if err != nil {
		s.logger.Error("Access validation failed", 
			zap.Error(err),
			zap.String("user_id", req.UserID.String()),
			zap.String("patient_id", req.PatientID.String()))
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Access validation failed",
		})
		return
	}
	
	response := AccessDecisionResponse{
		Granted:         decision.Granted,
		Reason:          decision.Reason,
		ConsentID:       decision.ConsentID,
		RelationshipID:  decision.RelationshipID,
		EmergencyAccess: decision.EmergencyAccess,
		Timestamp:       decision.Timestamp,
	}
	
	c.JSON(http.StatusOK, response)
}

// Helper methods
func (s *ConsentService) validateConsentRequirements(req CreateConsentRequest) error {
	// Implement HIPAA consent validation logic
	// - Check grantor authority
	// - Validate purpose-role compatibility
	// - Ensure minimum necessary principle
	// - Verify data types are appropriate
	return nil
}

func (s *ConsentService) logConsentAction(action string, consentID uuid.UUID, userID uuid.UUID, details string) {
	// Log to audit trail
	s.logger.Info("Consent action performed",
		zap.String("action", action),
		zap.String("consent_id", consentID.String()),
		zap.String("user_id", userID.String()),
		zap.String("details", details),
		zap.Time("timestamp", time.Now()))
	
	// Also log to database audit table
	go func() {
		if err := s.db.LogConsentAction(models.LogConsentActionParams{
			Action:    action,
			ConsentID: consentID,
			UserID:    userID,
			Details:   details,
		}); err != nil {
			s.logger.Error("Failed to log consent action to database", zap.Error(err))
		}
	}()
}

// Missing service methods that need to be implemented

func (s *ConsentService) getPatientRightsDashboard(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "Patient rights dashboard endpoint",
		"status": "not_implemented_yet",
	})
}

func (s *ConsentService) getAccessLog(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "Access log endpoint", 
		"status": "not_implemented_yet",
	})
}

func (s *ConsentService) grantFamilyAccess(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "Grant family access endpoint",
		"status": "not_implemented_yet",
	})
}

func (s *ConsentService) createTreatmentRelationship(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "Create treatment relationship endpoint",
		"status": "not_implemented_yet", 
	})
}

func (s *ConsentService) createFamilyRelationship(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "Create family relationship endpoint",
		"status": "not_implemented_yet",
	})
}

func (s *ConsentService) getActiveRelationships(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"message": "Get active relationships endpoint",
		"status": "not_implemented_yet",
	})
}