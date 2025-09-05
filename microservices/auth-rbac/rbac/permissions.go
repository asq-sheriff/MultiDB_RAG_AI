// Package rbac provides comprehensive permission management for healthcare roles
package rbac

import (
	"github.com/google/uuid"
)

// Permission represents a specific permission that can be granted to a role
type Permission string

const (
	// Data Access Permissions
	PermCanAccessOwnData           Permission = "can_access_own_data"
	PermCanAccessOthersData        Permission = "can_access_others_data"
	PermCanAccessAssignedPatients  Permission = "can_access_assigned_patients"
	PermCanAccessFamilyMemberData  Permission = "can_access_family_member_data"
	
	// System Permissions
	PermCanModifySystemSettings    Permission = "can_modify_system_settings"
	PermCanViewAuditLogs          Permission = "can_view_audit_logs"
	PermCanManageUsers            Permission = "can_manage_users"
	PermCanViewSystemStats        Permission = "can_view_system_stats"
	
	// Crisis and Emergency Permissions
	PermCanEscalateCrisis         Permission = "can_escalate_crisis"
	PermCanAccessEmergencyData    Permission = "can_access_emergency_data"
	PermCanOverrideConsent        Permission = "can_override_consent"
	
	// Administrative Permissions
	PermCanManageBilling          Permission = "can_manage_billing"
	PermCanProcessPayments        Permission = "can_process_payments"
	PermCanViewFinancialReports   Permission = "can_view_financial_reports"
	PermCanManageSubscriptions    Permission = "can_manage_subscriptions"
	
	// Care Coordination Permissions
	PermCanCoordinateCare         Permission = "can_coordinate_care"
	PermCanManageTreatmentPlans   Permission = "can_manage_treatment_plans"
	PermCanViewCareNotes          Permission = "can_view_care_notes"
	PermCanEditCareNotes          Permission = "can_edit_care_notes"
	
	// Communication Permissions
	PermCanSendSystemMessages     Permission = "can_send_system_messages"
	PermCanAccessChatHistory      Permission = "can_access_chat_history"
	PermCanModerateContent        Permission = "can_moderate_content"
)

// RolePermissions maps healthcare roles to their allowed permissions
// This follows the principle of least privilege and HIPAA minimum necessary access
var RolePermissions = map[HealthcareRole]map[Permission]bool{
	RoleResident: {
		// Residents can only access their own data
		PermCanAccessOwnData:         true,
		PermCanAccessOthersData:      false,
		PermCanModifySystemSettings:  false,
		PermCanEscalateCrisis:        false,
		PermCanViewAuditLogs:         false,
		PermCanAccessChatHistory:     true,  // Own chat history only
	},
	
	RoleFamilyMember: {
		// Family members have limited access to their assigned family member's data
		PermCanAccessOwnData:          true,
		PermCanAccessOthersData:       false,
		PermCanAccessFamilyMemberData: true,   // NEW: Specific permission for assigned family member
		PermCanModifySystemSettings:   false,
		PermCanEscalateCrisis:         true,   // Can escalate concerns about their family member
		PermCanViewAuditLogs:          false,
		PermCanAccessChatHistory:      true,   // Limited to family member's care-related chats
	},
	
	RoleHealthPlanMember: {
		// Health plan members have access to their own data and can escalate issues
		PermCanAccessOwnData:         true,
		PermCanAccessOthersData:      false,
		PermCanModifySystemSettings:  false,
		PermCanEscalateCrisis:        true,
		PermCanViewAuditLogs:         false,
		PermCanAccessChatHistory:     true,
	},
	
	RoleCareStaff: {
		// Care staff have access to assigned patients and crisis management
		PermCanAccessOwnData:           true,
		PermCanAccessAssignedPatients:  true,  // Can access data for patients under their care
		PermCanAccessOthersData:        false, // Cannot access unassigned patients
		PermCanModifySystemSettings:    false,
		PermCanEscalateCrisis:          true,
		PermCanViewAuditLogs:           false, // Limited audit access
		PermCanAccessEmergencyData:     true,  // Can access in emergencies
		PermCanCoordinateCare:          true,
		PermCanViewCareNotes:           true,
		PermCanEditCareNotes:           true,
		PermCanAccessChatHistory:       true,  // For assigned patients only
		PermCanSendSystemMessages:      true,
	},
	
	RoleCaseManager: {
		// Case managers have broader access for care coordination
		PermCanAccessOwnData:           true,
		PermCanAccessAssignedPatients:  true,
		PermCanAccessOthersData:        true,  // Limited cross-patient access for coordination
		PermCanModifySystemSettings:    false,
		PermCanEscalateCrisis:          true,
		PermCanViewAuditLogs:           true,  // Can view relevant audit logs
		PermCanAccessEmergencyData:     true,
		PermCanCoordinateCare:          true,
		PermCanManageTreatmentPlans:    true,
		PermCanViewCareNotes:           true,
		PermCanEditCareNotes:           true,
		PermCanAccessChatHistory:       true,
		PermCanSendSystemMessages:      true,
	},
	
	RoleCareManager: {
		// Care managers have supervisory access over care operations
		PermCanAccessOwnData:           true,
		PermCanAccessAssignedPatients:  true,
		PermCanAccessOthersData:        true,
		PermCanModifySystemSettings:    true,  // Can modify care-related settings
		PermCanEscalateCrisis:          true,
		PermCanViewAuditLogs:           true,
		PermCanManageUsers:             true,  // Can manage care staff
		PermCanAccessEmergencyData:     true,
		PermCanOverrideConsent:         true,  // In emergency situations with proper justification
		PermCanCoordinateCare:          true,
		PermCanManageTreatmentPlans:    true,
		PermCanViewCareNotes:           true,
		PermCanEditCareNotes:           true,
		PermCanAccessChatHistory:       true,
		PermCanSendSystemMessages:      true,
		PermCanModerateContent:         true,
	},
	
	RoleAdmin: {
		// Administrators have full system access with audit requirements
		PermCanAccessOwnData:           true,
		PermCanAccessOthersData:        true,
		PermCanAccessAssignedPatients:  true,
		PermCanAccessFamilyMemberData:  true,
		PermCanModifySystemSettings:    true,
		PermCanViewAuditLogs:           true,
		PermCanManageUsers:             true,
		PermCanViewSystemStats:         true,
		PermCanEscalateCrisis:          true,
		PermCanAccessEmergencyData:     true,
		PermCanOverrideConsent:         true,
		PermCanManageBilling:           true,
		PermCanProcessPayments:         true,
		PermCanViewFinancialReports:    true,
		PermCanManageSubscriptions:     true,
		PermCanCoordinateCare:          true,
		PermCanManageTreatmentPlans:    true,
		PermCanViewCareNotes:           true,
		PermCanEditCareNotes:           true,
		PermCanAccessChatHistory:       true,
		PermCanSendSystemMessages:      true,
		PermCanModerateContent:         true,
	},
}

