// Package main provides multi-database connection management for API Gateway
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/gocql/gocql"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// DatabaseManager manages all database connections
type DatabaseManager struct {
	PostgresPool *pgxpool.Pool
	RedisClient  *redis.Client
	MongoClient  *mongo.Client
	ScyllaSession *gocql.Session
	
	ctx           context.Context
	config        *ServiceConfig
	healthStatus  map[string]*DatabaseHealth
	healthMutex   sync.RWMutex
}

// NewDatabaseManager creates a new database manager with all connections
func NewDatabaseManager(config *ServiceConfig) *DatabaseManager {
	ctx := context.Background()
	
	dm := &DatabaseManager{
		ctx:          ctx,
		config:       config,
		healthStatus: make(map[string]*DatabaseHealth),
	}

	// Initialize all database connections
	// Database connections will be initialized via Connect() method

	return dm
}

// Connect initializes all database connections
func (dm *DatabaseManager) Connect() error {
	// Connect to PostgreSQL
	if err := dm.connectToPostgreSQL(); err != nil {
		log.Printf("❌ PostgreSQL connection failed: %v", err)
	}

	// Connect to Redis
	if err := dm.connectToRedis(); err != nil {
		log.Printf("❌ Redis connection failed: %v", err)
	}

	// Connect to MongoDB
	if err := dm.connectToMongoDB(); err != nil {
		log.Printf("❌ MongoDB connection failed: %v", err)
	}

	// Connect to ScyllaDB
	if err := dm.connectToScyllaDB(); err != nil {
		log.Printf("❌ ScyllaDB connection failed: %v", err)
	}

	return nil
}

// Close closes all database connections
func (dm *DatabaseManager) Close() {
	if dm.PostgresPool != nil {
		dm.PostgresPool.Close()
	}
	if dm.RedisClient != nil {
		dm.RedisClient.Close()
	}
	if dm.MongoClient != nil {
		dm.MongoClient.Disconnect(dm.ctx)
	}
	if dm.ScyllaSession != nil {
		dm.ScyllaSession.Close()
	}
}

// connectToPostgreSQL establishes PostgreSQL connection pool
func (dm *DatabaseManager) connectToPostgreSQL() error {
	config, err := pgxpool.ParseConfig(dm.config.PostgresURL)
	if err != nil {
		return fmt.Errorf("failed to parse PostgreSQL URL: %w", err)
	}

	// Configure connection pool
	config.MaxConns = 25
	config.MinConns = 5
	config.MaxConnLifetime = time.Hour
	config.MaxConnIdleTime = time.Minute * 30
	config.HealthCheckPeriod = time.Minute

	pool, err := pgxpool.NewWithConfig(dm.ctx, config)
	if err != nil {
		return fmt.Errorf("failed to create PostgreSQL pool: %w", err)
	}

	// Test connection
	if err := pool.Ping(dm.ctx); err != nil {
		pool.Close()
		return fmt.Errorf("failed to ping PostgreSQL: %w", err)
	}

	dm.PostgresPool = pool
	log.Println("✅ PostgreSQL connection established")
	return nil
}

// connectToRedis establishes Redis connection
func (dm *DatabaseManager) connectToRedis() error {
	opts, err := redis.ParseURL(dm.config.RedisURL)
	if err != nil {
		return fmt.Errorf("failed to parse Redis URL: %w", err)
	}

	// Configure Redis client
	opts.PoolSize = 20
	opts.MinIdleConns = 5
	opts.PoolTimeout = 30 * time.Second
	opts.ConnMaxIdleTime = 300 * time.Second
	opts.ConnMaxLifetime = 3600 * time.Second

	client := redis.NewClient(opts)

	// Test connection
	_, err = client.Ping(dm.ctx).Result()
	if err != nil {
		client.Close()
		return fmt.Errorf("failed to ping Redis: %w", err)
	}

	dm.RedisClient = client
	log.Println("✅ Redis connection established")
	return nil
}

