package config

import (
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"

	"github.com/joho/godotenv"
	"gopkg.in/yaml.v2"
)

// EnvironmentConfig represents the environment configuration structure
type EnvironmentConfig struct {
	Environments map[string]Environment `yaml:"environments"`
	DefaultEnvironment string `yaml:"default_environment"`
	DetectionRules []DetectionRule `yaml:"detection_rules"`
}

// Environment represents configuration for a specific environment
type Environment struct {
	EnvFile     *string           `yaml:"env_file"`
	Description string            `yaml:"description"`
	Databases   map[string]string `yaml:"databases"`
}

// DetectionRule represents a rule for detecting the environment
type DetectionRule struct {
	EnvVar  string `yaml:"env_var"`
	Value   string `yaml:"value,omitempty"`
	MapsTo  string `yaml:"maps_to,omitempty"`
}

// LoadEnvironmentConfig loads the environment configuration from YAML file
func LoadEnvironmentConfig() (*EnvironmentConfig, error) {
	// Find the config file from various possible locations
	configPaths := []string{
		"../../config/environments.yaml",           // From microservice directory
		"../../../config/environments.yaml",       // From nested directory
		"./config/environments.yaml",              // From project root
		"/Users/asqmac/git-repos/MultiDB-Chatbot/config/environments.yaml", // Absolute fallback
	}
	
	var configPath string
	for _, path := range configPaths {
		if _, err := os.Stat(path); err == nil {
			configPath = path
			break
		}
	}
	
	if configPath == "" {
		return &EnvironmentConfig{
			Environments: make(map[string]Environment),
			DefaultEnvironment: "development",
		}, fmt.Errorf("environment config not found")
	}
	
	data, err := ioutil.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read environment config: %v", err)
	}
	
	var config EnvironmentConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse environment config: %v", err)
	}
	
	return &config, nil
}

// DetectEnvironment detects which environment we should be running in
func DetectEnvironment() string {
	config, err := LoadEnvironmentConfig()
	if err != nil {
		fmt.Printf("Warning: Could not load environment config: %v\n", err)
		return "development"
	}
	
	// Apply detection rules in priority order
	for _, rule := range config.DetectionRules {
		envValue := os.Getenv(rule.EnvVar)
		if envValue == "" {
			continue
		}
		
		// Check if rule has specific value requirement
		if rule.Value != "" {
			if envValue == rule.Value {
				if rule.MapsTo != "" {
					return rule.MapsTo
				}
				return strings.ToLower(envValue)
			}
		} else {
			// Direct environment variable value
			envLower := strings.ToLower(envValue)
			switch envLower {
			case "demo_v1", "demo":
				return "demo"
			case "development", "dev":
				return "development"
			case "production", "prod":
				return "production"
			case "testing", "test":
				return "testing"
			default:
				return envLower
			}
		}
	}
	
	// Return default environment
	return config.DefaultEnvironment
}

// LoadEnvironmentFile loads environment file for the specified environment type
func LoadEnvironmentFile(envType string) error {
	config, err := LoadEnvironmentConfig()
	if err != nil {
		return err
	}
	
	environment, exists := config.Environments[envType]
	if !exists {
		return fmt.Errorf("no configuration found for environment: %s", envType)
	}
	
	// If env_file is null, use system environment variables
	if environment.EnvFile == nil {
		fmt.Printf("✅ %s environment - using system variables\n", strings.Title(envType))
		return nil
	}
	
	// Find the actual file path
	envFilePaths := []string{
		*environment.EnvFile,                                   // Relative to current directory
		fmt.Sprintf("../../%s", *environment.EnvFile),         // From microservice directory
		fmt.Sprintf("../../../%s", *environment.EnvFile),      // From nested directory
		fmt.Sprintf("/Users/asqmac/git-repos/MultiDB-Chatbot/%s", *environment.EnvFile), // Absolute path
	}
	
	var actualPath string
	for _, path := range envFilePaths {
		if _, err := os.Stat(path); err == nil {
			actualPath = path
			break
		}
	}
	
	if actualPath == "" {
		return fmt.Errorf("environment file not found: %s", *environment.EnvFile)
	}
	
	// Load the environment file with override=true to ensure environment-specific settings take precedence
	if err := godotenv.Overload(actualPath); err != nil {
		return fmt.Errorf("failed to load %s environment: %v", envType, err)
	}
	
	fmt.Printf("✅ Loaded %s environment from %s\n", envType, filepath.Base(actualPath))
	return nil
}

// LoadEnvironment is the main environment loader - detects and loads appropriate config
func LoadEnvironment(envType ...string) error {
	var targetEnv string
	if len(envType) > 0 {
		targetEnv = envType[0]
	} else {
		targetEnv = DetectEnvironment()
	}
	
	fmt.Printf("🔧 Detected environment: %s\n", targetEnv)
	return LoadEnvironmentFile(targetEnv)
}

// IsDemoMode checks if we're running in demo mode
func IsDemoMode() bool {
	return DetectEnvironment() == "demo"
}

// GetServiceConfig returns database configuration based on detected environment
func GetServiceConfig() map[string]string {
	envType := DetectEnvironment()
	config, err := LoadEnvironmentConfig()
	if err != nil {
		return make(map[string]string)
	}
	
	environment, exists := config.Environments[envType]
	if !exists {
		return make(map[string]string)
	}
	
	return environment.Databases
}

// Legacy function for backward compatibility
func LoadDemoEnvironment() error {
	envType := DetectEnvironment()
	if envType == "demo" {
		return LoadEnvironmentFile("demo")
	}
	return nil
}