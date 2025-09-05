package database

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	"github.com/lib/pq"
	_ "github.com/lib/pq"
	"github.com/MultiDB-Chatbot/microservices/shared/models"
)

type DatabaseManager struct {
	db *sql.DB
}

func NewDatabaseManager(databaseURL string) (*DatabaseManager, error) {
	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Configure connection pool
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	// Test connection
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	log.Println("✅ PostgreSQL database connected successfully")
	return &DatabaseManager{db: db}, nil
}

func (dm *DatabaseManager) Close() error {
	if dm.db != nil {
		return dm.db.Close()
	}
	return nil
}

func (dm *DatabaseManager) Ping() error {
	return dm.db.Ping()
}

// Session management methods
func (dm *DatabaseManager) CreateSession(req *models.SessionCreateRequest) (*models.Session, error) {
	userID, err := uuid.Parse(req.UserID)
	if err != nil {
		return nil, fmt.Errorf("invalid user ID: %w", err)
	}

	session := &models.Session{
		SessionID:    uuid.New(),
		UserID:       userID,
		SessionToken: generateSessionToken(),
		CreatedAt:    time.Now(),
		ExpiresAt:    time.Now().Add(24 * time.Hour),
		IsActive:     true,
		LastActivity: time.Now(),
		IPAddress:    &req.IPAddress,
		UserAgent:    &req.UserAgent,
		DeviceInfo:   req.DeviceInfo,
	}

	query := `
		INSERT INTO auth.sessions (session_id, user_id, session_token, created_at, expires_at, is_active, last_activity, ip_address, user_agent, device_info)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`

	_, err = dm.db.Exec(query, session.SessionID, session.UserID, session.SessionToken, 
		session.CreatedAt, session.ExpiresAt, session.IsActive, session.LastActivity,
		session.IPAddress, session.UserAgent, session.DeviceInfo)
	
	if err != nil {
		return nil, fmt.Errorf("failed to create session: %w", err)
	}

	return session, nil
}

func (dm *DatabaseManager) GetUserByID(userID uuid.UUID) (*models.User, error) {
	user := &models.User{}
	query := `SELECT user_id, username, email, full_name, healthcare_role, organization_id, 
		is_active, last_login_at, created_at, updated_at FROM auth.users WHERE user_id = $1`
	
	row := dm.db.QueryRow(query, userID)
	err := row.Scan(&user.UserID, &user.Username, &user.Email, &user.FullName, 
		&user.HealthcareRole, &user.OrganizationID, &user.IsActive, 
		&user.LastLoginAt, &user.CreatedAt, &user.UpdatedAt)
	
	if err != nil {
		return nil, fmt.Errorf("failed to get user: %w", err)
	}
	
	return user, nil
}

func generateSessionToken() string {
	return uuid.New().String() + "-" + fmt.Sprintf("%d", time.Now().Unix())
}

// Consent Management Methods
func (dm *DatabaseManager) CreatePatientConsent(params models.CreatePatientConsentParams) (*models.PatientConsent, error) {
	consentID := uuid.New()
	now := time.Now()

	query := `
		INSERT INTO compliance.patient_consents (
			consent_id, patient_id, grantor_id, grantee_id, purpose, 
			data_types, expires_at, consent_document_path, status, 
			granted_at, created_at, updated_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', $9, $10, $11)
		RETURNING consent_id, patient_id, grantor_id, grantee_id, purpose, 
				  data_types, status, granted_at, expires_at, revoked_at, 
				  revoked_by, consent_document_path, created_at, updated_at`

	var consent models.PatientConsent
	err := dm.db.QueryRow(
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
		return nil, fmt.Errorf("failed to create patient consent: %w", err)
	}

	return &consent, nil
}

