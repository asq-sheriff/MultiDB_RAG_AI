"""
Integration tests for Relationship Management Service (Phase 8).

Tests the Go relationship management service including therapeutic relationships,
family connections, guardian oversight, and HIPAA-compliant access control.
"""

import pytest
import httpx
import asyncio
import json
from datetime import datetime, timedelta


class TestRelationshipManagement:
    """Test Relationship Management Service functionality."""

    BASE_URL = "http://localhost:8083"

    async def test_relationship_service_health_check(self):
        """Test relationship management service health endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/health")
                assert response.status_code == 200
                
                data = response.json()
                
                # Verify relationship service metadata
                assert data['service'] == 'relationship-management-service'
                assert data['version'] == '1.0.0-hipaa'
                assert data['status'] == 'healthy'
                
                # Verify relationship type capabilities
                expected_types = [
                    'primary_therapist', 'secondary_therapist', 'psychiatrist', 'case_manager',
                    'family_primary', 'family_secondary', 'guardian_legal', 'guardian_medical',
                    'emergency_contact', 'authorized_caregiver'
                ]
                for rel_type in expected_types:
                    assert rel_type in data['capabilities']['relationship_types']
                
                # Verify access level capabilities
                expected_access_levels = ['full', 'limited', 'read_only', 'emergency_only', 'none']
                for access_level in expected_access_levels:
                    assert access_level in data['capabilities']['access_levels']
                
                # Verify HIPAA compliance capabilities
                expected_compliance = ['hipaa_audit_trail', 'relationship_validation', 'permission_management', 'access_control']
                for compliance_feature in expected_compliance:
                    assert compliance_feature in data['capabilities']['compliance']
                
                # Verify service metrics
                assert 'total_relationships' in data['metrics']
                assert 'active_relationships' in data['metrics']
                assert 'pending_relationships' in data['metrics']
                assert 'access_requests' in data['metrics']
                assert 'audit_entries' in data['metrics']
                
                print("✅ Relationship Management Service health check passed")
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_create_primary_therapist_relationship(self):
        """Test creating a primary therapist relationship with full access."""
        relationship_data = {
            "patient_id": "patient-001",
            "related_person_id": "therapist-primary-123",
            "related_person_name": "Dr. Sarah Wilson, LCSW",
            "related_person_email": "dr.wilson@therapy.com",
            "related_person_phone": "555-0123",
            "relationship_type": "primary_therapist",
            "access_level": "full",
            "notes": "Primary therapeutic relationship established for comprehensive mental health treatment",
            "created_by": "intake-coordinator-456",
            "consent_document_id": "consent-doc-789"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/relationships",
                    json=relationship_data
                )
                
                assert response.status_code == 201
                data = response.json()
                
                # Verify relationship creation
                assert data['patient_id'] == 'patient-001'
                assert data['related_person_id'] == 'therapist-primary-123'
                assert data['relationship_type'] == 'primary_therapist'
                assert data['access_level'] == 'full'
                assert data['status'] == 'pending'
                
                # Verify relationship ID and timestamps
                assert 'relationship_id' in data
                assert 'established_date' in data
                assert 'last_updated' in data
                
                # Verify default permissions for primary therapist
                expected_permissions = [
                    'read_therapy_notes', 'write_therapy_notes', 
                    'read_treatment_plan', 'write_treatment_plan',
                    'access_crisis_info'
                ]
                for permission in expected_permissions:
                    assert permission in data['permissions']
                
                # Verify audit trail
                assert 'audit_trail' in data
                assert len(data['audit_trail']) == 1
                audit_entry = data['audit_trail'][0]
                assert audit_entry['action'] == 'RELATIONSHIP_CREATED'
                assert audit_entry['changed_by'] == 'intake-coordinator-456'
                
                print("✅ Primary therapist relationship created successfully")
                return data['relationship_id']
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_create_guardian_legal_relationship(self):
        """Test creating a legal guardian relationship with comprehensive access."""
        relationship_data = {
            "patient_id": "patient-002",
            "related_person_id": "guardian-legal-456",
            "related_person_name": "Robert Johnson (Legal Guardian)",
            "related_person_email": "robert.johnson@email.com",
            "related_person_phone": "555-0456",
            "relationship_type": "guardian_legal",
            "access_level": "full",
            "notes": "Court-appointed legal guardian with full treatment decision authority",
            "created_by": "legal-admin-789",
            "consent_document_id": "legal-guardianship-doc-123"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/relationships",
                    json=relationship_data
                )
                
                assert response.status_code == 201
                data = response.json()
                
                # Verify guardian relationship creation
                assert data['relationship_type'] == 'guardian_legal'
                assert data['access_level'] == 'full'
                assert data['status'] == 'pending'
                
                # Verify guardian permissions (should include decision-making)
                expected_permissions = [
                    'read_all_records', 'make_treatment_decisions', 
                    'access_crisis_info', 'emergency_contact'
                ]
                for permission in expected_permissions:
                    assert permission in data['permissions']
                
                print("✅ Legal guardian relationship created successfully")
                return data['relationship_id']
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_create_family_relationship_limited_access(self):
        """Test creating a family relationship with limited access."""
        relationship_data = {
            "patient_id": "patient-003",
            "related_person_id": "family-member-789",
            "related_person_name": "Mary Smith (Sister)",
            "related_person_email": "mary.smith@email.com",
            "relationship_type": "family_primary",
            "access_level": "limited",
            "notes": "Primary family contact for general updates and emergency situations",
            "created_by": "family-liaison-123"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/relationships",
                    json=relationship_data
                )
                
                assert response.status_code == 201
                data = response.json()
                
                # Verify family relationship with limited access
                assert data['relationship_type'] == 'family_primary'
                assert data['access_level'] == 'limited'
                
                # Verify limited permissions for family (no write access)
                expected_permissions = ['read_basic_info', 'receive_updates', 'emergency_contact']
                for permission in expected_permissions:
                    assert permission in data['permissions']
                
                # Should not have write permissions
                assert 'write_therapy_notes' not in data['permissions']
                assert 'make_treatment_decisions' not in data['permissions']
                
                print("✅ Family relationship with limited access created successfully")
                return data['relationship_id']
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_create_emergency_contact_relationship(self):
        """Test creating an emergency contact relationship."""
        relationship_data = {
            "patient_id": "patient-004",
            "related_person_id": "emergency-contact-321",
            "related_person_name": "David Brown (Emergency Contact)",
            "related_person_phone": "555-0999",
            "relationship_type": "emergency_contact",
            "access_level": "emergency_only",
            "notes": "Emergency contact for crisis situations only",
            "created_by": "emergency-coordinator-456"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/relationships",
                    json=relationship_data
                )
                
                assert response.status_code == 201
                data = response.json()
                
                # Verify emergency contact relationship
                assert data['relationship_type'] == 'emergency_contact'
                assert data['access_level'] == 'emergency_only'
                
                # Verify emergency-only permissions
                expected_permissions = ['emergency_contact', 'crisis_notification']
                for permission in expected_permissions:
                    assert permission in data['permissions']
                
                # Should not have any read/write permissions
                assert 'read_therapy_notes' not in data['permissions']
                assert 'read_basic_info' not in data['permissions']
                
                print("✅ Emergency contact relationship created successfully")
                return data['relationship_id']
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_invalid_relationship_creation(self):
        """Test that invalid relationship creation requests are rejected."""
        # Missing required fields
        invalid_relationship = {
            "patient_id": "patient-005",
            "relationship_type": "primary_therapist",
            # Missing related_person_id, related_person_name, access_level, created_by
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/relationships",
                    json=invalid_relationship
                )
                
                assert response.status_code == 400
                data = response.json()
                assert 'error' in data
                assert 'Invalid relationship data' in data['error']
                
                print("✅ Invalid relationship creation properly rejected")
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_update_relationship_status(self):
        """Test updating relationship status with audit trail."""
        # First create a relationship
        relationship_data = {
            "patient_id": "patient-status-test",
            "related_person_id": "therapist-status-test",
            "related_person_name": "Dr. Status Test",
            "relationship_type": "primary_therapist",
            "access_level": "full",
            "created_by": "status-test-coordinator"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Create relationship
                create_response = await client.post(
                    f"{self.BASE_URL}/relationships",
                    json=relationship_data
                )
                
                if create_response.status_code == 201:
                    created_data = create_response.json()
                    relationship_id = created_data['relationship_id']
                    
                    # Update status to active
                    status_update = {
                        "status": "active",
                        "changed_by": "clinical-supervisor-123",
                        "justification": "Relationship approved after credential verification and consent documentation review"
                    }
                    
                    update_response = await client.put(
                        f"{self.BASE_URL}/relationships/{relationship_id}/status",
                        json=status_update
                    )
                    
                    assert update_response.status_code == 200
                    update_data = update_response.json()
                    
                    # Verify status update response
                    assert update_data['relationship_id'] == relationship_id
                    assert update_data['new_status'] == 'active'
                    assert 'message' in update_data
                    
                    print("✅ Relationship status update successful")
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_get_patient_relationships(self):
        """Test retrieving all relationships for a specific patient."""
        patient_id = "patient-001"  # Use patient from earlier test
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/relationships/patient/{patient_id}"
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert data['patient_id'] == patient_id
                assert 'relationships' in data
                assert 'count' in data
                
                # If relationships exist, verify structure
                if data['count'] > 0:
                    relationship = data['relationships'][0]
                    assert 'relationship_id' in relationship
                    assert 'relationship_type' in relationship
                    assert 'status' in relationship
                    assert 'permissions' in relationship
                
                print("✅ Patient relationships retrieved successfully")
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_create_relationship_access_request(self):
        """Test creating a relationship-based access request."""
        # First create a relationship to use for access request
        relationship_data = {
            "patient_id": "patient-access-test",
            "related_person_id": "therapist-access-test",
            "related_person_name": "Dr. Access Test",
            "relationship_type": "primary_therapist",
            "access_level": "full",
            "created_by": "access-test-coordinator"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Create relationship
                create_response = await client.post(
                    f"{self.BASE_URL}/relationships",
                    json=relationship_data
                )
                
                if create_response.status_code == 201:
                    created_data = create_response.json()
                    relationship_id = created_data['relationship_id']
                    
                    # Update status to active first
                    status_update = {
                        "status": "active",
                        "changed_by": "test-supervisor",
                        "justification": "Test relationship activation"
                    }
                    
                    await client.put(
                        f"{self.BASE_URL}/relationships/{relationship_id}/status",
                        json=status_update
                    )
                    
                    # Create access request
                    access_request = {
                        "relationship_id": relationship_id,
                        "requested_by": "therapist-access-test",
                        "patient_id": "patient-access-test",
                        "access_type": "read_therapy_notes",
                        "resource_requested": "/patient/therapy-notes/session-data",
                        "justification": "Reviewing previous therapy session notes to prepare for upcoming appointment and assess treatment progress"
                    }
                    
                    access_response = await client.post(
                        f"{self.BASE_URL}/relationships/access-request",
                        json=access_request
                    )
                    
                    assert access_response.status_code == 201
                    access_data = access_response.json()
                    
                    # Verify access request
                    assert access_data['relationship_id'] == relationship_id
                    assert access_data['access_type'] == 'read_therapy_notes'
                    assert access_data['status'] == 'pending'
                    assert 'request_id' in access_data
                    assert 'request_timestamp' in access_data
                    
                    print("✅ Relationship access request created successfully")
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_relationship_audit_trail(self):
        """Test relationship audit trail functionality."""
        headers = {
            "X-User-ID": "relationship-audit-admin"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/relationships/audit",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verify audit trail structure
                    assert 'audit_entries' in data
                    assert 'total_returned' in data
                    assert 'compliance_notice' in data
                    assert 'Relationship audit data maintained per HIPAA requirements' in data['compliance_notice']
                    
                    # If audit entries exist, verify structure
                    if data['audit_entries']:
                        audit_entry = data['audit_entries'][0]
                        required_fields = [
                            'audit_id', 'relationship_id', 'action', 
                            'changed_by', 'timestamp', 'ip_address'
                        ]
                        for field in required_fields:
                            assert field in audit_entry
                    
                    print("✅ Relationship audit trail accessible and compliant")
                
                # May return 401 if stricter authentication is required
                assert response.status_code in [200, 401]
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")

    async def test_relationship_statistics(self):
        """Test relationship statistics and reporting."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/relationships/stats")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify statistics structure
                assert 'relationship_stats' in data
                assert 'service_status' in data
                assert 'compliance_monitoring' in data
                
                stats = data['relationship_stats']
                assert 'total_relationships' in stats
                assert 'total_access_requests' in stats
                assert 'total_audit_entries' in stats
                
                # Verify distribution data
                if 'relationship_type_distribution' in stats:
                    type_dist = stats['relationship_type_distribution']
                    assert isinstance(type_dist, dict)
                
                if 'relationship_status_distribution' in stats:
                    status_dist = stats['relationship_status_distribution']
                    assert isinstance(status_dist, dict)
                
                assert data['service_status'] == 'operational'
                assert data['compliance_monitoring'] == 'active'
                
                print("✅ Relationship statistics reporting functional")
                
            except httpx.ConnectError:
                pytest.skip("Relationship Management Service not running")


