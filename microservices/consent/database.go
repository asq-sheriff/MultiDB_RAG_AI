package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/lib/pq"
	_ "github.com/lib/pq"
	"go.uber.org/zap"
)

type PostgresDB struct {
	conn   *sql.DB
	logger *zap.Logger
}

func NewPostgresDB(databaseURL string) (*PostgresDB, error) {
	conn, err := sql.Open("postgres", databaseURL)
	if err != nil {
		return nil, fmt.Errorf("failed to open database connection: %w", err)
	}

	// Configure connection pool
	conn.SetMaxOpenConns(25)
	conn.SetMaxIdleConns(5)
	conn.SetConnMaxLifetime(5 * time.Minute)

	// Test connection
	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	logger, _ := zap.NewProduction()

	return &PostgresDB{
		conn:   conn,
		logger: logger,
	}, nil
}

func (db *PostgresDB) Close() error {
	return db.conn.Close()
}

func (db *PostgresDB) Ping() error {
	return db.conn.Ping()
}

// Patient Consent Management
type PatientConsent struct {
	ConsentID           uuid.UUID              `json:"consent_id"`
	PatientID          uuid.UUID              `json:"patient_id"`
	GrantorID          uuid.UUID              `json:"grantor_id"`
	GranteeID          uuid.UUID              `json:"grantee_id"`
	Purpose            string                 `json:"purpose"`
	DataTypes          []string               `json:"data_types"`
	Status             string                 `json:"status"`
	GrantedAt          time.Time              `json:"granted_at"`
	ExpiresAt          *time.Time             `json:"expires_at"`
	RevokedAt          *time.Time             `json:"revoked_at"`
	RevokedBy          *uuid.UUID             `json:"revoked_by"`
	ConsentDocumentPath *string               `json:"consent_document_path"`
	Metadata           map[string]interface{} `json:"metadata,omitempty"`
	CreatedAt          time.Time              `json:"created_at"`
	UpdatedAt          time.Time              `json:"updated_at"`
}

type CreatePatientConsentParams struct {
	PatientID           uuid.UUID
	GrantorID           uuid.UUID
	GranteeID           uuid.UUID
	Purpose             string
	DataTypes           []string
	ExpiresAt           *time.Time
	ConsentDocumentPath *string
}

func (db *PostgresDB) CreatePatientConsent(params CreatePatientConsentParams) (*PatientConsent, error) {
	consentID := uuid.New()
	now := time.Now()

	query := `
		INSERT INTO patient_consents (
			consent_id, patient_id, grantor_id, grantee_id, purpose, 
			data_types, expires_at, consent_document_path, status, 
			granted_at, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', $9, $10, $11)
		RETURNING consent_id, patient_id, grantor_id, grantee_id, purpose, 
				  data_types, status, granted_at, expires_at, revoked_at, 
				  revoked_by, consent_document_path, created_at, updated_at`

	var consent PatientConsent
	err := db.conn.QueryRow(
		query,
		consentID, params.PatientID, params.GrantorID, params.GranteeID,
		params.Purpose, pq.Array(params.DataTypes), params.ExpiresAt,
		params.ConsentDocumentPath, now, now, now,
	).Scan(
		&consent.ConsentID, &consent.PatientID, &consent.GrantorID,
		&consent.GranteeID, &consent.Purpose, pq.Array(&consent.DataTypes),
		&consent.Status, &consent.GrantedAt, &consent.ExpiresAt,
		&consent.RevokedAt, &consent.RevokedBy, &consent.ConsentDocumentPath,
		&consent.CreatedAt, &consent.UpdatedAt,
	)

	if err != nil {
		db.logger.Error("Failed to create patient consent", zap.Error(err))
		return nil, fmt.Errorf("failed to create patient consent: %w", err)
	}

	// Log consent creation for audit
	go db.logPHIAccess(LogPHIAccessParams{
		AccessorID:       params.GrantorID,
		PatientID:        params.PatientID,
		Purpose:          "patient_request",
		DataTypesAccessed: []string{"consent_creation"},
		ConsentID:        &consentID,
		AccessGranted:    true,
		IPAddress:        nil,
		UserAgent:        nil,
	})

	return &consent, nil
}

type RevokeConsentParams struct {
	ConsentID uuid.UUID
	RevokedBy uuid.UUID
	Reason    *string
}

