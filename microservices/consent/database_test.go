package main

import (
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
	_ "github.com/lib/pq"
)

type DatabaseTestSuite struct {
	suite.Suite
	db *PostgresDB
}

func (suite *DatabaseTestSuite) SetupSuite() {
	// Use test database URL
	testDatabaseURL := os.Getenv("TEST_DATABASE_URL")
	if testDatabaseURL == "" {
		testDatabaseURL = "postgres://chatbot_user:chatbot_password@localhost:5432/chatbot_app_test"
	}

	var err error
	suite.db, err = NewPostgresDB(testDatabaseURL)
	if err != nil {
		suite.T().Skip("Test database not available:", err)
	}

	// Create test schema
	suite.createTestSchema()
}

func (suite *DatabaseTestSuite) TearDownSuite() {
	if suite.db != nil {
		suite.cleanupTestData()
		suite.db.Close()
	}
}

func (suite *DatabaseTestSuite) SetupTest() {
	// Clean up any existing test data before each test
	suite.cleanupTestData()
}

func (suite *DatabaseTestSuite) createTestSchema() {
	// Create test users
	_, err := suite.db.conn.Exec(`
		INSERT INTO users (user_id, email, password_hash, healthcare_role) VALUES
		($1, 'patient@test.com', 'hash1', 'resident'),
		($2, 'doctor@test.com', 'hash2', 'care_staff'),
		($3, 'family@test.com', 'hash3', 'family')
		ON CONFLICT (user_id) DO NOTHING`,
		testPatientID, testDoctorID, testFamilyID)
	if err != nil {
		suite.T().Fatalf("Failed to create test users: %v", err)
	}
}

func (suite *DatabaseTestSuite) cleanupTestData() {
	// Clean up test data in reverse foreign key order
	tables := []string{
		"phi_access_log",
		"emergency_access_log", 
		"patient_consents",
		"treatment_relationships",
		"family_relationships",
	}
	
	for _, table := range tables {
		_, err := suite.db.conn.Exec(fmt.Sprintf("DELETE FROM %s WHERE patient_id IN ($1, $2, $3)", table), 
			testPatientID, testDoctorID, testFamilyID)
		if err != nil {
			suite.T().Logf("Warning: failed to clean up table %s: %v", table, err)
		}
	}
}

// Test data constants
var (
	testPatientID = uuid.MustParse("550e8400-e29b-41d4-a716-446655440001")
	testDoctorID  = uuid.MustParse("550e8400-e29b-41d4-a716-446655440002")
	testFamilyID  = uuid.MustParse("550e8400-e29b-41d4-a716-446655440003")
)

func (suite *DatabaseTestSuite) TestCreatePatientConsent() {
	params := CreatePatientConsentParams{
		PatientID:           testPatientID,
		GrantorID:           testPatientID,
		GranteeID:           testDoctorID,
		Purpose:             "treatment",
		DataTypes:           []string{"conversations", "care_notes"},
		ExpiresAt:           nil,
		ConsentDocumentPath: nil,
	}

	consent, err := suite.db.CreatePatientConsent(params)
	
	assert.NoError(suite.T(), err)
	assert.NotNil(suite.T(), consent)
	assert.NotEqual(suite.T(), uuid.Nil, consent.ConsentID)
	assert.Equal(suite.T(), testPatientID, consent.PatientID)
	assert.Equal(suite.T(), testPatientID, consent.GrantorID)
	assert.Equal(suite.T(), testDoctorID, consent.GranteeID)
	assert.Equal(suite.T(), "treatment", consent.Purpose)
	assert.Equal(suite.T(), []string{"conversations", "care_notes"}, consent.DataTypes)
	assert.Equal(suite.T(), "active", consent.Status)
	assert.Nil(suite.T(), consent.RevokedAt)
}

func (suite *DatabaseTestSuite) TestCreatePatientConsentWithExpiry() {
	expiryTime := time.Now().Add(30 * 24 * time.Hour) // 30 days
	
	params := CreatePatientConsentParams{
		PatientID: testPatientID,
		GrantorID: testPatientID,
		GranteeID: testDoctorID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations"},
		ExpiresAt: &expiryTime,
	}

	consent, err := suite.db.CreatePatientConsent(params)
	
	assert.NoError(suite.T(), err)
	assert.NotNil(suite.T(), consent.ExpiresAt)
	assert.WithinDuration(suite.T(), expiryTime, *consent.ExpiresAt, time.Second)
}

