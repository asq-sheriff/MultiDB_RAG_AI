package main

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.uber.org/zap"
)

type DatabaseHealth struct {
	PostgreSQL   string `json:"postgresql"`
	Redis        string `json:"redis"`
	MongoDB      string `json:"mongodb"`
	OverallStatus string `json:"overall_status"`
}

type DatabaseConfig struct {
	PostgresURL       string
	ScyllaHosts       []string
	ScyllaKeyspace    string
	MongoURL          string
	MongoDatabase     string
	RedisURL          string
	RedisDB           int
	MaxConnections    int
	ConnectionTimeout time.Duration
}

type DatabaseManager struct {
	logger    *zap.Logger
	postgres  *pgxpool.Pool
	redis     *redis.Client
	mongo     *mongo.Client
	mongoDb   *mongo.Database
	config    DatabaseConfig
}

func NewDatabaseManager(config DatabaseConfig, logger *zap.Logger) (*DatabaseManager, error) {
	dm := &DatabaseManager{
		logger: logger,
		config: config,
	}

	ctx, cancel := context.WithTimeout(context.Background(), config.ConnectionTimeout)
	defer cancel()

	// Initialize PostgreSQL
	if err := dm.initPostgreSQL(ctx, config); err != nil {
		logger.Warn("PostgreSQL initialization failed", zap.Error(err))
	}

	// Initialize Redis
	if err := dm.initRedis(config); err != nil {
		logger.Warn("Redis initialization failed", zap.Error(err))
	}

	// Initialize MongoDB
	if err := dm.initMongoDB(ctx, config); err != nil {
		logger.Warn("MongoDB initialization failed", zap.Error(err))
	}

	logger.Info("Database manager initialized successfully")
	return dm, nil
}

func (dm *DatabaseManager) initPostgreSQL(ctx context.Context, config DatabaseConfig) error {
	if config.PostgresURL == "" {
		return fmt.Errorf("PostgreSQL URL is empty")
	}

	pgConfig, err := pgxpool.ParseConfig(config.PostgresURL)
	if err != nil {
		return fmt.Errorf("failed to parse PostgreSQL config: %w", err)
	}

	pgConfig.MaxConns = int32(config.MaxConnections)
	pgConfig.MaxConnLifetime = 30 * time.Minute
	pgConfig.MaxConnIdleTime = 5 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, pgConfig)
	if err != nil {
		return fmt.Errorf("failed to create PostgreSQL pool: %w", err)
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return fmt.Errorf("failed to ping PostgreSQL: %w", err)
	}

	dm.postgres = pool
	dm.logger.Info("PostgreSQL connection established")
	return nil
}

func (dm *DatabaseManager) initRedis(config DatabaseConfig) error {
	if config.RedisURL == "" {
		return fmt.Errorf("Redis URL is empty")
	}

	// Parse Redis URL using standard format (redis://host:port/db)
	opts, err := redis.ParseURL(config.RedisURL)
	if err != nil {
		return fmt.Errorf("failed to parse Redis URL: %w", err)
	}
	
	rdb := redis.NewClient(opts)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		return fmt.Errorf("failed to ping Redis: %w", err)
	}

	dm.redis = rdb
	dm.logger.Info("Redis connection established")
	return nil
}

func (dm *DatabaseManager) initMongoDB(ctx context.Context, config DatabaseConfig) error {
	if config.MongoURL == "" {
		return fmt.Errorf("MongoDB URL is empty")
	}

	clientOptions := options.Client().ApplyURI(config.MongoURL)
	client, err := mongo.Connect(ctx, clientOptions)
	if err != nil {
		return fmt.Errorf("failed to connect to MongoDB: %w", err)
	}

	if err := client.Ping(ctx, nil); err != nil {
		client.Disconnect(ctx)
		return fmt.Errorf("failed to ping MongoDB: %w", err)
	}

	dm.mongo = client
	dm.mongoDb = client.Database(config.MongoDatabase)
	dm.logger.Info("MongoDB connection established")
	return nil
}

func (dm *DatabaseManager) GetHealthStatus() DatabaseHealth {
	health := DatabaseHealth{
		PostgreSQL:    "unhealthy",
		Redis:         "unhealthy", 
		MongoDB:       "unhealthy",
		OverallStatus: "unhealthy",
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	healthyCount := 0
	totalServices := 3

	// Check PostgreSQL
	if dm.postgres != nil {
		if err := dm.postgres.Ping(ctx); err == nil {
			health.PostgreSQL = "healthy"
			healthyCount++
		}
	}

	// Check Redis
	if dm.redis != nil {
		if err := dm.redis.Ping(ctx).Err(); err == nil {
			health.Redis = "healthy"
			healthyCount++
		}
	}

	// Check MongoDB
	if dm.mongo != nil {
		if err := dm.mongo.Ping(ctx, nil); err == nil {
			health.MongoDB = "healthy"
			healthyCount++
		}
	}

	// Determine overall status
	if healthyCount == totalServices {
		health.OverallStatus = "healthy"
	} else if healthyCount > 0 {
		health.OverallStatus = "degraded"
	}

	return health
}

func (dm *DatabaseManager) Close() {
	dm.logger.Info("Closing database connections")

	if dm.postgres != nil {
		dm.postgres.Close()
		dm.logger.Info("PostgreSQL connection closed")
	}

	if dm.redis != nil {
		dm.redis.Close()
		dm.logger.Info("Redis connection closed")
	}

	if dm.mongo != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		dm.mongo.Disconnect(ctx)
		dm.logger.Info("MongoDB connection closed")
	}
}