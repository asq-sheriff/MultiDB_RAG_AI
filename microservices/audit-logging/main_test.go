// Package main provides comprehensive tests for the HIPAA-compliant Audit Logging service
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Test Configuration
const (
	testMaxEntries = 1000
	testRetentionDays = 30 // Shorter for testing
)

// Test setup helpers

func setupTestAuditLogger() *ComprehensiveAuditLogger {
	gin.SetMode(gin.TestMode)
	
	logger := &ComprehensiveAuditLogger{
		AuditEntries:       make([]AuditLogEntry, 0),
		ServiceRegistry:    make(map[string]ServiceRegistration),
		MaxEntries:         testMaxEntries,
		RetentionDays:      testRetentionDays,
		AggregationReports: make([]AuditAggregationReport, 0),
	}
	
	// Don't start background processes for testing
	
	return logger
}

func createTestAuditEntry(eventType AuditEventType, level AuditLogLevel, phiAccessed bool) AuditLogEntry {
	return AuditLogEntry{
		AuditID:     uuid.New().String(),
		Timestamp:   time.Now().UTC(),
		EventType:   eventType,
		LogLevel:    level,
		ServiceName: "test-service",
		ServiceHost: "localhost",
		UserID:      "test-user-123",
		SessionID:   "test-session-456",
		PatientID:   "test-patient-789",
		RequestID:   "test-request-abc",
		Event: AuditEvent{
			Action:      "test_action",
			Resource:    "test_resource",
			Description: "Test audit entry for testing purposes",
			Success:     true,
			Context: map[string]interface{}{
				"test_param": "test_value",
			},
		},
		ClientIP:          "192.168.1.100",
		UserAgent:         "TestAgent/1.0",
		RequestPath:       "/api/v1/test",
		HTTPMethod:        "POST",
		StatusCode:        200,
		PHIAccessed:       phiAccessed,
		DataSensitivity:   "high",
		ComplianceContext: "testing",
		Tags:              []string{"test", "hipaa"},
		Metadata: map[string]interface{}{
			"test_meta": "test_meta_value",
		},
		RetentionPolicy: "hipaa_phi_7_years",
	}
}

func createTestServiceRegistration(name string) ServiceRegistration {
	return ServiceRegistration{
		ServiceName:   name,
		ServiceURL:    fmt.Sprintf("http://localhost:808%d", len(name)%10),
		HealthCheck:   "/api/v1/health",
		AuditEndpoint: "/api/v1/audit-entries",
		LastSeen:      time.Now().UTC(),
		Status:        "active",
		Version:       "1.0.0",
	}
}

// Core Audit Logging Tests

func TestNewComprehensiveAuditLogger(t *testing.T) {
	logger := setupTestAuditLogger()

	assert.NotNil(t, logger)
	assert.Equal(t, testMaxEntries, logger.MaxEntries)
	assert.Equal(t, testRetentionDays, logger.RetentionDays)
	assert.NotNil(t, logger.AuditEntries)
	assert.NotNil(t, logger.ServiceRegistry)
	assert.NotNil(t, logger.AggregationReports)
}