// connectToMongoDB establishes MongoDB connection
func (dm *DatabaseManager) connectToMongoDB() error {
	clientOptions := options.Client().ApplyURI(dm.config.MongoURL)
	
	// Configure connection pool
	maxPoolSize := uint64(20)
	minPoolSize := uint64(5)
	maxConnIdleTime := time.Duration(300) * time.Second
	
	clientOptions.SetMaxPoolSize(maxPoolSize)
	clientOptions.SetMinPoolSize(minPoolSize)
	clientOptions.SetMaxConnIdleTime(maxConnIdleTime)
	clientOptions.SetServerSelectionTimeout(10 * time.Second)
	
	client, err := mongo.Connect(dm.ctx, clientOptions)
	if err != nil {
		return fmt.Errorf("failed to connect to MongoDB: %w", err)
	}

	// Test connection
	if err := client.Ping(dm.ctx, nil); err != nil {
		client.Disconnect(dm.ctx)
		return fmt.Errorf("failed to ping MongoDB: %w", err)
	}

	dm.MongoClient = client
	log.Println("✅ MongoDB connection established")
	return nil
}

// connectToScyllaDB establishes ScyllaDB connection
func (dm *DatabaseManager) connectToScyllaDB() error {
	if len(dm.config.ScyllaHosts) == 0 {
		return fmt.Errorf("no ScyllaDB hosts configured")
	}

	cluster := gocql.NewCluster(dm.config.ScyllaHosts...)
	cluster.Keyspace = "chatbot_keyspace"
	cluster.Consistency = gocql.Quorum
	cluster.Timeout = 10 * time.Second
	cluster.ConnectTimeout = 10 * time.Second
	cluster.NumConns = 4
	cluster.HostFilter = gocql.WhiteListHostFilter(dm.config.ScyllaHosts...)

	session, err := cluster.CreateSession()
	if err != nil {
		return fmt.Errorf("failed to create ScyllaDB session: %w", err)
	}

	dm.ScyllaSession = session
	log.Println("✅ ScyllaDB connection established")
	return nil
}

// Session management operations

// CreateSession creates a new user session in Redis
func (dm *DatabaseManager) CreateSession(sessionID, userID, ipAddress, userAgent string, metadata map[string]interface{}) error {
	if dm.RedisClient == nil {
		return fmt.Errorf("Redis not available")
	}

	session := Session{
		ID:           sessionID,
		UserID:       userID,
		IPAddress:    ipAddress,
		UserAgent:    userAgent,
		CreatedAt:    time.Now().UTC(),
		LastActivity: time.Now().UTC(),
		IsActive:     true,
		RequestCount: 0,
		Metadata:     metadata,
		ExpiresAt:    time.Now().UTC().Add(time.Duration(dm.config.SessionTTL) * time.Second),
	}

	sessionData, err := json.Marshal(session)
	if err != nil {
		return fmt.Errorf("failed to marshal session: %w", err)
	}

	key := fmt.Sprintf("session:%s", sessionID)
	err = dm.RedisClient.SetEx(dm.ctx, key, sessionData, time.Duration(dm.config.SessionTTL)*time.Second).Err()
	if err != nil {
		return fmt.Errorf("failed to store session in Redis: %w", err)
	}

	// Store user-session mapping if user is authenticated
	if userID != "" {
		userSessionKey := fmt.Sprintf("user_sessions:%s", userID)
		dm.RedisClient.SAdd(dm.ctx, userSessionKey, sessionID)
		dm.RedisClient.Expire(dm.ctx, userSessionKey, time.Duration(dm.config.SessionTTL)*time.Second)
	}

	return nil
}

// GetSession retrieves session from Redis
func (dm *DatabaseManager) GetSession(sessionID string) (*Session, error) {
	if dm.RedisClient == nil {
		return nil, fmt.Errorf("Redis not available")
	}

	key := fmt.Sprintf("session:%s", sessionID)
	sessionData, err := dm.RedisClient.Get(dm.ctx, key).Result()
	if err == redis.Nil {
		return nil, fmt.Errorf("session not found")
	} else if err != nil {
		return nil, fmt.Errorf("failed to get session from Redis: %w", err)
	}

	var session Session
	if err := json.Unmarshal([]byte(sessionData), &session); err != nil {
		return nil, fmt.Errorf("failed to unmarshal session: %w", err)
	}

	// Update last activity
	session.LastActivity = time.Now().UTC()
	session.RequestCount++

	// Save updated session
	updatedData, _ := json.Marshal(session)
	dm.RedisClient.SetEx(dm.ctx, key, updatedData, time.Duration(dm.config.SessionTTL)*time.Second)

	return &session, nil
}

// DeleteSession removes session from Redis
func (dm *DatabaseManager) DeleteSession(sessionID string) error {
	if dm.RedisClient == nil {
		return fmt.Errorf("Redis not available")
	}

	key := fmt.Sprintf("session:%s", sessionID)
	return dm.RedisClient.Del(dm.ctx, key).Err()
}