func (dm *DatabaseManager) RevokeConsent(params models.RevokeConsentParams) (bool, error) {
	// First verify the user has authority to revoke this consent
	var patientID, grantorID uuid.UUID
	checkQuery := `
		SELECT patient_id, grantor_id 
		FROM compliance.patient_consents 
		WHERE consent_id = $1 AND status = 'active'`

	err := dm.db.QueryRow(checkQuery, params.ConsentID).Scan(&patientID, &grantorID)
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
		UPDATE compliance.patient_consents 
		SET status = 'revoked', revoked_at = $2, revoked_by = $3, updated_at = $4
		WHERE consent_id = $1 AND status = 'active'`

	result, err := dm.db.Exec(updateQuery, params.ConsentID, now, params.RevokedBy, now)
	if err != nil {
		return false, fmt.Errorf("failed to revoke consent: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("failed to get affected rows: %w", err)
	}

	return rowsAffected > 0, nil
}

func (dm *DatabaseManager) GetPatientConsents(params models.GetPatientConsentsParams) ([]models.PatientConsent, error) {
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
			   data_types, status, granted_at, expires_at, revoked_at, 
			   revoked_by, consent_document_path, created_at, updated_at
		FROM compliance.patient_consents 
		WHERE patient_id = $1`

	args := []interface{}{params.PatientID}

	if params.ActiveOnly {
		query += ` AND status = 'active' 
				   AND (expires_at IS NULL OR expires_at > NOW()) 
				   AND revoked_at IS NULL`
	}

	query += ` ORDER BY created_at DESC`

	rows, err := dm.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to get patient consents: %w", err)
	}
	defer rows.Close()

	var consents []models.PatientConsent
	for rows.Next() {
		var consent models.PatientConsent
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

func (dm *DatabaseManager) GetPatientConsent(params models.GetPatientConsentParams) (*models.PatientConsent, error) {
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
		       data_types, status, granted_at, expires_at, revoked_at, 
		       revoked_by, consent_document_path, created_at, updated_at
		FROM compliance.patient_consents 
		WHERE consent_id = $1 AND patient_id = $2`
	
	var consent models.PatientConsent
	err := dm.db.QueryRow(query, params.ConsentID, params.PatientID).Scan(
		&consent.ConsentID, &consent.PatientID, &consent.GrantorID, &consent.GranteeID,
		&consent.Purpose, pq.Array(&consent.DataTypes), &consent.Status, 
		&consent.GrantedAt, &consent.ExpiresAt, &consent.RevokedAt, &consent.RevokedBy,
		&consent.ConsentDocumentPath, &consent.CreatedAt, &consent.UpdatedAt,
	)
	
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get patient consent: %w", err)
	}
	
	return &consent, nil
}

func (dm *DatabaseManager) GetAllPatientConsents(params models.GetAllPatientConsentsParams) ([]models.PatientConsent, error) {
	limit := params.Limit
	if limit <= 0 {
		limit = 100
	}
	
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
		       data_types, status, granted_at, expires_at, revoked_at, 
		       revoked_by, consent_document_path, created_at, updated_at
		FROM compliance.patient_consents 
		WHERE patient_id = $1
		ORDER BY granted_at DESC
		LIMIT $2 OFFSET $3`
	
	rows, err := dm.db.Query(query, params.PatientID, limit, params.Offset)
	if err != nil {
		return nil, fmt.Errorf("failed to query patient consents: %w", err)
	}
	defer rows.Close()
	
	var consents []models.PatientConsent
	for rows.Next() {
		var consent models.PatientConsent
		err := rows.Scan(
			&consent.ConsentID, &consent.PatientID, &consent.GrantorID, &consent.GranteeID,
			&consent.Purpose, pq.Array(&consent.DataTypes), &consent.Status,
			&consent.GrantedAt, &consent.ExpiresAt, &consent.RevokedAt, &consent.RevokedBy,
			&consent.ConsentDocumentPath, &consent.CreatedAt, &consent.UpdatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan consent row: %w", err)
		}
		consents = append(consents, consent)
	}
	
	return consents, nil
}

func (dm *DatabaseManager) UpdateConsentStatus(params models.UpdateConsentStatusParams) (bool, error) {
	query := `
		UPDATE compliance.patient_consents 
		SET status = $2, updated_at = NOW() 
		WHERE consent_id = $1`
	
	result, err := dm.db.Exec(query, params.ConsentID, params.Status)
	if err != nil {
		return false, fmt.Errorf("failed to update consent status: %w", err)
	}
	
	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("failed to get rows affected: %w", err)
	}
	
	return rowsAffected > 0, nil
}

