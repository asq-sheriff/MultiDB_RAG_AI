package main

import (
	"context"
	"fmt"
	"time"

	"github.com/gocql/gocql"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.uber.org/zap"
)

// DatabaseManager manages all database connections
// DatabaseInterface defines the interface for database operations
type DatabaseInterface interface {
	HealthCheck(ctx context.Context) DatabaseHealth
	CreateSession(ctx context.Context, session *Session) error
	GetSession(ctx context.Context, sessionID uuid.UUID) (*Session, error)
	EndSession(ctx context.Context, sessionID uuid.UUID) error
	CreateMessage(ctx context.Context, message *Message) error
	StoreConversationMessage(ctx context.Context, msg *ConversationMessage) error
	GetConversationHistory(ctx context.Context, sessionID gocql.UUID, limit int, startTime *time.Time) ([]ConversationMessage, error)
	StoreFeedback(ctx context.Context, feedback *UserFeedback) error
	StoreMessageEmotion(ctx context.Context, emotion *MessageEmotion) error
	SearchKnowledgeBase(ctx context.Context, embedding []float64, limit int) ([]KnowledgeDocument, error)
	CacheSession(ctx context.Context, sessionCache *SessionCache) error
	GetCachedSession(ctx context.Context, sessionID string) (*SessionCache, error)
	IncrementAnalyticsCounter(ctx context.Context, metric string, tags map[string]string) error
	// Cache operations
	GetFromCache(ctx context.Context, key string) (string, error)
	SetToCache(ctx context.Context, key string, value string, ttl time.Duration) error
	Close()
}

type DatabaseManager struct {
	postgres *pgxpool.Pool
	scylla   *gocql.Session
	mongo    *mongo.Client
	redis    *redis.Client
	logger   *zap.Logger
}

// Config represents database configuration
type DatabaseConfig struct {
	PostgresURL      string
	ScyllaHosts      []string
	ScyllaKeyspace   string
	MongoURL         string
	MongoDatabase    string
	RedisURL         string
	RedisDB          int
	MaxConnections   int
	ConnectionTimeout time.Duration
}

// NewDatabaseManager creates a new database manager with all connections
func NewDatabaseManager(config DatabaseConfig, logger *zap.Logger) (*DatabaseManager, error) {
	dm := &DatabaseManager{
		logger: logger,
	}

	// Initialize PostgreSQL connection
	if err := dm.initPostgreSQL(config); err != nil {
		return nil, fmt.Errorf("failed to initialize PostgreSQL: %w", err)
	}

	// Initialize ScyllaDB connection
	if err := dm.initScyllaDB(config); err != nil {
		return nil, fmt.Errorf("failed to initialize ScyllaDB: %w", err)
	}

	// Initialize MongoDB connection
	if err := dm.initMongoDB(config); err != nil {
		return nil, fmt.Errorf("failed to initialize MongoDB: %w", err)
	}

	// Initialize Redis connection
	if err := dm.initRedis(config); err != nil {
		return nil, fmt.Errorf("failed to initialize Redis: %w", err)
	}

	logger.Info("Database manager initialized successfully",
		zap.String("postgres", "connected"),
		zap.String("scylla", "connected"),
		zap.String("mongo", "connected"),
		zap.String("redis", "connected"))

	return dm, nil
}

// ========================================
// PostgreSQL Management
// ========================================

func (dm *DatabaseManager) initPostgreSQL(config DatabaseConfig) error {
	poolConfig, err := pgxpool.ParseConfig(config.PostgresURL)
	if err != nil {
		return fmt.Errorf("failed to parse PostgreSQL URL: %w", err)
	}

	// Configure connection pool
	poolConfig.MaxConns = int32(config.MaxConnections)
	poolConfig.MinConns = 5
	poolConfig.MaxConnLifetime = time.Hour
	poolConfig.MaxConnIdleTime = time.Minute * 30
	poolConfig.HealthCheckPeriod = time.Minute * 1

	ctx, cancel := context.WithTimeout(context.Background(), config.ConnectionTimeout)
	defer cancel()

	pool, err := pgxpool.NewWithConfig(ctx, poolConfig)
	if err != nil {
		return fmt.Errorf("failed to create PostgreSQL pool: %w", err)
	}

	// Test the connection
	if err := pool.Ping(ctx); err != nil {
		return fmt.Errorf("failed to ping PostgreSQL: %w", err)
	}

	dm.postgres = pool
	dm.logger.Info("PostgreSQL connection established")
	return nil
}

