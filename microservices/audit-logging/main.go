package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sort"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/joho/godotenv"
)

// AuditLogLevel defines the severity level of audit events
type AuditLogLevel string

const (
	AUDIT_DEBUG    AuditLogLevel = "debug"
	AUDIT_INFO     AuditLogLevel = "info"
	AUDIT_WARNING  AuditLogLevel = "warning"
	AUDIT_ERROR    AuditLogLevel = "error"
	AUDIT_CRITICAL AuditLogLevel = "critical"
)

// AuditEventType defines the type of audit event
type AuditEventType string

const (
	EVENT_USER_LOGIN           AuditEventType = "user_login"
	EVENT_USER_LOGOUT          AuditEventType = "user_logout"
	EVENT_PHI_ACCESS           AuditEventType = "phi_access"
	EVENT_EMERGENCY_ACCESS     AuditEventType = "emergency_access"
	EVENT_RELATIONSHIP_CHANGE  AuditEventType = "relationship_change"
	EVENT_CONSENT_CHANGE       AuditEventType = "consent_change"
	EVENT_DATA_EXPORT          AuditEventType = "data_export"
	EVENT_DATA_DELETION        AuditEventType = "data_deletion"
	EVENT_SYSTEM_CONFIG        AuditEventType = "system_config"
	EVENT_COMPLIANCE_VIOLATION AuditEventType = "compliance_violation"
	EVENT_SECURITY_INCIDENT    AuditEventType = "security_incident"
	EVENT_API_ACCESS           AuditEventType = "api_access"
	EVENT_SERVICE_START        AuditEventType = "service_start"
	EVENT_SERVICE_STOP         AuditEventType = "service_stop"
)

// AuditLogEntry represents a comprehensive audit log entry
type AuditLogEntry struct {
	// Core identification
	AuditID       string         `json:"audit_id"`
	Timestamp     time.Time      `json:"timestamp"`
	EventType     AuditEventType `json:"event_type"`
	LogLevel      AuditLogLevel  `json:"log_level"`
	ServiceName   string         `json:"service_name"`
	ServiceHost   string         `json:"service_host,omitempty"`
	
	// User and session context
	UserID        string         `json:"user_id,omitempty"`
	SessionID     string         `json:"session_id,omitempty"`
	PatientID     string         `json:"patient_id,omitempty"`
	RequestID     string         `json:"request_id,omitempty"`
	
	// Event details
	Event         AuditEvent     `json:"event"`
	
	// Network and technical context
	ClientIP      string         `json:"client_ip,omitempty"`
	UserAgent     string         `json:"user_agent,omitempty"`
	RequestPath   string         `json:"request_path,omitempty"`
	HTTPMethod    string         `json:"http_method,omitempty"`
	StatusCode    int            `json:"status_code,omitempty"`
	
	// HIPAA compliance context
	PHIAccessed   bool           `json:"phi_accessed"`
	DataSensitivity string       `json:"data_sensitivity,omitempty"` // low, medium, high, critical
	ComplianceContext string     `json:"compliance_context,omitempty"`
	
	// Metadata
	Tags          []string       `json:"tags,omitempty"`
	Metadata      map[string]interface{} `json:"metadata,omitempty"`
	
	// Retention and archival
	RetentionPolicy string       `json:"retention_policy,omitempty"`
	ArchivedAt     *time.Time    `json:"archived_at,omitempty"`
}

// AuditEvent contains the specific details of an audit event
type AuditEvent struct {
	Action        string                 `json:"action"`
	Resource      string                 `json:"resource,omitempty"`
	ResourceType  string                 `json:"resource_type,omitempty"`
	Description   string                 `json:"description"`
	Success       bool                   `json:"success"`
	ErrorMessage  string                 `json:"error_message,omitempty"`
	Duration      *time.Duration         `json:"duration,omitempty"`
	Changes       []AuditChange          `json:"changes,omitempty"`
	Context       map[string]interface{} `json:"context,omitempty"`
}

// AuditChange represents a specific change made during an event
type AuditChange struct {
	Field     string      `json:"field"`
	OldValue  interface{} `json:"old_value,omitempty"`
	NewValue  interface{} `json:"new_value"`
	ChangeType string     `json:"change_type"` // create, update, delete
}

// ServiceRegistration represents a registered service for audit collection
type ServiceRegistration struct {
	ServiceName   string    `json:"service_name"`
	ServiceURL    string    `json:"service_url"`
	HealthCheck   string    `json:"health_check"`
	AuditEndpoint string    `json:"audit_endpoint"`
	LastSeen      time.Time `json:"last_seen"`
	Status        string    `json:"status"`
	Version       string    `json:"version,omitempty"`
}

// AuditAggregationReport represents aggregated audit statistics
type AuditAggregationReport struct {
	ReportID         string                    `json:"report_id"`
	GeneratedAt      time.Time                 `json:"generated_at"`
	ReportPeriod     string                    `json:"report_period"`
	TotalEvents      int                       `json:"total_events"`
	EventsByType     map[AuditEventType]int    `json:"events_by_type"`
	EventsByService  map[string]int            `json:"events_by_service"`
	EventsByLevel    map[AuditLogLevel]int     `json:"events_by_level"`
	PHIAccessEvents  int                       `json:"phi_access_events"`
	SecurityEvents   int                       `json:"security_events"`
	ComplianceScore  float64                   `json:"compliance_score"`
	TopUsers         []UserActivitySummary     `json:"top_users"`
	ServiceHealth    []ServiceHealthSummary    `json:"service_health"`
	Recommendations  []string                  `json:"recommendations"`
}