func (dm *DatabaseManager) CheckDataAccess(params models.CheckDataAccessParams) (*models.AccessDecision, error) {
	now := time.Now()

	// 1. Self-access always allowed
	if params.UserID == params.PatientID {
		return &models.AccessDecision{
			Granted:         true,
			Reason:          "Self-access granted",
			ConsentID:       nil,
			RelationshipID:  nil,
			EmergencyAccess: false,
			Timestamp:       now,
		}, nil
	}

	// 2. Emergency access
	if params.Purpose == models.AccessPurposeEmergency && params.EmergencyJustification != nil {
		// Check if user role allows emergency access
		user, err := dm.GetUserByID(params.UserID)
		if err != nil {
			return nil, err
		}

		allowedRoles := []models.HealthcareRole{
			models.RoleCareStaff, 
			models.RoleCareManager, 
			models.RoleAdmin,
		}
		
		roleAllowed := false
		for _, role := range allowedRoles {
			if user.HealthcareRole == role {
				roleAllowed = true
				break
			}
		}

		if roleAllowed {
			return &models.AccessDecision{
				Granted:         true,
				Reason:          "Emergency access granted",
				EmergencyAccess: true,
				Timestamp:       now,
			}, nil
		}
	}

	// 3. Check for active consent
	consent, err := dm.getActiveConsent(params.PatientID, params.UserID, params.Purpose, params.DataTypes)
	if err != nil {
		return &models.AccessDecision{
			Granted:   false,
			Reason:    "Failed to validate consent",
			Timestamp: now,
		}, err
	}

	if consent != nil {
		return &models.AccessDecision{
			Granted:         true,
			Reason:          fmt.Sprintf("Access granted via patient consent for %s", params.Purpose),
			ConsentID:       &consent.ConsentID,
			RelationshipID:  nil,
			EmergencyAccess: false,
			Timestamp:       now,
		}, nil
	}

	// 4. Default deny
	return &models.AccessDecision{
		Granted:   false,
		Reason:    "No valid authorization found for requested access",
		Timestamp: now,
	}, nil
}

func (dm *DatabaseManager) getActiveConsent(patientID, granteeID uuid.UUID, purpose models.AccessPurpose, dataTypes []string) (*models.PatientConsent, error) {
	query := `
		SELECT consent_id, patient_id, grantor_id, grantee_id, purpose, 
			   data_types, status, granted_at, expires_at, revoked_at, 
			   revoked_by, consent_document_path, created_at, updated_at
		FROM compliance.patient_consents 
		WHERE patient_id = $1 AND grantee_id = $2 AND purpose = $3 
			  AND status = 'active' AND revoked_at IS NULL
			  AND (expires_at IS NULL OR expires_at > NOW())`

	rows, err := dm.db.Query(query, patientID, granteeID, purpose)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var consent models.PatientConsent
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
		if dm.coversDataTypes(consent.DataTypes, dataTypes) {
			return &consent, nil
		}
	}

	return nil, nil
}

func (dm *DatabaseManager) coversDataTypes(consentDataTypes, requestedDataTypes []string) bool {
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

func (dm *DatabaseManager) LogConsentAction(params models.LogConsentActionParams) error {
	// Simple audit logging
	log.Printf("Consent action: %s, ConsentID: %s, UserID: %s, Details: %s",
		params.Action, params.ConsentID.String(), params.UserID.String(), params.Details)
	return nil
}