func TestLogAuditEntry(t *testing.T) {
	logger := setupTestAuditLogger()

	t.Run("BasicAuditEntryLogging", func(t *testing.T) {
		entry := createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true)
		originalID := entry.AuditID
		originalTimestamp := entry.Timestamp

		logger.LogAuditEntry(entry)

		assert.Equal(t, 1, len(logger.AuditEntries))
		loggedEntry := logger.AuditEntries[0]
		assert.Equal(t, originalID, loggedEntry.AuditID)
		assert.Equal(t, originalTimestamp.Unix(), loggedEntry.Timestamp.Unix())
		assert.Equal(t, EVENT_PHI_ACCESS, loggedEntry.EventType)
		assert.True(t, loggedEntry.PHIAccessed)
	})

	t.Run("AutoGenerateAuditID", func(t *testing.T) {
		entry := createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false)
		entry.AuditID = "" // Clear ID to test auto-generation

		logger.LogAuditEntry(entry)

		assert.Equal(t, 2, len(logger.AuditEntries))
		loggedEntry := logger.AuditEntries[1]
		assert.NotEmpty(t, loggedEntry.AuditID)
		assert.Len(t, loggedEntry.AuditID, 36) // UUID format
	})

	t.Run("AutoGenerateTimestamp", func(t *testing.T) {
		entry := createTestAuditEntry(EVENT_USER_LOGOUT, AUDIT_INFO, false)
		entry.Timestamp = time.Time{} // Clear timestamp

		beforeLog := time.Now().UTC()
		logger.LogAuditEntry(entry)
		afterLog := time.Now().UTC()

		assert.Equal(t, 3, len(logger.AuditEntries))
		loggedEntry := logger.AuditEntries[2]
		assert.True(t, loggedEntry.Timestamp.After(beforeLog) || loggedEntry.Timestamp.Equal(beforeLog))
		assert.True(t, loggedEntry.Timestamp.Before(afterLog) || loggedEntry.Timestamp.Equal(afterLog))
	})

	t.Run("RetentionPolicyAssignment", func(t *testing.T) {
		// Test PHI access entry
		phiEntry := createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true)
		phiEntry.RetentionPolicy = ""
		logger.LogAuditEntry(phiEntry)

		// Test non-PHI entry
		nonPhiEntry := createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false)
		nonPhiEntry.RetentionPolicy = ""
		logger.LogAuditEntry(nonPhiEntry)

		assert.Equal(t, 5, len(logger.AuditEntries))
		assert.Equal(t, "hipaa_phi_7_years", logger.AuditEntries[3].RetentionPolicy)
		assert.Equal(t, "standard_1_year", logger.AuditEntries[4].RetentionPolicy)
	})

	t.Run("MaxEntriesLimit", func(t *testing.T) {
		// Create a fresh logger with small limit for testing
		smallLogger := &ComprehensiveAuditLogger{
			AuditEntries:       make([]AuditLogEntry, 0),
			ServiceRegistry:    make(map[string]ServiceRegistration),
			MaxEntries:         10,
			RetentionDays:      testRetentionDays,
			AggregationReports: make([]AuditAggregationReport, 0),
		}

		// Add more entries than the limit
		for i := 0; i < 15; i++ {
			entry := createTestAuditEntry(EVENT_API_ACCESS, AUDIT_INFO, false)
			entry.Event.Description = fmt.Sprintf("Test entry %d", i)
			smallLogger.LogAuditEntry(entry)
		}

		// Should keep only 90% of max entries (9 entries)
		assert.Equal(t, 9, len(smallLogger.AuditEntries))
		// Should keep the most recent entries
		assert.Contains(t, smallLogger.AuditEntries[0].Event.Description, "Test entry")
	})
}

func TestServiceRegistration(t *testing.T) {
	logger := setupTestAuditLogger()

	t.Run("RegisterService", func(t *testing.T) {
		service := createTestServiceRegistration("test-service")
		originalLastSeen := service.LastSeen

		logger.RegisterService(service)

		assert.Equal(t, 1, len(logger.ServiceRegistry))
		registeredService := logger.ServiceRegistry["test-service"]
		assert.Equal(t, "test-service", registeredService.ServiceName)
		assert.Equal(t, "active", registeredService.Status)
		// LastSeen should be updated during registration
		assert.True(t, registeredService.LastSeen.After(originalLastSeen) || registeredService.LastSeen.Equal(originalLastSeen))
		
		// Should create audit entry for registration
		assert.Greater(t, len(logger.AuditEntries), 0)
		registrationEntry := logger.AuditEntries[0]
		assert.Equal(t, EVENT_SERVICE_START, registrationEntry.EventType)
		assert.Contains(t, registrationEntry.Event.Description, "test-service registered")
	})

	t.Run("UpdateExistingService", func(t *testing.T) {
		// Register initial service
		service := createTestServiceRegistration("update-service")
		logger.RegisterService(service)
		initialEntryCount := len(logger.AuditEntries)

		// Update the same service
		service.Version = "2.0.0"
		logger.RegisterService(service)

		assert.Equal(t, 2, len(logger.ServiceRegistry))
		updatedService := logger.ServiceRegistry["update-service"]
		assert.Equal(t, "2.0.0", updatedService.Version)
		
		// Should create another audit entry for the update
		assert.Equal(t, initialEntryCount+1, len(logger.AuditEntries))
	})
}