// GetSessionStats returns session statistics
func (dm *DatabaseManager) GetSessionStats() (*SessionStats, error) {
	if dm.RedisClient == nil {
		return nil, fmt.Errorf("Redis not available")
	}

	// Get all session keys
	keys, err := dm.RedisClient.Keys(dm.ctx, "session:*").Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get session keys: %w", err)
	}

	stats := &SessionStats{
		TotalSessions:  len(keys),
		ActiveSessions: 0,
		RequestCount:   0,
		CreatedAt:      time.Now().UTC(),
	}

	if len(keys) == 0 {
		return stats, nil
	}

	// Sample sessions for detailed stats
	var totalDuration time.Duration
	var totalRequests int
	
	for i, key := range keys {
		if i >= 100 { // Limit sampling to avoid performance issues
			break
		}

		sessionData, err := dm.RedisClient.Get(dm.ctx, key).Result()
		if err != nil {
			continue
		}

		var session Session
		if json.Unmarshal([]byte(sessionData), &session) != nil {
			continue
		}

		if session.IsActive && time.Now().Before(session.ExpiresAt) {
			stats.ActiveSessions++
		}

		duration := session.LastActivity.Sub(session.CreatedAt)
		totalDuration += duration
		totalRequests += session.RequestCount
	}

	if stats.TotalSessions > 0 {
		stats.AverageDuration = totalDuration.Minutes() / float64(len(keys))
		stats.RequestCount = totalRequests
		stats.MemoryUsage = int64(len(keys) * 1024) // Rough estimate
	}

	return stats, nil
}

// User authentication operations

