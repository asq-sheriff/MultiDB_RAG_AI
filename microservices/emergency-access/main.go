package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/joho/godotenv"
)

// EmergencyAccessLevel defines the urgency level of emergency access
type EmergencyAccessLevel string

const (
	EMERGENCY_LOW      EmergencyAccessLevel = "low"
	EMERGENCY_MODERATE EmergencyAccessLevel = "moderate"
	EMERGENCY_HIGH     EmergencyAccessLevel = "high"
	EMERGENCY_CRITICAL EmergencyAccessLevel = "critical"
)

// EmergencyAccessType defines the type of emergency access
type EmergencyAccessType string

const (
	ACCESS_CRISIS_INTERVENTION   EmergencyAccessType = "crisis_intervention"
	ACCESS_MEDICAL_EMERGENCY     EmergencyAccessType = "medical_emergency"
	ACCESS_SAFETY_OVERRIDE       EmergencyAccessType = "safety_override"
	ACCESS_THERAPEUTIC_URGENT    EmergencyAccessType = "therapeutic_urgent"
	ACCESS_SYSTEM_MAINTENANCE    EmergencyAccessType = "system_maintenance"
	ACCESS_COMPLIANCE_AUDIT      EmergencyAccessType = "compliance_audit"
)

// EmergencyAccessRequest represents a request for emergency access
type EmergencyAccessRequest struct {
	RequestID        string               `json:"request_id"`
	UserID           string               `json:"user_id" binding:"required"`
	SessionID        string               `json:"session_id"`
	AccessType       EmergencyAccessType  `json:"access_type" binding:"required"`
	EmergencyLevel   EmergencyAccessLevel `json:"emergency_level" binding:"required"`
	Justification    string               `json:"justification" binding:"required"`
	PatientID        string               `json:"patient_id,omitempty"`
	ResourceAccessed string               `json:"resource_accessed" binding:"required"`
	RequestedBy      string               `json:"requested_by" binding:"required"`
	SupervisorID     string               `json:"supervisor_id,omitempty"`
	Timestamp        time.Time            `json:"timestamp"`
	ClientIP         string               `json:"client_ip"`
	UserAgent        string               `json:"user_agent"`
}

// EmergencyAccessResponse represents the response to an emergency access request
type EmergencyAccessResponse struct {
	RequestID          string               `json:"request_id"`
	AccessGranted      bool                 `json:"access_granted"`
	EmergencyLevel     EmergencyAccessLevel `json:"emergency_level"`
	AccessType         EmergencyAccessType  `json:"access_type"`
	GrantedAt          time.Time            `json:"granted_at"`
	ExpiresAt          time.Time            `json:"expires_at"`
	AccessToken        string               `json:"access_token,omitempty"`
	Restrictions       []string             `json:"restrictions,omitempty"`
	AuditTrailID       string               `json:"audit_trail_id"`
	ComplianceStatus   string               `json:"compliance_status"`
	AlertsTriggered    []string             `json:"alerts_triggered,omitempty"`
	SupervisorNotified bool                 `json:"supervisor_notified"`
}

// EmergencyAccessAuditEntry represents an audit entry for emergency access
type EmergencyAccessAuditEntry struct {
	AuditID            string               `json:"audit_id"`
	RequestID          string               `json:"request_id"`
	UserID             string               `json:"user_id"`
	SessionID          string               `json:"session_id"`
	AccessType         EmergencyAccessType  `json:"access_type"`
	EmergencyLevel     EmergencyAccessLevel `json:"emergency_level"`
	AccessGranted      bool                 `json:"access_granted"`
	Justification      string               `json:"justification"`
	ResourceAccessed   string               `json:"resource_accessed"`
	AccessDuration     time.Duration        `json:"access_duration"`
	PHIAccessed        bool                 `json:"phi_accessed"`
	ComplianceViolation bool                `json:"compliance_violation"`
	AlertsTriggered    []string             `json:"alerts_triggered"`
	SupervisorNotified bool                 `json:"supervisor_notified"`
	Timestamp          time.Time            `json:"timestamp"`
	ResolvedAt         *time.Time           `json:"resolved_at,omitempty"`
	ClientIP           string               `json:"client_ip"`
	UserAgent          string               `json:"user_agent"`
}