// ========================================
// ScyllaDB Management
// ========================================

func (dm *DatabaseManager) initScyllaDB(config DatabaseConfig) error {
	if len(config.ScyllaHosts) == 0 {
		dm.logger.Warn("ScyllaDB hosts not configured, skipping ScyllaDB initialization")
		return nil
	}
	
	cluster := gocql.NewCluster(config.ScyllaHosts...)
	cluster.Keyspace = config.ScyllaKeyspace
	cluster.Timeout = 15 * time.Second
	cluster.ConnectTimeout = 30 * time.Second
	cluster.Consistency = gocql.Quorum
	cluster.NumConns = 4
	cluster.SocketKeepalive = time.Second * 30

	// Configure retry policy
	cluster.RetryPolicy = &gocql.ExponentialBackoffRetryPolicy{
		Min:        time.Millisecond * 100,
		Max:        time.Second * 2,
		NumRetries: 3,
	}

	// Enable host filtering and token aware routing
	cluster.PoolConfig.HostSelectionPolicy = gocql.TokenAwareHostPolicy(gocql.RoundRobinHostPolicy())

	session, err := cluster.CreateSession()
	if err != nil {
		dm.logger.Error("Failed to connect to ScyllaDB - DETAILED ERROR", 
			zap.Error(err),
			zap.Strings("hosts", config.ScyllaHosts),
			zap.String("keyspace", config.ScyllaKeyspace),
			zap.String("consistency", "Quorum"),
		)
		dm.scylla = nil
		return fmt.Errorf("ScyllaDB connection failed: %w", err)
	}

	dm.scylla = session
	dm.logger.Info("ScyllaDB connection established", zap.Strings("hosts", config.ScyllaHosts))
	return nil
}

// ========================================
// MongoDB Management
// ========================================

func (dm *DatabaseManager) initMongoDB(config DatabaseConfig) error {
	clientOptions := options.Client().
		ApplyURI(config.MongoURL).
		SetMaxPoolSize(uint64(config.MaxConnections)).
		SetMinPoolSize(5).
		SetMaxConnIdleTime(30 * time.Minute).
		SetServerSelectionTimeout(config.ConnectionTimeout).
		SetDirect(true)

	ctx, cancel := context.WithTimeout(context.Background(), config.ConnectionTimeout)
	defer cancel()

	client, err := mongo.Connect(ctx, clientOptions)
	if err != nil {
		return fmt.Errorf("failed to connect to MongoDB: %w", err)
	}

	// Test the connection
	if err := client.Ping(ctx, nil); err != nil {
		return fmt.Errorf("failed to ping MongoDB: %w", err)
	}

	dm.mongo = client
	dm.logger.Info("MongoDB connection established")
	return nil
}

// ========================================
// Redis Management
// ========================================

func (dm *DatabaseManager) initRedis(config DatabaseConfig) error {
	// Parse Redis URL for production-ready connection
	var opts *redis.Options
	var err error
	
	if config.RedisURL != "" {
		opts, err = redis.ParseURL(config.RedisURL)
		if err != nil {
			return fmt.Errorf("failed to parse Redis URL: %w", err)
		}
		// Override with config values if specified
		if config.RedisDB != 0 {
			opts.DB = config.RedisDB
		}
		if config.MaxConnections > 0 {
			opts.PoolSize = config.MaxConnections
		}
	} else {
		// Fallback to manual configuration
		opts = &redis.Options{
			Addr:         "localhost:6379",
			DB:           config.RedisDB,
			Password:     "",
			PoolSize:     config.MaxConnections,
		}
	}
	
	// Set production-ready timeouts
	opts.MinIdleConns = 10
	opts.PoolTimeout = 30 * time.Second
	opts.ReadTimeout = 5 * time.Second
	opts.WriteTimeout = 5 * time.Second
	opts.DialTimeout = 5 * time.Second
	
	rdb := redis.NewClient(opts)

	ctx, cancel := context.WithTimeout(context.Background(), config.ConnectionTimeout)
	defer cancel()

	// Test the connection
	if err := rdb.Ping(ctx).Err(); err != nil {
		return fmt.Errorf("failed to ping Redis: %w", err)
	}

	dm.redis = rdb
	dm.logger.Info("Redis connection established")
	return nil
}

// ========================================
// Health Check Methods
// ========================================

