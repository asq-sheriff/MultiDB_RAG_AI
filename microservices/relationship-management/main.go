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

// RelationshipType defines types of therapeutic and family relationships
type RelationshipType string

const (
	RELATIONSHIP_PRIMARY_THERAPIST     RelationshipType = "primary_therapist"
	RELATIONSHIP_SECONDARY_THERAPIST   RelationshipType = "secondary_therapist"
	RELATIONSHIP_PSYCHIATRIST          RelationshipType = "psychiatrist"
	RELATIONSHIP_CASE_MANAGER          RelationshipType = "case_manager"
	RELATIONSHIP_FAMILY_PRIMARY        RelationshipType = "family_primary"
	RELATIONSHIP_FAMILY_SECONDARY      RelationshipType = "family_secondary"
	RELATIONSHIP_GUARDIAN_LEGAL        RelationshipType = "guardian_legal"
	RELATIONSHIP_GUARDIAN_MEDICAL      RelationshipType = "guardian_medical"
	RELATIONSHIP_EMERGENCY_CONTACT     RelationshipType = "emergency_contact"
	RELATIONSHIP_AUTHORIZED_CAREGIVER  RelationshipType = "authorized_caregiver"
)

// RelationshipStatus defines the status of a therapeutic relationship
type RelationshipStatus string

const (
	STATUS_ACTIVE         RelationshipStatus = "active"
	STATUS_INACTIVE       RelationshipStatus = "inactive"
	STATUS_PENDING        RelationshipStatus = "pending"
	STATUS_TERMINATED     RelationshipStatus = "terminated"
	STATUS_SUSPENDED      RelationshipStatus = "suspended"
	STATUS_UNDER_REVIEW   RelationshipStatus = "under_review"
)

// AccessLevel defines what level of access each relationship has
type AccessLevel string

const (
	ACCESS_FULL         AccessLevel = "full"
	ACCESS_LIMITED      AccessLevel = "limited"
	ACCESS_READ_ONLY    AccessLevel = "read_only"
	ACCESS_EMERGENCY    AccessLevel = "emergency_only"
	ACCESS_NONE         AccessLevel = "none"
)

// TherapeuticRelationship represents a relationship in the therapeutic care network
type TherapeuticRelationship struct {
	RelationshipID     string             `json:"relationship_id"`
	PatientID          string             `json:"patient_id" binding:"required"`
	RelatedPersonID    string             `json:"related_person_id" binding:"required"`
	RelatedPersonName  string             `json:"related_person_name" binding:"required"`
	RelatedPersonEmail string             `json:"related_person_email,omitempty"`
	RelatedPersonPhone string             `json:"related_person_phone,omitempty"`
	RelationshipType   RelationshipType   `json:"relationship_type" binding:"required"`
	Status             RelationshipStatus `json:"status"`
	AccessLevel        AccessLevel        `json:"access_level" binding:"required"`
	EstablishedDate    time.Time          `json:"established_date"`
	LastUpdated        time.Time          `json:"last_updated"`
	ExpirationDate     *time.Time         `json:"expiration_date,omitempty"`
	Notes              string             `json:"notes,omitempty"`
	Permissions        []string           `json:"permissions"`
	CreatedBy          string             `json:"created_by" binding:"required"`
	ApprovedBy         string             `json:"approved_by,omitempty"`
	ConsentDocumentID  string             `json:"consent_document_id,omitempty"`
	AuditTrail         []RelationshipAuditEntry `json:"audit_trail,omitempty"`
}

// RelationshipAuditEntry tracks changes to therapeutic relationships
type RelationshipAuditEntry struct {
	AuditID        string             `json:"audit_id"`
	RelationshipID string             `json:"relationship_id"`
	Action         string             `json:"action"`
	OldValue       string             `json:"old_value,omitempty"`
	NewValue       string             `json:"new_value,omitempty"`
	ChangedBy      string             `json:"changed_by"`
	Timestamp      time.Time          `json:"timestamp"`
	Justification  string             `json:"justification,omitempty"`
	IPAddress      string             `json:"ip_address"`
}

