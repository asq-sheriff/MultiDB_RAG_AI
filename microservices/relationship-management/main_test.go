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
	
	// Initialize relationship manager (matching the actual service structure)
	manager := NewRelationshipManager()
	
	// Setup basic routes (simplified version of main.go routes)
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":    "healthy",
			"service":   "relationship-management-service",
			"version":   "1.0.0",
			"timestamp": time.Now().UTC(),
		})
	})
	
	router.POST("/relationships", func(c *gin.Context) {
		var req TherapeuticRelationship
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		
		clientIP := c.ClientIP()
		relationship, err := manager.CreateRelationship(&req, clientIP)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		
		c.JSON(http.StatusCreated, relationship)
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
	
	assert.Equal(t, "relationship-management-service", response["service"])
	assert.Equal(t, "healthy", response["status"])
}

func TestCreateRelationship(t *testing.T) {
	router := setupTestRouter()
	
	requestBody := TherapeuticRelationship{
		PatientID:         "patient-123",
		RelatedPersonID:   "therapist-456",
		RelatedPersonName: "Dr. Jane Smith",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		Status:            STATUS_ACTIVE,
		CreatedBy:         "admin-user-001",
	}
	
	jsonBody, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/relationships", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response TherapeuticRelationship
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.NotEmpty(t, response.RelationshipID)
	assert.Equal(t, "patient-123", response.PatientID)
	assert.Equal(t, "therapist-456", response.RelatedPersonID)
}

func TestRelationshipTypes(t *testing.T) {
	types := []RelationshipType{
		RELATIONSHIP_PRIMARY_THERAPIST,
		RELATIONSHIP_SECONDARY_THERAPIST,
		RELATIONSHIP_PSYCHIATRIST,
		RELATIONSHIP_CASE_MANAGER,
		RELATIONSHIP_FAMILY_PRIMARY,
		RELATIONSHIP_FAMILY_SECONDARY,
		RELATIONSHIP_GUARDIAN_LEGAL,
		RELATIONSHIP_GUARDIAN_MEDICAL,
		RELATIONSHIP_EMERGENCY_CONTACT,
		RELATIONSHIP_AUTHORIZED_CAREGIVER,
	}
	
	for _, relationshipType := range types {
		assert.NotEmpty(t, string(relationshipType))
	}
}

func TestRelationshipStatuses(t *testing.T) {
	statuses := []RelationshipStatus{
		STATUS_ACTIVE,
		STATUS_INACTIVE,
		STATUS_PENDING,
		STATUS_TERMINATED,
		STATUS_SUSPENDED,
		STATUS_UNDER_REVIEW,
	}
	
	for _, status := range statuses {
		assert.NotEmpty(t, string(status))
	}
}

func TestAccessLevels(t *testing.T) {
	levels := []AccessLevel{
		ACCESS_FULL,
		ACCESS_LIMITED,
		ACCESS_READ_ONLY,
		ACCESS_EMERGENCY,
		ACCESS_NONE,
	}
	
	for _, level := range levels {
		assert.NotEmpty(t, string(level))
	}
}

// Comprehensive tests for relationship management functionality

func TestNewRelationshipManager(t *testing.T) {
	manager := NewRelationshipManager()
	
	assert.NotNil(t, manager)
	assert.NotNil(t, manager.Relationships)
	assert.NotNil(t, manager.AccessRequests)
	assert.NotNil(t, manager.AuditTrail)
	assert.Equal(t, 10000, manager.MaxRelationships)
	assert.Equal(t, 50000, manager.MaxAuditEntries)
	assert.True(t, manager.ComplianceEnabled)
}

func TestValidateRelationship(t *testing.T) {
	manager := NewRelationshipManager()
	
	tests := []struct {
		name         string
		relationship *TherapeuticRelationship
		expectError  bool
		errorContains string
	}{
		{
			name: "Valid relationship",
			relationship: &TherapeuticRelationship{
				PatientID:         "patient-123",
				RelatedPersonID:   "therapist-456",
				RelatedPersonName: "Dr. Jane Smith",
				RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
				AccessLevel:       ACCESS_FULL,
				CreatedBy:         "admin-001",
			},
			expectError: false,
		},
		{
			name: "Missing patient ID",
			relationship: &TherapeuticRelationship{
				RelatedPersonID:   "therapist-456",
				RelatedPersonName: "Dr. Jane Smith",
				RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
				AccessLevel:       ACCESS_FULL,
				CreatedBy:         "admin-001",
			},
			expectError:   true,
			errorContains: "patient ID is required",
		},
		{
			name: "Missing related person ID",
			relationship: &TherapeuticRelationship{
				PatientID:         "patient-123",
				RelatedPersonName: "Dr. Jane Smith",
				RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
				AccessLevel:       ACCESS_FULL,
				CreatedBy:         "admin-001",
			},
			expectError:   true,
			errorContains: "related person ID is required",
		},
		{
			name: "Missing related person name",
			relationship: &TherapeuticRelationship{
				PatientID:        "patient-123",
				RelatedPersonID:  "therapist-456",
				RelationshipType: RELATIONSHIP_PRIMARY_THERAPIST,
				AccessLevel:      ACCESS_FULL,
				CreatedBy:        "admin-001",
			},
			expectError:   true,
			errorContains: "related person name is required",
		},
		{
			name: "Missing created by",
			relationship: &TherapeuticRelationship{
				PatientID:         "patient-123",
				RelatedPersonID:   "therapist-456",
				RelatedPersonName: "Dr. Jane Smith",
				RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
				AccessLevel:       ACCESS_FULL,
			},
			expectError:   true,
			errorContains: "created by field is required",
		},
		{
			name: "Invalid relationship type",
			relationship: &TherapeuticRelationship{
				PatientID:         "patient-123",
				RelatedPersonID:   "therapist-456",
				RelatedPersonName: "Dr. Jane Smith",
				RelationshipType:  "invalid_type",
				AccessLevel:       ACCESS_FULL,
				CreatedBy:         "admin-001",
			},
			expectError:   true,
			errorContains: "invalid relationship type",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := manager.validateRelationship(tt.relationship)
			
			if tt.expectError {
				assert.Error(t, err)
				if tt.errorContains != "" {
					assert.Contains(t, err.Error(), tt.errorContains)
				}
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestGetDefaultPermissions(t *testing.T) {
	manager := NewRelationshipManager()
	
	tests := []struct {
		name          string
		relType       RelationshipType
		accessLevel   AccessLevel
		expectContains []string
		expectExcludes []string
	}{
		{
			name:          "Primary therapist with full access",
			relType:       RELATIONSHIP_PRIMARY_THERAPIST,
			accessLevel:   ACCESS_FULL,
			expectContains: []string{"read_therapy_notes", "write_therapy_notes", "read_treatment_plan", "write_treatment_plan", "access_crisis_info"},
		},
		{
			name:          "Family member with limited access",
			relType:       RELATIONSHIP_FAMILY_PRIMARY,
			accessLevel:   ACCESS_LIMITED,
			expectContains: []string{"read_basic_info", "receive_updates", "emergency_contact"},
			expectExcludes: []string{"write_therapy_notes", "write_treatment_plan"},
		},
		{
			name:          "Guardian with read-only access",
			relType:       RELATIONSHIP_GUARDIAN_LEGAL,
			accessLevel:   ACCESS_READ_ONLY,
			expectContains: []string{"read_all_records"},
			expectExcludes: []string{"make_treatment_decisions", "make_medical_decisions"},
		},
		{
			name:          "Emergency contact with emergency access",
			relType:       RELATIONSHIP_EMERGENCY_CONTACT,
			accessLevel:   ACCESS_EMERGENCY,
			expectContains: []string{"emergency_contact", "crisis_notification", "access_crisis_info"},
		},
		{
			name:          "Any relationship with no access",
			relType:       RELATIONSHIP_PRIMARY_THERAPIST,
			accessLevel:   ACCESS_NONE,
			expectContains: []string{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			permissions := manager.getDefaultPermissions(tt.relType, tt.accessLevel)
			
			for _, expectedPerm := range tt.expectContains {
				assert.Contains(t, permissions, expectedPerm)
			}
			
			for _, excludedPerm := range tt.expectExcludes {
				assert.NotContains(t, permissions, excludedPerm)
			}
		})
	}
}

func TestCreateRelationshipComplete(t *testing.T) {
	manager := NewRelationshipManager()
	
	tests := []struct {
		name         string
		relationship *TherapeuticRelationship
		expectError  bool
		errorContains string
	}{
		{
			name: "Valid primary therapist relationship",
			relationship: &TherapeuticRelationship{
				PatientID:         "patient-123",
				RelatedPersonID:   "therapist-456",
				RelatedPersonName: "Dr. Jane Smith",
				RelatedPersonEmail: "jane.smith@therapy.com",
				RelatedPersonPhone: "+1-555-0123",
				RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
				AccessLevel:       ACCESS_FULL,
				CreatedBy:         "admin-001",
				Notes:             "Primary therapist assignment for ongoing care",
			},
			expectError: false,
		},
		{
			name: "Valid family relationship",
			relationship: &TherapeuticRelationship{
				PatientID:         "patient-789",
				RelatedPersonID:   "family-001",
				RelatedPersonName: "John Doe",
				RelatedPersonEmail: "john.doe@email.com",
				RelationshipType:  RELATIONSHIP_FAMILY_PRIMARY,
				AccessLevel:       ACCESS_LIMITED,
				CreatedBy:         "case-manager-002",
				Notes:             "Primary family contact for patient updates",
			},
			expectError: false,
		},
		{
			name: "Invalid relationship - missing patient ID",
			relationship: &TherapeuticRelationship{
				RelatedPersonID:   "therapist-456",
				RelatedPersonName: "Dr. Jane Smith",
				RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
				AccessLevel:       ACCESS_FULL,
				CreatedBy:         "admin-001",
			},
			expectError:   true,
			errorContains: "patient ID is required",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			relationship, err := manager.CreateRelationship(tt.relationship, "127.0.0.1")
			
			if tt.expectError {
				assert.Error(t, err)
				assert.Nil(t, relationship)
				if tt.errorContains != "" {
					assert.Contains(t, err.Error(), tt.errorContains)
				}
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, relationship)
				assert.NotEmpty(t, relationship.RelationshipID)
				assert.Equal(t, STATUS_PENDING, relationship.Status)
				assert.NotEmpty(t, relationship.Permissions)
				assert.NotEmpty(t, relationship.AuditTrail)
				assert.Equal(t, "RELATIONSHIP_CREATED", relationship.AuditTrail[0].Action)
			}
		})
	}
}

func TestUpdateRelationshipStatus(t *testing.T) {
	manager := NewRelationshipManager()
	
	// First create a relationship
	relationship := &TherapeuticRelationship{
		PatientID:         "patient-123",
		RelatedPersonID:   "therapist-456",
		RelatedPersonName: "Dr. Jane Smith",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "admin-001",
	}
	
	createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
	require.NoError(t, err)
	
	tests := []struct {
		name           string
		relationshipID string
		newStatus      RelationshipStatus
		changedBy      string
		justification  string
		expectError    bool
	}{
		{
			name:           "Update to active status",
			relationshipID: createdRel.RelationshipID,
			newStatus:      STATUS_ACTIVE,
			changedBy:      "supervisor-001",
			justification:  "Relationship approved after verification",
			expectError:    false,
		},
		{
			name:           "Update to suspended status",
			relationshipID: createdRel.RelationshipID,
			newStatus:      STATUS_SUSPENDED,
			changedBy:      "admin-002",
			justification:  "Temporary suspension pending review",
			expectError:    false,
		},
		{
			name:           "Invalid relationship ID",
			relationshipID: "non-existent-id",
			newStatus:      STATUS_ACTIVE,
			changedBy:      "admin-001",
			justification:  "Test",
			expectError:    true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := manager.UpdateRelationshipStatus(tt.relationshipID, tt.newStatus, tt.changedBy, tt.justification, "127.0.0.1")
			
			if tt.expectError {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
				
				// Verify status was updated
				updatedRel := manager.Relationships[tt.relationshipID]
				assert.Equal(t, tt.newStatus, updatedRel.Status)
				
				// Verify audit trail was updated
				assert.GreaterOrEqual(t, len(updatedRel.AuditTrail), 2)
				lastAudit := updatedRel.AuditTrail[len(updatedRel.AuditTrail)-1]
				assert.Equal(t, "STATUS_UPDATED", lastAudit.Action)
				assert.Equal(t, tt.changedBy, lastAudit.ChangedBy)
				assert.Equal(t, tt.justification, lastAudit.Justification)
			}
		})
	}
}

func TestRequestRelationshipAccess(t *testing.T) {
	manager := NewRelationshipManager()
	
	// First create an active relationship
	relationship := &TherapeuticRelationship{
		PatientID:         "patient-123",
		RelatedPersonID:   "therapist-456",
		RelatedPersonName: "Dr. Jane Smith",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "admin-001",
	}
	
	createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
	require.NoError(t, err)
	
	// Activate the relationship
	err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, STATUS_ACTIVE, "supervisor-001", "Approved", "127.0.0.1")
	require.NoError(t, err)
	
	tests := []struct {
		name         string
		request      *RelationshipAccessRequest
		expectError  bool
		errorContains string
	}{
		{
			name: "Valid access request",
			request: &RelationshipAccessRequest{
				RelationshipID:    createdRel.RelationshipID,
				RequestedBy:       "therapist-456",
				PatientID:         "patient-123",
				AccessType:        "read_therapy_notes",
				ResourceRequested: "therapy_session_notes",
				Justification:     "Review patient progress for treatment planning",
				ClientIP:          "192.168.1.100",
				UserAgent:         "Mozilla/5.0 Test Client",
			},
			expectError: false,
		},
		{
			name: "Non-existent relationship",
			request: &RelationshipAccessRequest{
				RelationshipID:    "non-existent-id",
				RequestedBy:       "therapist-456",
				PatientID:         "patient-123",
				AccessType:        "read_therapy_notes",
				ResourceRequested: "therapy_session_notes",
				Justification:     "Test access",
			},
			expectError:   true,
			errorContains: "relationship not found",
		},
		{
			name: "Insufficient permissions",
			request: &RelationshipAccessRequest{
				RelationshipID:    createdRel.RelationshipID,
				RequestedBy:       "therapist-456",
				PatientID:         "patient-123",
				AccessType:        "unauthorized_access",
				ResourceRequested: "confidential_data",
				Justification:     "Test access",
			},
			expectError:   true,
			errorContains: "insufficient permissions",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			accessRequest, err := manager.RequestRelationshipAccess(tt.request)
			
			if tt.expectError {
				assert.Error(t, err)
				assert.Nil(t, accessRequest)
				if tt.errorContains != "" {
					assert.Contains(t, err.Error(), tt.errorContains)
				}
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, accessRequest)
				assert.NotEmpty(t, accessRequest.RequestID)
				assert.Equal(t, "pending", accessRequest.Status)
				assert.False(t, accessRequest.RequestTimestamp.IsZero())
				
				// Verify request was stored
				storedRequest := manager.AccessRequests[accessRequest.RequestID]
				assert.Equal(t, accessRequest.RequestID, storedRequest.RequestID)
			}
		})
	}
}