// HealthCheck checks the health of all database connections
func (dm *DatabaseManager) HealthCheck(ctx context.Context) DatabaseHealth {
	health := DatabaseHealth{}

	// Check PostgreSQL
	if dm.postgres != nil {
		if err := dm.postgres.Ping(ctx); err == nil {
			health.PostgreSQL = true
		}
	}

	// Check ScyllaDB
	if dm.scylla != nil {
		// Simple query to test connection
		if err := dm.scylla.Query("SELECT now() FROM system.local").WithContext(ctx).Exec(); err == nil {
			health.ScyllaDB = true
		} else {
			dm.logger.Error("ScyllaDB health check failed", zap.Error(err))
		}
	} else {
		dm.logger.Warn("ScyllaDB session is nil during health check")
	}

	// Check MongoDB
	if dm.mongo != nil {
		if err := dm.mongo.Ping(ctx, nil); err == nil {
			health.MongoDB = true
		}
	}

	// Check Redis
	if dm.redis != nil {
		if err := dm.redis.Ping(ctx).Err(); err == nil {
			health.Redis = true
		}
	}

	return health
}

// ========================================
// Session Management (PostgreSQL)
// ========================================

// CreateSession creates a new chat session in PostgreSQL
func (dm *DatabaseManager) CreateSession(ctx context.Context, session *Session) error {
	query := `
		INSERT INTO chat_sessions (session_id, user_id, channel, started_at, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6)`
	
	_, err := dm.postgres.Exec(ctx, query, 
		session.SessionID, session.UserID, session.Channel, 
		session.StartedAt, session.CreatedAt, session.UpdatedAt)
	
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}

	dm.logger.Info("Session created",
		zap.String("session_id", session.SessionID.String()),
		zap.String("user_id", session.UserID.String()))
	
	return nil
}

// GetSession retrieves a session from PostgreSQL
func (dm *DatabaseManager) GetSession(ctx context.Context, sessionID uuid.UUID) (*Session, error) {
	query := `
		SELECT session_id, user_id, channel, started_at, ended_at, created_at, updated_at
		FROM chat_sessions WHERE session_id = $1`
	
	var session Session
	var endedAt *time.Time
	
	err := dm.postgres.QueryRow(ctx, query, sessionID).Scan(
		&session.SessionID, &session.UserID, &session.Channel,
		&session.StartedAt, &endedAt, &session.CreatedAt, &session.UpdatedAt)
	
	if err != nil {
		return nil, fmt.Errorf("failed to get session: %w", err)
	}
	
	session.EndedAt = endedAt
	return &session, nil
}

// EndSession marks a session as ended in PostgreSQL
func (dm *DatabaseManager) EndSession(ctx context.Context, sessionID uuid.UUID) error {
	query := `
		UPDATE chat_sessions 
		SET ended_at = $1, updated_at = $2 
		WHERE session_id = $3`
	
	now := time.Now()
	_, err := dm.postgres.Exec(ctx, query, now, now, sessionID)
	
	if err != nil {
		return fmt.Errorf("failed to end session: %w", err)
	}
	
	dm.logger.Info("Session ended", zap.String("session_id", sessionID.String()))
	return nil
}

// ========================================
// Message Management (PostgreSQL)
// ========================================

// CreateMessage creates a new message in PostgreSQL
func (dm *DatabaseManager) CreateMessage(ctx context.Context, message *Message) error {
	query := `
		INSERT INTO chat_messages (message_id, session_id, user_id, role, content, content_hash, created_at, updated_at, pii_present)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`
	
	_, err := dm.postgres.Exec(ctx, query,
		message.MessageID, message.SessionID, message.UserID, string(message.Role),
		message.Content, message.ContentHash, message.CreatedAt, message.UpdatedAt, message.PIIPresent)
	
	if err != nil {
		return fmt.Errorf("failed to create message: %w", err)
	}

	dm.logger.Debug("Message created",
		zap.String("message_id", message.MessageID.String()),
		zap.String("session_id", message.SessionID.String()),
		zap.String("role", string(message.Role)))
	
	return nil
}

// StoreMessageEmotion stores emotion analysis for a message in PostgreSQL
func (dm *DatabaseManager) StoreMessageEmotion(ctx context.Context, emotion *MessageEmotion) error {
	query := `
		INSERT INTO message_emotions (message_id, valence, arousal, label, confidence, prosody_features, inferred_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (message_id) DO UPDATE SET
			valence = EXCLUDED.valence,
			arousal = EXCLUDED.arousal,
			label = EXCLUDED.label,
			confidence = EXCLUDED.confidence,
			prosody_features = EXCLUDED.prosody_features,
			inferred_at = EXCLUDED.inferred_at`
	
	_, err := dm.postgres.Exec(ctx, query,
		emotion.MessageID, emotion.Valence, emotion.Arousal, string(emotion.Label),
		emotion.Confidence, emotion.ProsodyFeatures, emotion.InferredAt)
	
	if err != nil {
		return fmt.Errorf("failed to store message emotion: %w", err)
	}
	
	return nil
}