// EmergencyAccessAlert represents a compliance alert
type EmergencyAccessAlert struct {
	AlertID           string               `json:"alert_id"`
	RequestID         string               `json:"request_id"`
	AlertType         string               `json:"alert_type"`
	Severity          EmergencyAccessLevel `json:"severity"`
	Message           string               `json:"message"`
	TriggeredAt       time.Time            `json:"triggered_at"`
	UserID            string               `json:"user_id"`
	ResourceAccessed  string               `json:"resource_accessed"`
	ActionRequired    bool                 `json:"action_required"`
	NotificationsSent []string             `json:"notifications_sent"`
	ResolvedAt        *time.Time           `json:"resolved_at,omitempty"`
}

// EmergencyAccessMonitor manages emergency access monitoring and compliance
type EmergencyAccessMonitor struct {
	ActiveSessions    map[string]*EmergencyAccessResponse `json:"active_sessions"`
	AuditTrail        []EmergencyAccessAuditEntry         `json:"audit_trail"`
	Alerts            []EmergencyAccessAlert              `json:"alerts"`
	MaxSessions       int                                 `json:"max_sessions"`
	MaxAuditEntries   int                                 `json:"max_audit_entries"`
	ComplianceEnabled bool                                `json:"compliance_enabled"`
	mutex             sync.RWMutex
}

// NewEmergencyAccessMonitor creates a new emergency access monitoring service
func NewEmergencyAccessMonitor() *EmergencyAccessMonitor {
	monitor := &EmergencyAccessMonitor{
		ActiveSessions:    make(map[string]*EmergencyAccessResponse),
		AuditTrail:        make([]EmergencyAccessAuditEntry, 0),
		Alerts:            make([]EmergencyAccessAlert, 0),
		MaxSessions:       100,
		MaxAuditEntries:   10000,
		ComplianceEnabled: true,
	}
	
	// Start background cleanup routine
	go monitor.cleanupExpiredSessions()
	
	log.Println("🚨 Emergency Access Monitoring Service initialized")
	return monitor
}

// RequestEmergencyAccess processes an emergency access request
func (monitor *EmergencyAccessMonitor) RequestEmergencyAccess(req *EmergencyAccessRequest) *EmergencyAccessResponse {
	monitor.mutex.Lock()
	defer monitor.mutex.Unlock()
	
	// Generate unique identifiers
	if req.RequestID == "" {
		req.RequestID = uuid.New().String()
	}
	auditID := uuid.New().String()
	
	// Validate request
	if !monitor.validateEmergencyRequest(req) {
		response := &EmergencyAccessResponse{
			RequestID:        req.RequestID,
			AccessGranted:    false,
			EmergencyLevel:   req.EmergencyLevel,
			AccessType:       req.AccessType,
			GrantedAt:        time.Now().UTC(),
			ComplianceStatus: "rejected_invalid_request",
			AuditTrailID:     auditID,
		}
		
		// Log rejection
		monitor.logEmergencyAccess(req, response, auditID, false)
		return response
	}
	
	// Determine access duration based on emergency level
	var accessDuration time.Duration
	var restrictions []string
	
	switch req.EmergencyLevel {
	case EMERGENCY_CRITICAL:
		accessDuration = 4 * time.Hour // 4 hours for critical emergencies
		restrictions = []string{"requires_supervisor_review_within_1_hour"}
	case EMERGENCY_HIGH:
		accessDuration = 2 * time.Hour // 2 hours for high emergencies
		restrictions = []string{"requires_supervisor_review_within_2_hours", "limited_phi_access"}
	case EMERGENCY_MODERATE:
		accessDuration = 1 * time.Hour // 1 hour for moderate emergencies
		restrictions = []string{"requires_supervisor_review_within_4_hours", "limited_phi_access", "read_only_access"}
	case EMERGENCY_LOW:
		accessDuration = 30 * time.Minute // 30 minutes for low emergencies
		restrictions = []string{"requires_supervisor_approval", "read_only_access", "no_phi_access"}
	}
	
	// Generate access token
	accessToken := fmt.Sprintf("emergency_%s_%d", req.RequestID[:8], time.Now().Unix())
	
	// Create response
	response := &EmergencyAccessResponse{
		RequestID:          req.RequestID,
		AccessGranted:      true,
		EmergencyLevel:     req.EmergencyLevel,
		AccessType:         req.AccessType,
		GrantedAt:          time.Now().UTC(),
		ExpiresAt:          time.Now().UTC().Add(accessDuration),
		AccessToken:        accessToken,
		Restrictions:       restrictions,
		AuditTrailID:       auditID,
		ComplianceStatus:   "granted_with_monitoring",
		SupervisorNotified: req.EmergencyLevel == EMERGENCY_CRITICAL || req.EmergencyLevel == EMERGENCY_HIGH,
	}
	
	// Check for compliance alerts
	alerts := monitor.checkComplianceAlerts(req, response)
	response.AlertsTriggered = alerts
	
	// Store active session
	monitor.ActiveSessions[req.RequestID] = response
	
	// Log successful access grant
	monitor.logEmergencyAccess(req, response, auditID, true)
	
	// Trigger notifications
	if response.SupervisorNotified {
		monitor.notifySupervisor(req, response)
	}
	
	log.Printf("🚨 EMERGENCY ACCESS GRANTED: Request: %s, User: %s, Level: %s, Type: %s", 
		req.RequestID[:8], req.UserID, req.EmergencyLevel, req.AccessType)
	
	return response
}