func (db *PostgresDB) RevokeConsent(params RevokeConsentParams) (bool, error) {
	// First verify the user has authority to revoke this consent
	var patientID, grantorID uuid.UUID
	checkQuery := `
		SELECT patient_id, grantor_id 
		FROM patient_consents 
		WHERE consent_id = $1 AND status = 'active'`

	err := db.conn.QueryRow(checkQuery, params.ConsentID).Scan(&patientID, &grantorID)
	if err != nil {
		if err == sql.ErrNoRows {
			return false, fmt.Errorf("consent not found or already revoked")
		}
		return false, fmt.Errorf("failed to check consent authority: %w", err)
	}

	// Check if user has authority to revoke (patient or grantor)
	if params.RevokedBy != patientID && params.RevokedBy != grantorID {
		return false, nil // Not authorized
	}

	// Revoke the consent
	now := time.Now()
	updateQuery := `
		UPDATE patient_consents 
		SET status = 'revoked', revoked_at = $2, revoked_by = $3, updated_at = $4
		WHERE consent_id = $1 AND status = 'active'`

	result, err := db.conn.Exec(updateQuery, params.ConsentID, now, params.RevokedBy, now)
	if err != nil {
		return false, fmt.Errorf("failed to revoke consent: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("failed to get affected rows: %w", err)
	}

	if rowsAffected == 0 {
		return false, fmt.Errorf("consent not found or already revoked")
	}

	// Log consent revocation
	go db.logPHIAccess(LogPHIAccessParams{
		AccessorID:       params.RevokedBy,
		PatientID:        patientID,
		Purpose:          "patient_request",
		DataTypesAccessed: []string{"consent_revocation"},
		ConsentID:        &params.ConsentID,
		AccessGranted:    true,
		IPAddress:        nil,
		UserAgent:        nil,
	})

	return true, nil
}

type GetPatientConsentsParams struct {
	PatientID  uuid.UUID
	ActiveOnly bool
}

type GetPatientConsentParams struct {
	ConsentID uuid.UUID `json:"consent_id"`
	PatientID uuid.UUID `json:"patient_id"`
}

type GetAllPatientConsentsParams struct {
	PatientID uuid.UUID `json:"patient_id"`
	Limit     int       `json:"limit,omitempty"`
	Offset    int       `json:"offset,omitempty"`
}

type UpdateConsentStatusParams struct {
	ConsentID uuid.UUID `json:"consent_id"`
	Status    string    `json:"status"`
	UpdatedBy uuid.UUID `json:"updated_by"`
}

func (db *PostgresDB) GetPatientConsents(params GetPatientConsentsParams) ([]PatientConsent, error) {
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
			   data_types, status, granted_at, expires_at, revoked_at, 
			   revoked_by, consent_document_path, created_at, updated_at
		FROM patient_consents 
		WHERE patient_id = $1`

	args := []interface{}{params.PatientID}

	if params.ActiveOnly {
		query += ` AND status = 'active' 
				   AND (expires_at IS NULL OR expires_at > NOW()) 
				   AND revoked_at IS NULL`
	}

	query += ` ORDER BY created_at DESC`

	rows, err := db.conn.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to get patient consents: %w", err)
	}
	defer rows.Close()

	var consents []PatientConsent
	for rows.Next() {
		var consent PatientConsent
		err := rows.Scan(
			&consent.ConsentID, &consent.PatientID, &consent.GrantorID,
			&consent.GranteeID, &consent.Purpose, pq.Array(&consent.DataTypes),
			&consent.Status, &consent.GrantedAt, &consent.ExpiresAt,
			&consent.RevokedAt, &consent.RevokedBy, &consent.ConsentDocumentPath,
			&consent.CreatedAt, &consent.UpdatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan consent: %w", err)
		}
		consents = append(consents, consent)
	}

	return consents, nil
}

func (db *PostgresDB) GetPatientConsent(params GetPatientConsentParams) (*PatientConsent, error) {
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
		       data_types, granted_at, revoked_at, status, metadata
		FROM patient_consents 
		WHERE consent_id = $1 AND patient_id = $2
	`
	
	var consent PatientConsent
	var revokedAt sql.NullTime
	var metadata []byte
	
	err := db.conn.QueryRow(query, params.ConsentID, params.PatientID).Scan(
		&consent.ConsentID, &consent.PatientID, &consent.GrantorID, &consent.GranteeID,
		&consent.Purpose, pq.Array(&consent.DataTypes), &consent.GrantedAt,
		&revokedAt, &consent.Status, &metadata,
	)
	
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get patient consent: %w", err)
	}
	
	if revokedAt.Valid {
		consent.RevokedAt = &revokedAt.Time
	}
	
	if len(metadata) > 0 {
		if err := json.Unmarshal(metadata, &consent.Metadata); err != nil {
			return nil, fmt.Errorf("failed to unmarshal metadata: %w", err)
		}
	}
	
	return &consent, nil
}