func TestAggregationReporting(t *testing.T) {
	logger := setupTestAuditLogger()

	// Add sample audit entries for testing
	entries := []AuditLogEntry{
		createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true),
		createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false),
		createTestAuditEntry(EVENT_EMERGENCY_ACCESS, AUDIT_WARNING, true),
		createTestAuditEntry(EVENT_COMPLIANCE_VIOLATION, AUDIT_CRITICAL, true),
		createTestAuditEntry(EVENT_SECURITY_INCIDENT, AUDIT_ERROR, false),
	}

	for _, entry := range entries {
		logger.LogAuditEntry(entry)
	}

	t.Run("GenerateHourlyReport", func(t *testing.T) {
		report := logger.generateAggregationReport("hourly")

		assert.NotNil(t, report)
		assert.NotEmpty(t, report.ReportID)
		assert.Equal(t, 5, report.TotalEvents)
		assert.Equal(t, 3, report.PHIAccessEvents) // 3 entries with PHI access
		assert.Equal(t, 2, report.SecurityEvents)  // compliance_violation + security_incident
		assert.Contains(t, report.ReportPeriod, "hourly")

		// Check event type aggregation
		assert.Equal(t, 1, report.EventsByType[EVENT_PHI_ACCESS])
		assert.Equal(t, 1, report.EventsByType[EVENT_USER_LOGIN])
		assert.Equal(t, 1, report.EventsByType[EVENT_EMERGENCY_ACCESS])

		// Check log level aggregation
		assert.Equal(t, 2, report.EventsByLevel[AUDIT_INFO])
		assert.Equal(t, 1, report.EventsByLevel[AUDIT_WARNING])
		assert.Equal(t, 1, report.EventsByLevel[AUDIT_CRITICAL])
		assert.Equal(t, 1, report.EventsByLevel[AUDIT_ERROR])
	})

	t.Run("GenerateDailyReport", func(t *testing.T) {
		report := logger.generateAggregationReport("daily")

		assert.NotNil(t, report)
		assert.Contains(t, report.ReportPeriod, "daily")
		assert.Equal(t, 5, report.TotalEvents)
	})

	t.Run("ComplianceScoreCalculation", func(t *testing.T) {
		report := logger.generateAggregationReport("hourly")

		// With 1 compliance violation and 1 critical event, score should be reduced
		assert.Less(t, report.ComplianceScore, 100.0)
		assert.GreaterOrEqual(t, report.ComplianceScore, 0.0)
	})

	t.Run("UserActivitySummary", func(t *testing.T) {
		report := logger.generateAggregationReport("hourly")

		assert.Greater(t, len(report.TopUsers), 0)
		userSummary := report.TopUsers[0]
		assert.Equal(t, "test-user-123", userSummary.UserID)
		assert.Equal(t, 5, userSummary.EventCount)
		assert.Equal(t, 3, userSummary.PHIAccesses)
		assert.Greater(t, userSummary.RiskScore, 0)
	})

	t.Run("ServiceHealthSummary", func(t *testing.T) {
		report := logger.generateAggregationReport("hourly")

		assert.Greater(t, len(report.ServiceHealth), 0)
		serviceSummary := report.ServiceHealth[0]
		assert.Equal(t, "test-service", serviceSummary.ServiceName)
		assert.Equal(t, 5, serviceSummary.EventCount)
		assert.GreaterOrEqual(t, serviceSummary.ErrorRate, 0.0)
	})

	t.Run("Recommendations", func(t *testing.T) {
		report := logger.generateAggregationReport("hourly")

		assert.NotNil(t, report.Recommendations)
		// With compliance violations, should have recommendations
		if report.ComplianceScore < 80 {
			assert.Contains(t, report.Recommendations[0], "compliance review required")
		}
	})
}