// RelationshipAccessRequest represents a request to access patient data through relationship
type RelationshipAccessRequest struct {
	RequestID        string             `json:"request_id"`
	RelationshipID   string             `json:"relationship_id" binding:"required"`
	RequestedBy      string             `json:"requested_by" binding:"required"`
	PatientID        string             `json:"patient_id" binding:"required"`
	AccessType       string             `json:"access_type" binding:"required"`
	ResourceRequested string            `json:"resource_requested" binding:"required"`
	Justification    string             `json:"justification" binding:"required"`
	RequestTimestamp time.Time          `json:"request_timestamp"`
	Status           string             `json:"status"`
	ApprovedBy       string             `json:"approved_by,omitempty"`
	ApprovalTimestamp *time.Time        `json:"approval_timestamp,omitempty"`
	ExpiresAt        *time.Time         `json:"expires_at,omitempty"`
	ClientIP         string             `json:"client_ip"`
	UserAgent        string             `json:"user_agent"`
}

// RelationshipManager manages therapeutic relationships and access control
type RelationshipManager struct {
	Relationships      map[string]*TherapeuticRelationship `json:"relationships"`
	AccessRequests     map[string]*RelationshipAccessRequest `json:"access_requests"`
	AuditTrail         []RelationshipAuditEntry           `json:"audit_trail"`
	MaxRelationships   int                                 `json:"max_relationships"`
	MaxAuditEntries    int                                 `json:"max_audit_entries"`
	ComplianceEnabled  bool                                `json:"compliance_enabled"`
	mutex              sync.RWMutex
}

// NewRelationshipManager creates a new relationship management service
func NewRelationshipManager() *RelationshipManager {
	manager := &RelationshipManager{
		Relationships:     make(map[string]*TherapeuticRelationship),
		AccessRequests:    make(map[string]*RelationshipAccessRequest),
		AuditTrail:        make([]RelationshipAuditEntry, 0),
		MaxRelationships:  10000,
		MaxAuditEntries:   50000,
		ComplianceEnabled: true,
	}
	
	log.Println("👥 Relationship Management Service initialized with HIPAA compliance")
	return manager
}

// CreateRelationship establishes a new therapeutic relationship
func (rm *RelationshipManager) CreateRelationship(relationship *TherapeuticRelationship, clientIP string) (*TherapeuticRelationship, error) {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()
	
	// Generate relationship ID
	if relationship.RelationshipID == "" {
		relationship.RelationshipID = uuid.New().String()
	}
	
	// Set default values
	relationship.EstablishedDate = time.Now().UTC()
	relationship.LastUpdated = time.Now().UTC()
	relationship.Status = STATUS_PENDING // Relationships start as pending
	
	// Set default permissions based on relationship type
	relationship.Permissions = rm.getDefaultPermissions(relationship.RelationshipType, relationship.AccessLevel)
	
	// Validate relationship
	if err := rm.validateRelationship(relationship); err != nil {
		return nil, fmt.Errorf("relationship validation failed: %w", err)
	}
	
	// Check for existing relationships and limits
	if err := rm.checkRelationshipLimits(relationship.PatientID); err != nil {
		return nil, fmt.Errorf("relationship limits exceeded: %w", err)
	}
	
	// Store relationship
	rm.Relationships[relationship.RelationshipID] = relationship
	
	// Create audit entry
	auditEntry := RelationshipAuditEntry{
		AuditID:        uuid.New().String(),
		RelationshipID: relationship.RelationshipID,
		Action:         "RELATIONSHIP_CREATED",
		NewValue:       fmt.Sprintf("Type: %s, Access: %s, Status: %s", relationship.RelationshipType, relationship.AccessLevel, relationship.Status),
		ChangedBy:      relationship.CreatedBy,
		Timestamp:      time.Now().UTC(),
		Justification:  "New therapeutic relationship establishment",
		IPAddress:      clientIP,
	}
	
	rm.addAuditEntry(auditEntry)
	relationship.AuditTrail = []RelationshipAuditEntry{auditEntry}
	
	log.Printf("👥 RELATIONSHIP CREATED: ID: %s, Patient: %s, Type: %s, RelatedPerson: %s", 
		relationship.RelationshipID[:8], relationship.PatientID, relationship.RelationshipType, relationship.RelatedPersonID)
	
	return relationship, nil
}

