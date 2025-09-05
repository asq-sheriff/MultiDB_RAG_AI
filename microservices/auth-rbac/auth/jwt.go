// Package auth provides JWT token management for authentication
package auth

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	
	"auth-rbac-service/models"
	"auth-rbac-service/rbac"
)

// JWTManager handles JWT token creation, validation, and management
type JWTManager struct {
	secretKey             []byte
	accessTokenDuration   time.Duration
	refreshTokenDuration  time.Duration
	issuer                string
}

// NewJWTManager creates a new JWT manager with the specified configuration
func NewJWTManager(secretKey string, accessTokenDuration, refreshTokenDuration time.Duration, issuer string) *JWTManager {
	return &JWTManager{
		secretKey:             []byte(secretKey),
		accessTokenDuration:   accessTokenDuration,
		refreshTokenDuration:  refreshTokenDuration,
		issuer:                issuer,
	}
}

// GenerateTokenPair generates both access and refresh tokens for a user
func (jm *JWTManager) GenerateTokenPair(user *models.User, sessionID string) (*models.LoginResponse, error) {
	// Generate access token
	accessToken, accessExpiresAt, err := jm.GenerateAccessToken(user, sessionID)
	if err != nil {
		return nil, fmt.Errorf("failed to generate access token: %w", err)
	}

	// Generate refresh token
	refreshToken, err := jm.GenerateRefreshToken(user.ID, sessionID)
	if err != nil {
		return nil, fmt.Errorf("failed to generate refresh token: %w", err)
	}

	// Calculate expires in seconds
	expiresIn := int64(time.Until(accessExpiresAt).Seconds())

	return &models.LoginResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "Bearer",
		ExpiresIn:    expiresIn,
		User:         user.ToProfile(),
	}, nil
}

// GenerateAccessToken generates a JWT access token for a user
func (jm *JWTManager) GenerateAccessToken(user *models.User, sessionID string) (string, time.Time, error) {
	now := time.Now()
	expiresAt := now.Add(jm.accessTokenDuration)

	// Create custom claims
	claims := &jwt.RegisteredClaims{
		ID:        uuid.New().String(), // JTI (JWT ID)
		Subject:   user.ID.String(),    // User ID
		Issuer:    jm.issuer,
		IssuedAt:  jwt.NewNumericDate(now),
		ExpiresAt: jwt.NewNumericDate(expiresAt),
		NotBefore: jwt.NewNumericDate(now),
	}

	// Create token with custom claims in a map for additional data
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"jti":             claims.ID,
		"sub":             claims.Subject,
		"iss":             claims.Issuer,
		"iat":             claims.IssuedAt.Unix(),
		"exp":             claims.ExpiresAt.Unix(),
		"nbf":             claims.NotBefore.Unix(),
		"user_id":         user.ID.String(),
		"email":           user.Email,
		"healthcare_role": string(user.HealthcareRole),
		"is_superuser":    user.IsSuperuser,
		"is_active":       user.IsActive,
		"is_verified":     user.IsVerified,
		"session_id":      sessionID,
		"token_type":      "access",
	})

	// Sign token with secret key
	tokenString, err := token.SignedString(jm.secretKey)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("failed to sign token: %w", err)
	}

	return tokenString, expiresAt, nil
}

// GenerateRefreshToken generates a refresh token for a user
func (jm *JWTManager) GenerateRefreshToken(userID uuid.UUID, sessionID string) (string, error) {
	now := time.Now()
	expiresAt := now.Add(jm.refreshTokenDuration)

	// Create refresh token with minimal claims
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"jti":        uuid.New().String(),
		"sub":        userID.String(),
		"iss":        jm.issuer,
		"iat":        now.Unix(),
		"exp":        expiresAt.Unix(),
		"session_id": sessionID,
		"token_type": "refresh",
	})

	// Sign token with secret key
	tokenString, err := token.SignedString(jm.secretKey)
	if err != nil {
		return "", fmt.Errorf("failed to sign refresh token: %w", err)
	}

	return tokenString, nil
}

// ValidateToken validates a JWT token and returns the claims
func (jm *JWTManager) ValidateToken(tokenString string) (*models.JWTClaims, error) {
	// Parse token
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Validate signing method
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return jm.secretKey, nil
	})

	if err != nil {
		return nil, fmt.Errorf("failed to parse token: %w", err)
	}

	// Validate token
	if !token.Valid {
		return nil, fmt.Errorf("invalid token")
	}

	// Extract claims
	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, fmt.Errorf("invalid token claims")
	}

	// Convert claims to our custom structure
	jwtClaims, err := jm.extractClaims(claims)
	if err != nil {
		return nil, fmt.Errorf("failed to extract claims: %w", err)
	}

	// Validate expiration
	if time.Now().After(jwtClaims.ExpiresAt) {
		return nil, fmt.Errorf("token has expired")
	}

	// Validate not before
	if time.Now().Before(jwtClaims.NotBefore) {
		return nil, fmt.Errorf("token not valid yet")
	}

	return jwtClaims, nil
}