func TestRetentionPolicyAndCleanup(t *testing.T) {
	logger := setupTestAuditLogger()

	t.Run("RetentionPolicyAssignment", func(t *testing.T) {
		// Test different scenarios for retention policy assignment
		testCases := []struct {
			name            string
			phiAccessed     bool
			expectedPolicy  string
		}{
			{"PHI Access", true, "hipaa_phi_7_years"},
			{"Non-PHI Access", false, "standard_1_year"},
		}

		for _, tc := range testCases {
			t.Run(tc.name, func(t *testing.T) {
				entry := createTestAuditEntry(EVENT_API_ACCESS, AUDIT_INFO, tc.phiAccessed)
				entry.RetentionPolicy = "" // Clear to test auto-assignment
				
				logger.LogAuditEntry(entry)
				
				lastEntry := logger.AuditEntries[len(logger.AuditEntries)-1]
				assert.Equal(t, tc.expectedPolicy, lastEntry.RetentionPolicy)
			})
		}
	})

	t.Run("RetentionCleanup", func(t *testing.T) {
		// Create entries with different ages
		oldEntry := createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true)
		oldEntry.Timestamp = time.Now().UTC().Add(-2 * 365 * 24 * time.Hour) // 2 years old
		oldEntry.RetentionPolicy = "standard_1_year"
		
		recentEntry := createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false)
		recentEntry.Timestamp = time.Now().UTC().Add(-1 * time.Hour) // 1 hour old
		recentEntry.RetentionPolicy = "standard_1_year"

		logger.LogAuditEntry(oldEntry)
		logger.LogAuditEntry(recentEntry)
		
		initialCount := len(logger.AuditEntries)
		logger.performRetentionCleanup()
		
		// Old entry should be removed, recent entry should remain
		assert.Less(t, len(logger.AuditEntries), initialCount)
		
		// Check that remaining entries are recent
		for _, entry := range logger.AuditEntries {
			timeDiff := time.Now().UTC().Sub(entry.Timestamp)
			assert.Less(t, timeDiff, 365*24*time.Hour) // Less than 1 year old
		}
	})
}

func TestUserRiskScoreCalculation(t *testing.T) {
	logger := setupTestAuditLogger()

	// Create entries with different risk profiles
	entries := []AuditLogEntry{
		// High activity user
		createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true),
		createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true),
		createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_ERROR, false), // Failed action
		createTestAuditEntry(EVENT_COMPLIANCE_VIOLATION, AUDIT_CRITICAL, true), // Critical event
	}

	// Modify entries to have same user ID
	userID := "high-risk-user"
	for i := range entries {
		entries[i].UserID = userID
	}

	t.Run("CalculateUserRiskScore", func(t *testing.T) {
		riskScore := logger.calculateUserRiskScore(userID, entries)

		assert.Greater(t, riskScore, 0)
		assert.LessOrEqual(t, riskScore, 100)
		
		// User with critical events and PHI access should have higher risk
		assert.Greater(t, riskScore, 30) // Threshold for high-risk behavior
	})

	t.Run("LowRiskUser", func(t *testing.T) {
		lowRiskEntries := []AuditLogEntry{
			createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false),
		}
		lowRiskEntries[0].UserID = "low-risk-user"

		riskScore := logger.calculateUserRiskScore("low-risk-user", lowRiskEntries)
		assert.LessOrEqual(t, riskScore, 20) // Should be relatively low risk
	})
}