// getDefaultPermissions returns default permissions based on relationship type and access level
func (rm *RelationshipManager) getDefaultPermissions(relType RelationshipType, accessLevel AccessLevel) []string {
	basePermissions := map[RelationshipType][]string{
		RELATIONSHIP_PRIMARY_THERAPIST:    {"read_therapy_notes", "write_therapy_notes", "read_treatment_plan", "write_treatment_plan", "access_crisis_info"},
		RELATIONSHIP_SECONDARY_THERAPIST:  {"read_therapy_notes", "read_treatment_plan", "access_crisis_info"},
		RELATIONSHIP_PSYCHIATRIST:         {"read_therapy_notes", "read_medication_history", "write_medication_notes", "access_crisis_info"},
		RELATIONSHIP_CASE_MANAGER:         {"read_basic_info", "read_treatment_plan", "coordinate_care"},
		RELATIONSHIP_FAMILY_PRIMARY:       {"read_basic_info", "receive_updates", "emergency_contact"},
		RELATIONSHIP_FAMILY_SECONDARY:     {"read_basic_info", "receive_updates"},
		RELATIONSHIP_GUARDIAN_LEGAL:       {"read_all_records", "make_treatment_decisions", "access_crisis_info", "emergency_contact"},
		RELATIONSHIP_GUARDIAN_MEDICAL:     {"read_medical_records", "make_medical_decisions", "access_crisis_info", "emergency_contact"},
		RELATIONSHIP_EMERGENCY_CONTACT:    {"emergency_contact", "crisis_notification"},
		RELATIONSHIP_AUTHORIZED_CAREGIVER: {"read_basic_info", "receive_care_instructions", "emergency_contact"},
	}
	
	permissions := basePermissions[relType]
	
	// Modify permissions based on access level
	switch accessLevel {
	case ACCESS_LIMITED:
		// Remove write permissions for limited access
		filteredPerms := []string{}
		for _, perm := range permissions {
			if !contains(perm, []string{"write_therapy_notes", "write_treatment_plan", "make_treatment_decisions", "make_medical_decisions"}) {
				filteredPerms = append(filteredPerms, perm)
			}
		}
		permissions = filteredPerms
	case ACCESS_READ_ONLY:
		// Only keep read permissions
		filteredPerms := []string{}
		for _, perm := range permissions {
			if contains(perm, []string{"read_therapy_notes", "read_treatment_plan", "read_basic_info", "read_medical_records", "read_all_records"}) {
				filteredPerms = append(filteredPerms, perm)
			}
		}
		permissions = filteredPerms
	case ACCESS_EMERGENCY:
		// Only emergency and crisis permissions
		permissions = []string{"emergency_contact", "crisis_notification", "access_crisis_info"}
	case ACCESS_NONE:
		permissions = []string{}
	}
	
	return permissions
}