func TestGetPatientRelationships(t *testing.T) {
	manager := NewRelationshipManager()
	
	patientID := "patient-123"
	
	// Create multiple relationships for the patient
	relationships := []*TherapeuticRelationship{
		{
			PatientID:         patientID,
			RelatedPersonID:   "therapist-001",
			RelatedPersonName: "Dr. John Smith",
			RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
			AccessLevel:       ACCESS_FULL,
			CreatedBy:         "admin-001",
		},
		{
			PatientID:         patientID,
			RelatedPersonID:   "family-001",
			RelatedPersonName: "Jane Doe",
			RelationshipType:  RELATIONSHIP_FAMILY_PRIMARY,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "case-manager-001",
		},
		{
			PatientID:         "different-patient-456",
			RelatedPersonID:   "therapist-002",
			RelatedPersonName: "Dr. Alice Johnson",
			RelationshipType:  RELATIONSHIP_PSYCHIATRIST,
			AccessLevel:       ACCESS_FULL,
			CreatedBy:         "admin-002",
		},
	}
	
	// Create the relationships
	for _, rel := range relationships {
		_, err := manager.CreateRelationship(rel, "127.0.0.1")
		require.NoError(t, err)
	}
	
	// Test getting relationships for the specific patient
	patientRels := manager.GetPatientRelationships(patientID)
	
	assert.Equal(t, 2, len(patientRels))
	
	// Verify the returned relationships belong to the correct patient
	for _, rel := range patientRels {
		assert.Equal(t, patientID, rel.PatientID)
	}
	
	// Test getting relationships for a patient with no relationships
	emptyRels := manager.GetPatientRelationships("non-existent-patient")
	assert.Equal(t, 0, len(emptyRels))
}