func TestComplianceScoreCalculation(t *testing.T) {
	logger := setupTestAuditLogger()

	t.Run("PerfectCompliance", func(t *testing.T) {
		perfectEntries := []AuditLogEntry{
			createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false),
			createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true),
		}
		
		for i := range perfectEntries {
			perfectEntries[i].Event.Success = true
		}

		score := logger.calculateComplianceScore(perfectEntries)
		assert.Equal(t, 100.0, score)
	})

	t.Run("ComplianceViolations", func(t *testing.T) {
		violationEntries := []AuditLogEntry{
			createTestAuditEntry(EVENT_COMPLIANCE_VIOLATION, AUDIT_CRITICAL, true),
			createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_ERROR, true), // Failed PHI access
			createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false),
		}
		
		violationEntries[1].Event.Success = false // Failed PHI access

		score := logger.calculateComplianceScore(violationEntries)
		assert.Less(t, score, 100.0)
		assert.GreaterOrEqual(t, score, 0.0)
	})

	t.Run("EmptyEntries", func(t *testing.T) {
		score := logger.calculateComplianceScore([]AuditLogEntry{})
		assert.Equal(t, 100.0, score)
	})
}

// HTTP API Tests

func TestAuditLoggingAPI(t *testing.T) {
	logger := setupTestAuditLogger()
	router := logger.setupRouter()

	t.Run("LogAuditEntryEndpoint", func(t *testing.T) {
		entry := createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true)
		jsonData, _ := json.Marshal(entry)

		req, _ := http.NewRequest("POST", "/api/v1/audit-entries", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusCreated, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		assert.Equal(t, "Audit entry logged successfully", response["message"])
		assert.NotEmpty(t, response["audit_id"])
		assert.Equal(t, 1, len(logger.AuditEntries))
	})

	t.Run("GetAuditEntriesEndpoint", func(t *testing.T) {
		// Add some test entries
		for i := 0; i < 5; i++ {
			entry := createTestAuditEntry(EVENT_API_ACCESS, AUDIT_INFO, false)
			logger.LogAuditEntry(entry)
		}

		req, _ := http.NewRequest("GET", "/api/v1/audit-entries", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		assert.Equal(t, float64(6), response["total"]) // 5 + 1 from previous test
		entries := response["entries"].([]interface{})
		assert.Greater(t, len(entries), 0)
	})

	t.Run("GetAuditEntriesWithFiltering", func(t *testing.T) {
		// Add PHI access entry
		phiEntry := createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_WARNING, true)
		logger.LogAuditEntry(phiEntry)

		// Test PHI-only filtering
		req, _ := http.NewRequest("GET", "/api/v1/audit-entries?phi_only=true", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		entries := response["entries"].([]interface{})
		assert.Greater(t, len(entries), 0)
		
		// All returned entries should have PHI access
		for _, entryInterface := range entries {
			entryMap := entryInterface.(map[string]interface{})
			assert.True(t, entryMap["phi_accessed"].(bool))
		}
	})
}

func TestServiceRegistrationAPI(t *testing.T) {
	logger := setupTestAuditLogger()
	router := logger.setupRouter()

	t.Run("RegisterServiceEndpoint", func(t *testing.T) {
		service := createTestServiceRegistration("api-test-service")
		jsonData, _ := json.Marshal(service)

		req, _ := http.NewRequest("POST", "/api/v1/services/register", bytes.NewBuffer(jsonData))
		req.Header.Set("Content-Type", "application/json")
		
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusCreated, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		assert.Equal(t, "Service registered successfully", response["message"])
		assert.Equal(t, "api-test-service", response["service_name"])
		assert.Equal(t, 1, len(logger.ServiceRegistry))
	})

	t.Run("GetServicesEndpoint", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/services", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		assert.Equal(t, float64(1), response["total"])
		services := response["services"].([]interface{})
		assert.Equal(t, 1, len(services))
		
		service := services[0].(map[string]interface{})
		assert.Equal(t, "api-test-service", service["service_name"])
	})
}

