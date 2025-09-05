// Package database provides PostgreSQL database connection and management
package database

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/google/uuid"
	
	"auth-rbac-service/models"
	"auth-rbac-service/rbac"
	"encoding/json"
)

// Manager handles all database operations
type Manager struct {
	pool *pgxpool.Pool
}

// NewManager creates a new database manager with connection pooling
func NewManager(databaseURL string) (*Manager, error) {
	config, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse database URL: %w", err)
	}

	// Configure connection pool
	config.MaxConns = 30
	config.MinConns = 5
	config.MaxConnLifetime = time.Hour
	config.MaxConnIdleTime = time.Minute * 30
	config.HealthCheckPeriod = time.Minute * 5

	pool, err := pgxpool.NewWithConfig(context.Background(), config)
	if err != nil {
		return nil, fmt.Errorf("failed to create connection pool: %w", err)
	}

	return &Manager{pool: pool}, nil
}

// Close closes the database connection pool
func (m *Manager) Close() {
	if m.pool != nil {
		m.pool.Close()
	}
}

// Ping checks database connectivity
func (m *Manager) Ping(ctx context.Context) error {
	return m.pool.Ping(ctx)
}

// CreateUser creates a new user in the database
func (m *Manager) CreateUser(ctx context.Context, user *models.CreateUser, passwordHash string) (*models.User, error) {
	query := `
		INSERT INTO users (
			id, email, password_hash, first_name, last_name, phone,
			healthcare_role, subscription_plan, is_active, is_verified,
			is_superuser, created_at, updated_at
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
		) RETURNING id, email, first_name, last_name, phone, healthcare_role,
		  subscription_plan, is_active, is_verified, is_superuser, created_at, updated_at`

	userID := uuid.New()
	now := time.Now()

	var dbUser models.User
	err := m.pool.QueryRow(ctx, query,
		userID,
		user.Email,
		passwordHash,
		user.FirstName,
		user.LastName,
		user.Phone,
		string(user.HealthcareRole),
		user.SubscriptionPlan,
		true,  // is_active
		false, // is_verified (would be set after email verification)
		false, // is_superuser
		now,
		now,
	).Scan(
		&dbUser.ID,
		&dbUser.Email,
		&dbUser.FirstName,
		&dbUser.LastName,
		&dbUser.Phone,
		&dbUser.HealthcareRole,
		&dbUser.SubscriptionPlan,
		&dbUser.IsActive,
		&dbUser.IsVerified,
		&dbUser.IsSuperuser,
		&dbUser.CreatedAt,
		&dbUser.UpdatedAt,
	)

	if err != nil {
		return nil, fmt.Errorf("failed to create user: %w", err)
	}

	return &dbUser, nil
}

// GetUserByEmail retrieves a user by email address
func (m *Manager) GetUserByEmail(ctx context.Context, email string) (*models.User, error) {
	query := `
		SELECT id, email, password_hash, first_name, last_name, phone,
		       healthcare_role, subscription_plan, is_active, is_verified,
		       is_superuser, last_login, created_at, updated_at
		FROM users WHERE email = $1`

	var user models.User
	err := m.pool.QueryRow(ctx, query, email).Scan(
		&user.ID,
		&user.Email,
		&user.PasswordHash,
		&user.FirstName,
		&user.LastName,
		&user.Phone,
		&user.HealthcareRole,
		&user.SubscriptionPlan,
		&user.IsActive,
		&user.IsVerified,
		&user.IsSuperuser,
		&user.LastLoginAt,
		&user.CreatedAt,
		&user.UpdatedAt,
	)

	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("failed to get user by email: %w", err)
	}

	return &user, nil
}