// GetUserByEmail retrieves user by email from PostgreSQL
func (dm *DatabaseManager) GetUserByEmail(email string) (*User, error) {
	if dm.PostgresPool == nil {
		return nil, fmt.Errorf("PostgreSQL not available")
	}

	query := `
		SELECT id, email, first_name, last_name, phone, is_active, is_superuser, 
		       created_at, updated_at, last_login_at
		FROM users WHERE email = $1 AND is_active = true
	`

	var user User
	var lastLoginAt sql.NullTime

	err := dm.PostgresPool.QueryRow(dm.ctx, query, email).Scan(
		&user.ID, &user.Email, &user.FirstName, &user.LastName, &user.Phone,
		&user.IsActive, &user.IsSuperuser, &user.CreatedAt, &user.UpdatedAt, &lastLoginAt,
	)

	if err == pgx.ErrNoRows {
		return nil, fmt.Errorf("user not found")
	} else if err != nil {
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	if lastLoginAt.Valid {
		user.LastLoginAt = &lastLoginAt.Time
	}

	return &user, nil
}

// UpdateUserLastLogin updates user's last login timestamp
func (dm *DatabaseManager) UpdateUserLastLogin(userID uuid.UUID) error {
	if dm.PostgresPool == nil {
		return fmt.Errorf("PostgreSQL not available")
	}

	query := "UPDATE users SET last_login_at = $1, updated_at = $1 WHERE id = $2"
	_, err := dm.PostgresPool.Exec(dm.ctx, query, time.Now().UTC(), userID)
	return err
}

// Analytics and conversation operations

// StoreConversationMessage stores message in ScyllaDB
func (dm *DatabaseManager) StoreConversationMessage(message *ConversationMessage) error {
	if dm.ScyllaSession == nil {
		return fmt.Errorf("ScyllaDB not available")
	}

	query := `
		INSERT INTO conversation_messages (id, session_id, user_id, content, type, timestamp, metadata)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`

	metadataJSON, _ := json.Marshal(message.Metadata)

	return dm.ScyllaSession.Query(query,
		message.ID, message.SessionID, message.UserID, message.Content,
		message.Type, message.Timestamp, string(metadataJSON),
	).Exec()
}

// GetConversationHistory retrieves conversation from ScyllaDB
func (dm *DatabaseManager) GetConversationHistory(sessionID string, limit int) (*ConversationHistory, error) {
	if dm.ScyllaSession == nil {
		return nil, fmt.Errorf("ScyllaDB not available")
	}

	query := `
		SELECT id, session_id, user_id, content, type, timestamp, metadata
		FROM conversation_messages
		WHERE session_id = ? 
		ORDER BY timestamp DESC
		LIMIT ?
	`

	iter := dm.ScyllaSession.Query(query, sessionID, limit).Iter()
	defer iter.Close()

	var messages []ConversationMessage
	var id, userID, content, msgType, metadataStr string
	var timestamp time.Time

	for iter.Scan(&id, &sessionID, &userID, &content, &msgType, &timestamp, &metadataStr) {
		message := ConversationMessage{
			ID:        id,
			SessionID: sessionID,
			UserID:    userID,
			Content:   content,
			Type:      msgType,
			Timestamp: timestamp,
		}

		if metadataStr != "" {
			json.Unmarshal([]byte(metadataStr), &message.Metadata)
		}

		messages = append(messages, message)
	}

	if err := iter.Close(); err != nil {
		return nil, fmt.Errorf("failed to scan conversation history: %w", err)
	}

	// Reverse to get chronological order
	for i := len(messages)/2 - 1; i >= 0; i-- {
		opp := len(messages) - 1 - i
		messages[i], messages[opp] = messages[opp], messages[i]
	}

	var startTime, lastActivity time.Time
	if len(messages) > 0 {
		startTime = messages[0].Timestamp
		lastActivity = messages[len(messages)-1].Timestamp
	}

	history := &ConversationHistory{
		SessionID:     sessionID,
		Messages:      messages,
		TotalMessages: len(messages),
		StartTime:     startTime,
		LastActivity:  lastActivity,
		Duration:      lastActivity.Sub(startTime),
	}

	if len(messages) > 0 {
		history.UserID = messages[0].UserID
	}

	return history, nil
}

// Rate limiting operations

// CheckRateLimit checks if user/IP is within rate limits
func (dm *DatabaseManager) CheckRateLimit(key string, limit int, window time.Duration) (bool, *RateLimitInfo, error) {
	if dm.RedisClient == nil {
		return true, nil, fmt.Errorf("Redis not available")
	}

	now := time.Now()
	windowStart := now.Truncate(window)
	redisKey := fmt.Sprintf("rate_limit:%s:%d", key, windowStart.Unix())

	current, err := dm.RedisClient.Incr(dm.ctx, redisKey).Result()
	if err != nil {
		return true, nil, err
	}

	if current == 1 {
		dm.RedisClient.Expire(dm.ctx, redisKey, window)
	}

	info := &RateLimitInfo{
		Limit:     limit,
		Remaining: max(0, limit-int(current)),
		Reset:     windowStart.Add(window),
		Window:    window.String(),
	}

	if current > int64(limit) {
		info.RetryAfter = int(time.Until(info.Reset).Seconds())
		return false, info, nil
	}

	return true, info, nil
}

// Caching operations

// CacheSet stores data in Redis with TTL
func (dm *DatabaseManager) CacheSet(key string, data interface{}, ttl time.Duration) error {
	if dm.RedisClient == nil {
		return fmt.Errorf("Redis not available")
	}

	jsonData, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("failed to marshal cache data: %w", err)
	}

	return dm.RedisClient.SetEx(dm.ctx, key, jsonData, ttl).Err()
}

// CacheGet retrieves data from Redis
func (dm *DatabaseManager) CacheGet(key string, dest interface{}) error {
	if dm.RedisClient == nil {
		return fmt.Errorf("Redis not available")
	}

	data, err := dm.RedisClient.Get(dm.ctx, key).Result()
	if err == redis.Nil {
		return fmt.Errorf("cache miss")
	} else if err != nil {
		return fmt.Errorf("failed to get cache data: %w", err)
	}

	return json.Unmarshal([]byte(data), dest)
}

// Health monitoring

// monitorHealth continuously monitors database health
func (dm *DatabaseManager) monitorHealth() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			dm.updateHealthStatus()
		case <-dm.ctx.Done():
			return
		}
	}
}

// updateHealthStatus checks and updates health status for all databases
func (dm *DatabaseManager) updateHealthStatus() {
	dm.healthMutex.Lock()
	defer dm.healthMutex.Unlock()

	// Check PostgreSQL
	dm.checkPostgreSQLHealth()
	
	// Check Redis
	dm.checkRedisHealth()
	
	// Check MongoDB
	dm.checkMongoDBHealth()
	
	// Check ScyllaDB
	dm.checkScyllaDBHealth()
}