func TestReportingAPI(t *testing.T) {
	logger := setupTestAuditLogger()
	router := logger.setupRouter()

	// Add some test data for reporting
	entries := []AuditLogEntry{
		createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true),
		createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false),
		createTestAuditEntry(EVENT_EMERGENCY_ACCESS, AUDIT_WARNING, true),
	}
	
	for _, entry := range entries {
		logger.LogAuditEntry(entry)
	}

	t.Run("GetAggregationReportEndpoint", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/reports/aggregation?type=hourly", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var report AuditAggregationReport
		err := json.Unmarshal(w.Body.Bytes(), &report)
		require.NoError(t, err)
		
		assert.NotEmpty(t, report.ReportID)
		assert.Equal(t, 3, report.TotalEvents)
		assert.Equal(t, 2, report.PHIAccessEvents)
		assert.Contains(t, report.ReportPeriod, "hourly")
	})

	t.Run("GetRecentReportsEndpoint", func(t *testing.T) {
		// Add a report to the logger
		report := logger.generateAggregationReport("hourly")
		logger.AggregationReports = append(logger.AggregationReports, *report)

		req, _ := http.NewRequest("GET", "/api/v1/reports/recent?limit=5", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		assert.Equal(t, float64(1), response["total"])
		reports := response["reports"].([]interface{})
		assert.Equal(t, 1, len(reports))
	})
}

func TestHealthCheckAPI(t *testing.T) {
	logger := setupTestAuditLogger()
	router := logger.setupRouter()

	t.Run("HealthCheckEndpoint", func(t *testing.T) {
		req, _ := http.NewRequest("GET", "/api/v1/health", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		assert.Equal(t, "audit-logging-service", response["service"])
		assert.Equal(t, "1.0.0", response["version"])
		assert.Equal(t, "healthy", response["status"])
		assert.Equal(t, float64(testMaxEntries), response["max_entries"])
		assert.Equal(t, float64(testRetentionDays), response["retention_days"])
		assert.NotNil(t, response["timestamp"])
	})

	t.Run("HealthCheckWithHighEntries", func(t *testing.T) {
		// Fill logger with many entries to trigger warning
		for i := 0; i < int(float64(logger.MaxEntries)*0.95); i++ {
			entry := createTestAuditEntry(EVENT_API_ACCESS, AUDIT_INFO, false)
			logger.LogAuditEntry(entry)
		}

		req, _ := http.NewRequest("GET", "/api/v1/health", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
		
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		
		assert.Equal(t, "warning_high_entries", response["status"])
	})
}

func TestLogLevelDetermination(t *testing.T) {
	logger := setupTestAuditLogger()

	testCases := []struct {
		name           string
		success        bool
		violation      bool
		riskScore      int
		expectedLevel  AuditLogLevel
	}{
		{"ComplianceViolation", true, true, 50, AUDIT_CRITICAL},
		{"FailedAction", false, false, 50, AUDIT_ERROR},
		{"HighRiskSuccess", true, false, 80, AUDIT_WARNING},
		{"NormalSuccess", true, false, 30, AUDIT_INFO},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			level := logger.determineLogLevel(tc.success, tc.violation, tc.riskScore)
			assert.Equal(t, tc.expectedLevel, level)
		})
	}
}

func TestSensitivityDetermination(t *testing.T) {
	logger := setupTestAuditLogger()

	testCases := []struct {
		name         string
		phiAccessed  bool
		riskScore    int
		expected     string
	}{
		{"CriticalPHIHighRisk", true, 80, "critical"},
		{"HighPHILowRisk", true, 30, "high"},
		{"MediumNonPHIHighRisk", false, 60, "medium"},
		{"LowNonPHILowRisk", false, 30, "low"},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			sensitivity := logger.determineSensitivity(tc.phiAccessed, tc.riskScore)
			assert.Equal(t, tc.expected, sensitivity)
		})
	}
}

