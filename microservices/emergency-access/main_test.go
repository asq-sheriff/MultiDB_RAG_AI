package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestMain(m *testing.M) {
	gin.SetMode(gin.TestMode)
	m.Run()
}

func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	
	// Initialize monitor (matching the actual service structure)
	monitor := NewEmergencyAccessMonitor()
	
	// Setup basic routes (simplified version of main.go routes)
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":    "healthy",
			"service":   "emergency-access-service",
			"version":   "1.0.0",
			"timestamp": time.Now().UTC(),
		})
	})
	
	router.POST("/emergency/request", func(c *gin.Context) {
		var req EmergencyAccessRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		
		response := monitor.RequestEmergencyAccess(&req)
		if response.AccessGranted {
			c.JSON(http.StatusCreated, gin.H{
				"success":    true,
				"request_id": response.RequestID,
				"message":    "Emergency access granted",
			})
		} else {
			c.JSON(http.StatusForbidden, gin.H{
				"success":    false,
				"request_id": response.RequestID,
				"message":    "Emergency access denied",
				"compliance_status": response.ComplianceStatus,
			})
		}
	})
	
	return router
}

func TestHealthCheck(t *testing.T) {
	router := setupTestRouter()
	
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, "emergency-access-service", response["service"])
	assert.Equal(t, "healthy", response["status"])
}

func TestRequestEmergencyAccess(t *testing.T) {
	router := setupTestRouter()
	
	requestBody := EmergencyAccessRequest{
		UserID:           "test-user-123",
		AccessType:       ACCESS_MEDICAL_EMERGENCY,
		EmergencyLevel:   EMERGENCY_HIGH,
		Justification:    "Patient experiencing severe symptoms, need immediate access to medical records",
		ResourceAccessed: "patient_medical_records",
		RequestedBy:      "Dr. Smith",
	}
	
	jsonBody, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/emergency/request", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.True(t, response["success"].(bool))
	assert.NotEmpty(t, response["request_id"])
}

func TestEmergencyAccessLevels(t *testing.T) {
	levels := []EmergencyAccessLevel{
		EMERGENCY_LOW,
		EMERGENCY_MODERATE,
		EMERGENCY_HIGH,
		EMERGENCY_CRITICAL,
	}
	
	for _, level := range levels {
		assert.NotEmpty(t, string(level))
	}
}

func TestEmergencyAccessTypes(t *testing.T) {
	types := []EmergencyAccessType{
		ACCESS_CRISIS_INTERVENTION,
		ACCESS_MEDICAL_EMERGENCY,
		ACCESS_SAFETY_OVERRIDE,
		ACCESS_THERAPEUTIC_URGENT,
		ACCESS_SYSTEM_MAINTENANCE,
		ACCESS_COMPLIANCE_AUDIT,
	}
	
	for _, accessType := range types {
		assert.NotEmpty(t, string(accessType))
	}
}