package utils

import (
	"fmt"
	"os"

	"../config"
)

// LoadDemoEnvironment loads environment variables from demo config file if it exists
// This provides a consistent way for all microservices to use demo configurations
// Deprecated: Use LoadEnvironment() instead for better environment detection
func LoadDemoEnvironment() error {
	return config.LoadDemoEnvironment()
}

// LoadEnvironment loads the appropriate environment configuration
// This is the recommended way to load environment for all microservices
func LoadEnvironment(envType ...string) error {
	return config.LoadEnvironment(envType...)
}

// IsDemoMode checks if we're running in demo mode
func IsDemoMode() bool {
	return config.IsDemoMode()
}

// DetectEnvironment detects the current environment
func DetectEnvironment() string {
	return config.DetectEnvironment()
}

// GetDemoServicePort returns the demo port for a service if in demo mode
func GetDemoServicePort(serviceName string) string {
	if !IsDemoMode() {
		return ""
	}
	
	portMap := map[string]string{
		"search":        "8001",
		"chat-history":  "8002", 
		"embedding":     "8005",
		"generation":    "8006",
		"content-safety": "8007",
		"auth":          "8080",
		"audit":         "8084",
		"consent":       "8085",
		"api-gateway":   "8090",
	}
	
	return portMap[serviceName]
}

// GetEnvironmentDatabaseURL returns the appropriate database URL for the current environment
func GetEnvironmentDatabaseURL(dbType string) string {
	envType := DetectEnvironment()
	config, _ := config.LoadEnvironmentConfig()
	
	if env, exists := config.Environments[envType]; exists {
		if url, exists := env.Databases[dbType]; exists {
			// Convert to proper connection strings based on environment
			switch dbType {
			case "postgres":
				if envType == "demo" {
					return fmt.Sprintf("postgresql://demo_v1_user:demo_secure_password_v1@%s/demo_v1_chatbot_app", url)
				}
				return fmt.Sprintf("postgresql://chatbot_user:chatbot_password@%s/chatbot_app", url)
			case "mongodb":
				if envType == "demo" {
					return fmt.Sprintf("mongodb://root:demo_example_v1@%s/demo_v1_chatbot_app?authSource=admin&directConnection=true", url)
				}
				return fmt.Sprintf("mongodb://root:example@%s/chatbot_app?authSource=admin", url)
			case "redis":
				return fmt.Sprintf("redis://%s", url)
			}
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