func TestAuditEntryValidation(t *testing.T) {
	logger := setupTestAuditLogger()

	t.Run("ValidAuditEntry", func(t *testing.T) {
		entry := createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true)
		
		// Valid entry should be logged successfully
		initialCount := len(logger.AuditEntries)
		logger.LogAuditEntry(entry)
		assert.Equal(t, initialCount+1, len(logger.AuditEntries))
	})

	t.Run("EntryWithMinimalData", func(t *testing.T) {
		entry := AuditLogEntry{
			EventType:   EVENT_SYSTEM_CONFIG,
			LogLevel:    AUDIT_INFO,
			ServiceName: "minimal-service",
			Event: AuditEvent{
				Action:      "minimal_action",
				Description: "Minimal test entry",
				Success:     true,
			},
		}

		initialCount := len(logger.AuditEntries)
		logger.LogAuditEntry(entry)
		assert.Equal(t, initialCount+1, len(logger.AuditEntries))
		
		// Check that missing fields are populated
		loggedEntry := logger.AuditEntries[len(logger.AuditEntries)-1]
		assert.NotEmpty(t, loggedEntry.AuditID)
		assert.False(t, loggedEntry.Timestamp.IsZero())
		assert.NotEmpty(t, loggedEntry.RetentionPolicy)
	})
}

// Benchmark Tests

func BenchmarkLogAuditEntry(b *testing.B) {
	logger := setupTestAuditLogger()
	entry := createTestAuditEntry(EVENT_API_ACCESS, AUDIT_INFO, false)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		entry.AuditID = uuid.New().String() // Unique ID for each iteration
		logger.LogAuditEntry(entry)
	}
}

func BenchmarkGenerateAggregationReport(b *testing.B) {
	logger := setupTestAuditLogger()
	
	// Pre-populate with test data
	for i := 0; i < 1000; i++ {
		entry := createTestAuditEntry(EVENT_API_ACCESS, AUDIT_INFO, i%3 == 0)
		logger.LogAuditEntry(entry)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		logger.generateAggregationReport("hourly")
	}
}

func BenchmarkCalculateComplianceScore(b *testing.B) {
	logger := setupTestAuditLogger()
	
	// Create test entries
	entries := make([]AuditLogEntry, 1000)
	for i := 0; i < 1000; i++ {
		entries[i] = createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		logger.calculateComplianceScore(entries)
	}
}