// UserActivitySummary summarizes user activity for audit reports
type UserActivitySummary struct {
	UserID          string `json:"user_id"`
	EventCount      int    `json:"event_count"`
	PHIAccesses     int    `json:"phi_accesses"`
	LastActivity    time.Time `json:"last_activity"`
	RiskScore       int    `json:"risk_score"`
}

// ServiceHealthSummary summarizes service health for audit reports
type ServiceHealthSummary struct {
	ServiceName     string    `json:"service_name"`
	Status          string    `json:"status"`
	EventCount      int       `json:"event_count"`
	ErrorRate       float64   `json:"error_rate"`
	LastAuditEvent  time.Time `json:"last_audit_event"`
	AvgResponseTime *float64  `json:"avg_response_time,omitempty"`
}

// ComprehensiveAuditLogger manages centralized audit logging
type ComprehensiveAuditLogger struct {
	AuditEntries      []AuditLogEntry           `json:"audit_entries"`
	ServiceRegistry   map[string]ServiceRegistration `json:"service_registry"`
	MaxEntries        int                       `json:"max_entries"`
	RetentionDays     int                       `json:"retention_days"`
	AggregationReports []AuditAggregationReport `json:"aggregation_reports"`
	mutex             sync.RWMutex
}

// NewComprehensiveAuditLogger creates a new audit logging service
func NewComprehensiveAuditLogger() *ComprehensiveAuditLogger {
	logger := &ComprehensiveAuditLogger{
		AuditEntries:       make([]AuditLogEntry, 0),
		ServiceRegistry:    make(map[string]ServiceRegistration),
		MaxEntries:         100000, // Store up to 100k audit entries
		RetentionDays:      2555,   // 7 years for HIPAA compliance
		AggregationReports: make([]AuditAggregationReport, 0),
	}
	
	// Start background processes
	go logger.periodicServiceHealthCheck()
	go logger.periodicAggregationReporting()
	go logger.periodicRetentionCleanup()
	go logger.collectFromRegisteredServices()
	
	// Register self as a service
	logger.registerSelfService()
	
	log.Println("🗂️ Comprehensive Audit Logging Service initialized")
	log.Printf("📊 Max Entries: %d | Retention: %d days", logger.MaxEntries, logger.RetentionDays)
	
	return logger
}

// registerSelfService registers the audit service itself
func (logger *ComprehensiveAuditLogger) registerSelfService() {
	selfRegistration := ServiceRegistration{
		ServiceName:   "audit-logging-service",
		ServiceURL:    fmt.Sprintf("http://localhost:%s", os.Getenv("PORT")),
		HealthCheck:   "/api/v1/health",
		AuditEndpoint: "/api/v1/audit-entries",
		LastSeen:      time.Now().UTC(),
		Status:        "active",
		Version:       "1.0.0",
	}
	
	logger.mutex.Lock()
	logger.ServiceRegistry["audit-logging-service"] = selfRegistration
	logger.mutex.Unlock()
	
	// Log service startup
	startupEntry := AuditLogEntry{
		AuditID:     uuid.New().String(),
		Timestamp:   time.Now().UTC(),
		EventType:   EVENT_SERVICE_START,
		LogLevel:    AUDIT_INFO,
		ServiceName: "audit-logging-service",
		ServiceHost: "localhost",
		Event: AuditEvent{
			Action:      "service_startup",
			Resource:    "audit-logging-service",
			Description: "Comprehensive audit logging service started successfully",
			Success:     true,
			Context: map[string]interface{}{
				"max_entries":    logger.MaxEntries,
				"retention_days": logger.RetentionDays,
				"version":        "1.0.0",
			},
		},
		PHIAccessed:       false,
		DataSensitivity:   "low",
		ComplianceContext: "system_initialization",
		RetentionPolicy:   "hipaa_compliant_7_years",
	}
	
	logger.LogAuditEntry(startupEntry)
}

// LogAuditEntry adds a new audit entry to the centralized log
func (logger *ComprehensiveAuditLogger) LogAuditEntry(entry AuditLogEntry) {
	logger.mutex.Lock()
	defer logger.mutex.Unlock()
	
	// Set audit ID if not provided
	if entry.AuditID == "" {
		entry.AuditID = uuid.New().String()
	}
	
	// Set timestamp if not provided
	if entry.Timestamp.IsZero() {
		entry.Timestamp = time.Now().UTC()
	}
	
	// Set retention policy based on PHI access
	if entry.RetentionPolicy == "" {
		if entry.PHIAccessed {
			entry.RetentionPolicy = "hipaa_phi_7_years"
		} else {
			entry.RetentionPolicy = "standard_1_year"
		}
	}
	
	// Add to entries
	logger.AuditEntries = append(logger.AuditEntries, entry)
	
	// Maintain size limit
	if len(logger.AuditEntries) > logger.MaxEntries {
		// Keep last 90% of entries
		keepCount := int(float64(logger.MaxEntries) * 0.9)
		logger.AuditEntries = logger.AuditEntries[len(logger.AuditEntries)-keepCount:]
	}
	
	// Log critical events immediately
	if entry.LogLevel == AUDIT_CRITICAL || entry.LogLevel == AUDIT_ERROR {
		log.Printf("🚨 CRITICAL AUDIT: %s | %s | %s | %s", 
			entry.AuditID[:8], entry.EventType, entry.ServiceName, entry.Event.Description)
	}
}