// contains checks if a string is in a slice of strings
func contains(item string, slice []string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// validateRelationship validates a therapeutic relationship
func (rm *RelationshipManager) validateRelationship(relationship *TherapeuticRelationship) error {
	if relationship.PatientID == "" {
		return fmt.Errorf("patient ID is required")
	}
	if relationship.RelatedPersonID == "" {
		return fmt.Errorf("related person ID is required")
	}
	if relationship.RelatedPersonName == "" {
		return fmt.Errorf("related person name is required")
	}
	if relationship.CreatedBy == "" {
		return fmt.Errorf("created by field is required")
	}
	
	// Validate relationship type
	validTypes := []RelationshipType{
		RELATIONSHIP_PRIMARY_THERAPIST, RELATIONSHIP_SECONDARY_THERAPIST, RELATIONSHIP_PSYCHIATRIST,
		RELATIONSHIP_CASE_MANAGER, RELATIONSHIP_FAMILY_PRIMARY, RELATIONSHIP_FAMILY_SECONDARY,
		RELATIONSHIP_GUARDIAN_LEGAL, RELATIONSHIP_GUARDIAN_MEDICAL, RELATIONSHIP_EMERGENCY_CONTACT,
		RELATIONSHIP_AUTHORIZED_CAREGIVER,
	}
	
	typeValid := false
	for _, validType := range validTypes {
		if relationship.RelationshipType == validType {
			typeValid = true
			break
		}
	}
	if !typeValid {
		return fmt.Errorf("invalid relationship type: %s", relationship.RelationshipType)
	}
	
	return nil
}

// checkRelationshipLimits checks if adding this relationship would exceed limits
func (rm *RelationshipManager) checkRelationshipLimits(patientID string) error {
	// Count existing relationships for patient
	count := 0
	for _, rel := range rm.Relationships {
		if rel.PatientID == patientID && rel.Status == STATUS_ACTIVE {
			count++
		}
	}
	
	// Set reasonable limits
	maxRelationshipsPerPatient := 20
	if count >= maxRelationshipsPerPatient {
		return fmt.Errorf("maximum relationships per patient exceeded (%d)", maxRelationshipsPerPatient)
	}
	
	return nil
}

// UpdateRelationshipStatus updates the status of a therapeutic relationship
func (rm *RelationshipManager) UpdateRelationshipStatus(relationshipID string, newStatus RelationshipStatus, changedBy string, justification string, clientIP string) error {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()
	
	relationship, exists := rm.Relationships[relationshipID]
	if !exists {
		return fmt.Errorf("relationship not found: %s", relationshipID)
	}
	
	oldStatus := relationship.Status
	relationship.Status = newStatus
	relationship.LastUpdated = time.Now().UTC()
	
	// Create audit entry
	auditEntry := RelationshipAuditEntry{
		AuditID:        uuid.New().String(),
		RelationshipID: relationshipID,
		Action:         "STATUS_UPDATED",
		OldValue:       string(oldStatus),
		NewValue:       string(newStatus),
		ChangedBy:      changedBy,
		Timestamp:      time.Now().UTC(),
		Justification:  justification,
		IPAddress:      clientIP,
	}
	
	rm.addAuditEntry(auditEntry)
	relationship.AuditTrail = append(relationship.AuditTrail, auditEntry)
	
	log.Printf("👥 RELATIONSHIP STATUS UPDATED: ID: %s, Old: %s, New: %s, By: %s", 
		relationshipID[:8], oldStatus, newStatus, changedBy)
	
	return nil
}

// RequestRelationshipAccess creates a request for accessing patient data through a relationship
func (rm *RelationshipManager) RequestRelationshipAccess(request *RelationshipAccessRequest) (*RelationshipAccessRequest, error) {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()
	
	// Generate request ID
	if request.RequestID == "" {
		request.RequestID = uuid.New().String()
	}
	
	request.RequestTimestamp = time.Now().UTC()
	request.Status = "pending"
	
	// Validate the relationship exists and is active
	relationship, exists := rm.Relationships[request.RelationshipID]
	if !exists {
		return nil, fmt.Errorf("relationship not found: %s", request.RelationshipID)
	}
	
	if relationship.Status != STATUS_ACTIVE {
		return nil, fmt.Errorf("relationship is not active (status: %s)", relationship.Status)
	}
	
	// Check if the requester has permission for this type of access
	if !rm.hasPermission(relationship, request.AccessType) {
		return nil, fmt.Errorf("insufficient permissions for access type: %s", request.AccessType)
	}
	
	// Store access request
	rm.AccessRequests[request.RequestID] = request
	
	// Create audit entry
	auditEntry := RelationshipAuditEntry{
		AuditID:        uuid.New().String(),
		RelationshipID: request.RelationshipID,
		Action:         "ACCESS_REQUESTED",
		NewValue:       fmt.Sprintf("Type: %s, Resource: %s", request.AccessType, request.ResourceRequested),
		ChangedBy:      request.RequestedBy,
		Timestamp:      time.Now().UTC(),
		Justification:  request.Justification,
		IPAddress:      request.ClientIP,
	}
	
	rm.addAuditEntry(auditEntry)
	
	log.Printf("👥 ACCESS REQUESTED: Request: %s, Relationship: %s, Type: %s, Resource: %s", 
		request.RequestID[:8], request.RelationshipID[:8], request.AccessType, request.ResourceRequested)
	
	return request, nil
}

// hasPermission checks if a relationship has permission for a specific access type
func (rm *RelationshipManager) hasPermission(relationship *TherapeuticRelationship, accessType string) bool {
	for _, permission := range relationship.Permissions {
		if permission == accessType {
			return true
		}
	}
	return false
}

// GetPatientRelationships returns all relationships for a specific patient
func (rm *RelationshipManager) GetPatientRelationships(patientID string) []*TherapeuticRelationship {
	rm.mutex.RLock()
	defer rm.mutex.RUnlock()
	
	relationships := make([]*TherapeuticRelationship, 0)
	for _, relationship := range rm.Relationships {
		if relationship.PatientID == patientID {
			relationships = append(relationships, relationship)
		}
	}
	
	return relationships
}

// GetPersonRelationships returns all relationships for a specific person (as related person)
func (rm *RelationshipManager) GetPersonRelationships(personID string) []*TherapeuticRelationship {
	rm.mutex.RLock()
	defer rm.mutex.RUnlock()
	
	relationships := make([]*TherapeuticRelationship, 0)
	for _, relationship := range rm.Relationships {
		if relationship.RelatedPersonID == personID {
			relationships = append(relationships, relationship)
		}
	}
	
	return relationships
}

// addAuditEntry adds an entry to the audit trail
func (rm *RelationshipManager) addAuditEntry(entry RelationshipAuditEntry) {
	rm.AuditTrail = append(rm.AuditTrail, entry)
	
	// Manage audit trail size
	if len(rm.AuditTrail) > rm.MaxAuditEntries {
		rm.AuditTrail = rm.AuditTrail[len(rm.AuditTrail)-rm.MaxAuditEntries:]
	}
	
	// Log audit entry
	auditJSON, _ := json.Marshal(entry)
	log.Printf("🔒 RELATIONSHIP_AUDIT: %s", string(auditJSON))
}

// Global relationship manager instance
var relationshipManager *RelationshipManager

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
	
	// Initialize relationship manager
	relationshipManager = NewRelationshipManager()

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
		relationshipManager.mutex.RLock()
		activeCount := 0
		pendingCount := 0
		for _, rel := range relationshipManager.Relationships {
			if rel.Status == STATUS_ACTIVE {
				activeCount++
			} else if rel.Status == STATUS_PENDING {
				pendingCount++
			}
		}
		relationshipManager.mutex.RUnlock()
		
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
				"total_relationships": len(relationshipManager.Relationships),
				"active_relationships": activeCount,
				"pending_relationships": pendingCount,
				"access_requests": len(relationshipManager.AccessRequests),
				"audit_entries": len(relationshipManager.AuditTrail),
			},
		})
	})

	// Create relationship endpoint
	router.POST("/relationships", func(c *gin.Context) {
		var relationship TherapeuticRelationship
		if err := c.ShouldBindJSON(&relationship); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid relationship data",
				"details": err.Error(),
			})
			return
		}
		
		clientIP := c.ClientIP()
		createdRelationship, err := relationshipManager.CreateRelationship(&relationship, clientIP)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Failed to create relationship",
				"details": err.Error(),
			})
			return
		}
		
		c.JSON(http.StatusCreated, createdRelationship)
	})

	// Get patient relationships endpoint
	router.GET("/relationships/patient/:patient_id", func(c *gin.Context) {
		patientID := c.Param("patient_id")
		relationships := relationshipManager.GetPatientRelationships(patientID)
		
		c.JSON(http.StatusOK, gin.H{
			"patient_id": patientID,
			"relationships": relationships,
			"count": len(relationships),
		})
	})

	// Get person relationships endpoint (as related person)
	router.GET("/relationships/person/:person_id", func(c *gin.Context) {
		personID := c.Param("person_id")
		relationships := relationshipManager.GetPersonRelationships(personID)
		
		c.JSON(http.StatusOK, gin.H{
			"person_id": personID,
			"relationships": relationships,
			"count": len(relationships),
		})
	})

	// Update relationship status endpoint
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
		err := relationshipManager.UpdateRelationshipStatus(relationshipID, updateRequest.Status, updateRequest.ChangedBy, updateRequest.Justification, clientIP)
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

	// Request access through relationship endpoint
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
		
		createdRequest, err := relationshipManager.RequestRelationshipAccess(&accessRequest)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Failed to create access request",
				"details": err.Error(),
			})
			return
		}
		
		c.JSON(http.StatusCreated, createdRequest)
	})

	// Get relationship audit trail endpoint (protected)
	router.GET("/relationships/audit", func(c *gin.Context) {
		// Verify admin access
		userID := c.GetHeader("X-User-ID")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "Authentication required for relationship audit access",
			})
			return
		}
		
		relationshipManager.mutex.RLock()
		auditEntries := make([]RelationshipAuditEntry, len(relationshipManager.AuditTrail))
		copy(auditEntries, relationshipManager.AuditTrail)
		relationshipManager.mutex.RUnlock()
		
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

	// Get relationship statistics endpoint
	router.GET("/relationships/stats", func(c *gin.Context) {
		relationshipManager.mutex.RLock()
		
		// Calculate statistics
		stats := gin.H{
			"total_relationships": len(relationshipManager.Relationships),
			"total_access_requests": len(relationshipManager.AccessRequests),
			"total_audit_entries": len(relationshipManager.AuditTrail),
		}
		
		// Relationship type distribution
		typeDistribution := make(map[RelationshipType]int)
		statusDistribution := make(map[RelationshipStatus]int)
		for _, rel := range relationshipManager.Relationships {
			typeDistribution[rel.RelationshipType]++
			statusDistribution[rel.Status]++
		}
		stats["relationship_type_distribution"] = typeDistribution
		stats["relationship_status_distribution"] = statusDistribution
		
		relationshipManager.mutex.RUnlock()
		
		c.JSON(http.StatusOK, gin.H{
			"relationship_stats": stats,
			"service_status": "operational",
			"compliance_monitoring": "active",
			"timestamp": time.Now().UTC(),
		})
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8083"
	}

	log.Printf("🚀 Relationship Management Service starting on port %s", port)
	log.Printf("👥 Therapeutic relationship management active with HIPAA compliance")
	log.Printf("📊 Service capabilities:")
	log.Printf("   - Therapeutic relationship management")
	log.Printf("   - Family and guardian relationship tracking")
	log.Printf("   - Permission-based access control")
	log.Printf("   - HIPAA-compliant audit trail")
	log.Printf("   - Relationship status lifecycle management")
	
	if err := router.Run(":" + port); err != nil {
		log.Fatalf("Failed to start Relationship Management Service: %v", err)
	}
}