func TestGetPersonRelationships(t *testing.T) {
	manager := NewRelationshipManager()
	
	personID := "therapist-001"
	
	// Create multiple relationships where this person is the related person
	relationships := []*TherapeuticRelationship{
		{
			PatientID:         "patient-123",
			RelatedPersonID:   personID,
			RelatedPersonName: "Dr. John Smith",
			RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
			AccessLevel:       ACCESS_FULL,
			CreatedBy:         "admin-001",
		},
		{
			PatientID:         "patient-456",
			RelatedPersonID:   personID,
			RelatedPersonName: "Dr. John Smith",
			RelationshipType:  RELATIONSHIP_SECONDARY_THERAPIST,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "admin-001",
		},
		{
			PatientID:         "patient-789",
			RelatedPersonID:   "different-person",
			RelatedPersonName: "Dr. Alice Johnson",
			RelationshipType:  RELATIONSHIP_PSYCHIATRIST,
			AccessLevel:       ACCESS_FULL,
			CreatedBy:         "admin-002",
		},
	}
	
	// Create the relationships
	for _, rel := range relationships {
		_, err := manager.CreateRelationship(rel, "127.0.0.1")
		require.NoError(t, err)
	}
	
	// Test getting relationships for the specific person
	personRels := manager.GetPersonRelationships(personID)
	
	assert.Equal(t, 2, len(personRels))
	
	// Verify the returned relationships have the correct related person
	for _, rel := range personRels {
		assert.Equal(t, personID, rel.RelatedPersonID)
	}
}

func TestCheckRelationshipLimits(t *testing.T) {
	manager := NewRelationshipManager()
	
	patientID := "patient-test-limits"
	
	// Create relationships up to the limit (we'll create 5 for testing)
	for i := 0; i < 5; i++ {
		relationship := &TherapeuticRelationship{
			PatientID:         patientID,
			RelatedPersonID:   fmt.Sprintf("person-%d", i),
			RelatedPersonName: fmt.Sprintf("Person %d", i),
			RelationshipType:  RELATIONSHIP_FAMILY_SECONDARY,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "admin-001",
		}
		
		_, err := manager.CreateRelationship(relationship, "127.0.0.1")
		require.NoError(t, err)
		
		// Activate the relationship
		rel := manager.Relationships[relationship.RelationshipID]
		rel.Status = STATUS_ACTIVE
	}
	
	// Test that limits are working (this should pass since 5 < 20)
	err := manager.checkRelationshipLimits(patientID)
	assert.NoError(t, err)
	
	// Test with a different patient should also pass
	err = manager.checkRelationshipLimits("different-patient")
	assert.NoError(t, err)
}