// RegisterService registers a service for audit collection
func (logger *ComprehensiveAuditLogger) RegisterService(registration ServiceRegistration) {
	logger.mutex.Lock()
	defer logger.mutex.Unlock()
	
	registration.LastSeen = time.Now().UTC()
	if registration.Status == "" {
		registration.Status = "active"
	}
	
	logger.ServiceRegistry[registration.ServiceName] = registration
	
	// Log service registration
	registrationEntry := AuditLogEntry{
		AuditID:     uuid.New().String(),
		Timestamp:   time.Now().UTC(),
		EventType:   EVENT_SERVICE_START,
		LogLevel:    AUDIT_INFO,
		ServiceName: "audit-logging-service",
		Event: AuditEvent{
			Action:      "service_registration",
			Resource:    registration.ServiceName,
			Description: fmt.Sprintf("Service %s registered for audit collection", registration.ServiceName),
			Success:     true,
			Context: map[string]interface{}{
				"service_url":     registration.ServiceURL,
				"health_check":    registration.HealthCheck,
				"audit_endpoint":  registration.AuditEndpoint,
				"version":         registration.Version,
			},
		},
		PHIAccessed:     false,
		DataSensitivity: "low",
		RetentionPolicy: "standard_1_year",
	}
	
	logger.LogAuditEntry(registrationEntry)
	
	log.Printf("📝 Service Registered: %s (%s)", registration.ServiceName, registration.ServiceURL)
}

// collectFromRegisteredServices periodically collects audit data from registered services
func (logger *ComprehensiveAuditLogger) collectFromRegisteredServices() {
	ticker := time.NewTicker(30 * time.Second) // Collect every 30 seconds
	defer ticker.Stop()
	
	for range ticker.C {
		logger.mutex.RLock()
		services := make([]ServiceRegistration, 0, len(logger.ServiceRegistry))
		for _, service := range logger.ServiceRegistry {
			if service.ServiceName != "audit-logging-service" { // Don't collect from self
				services = append(services, service)
			}
		}
		logger.mutex.RUnlock()
		
		for _, service := range services {
			go logger.collectFromService(service)
		}
	}
}

// collectFromService collects audit data from a specific service
func (logger *ComprehensiveAuditLogger) collectFromService(service ServiceRegistration) {
	if service.AuditEndpoint == "" {
		return
	}
	
	client := &http.Client{Timeout: 10 * time.Second}
	
	// Try to collect audit data
	url := fmt.Sprintf("%s%s", service.ServiceURL, service.AuditEndpoint)
	resp, err := client.Get(url)
	if err != nil {
		logger.logServiceCollectionError(service.ServiceName, fmt.Sprintf("Failed to connect: %v", err))
		return
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		logger.logServiceCollectionError(service.ServiceName, fmt.Sprintf("HTTP %d", resp.StatusCode))
		return
	}
	
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.logServiceCollectionError(service.ServiceName, fmt.Sprintf("Failed to read response: %v", err))
		return
	}
	
	// Parse audit entries
	var auditResponse struct {
		Entries []AuditLogEntry `json:"entries"`
		Total   int             `json:"total"`
	}
	
	if err := json.Unmarshal(body, &auditResponse); err != nil {
		// Try parsing as emergency access audit format
		var emergencyResponse struct {
			Entries []struct {
				AuditID              string                 `json:"audit_id"`
				RequestID            string                 `json:"request_id"`
				UserID               string                 `json:"user_id"`
				SessionID            string                 `json:"session_id"`
				AccessType           string                 `json:"access_type"`
				EmergencyLevel       string                 `json:"emergency_level"`
				AccessGranted        bool                   `json:"access_granted"`
				Justification        string                 `json:"justification"`
				ResourceAccessed     string                 `json:"resource_accessed"`
				PHIAccessed          bool                   `json:"phi_accessed"`
				ComplianceViolation  bool                   `json:"compliance_violation"`
				AlertsTriggered      []string               `json:"alerts_triggered"`
				SupervisorNotified   bool                   `json:"supervisor_notified"`
				RelationshipValidated bool                  `json:"relationship_validated"`
				ActionsPerformed     []string               `json:"actions_performed"`
				Timestamp            time.Time              `json:"timestamp"`
				ClientIP             string                 `json:"client_ip"`
				UserAgent            string                 `json:"user_agent"`
				RiskScore            int                    `json:"risk_score"`
			} `json:"entries"`
		}
		
		if err := json.Unmarshal(body, &emergencyResponse); err != nil {
			logger.logServiceCollectionError(service.ServiceName, fmt.Sprintf("Failed to parse response: %v", err))
			return
		}
		
		// Convert emergency access format to standard audit format
		for _, entry := range emergencyResponse.Entries {
			standardEntry := AuditLogEntry{
				AuditID:     entry.AuditID,
				Timestamp:   entry.Timestamp,
				EventType:   EVENT_EMERGENCY_ACCESS,
				LogLevel:    logger.determineLogLevel(entry.AccessGranted, entry.ComplianceViolation, entry.RiskScore),
				ServiceName: service.ServiceName,
				UserID:      entry.UserID,
				SessionID:   entry.SessionID,
				RequestID:   entry.RequestID,
				Event: AuditEvent{
					Action:      fmt.Sprintf("emergency_access_%s", entry.AccessType),
					Resource:    entry.ResourceAccessed,
					Description: entry.Justification,
					Success:     entry.AccessGranted,
					Context: map[string]interface{}{
						"emergency_level":       entry.EmergencyLevel,
						"access_type":           entry.AccessType,
						"supervisor_notified":   entry.SupervisorNotified,
						"relationship_validated": entry.RelationshipValidated,
						"actions_performed":     entry.ActionsPerformed,
						"alerts_triggered":      entry.AlertsTriggered,
						"risk_score":           entry.RiskScore,
					},
				},
				ClientIP:          entry.ClientIP,
				UserAgent:         entry.UserAgent,
				PHIAccessed:       entry.PHIAccessed,
				DataSensitivity:   logger.determineSensitivity(entry.PHIAccessed, entry.RiskScore),
				ComplianceContext: "emergency_access",
				Tags:              []string{"emergency", "access_control", entry.AccessType},
			}
			
			logger.LogAuditEntry(standardEntry)
		}
		
		logger.updateServiceHealth(service.ServiceName, true, len(emergencyResponse.Entries))
		return
	}
	
	// Process standard audit entries
	for _, entry := range auditResponse.Entries {
		entry.ServiceName = service.ServiceName // Ensure service name is set
		logger.LogAuditEntry(entry)
	}
	
	logger.updateServiceHealth(service.ServiceName, true, len(auditResponse.Entries))
}

