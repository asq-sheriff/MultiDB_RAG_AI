// Environment Loader Template - Copy this code into each microservice main.go
// Add this code at the top of your main.go file after the package declaration

import (
	"os"
	"path/filepath"
	"strings"
	"github.com/joho/godotenv"
)

// detectEnvironment detects which environment we should be running in
func detectEnvironment() string {
	// Highest priority: explicit override flags
	if os.Getenv("DEMO_MODE") == "1" {
		return "demo"
	}
	
	if os.Getenv("CI") == "true" {
		return "testing"
	}
	
	// Medium priority: explicit environment variables
	if appEnv := os.Getenv("APP_ENVIRONMENT"); appEnv != "" {
		return strings.ToLower(appEnv)
	}
	
	// Lowest priority: general environment variable
	if env := strings.ToLower(os.Getenv("ENVIRONMENT")); env != "" {
		switch env {
		case "demo_v1", "demo":
			return "demo"
		case "development", "dev":
			return "development"
		case "production", "prod":
			return "production"
		case "testing", "test":
			return "testing"
		default:
			return env
		}
	}
	
	// Default to development
	return "development"
}

// loadEnvironment loads the appropriate environment configuration
func loadEnvironment() error {
	envType := detectEnvironment()
	fmt.Printf("🔧 Service detected environment: %s\n", envType)
	
	// Map environment to file paths
	var envFilePath string
	switch envType {
	case "demo":
		envFilePath = "demo/config/.env.demo_v1"
	case "development":
		envFilePath = ".env"
	case "testing":
		envFilePath = "config/testing.env"
	case "production":
		// Production uses system environment variables
		fmt.Printf("✅ %s environment - using system variables\n", envType)
		return nil
	default:
		fmt.Printf("⚠️ Unknown environment: %s, using development\n", envType)
		envFilePath = ".env"
	}
	
	// Find the actual file path from various possible locations
	searchPaths := []string{
		envFilePath,                                                                // Current directory
		fmt.Sprintf("../../%s", envFilePath),                                      // From microservice directory
		fmt.Sprintf("../../../%s", envFilePath),                                   // From nested directory
		fmt.Sprintf("/Users/asqmac/git-repos/MultiDB-Chatbot/%s", envFilePath),    // Absolute path
	}
	
	var actualPath string
	for _, path := range searchPaths {
		if _, err := os.Stat(path); err == nil {
			actualPath = path
			break
		}
	}
	
	if actualPath == "" {
		fmt.Printf("⚠️ Environment file %s not found, using defaults\n", envFilePath)
		return nil
	}
	
	// Load with override=true for environment-specific settings
	if err := godotenv.Overload(actualPath); err != nil {
		return fmt.Errorf("failed to load %s environment: %v", envType, err)
	}
	
	fmt.Printf("✅ Loaded %s environment from %s\n", envType, filepath.Base(actualPath))
	return nil
}

// getEnvironmentDatabaseURL returns the appropriate database URL for current environment
func getEnvironmentDatabaseURL(dbType string) string {
	envType := detectEnvironment()
	
	// Environment-specific database URLs
	switch envType {
	case "demo":
		switch dbType {
		case "postgres":
			return "postgresql://demo_v1_user:demo_secure_password_v1@localhost:5433/demo_v1_chatbot_app"
		case "mongodb":
			return "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true"
		case "redis":
			return "redis://localhost:6380/10"
		}
	case "development":
		switch dbType {
		case "postgres":
			return "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_app"
		case "mongodb":
			return "mongodb://root:example@localhost:27017/chatbot_app?authSource=admin"
		case "redis":
			return "redis://localhost:6379/0"
		}
	}
	
	// Fallback to environment variables
	switch dbType {
	case "postgres":
		return os.Getenv("DATABASE_URL")
	case "mongodb": 
		return os.Getenv("MONGODB_URL")
	case "redis":
		return os.Getenv("REDIS_URL") 
	default:
		return ""
	}
}

// USAGE PATTERN:
// 1. Add these functions to your main.go
// 2. Add to main() function BEFORE envconfig.Process():
//    if err := loadEnvironment(); err != nil {
//        fmt.Printf("Warning: Could not load environment: %v\n", err)
//    }
// 3. Set database URLs before envconfig:
//    if dbURL := getEnvironmentDatabaseURL("postgres"); dbURL != "" {
//        os.Setenv("DATABASE_URL", dbURL)
//    }
// 4. Add godotenv to go.mod:
//    go get github.com/joho/godotenv