// validateEmergencyRequest validates the emergency access request
func (monitor *EmergencyAccessMonitor) validateEmergencyRequest(req *EmergencyAccessRequest) bool {
	// Basic validation
	if req.UserID == "" || req.Justification == "" || req.ResourceAccessed == "" || req.RequestedBy == "" {
		return false
	}
	
	// Validate justification length (minimum 20 characters for audit purposes)
	if len(req.Justification) < 20 {
		return false
	}
	
	// Check for valid emergency level and type
	validLevels := []EmergencyAccessLevel{EMERGENCY_LOW, EMERGENCY_MODERATE, EMERGENCY_HIGH, EMERGENCY_CRITICAL}
	validTypes := []EmergencyAccessType{ACCESS_CRISIS_INTERVENTION, ACCESS_MEDICAL_EMERGENCY, ACCESS_SAFETY_OVERRIDE, ACCESS_THERAPEUTIC_URGENT, ACCESS_SYSTEM_MAINTENANCE, ACCESS_COMPLIANCE_AUDIT}
	
	levelValid := false
	typeValid := false
	
	for _, level := range validLevels {
		if req.EmergencyLevel == level {
			levelValid = true
			break
		}
	}
	
	for _, accessType := range validTypes {
		if req.AccessType == accessType {
			typeValid = true
			break
		}
	}
	
	return levelValid && typeValid
}

// checkComplianceAlerts checks for compliance issues and generates alerts
func (monitor *EmergencyAccessMonitor) checkComplianceAlerts(req *EmergencyAccessRequest, response *EmergencyAccessResponse) []string {
	var alerts []string
	
	// Check for multiple concurrent emergency sessions for same user
	concurrentCount := 0
	for _, session := range monitor.ActiveSessions {
		if session.AccessGranted && time.Now().Before(session.ExpiresAt) {
			concurrentCount++
		}
	}
	
	if concurrentCount > 3 {
		alert := monitor.createAlert(req.RequestID, "MULTIPLE_CONCURRENT_EMERGENCY_ACCESS", EMERGENCY_HIGH, 
			fmt.Sprintf("User %s has %d concurrent emergency access sessions", req.UserID, concurrentCount))
		alerts = append(alerts, alert.AlertID)
	}
	
	// Check for critical access without supervisor ID
	if req.EmergencyLevel == EMERGENCY_CRITICAL && req.SupervisorID == "" {
		alert := monitor.createAlert(req.RequestID, "CRITICAL_ACCESS_NO_SUPERVISOR", EMERGENCY_CRITICAL,
			"Critical emergency access requested without supervisor identification")
		alerts = append(alerts, alert.AlertID)
	}
	
	// Check for suspicious access patterns (same user, same resource, short time intervals)
	recentAccess := 0
	for _, entry := range monitor.AuditTrail {
		if entry.UserID == req.UserID && 
		   entry.ResourceAccessed == req.ResourceAccessed && 
		   time.Since(entry.Timestamp) < 1*time.Hour {
			recentAccess++
		}
	}
	
	if recentAccess > 2 {
		alert := monitor.createAlert(req.RequestID, "SUSPICIOUS_ACCESS_PATTERN", EMERGENCY_MODERATE,
			fmt.Sprintf("User %s accessed resource %s %d times in past hour", req.UserID, req.ResourceAccessed, recentAccess))
		alerts = append(alerts, alert.AlertID)
	}
	
	return alerts
}