// GetUserByID retrieves a user by ID
func (m *Manager) GetUserByID(ctx context.Context, userID uuid.UUID) (*models.User, error) {
	query := `
		SELECT id, email, password_hash, first_name, last_name, phone,
		       healthcare_role, subscription_plan, is_active, is_verified,
		       is_superuser, last_login, created_at, updated_at
		FROM users WHERE id = $1`

	var user models.User
	err := m.pool.QueryRow(ctx, query, userID).Scan(
		&user.ID,
		&user.Email,
		&user.PasswordHash,
		&user.FirstName,
		&user.LastName,
		&user.Phone,
		&user.HealthcareRole,
		&user.SubscriptionPlan,
		&user.IsActive,
		&user.IsVerified,
		&user.IsSuperuser,
		&user.LastLoginAt,
		&user.CreatedAt,
		&user.UpdatedAt,
	)

	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("failed to get user by ID: %w", err)
	}

	return &user, nil
}

// UpdateUserLastLogin updates the user's last login timestamp
func (m *Manager) UpdateUserLastLogin(ctx context.Context, userID uuid.UUID) error {
	query := `UPDATE users SET last_login = $1, updated_at = $1 WHERE id = $2`
	
	now := time.Now()
	_, err := m.pool.Exec(ctx, query, now, userID)
	if err != nil {
		return fmt.Errorf("failed to update last login: %w", err)
	}

	return nil
}

// CreateSession creates a new user session
func (m *Manager) CreateSession(ctx context.Context, session *models.Session) error {
	query := `
		INSERT INTO sessions (
			id, user_id, expires_at, created_at, last_activity,
			ip_address, user_agent, is_active
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`

	_, err := m.pool.Exec(ctx, query,
		session.ID,
		session.UserID,
		session.ExpiresAt,
		session.CreatedAt,
		session.LastActivity,
		session.IPAddress,
		session.UserAgent,
		session.IsActive,
	)

	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	return nil
}

// GetSessionByID retrieves a session by ID
func (m *Manager) GetSessionByID(ctx context.Context, sessionID string) (*models.Session, error) {
	query := `
		SELECT id, user_id, expires_at, created_at, last_activity,
		       ip_address, user_agent, is_active
		FROM sessions WHERE id = $1`

	var session models.Session
	err := m.pool.QueryRow(ctx, query, sessionID).Scan(
		&session.ID,
		&session.UserID,
		&session.ExpiresAt,
		&session.CreatedAt,
		&session.LastActivity,
		&session.IPAddress,
		&session.UserAgent,
		&session.IsActive,
	)

	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("session not found")
		}
		return nil, fmt.Errorf("failed to get session: %w", err)
	}

	return &session, nil
}

// UpdateSessionActivity updates the session's last activity timestamp
func (m *Manager) UpdateSessionActivity(ctx context.Context, sessionID string) error {
	query := `UPDATE sessions SET last_activity = $1 WHERE id = $2`
	
	_, err := m.pool.Exec(ctx, query, time.Now(), sessionID)
	if err != nil {
		return fmt.Errorf("failed to update session activity: %w", err)
	}

	return nil
}

// DeactivateSession deactivates a session
func (m *Manager) DeactivateSession(ctx context.Context, sessionID string) error {
	query := `UPDATE sessions SET is_active = false WHERE id = $1`
	
	_, err := m.pool.Exec(ctx, query, sessionID)
	if err != nil {
		return fmt.Errorf("failed to deactivate session: %w", err)
	}

	return nil
}

// GetUserSessions retrieves all active sessions for a user
func (m *Manager) GetUserSessions(ctx context.Context, userID uuid.UUID) ([]*models.Session, error) {
	query := `
		SELECT id, user_id, expires_at, created_at, last_activity,
		       ip_address, user_agent, is_active
		FROM sessions WHERE user_id = $1 AND is_active = true
		ORDER BY created_at DESC`

	rows, err := m.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get user sessions: %w", err)
	}
	defer rows.Close()

	var sessions []*models.Session
	for rows.Next() {
		var session models.Session
		err := rows.Scan(
			&session.ID,
			&session.UserID,
			&session.ExpiresAt,
			&session.CreatedAt,
			&session.LastActivity,
			&session.IPAddress,
			&session.UserAgent,
			&session.IsActive,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan session: %w", err)
		}
		sessions = append(sessions, &session)
	}

	return sessions, nil
}