// ========================================
// Conversation Storage (ScyllaDB)
// ========================================

// StoreConversationMessage stores a message in ScyllaDB for high-performance access
func (dm *DatabaseManager) StoreConversationMessage(ctx context.Context, msg *ConversationMessage) error {
	if dm.scylla == nil {
		dm.logger.Debug("ScyllaDB not available, skipping conversation message storage")
		return nil // Graceful degradation
	}
	
	query := `INSERT INTO conversation_history 
		(session_id, timestamp, message_id, actor, message, confidence, cached, 
		 response_time_ms, route_used, generation_used, metadata) 
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`

	err := dm.scylla.Query(query,
		msg.SessionID, msg.Timestamp, msg.MessageID, msg.Actor, msg.Message,
		msg.Confidence, msg.Cached, msg.ResponseTimeMs, msg.RouteUsed,
		msg.GenerationUsed, msg.Metadata).WithContext(ctx).Exec()

	if err != nil {
		return fmt.Errorf("failed to store conversation message: %w", err)
	}

	dm.logger.Debug("Conversation message stored",
		zap.String("session_id", msg.SessionID.String()),
		zap.String("actor", msg.Actor))

	return nil
}

// GetConversationHistory retrieves conversation history from ScyllaDB
func (dm *DatabaseManager) GetConversationHistory(ctx context.Context, sessionID gocql.UUID, limit int, startTime *time.Time) ([]ConversationMessage, error) {
	if dm.scylla == nil {
		dm.logger.Debug("ScyllaDB not available, returning empty conversation history")
		return []ConversationMessage{}, nil // Graceful degradation
	}
	
	var query string
	var args []interface{}

	if startTime != nil {
		query = `SELECT session_id, timestamp, message_id, actor, message, confidence, cached,
			response_time_ms, route_used, generation_used, metadata
			FROM conversation_history 
			WHERE session_id = ? AND timestamp >= ?
			ORDER BY timestamp ASC LIMIT ?`
		args = []interface{}{sessionID, *startTime, limit}
	} else {
		query = `SELECT session_id, timestamp, message_id, actor, message, confidence, cached,
			response_time_ms, route_used, generation_used, metadata
			FROM conversation_history 
			WHERE session_id = ?
			ORDER BY timestamp ASC LIMIT ?`
		args = []interface{}{sessionID, limit}
	}

	iter := dm.scylla.Query(query, args...).WithContext(ctx).Iter()
	defer iter.Close()

	var messages []ConversationMessage
	var msg ConversationMessage

	for iter.Scan(&msg.SessionID, &msg.Timestamp, &msg.MessageID, &msg.Actor,
		&msg.Message, &msg.Confidence, &msg.Cached, &msg.ResponseTimeMs,
		&msg.RouteUsed, &msg.GenerationUsed, &msg.Metadata) {
		
		messages = append(messages, msg)
	}

	if err := iter.Close(); err != nil {
		return nil, fmt.Errorf("failed to iterate conversation history: %w", err)
	}

	return messages, nil
}

// StoreFeedback stores user feedback in ScyllaDB
func (dm *DatabaseManager) StoreFeedback(ctx context.Context, feedback *UserFeedback) error {
	if dm.scylla == nil {
		dm.logger.Debug("ScyllaDB not available, skipping feedback storage")
		return nil // Graceful degradation
	}
	
	query := `INSERT INTO user_feedback 
		(feedback_id, session_id, message_id, user_id, rating, feedback, category, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`

	err := dm.scylla.Query(query,
		feedback.FeedbackID, feedback.SessionID, feedback.MessageID, feedback.UserID,
		feedback.Rating, feedback.Feedback, feedback.Category, feedback.CreatedAt).
		WithContext(ctx).Exec()

	if err != nil {
		return fmt.Errorf("failed to store feedback: %w", err)
	}

	dm.logger.Info("Feedback stored",
		zap.String("feedback_id", feedback.FeedbackID.String()),
		zap.Int("rating", feedback.Rating))

	return nil
}

// ========================================
// Session Caching (Redis)
// ========================================