func (suite *DatabaseTestSuite) TestRevokeConsentByPatient() {
	// First create a consent
	consent := suite.createTestConsent()

	// Revoke by patient (self)
	success, err := suite.db.RevokeConsent(RevokeConsentParams{
		ConsentID: consent.ConsentID,
		RevokedBy: testPatientID,
		Reason:    stringPtr("Patient requested revocation"),
	})

	assert.NoError(suite.T(), err)
	assert.True(suite.T(), success)

	// Verify consent is revoked
	consents, err := suite.db.GetPatientConsents(GetPatientConsentsParams{
		PatientID:  testPatientID,
		ActiveOnly: false, // Include revoked
	})
	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), consents, 1)
	assert.Equal(suite.T(), "revoked", consents[0].Status)
	assert.NotNil(suite.T(), consents[0].RevokedAt)
	assert.Equal(suite.T(), testPatientID, *consents[0].RevokedBy)
}

func (suite *DatabaseTestSuite) TestRevokeConsentUnauthorized() {
	// Create a consent
	consent := suite.createTestConsent()

	// Try to revoke by unauthorized user
	success, err := suite.db.RevokeConsent(RevokeConsentParams{
		ConsentID: consent.ConsentID,
		RevokedBy: testFamilyID, // Not patient or grantor
		Reason:    stringPtr("Unauthorized attempt"),
	})

	assert.NoError(suite.T(), err)
	assert.False(suite.T(), success) // Should fail authorization
}

func (suite *DatabaseTestSuite) TestRevokeNonExistentConsent() {
	success, err := suite.db.RevokeConsent(RevokeConsentParams{
		ConsentID: uuid.New(), // Random UUID that doesn't exist
		RevokedBy: testPatientID,
	})

	assert.Error(suite.T(), err)
	assert.False(suite.T(), success)
}

func (suite *DatabaseTestSuite) TestGetPatientConsentsActiveOnly() {
	// Create active consent
	activeConsent := suite.createTestConsent()
	
	// Create expired consent
	expiredTime := time.Now().Add(-24 * time.Hour) // Yesterday
	suite.createTestConsentWithExpiry(&expiredTime)

	// Create revoked consent
	revokedConsent := suite.createTestConsent()
	_, err := suite.db.RevokeConsent(RevokeConsentParams{
		ConsentID: revokedConsent.ConsentID,
		RevokedBy: testPatientID,
	})
	assert.NoError(suite.T(), err)

	// Get active consents only
	consents, err := suite.db.GetPatientConsents(GetPatientConsentsParams{
		PatientID:  testPatientID,
		ActiveOnly: true,
	})

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), consents, 1) // Only active consent
	assert.Equal(suite.T(), activeConsent.ConsentID, consents[0].ConsentID)
	assert.Equal(suite.T(), "active", consents[0].Status)
}

func (suite *DatabaseTestSuite) TestGetPatientConsentsAll() {
	// Create multiple consents with different statuses
	_ = suite.createTestConsent() // activeConsent for testing
	
	revokedConsent := suite.createTestConsent()
	_, err := suite.db.RevokeConsent(RevokeConsentParams{
		ConsentID: revokedConsent.ConsentID,
		RevokedBy: testPatientID,
	})
	assert.NoError(suite.T(), err)

	// Get all consents
	consents, err := suite.db.GetPatientConsents(GetPatientConsentsParams{
		PatientID:  testPatientID,
		ActiveOnly: false,
	})

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), consents, 2) // Active and revoked
	
	// Should be ordered by created_at DESC
	assert.True(suite.T(), consents[0].CreatedAt.After(consents[1].CreatedAt) || 
		consents[0].CreatedAt.Equal(consents[1].CreatedAt))
}

func (suite *DatabaseTestSuite) TestCheckDataAccessSelfAccess() {
	decision, err := suite.db.checkDataAccess(CheckDataAccessParams{
		UserID:    testPatientID,
		PatientID: testPatientID, // Same user
		Purpose:   "patient_request",
		DataTypes: []string{"conversations"},
	})

	assert.NoError(suite.T(), err)
	assert.True(suite.T(), decision.Granted)
	assert.Contains(suite.T(), decision.Reason, "Self-access granted")
	assert.False(suite.T(), decision.EmergencyAccess)
}