// Helper functions for audit processing
func (logger *ComprehensiveAuditLogger) determineLogLevel(success bool, violation bool, riskScore int) AuditLogLevel {
	if violation {
		return AUDIT_CRITICAL
	}
	if !success {
		return AUDIT_ERROR
	}
	if riskScore > 70 {
		return AUDIT_WARNING
	}
	return AUDIT_INFO
}

func (logger *ComprehensiveAuditLogger) determineSensitivity(phiAccessed bool, riskScore int) string {
	if phiAccessed && riskScore > 70 {
		return "critical"
	}
	if phiAccessed {
		return "high"
	}
	if riskScore > 50 {
		return "medium"
	}
	return "low"
}

func (logger *ComprehensiveAuditLogger) logServiceCollectionError(serviceName, errorMsg string) {
	errorEntry := AuditLogEntry{
		AuditID:     uuid.New().String(),
		Timestamp:   time.Now().UTC(),
		EventType:   EVENT_SYSTEM_CONFIG,
		LogLevel:    AUDIT_WARNING,
		ServiceName: "audit-logging-service",
		Event: AuditEvent{
			Action:       "service_collection_failed",
			Resource:     serviceName,
			Description:  fmt.Sprintf("Failed to collect audit data from %s: %s", serviceName, errorMsg),
			Success:      false,
			ErrorMessage: errorMsg,
		},
		PHIAccessed:     false,
		DataSensitivity: "low",
		RetentionPolicy: "standard_1_year",
	}
	
	logger.LogAuditEntry(errorEntry)
}

func (logger *ComprehensiveAuditLogger) updateServiceHealth(serviceName string, success bool, entriesCount int) {
	logger.mutex.Lock()
	defer logger.mutex.Unlock()
	
	if service, exists := logger.ServiceRegistry[serviceName]; exists {
		service.LastSeen = time.Now().UTC()
		if success {
			service.Status = "active"
		} else {
			service.Status = "error"
		}
		logger.ServiceRegistry[serviceName] = service
	}
}

// periodicServiceHealthCheck performs periodic health checks on registered services
func (logger *ComprehensiveAuditLogger) periodicServiceHealthCheck() {
	ticker := time.NewTicker(2 * time.Minute) // Health check every 2 minutes
	defer ticker.Stop()
	
	for range ticker.C {
		logger.mutex.RLock()
		services := make([]ServiceRegistration, 0, len(logger.ServiceRegistry))
		for _, service := range logger.ServiceRegistry {
			services = append(services, service)
		}
		logger.mutex.RUnlock()
		
		for _, service := range services {
			if service.ServiceName == "audit-logging-service" {
				continue // Skip self
			}
			
			go logger.checkServiceHealth(service)
		}
	}
}

