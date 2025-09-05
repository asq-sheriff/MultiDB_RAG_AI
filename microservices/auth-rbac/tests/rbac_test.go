// Package tests provides comprehensive testing for the auth-rbac service
package tests

import (
	"testing"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/google/uuid"
	
	"auth-rbac-service/rbac"
	"auth-rbac-service/models"
)

func TestHealthcareRoles(t *testing.T) {
	t.Run("AllRolesAreValid", func(t *testing.T) {
		roles := rbac.AllHealthcareRoles()
		assert.Len(t, roles, 7, "Should have 7 healthcare roles")
		
		for _, role := range roles {
			assert.True(t, role.IsValid(), "Role %s should be valid", role)
		}
	})
	
	t.Run("RoleValidation", func(t *testing.T) {
		validRole := rbac.RoleAdmin
		assert.True(t, validRole.IsValid())
		
		invalidRole := rbac.HealthcareRole("invalid_role")
		assert.False(t, invalidRole.IsValid())
	})
	
	t.Run("RoleHierarchy", func(t *testing.T) {
		admin := rbac.RoleAdmin
		careStaff := rbac.RoleCareStaff
		resident := rbac.RoleResident
		
		assert.True(t, admin.HasHigherPrecedence(careStaff))
		assert.True(t, careStaff.HasHigherPrecedence(resident))
		assert.True(t, admin.HasHigherPrecedence(resident))
		
		assert.False(t, resident.HasHigherPrecedence(admin))
		assert.False(t, careStaff.HasHigherPrecedence(admin))
	})
	
	t.Run("RoleStringConversion", func(t *testing.T) {
		role := rbac.RoleAdmin
		assert.Equal(t, "admin", role.String())
		
		parsedRole, err := rbac.GetHealthcareRoleByString("admin")
		require.NoError(t, err)
		assert.Equal(t, role, parsedRole)
		
		_, err = rbac.GetHealthcareRoleByString("invalid")
		assert.Error(t, err)
	})
}

func TestAccessPurposes(t *testing.T) {
	t.Run("AllPurposesAreValid", func(t *testing.T) {
		purposes := rbac.AllAccessPurposes()
		assert.Len(t, purposes, 7, "Should have 7 access purposes")
		
		for _, purpose := range purposes {
			assert.True(t, purpose.IsValid(), "Purpose %s should be valid", purpose)
		}
	})
	
	t.Run("EmergencyPurposeDetection", func(t *testing.T) {
		emergency := rbac.PurposeEmergency
		assert.True(t, emergency.IsEmergencyPurpose())
		
		treatment := rbac.PurposeTreatment
		assert.False(t, treatment.IsEmergencyPurpose())
	})
}