func (suite *DatabaseTestSuite) TestCheckDataAccessWithValidConsent() {
	// Create consent
	consent := suite.createTestConsent()

	decision, err := suite.db.checkDataAccess(CheckDataAccessParams{
		UserID:    testDoctorID, // Grantee
		PatientID: testPatientID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations"}, // Subset of consented data
	})

	assert.NoError(suite.T(), err)
	assert.True(suite.T(), decision.Granted)
	assert.Contains(suite.T(), decision.Reason, "patient consent")
	assert.Equal(suite.T(), consent.ConsentID, *decision.ConsentID)
}

func (suite *DatabaseTestSuite) TestCheckDataAccessNoConsent() {
	decision, err := suite.db.checkDataAccess(CheckDataAccessParams{
		UserID:    testFamilyID, // No consent
		PatientID: testPatientID,
		Purpose:   "family_care",
		DataTypes: []string{"conversations"},
	})

	assert.NoError(suite.T(), err)
	assert.False(suite.T(), decision.Granted)
	assert.Contains(suite.T(), decision.Reason, "No valid authorization")
}

func (suite *DatabaseTestSuite) TestCheckDataAccessEmergencyAccess() {
	decision, err := suite.db.checkDataAccess(CheckDataAccessParams{
		UserID:                 testDoctorID,
		PatientID:              testPatientID,
		Purpose:                "emergency",
		DataTypes:              []string{"vital_signs", "medications"},
		EmergencyJustification: stringPtr("Patient unconscious, need medical history"),
	})

	assert.NoError(suite.T(), err)
	assert.True(suite.T(), decision.Granted)
	assert.True(suite.T(), decision.EmergencyAccess)
	assert.Contains(suite.T(), decision.Reason, "Emergency access granted")
}

func (suite *DatabaseTestSuite) TestCheckDataAccessEmergencyUnauthorizedRole() {
	decision, err := suite.db.checkDataAccess(CheckDataAccessParams{
		UserID:                 testFamilyID, // Family role not authorized for emergency
		PatientID:              testPatientID,
		Purpose:                "emergency",
		DataTypes:              []string{"vital_signs"},
		EmergencyJustification: stringPtr("Family emergency"),
	})

	assert.NoError(suite.T(), err)
	assert.False(suite.T(), decision.Granted)
	assert.False(suite.T(), decision.EmergencyAccess)
	assert.Contains(suite.T(), decision.Reason, "not authorized for emergency access")
}

func (suite *DatabaseTestSuite) TestGetActiveConsentCoversDataTypes() {
	// Create consent for specific data types
	params := CreatePatientConsentParams{
		PatientID: testPatientID,
		GrantorID: testPatientID,
		GranteeID: testDoctorID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations", "care_notes", "medications"},
	}
	
	consent, err := suite.db.CreatePatientConsent(params)
	assert.NoError(suite.T(), err)

	// Test requesting subset of consented data types
	foundConsent, err := suite.db.getActiveConsent(testPatientID, testDoctorID, "treatment", []string{"conversations", "medications"})
	assert.NoError(suite.T(), err)
	assert.NotNil(suite.T(), foundConsent)
	assert.Equal(suite.T(), consent.ConsentID, foundConsent.ConsentID)

	// Test requesting data types not covered by consent
	notFoundConsent, err := suite.db.getActiveConsent(testPatientID, testDoctorID, "treatment", []string{"financial_data"})
	assert.NoError(suite.T(), err)
	assert.Nil(suite.T(), notFoundConsent)
}

func (suite *DatabaseTestSuite) TestGetActiveConsentExpired() {
	// Create expired consent
	expiredTime := time.Now().Add(-24 * time.Hour)
	suite.createTestConsentWithExpiry(&expiredTime)

	// Should not find expired consent
	foundConsent, err := suite.db.getActiveConsent(testPatientID, testDoctorID, "treatment", []string{"conversations"})
	assert.NoError(suite.T(), err)
	assert.Nil(suite.T(), foundConsent)
}