// checkServiceHealth checks the health of a specific service
func (logger *ComprehensiveAuditLogger) checkServiceHealth(service ServiceRegistration) {
	client := &http.Client{Timeout: 5 * time.Second}
	
	url := fmt.Sprintf("%s%s", service.ServiceURL, service.HealthCheck)
	resp, err := client.Get(url)
	
	healthy := false
	errorMsg := ""
	
	if err != nil {
		errorMsg = fmt.Sprintf("Health check failed: %v", err)
	} else {
		defer resp.Body.Close()
		if resp.StatusCode == http.StatusOK {
			healthy = true
		} else {
			errorMsg = fmt.Sprintf("Health check returned HTTP %d", resp.StatusCode)
		}
	}
	
	logger.mutex.Lock()
	if serviceReg, exists := logger.ServiceRegistry[service.ServiceName]; exists {
		serviceReg.LastSeen = time.Now().UTC()
		if healthy {
			serviceReg.Status = "active"
		} else {
			serviceReg.Status = "unhealthy"
		}
		logger.ServiceRegistry[service.ServiceName] = serviceReg
	}
	logger.mutex.Unlock()
	
	// Log health check results
	healthEntry := AuditLogEntry{
		AuditID:     uuid.New().String(),
		Timestamp:   time.Now().UTC(),
		EventType:   EVENT_SYSTEM_CONFIG,
		LogLevel:    func() AuditLogLevel {
			if healthy {
				return AUDIT_DEBUG
			}
			return AUDIT_WARNING
		}(),
		ServiceName: "audit-logging-service",
		Event: AuditEvent{
			Action:      "service_health_check",
			Resource:    service.ServiceName,
			Description: fmt.Sprintf("Health check for %s", service.ServiceName),
			Success:     healthy,
			ErrorMessage: errorMsg,
			Context: map[string]interface{}{
				"service_url": service.ServiceURL,
				"status":      service.Status,
			},
		},
		PHIAccessed:     false,
		DataSensitivity: "low",
		RetentionPolicy: "standard_1_year",
	}
	
	logger.LogAuditEntry(healthEntry)
}

// periodicAggregationReporting generates periodic aggregation reports
func (logger *ComprehensiveAuditLogger) periodicAggregationReporting() {
	ticker := time.NewTicker(1 * time.Hour) // Generate reports every hour
	defer ticker.Stop()
	
	for range ticker.C {
		report := logger.generateAggregationReport("hourly")
		
		logger.mutex.Lock()
		logger.AggregationReports = append(logger.AggregationReports, *report)
		
		// Keep last 168 reports (7 days of hourly reports)
		if len(logger.AggregationReports) > 168 {
			logger.AggregationReports = logger.AggregationReports[1:]
		}
		logger.mutex.Unlock()
		
		log.Printf("📊 Aggregation Report Generated: %s | Events: %d | Compliance: %.1f%%", 
			report.ReportID[:8], report.TotalEvents, report.ComplianceScore)
	}
}