// CacheSession caches session data in Redis
func (dm *DatabaseManager) CacheSession(ctx context.Context, sessionCache *SessionCache) error {
	key := fmt.Sprintf("session:%s", sessionCache.SessionID)
	
	err := dm.redis.Set(ctx, key, sessionCache, time.Hour*24).Err()
	if err != nil {
		return fmt.Errorf("failed to cache session: %w", err)
	}
	
	return nil
}

// GetCachedSession retrieves cached session data from Redis
func (dm *DatabaseManager) GetCachedSession(ctx context.Context, sessionID string) (*SessionCache, error) {
	key := fmt.Sprintf("session:%s", sessionID)
	
	var session SessionCache
	err := dm.redis.Get(ctx, key).Scan(&session)
	if err != nil {
		if err == redis.Nil {
			return nil, nil // Session not cached
		}
		return nil, fmt.Errorf("failed to get cached session: %w", err)
	}
	
	return &session, nil
}

// IncrementAnalyticsCounter increments an analytics counter in Redis
func (dm *DatabaseManager) IncrementAnalyticsCounter(ctx context.Context, metric string, tags map[string]string) error {
	key := fmt.Sprintf("analytics:counter:%s", metric)
	
	// Add tags to key if provided
	if len(tags) > 0 {
		for k, v := range tags {
			key += fmt.Sprintf(":%s=%s", k, v)
		}
	}
	
	err := dm.redis.Incr(ctx, key).Err()
	if err != nil {
		return fmt.Errorf("failed to increment analytics counter: %w", err)
	}
	
	// Set expiration for cleanup
	dm.redis.Expire(ctx, key, time.Hour*24*7)
	
	return nil
}

// ========================================
// Knowledge Base (MongoDB)
// ========================================

// SearchKnowledgeBase performs vector search in MongoDB
func (dm *DatabaseManager) SearchKnowledgeBase(ctx context.Context, embedding []float64, limit int) ([]KnowledgeDocument, error) {
	collection := dm.mongo.Database("chatbot_app").Collection("knowledge_documents")
	
	// Vector search pipeline (Atlas Vector Search)
	pipeline := []interface{}{
		map[string]interface{}{
			"$vectorSearch": map[string]interface{}{
				"index": "vector_index",
				"path":  "embedding_vector",
				"queryVector": embedding,
				"numCandidates": limit * 10,
				"limit": limit,
			},
		},
		map[string]interface{}{
			"$project": map[string]interface{}{
				"title": 1,
				"content": 1,
				"document_type": 1,
				"care_context": 1,
				"keywords": 1,
				"metadata": 1,
				"created_at": 1,
				"score": map[string]interface{}{"$meta": "vectorSearchScore"},
			},
		},
	}
	
	cursor, err := collection.Aggregate(ctx, pipeline)
	if err != nil {
		return nil, fmt.Errorf("failed to search knowledge base: %w", err)
	}
	defer cursor.Close(ctx)
	
	var documents []KnowledgeDocument
	if err := cursor.All(ctx, &documents); err != nil {
		return nil, fmt.Errorf("failed to decode search results: %w", err)
	}
	
	return documents, nil
}

// ========================================
// Cleanup and Shutdown
// ========================================

// Close closes all database connections
func (dm *DatabaseManager) Close() {
	if dm.postgres != nil {
		dm.postgres.Close()
		dm.logger.Info("PostgreSQL connection closed")
	}
	
	if dm.scylla != nil {
		dm.scylla.Close()
		dm.logger.Info("ScyllaDB connection closed")
	}
	
	if dm.mongo != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		
		if err := dm.mongo.Disconnect(ctx); err != nil {
			dm.logger.Error("Error closing MongoDB connection", zap.Error(err))
		} else {
			dm.logger.Info("MongoDB connection closed")
		}
	}
	
	if dm.redis != nil {
		if err := dm.redis.Close(); err != nil {
			dm.logger.Error("Error closing Redis connection", zap.Error(err))
		} else {
			dm.logger.Info("Redis connection closed")
		}
	}
}

// GetFromCache retrieves a value from Redis cache
func (dm *DatabaseManager) GetFromCache(ctx context.Context, key string) (string, error) {
	if dm.redis == nil {
		return "", fmt.Errorf("redis not available")
	}
	return dm.redis.Get(ctx, key).Result()
}

// SetToCache stores a value in Redis cache
func (dm *DatabaseManager) SetToCache(ctx context.Context, key string, value string, ttl time.Duration) error {
	if dm.redis == nil {
		return fmt.Errorf("redis not available")
	}
	return dm.redis.SetEx(ctx, key, value, ttl).Err()
}