// Package rbac provides Role-Based Access Control for healthcare applications
package rbac

import (
	"fmt"
)

// HealthcareRole represents different healthcare roles in the system
// Matches the Python HealthcareRole enum for consistency
type HealthcareRole string

const (
	RoleResident          HealthcareRole = "resident"
	RoleFamilyMember      HealthcareRole = "family"
	RoleCareStaff         HealthcareRole = "care_staff"
	RoleCareManager       HealthcareRole = "care_manager"
	RoleAdmin             HealthcareRole = "admin"
	RoleHealthPlanMember  HealthcareRole = "hp_member"
	RoleCaseManager       HealthcareRole = "case_manager"
)

// AllHealthcareRoles returns all valid healthcare roles
func AllHealthcareRoles() []HealthcareRole {
	return []HealthcareRole{
		RoleResident,
		RoleFamilyMember,
		RoleCareStaff,
		RoleCareManager,
		RoleAdmin,
		RoleHealthPlanMember,
		RoleCaseManager,
	}
}

// IsValid checks if the healthcare role is valid
func (r HealthcareRole) IsValid() bool {
	for _, role := range AllHealthcareRoles() {
		if r == role {
			return true
		}
	}
	return false
}

// String returns the string representation of the role
func (r HealthcareRole) String() string {
	return string(r)
}

// GetRoleHierarchyLevel returns the hierarchy level for role precedence
// Lower numbers indicate higher precedence
func (r HealthcareRole) GetRoleHierarchyLevel() int {
	switch r {
	case RoleAdmin:
		return 1
	case RoleCareManager:
		return 2
	case RoleCaseManager:
		return 3
	case RoleCareStaff:
		return 4
	case RoleHealthPlanMember:
		return 5
	case RoleFamilyMember:
		return 6
	case RoleResident:
		return 7
	default:
		return 999 // Unknown role has lowest precedence
	}
}

// HasHigherPrecedence checks if this role has higher precedence than another
func (r HealthcareRole) HasHigherPrecedence(other HealthcareRole) bool {
	return r.GetRoleHierarchyLevel() < other.GetRoleHierarchyLevel()
}

// SenderRole represents message sender roles in conversation
type SenderRole string

const (
	SenderUser        SenderRole = "user"
	SenderAssistant   SenderRole = "assistant" 
	SenderSystem      SenderRole = "system"
	SenderHumanHelper SenderRole = "human_helper"
)

// AllSenderRoles returns all valid sender roles
func AllSenderRoles() []SenderRole {
	return []SenderRole{
		SenderUser,
		SenderAssistant,
		SenderSystem,
		SenderHumanHelper,
	}
}

// IsValid checks if the sender role is valid
func (s SenderRole) IsValid() bool {
	for _, role := range AllSenderRoles() {
		if s == role {
			return true
		}
	}
	return false
}

// AccessPurpose represents the purpose for accessing PHI data
type AccessPurpose string

const (
	PurposeTreatment       AccessPurpose = "treatment"
	PurposePayment         AccessPurpose = "payment"
	PurposeOperations      AccessPurpose = "operations"
	PurposeEmergency       AccessPurpose = "emergency"
	PurposePatientRequest  AccessPurpose = "patient_request"
	PurposeLegalRequirement AccessPurpose = "legal_requirement"
	PurposeFamilyCare      AccessPurpose = "family_care"
)

// AllAccessPurposes returns all valid access purposes
func AllAccessPurposes() []AccessPurpose {
	return []AccessPurpose{
		PurposeTreatment,
		PurposePayment,
		PurposeOperations,
		PurposeEmergency,
		PurposePatientRequest,
		PurposeLegalRequirement,
		PurposeFamilyCare,
	}
}

// IsValid checks if the access purpose is valid
func (a AccessPurpose) IsValid() bool {
	for _, purpose := range AllAccessPurposes() {
		if a == purpose {
			return true
		}
	}
	return false
}

// IsEmergencyPurpose checks if this is an emergency access purpose
func (a AccessPurpose) IsEmergencyPurpose() bool {
	return a == PurposeEmergency
}

// GetHealthcareRoleByString converts string to HealthcareRole with validation
func GetHealthcareRoleByString(roleStr string) (HealthcareRole, error) {
	role := HealthcareRole(roleStr)
	if !role.IsValid() {
		return "", fmt.Errorf("invalid healthcare role: %s", roleStr)
	}
	return role, nil
}

// GetAccessPurposeByString converts string to AccessPurpose with validation
func GetAccessPurposeByString(purposeStr string) (AccessPurpose, error) {
	purpose := AccessPurpose(purposeStr)
	if !purpose.IsValid() {
		return "", fmt.Errorf("invalid access purpose: %s", purposeStr)
	}
	return purpose, nil
}