// generateAggregationReport generates a comprehensive audit aggregation report
func (logger *ComprehensiveAuditLogger) generateAggregationReport(reportType string) *AuditAggregationReport {
	logger.mutex.RLock()
	defer logger.mutex.RUnlock()
	
	reportID := uuid.New().String()
	now := time.Now().UTC()
	
	// Determine report period
	var periodStart time.Time
	switch reportType {
	case "hourly":
		periodStart = now.Add(-1 * time.Hour)
	case "daily":
		periodStart = now.Add(-24 * time.Hour)
	case "weekly":
		periodStart = now.Add(-7 * 24 * time.Hour)
	case "monthly":
		periodStart = now.AddDate(0, -1, 0)
	default:
		periodStart = now.Add(-1 * time.Hour)
	}
	
	// Filter entries for the period
	var periodEntries []AuditLogEntry
	for _, entry := range logger.AuditEntries {
		if entry.Timestamp.After(periodStart) {
			periodEntries = append(periodEntries, entry)
		}
	}
	
	// Aggregate statistics
	eventsByType := make(map[AuditEventType]int)
	eventsByService := make(map[string]int)
	eventsByLevel := make(map[AuditLogLevel]int)
	phiAccessEvents := 0
	securityEvents := 0
	userActivity := make(map[string]*UserActivitySummary)
	serviceActivity := make(map[string]*ServiceHealthSummary)
	
	for _, entry := range periodEntries {
		eventsByType[entry.EventType]++
		eventsByService[entry.ServiceName]++
		eventsByLevel[entry.LogLevel]++
		
		if entry.PHIAccessed {
			phiAccessEvents++
		}
		
		if entry.EventType == EVENT_SECURITY_INCIDENT || entry.EventType == EVENT_COMPLIANCE_VIOLATION {
			securityEvents++
		}
		
		// Track user activity
		if entry.UserID != "" {
			if userSummary, exists := userActivity[entry.UserID]; exists {
				userSummary.EventCount++
				if entry.PHIAccessed {
					userSummary.PHIAccesses++
				}
				if entry.Timestamp.After(userSummary.LastActivity) {
					userSummary.LastActivity = entry.Timestamp
				}
			} else {
				phiCount := 0
				if entry.PHIAccessed {
					phiCount = 1
				}
				userActivity[entry.UserID] = &UserActivitySummary{
					UserID:       entry.UserID,
					EventCount:   1,
					PHIAccesses:  phiCount,
					LastActivity: entry.Timestamp,
					RiskScore:    logger.calculateUserRiskScore(entry.UserID, periodEntries),
				}
			}
		}
		
		// Track service activity
		if serviceSummary, exists := serviceActivity[entry.ServiceName]; exists {
			serviceSummary.EventCount++
			if !entry.Event.Success {
				serviceSummary.ErrorRate = float64(serviceSummary.EventCount-serviceSummary.EventCount) / float64(serviceSummary.EventCount) * 100
			}
			if entry.Timestamp.After(serviceSummary.LastAuditEvent) {
				serviceSummary.LastAuditEvent = entry.Timestamp
			}
		} else {
			errorRate := 0.0
			if !entry.Event.Success {
				errorRate = 100.0
			}
			
			status := "active"
			if service, exists := logger.ServiceRegistry[entry.ServiceName]; exists {
				status = service.Status
			}
			
			serviceActivity[entry.ServiceName] = &ServiceHealthSummary{
				ServiceName:    entry.ServiceName,
				Status:         status,
				EventCount:     1,
				ErrorRate:      errorRate,
				LastAuditEvent: entry.Timestamp,
			}
		}
	}
	
	// Calculate compliance score
	complianceScore := logger.calculateComplianceScore(periodEntries)
	
	// Convert maps to slices for JSON
	topUsers := make([]UserActivitySummary, 0)
	for _, summary := range userActivity {
		topUsers = append(topUsers, *summary)
	}
	
	// Sort by event count (descending)
	sort.Slice(topUsers, func(i, j int) bool {
		return topUsers[i].EventCount > topUsers[j].EventCount
	})
	
	// Keep top 10 users
	if len(topUsers) > 10 {
		topUsers = topUsers[:10]
	}
	
	serviceHealth := make([]ServiceHealthSummary, 0)
	for _, summary := range serviceActivity {
		serviceHealth = append(serviceHealth, *summary)
	}
	
	// Generate recommendations
	recommendations := logger.generateRecommendations(periodEntries, complianceScore)
	
	report := &AuditAggregationReport{
		ReportID:         reportID,
		GeneratedAt:      now,
		ReportPeriod:     fmt.Sprintf("%s_%s_to_%s", reportType, periodStart.Format("2006-01-02T15:04"), now.Format("2006-01-02T15:04")),
		TotalEvents:      len(periodEntries),
		EventsByType:     eventsByType,
		EventsByService:  eventsByService,
		EventsByLevel:    eventsByLevel,
		PHIAccessEvents:  phiAccessEvents,
		SecurityEvents:   securityEvents,
		ComplianceScore:  complianceScore,
		TopUsers:         topUsers,
		ServiceHealth:    serviceHealth,
		Recommendations:  recommendations,
	}
	
	return report
}

// calculateUserRiskScore calculates risk score for a user based on their activity
func (logger *ComprehensiveAuditLogger) calculateUserRiskScore(userID string, entries []AuditLogEntry) int {
	riskScore := 0
	userEntries := 0
	phiAccesses := 0
	failedActions := 0
	
	for _, entry := range entries {
		if entry.UserID == userID {
			userEntries++
			if entry.PHIAccessed {
				phiAccesses++
			}
			if !entry.Event.Success {
				failedActions++
			}
			if entry.LogLevel == AUDIT_CRITICAL || entry.LogLevel == AUDIT_ERROR {
				riskScore += 20
			}
		}
	}
	
	// Calculate risk based on activity patterns
	if userEntries > 50 {
		riskScore += 10 // High activity
	}
	if phiAccesses > userEntries/3 {
		riskScore += 15 // High PHI access rate
	}
	if failedActions > userEntries/10 {
		riskScore += 20 // High failure rate
	}
	
	if riskScore > 100 {
		riskScore = 100
	}
	
	return riskScore
}

// calculateComplianceScore calculates overall compliance score
func (logger *ComprehensiveAuditLogger) calculateComplianceScore(entries []AuditLogEntry) float64 {
	if len(entries) == 0 {
		return 100.0
	}
	
	violations := 0
	criticalEvents := 0
	phiUnauthorizedAccess := 0
	
	for _, entry := range entries {
		if entry.EventType == EVENT_COMPLIANCE_VIOLATION {
			violations++
		}
		if entry.LogLevel == AUDIT_CRITICAL {
			criticalEvents++
		}
		if entry.PHIAccessed && !entry.Event.Success {
			phiUnauthorizedAccess++
		}
	}
	
	// Calculate score (100 - penalties)
	score := 100.0
	score -= float64(violations) / float64(len(entries)) * 50.0           // Violations penalty
	score -= float64(criticalEvents) / float64(len(entries)) * 30.0      // Critical events penalty
	score -= float64(phiUnauthorizedAccess) / float64(len(entries)) * 40.0 // PHI unauthorized access penalty
	
	if score < 0 {
		score = 0
	}
	
	return score
}