func BenchmarkHealthCheckAPI(b *testing.B) {
	logger := setupTestAuditLogger()
	router := logger.setupRouter()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		req, _ := http.NewRequest("GET", "/api/v1/health", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}

// Integration Tests

func TestHIPAAComplianceIntegration(t *testing.T) {
	logger := setupTestAuditLogger()

	t.Run("PHIAccessAuditTrail", func(t *testing.T) {
		// Simulate PHI access scenario
		phiEntry := AuditLogEntry{
			AuditID:     uuid.New().String(),
			Timestamp:   time.Now().UTC(),
			EventType:   EVENT_PHI_ACCESS,
			LogLevel:    AUDIT_INFO,
			ServiceName: "healthcare-service",
			UserID:      "doctor-123",
			SessionID:   "session-456",
			PatientID:   "patient-789",
			Event: AuditEvent{
				Action:      "view_patient_record",
				Resource:    "patient_record",
				ResourceType: "medical_record",
				Description: "Doctor accessed patient medical record",
				Success:     true,
				Context: map[string]interface{}{
					"patient_id": "patient-789",
					"record_type": "full_medical_history",
					"access_reason": "scheduled_appointment",
				},
			},
			ClientIP:          "10.0.1.100",
			PHIAccessed:       true,
			DataSensitivity:   "critical",
			ComplianceContext: "healthcare_delivery",
			RetentionPolicy:   "hipaa_phi_7_years",
		}

		logger.LogAuditEntry(phiEntry)

		// Verify HIPAA compliance requirements
		assert.Equal(t, 1, len(logger.AuditEntries))
		loggedEntry := logger.AuditEntries[0]
		
		// Must have all required HIPAA fields
		assert.NotEmpty(t, loggedEntry.AuditID)
		assert.False(t, loggedEntry.Timestamp.IsZero())
		assert.NotEmpty(t, loggedEntry.UserID)
		assert.NotEmpty(t, loggedEntry.PatientID)
		assert.True(t, loggedEntry.PHIAccessed)
		assert.Equal(t, "hipaa_phi_7_years", loggedEntry.RetentionPolicy)
		assert.NotEmpty(t, loggedEntry.ClientIP)
		assert.Equal(t, "critical", loggedEntry.DataSensitivity)
	})

	t.Run("EmergencyAccessCompliance", func(t *testing.T) {
		emergencyEntry := createTestAuditEntry(EVENT_EMERGENCY_ACCESS, AUDIT_WARNING, true)
		emergencyEntry.ComplianceContext = "emergency_medical_access"
		emergencyEntry.Tags = []string{"emergency", "break_glass", "life_threatening"}
		emergencyEntry.Event.Context = map[string]interface{}{
			"emergency_level": "critical",
			"justification": "Patient in cardiac arrest, immediate access required",
			"supervisor_notified": true,
		}

		logger.LogAuditEntry(emergencyEntry)

		// Verify emergency access is properly logged
		assert.Equal(t, 2, len(logger.AuditEntries))
		emergencyLoggedEntry := logger.AuditEntries[1]
		assert.Equal(t, EVENT_EMERGENCY_ACCESS, emergencyLoggedEntry.EventType)
		assert.Contains(t, emergencyLoggedEntry.Tags, "emergency")
		assert.True(t, emergencyLoggedEntry.PHIAccessed)
	})

	t.Run("ComplianceViolationTracking", func(t *testing.T) {
		violationEntry := createTestAuditEntry(EVENT_COMPLIANCE_VIOLATION, AUDIT_CRITICAL, true)
		violationEntry.Event.Success = false
		violationEntry.Event.ErrorMessage = "Unauthorized PHI access attempt"
		violationEntry.Event.Context = map[string]interface{}{
			"violation_type": "unauthorized_access",
			"policy_violated": "HIPAA_minimum_necessary",
			"action_taken": "access_denied_user_flagged",
		}

		logger.LogAuditEntry(violationEntry)

		// Generate compliance report
		report := logger.generateAggregationReport("hourly")
		
		// Compliance score should be significantly reduced
		assert.Less(t, report.ComplianceScore, 80.0)
		assert.Equal(t, 1, report.SecurityEvents)
		assert.Greater(t, len(report.Recommendations), 0)
		assert.Contains(t, report.Recommendations[0], "compliance review required")
	})

	t.Run("RetentionPolicyCompliance", func(t *testing.T) {
		// Test 7-year retention for PHI
		phiEntry := createTestAuditEntry(EVENT_PHI_ACCESS, AUDIT_INFO, true)
		phiEntry.Timestamp = time.Now().UTC().Add(-6 * 365 * 24 * time.Hour) // 6 years old
		phiEntry.RetentionPolicy = "hipaa_phi_7_years"
		
		nonPhiEntry := createTestAuditEntry(EVENT_USER_LOGIN, AUDIT_INFO, false)
		nonPhiEntry.Timestamp = time.Now().UTC().Add(-2 * 365 * 24 * time.Hour) // 2 years old
		nonPhiEntry.RetentionPolicy = "standard_1_year"
		
		logger.LogAuditEntry(phiEntry)
		logger.LogAuditEntry(nonPhiEntry)
		
		initialCount := len(logger.AuditEntries)
		logger.performRetentionCleanup()
		
		// PHI entry should remain (within 7-year limit)
		// Non-PHI entry should be removed (beyond 1-year limit)
		assert.Less(t, len(logger.AuditEntries), initialCount)
		
		// Verify remaining entry is PHI entry
		hasPhiEntry := false
		for _, entry := range logger.AuditEntries {
			if entry.EventType == EVENT_PHI_ACCESS && entry.PHIAccessed {
				hasPhiEntry = true
				break
			}
		}
		assert.True(t, hasPhiEntry)
	})
}