func TestPermissionChecker(t *testing.T) {
	checker := rbac.NewPermissionChecker()
	
	t.Run("AdminPermissions", func(t *testing.T) {
		// Admin should have all permissions
		adminPerms := checker.GetRolePermissions(rbac.RoleAdmin)
		
		// Test key permissions
		assert.True(t, adminPerms[rbac.PermCanAccessOwnData])
		assert.True(t, adminPerms[rbac.PermCanAccessOthersData])
		assert.True(t, adminPerms[rbac.PermCanModifySystemSettings])
		assert.True(t, adminPerms[rbac.PermCanViewAuditLogs])
		assert.True(t, adminPerms[rbac.PermCanManageUsers])
		assert.True(t, adminPerms[rbac.PermCanAccessEmergencyData])
	})
	
	t.Run("ResidentPermissions", func(t *testing.T) {
		// Resident should have very limited permissions
		residentPerms := checker.GetRolePermissions(rbac.RoleResident)
		
		assert.True(t, residentPerms[rbac.PermCanAccessOwnData])
		assert.False(t, residentPerms[rbac.PermCanAccessOthersData])
		assert.False(t, residentPerms[rbac.PermCanModifySystemSettings])
		assert.False(t, residentPerms[rbac.PermCanViewAuditLogs])
		assert.False(t, residentPerms[rbac.PermCanManageUsers])
	})
	
	t.Run("CareStaffPermissions", func(t *testing.T) {
		// Care staff should have patient care permissions
		careStaffPerms := checker.GetRolePermissions(rbac.RoleCareStaff)
		
		assert.True(t, careStaffPerms[rbac.PermCanAccessOwnData])
		assert.True(t, careStaffPerms[rbac.PermCanAccessAssignedPatients])
		assert.False(t, careStaffPerms[rbac.PermCanAccessOthersData])
		assert.True(t, careStaffPerms[rbac.PermCanAccessEmergencyData])
		assert.True(t, careStaffPerms[rbac.PermCanCoordinateCare])
		assert.False(t, careStaffPerms[rbac.PermCanModifySystemSettings])
	})
	
	t.Run("FamilyMemberPermissions", func(t *testing.T) {
		// Family members should have limited access to family member data
		familyPerms := checker.GetRolePermissions(rbac.RoleFamilyMember)
		
		assert.True(t, familyPerms[rbac.PermCanAccessOwnData])
		assert.True(t, familyPerms[rbac.PermCanAccessFamilyMemberData])
		assert.False(t, familyPerms[rbac.PermCanAccessOthersData])
		assert.True(t, familyPerms[rbac.PermCanEscalateCrisis])
		assert.False(t, familyPerms[rbac.PermCanModifySystemSettings])
	})
	
	t.Run("HasPermissionCheck", func(t *testing.T) {
		// Test direct permission checking
		assert.True(t, checker.HasPermission(rbac.RoleAdmin, rbac.PermCanManageUsers))
		assert.False(t, checker.HasPermission(rbac.RoleResident, rbac.PermCanManageUsers))
		assert.True(t, checker.HasPermission(rbac.RoleCareStaff, rbac.PermCanAccessEmergencyData))
		assert.False(t, checker.HasPermission(rbac.RoleResident, rbac.PermCanAccessEmergencyData))
	})
}

func TestMessageRoleMapping(t *testing.T) {
	checker := rbac.NewPermissionChecker()
	
	t.Run("ResidentMessageRoles", func(t *testing.T) {
		roles := checker.GetAllowedMessageRoles(rbac.RoleResident)
		assert.Equal(t, []rbac.SenderRole{rbac.SenderUser}, roles)
	})
	
	t.Run("CareStaffMessageRoles", func(t *testing.T) {
		roles := checker.GetAllowedMessageRoles(rbac.RoleCareStaff)
		expectedRoles := []rbac.SenderRole{rbac.SenderUser, rbac.SenderHumanHelper}
		assert.ElementsMatch(t, expectedRoles, roles)
	})
	
	t.Run("AdminMessageRoles", func(t *testing.T) {
		roles := checker.GetAllowedMessageRoles(rbac.RoleAdmin)
		expectedRoles := []rbac.SenderRole{rbac.SenderUser, rbac.SenderHumanHelper, rbac.SenderSystem}
		assert.ElementsMatch(t, expectedRoles, roles)
	})
}

func TestAccessControlLogic(t *testing.T) {
	checker := rbac.NewPermissionChecker()
	
	t.Run("SameUserAccess", func(t *testing.T) {
		userID := uuid.New()
		
		// Users should be able to access their own data regardless of role
		canAccess := checker.CanAccessUserData(rbac.RoleResident, userID, userID, rbac.PurposeTreatment)
		assert.True(t, canAccess)
		
		canAccess = checker.CanAccessUserData(rbac.RoleCareStaff, userID, userID, rbac.PurposeTreatment)
		assert.True(t, canAccess)
	})
	
	t.Run("EmergencyAccess", func(t *testing.T) {
		accessingUser := uuid.New()
		targetUser := uuid.New()
		
		// Care staff should have emergency access
		canAccess := checker.CanAccessUserData(rbac.RoleCareStaff, accessingUser, targetUser, rbac.PurposeEmergency)
		assert.True(t, canAccess)
		
		// Residents should not have emergency access to others
		canAccess = checker.CanAccessUserData(rbac.RoleResident, accessingUser, targetUser, rbac.PurposeEmergency)
		assert.False(t, canAccess)
		
		// Admin should have emergency access
		canAccess = checker.CanAccessUserData(rbac.RoleAdmin, accessingUser, targetUser, rbac.PurposeEmergency)
		assert.True(t, canAccess)
	})
	
	t.Run("CrossUserAccess", func(t *testing.T) {
		accessingUser := uuid.New()
		targetUser := uuid.New()
		
		// Admin should be able to access others' data
		canAccess := checker.CanAccessUserData(rbac.RoleAdmin, accessingUser, targetUser, rbac.PurposeTreatment)
		assert.True(t, canAccess)
		
		// Care Manager should be able to access others' data
		canAccess = checker.CanAccessUserData(rbac.RoleCareManager, accessingUser, targetUser, rbac.PurposeTreatment)
		assert.True(t, canAccess)
		
		// Resident should not be able to access others' data
		canAccess = checker.CanAccessUserData(rbac.RoleResident, accessingUser, targetUser, rbac.PurposeTreatment)
		assert.False(t, canAccess)
	})
}