func TestHasPermission(t *testing.T) {
	manager := NewRelationshipManager()
	
	relationship := &TherapeuticRelationship{
		Permissions: []string{"read_therapy_notes", "write_therapy_notes", "access_crisis_info"},
	}
	
	tests := []struct {
		name       string
		accessType string
		expected   bool
	}{
		{
			name:       "Has read permission",
			accessType: "read_therapy_notes",
			expected:   true,
		},
		{
			name:       "Has write permission",
			accessType: "write_therapy_notes",
			expected:   true,
		},
		{
			name:       "Does not have unauthorized permission",
			accessType: "delete_all_records",
			expected:   false,
		},
		{
			name:       "Empty access type",
			accessType: "",
			expected:   false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := manager.hasPermission(relationship, tt.accessType)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestContainsUtility(t *testing.T) {
	slice := []string{"apple", "banana", "cherry"}
	
	assert.True(t, contains("apple", slice))
	assert.True(t, contains("banana", slice))
	assert.False(t, contains("orange", slice))
	assert.False(t, contains("", slice))
}

func TestAuditTrailManagement(t *testing.T) {
	manager := NewRelationshipManager()
	manager.MaxAuditEntries = 3 // Set small limit for testing
	
	// Add multiple audit entries to test size management
	for i := 0; i < 5; i++ {
		auditEntry := RelationshipAuditEntry{
			AuditID:       fmt.Sprintf("audit-%d", i),
			Action:        "TEST_ACTION",
			ChangedBy:     "test-user",
			Timestamp:     time.Now().UTC(),
			Justification: fmt.Sprintf("Test entry %d", i),
		}
		manager.addAuditEntry(auditEntry)
	}
	
	// Verify audit trail size is limited
	assert.Equal(t, 3, len(manager.AuditTrail))
	
	// Verify the latest entries are kept
	assert.Equal(t, "audit-4", manager.AuditTrail[2].AuditID)
	assert.Equal(t, "audit-3", manager.AuditTrail[1].AuditID)
	assert.Equal(t, "audit-2", manager.AuditTrail[0].AuditID)
}

// API Endpoint Tests

func TestCreateRelationshipAPI(t *testing.T) {
	router := setupTestRouter()
	
	requestBody := TherapeuticRelationship{
		PatientID:         "patient-api-test",
		RelatedPersonID:   "therapist-api-test",
		RelatedPersonName: "Dr. API Test",
		RelatedPersonEmail: "api.test@therapy.com",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "api-admin",
		Notes:             "API test relationship creation",
	}
	
	jsonBody, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/relationships", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Forwarded-For", "192.168.1.100")
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response TherapeuticRelationship
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.NotEmpty(t, response.RelationshipID)
	assert.Equal(t, "patient-api-test", response.PatientID)
	assert.Equal(t, "therapist-api-test", response.RelatedPersonID)
	assert.Equal(t, STATUS_PENDING, response.Status)
	assert.NotEmpty(t, response.Permissions)
	assert.Len(t, response.AuditTrail, 1)
}

func TestCreateRelationshipAPI_InvalidData(t *testing.T) {
	router := setupTestRouter()
	
	// Test with missing required fields
	requestBody := TherapeuticRelationship{
		PatientID:        "patient-api-test",
		// Missing RelatedPersonID, RelatedPersonName, RelationshipType, AccessLevel, CreatedBy
	}
	
	jsonBody, _ := json.Marshal(requestBody)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/relationships", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusBadRequest, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, "Failed to create relationship", response["error"])
}

func TestRelationshipPermissionMapping(t *testing.T) {
	manager := NewRelationshipManager()
	
	tests := []struct {
		relType        RelationshipType
		accessLevel    AccessLevel
		shouldHaveRead bool
		shouldHaveWrite bool
		shouldHaveEmergency bool
	}{
		{
			relType:             RELATIONSHIP_PRIMARY_THERAPIST,
			accessLevel:         ACCESS_FULL,
			shouldHaveRead:      true,
			shouldHaveWrite:     true,
			shouldHaveEmergency: true,
		},
		{
			relType:             RELATIONSHIP_SECONDARY_THERAPIST,
			accessLevel:         ACCESS_FULL,
			shouldHaveRead:      true,
			shouldHaveWrite:     false,
			shouldHaveEmergency: true,
		},
		{
			relType:             RELATIONSHIP_FAMILY_PRIMARY,
			accessLevel:         ACCESS_LIMITED,
			shouldHaveRead:      true,
			shouldHaveWrite:     false,
			shouldHaveEmergency: true,
		},
		{
			relType:             RELATIONSHIP_GUARDIAN_LEGAL,
			accessLevel:         ACCESS_READ_ONLY,
			shouldHaveRead:      true,
			shouldHaveWrite:     false,
			shouldHaveEmergency: false,
		},
		{
			relType:             RELATIONSHIP_EMERGENCY_CONTACT,
			accessLevel:         ACCESS_EMERGENCY,
			shouldHaveRead:      false,
			shouldHaveWrite:     false,
			shouldHaveEmergency: true,
		},
	}

	for _, tt := range tests {
		t.Run(fmt.Sprintf("%s_%s", tt.relType, tt.accessLevel), func(t *testing.T) {
			permissions := manager.getDefaultPermissions(tt.relType, tt.accessLevel)
			
			hasRead := false
			hasWrite := false
			hasEmergency := false
			
			for _, perm := range permissions {
				if contains(perm, []string{"read_therapy_notes", "read_treatment_plan", "read_basic_info", "read_medical_records", "read_all_records"}) {
					hasRead = true
				}
				if contains(perm, []string{"write_therapy_notes", "write_treatment_plan", "make_treatment_decisions", "make_medical_decisions"}) {
					hasWrite = true
				}
				if contains(perm, []string{"emergency_contact", "crisis_notification", "access_crisis_info"}) {
					hasEmergency = true
				}
			}
			
			assert.Equal(t, tt.shouldHaveRead, hasRead, "Read permission mismatch")
			assert.Equal(t, tt.shouldHaveWrite, hasWrite, "Write permission mismatch")
			assert.Equal(t, tt.shouldHaveEmergency, hasEmergency, "Emergency permission mismatch")
		})
	}
}

// Integration Tests for API endpoints

func TestGetPatientRelationshipsAPI(t *testing.T) {
	// Create a more comprehensive test router that includes all endpoints
	gin.SetMode(gin.TestMode)
	router := gin.New()
	manager := NewRelationshipManager()
	
	// Add the patient relationships endpoint
	router.GET("/relationships/patient/:patient_id", func(c *gin.Context) {
		patientID := c.Param("patient_id")
		relationships := manager.GetPatientRelationships(patientID)
		
		c.JSON(http.StatusOK, gin.H{
			"patient_id":    patientID,
			"relationships": relationships,
			"count":         len(relationships),
		})
	})
	
	// First create some test relationships
	patientID := "api-test-patient-123"
	relationship1 := &TherapeuticRelationship{
		PatientID:         patientID,
		RelatedPersonID:   "therapist-api-001",
		RelatedPersonName: "Dr. API Test 1",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "api-admin",
	}
	
	relationship2 := &TherapeuticRelationship{
		PatientID:         patientID,
		RelatedPersonID:   "family-api-001",
		RelatedPersonName: "Family API Test",
		RelationshipType:  RELATIONSHIP_FAMILY_PRIMARY,
		AccessLevel:       ACCESS_LIMITED,
		CreatedBy:         "api-admin",
	}
	
	_, err := manager.CreateRelationship(relationship1, "127.0.0.1")
	require.NoError(t, err)
	
	_, err = manager.CreateRelationship(relationship2, "127.0.0.1")
	require.NoError(t, err)
	
	// Test the API endpoint
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", fmt.Sprintf("/relationships/patient/%s", patientID), nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, patientID, response["patient_id"])
	assert.Equal(t, float64(2), response["count"])
	
	relationships := response["relationships"].([]interface{})
	assert.Len(t, relationships, 2)
}

func TestGetPersonRelationshipsAPI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	manager := NewRelationshipManager()
	
	// Add the person relationships endpoint
	router.GET("/relationships/person/:person_id", func(c *gin.Context) {
		personID := c.Param("person_id")
		relationships := manager.GetPersonRelationships(personID)
		
		c.JSON(http.StatusOK, gin.H{
			"person_id":     personID,
			"relationships": relationships,
			"count":         len(relationships),
		})
	})
	
	// Create test relationships
	personID := "api-test-person-456"
	relationship := &TherapeuticRelationship{
		PatientID:         "patient-api-001",
		RelatedPersonID:   personID,
		RelatedPersonName: "API Test Person",
		RelationshipType:  RELATIONSHIP_CASE_MANAGER,
		AccessLevel:       ACCESS_LIMITED,
		CreatedBy:         "api-admin",
	}
	
	_, err := manager.CreateRelationship(relationship, "127.0.0.1")
	require.NoError(t, err)
	
	// Test the API endpoint
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", fmt.Sprintf("/relationships/person/%s", personID), nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, personID, response["person_id"])
	assert.Equal(t, float64(1), response["count"])
}

// Performance and Benchmark Tests

func BenchmarkCreateRelationship(b *testing.B) {
	manager := NewRelationshipManager()
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		relationship := &TherapeuticRelationship{
			PatientID:         fmt.Sprintf("patient-%d", i),
			RelatedPersonID:   fmt.Sprintf("person-%d", i),
			RelatedPersonName: fmt.Sprintf("Person %d", i),
			RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
			AccessLevel:       ACCESS_FULL,
			CreatedBy:         "bench-user",
		}
		
		manager.CreateRelationship(relationship, "127.0.0.1")
	}
}

