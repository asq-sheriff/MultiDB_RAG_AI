package shared

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	
	"github.com/joho/godotenv"
	"gopkg.in/yaml.v2"
)

// EnvironmentConfig represents the environment configuration structure
type EnvironmentConfig struct {
	Environments map[string]struct {
		EnvFile     *string           `yaml:"env_file"`
		Description string            `yaml:"description"`
		Databases   map[string]string `yaml:"databases"`
	} `yaml:"environments"`
	DefaultEnvironment string `yaml:"default_environment"`
	DetectionRules []struct {
		EnvVar  string `yaml:"env_var"`
		Value   string `yaml:"value,omitempty"`
		MapsTo  string `yaml:"maps_to,omitempty"`
	} `yaml:"detection_rules"`
}

// DetectEnvironment detects which environment we should be running in
func DetectEnvironment() string {
	// Quick detection without loading full config for performance
	
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

// LoadEnvironment loads the appropriate environment configuration
func LoadEnvironment(envType ...string) error {
	var targetEnv string
	if len(envType) > 0 {
		targetEnv = envType[0]
	} else {
		targetEnv = DetectEnvironment()
	}
	
	fmt.Printf("🔧 Go service detected environment: %s\n", targetEnv)
	
	// Map environment to file paths
	var envFilePath string
	switch targetEnv {
	case "demo":
		envFilePath = "demo/config/.env.demo_v1"
	case "development":
		envFilePath = ".env"
	case "testing":
		envFilePath = "config/testing.env"
	case "production":
		// Production uses system environment variables
		fmt.Printf("✅ %s environment - using system variables\n", targetEnv)
		return nil
	default:
		fmt.Printf("⚠️ Unknown environment: %s, using development\n", targetEnv)
		envFilePath = ".env"
	}
	
	// Find the actual file path from various possible locations
	searchPaths := []string{
		envFilePath,                                                                // From current directory
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
	
	// Load with override=true to ensure environment-specific settings take precedence
	if err := godotenv.Overload(actualPath); err != nil {
		return fmt.Errorf("failed to load %s environment: %v", targetEnv, err)
	}
	
	fmt.Printf("✅ Loaded %s environment from %s\n", targetEnv, filepath.Base(actualPath))
	return nil
}

// IsDemoMode checks if we're running in demo mode
func IsDemoMode() bool {
	return DetectEnvironment() == "demo"
}

// GetEnvironmentDatabaseURL returns the appropriate database URL for the current environment
func GetEnvironmentDatabaseURL(dbType string) string {
	envType := DetectEnvironment()
	
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
		case "scylla":
			return "localhost:9045,localhost:9046,localhost:9047"
		}
	case "development":
		switch dbType {
		case "postgres":
			return "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_app"
		case "mongodb":
			return "mongodb://root:example@localhost:27017/chatbot_app?authSource=admin"
		case "redis":
			return "redis://localhost:6379/0"
		case "scylla":
			return "localhost:9042,localhost:9043,localhost:9044"
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
	case "scylla":
		return os.Getenv("SCYLLA_HOSTS")
	default:
		return ""
	}
}

// Legacy function for backward compatibility  
func LoadDemoEnvironment() error {
	envType := DetectEnvironment()
	if envType == "demo" {
		return LoadEnvironment("demo")
	}
	return LoadEnvironment()
}