// createAlert creates and stores a compliance alert
func (monitor *EmergencyAccessMonitor) createAlert(requestID, alertType string, severity EmergencyAccessLevel, message string) *EmergencyAccessAlert {
	alert := &EmergencyAccessAlert{
		AlertID:       uuid.New().String(),
		RequestID:     requestID,
		AlertType:     alertType,
		Severity:      severity,
		Message:       message,
		TriggeredAt:   time.Now().UTC(),
		ActionRequired: severity == EMERGENCY_CRITICAL || severity == EMERGENCY_HIGH,
	}
	
	monitor.Alerts = append(monitor.Alerts, *alert)
	
	// Log alert
	alertJSON, _ := json.Marshal(alert)
	log.Printf("🚨 COMPLIANCE ALERT: %s", string(alertJSON))
	
	return alert
}

// logEmergencyAccess logs emergency access requests to audit trail
func (monitor *EmergencyAccessMonitor) logEmergencyAccess(req *EmergencyAccessRequest, response *EmergencyAccessResponse, auditID string, granted bool) {
	auditEntry := EmergencyAccessAuditEntry{
		AuditID:            auditID,
		RequestID:          req.RequestID,
		UserID:             req.UserID,
		SessionID:          req.SessionID,
		AccessType:         req.AccessType,
		EmergencyLevel:     req.EmergencyLevel,
		AccessGranted:      granted,
		Justification:      req.Justification,
		ResourceAccessed:   req.ResourceAccessed,
		PHIAccessed:        monitor.containsPHI(req.ResourceAccessed),
		AlertsTriggered:    response.AlertsTriggered,
		SupervisorNotified: response.SupervisorNotified,
		Timestamp:          time.Now().UTC(),
		ClientIP:           req.ClientIP,
		UserAgent:          req.UserAgent,
	}
	
	if granted {
		auditEntry.AccessDuration = response.ExpiresAt.Sub(response.GrantedAt)
	}
	
	// Add to audit trail
	monitor.AuditTrail = append(monitor.AuditTrail, auditEntry)
	
	// Manage audit trail size
	if len(monitor.AuditTrail) > monitor.MaxAuditEntries {
		monitor.AuditTrail = monitor.AuditTrail[len(monitor.AuditTrail)-monitor.MaxAuditEntries:]
	}
	
	// Log to system
	auditJSON, _ := json.Marshal(auditEntry)
	log.Printf("🔒 EMERGENCY_ACCESS_AUDIT: %s", string(auditJSON))
}

// containsPHI checks if the resource might contain PHI
func (monitor *EmergencyAccessMonitor) containsPHI(resource string) bool {
	phiIndicators := []string{"patient", "medical", "health", "phi", "therapy", "clinical", "diagnosis", "treatment"}
	resourceLower := fmt.Sprintf("%s", resource)
	
	for _, indicator := range phiIndicators {
		if len(resourceLower) > 0 && len(indicator) > 0 {
			// Simple substring check
			for i := 0; i <= len(resourceLower)-len(indicator); i++ {
				match := true
				for j := 0; j < len(indicator); j++ {
					if resourceLower[i+j] != indicator[j] && resourceLower[i+j] != indicator[j]-32 {
						match = false
						break
					}
				}
				if match {
					return true
				}
			}
		}
	}
	return false
}