func BenchmarkGetPatientRelationships(b *testing.B) {
	manager := NewRelationshipManager()
	
	// Pre-populate with test data
	for i := 0; i < 100; i++ {
		relationship := &TherapeuticRelationship{
			PatientID:         "benchmark-patient",
			RelatedPersonID:   fmt.Sprintf("person-%d", i),
			RelatedPersonName: fmt.Sprintf("Person %d", i),
			RelationshipType:  RELATIONSHIP_FAMILY_SECONDARY,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "bench-user",
		}
		
		manager.CreateRelationship(relationship, "127.0.0.1")
	}
	
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		manager.GetPatientRelationships("benchmark-patient")
	}
}

func TestAuditTrailCompliance(t *testing.T) {
	manager := NewRelationshipManager()
	
	// Create a relationship and perform operations
	relationship := &TherapeuticRelationship{
		PatientID:         "audit-test-patient",
		RelatedPersonID:   "audit-test-person",
		RelatedPersonName: "Audit Test Person",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "audit-admin",
	}
	
	// Create relationship
	createdRel, err := manager.CreateRelationship(relationship, "192.168.1.50")
	require.NoError(t, err)
	
	// Update status multiple times
	err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, STATUS_ACTIVE, "supervisor", "Approved after verification", "192.168.1.51")
	require.NoError(t, err)
	
	err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, STATUS_SUSPENDED, "admin", "Temporary suspension", "192.168.1.52")
	require.NoError(t, err)
	
	// Verify audit trail has all operations
	finalRel := manager.Relationships[createdRel.RelationshipID]
	assert.Len(t, finalRel.AuditTrail, 3) // CREATE + 2 STATUS_UPDATES
	
	// Verify audit entry details
	createAudit := finalRel.AuditTrail[0]
	assert.Equal(t, "RELATIONSHIP_CREATED", createAudit.Action)
	assert.Equal(t, "audit-admin", createAudit.ChangedBy)
	assert.Equal(t, "192.168.1.50", createAudit.IPAddress)
	
	activateAudit := finalRel.AuditTrail[1]
	assert.Equal(t, "STATUS_UPDATED", activateAudit.Action)
	assert.Equal(t, string(STATUS_PENDING), activateAudit.OldValue)
	assert.Equal(t, string(STATUS_ACTIVE), activateAudit.NewValue)
	assert.Equal(t, "supervisor", activateAudit.ChangedBy)
	
	suspendAudit := finalRel.AuditTrail[2]
	assert.Equal(t, "STATUS_UPDATED", suspendAudit.Action)
	assert.Equal(t, string(STATUS_ACTIVE), suspendAudit.OldValue)
	assert.Equal(t, string(STATUS_SUSPENDED), suspendAudit.NewValue)
	assert.Equal(t, "admin", suspendAudit.ChangedBy)
}

// Additional API endpoint tests to increase coverage

func TestUpdateRelationshipStatusAPI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	manager := NewRelationshipManager()
	
	// Add the update status endpoint
	router.PUT("/relationships/:relationship_id/status", func(c *gin.Context) {
		relationshipID := c.Param("relationship_id")
		
		var updateRequest struct {
			Status        RelationshipStatus `json:"status" binding:"required"`
			ChangedBy     string            `json:"changed_by" binding:"required"`
			Justification string            `json:"justification" binding:"required"`
		}
		
		if err := c.ShouldBindJSON(&updateRequest); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid status update request",
				"details": err.Error(),
			})
			return
		}
		
		clientIP := c.ClientIP()
		err := manager.UpdateRelationshipStatus(relationshipID, updateRequest.Status, updateRequest.ChangedBy, updateRequest.Justification, clientIP)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Failed to update relationship status",
				"details": err.Error(),
			})
			return
		}
		
		c.JSON(http.StatusOK, gin.H{
			"message": "Relationship status updated successfully",
			"relationship_id": relationshipID,
			"new_status": updateRequest.Status,
		})
	})
	
	// First create a relationship
	relationship := &TherapeuticRelationship{
		PatientID:         "patient-status-test",
		RelatedPersonID:   "person-status-test",
		RelatedPersonName: "Status Test Person",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "api-admin",
	}
	
	createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
	require.NoError(t, err)
	
	// Test status update
	updateRequest := map[string]interface{}{
		"status":        STATUS_ACTIVE,
		"changed_by":    "supervisor-api",
		"justification": "API test status update",
	}
	
	jsonBody, _ := json.Marshal(updateRequest)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("PUT", fmt.Sprintf("/relationships/%s/status", createdRel.RelationshipID), bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, "Relationship status updated successfully", response["message"])
	assert.Equal(t, createdRel.RelationshipID, response["relationship_id"])
}