func TestAuditRequirements(t *testing.T) {
	checker := rbac.NewPermissionChecker()
	
	t.Run("AdminOperationsRequireAudit", func(t *testing.T) {
		// All admin operations should require audit logging
		requiresAudit := checker.RequiresAuditLog(rbac.RoleAdmin, rbac.PermCanAccessOwnData)
		assert.True(t, requiresAudit)
		
		requiresAudit = checker.RequiresAuditLog(rbac.RoleAdmin, rbac.PermCanManageUsers)
		assert.True(t, requiresAudit)
	})
	
	t.Run("SensitiveOperationsRequireAudit", func(t *testing.T) {
		// Sensitive operations should require audit regardless of role
		requiresAudit := checker.RequiresAuditLog(rbac.RoleCareStaff, rbac.PermCanAccessEmergencyData)
		assert.True(t, requiresAudit)
		
		requiresAudit = checker.RequiresAuditLog(rbac.RoleCareManager, rbac.PermCanOverrideConsent)
		assert.True(t, requiresAudit)
	})
	
	t.Run("RegularOperationsNoAudit", func(t *testing.T) {
		// Regular operations shouldn't require audit for non-admin roles
		requiresAudit := checker.RequiresAuditLog(rbac.RoleResident, rbac.PermCanAccessOwnData)
		assert.False(t, requiresAudit)
		
		requiresAudit = checker.RequiresAuditLog(rbac.RoleCareStaff, rbac.PermCanCoordinateCare)
		assert.False(t, requiresAudit)
	})
}