// HealthcareToMessageRoleMapping maps healthcare roles to allowed message sender roles
var HealthcareToMessageRoleMapping = map[HealthcareRole][]SenderRole{
	RoleResident:         {SenderUser},
	RoleFamilyMember:     {SenderUser},
	RoleHealthPlanMember: {SenderUser},
	RoleCareStaff:        {SenderUser, SenderHumanHelper},
	RoleCaseManager:      {SenderUser, SenderHumanHelper},
	RoleCareManager:      {SenderUser, SenderHumanHelper, SenderSystem},
	RoleAdmin:            {SenderUser, SenderHumanHelper, SenderSystem},
}

// PermissionChecker provides methods to check role permissions
type PermissionChecker struct{}

// NewPermissionChecker creates a new permission checker
func NewPermissionChecker() *PermissionChecker {
	return &PermissionChecker{}
}

// HasPermission checks if a healthcare role has a specific permission
func (pc *PermissionChecker) HasPermission(role HealthcareRole, permission Permission) bool {
	rolePerms, exists := RolePermissions[role]
	if !exists {
		return false
	}
	
	return rolePerms[permission]
}

// GetRolePermissions returns all permissions for a given role
func (pc *PermissionChecker) GetRolePermissions(role HealthcareRole) map[Permission]bool {
	rolePerms, exists := RolePermissions[role]
	if !exists {
		return make(map[Permission]bool)
	}
	
	// Return a copy to prevent modification
	permsCopy := make(map[Permission]bool)
	for perm, allowed := range rolePerms {
		permsCopy[perm] = allowed
	}
	return permsCopy
}

// GetAllowedMessageRoles returns the sender roles allowed for a healthcare role
func (pc *PermissionChecker) GetAllowedMessageRoles(role HealthcareRole) []SenderRole {
	roles, exists := HealthcareToMessageRoleMapping[role]
	if !exists {
		return []SenderRole{SenderUser} // Default to user role only
	}
	
	// Return a copy to prevent modification
	rolesCopy := make([]SenderRole, len(roles))
	copy(rolesCopy, roles)
	return rolesCopy
}