func TestRequestAccessAPI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	manager := NewRelationshipManager()
	
	// Add the access request endpoint
	router.POST("/relationships/access-request", func(c *gin.Context) {
		var accessRequest RelationshipAccessRequest
		if err := c.ShouldBindJSON(&accessRequest); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid access request data",
				"details": err.Error(),
			})
			return
		}
		
		accessRequest.ClientIP = c.ClientIP()
		accessRequest.UserAgent = c.GetHeader("User-Agent")
		
		createdRequest, err := manager.RequestRelationshipAccess(&accessRequest)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Failed to create access request",
				"details": err.Error(),
			})
			return
		}
		
		c.JSON(http.StatusCreated, createdRequest)
	})
	
	// First create an active relationship
	relationship := &TherapeuticRelationship{
		PatientID:         "patient-access-test",
		RelatedPersonID:   "person-access-test",
		RelatedPersonName: "Access Test Person",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "api-admin",
	}
	
	createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
	require.NoError(t, err)
	
	// Activate the relationship
	err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, STATUS_ACTIVE, "supervisor", "Approved", "127.0.0.1")
	require.NoError(t, err)
	
	// Test access request
	accessRequest := RelationshipAccessRequest{
		RelationshipID:    createdRel.RelationshipID,
		RequestedBy:       "person-access-test",
		PatientID:         "patient-access-test",
		AccessType:        "read_therapy_notes",
		ResourceRequested: "therapy_notes",
		Justification:     "Review patient progress",
	}
	
	jsonBody, _ := json.Marshal(accessRequest)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/relationships/access-request", bytes.NewBuffer(jsonBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "Test Client/1.0")
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response RelationshipAccessRequest
	err = json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.NotEmpty(t, response.RequestID)
	assert.Equal(t, "pending", response.Status)
	assert.Equal(t, "Test Client/1.0", response.UserAgent)
}

func TestGetAuditTrailAPI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	manager := NewRelationshipManager()
	
	// Add the audit trail endpoint
	router.GET("/relationships/audit", func(c *gin.Context) {
		// Verify admin access
		userID := c.GetHeader("X-User-ID")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Authentication required for relationship audit access",
			})
			return
		}
		
		manager.mutex.RLock()
		auditEntries := make([]RelationshipAuditEntry, len(manager.AuditTrail))
		copy(auditEntries, manager.AuditTrail)
		manager.mutex.RUnlock()
		
		// Limit returned entries
		limit := 100
		if len(auditEntries) > limit {
			auditEntries = auditEntries[len(auditEntries)-limit:]
		}
		
		c.JSON(http.StatusOK, gin.H{
			"audit_entries": auditEntries,
			"total_returned": len(auditEntries),
			"compliance_notice": "Relationship audit data maintained per HIPAA requirements",
			"timestamp": time.Now().UTC(),
		})
	})
	
	// Create some audit entries by creating relationships
	for i := 0; i < 3; i++ {
		relationship := &TherapeuticRelationship{
			PatientID:         fmt.Sprintf("patient-audit-%d", i),
			RelatedPersonID:   fmt.Sprintf("person-audit-%d", i),
			RelatedPersonName: fmt.Sprintf("Audit Person %d", i),
			RelationshipType:  RELATIONSHIP_FAMILY_SECONDARY,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "audit-creator",
		}
		
		_, err := manager.CreateRelationship(relationship, "127.0.0.1")
		require.NoError(t, err)
	}
	
	// Test with authentication
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/relationships/audit", nil)
	req.Header.Set("X-User-ID", "admin-user")
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Contains(t, response, "audit_entries")
	assert.Contains(t, response, "compliance_notice")
	assert.Equal(t, float64(3), response["total_returned"])
	
	// Test without authentication
	w2 := httptest.NewRecorder()
	req2, _ := http.NewRequest("GET", "/relationships/audit", nil)
	
	router.ServeHTTP(w2, req2)
	
	assert.Equal(t, http.StatusUnauthorized, w2.Code)
}

func TestGetRelationshipStatsAPI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	manager := NewRelationshipManager()
	
	// Add the stats endpoint
	router.GET("/relationships/stats", func(c *gin.Context) {
		manager.mutex.RLock()
		
		// Calculate statistics
		stats := gin.H{
			"total_relationships": len(manager.Relationships),
			"total_access_requests": len(manager.AccessRequests),
			"total_audit_entries": len(manager.AuditTrail),
		}
		
		// Relationship type distribution
		typeDistribution := make(map[RelationshipType]int)
		statusDistribution := make(map[RelationshipStatus]int)
		for _, rel := range manager.Relationships {
			typeDistribution[rel.RelationshipType]++
			statusDistribution[rel.Status]++
		}
		stats["relationship_type_distribution"] = typeDistribution
		stats["relationship_status_distribution"] = statusDistribution
		
		manager.mutex.RUnlock()
		
		c.JSON(http.StatusOK, gin.H{
			"relationship_stats": stats,
			"service_status": "operational",
			"compliance_monitoring": "active",
			"timestamp": time.Now().UTC(),
		})
	})
	
	// Create test data
	testRelationships := []struct {
		relType RelationshipType
		status  RelationshipStatus
	}{
		{RELATIONSHIP_PRIMARY_THERAPIST, STATUS_ACTIVE},
		{RELATIONSHIP_FAMILY_PRIMARY, STATUS_PENDING},
		{RELATIONSHIP_PSYCHIATRIST, STATUS_ACTIVE},
		{RELATIONSHIP_EMERGENCY_CONTACT, STATUS_ACTIVE},
	}
	
	for i, testRel := range testRelationships {
		relationship := &TherapeuticRelationship{
			PatientID:         fmt.Sprintf("patient-stats-%d", i),
			RelatedPersonID:   fmt.Sprintf("person-stats-%d", i),
			RelatedPersonName: fmt.Sprintf("Stats Person %d", i),
			RelationshipType:  testRel.relType,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "stats-creator",
		}
		
		createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
		require.NoError(t, err)
		
		// Set the desired status
		if testRel.status != STATUS_PENDING {
			err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, testRel.status, "admin", "Status update", "127.0.0.1")
			require.NoError(t, err)
		}
	}
	
	// Test the stats endpoint
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/relationships/stats", nil)
	
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, "operational", response["service_status"])
	assert.Equal(t, "active", response["compliance_monitoring"])
	
	stats := response["relationship_stats"].(map[string]interface{})
	assert.Equal(t, float64(4), stats["total_relationships"])
	
	typeDistribution := stats["relationship_type_distribution"].(map[string]interface{})
	assert.Equal(t, float64(1), typeDistribution["primary_therapist"])
	assert.Equal(t, float64(1), typeDistribution["family_primary"])
}