// checkPostgreSQLHealth checks PostgreSQL connection health
func (dm *DatabaseManager) checkPostgreSQLHealth() {
	start := time.Now()
	status := "healthy"
	var errorCount int

	if dm.PostgresPool == nil {
		status = "unhealthy"
		errorCount = 1
	} else {
		if err := dm.PostgresPool.Ping(dm.ctx); err != nil {
			status = "unhealthy"
			errorCount = 1
		}
	}

	dm.healthStatus["postgresql"] = &DatabaseHealth{
		Status:       status,
		ResponseTime: time.Since(start),
		LastCheck:    time.Now().UTC(),
		ErrorCount:   errorCount,
		URL:          dm.config.PostgresURL,
	}

	if dm.PostgresPool != nil {
		dm.healthStatus["postgresql"].Connections = int(dm.PostgresPool.Stat().TotalConns())
	}
}

// checkRedisHealth checks Redis connection health
func (dm *DatabaseManager) checkRedisHealth() {
	start := time.Now()
	status := "healthy"
	var errorCount int

	if dm.RedisClient == nil {
		status = "unhealthy"
		errorCount = 1
	} else {
		if _, err := dm.RedisClient.Ping(dm.ctx).Result(); err != nil {
			status = "unhealthy"
			errorCount = 1
		}
	}

	dm.healthStatus["redis"] = &DatabaseHealth{
		Status:       status,
		ResponseTime: time.Since(start),
		LastCheck:    time.Now().UTC(),
		ErrorCount:   errorCount,
		URL:          dm.config.RedisURL,
	}
}

// checkMongoDBHealth checks MongoDB connection health
func (dm *DatabaseManager) checkMongoDBHealth() {
	start := time.Now()
	status := "healthy"
	var errorCount int

	if dm.MongoClient == nil {
		status = "unhealthy"
		errorCount = 1
	} else {
		if err := dm.MongoClient.Ping(dm.ctx, nil); err != nil {
			status = "unhealthy"
			errorCount = 1
		}
	}

	dm.healthStatus["mongodb"] = &DatabaseHealth{
		Status:       status,
		ResponseTime: time.Since(start),
		LastCheck:    time.Now().UTC(),
		ErrorCount:   errorCount,
		URL:          dm.config.MongoURL,
	}
}

// checkScyllaDBHealth checks ScyllaDB connection health
func (dm *DatabaseManager) checkScyllaDBHealth() {
	start := time.Now()
	status := "healthy"
	var errorCount int

	if dm.ScyllaSession == nil {
		status = "unhealthy"
		errorCount = 1
	} else {
		if err := dm.ScyllaSession.Query("SELECT now() FROM system.local").Exec(); err != nil {
			status = "unhealthy"
			errorCount = 1
		}
	}

	dm.healthStatus["scylladb"] = &DatabaseHealth{
		Status:       status,
		ResponseTime: time.Since(start),
		LastCheck:    time.Now().UTC(),
		ErrorCount:   errorCount,
		URL:          strings.Join(dm.config.ScyllaHosts, ","),
	}
}

// GetHealthStatus returns current health status for all databases
func (dm *DatabaseManager) GetHealthStatus() map[string]DatabaseHealth {
	dm.healthMutex.RLock()
	defer dm.healthMutex.RUnlock()

	result := make(map[string]DatabaseHealth)
	for name, health := range dm.healthStatus {
		if health != nil {
			result[name] = *health
		}
	}

	return result
}

// Cleanup closes all database connections (duplicate removed)

// Helper functions

// parseMongoURI extracts database name from MongoDB URI
func parseMongoURI(uri string) string {
	u, err := url.Parse(uri)
	if err != nil {
		return "unknown"
	}
	return strings.TrimPrefix(u.Path, "/")
}

// max returns the maximum of two integers
func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// User authentication methods

// AuthenticateUser validates user credentials
func (dm *DatabaseManager) AuthenticateUser(email, password string) (*User, error) {
	if dm.PostgresPool == nil {
		return nil, fmt.Errorf("database not available")
	}

	var user User
	var hashedPassword string
	
	query := `
		SELECT id, email, first_name, last_name, phone, is_active, is_superuser, 
			   created_at, updated_at, last_login_at, password_hash
		FROM users 
		WHERE email = $1 AND is_active = true
	`
	
	err := dm.PostgresPool.QueryRow(dm.ctx, query, email).Scan(
		&user.ID, &user.Email, &user.FirstName, &user.LastName, 
		&user.Phone, &user.IsActive, &user.IsSuperuser,
		&user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt,
		&hashedPassword,
	)
	
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("database error: %w", err)
	}

	// In a real implementation, you would verify the password hash
	// For now, we'll do a simple comparison (NOT SECURE - use bcrypt in production)
	if password != hashedPassword {
		return nil, fmt.Errorf("invalid password")
	}

	return &user, nil
}