// CanAccessUserData checks if accessing user can access target user's data
func (pc *PermissionChecker) CanAccessUserData(
	accessingRole HealthcareRole,
	accessingUserID uuid.UUID,
	targetUserID uuid.UUID,
	purpose AccessPurpose,
) bool {
	// Users can always access their own data
	if accessingUserID == targetUserID {
		return pc.HasPermission(accessingRole, PermCanAccessOwnData)
	}
	
	// Check emergency access
	if purpose.IsEmergencyPurpose() {
		return pc.HasPermission(accessingRole, PermCanAccessEmergencyData)
	}
	
	// Check role-specific access permissions
	switch accessingRole {
	case RoleAdmin, RoleCareManager:
		return pc.HasPermission(accessingRole, PermCanAccessOthersData)
		
	case RoleCaseManager, RoleCareStaff:
		// These roles need additional validation (assigned patients, etc.)
		// This would integrate with the consent/relationship services
		return pc.HasPermission(accessingRole, PermCanAccessAssignedPatients)
		
	case RoleFamilyMember:
		// Family members need relationship validation
		// This would integrate with the relationship management service
		return pc.HasPermission(accessingRole, PermCanAccessFamilyMemberData)
		
	default:
		return false
	}
}

// RequiresAuditLog checks if an operation requires audit logging
func (pc *PermissionChecker) RequiresAuditLog(role HealthcareRole, permission Permission) bool {
	// All admin operations require audit logging
	if role == RoleAdmin {
		return true
	}
	
	// Sensitive operations require audit logging
	sensitivePerms := []Permission{
		PermCanAccessOthersData,
		PermCanAccessEmergencyData,
		PermCanOverrideConsent,
		PermCanModifySystemSettings,
		PermCanManageUsers,
	}
	
	for _, sensitivePerm := range sensitivePerms {
		if permission == sensitivePerm {
			return true
		}
	}
	
	return false
}

// AllPermissions returns all available permissions
func AllPermissions() []Permission {
	return []Permission{
		PermCanAccessOwnData,
		PermCanAccessOthersData,
		PermCanAccessAssignedPatients,
		PermCanAccessFamilyMemberData,
		PermCanModifySystemSettings,
		PermCanViewAuditLogs,
		PermCanManageUsers,
		PermCanViewSystemStats,
		PermCanEscalateCrisis,
		PermCanAccessEmergencyData,
		PermCanOverrideConsent,
		PermCanManageBilling,
		PermCanProcessPayments,
		PermCanViewFinancialReports,
		PermCanManageSubscriptions,
		PermCanCoordinateCare,
		PermCanManageTreatmentPlans,
		PermCanViewCareNotes,
		PermCanEditCareNotes,
		PermCanSendSystemMessages,
		PermCanAccessChatHistory,
		PermCanModerateContent,
	}
}

// AccessDecision represents the result of an access check
type AccessDecision struct {
	Allowed      bool                `json:"allowed"`
	Role         HealthcareRole      `json:"role"`
	ResourceType string              `json:"resource_type"`
	Action       string              `json:"action"`
	Purpose      AccessPurpose       `json:"purpose"`
	Reason       string              `json:"reason,omitempty"`
}

// CheckAccess performs comprehensive access checking
func (pc *PermissionChecker) CheckAccess(role HealthcareRole, resourceType, action string, purpose AccessPurpose) *AccessDecision {
	decision := &AccessDecision{
		Allowed:      false,
		Role:         role,
		ResourceType: resourceType,
		Action:       action,
		Purpose:      purpose,
	}
	
	// Map resource actions to permissions
	var requiredPermission Permission
	
	switch resourceType {
	case "user_data":
		switch action {
		case "read":
			requiredPermission = PermCanAccessOwnData
			if purpose.IsEmergencyPurpose() {
				requiredPermission = PermCanAccessEmergencyData
			}
		case "write", "update":
			requiredPermission = PermCanAccessOwnData // Will be enhanced to check ownership
		default:
			decision.Reason = "Unknown action for user_data"
			return decision
		}
	case "medical_records":
		switch action {
		case "read":
			requiredPermission = PermCanViewCareNotes
		case "write", "update":
			requiredPermission = PermCanEditCareNotes
		default:
			decision.Reason = "Unknown action for medical_records"
			return decision
		}
	case "system_settings":
		requiredPermission = PermCanModifySystemSettings
	case "audit_logs":
		requiredPermission = PermCanViewAuditLogs
	case "billing_data":
		switch action {
		case "read":
			requiredPermission = PermCanViewFinancialReports
		case "write", "update":
			requiredPermission = PermCanManageBilling
		default:
			decision.Reason = "Unknown action for billing_data"
			return decision
		}
	default:
		decision.Reason = "Unknown resource type"
		return decision
	}
	
	// Check if role has the required permission
	decision.Allowed = pc.HasPermission(role, requiredPermission)
	
	if !decision.Allowed {
		decision.Reason = "Insufficient permissions for this operation"
	}
	
	return decision
}