func (db *PostgresDB) GetAllPatientConsents(params GetAllPatientConsentsParams) ([]PatientConsent, error) {
	limit := params.Limit
	if limit <= 0 {
		limit = 100
	}
	
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
		       data_types, granted_at, revoked_at, status, metadata
		FROM patient_consents 
		WHERE patient_id = $1
		ORDER BY granted_at DESC
		LIMIT $2 OFFSET $3
	`
	
	rows, err := db.conn.Query(query, params.PatientID, limit, params.Offset)
	if err != nil {
		return nil, fmt.Errorf("failed to query patient consents: %w", err)
	}
	defer rows.Close()
	
	var consents []PatientConsent
	for rows.Next() {
		var consent PatientConsent
		var revokedAt sql.NullTime
		var metadata []byte
		
		err := rows.Scan(
			&consent.ConsentID, &consent.PatientID, &consent.GrantorID, &consent.GranteeID,
			&consent.Purpose, pq.Array(&consent.DataTypes), &consent.GrantedAt,
			&revokedAt, &consent.Status, &metadata,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan consent row: %w", err)
		}
		
		if revokedAt.Valid {
			consent.RevokedAt = &revokedAt.Time
		}
		
		if len(metadata) > 0 {
			if err := json.Unmarshal(metadata, &consent.Metadata); err != nil {
				return nil, fmt.Errorf("failed to unmarshal metadata: %w", err)
			}
		}
		
		consents = append(consents, consent)
	}
	
	return consents, nil
}

func (db *PostgresDB) UpdateConsentStatus(params UpdateConsentStatusParams) (bool, error) {
	query := `
		UPDATE patient_consents 
		SET status = $2, updated_at = NOW() 
		WHERE consent_id = $1
	`
	
	result, err := db.conn.Exec(query, params.ConsentID, params.Status)
	if err != nil {
		return false, fmt.Errorf("failed to update consent status: %w", err)
	}
	
	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("failed to get rows affected: %w", err)
	}
	
	return rowsAffected > 0, nil
}

// Access Decision Logic
type CheckDataAccessParams struct {
	UserID                 uuid.UUID
	PatientID              uuid.UUID
	Purpose                string
	DataTypes              []string
	EmergencyJustification *string
}

type AccessDecision struct {
	Granted         bool
	Reason          string
	ConsentID       *uuid.UUID
	RelationshipID  *uuid.UUID
	EmergencyAccess bool
	Timestamp       time.Time
}

func (db *PostgresDB) checkDataAccess(params CheckDataAccessParams) (*AccessDecision, error) {
	now := time.Now()

	// 1. Self-access always allowed
	if params.UserID == params.PatientID {
		go db.logPHIAccess(LogPHIAccessParams{
			AccessorID:       params.UserID,
			PatientID:        params.PatientID,
			Purpose:          params.Purpose,
			DataTypesAccessed: params.DataTypes,
			AccessGranted:    true,
		})

		return &AccessDecision{
			Granted:         true,
			Reason:          "Self-access granted",
			ConsentID:       nil,
			RelationshipID:  nil,
			EmergencyAccess: false,
			Timestamp:       now,
		}, nil
	}

	// 2. Emergency access
	if params.Purpose == "emergency" && params.EmergencyJustification != nil {
		return db.handleEmergencyAccess(params, now)
	}

	// 3. Check for active consent
	consent, err := db.getActiveConsent(params.PatientID, params.UserID, params.Purpose, params.DataTypes)
	if err != nil {
		db.logger.Error("Failed to check consent", zap.Error(err))
		return &AccessDecision{
			Granted:   false,
			Reason:    "Failed to validate consent",
			Timestamp: now,
		}, err
	}

	if consent != nil {
		// Log successful access
		go db.logPHIAccess(LogPHIAccessParams{
			AccessorID:       params.UserID,
			PatientID:        params.PatientID,
			Purpose:          params.Purpose,
			DataTypesAccessed: params.DataTypes,
			ConsentID:        &consent.ConsentID,
			AccessGranted:    true,
		})

		return &AccessDecision{
			Granted:         true,
			Reason:          fmt.Sprintf("Access granted via patient consent for %s", params.Purpose),
			ConsentID:       &consent.ConsentID,
			RelationshipID:  nil,
			EmergencyAccess: false,
			Timestamp:       now,
		}, nil
	}

	// 4. Check treatment relationships
	if params.Purpose == "treatment" {
		if relationship, err := db.getActiveTreatmentRelationship(params.UserID, params.PatientID); err == nil && relationship != nil {
			go db.logPHIAccess(LogPHIAccessParams{
				AccessorID:       params.UserID,
				PatientID:        params.PatientID,
				Purpose:          params.Purpose,
				DataTypesAccessed: params.DataTypes,
				RelationshipID:   &relationship.RelationshipID,
				AccessGranted:    true,
			})

			return &AccessDecision{
				Granted:        true,
				Reason:         fmt.Sprintf("Access granted via treatment relationship (%s)", relationship.RelationshipType),
				RelationshipID: &relationship.RelationshipID,
				Timestamp:      now,
			}, nil
		}
	}

	// 5. Default deny with audit log
	denialReason := "No valid authorization found"
	go db.logPHIAccess(LogPHIAccessParams{
		AccessorID:       params.UserID,
		PatientID:        params.PatientID,
		Purpose:          params.Purpose,
		DataTypesAccessed: params.DataTypes,
		AccessGranted:    false,
		DenialReason:     &denialReason,
	})

	return &AccessDecision{
		Granted:   false,
		Reason:    "No valid authorization found for requested access",
		Timestamp: now,
	}, nil
}

func (db *PostgresDB) getActiveConsent(patientID, granteeID uuid.UUID, purpose string, dataTypes []string) (*PatientConsent, error) {
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
			   data_types, status, granted_at, expires_at, revoked_at, 
			   revoked_by, consent_document_path, created_at, updated_at
		FROM patient_consents 
		WHERE patient_id = $1 AND grantee_id = $2 AND purpose = $3 
			  AND status = 'active' AND revoked_at IS NULL
			  AND (expires_at IS NULL OR expires_at > NOW())`

	rows, err := db.conn.Query(query, patientID, granteeID, purpose)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var consent PatientConsent
		err := rows.Scan(
			&consent.ConsentID, &consent.PatientID, &consent.GrantorID,
			&consent.GranteeID, &consent.Purpose, pq.Array(&consent.DataTypes),
			&consent.Status, &consent.GrantedAt, &consent.ExpiresAt,
			&consent.RevokedAt, &consent.RevokedBy, &consent.ConsentDocumentPath,
			&consent.CreatedAt, &consent.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}

		// Check if consent covers all requested data types
		if db.coversDataTypes(consent.DataTypes, dataTypes) {
			return &consent, nil
		}
	}

	return nil, nil
}