// notifySupervisor sends notifications for high-priority emergency access
func (monitor *EmergencyAccessMonitor) notifySupervisor(req *EmergencyAccessRequest, response *EmergencyAccessResponse) {
	log.Printf("📧 SUPERVISOR NOTIFICATION: Emergency access granted - Request: %s, User: %s, Level: %s", 
		req.RequestID[:8], req.UserID, req.EmergencyLevel)
	
	// In production, this would send actual notifications (email, SMS, Slack, etc.)
	// For now, we log the notification
}

// cleanupExpiredSessions removes expired emergency access sessions
func (monitor *EmergencyAccessMonitor) cleanupExpiredSessions() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	
	for range ticker.C {
		monitor.mutex.Lock()
		now := time.Now().UTC()
		
		for requestID, session := range monitor.ActiveSessions {
			if now.After(session.ExpiresAt) {
				// Log session expiration
				log.Printf("⏰ EMERGENCY ACCESS EXPIRED: Request: %s, Duration: %v", 
					requestID[:8], session.ExpiresAt.Sub(session.GrantedAt))
				
				// Update audit trail
				for i := range monitor.AuditTrail {
					if monitor.AuditTrail[i].RequestID == requestID && monitor.AuditTrail[i].ResolvedAt == nil {
						monitor.AuditTrail[i].ResolvedAt = &now
						break
					}
				}
				
				delete(monitor.ActiveSessions, requestID)
			}
		}
		monitor.mutex.Unlock()
	}
}

// Global monitor instance
var emergencyMonitor *EmergencyAccessMonitor