// CreateUser creates a new user account
func (dm *DatabaseManager) CreateUser(req *RegisterRequest) (*User, error) {
	if dm.PostgresPool == nil {
		return nil, fmt.Errorf("database not available")
	}

	// Check if user already exists
	var exists bool
	err := dm.PostgresPool.QueryRow(dm.ctx, "SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)", req.Email).Scan(&exists)
	if err != nil {
		return nil, fmt.Errorf("database error: %w", err)
	}
	if exists {
		return nil, fmt.Errorf("user already exists")
	}

	// Create new user
	userID := uuid.New()
	now := time.Now()
	
	query := `
		INSERT INTO users (id, email, first_name, last_name, phone, password_hash, 
						   is_active, is_superuser, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`
	
	// In production, hash the password with bcrypt
	hashedPassword := req.Password // NOT SECURE - use bcrypt
	
	_, err = dm.PostgresPool.Exec(dm.ctx, query,
		userID, req.Email, req.FirstName, req.LastName, req.Phone,
		hashedPassword, true, false, now, now,
	)
	
	if err != nil {
		return nil, fmt.Errorf("failed to create user: %w", err)
	}

	user := &User{
		ID:          userID,
		Email:       req.Email,
		FirstName:   req.FirstName,
		LastName:    req.LastName,
		Phone:       req.Phone,
		IsActive:    true,
		IsSuperuser: false,
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	return user, nil
}

// GetUser retrieves user by ID
func (dm *DatabaseManager) GetUser(userID string) (*User, error) {
	if dm.PostgresPool == nil {
		return nil, fmt.Errorf("database not available")
	}

	var user User
	query := `
		SELECT id, email, first_name, last_name, phone, is_active, is_superuser,
			   created_at, updated_at, last_login_at
		FROM users 
		WHERE id = $1 AND is_active = true
	`
	
	err := dm.PostgresPool.QueryRow(dm.ctx, query, userID).Scan(
		&user.ID, &user.Email, &user.FirstName, &user.LastName,
		&user.Phone, &user.IsActive, &user.IsSuperuser,
		&user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt,
	)
	
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("database error: %w", err)
	}

	return &user, nil
}

// UpdateLastLogin updates user's last login timestamp
func (dm *DatabaseManager) UpdateLastLogin(userID string) error {
	if dm.PostgresPool == nil {
		return fmt.Errorf("database not available")
	}

	query := `UPDATE users SET last_login_at = $1, updated_at = $1 WHERE id = $2`
	_, err := dm.PostgresPool.Exec(dm.ctx, query, time.Now(), userID)
	return err
}

// Session management methods

// CreateSession duplicate method removed

// GetSession duplicate method removed

// InvalidateSession removes session from storage
func (dm *DatabaseManager) InvalidateSession(sessionID string) error {
	if dm.RedisClient == nil {
		return fmt.Errorf("Redis not available")
	}

	key := fmt.Sprintf("session:%s", sessionID)
	return dm.RedisClient.Del(dm.ctx, key).Err()
}

// GetSessionStats duplicate method removed

// CleanupExpiredSessions removes expired sessions
func (dm *DatabaseManager) CleanupExpiredSessions() error {
	if dm.RedisClient == nil {
		return fmt.Errorf("Redis not available")
	}

	// Redis automatically expires keys with TTL, so this is mainly for logging
	keys, err := dm.RedisClient.Keys(dm.ctx, "session:*").Result()
	if err != nil {
		return fmt.Errorf("failed to get session keys: %w", err)
	}

	log.Printf("Session cleanup: %d active sessions", len(keys))
	return nil
}

// StoreAnalyticsEvent stores analytics event
func (dm *DatabaseManager) StoreAnalyticsEvent(event *AnalyticsEvent) error {
	if dm.MongoClient == nil {
		return fmt.Errorf("MongoDB not available")
	}

	collection := dm.MongoClient.Database(parseMongoURI(dm.config.MongoURL)).Collection("analytics_events")
	_, err := collection.InsertOne(dm.ctx, event)
	if err != nil {
		return fmt.Errorf("failed to store analytics event: %w", err)
	}

	return nil
}