// Treatment Relationships
type TreatmentRelationship struct {
	RelationshipID   uuid.UUID  `json:"relationship_id"`
	ProviderID       uuid.UUID  `json:"provider_id"`
	PatientID        uuid.UUID  `json:"patient_id"`
	RelationshipType string     `json:"relationship_type"`
	StartedAt        time.Time  `json:"started_at"`
	EndedAt          *time.Time `json:"ended_at"`
	AuthorizedBy     uuid.UUID  `json:"authorized_by"`
	IsActive         bool       `json:"is_active"`
	CreatedAt        time.Time  `json:"created_at"`
	UpdatedAt        time.Time  `json:"updated_at"`
}

func (db *PostgresDB) getActiveTreatmentRelationship(providerID, patientID uuid.UUID) (*TreatmentRelationship, error) {
	query := `
		SELECT relationship_id, provider_id, patient_id, relationship_type, 
			   started_at, ended_at, authorized_by, is_active, created_at, updated_at
		FROM treatment_relationships 
		WHERE provider_id = $1 AND patient_id = $2 AND is_active = true
			  AND (ended_at IS NULL OR ended_at > NOW())`

	var rel TreatmentRelationship
	err := db.conn.QueryRow(query, providerID, patientID).Scan(
		&rel.RelationshipID, &rel.ProviderID, &rel.PatientID,
		&rel.RelationshipType, &rel.StartedAt, &rel.EndedAt,
		&rel.AuthorizedBy, &rel.IsActive, &rel.CreatedAt, &rel.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	return &rel, nil
}

// Emergency Access
func (db *PostgresDB) handleEmergencyAccess(params CheckDataAccessParams, now time.Time) (*AccessDecision, error) {
	// Check if user role allows emergency access
	userRole, err := db.getUserRole(params.UserID)
	if err != nil {
		return nil, err
	}

	allowedRoles := []string{"care_staff", "care_manager", "admin"}
	roleAllowed := false
	for _, role := range allowedRoles {
		if userRole == role {
			roleAllowed = true
			break
		}
	}

	if !roleAllowed {
		return &AccessDecision{
			Granted:   false,
			Reason:    fmt.Sprintf("%s role not authorized for emergency access", userRole),
			Timestamp: now,
		}, nil
	}

	// Log emergency access
	emergencyID := uuid.New()
	go func() {
		_, err := db.conn.Exec(`
			INSERT INTO emergency_access_log 
			(access_id, accessor_id, patient_id, emergency_type, justification, data_accessed)
			VALUES ($1, $2, $3, 'break_glass_access', $4, $5)`,
			emergencyID, params.UserID, params.PatientID,
			*params.EmergencyJustification, pq.Array(params.DataTypes))

		if err != nil {
			db.logger.Error("Failed to log emergency access", zap.Error(err))
		}

		// Also log to PHI access log
		db.logPHIAccess(LogPHIAccessParams{
			AccessorID:       params.UserID,
			PatientID:        params.PatientID,
			Purpose:          params.Purpose,
			DataTypesAccessed: params.DataTypes,
			AccessGranted:    true,
		})
	}()

	return &AccessDecision{
		Granted:         true,
		Reason:          fmt.Sprintf("Emergency access granted - requires post-incident review (Log ID: %s)", emergencyID.String()),
		EmergencyAccess: true,
		Timestamp:       now,
	}, nil
}

// PHI Access Logging
type LogPHIAccessParams struct {
	AccessorID       uuid.UUID
	PatientID        uuid.UUID
	Purpose          string
	DataTypesAccessed []string
	ConsentID        *uuid.UUID
	RelationshipID   *uuid.UUID
	AccessGranted    bool
	DenialReason     *string
	IPAddress        *string
	UserAgent        *string
}

func (db *PostgresDB) logPHIAccess(params LogPHIAccessParams) error {
	logID := uuid.New()
	_, err := db.conn.Exec(`
		INSERT INTO phi_access_log 
		(log_id, accessor_id, patient_id, purpose, data_types_accessed, 
		 consent_id, relationship_id, access_granted, denial_reason, 
		 ip_address, user_agent)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
		logID, params.AccessorID, params.PatientID, params.Purpose,
		pq.Array(params.DataTypesAccessed), params.ConsentID,
		params.RelationshipID, params.AccessGranted, params.DenialReason,
		params.IPAddress, params.UserAgent)

	if err != nil {
		db.logger.Error("Failed to log PHI access", zap.Error(err))
		return err
	}

	return nil
}

// Audit Logging
type LogConsentActionParams struct {
	Action    string
	ConsentID uuid.UUID
	UserID    uuid.UUID
	Details   string
}

func (db *PostgresDB) LogConsentAction(params LogConsentActionParams) error {
	// This would log to a dedicated audit table
	db.logger.Info("Consent action logged",
		zap.String("action", params.Action),
		zap.String("consent_id", params.ConsentID.String()),
		zap.String("user_id", params.UserID.String()),
		zap.String("details", params.Details))
	return nil
}

// Helper functions
func (db *PostgresDB) getUserRole(userID uuid.UUID) (string, error) {
	var role string
	err := db.conn.QueryRow(
		"SELECT healthcare_role FROM users WHERE user_id = $1",
		userID).Scan(&role)
	return role, err
}

func (db *PostgresDB) coversDataTypes(consentDataTypes, requestedDataTypes []string) bool {
	// Check if consent covers all requested data types
	for _, requested := range requestedDataTypes {
		found := false
		for _, consented := range consentDataTypes {
			if consented == requested {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}