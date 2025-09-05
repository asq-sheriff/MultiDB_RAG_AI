// Package auth provides secure password hashing and verification
package auth

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"fmt"
	"strings"

	"golang.org/x/crypto/argon2"
)

// PasswordHasher handles secure password hashing using Argon2
type PasswordHasher struct {
	memory      uint32
	iterations  uint32
	parallelism uint8
	saltLength  uint32
	keyLength   uint32
}

// NewPasswordHasher creates a new password hasher with secure defaults
func NewPasswordHasher() *PasswordHasher {
	return &PasswordHasher{
		memory:      64 * 1024, // 64 MB
		iterations:  3,         // 3 iterations
		parallelism: 2,         // 2 parallel threads
		saltLength:  16,        // 16 byte salt
		keyLength:   32,        // 32 byte key
	}
}

// HashPassword hashes a password using Argon2 with a random salt
func (ph *PasswordHasher) HashPassword(password string) (string, error) {
	// Generate a random salt
	salt, err := ph.generateRandomBytes(ph.saltLength)
	if err != nil {
		return "", fmt.Errorf("failed to generate salt: %w", err)
	}

	// Generate the hash using Argon2
	hash := argon2.IDKey([]byte(password), salt, ph.iterations, ph.memory, ph.parallelism, ph.keyLength)

	// Encode the salt and hash as base64
	b64Salt := base64.RawStdEncoding.EncodeToString(salt)
	b64Hash := base64.RawStdEncoding.EncodeToString(hash)

	// Return the encoded hash in the format: $argon2id$v=19$m=65536,t=3,p=2$salt$hash
	encodedHash := fmt.Sprintf("$argon2id$v=%d$m=%d,t=%d,p=%d$%s$%s",
		argon2.Version, ph.memory, ph.iterations, ph.parallelism, b64Salt, b64Hash)

	return encodedHash, nil
}

// VerifyPassword verifies a password against its hash
func (ph *PasswordHasher) VerifyPassword(password, encodedHash string) (bool, error) {
	// Parse the encoded hash
	salt, hash, memory, iterations, parallelism, err := ph.decodeHash(encodedHash)
	if err != nil {
		return false, fmt.Errorf("failed to decode hash: %w", err)
	}

	// Generate hash for the provided password using the same parameters
	comparisonHash := argon2.IDKey([]byte(password), salt, iterations, memory, parallelism, ph.keyLength)

	// Use constant-time comparison to prevent timing attacks
	return subtle.ConstantTimeCompare(hash, comparisonHash) == 1, nil
}

// generateRandomBytes generates cryptographically secure random bytes
func (ph *PasswordHasher) generateRandomBytes(n uint32) ([]byte, error) {
	b := make([]byte, n)
	_, err := rand.Read(b)
	if err != nil {
		return nil, err
	}
	return b, nil
}

// decodeHash parses an Argon2 encoded hash and extracts its components
func (ph *PasswordHasher) decodeHash(encodedHash string) (salt, hash []byte, memory, iterations uint32, parallelism uint8, err error) {
	vals := strings.Split(encodedHash, "$")
	if len(vals) != 6 {
		return nil, nil, 0, 0, 0, fmt.Errorf("invalid hash format")
	}

	if vals[1] != "argon2id" {
		return nil, nil, 0, 0, 0, fmt.Errorf("unsupported hash algorithm: %s", vals[1])
	}

	var version int
	_, err = fmt.Sscanf(vals[2], "v=%d", &version)
	if err != nil {
		return nil, nil, 0, 0, 0, fmt.Errorf("invalid version format: %w", err)
	}
	if version != argon2.Version {
		return nil, nil, 0, 0, 0, fmt.Errorf("unsupported version: %d", version)
	}

	_, err = fmt.Sscanf(vals[3], "m=%d,t=%d,p=%d", &memory, &iterations, &parallelism)
	if err != nil {
		return nil, nil, 0, 0, 0, fmt.Errorf("invalid parameters format: %w", err)
	}

	salt, err = base64.RawStdEncoding.DecodeString(vals[4])
	if err != nil {
		return nil, nil, 0, 0, 0, fmt.Errorf("invalid salt encoding: %w", err)
	}

	hash, err = base64.RawStdEncoding.DecodeString(vals[5])
	if err != nil {
		return nil, nil, 0, 0, 0, fmt.Errorf("invalid hash encoding: %w", err)
	}

	return salt, hash, memory, iterations, parallelism, nil
}

// ValidatePasswordStrength validates password strength requirements
func ValidatePasswordStrength(password string) error {
	if len(password) < 8 {
		return fmt.Errorf("password must be at least 8 characters long")
	}
	
	if len(password) > 128 {
		return fmt.Errorf("password must be less than 128 characters long")
	}

	var (
		hasLower   = false
		hasUpper   = false
		hasNumber  = false
		hasSpecial = false
	)

	for _, char := range password {
		switch {
		case 'a' <= char && char <= 'z':
			hasLower = true
		case 'A' <= char && char <= 'Z':
			hasUpper = true
		case '0' <= char && char <= '9':
			hasNumber = true
		default:
			hasSpecial = true
		}
	}

	if !hasLower {
		return fmt.Errorf("password must contain at least one lowercase letter")
	}
	if !hasUpper {
		return fmt.Errorf("password must contain at least one uppercase letter")
	}
	if !hasNumber {
		return fmt.Errorf("password must contain at least one number")
	}
	if !hasSpecial {
		return fmt.Errorf("password must contain at least one special character")
	}

	// Check for common weak passwords
	weakPasswords := []string{
		"password", "12345678", "qwerty123", "admin123", "password123",
		"welcome123", "letmein123", "monkey123", "dragon123", "master123",
	}
	
	for _, weak := range weakPasswords {
		if strings.EqualFold(password, weak) {
			return fmt.Errorf("password is too common and easily guessed")
		}
	}

	return nil
}

// GenerateSecurePassword generates a cryptographically secure password
func GenerateSecurePassword(length int) (string, error) {
	if length < 12 {
		length = 12 // Minimum secure length
	}
	if length > 128 {
		length = 128 // Maximum practical length
	}

	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"
	
	password := make([]byte, length)
	for i := range password {
		randomBytes := make([]byte, 1)
		_, err := rand.Read(randomBytes)
		if err != nil {
			return "", fmt.Errorf("failed to generate random password: %w", err)
		}
		password[i] = charset[int(randomBytes[0])%len(charset)]
	}

	return string(password), nil
}