func (suite *DatabaseTestSuite) TestPHIAccessLogging() {
	err := suite.db.logPHIAccess(LogPHIAccessParams{
		AccessorID:        testDoctorID,
		PatientID:         testPatientID,
		Purpose:           "treatment",
		DataTypesAccessed: []string{"conversations", "care_notes"},
		ConsentID:         uuidPtr(uuid.New()),
		AccessGranted:     true,
		IPAddress:         stringPtr("192.168.1.1"),
		UserAgent:         stringPtr("Test/1.0"),
	})

	assert.NoError(suite.T(), err)

	// Verify log was created
	var count int
	err = suite.db.conn.QueryRow(
		"SELECT COUNT(*) FROM phi_access_log WHERE accessor_id = $1 AND patient_id = $2",
		testDoctorID, testPatientID).Scan(&count)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), 1, count)
}

func (suite *DatabaseTestSuite) TestGetUserRole() {
	role, err := suite.db.getUserRole(testPatientID)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "resident", role)

	role, err = suite.db.getUserRole(testDoctorID)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "care_staff", role)
}

func (suite *DatabaseTestSuite) TestCoversDataTypes() {
	// Test full coverage
	assert.True(suite.T(), suite.db.coversDataTypes(
		[]string{"conversations", "care_notes", "medications"},
		[]string{"conversations", "medications"},
	))

	// Test partial coverage (should fail)
	assert.False(suite.T(), suite.db.coversDataTypes(
		[]string{"conversations"},
		[]string{"conversations", "medications"},
	))

	// Test empty request (should pass)
	assert.True(suite.T(), suite.db.coversDataTypes(
		[]string{"conversations"},
		[]string{},
	))

	// Test exact match
	assert.True(suite.T(), suite.db.coversDataTypes(
		[]string{"conversations", "medications"},
		[]string{"conversations", "medications"},
	))
}

// Helper methods
func (suite *DatabaseTestSuite) createTestConsent() *PatientConsent {
	params := CreatePatientConsentParams{
		PatientID: testPatientID,
		GrantorID: testPatientID,
		GranteeID: testDoctorID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations", "care_notes"},
	}
	
	consent, err := suite.db.CreatePatientConsent(params)
	assert.NoError(suite.T(), err)
	return consent
}

func (suite *DatabaseTestSuite) createTestConsentWithExpiry(expiresAt *time.Time) *PatientConsent {
	params := CreatePatientConsentParams{
		PatientID: testPatientID,
		GrantorID: testPatientID,
		GranteeID: testDoctorID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations"},
		ExpiresAt: expiresAt,
	}
	
	consent, err := suite.db.CreatePatientConsent(params)
	assert.NoError(suite.T(), err)
	return consent
}

// Benchmark tests
func BenchmarkCreatePatientConsent(b *testing.B) {
	// Setup
	testDB, err := NewPostgresDB("postgres://chatbot_user:chatbot_password@localhost:5432/chatbot_app_test")
	if err != nil {
		b.Skip("Test database not available")
	}
	defer testDB.Close()

	// Ensure test users exist
	testDB.conn.Exec(`
		INSERT INTO users (user_id, email, password_hash, healthcare_role) VALUES
		($1, 'patient@test.com', 'hash1', 'resident'),
		($2, 'doctor@test.com', 'hash2', 'care_staff')
		ON CONFLICT (user_id) DO NOTHING`,
		testPatientID, testDoctorID)

	params := CreatePatientConsentParams{
		PatientID: testPatientID,
		GrantorID: testPatientID,
		GranteeID: testDoctorID,
		Purpose:   "treatment",
		DataTypes: []string{"conversations", "care_notes"},
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := testDB.CreatePatientConsent(params)
		if err != nil {
			b.Fatalf("Failed to create consent: %v", err)
		}
		
		// Cleanup for next iteration
		testDB.conn.Exec("DELETE FROM patient_consents WHERE patient_id = $1", testPatientID)
	}
}

func BenchmarkCheckDataAccess(b *testing.B) {
	// Setup
	testDB, err := NewPostgresDB("postgres://chatbot_user:chatbot_password@localhost:5432/chatbot_app_test")
	if err != nil {
		b.Skip("Test database not available")
	}
	defer testDB.Close()

	params := CheckDataAccessParams{
		UserID:    testPatientID,
		PatientID: testPatientID, // Self-access (fastest path)
		Purpose:   "patient_request",
		DataTypes: []string{"conversations"},
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := testDB.checkDataAccess(params)
		if err != nil {
			b.Fatalf("Failed to check data access: %v", err)
		}
	}
}

func TestDatabaseTestSuite(t *testing.T) {
	suite.Run(t, new(DatabaseTestSuite))
}