// generateRecommendations generates compliance recommendations
func (logger *ComprehensiveAuditLogger) generateRecommendations(entries []AuditLogEntry, complianceScore float64) []string {
	var recommendations []string
	
	if complianceScore < 80 {
		recommendations = append(recommendations, "Immediate compliance review required - score below acceptable threshold")
	}
	
	if complianceScore < 90 {
		recommendations = append(recommendations, "Implement additional audit monitoring and alerting")
	}
	
	// Analyze specific patterns
	phiAccessRate := 0
	failureRate := 0
	for _, entry := range entries {
		if entry.PHIAccessed {
			phiAccessRate++
		}
		if !entry.Event.Success {
			failureRate++
		}
	}
	
	if len(entries) > 0 {
		phiAccessPercent := float64(phiAccessRate) / float64(len(entries)) * 100
		failurePercent := float64(failureRate) / float64(len(entries)) * 100
		
		if phiAccessPercent > 30 {
			recommendations = append(recommendations, "High PHI access rate detected - review access controls and user permissions")
		}
		
		if failurePercent > 10 {
			recommendations = append(recommendations, "High failure rate detected - investigate system issues and user training needs")
		}
	}
	
	return recommendations
}

// periodicRetentionCleanup performs periodic cleanup based on retention policies
func (logger *ComprehensiveAuditLogger) periodicRetentionCleanup() {
	ticker := time.NewTicker(24 * time.Hour) // Daily cleanup
	defer ticker.Stop()
	
	for range ticker.C {
		logger.performRetentionCleanup()
	}
}

// performRetentionCleanup removes entries based on retention policies
func (logger *ComprehensiveAuditLogger) performRetentionCleanup() {
	logger.mutex.Lock()
	defer logger.mutex.Unlock()
	
	now := time.Now().UTC()
	cleanedCount := 0
	archivedCount := 0
	
	filteredEntries := make([]AuditLogEntry, 0)
	
	for _, entry := range logger.AuditEntries {
		shouldArchive := false
		shouldDelete := false
		
		switch entry.RetentionPolicy {
		case "hipaa_phi_7_years":
			if now.Sub(entry.Timestamp) > (7 * 365 * 24 * time.Hour) {
				shouldDelete = true
			} else if now.Sub(entry.Timestamp) > (1 * 365 * 24 * time.Hour) {
				shouldArchive = true
			}
		case "standard_1_year":
			if now.Sub(entry.Timestamp) > (1 * 365 * 24 * time.Hour) {
				shouldDelete = true
			} else if now.Sub(entry.Timestamp) > (90 * 24 * time.Hour) {
				shouldArchive = true
			}
		default:
			// Default to standard 1 year retention
			if now.Sub(entry.Timestamp) > (1 * 365 * 24 * time.Hour) {
				shouldDelete = true
			}
		}
		
		if shouldDelete {
			cleanedCount++
		} else {
			if shouldArchive && entry.ArchivedAt == nil {
				archivedAt := now
				entry.ArchivedAt = &archivedAt
				archivedCount++
			}
			filteredEntries = append(filteredEntries, entry)
		}
	}
	
	logger.AuditEntries = filteredEntries
	
	if cleanedCount > 0 || archivedCount > 0 {
		log.Printf("🧹 Retention Cleanup: Deleted %d entries, Archived %d entries", cleanedCount, archivedCount)
	}
}

// REST API Handlers

// handleLogAuditEntry handles incoming audit log entries
func (logger *ComprehensiveAuditLogger) handleLogAuditEntry(c *gin.Context) {
	var entry AuditLogEntry
	
	if err := c.ShouldBindJSON(&entry); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	logger.LogAuditEntry(entry)
	
	c.JSON(http.StatusCreated, gin.H{
		"message":  "Audit entry logged successfully",
		"audit_id": entry.AuditID,
	})
}

// handleGetAuditEntries retrieves audit entries with filtering
func (logger *ComprehensiveAuditLogger) handleGetAuditEntries(c *gin.Context) {
	// Parse query parameters
	limit := 100
	if l := c.Query("limit"); l != "" {
		fmt.Sscanf(l, "%d", &limit)
		if limit > 1000 {
			limit = 1000
		}
	}
	
	serviceName := c.Query("service")
	eventType := c.Query("event_type")
	userID := c.Query("user_id")
	logLevel := c.Query("level")
	phiOnly := c.Query("phi_only") == "true"
	
	logger.mutex.RLock()
	defer logger.mutex.RUnlock()
	
	// Filter and paginate entries
	var filteredEntries []AuditLogEntry
	entryCount := 0
	
	// Start from most recent entries
	for i := len(logger.AuditEntries) - 1; i >= 0 && entryCount < limit; i-- {
		entry := logger.AuditEntries[i]
		
		// Apply filters
		if serviceName != "" && entry.ServiceName != serviceName {
			continue
		}
		if eventType != "" && string(entry.EventType) != eventType {
			continue
		}
		if userID != "" && entry.UserID != userID {
			continue
		}
		if logLevel != "" && string(entry.LogLevel) != logLevel {
			continue
		}
		if phiOnly && !entry.PHIAccessed {
			continue
		}
		
		filteredEntries = append(filteredEntries, entry)
		entryCount++
	}
	
	c.JSON(http.StatusOK, gin.H{
		"entries":  filteredEntries,
		"total":    len(logger.AuditEntries),
		"filtered": len(filteredEntries),
		"limit":    limit,
	})
}