// Test comprehensive health check API
func TestComprehensiveHealthCheckAPI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	manager := NewRelationshipManager()
	
	// Create some test data
	for i := 0; i < 5; i++ {
		relationship := &TherapeuticRelationship{
			PatientID:         fmt.Sprintf("health-patient-%d", i),
			RelatedPersonID:   fmt.Sprintf("health-person-%d", i),
			RelatedPersonName: fmt.Sprintf("Health Person %d", i),
			RelationshipType:  RELATIONSHIP_FAMILY_SECONDARY,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "health-admin",
		}
		
		createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
		require.NoError(t, err)
		
		// Activate some relationships
		if i < 3 {
			err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, STATUS_ACTIVE, "admin", "Activate for health test", "127.0.0.1")
			require.NoError(t, err)
		}
	}
	
	// Add comprehensive health check endpoint
	router.GET("/health", func(c *gin.Context) {
		manager.mutex.RLock()
		activeCount := 0
		pendingCount := 0
		for _, rel := range manager.Relationships {
			if rel.Status == STATUS_ACTIVE {
				activeCount++
			} else if rel.Status == STATUS_PENDING {
				pendingCount++
			}
		}
		manager.mutex.RUnlock()
		
		c.JSON(http.StatusOK, gin.H{
			"service":   "relationship-management-service",
			"status":    "healthy",
			"timestamp": time.Now().UTC(),
			"version":   "1.0.0-hipaa",
			"capabilities": gin.H{
				"relationship_types": []string{"primary_therapist", "secondary_therapist", "psychiatrist", "case_manager", "family_primary", "family_secondary", "guardian_legal", "guardian_medical", "emergency_contact", "authorized_caregiver"},
				"access_levels": []string{"full", "limited", "read_only", "emergency_only", "none"},
				"compliance": []string{"hipaa_audit_trail", "relationship_validation", "permission_management", "access_control"},
			},
			"metrics": gin.H{
				"total_relationships": len(manager.Relationships),
				"active_relationships": activeCount,
				"pending_relationships": pendingCount,
				"access_requests": len(manager.AccessRequests),
				"audit_entries": len(manager.AuditTrail),
			},
		})
	})
	
	// Test the health endpoint
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	require.NoError(t, err)
	
	assert.Equal(t, "relationship-management-service", response["service"])
	assert.Equal(t, "healthy", response["status"])
	assert.Equal(t, "1.0.0-hipaa", response["version"])
	
	capabilities := response["capabilities"].(map[string]interface{})
	assert.Len(t, capabilities["relationship_types"], 10)
	assert.Len(t, capabilities["access_levels"], 5)
	assert.Len(t, capabilities["compliance"], 4)
	
	metrics := response["metrics"].(map[string]interface{})
	assert.Equal(t, float64(5), metrics["total_relationships"])
	assert.Equal(t, float64(3), metrics["active_relationships"])
	assert.Equal(t, float64(2), metrics["pending_relationships"])
}

// Test error scenarios and edge cases

func TestRequestAccessInactiveRelationship(t *testing.T) {
	manager := NewRelationshipManager()
	
	// Create a pending relationship (not active)
	relationship := &TherapeuticRelationship{
		PatientID:         "patient-inactive",
		RelatedPersonID:   "person-inactive",
		RelatedPersonName: "Inactive Person",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "admin",
	}
	
	createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
	require.NoError(t, err)
	
	// Try to request access without activating the relationship
	accessRequest := &RelationshipAccessRequest{
		RelationshipID:    createdRel.RelationshipID,
		RequestedBy:       "person-inactive",
		PatientID:         "patient-inactive",
		AccessType:        "read_therapy_notes",
		ResourceRequested: "therapy_notes",
		Justification:     "Test access on inactive relationship",
	}
	
	_, err = manager.RequestRelationshipAccess(accessRequest)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "relationship is not active")
}

// Test complex permission scenarios

func TestComplexPermissionScenarios(t *testing.T) {
	manager := NewRelationshipManager()
	
	tests := []struct {
		name        string
		relType     RelationshipType
		accessLevel AccessLevel
		testAccess  []struct {
			permission string
			expected   bool
		}
	}{
		{
			name:        "Psychiatrist with full access",
			relType:     RELATIONSHIP_PSYCHIATRIST,
			accessLevel: ACCESS_FULL,
			testAccess: []struct {
				permission string
				expected   bool
			}{
				{"read_therapy_notes", true},
				{"read_medication_history", true},
				{"write_medication_notes", true},
				{"access_crisis_info", true},
				{"write_therapy_notes", false}, // Psychiatrists don't have therapy note write access
			},
		},
		{
			name:        "Case manager with limited access",
			relType:     RELATIONSHIP_CASE_MANAGER,
			accessLevel: ACCESS_LIMITED,
			testAccess: []struct {
				permission string
				expected   bool
			}{
				{"read_basic_info", true},
				{"read_treatment_plan", true},
				{"coordinate_care", true},
				{"write_treatment_plan", false}, // Limited access removes write permissions
			},
		},
		{
			name:        "Legal guardian with read-only access",
			relType:     RELATIONSHIP_GUARDIAN_LEGAL,
			accessLevel: ACCESS_READ_ONLY,
			testAccess: []struct {
				permission string
				expected   bool
			}{
				{"read_all_records", true},
				{"make_treatment_decisions", false}, // Read-only removes decision-making
				{"make_medical_decisions", false},   // Read-only removes decision-making
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			permissions := manager.getDefaultPermissions(tt.relType, tt.accessLevel)
			
			relationship := &TherapeuticRelationship{
				Permissions: permissions,
			}
			
			for _, testPerm := range tt.testAccess {
				result := manager.hasPermission(relationship, testPerm.permission)
				assert.Equal(t, testPerm.expected, result, 
					"Permission %s should be %v for %s with %s access", 
					testPerm.permission, testPerm.expected, tt.relType, tt.accessLevel)
			}
		})
	}
}

// Test concurrent access and thread safety

func TestConcurrentRelationshipOperations(t *testing.T) {
	manager := NewRelationshipManager()
	
	// Create multiple relationships concurrently
	numGoroutines := 10
	errChan := make(chan error, numGoroutines)
	
	for i := 0; i < numGoroutines; i++ {
		go func(index int) {
			relationship := &TherapeuticRelationship{
				PatientID:         fmt.Sprintf("concurrent-patient-%d", index),
				RelatedPersonID:   fmt.Sprintf("concurrent-person-%d", index),
				RelatedPersonName: fmt.Sprintf("Concurrent Person %d", index),
				RelationshipType:  RELATIONSHIP_FAMILY_SECONDARY,
				AccessLevel:       ACCESS_LIMITED,
				CreatedBy:         "concurrent-admin",
			}
			
			_, err := manager.CreateRelationship(relationship, "127.0.0.1")
			errChan <- err
		}(i)
	}
	
	// Wait for all goroutines to complete
	for i := 0; i < numGoroutines; i++ {
		err := <-errChan
		assert.NoError(t, err)
	}
	
	// Verify all relationships were created
	assert.Equal(t, numGoroutines, len(manager.Relationships))
}