// extractClaims extracts and validates claims from the token
func (jm *JWTManager) extractClaims(claims jwt.MapClaims) (*models.JWTClaims, error) {
	// Extract user ID
	userIDStr, ok := claims["user_id"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid user_id claim")
	}
	userID, err := uuid.Parse(userIDStr)
	if err != nil {
		return nil, fmt.Errorf("invalid user_id format: %w", err)
	}

	// Extract email
	email, ok := claims["email"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid email claim")
	}

	// Extract healthcare role
	roleStr, ok := claims["healthcare_role"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid healthcare_role claim")
	}
	role, err := rbac.GetHealthcareRoleByString(roleStr)
	if err != nil {
		return nil, fmt.Errorf("invalid healthcare role: %w", err)
	}

	// Extract boolean claims
	isSuperuser, _ := claims["is_superuser"].(bool)
	isActive, _ := claims["is_active"].(bool)
	isVerified, _ := claims["is_verified"].(bool)

	// Extract session ID
	sessionID, ok := claims["session_id"].(string)
	if !ok {
		return nil, fmt.Errorf("missing or invalid session_id claim")
	}

	// Extract timestamps
	iat, ok := claims["iat"].(float64)
	if !ok {
		return nil, fmt.Errorf("missing or invalid iat claim")
	}
	exp, ok := claims["exp"].(float64)
	if !ok {
		return nil, fmt.Errorf("missing or invalid exp claim")
	}
	nbf, ok := claims["nbf"].(float64)
	if !ok {
		return nil, fmt.Errorf("missing or invalid nbf claim")
	}

	// Extract optional claims
	issuer, _ := claims["iss"].(string)
	subject, _ := claims["sub"].(string)

	return &models.JWTClaims{
		UserID:         userID,
		Email:          email,
		HealthcareRole: role,
		IsSuperuser:    isSuperuser,
		IsActive:       isActive,
		IsVerified:     isVerified,
		SessionID:      sessionID,
		IssuedAt:       time.Unix(int64(iat), 0),
		ExpiresAt:      time.Unix(int64(exp), 0),
		NotBefore:      time.Unix(int64(nbf), 0),
		Issuer:         issuer,
		Subject:        subject,
	}, nil
}

// RefreshAccessToken generates a new access token using a valid refresh token
func (jm *JWTManager) RefreshAccessToken(refreshTokenString string, user *models.User) (*models.RefreshTokenResponse, error) {
	// Validate refresh token
	token, err := jwt.Parse(refreshTokenString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return jm.secretKey, nil
	})

	if err != nil {
		return nil, fmt.Errorf("invalid refresh token: %w", err)
	}

	if !token.Valid {
		return nil, fmt.Errorf("refresh token is not valid")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return nil, fmt.Errorf("invalid refresh token claims")
	}

	// Validate token type
	tokenType, ok := claims["token_type"].(string)
	if !ok || tokenType != "refresh" {
		return nil, fmt.Errorf("not a refresh token")
	}

	// Extract session ID
	sessionID, ok := claims["session_id"].(string)
	if !ok {
		return nil, fmt.Errorf("missing session_id in refresh token")
	}

	// Validate user ID matches
	userIDStr, ok := claims["sub"].(string)
	if !ok {
		return nil, fmt.Errorf("missing user ID in refresh token")
	}
	if userIDStr != user.ID.String() {
		return nil, fmt.Errorf("refresh token user ID mismatch")
	}

	// Generate new access token
	accessToken, expiresAt, err := jm.GenerateAccessToken(user, sessionID)
	if err != nil {
		return nil, fmt.Errorf("failed to generate new access token: %w", err)
	}

	expiresIn := int64(time.Until(expiresAt).Seconds())

	return &models.RefreshTokenResponse{
		AccessToken: accessToken,
		TokenType:   "Bearer",
		ExpiresIn:   expiresIn,
	}, nil
}

// GenerateSecureSecret generates a cryptographically secure secret key
func GenerateSecureSecret() (string, error) {
	bytes := make([]byte, 64) // 512-bit key
	_, err := rand.Read(bytes)
	if err != nil {
		return "", fmt.Errorf("failed to generate secure secret: %w", err)
	}
	return hex.EncodeToString(bytes), nil
}

// BlacklistToken adds a token to a blacklist (this would typically use Redis or database)
func (jm *JWTManager) BlacklistToken(tokenString string) error {
	// Parse token to get JTI
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		return jm.secretKey, nil
	})
	if err != nil {
		return fmt.Errorf("failed to parse token for blacklisting: %w", err)
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return fmt.Errorf("invalid token claims for blacklisting")
	}

	jti, ok := claims["jti"].(string)
	if !ok {
		return fmt.Errorf("missing JTI claim for blacklisting")
	}

	// In a real implementation, you would store the JTI in Redis or database
	// with an expiration time matching the token's expiration
	_ = jti // Placeholder for actual blacklist implementation

	return nil
}