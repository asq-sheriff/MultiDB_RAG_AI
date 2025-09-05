// Package main provides a migration runner for the auth-rbac service database
package main

import (
	"context"
	"fmt"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/joho/godotenv"
)

// Migration represents a database migration
type Migration struct {
	ID       string
	Name     string
	SQL      string
	FilePath string
}

func main() {
	// Load environment variables
	if err := godotenv.Load("../../../.env"); err != nil {
		log.Printf("Warning: Could not load .env file: %v", err)
	}

	// Get database URL
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		databaseURL = "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_app"
	}

	// Connect to database
	conn, err := pgx.Connect(context.Background(), databaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer conn.Close(context.Background())

	// Create migrations table if it doesn't exist
	if err := createMigrationsTable(conn); err != nil {
		log.Fatalf("Failed to create migrations table: %v", err)
	}

	// Load migrations from files
	migrations, err := loadMigrations(".")
	if err != nil {
		log.Fatalf("Failed to load migrations: %v", err)
	}

	// Get applied migrations
	appliedMigrations, err := getAppliedMigrations(conn)
	if err != nil {
		log.Fatalf("Failed to get applied migrations: %v", err)
	}

	// Run pending migrations
	for _, migration := range migrations {
		if _, applied := appliedMigrations[migration.ID]; applied {
			fmt.Printf("Migration %s (%s) already applied, skipping...\n", migration.ID, migration.Name)
			continue
		}

		fmt.Printf("Applying migration %s (%s)...\n", migration.ID, migration.Name)

		// Start transaction
		tx, err := conn.Begin(context.Background())
		if err != nil {
			log.Fatalf("Failed to start transaction: %v", err)
		}

		// Execute migration
		if _, err := tx.Exec(context.Background(), migration.SQL); err != nil {
			tx.Rollback(context.Background())
			log.Fatalf("Failed to execute migration %s: %v", migration.ID, err)
		}

		// Record migration as applied
		if err := recordMigration(tx, migration); err != nil {
			tx.Rollback(context.Background())
			log.Fatalf("Failed to record migration %s: %v", migration.ID, err)
		}

		// Commit transaction
		if err := tx.Commit(context.Background()); err != nil {
			log.Fatalf("Failed to commit migration %s: %v", migration.ID, err)
		}

		fmt.Printf("Migration %s (%s) applied successfully!\n", migration.ID, migration.Name)
	}

	fmt.Println("All migrations completed successfully!")
}

// createMigrationsTable creates the migrations tracking table
func createMigrationsTable(conn *pgx.Conn) error {
	query := `
		CREATE TABLE IF NOT EXISTS schema_migrations (
			id VARCHAR(255) PRIMARY KEY,
			name VARCHAR(255) NOT NULL,
			applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
			checksum VARCHAR(64)
		);
	`

	_, err := conn.Exec(context.Background(), query)
	return err
}

// loadMigrations loads all migration files from the given directory
func loadMigrations(dir string) ([]Migration, error) {
	var migrations []Migration

	err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if d.IsDir() || !strings.HasSuffix(path, ".sql") {
			return nil
		}

		filename := d.Name()
		
		// Skip the migration runner and other non-migration files
		if filename == "run_migrations.go" || !strings.Contains(filename, "_") {
			return nil
		}

		// Extract migration ID and name from filename
		// Expected format: 001_create_users_table.sql
		parts := strings.SplitN(filename, "_", 2)
		if len(parts) != 2 {
			return fmt.Errorf("invalid migration filename format: %s", filename)
		}

		id := parts[0]
		name := strings.TrimSuffix(parts[1], ".sql")

		// Read migration content
		content, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("failed to read migration file %s: %v", path, err)
		}

		migrations = append(migrations, Migration{
			ID:       id,
			Name:     name,
			SQL:      string(content),
			FilePath: path,
		})

		return nil
	})

	if err != nil {
		return nil, err
	}

	// Sort migrations by ID
	sort.Slice(migrations, func(i, j int) bool {
		return migrations[i].ID < migrations[j].ID
	})

	return migrations, nil
}

// getAppliedMigrations returns a map of applied migration IDs
func getAppliedMigrations(conn *pgx.Conn) (map[string]bool, error) {
	query := "SELECT id FROM schema_migrations"
	rows, err := conn.Query(context.Background(), query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	applied := make(map[string]bool)
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		applied[id] = true
	}

	return applied, rows.Err()
}

// recordMigration records a migration as applied
func recordMigration(tx pgx.Tx, migration Migration) error {
	query := `
		INSERT INTO schema_migrations (id, name, applied_at) 
		VALUES ($1, $2, NOW())
	`

	_, err := tx.Exec(context.Background(), query, migration.ID, migration.Name)
	return err
}