// handleRegisterService handles service registration
func (logger *ComprehensiveAuditLogger) handleRegisterService(c *gin.Context) {
	var registration ServiceRegistration
	
	if err := c.ShouldBindJSON(&registration); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	logger.RegisterService(registration)
	
	c.JSON(http.StatusCreated, gin.H{
		"message":      "Service registered successfully",
		"service_name": registration.ServiceName,
	})
}

// handleGetServices retrieves registered services
func (logger *ComprehensiveAuditLogger) handleGetServices(c *gin.Context) {
	logger.mutex.RLock()
	defer logger.mutex.RUnlock()
	
	services := make([]ServiceRegistration, 0, len(logger.ServiceRegistry))
	for _, service := range logger.ServiceRegistry {
		services = append(services, service)
	}
	
	c.JSON(http.StatusOK, gin.H{
		"services": services,
		"total":    len(services),
	})
}

// handleGetAggregationReport generates and returns aggregation report
func (logger *ComprehensiveAuditLogger) handleGetAggregationReport(c *gin.Context) {
	reportType := c.Query("type")
	if reportType == "" {
		reportType = "hourly"
	}
	
	report := logger.generateAggregationReport(reportType)
	c.JSON(http.StatusOK, report)
}

// handleGetRecentReports retrieves recent aggregation reports
func (logger *ComprehensiveAuditLogger) handleGetRecentReports(c *gin.Context) {
	limit := 10
	if l := c.Query("limit"); l != "" {
		fmt.Sscanf(l, "%d", &limit)
		if limit > 50 {
			limit = 50
		}
	}
	
	logger.mutex.RLock()
	defer logger.mutex.RUnlock()
	
	reports := logger.AggregationReports
	if len(reports) > limit {
		reports = reports[len(reports)-limit:]
	}
	
	c.JSON(http.StatusOK, gin.H{
		"reports": reports,
		"total":   len(logger.AggregationReports),
	})
}

// handleHealthCheck provides health check endpoint
func (logger *ComprehensiveAuditLogger) handleHealthCheck(c *gin.Context) {
	logger.mutex.RLock()
	totalEntries := len(logger.AuditEntries)
	totalServices := len(logger.ServiceRegistry)
	totalReports := len(logger.AggregationReports)
	logger.mutex.RUnlock()
	
	status := "healthy"
	if totalEntries > int(float64(logger.MaxEntries)*0.9) {
		status = "warning_high_entries"
	}
	
	// Count active services
	activeServices := 0
	logger.mutex.RLock()
	for _, service := range logger.ServiceRegistry {
		if service.Status == "active" {
			activeServices++
		}
	}
	logger.mutex.RUnlock()
	
	c.JSON(http.StatusOK, gin.H{
		"status":              status,
		"service":             "audit-logging-service",
		"version":             "1.0.0",
		"total_entries":       totalEntries,
		"max_entries":         logger.MaxEntries,
		"retention_days":      logger.RetentionDays,
		"registered_services": totalServices,
		"active_services":     activeServices,
		"aggregation_reports": totalReports,
		"timestamp":           time.Now().UTC(),
	})
}

// setupRouter sets up the Gin router with all endpoints
func (logger *ComprehensiveAuditLogger) setupRouter() *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	
	router := gin.New()
	router.Use(gin.Logger(), gin.Recovery())
	
	// CORS middleware
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		
		c.Next()
	})
	
	// API routes
	v1 := router.Group("/api/v1")
	{
		// Audit logging endpoints
		v1.POST("/audit-entries", logger.handleLogAuditEntry)
		v1.GET("/audit-entries", logger.handleGetAuditEntries)
		
		// Service registration endpoints
		v1.POST("/services/register", logger.handleRegisterService)
		v1.GET("/services", logger.handleGetServices)
		
		// Reporting endpoints
		v1.GET("/reports/aggregation", logger.handleGetAggregationReport)
		v1.GET("/reports/recent", logger.handleGetRecentReports)
		
		// Health and monitoring
		v1.GET("/health", logger.handleHealthCheck)
	}
	
	// Root level health endpoint for consistency with other services
	router.GET("/health", logger.handleHealthCheck)
	
	return router
}

// main function
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
	
	// Initialize comprehensive audit logger
	auditLogger := NewComprehensiveAuditLogger()
	
	// Services can register themselves dynamically via the /api/v1/register endpoint
	// Skipping auto-registration to avoid port conflicts and missing service issues
	
	// Setup router
	router := auditLogger.setupRouter()
	
	// Get port from environment
	port := os.Getenv("PORT")
	if port == "" {
		port = "8084" // Audit logging service port
	}
	
	log.Printf("🗂️ Comprehensive Audit Logging Service starting on port %s", port)
	log.Printf("📊 Configuration: %d max entries, %d days retention", auditLogger.MaxEntries, auditLogger.RetentionDays)
	log.Println("🎯 HIPAA-compliant centralized audit logging ready")
	
	// Start server
	if err := router.Run(":" + port); err != nil {
		log.Fatal("Failed to start audit logging service:", err)
	}
}