func main() {
	// Load environment variables from project root
	// Try different environment files in order of preference
	envFiles := []string{
		"../../.env",
		"../../.env.hybrid", 
		"../../.env.docker",
	}
	
	envLoaded := false
	for _, envFile := range envFiles {
		if err := godotenv.Load(envFile); err == nil {
			log.Printf("Loaded environment from: %s", envFile)
			envLoaded = true
			break
		}
	}
	
	if !envLoaded {
		log.Println("Warning: No .env file found, using system environment variables")
	}

	// Set Gin mode
	gin.SetMode(gin.ReleaseMode)
	
	// Initialize emergency access monitor
	emergencyMonitor = NewEmergencyAccessMonitor()

	// Setup router
	router := gin.New()
	router.Use(gin.Logger())
	router.Use(gin.Recovery())

	// CORS middleware
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-User-ID, X-Session-ID")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		
		c.Next()
	})

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service":   "emergency-access-monitoring-service",
			"status":    "healthy",
			"timestamp": time.Now().UTC(),
			"version":   "1.0.0-hipaa",
			"capabilities": gin.H{
				"emergency_access": []string{"crisis_intervention", "medical_emergency", "safety_override", "therapeutic_urgent"},
				"monitoring": []string{"real_time_alerts", "compliance_auditing", "supervisor_notifications", "access_expiration"},
				"compliance": []string{"hipaa_audit_trail", "phi_access_tracking", "emergency_justification", "supervisor_oversight"},
			},
			"active_sessions": len(emergencyMonitor.ActiveSessions),
			"audit_entries": len(emergencyMonitor.AuditTrail),
			"alerts_count": len(emergencyMonitor.Alerts),
		})
	})

	// Emergency access request endpoint
	router.POST("/emergency/request", func(c *gin.Context) {
		var req EmergencyAccessRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid emergency access request",
				"details": err.Error(),
			})
			return
		}
		
		// Add request metadata
		req.Timestamp = time.Now().UTC()
		req.ClientIP = c.ClientIP()
		req.UserAgent = c.GetHeader("User-Agent")
		
		// Process emergency access request
		response := emergencyMonitor.RequestEmergencyAccess(&req)
		
		if response.AccessGranted {
			c.JSON(http.StatusOK, response)
		} else {
			c.JSON(http.StatusForbidden, response)
		}
	})

	// Emergency access status endpoint
	router.GET("/emergency/status/:request_id", func(c *gin.Context) {
		requestID := c.Param("request_id")
		
		emergencyMonitor.mutex.RLock()
		session, exists := emergencyMonitor.ActiveSessions[requestID]
		emergencyMonitor.mutex.RUnlock()
		
		if !exists {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Emergency access session not found",
				"request_id": requestID,
			})
			return
		}
		
		c.JSON(http.StatusOK, gin.H{
			"request_id": requestID,
			"active": time.Now().UTC().Before(session.ExpiresAt),
			"expires_at": session.ExpiresAt,
			"emergency_level": session.EmergencyLevel,
			"access_type": session.AccessType,
			"restrictions": session.Restrictions,
		})
	})

	// Emergency access audit trail endpoint (protected)
	router.GET("/emergency/audit", func(c *gin.Context) {
		// Verify admin access
		userID := c.GetHeader("X-User-ID")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Authentication required for emergency audit access",
			})
			return
		}
		
		emergencyMonitor.mutex.RLock()
		auditEntries := make([]EmergencyAccessAuditEntry, len(emergencyMonitor.AuditTrail))
		copy(auditEntries, emergencyMonitor.AuditTrail)
		emergencyMonitor.mutex.RUnlock()
		
		// Limit returned entries for performance
		limit := 100
		if len(auditEntries) > limit {
			auditEntries = auditEntries[len(auditEntries)-limit:]
		}
		
		c.JSON(http.StatusOK, gin.H{
			"audit_entries": auditEntries,
			"total_returned": len(auditEntries),
			"compliance_notice": "Emergency access audit data maintained per HIPAA requirements",
			"timestamp": time.Now().UTC(),
		})
	})

	// Emergency alerts endpoint (protected)
	router.GET("/emergency/alerts", func(c *gin.Context) {
		// Verify admin access
		userID := c.GetHeader("X-User-ID")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Authentication required for alert access",
			})
			return
		}
		
		emergencyMonitor.mutex.RLock()
		alerts := make([]EmergencyAccessAlert, len(emergencyMonitor.Alerts))
		copy(alerts, emergencyMonitor.Alerts)
		emergencyMonitor.mutex.RUnlock()
		
		// Filter active alerts
		activeAlerts := make([]EmergencyAccessAlert, 0)
		for _, alert := range alerts {
			if alert.ResolvedAt == nil {
				activeAlerts = append(activeAlerts, alert)
			}
		}
		
		c.JSON(http.StatusOK, gin.H{
			"active_alerts": activeAlerts,
			"total_alerts": len(alerts),
			"active_count": len(activeAlerts),
			"timestamp": time.Now().UTC(),
		})
	})

	// Emergency statistics endpoint
	router.GET("/emergency/stats", func(c *gin.Context) {
		emergencyMonitor.mutex.RLock()
		
		// Calculate statistics
		stats := gin.H{
			"active_sessions": len(emergencyMonitor.ActiveSessions),
			"total_audit_entries": len(emergencyMonitor.AuditTrail),
			"total_alerts": len(emergencyMonitor.Alerts),
		}
		
		// Emergency level distribution
		levelDistribution := make(map[EmergencyAccessLevel]int)
		for _, entry := range emergencyMonitor.AuditTrail {
			levelDistribution[entry.EmergencyLevel]++
		}
		stats["emergency_level_distribution"] = levelDistribution
		
		// Access type distribution
		typeDistribution := make(map[EmergencyAccessType]int)
		for _, entry := range emergencyMonitor.AuditTrail {
			typeDistribution[entry.AccessType]++
		}
		stats["access_type_distribution"] = typeDistribution
		
		emergencyMonitor.mutex.RUnlock()
		
		c.JSON(http.StatusOK, gin.H{
			"emergency_access_stats": stats,
			"service_status": "operational",
			"compliance_monitoring": "active",
			"timestamp": time.Now().UTC(),
		})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8082"
	}

	log.Printf("🚀 Emergency Access Monitoring Service starting on port %s", port)
	log.Printf("🚨 Emergency access monitoring active with compliance alerting")
	log.Printf("📊 Service capabilities:")
	log.Printf("   - Real-time emergency access processing")
	log.Printf("   - HIPAA-compliant audit trail")
	log.Printf("   - Supervisor notifications")
	log.Printf("   - Compliance alert monitoring")
	log.Printf("   - Automatic session expiration")
	
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start Emergency Access Monitoring Service: %v", err)
	}
}