// LogAuditEvent logs an audit event for HIPAA compliance
func (m *Manager) LogAuditEvent(ctx context.Context, event *models.AuditLog) error {
	query := `
		INSERT INTO audit_logs (
			id, user_id, action, resource_type, resource_id,
			old_values, new_values, ip_address, user_agent,
			access_purpose, justification, created_at
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)`

	eventID := uuid.New()
	
	// Convert map to JSON for database storage
	var oldValuesJSON, newValuesJSON []byte
	var err error
	
	if event.OldValues != nil {
		oldValuesJSON, err = json.Marshal(event.OldValues)
		if err != nil {
			return fmt.Errorf("failed to marshal old values: %w", err)
		}
	}
	
	if event.NewValues != nil {
		newValuesJSON, err = json.Marshal(event.NewValues)
		if err != nil {
			return fmt.Errorf("failed to marshal new values: %w", err)
		}
	}
	
	_, err = m.pool.Exec(ctx, query,
		eventID,
		event.UserID,
		event.Action,
		event.ResourceType,
		event.ResourceID,
		oldValuesJSON,
		newValuesJSON,
		event.IPAddress,
		event.UserAgent,
		string(event.AccessPurpose),
		event.Justification,
		event.CreatedAt,
	)

	if err != nil {
		return fmt.Errorf("failed to log audit event: %w", err)
	}

	return nil
}

// GetAuditLogs retrieves audit logs with filtering and pagination
func (m *Manager) GetAuditLogs(ctx context.Context, userID *uuid.UUID, action string, limit, offset int) ([]*models.AuditLog, error) {
	query := `
		SELECT id, user_id, action, resource_type, resource_id,
		       old_values, new_values, ip_address, user_agent,
		       access_purpose, justification, created_at
		FROM audit_logs`
	
	var args []interface{}
	var conditions []string
	
	if userID != nil {
		conditions = append(conditions, fmt.Sprintf("user_id = $%d", len(args)+1))
		args = append(args, *userID)
	}
	
	if action != "" {
		conditions = append(conditions, fmt.Sprintf("action = $%d", len(args)+1))
		args = append(args, action)
	}
	
	if len(conditions) > 0 {
		query += " WHERE " + fmt.Sprintf("%v", conditions[0])
		for i := 1; i < len(conditions); i++ {
			query += " AND " + conditions[i]
		}
	}
	
	query += fmt.Sprintf(" ORDER BY created_at DESC LIMIT $%d OFFSET $%d", len(args)+1, len(args)+2)
	args = append(args, limit, offset)

	rows, err := m.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to get audit logs: %w", err)
	}
	defer rows.Close()

	var logs []*models.AuditLog
	for rows.Next() {
		var log models.AuditLog
		var accessPurposeStr string
		var oldValuesJSON, newValuesJSON []byte
		
		err := rows.Scan(
			&log.ID,
			&log.UserID,
			&log.Action,
			&log.ResourceType,
			&log.ResourceID,
			&oldValuesJSON,
			&newValuesJSON,
			&log.IPAddress,
			&log.UserAgent,
			&accessPurposeStr,
			&log.Justification,
			&log.CreatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan audit log: %w", err)
		}
		
		// Unmarshal JSON values
		if oldValuesJSON != nil {
			if err := json.Unmarshal(oldValuesJSON, &log.OldValues); err != nil {
				log.OldValues = nil // Fallback to nil if unmarshal fails
			}
		}
		
		if newValuesJSON != nil {
			if err := json.Unmarshal(newValuesJSON, &log.NewValues); err != nil {
				log.NewValues = nil // Fallback to nil if unmarshal fails
			}
		}
		
		// Convert string back to AccessPurpose enum
		if purpose, err := rbac.GetAccessPurposeByString(accessPurposeStr); err == nil {
			log.AccessPurpose = purpose
		}
		
		logs = append(logs, &log)
	}

	return logs, nil
}