func TestUserModel(t *testing.T) {
	t.Run("UserProfile", func(t *testing.T) {
		user := &models.User{
			ID:               uuid.New(),
			Email:            "test@example.com",
			FirstName:        "John",
			LastName:         "Doe",
			HealthcareRole:   rbac.RoleCareStaff,
			SubscriptionPlan: "pro",
			IsActive:         true,
			IsVerified:       true,
			IsSuperuser:      false,
			PasswordHash:     "hashed_password",
		}
		
		profile := user.ToProfile()
		
		assert.Equal(t, user.ID, profile.ID)
		assert.Equal(t, user.Email, profile.Email)
		assert.Equal(t, user.FirstName, profile.FirstName)
		assert.Equal(t, user.LastName, profile.LastName)
		assert.Equal(t, user.HealthcareRole, profile.HealthcareRole)
		assert.Equal(t, user.SubscriptionPlan, profile.SubscriptionPlan)
		assert.Equal(t, user.IsActive, profile.IsActive)
		assert.Equal(t, user.IsVerified, profile.IsVerified)
		
		// Password hash should not be included in profile
		// This is implicit since UserProfile doesn't have a PasswordHash field
	})
	
	t.Run("UserFullName", func(t *testing.T) {
		user := &models.User{
			FirstName: "John",
			LastName:  "Doe",
			Email:     "john.doe@example.com",
		}
		
		assert.Equal(t, "John Doe", user.GetFullName())
		
		// Test with empty names
		user.FirstName = ""
		user.LastName = ""
		assert.Equal(t, "john.doe@example.com", user.GetFullName())
	})
	
	t.Run("AdminRoleCheck", func(t *testing.T) {
		adminUser := &models.User{HealthcareRole: rbac.RoleAdmin}
		assert.True(t, adminUser.IsAdminRole())
		
		careManagerUser := &models.User{HealthcareRole: rbac.RoleCareManager}
		assert.True(t, careManagerUser.IsAdminRole())
		
		careStaffUser := &models.User{HealthcareRole: rbac.RoleCareStaff}
		assert.False(t, careStaffUser.IsAdminRole())
		
		residentUser := &models.User{HealthcareRole: rbac.RoleResident}
		assert.False(t, residentUser.IsAdminRole())
	})
	
	t.Run("EmergencyDataAccess", func(t *testing.T) {
		careStaffUser := &models.User{HealthcareRole: rbac.RoleCareStaff}
		assert.True(t, careStaffUser.CanAccessEmergencyData())
		
		residentUser := &models.User{HealthcareRole: rbac.RoleResident}
		assert.False(t, residentUser.CanAccessEmergencyData())
		
		adminUser := &models.User{HealthcareRole: rbac.RoleAdmin}
		assert.True(t, adminUser.CanAccessEmergencyData())
	})
	
	t.Run("AllowedSenderRoles", func(t *testing.T) {
		careStaffUser := &models.User{HealthcareRole: rbac.RoleCareStaff}
		allowedRoles := careStaffUser.GetAllowedSenderRoles()
		expectedRoles := []rbac.SenderRole{rbac.SenderUser, rbac.SenderHumanHelper}
		assert.ElementsMatch(t, expectedRoles, allowedRoles)
		
		residentUser := &models.User{HealthcareRole: rbac.RoleResident}
		allowedRoles = residentUser.GetAllowedSenderRoles()
		expectedRoles = []rbac.SenderRole{rbac.SenderUser}
		assert.ElementsMatch(t, expectedRoles, allowedRoles)
	})
}

func TestRequestValidation(t *testing.T) {
	t.Run("ValidRegistrationRequest", func(t *testing.T) {
		req := &models.RegisterRequest{
			Email:           "test@example.com",
			Password:        "SecurePassword123!",
			ConfirmPassword: "SecurePassword123!",
			FirstName:       "John",
			LastName:        "Doe",
			HealthcareRole:  rbac.RoleCareStaff,
		}
		
		err := req.Validate()
		assert.NoError(t, err)
	})
	
	t.Run("PasswordMismatch", func(t *testing.T) {
		req := &models.RegisterRequest{
			Email:           "test@example.com",
			Password:        "SecurePassword123!",
			ConfirmPassword: "DifferentPassword123!",
			FirstName:       "John",
			LastName:        "Doe",
			HealthcareRole:  rbac.RoleCareStaff,
		}
		
		err := req.Validate()
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "passwords do not match")
	})
	
	t.Run("InvalidHealthcareRole", func(t *testing.T) {
		req := &models.RegisterRequest{
			Email:           "test@example.com",
			Password:        "SecurePassword123!",
			ConfirmPassword: "SecurePassword123!",
			FirstName:       "John",
			LastName:        "Doe",
			HealthcareRole:  rbac.HealthcareRole("invalid_role"),
		}
		
		err := req.Validate()
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "invalid healthcare role")
	})
	
	t.Run("ValidPasswordChangeRequest", func(t *testing.T) {
		req := &models.ChangePasswordRequest{
			CurrentPassword: "OldPassword123!",
			NewPassword:     "NewPassword123!",
			ConfirmPassword: "NewPassword123!",
		}
		
		err := req.Validate()
		assert.NoError(t, err)
	})
	
	t.Run("SamePasswordChange", func(t *testing.T) {
		req := &models.ChangePasswordRequest{
			CurrentPassword: "SamePassword123!",
			NewPassword:     "SamePassword123!",
			ConfirmPassword: "SamePassword123!",
		}
		
		err := req.Validate()
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "new password must be different")
	})
}