func TestRelationshipInactiveWithInactiveStatus(t *testing.T) {
	manager := NewRelationshipManager()
	
	// Create a relationship and set it to inactive status
	relationship := &TherapeuticRelationship{
		PatientID:         "patient-inactive-test",
		RelatedPersonID:   "person-inactive-test",
		RelatedPersonName: "Inactive Test Person",
		RelationshipType:  RELATIONSHIP_PRIMARY_THERAPIST,
		AccessLevel:       ACCESS_FULL,
		CreatedBy:         "admin",
	}
	
	createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
	require.NoError(t, err)
	
	// Set to inactive
	err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, STATUS_INACTIVE, "admin", "Set inactive for testing", "127.0.0.1")
	require.NoError(t, err)
	
	// Try to request access through inactive relationship
	accessRequest := &RelationshipAccessRequest{
		RelationshipID:    createdRel.RelationshipID,
		RequestedBy:       "person-inactive-test",
		PatientID:         "patient-inactive-test",
		AccessType:        "read_therapy_notes",
		ResourceRequested: "therapy_notes",
		Justification:     "Test access on inactive relationship",
	}
	
	_, err = manager.RequestRelationshipAccess(accessRequest)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "relationship is not active")
}

// Test edge cases and error handling

func TestEmptyRelationshipData(t *testing.T) {
	manager := NewRelationshipManager()
	
	emptyRelationship := &TherapeuticRelationship{}
	
	_, err := manager.CreateRelationship(emptyRelationship, "127.0.0.1")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "patient ID is required")
}

func TestAllRelationshipTypesAndStatuses(t *testing.T) {
	manager := NewRelationshipManager()
	
	allTypes := []RelationshipType{
		RELATIONSHIP_PRIMARY_THERAPIST,
		RELATIONSHIP_SECONDARY_THERAPIST,
		RELATIONSHIP_PSYCHIATRIST,
		RELATIONSHIP_CASE_MANAGER,
		RELATIONSHIP_FAMILY_PRIMARY,
		RELATIONSHIP_FAMILY_SECONDARY,
		RELATIONSHIP_GUARDIAN_LEGAL,
		RELATIONSHIP_GUARDIAN_MEDICAL,
		RELATIONSHIP_EMERGENCY_CONTACT,
		RELATIONSHIP_AUTHORIZED_CAREGIVER,
	}
	
	allStatuses := []RelationshipStatus{
		STATUS_ACTIVE,
		STATUS_INACTIVE,
		STATUS_PENDING,
		STATUS_TERMINATED,
		STATUS_SUSPENDED,
		STATUS_UNDER_REVIEW,
	}
	
	// Test creating relationships with all types
	for i, relType := range allTypes {
		relationship := &TherapeuticRelationship{
			PatientID:         fmt.Sprintf("type-test-patient-%d", i),
			RelatedPersonID:   fmt.Sprintf("type-test-person-%d", i),
			RelatedPersonName: fmt.Sprintf("Type Test Person %d", i),
			RelationshipType:  relType,
			AccessLevel:       ACCESS_LIMITED,
			CreatedBy:         "type-test-admin",
		}
		
		createdRel, err := manager.CreateRelationship(relationship, "127.0.0.1")
		assert.NoError(t, err)
		assert.Equal(t, relType, createdRel.RelationshipType)
		assert.Equal(t, STATUS_PENDING, createdRel.Status)
		
		// Test status updates for each relationship
		for _, status := range allStatuses {
			if status != STATUS_PENDING { // Skip pending since that's the default
				err = manager.UpdateRelationshipStatus(createdRel.RelationshipID, status, "admin", fmt.Sprintf("Testing %s status", status), "127.0.0.1")
				assert.NoError(t, err)
				
				updatedRel := manager.Relationships[createdRel.RelationshipID]
				assert.Equal(t, status, updatedRel.Status)
			}
		}
	}
	
	// Verify all relationships were created
	assert.Equal(t, len(allTypes), len(manager.Relationships))
}

func TestAllAccessLevelPermissions(t *testing.T) {
	manager := NewRelationshipManager()
	
	allAccessLevels := []AccessLevel{
		ACCESS_FULL,
		ACCESS_LIMITED,
		ACCESS_READ_ONLY,
		ACCESS_EMERGENCY,
		ACCESS_NONE,
	}
	
	// Test permissions for each access level with primary therapist role
	for _, accessLevel := range allAccessLevels {
		t.Run(fmt.Sprintf("AccessLevel_%s", accessLevel), func(t *testing.T) {
			permissions := manager.getDefaultPermissions(RELATIONSHIP_PRIMARY_THERAPIST, accessLevel)
			
			switch accessLevel {
			case ACCESS_FULL:
				assert.Greater(t, len(permissions), 0)
				assert.Contains(t, permissions, "read_therapy_notes")
				assert.Contains(t, permissions, "write_therapy_notes")
			case ACCESS_LIMITED:
				assert.Greater(t, len(permissions), 0)
				assert.Contains(t, permissions, "read_therapy_notes")
				// Should not contain write permissions
				assert.NotContains(t, permissions, "write_therapy_notes")
			case ACCESS_READ_ONLY:
				if len(permissions) > 0 {
					// Should only contain read permissions
					for _, perm := range permissions {
						assert.True(t, contains(perm, []string{"read_therapy_notes", "read_treatment_plan"}), 
							"Permission %s should be read-only", perm)
					}
				}
			case ACCESS_EMERGENCY:
				assert.Contains(t, permissions, "emergency_contact")
				assert.Contains(t, permissions, "crisis_notification")
				assert.Contains(t, permissions, "access_crisis_info")
			case ACCESS_NONE:
				assert.Equal(t, 0, len(permissions))
			}
		})
	}
}

// Test CORS and middleware functionality
func TestCORSMiddleware(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	
	// Add CORS middleware like in main.go
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
	
	// Add a simple test endpoint
	router.GET("/test", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"test": "success"})
	})
	
	// Test CORS headers on regular request
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/test", nil)
	router.ServeHTTP(w, req)
	
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "*", w.Header().Get("Access-Control-Allow-Origin"))
	assert.Equal(t, "GET, POST, PUT, DELETE, OPTIONS", w.Header().Get("Access-Control-Allow-Methods"))
	
	// Test OPTIONS request
	w2 := httptest.NewRecorder()
	req2, _ := http.NewRequest("OPTIONS", "/test", nil)
	router.ServeHTTP(w2, req2)
	
	assert.Equal(t, http.StatusNoContent, w2.Code)
	assert.Equal(t, "*", w2.Header().Get("Access-Control-Allow-Origin"))
}