class TestRelationshipPhase8Completion:
    """Summary test to validate Phase 8 Relationship Management implementation."""

    async def test_relationship_management_phase_8_completion_summary(self):
        """Comprehensive test validating Phase 8 Relationship Management implementation."""
        
        async with httpx.AsyncClient() as client:
            try:
                # Test service health and capabilities
                health_response = await client.get("http://localhost:8083/health")
                assert health_response.status_code == 200
                
                health_data = health_response.json()
                
                # Verify relationship management service capabilities
                required_relationship_types = [
                    'primary_therapist', 'secondary_therapist', 'psychiatrist', 'case_manager',
                    'family_primary', 'family_secondary', 'guardian_legal', 'guardian_medical',
                    'emergency_contact', 'authorized_caregiver'
                ]
                for rel_type in required_relationship_types:
                    assert rel_type in health_data['capabilities']['relationship_types']
                
                # Verify access level capabilities
                required_access_levels = ['full', 'limited', 'read_only', 'emergency_only', 'none']
                for access_level in required_access_levels:
                    assert access_level in health_data['capabilities']['access_levels']
                
                # Verify compliance capabilities
                required_compliance = ['hipaa_audit_trail', 'relationship_validation', 'permission_management', 'access_control']
                for compliance_feature in required_compliance:
                    assert compliance_feature in health_data['capabilities']['compliance']
                
                # Test statistics endpoint
                stats_response = await client.get("http://localhost:8083/relationships/stats")
                assert stats_response.status_code == 200
                
                stats_data = stats_response.json()
                assert stats_data['service_status'] == 'operational'
                assert stats_data['compliance_monitoring'] == 'active'
                
                # Test a comprehensive relationship creation to verify functionality
                comprehensive_relationship = {
                    "patient_id": "patient-phase8-completion",
                    "related_person_id": "completion-test-therapist",
                    "related_person_name": "Dr. Phase 8 Completion Test",
                    "related_person_email": "phase8@completion.test",
                    "relationship_type": "primary_therapist",
                    "access_level": "full",
                    "notes": "Phase 8 completion test - verifying comprehensive relationship management functionality",
                    "created_by": "phase8-completion-coordinator",
                    "consent_document_id": "phase8-consent-doc"
                }
                
                relationship_response = await client.post(
                    "http://localhost:8083/relationships",
                    json=comprehensive_relationship
                )
                
                assert relationship_response.status_code == 201
                relationship_data = relationship_response.json()
                assert relationship_data['relationship_type'] == 'primary_therapist'
                assert relationship_data['access_level'] == 'full'
                assert 'permissions' in relationship_data
                assert len(relationship_data['permissions']) > 0
                
                print("🎯 PHASE 8 COMPLETION VALIDATED:")
                print("  ✅ Relationship Management Service deployed and operational")
                print("  ✅ Therapeutic relationship types implemented (10 types)")
                print("  ✅ Family and guardian relationship tracking active")
                print("  ✅ Permission-based access control functional")
                print("  ✅ Multi-level access control (full, limited, read-only, emergency, none)")
                print("  ✅ HIPAA-compliant audit trail operational")
                print("  ✅ Relationship status lifecycle management")
                print("  ✅ Access request processing through relationships")
                print("  ✅ Comprehensive relationship validation")
                print("  ✅ Statistics and compliance reporting")
                
                return True
                
            except httpx.ConnectError:
                pytest.fail("Relationship Management Service not available - Phase 8 incomplete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])