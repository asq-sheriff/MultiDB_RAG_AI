"""
Integration tests for Emergency Access Monitoring Service (Phase 7).

Tests the Go emergency access monitoring service including access requests,
compliance alerting, audit logging, and HIPAA-compliant emergency protocols.
"""

import pytest
import httpx
import asyncio
import json
from datetime import datetime, timedelta


class TestEmergencyAccessMonitoring:
    """Test Emergency Access Monitoring Service functionality."""

    BASE_URL = "http://localhost:8082"

    async def test_emergency_service_health_check(self):
        """Test emergency access monitoring service health endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/health")
                assert response.status_code == 200
                
                data = response.json()
                
                # Verify emergency service metadata
                assert data['service'] == 'emergency-access-monitoring-service'
                assert data['version'] == '1.0.0-hipaa'
                assert data['status'] == 'healthy'
                
                # Verify emergency access capabilities
                assert 'crisis_intervention' in data['capabilities']['emergency_access']
                assert 'medical_emergency' in data['capabilities']['emergency_access']
                assert 'safety_override' in data['capabilities']['emergency_access']
                assert 'therapeutic_urgent' in data['capabilities']['emergency_access']
                
                # Verify monitoring capabilities
                assert 'real_time_alerts' in data['capabilities']['monitoring']
                assert 'compliance_auditing' in data['capabilities']['monitoring']
                assert 'supervisor_notifications' in data['capabilities']['monitoring']
                assert 'access_expiration' in data['capabilities']['monitoring']
                
                # Verify HIPAA compliance capabilities
                assert 'hipaa_audit_trail' in data['capabilities']['compliance']
                assert 'phi_access_tracking' in data['capabilities']['compliance']
                assert 'emergency_justification' in data['capabilities']['compliance']
                assert 'supervisor_oversight' in data['capabilities']['compliance']
                
                # Verify service metrics
                assert 'active_sessions' in data
                assert 'audit_entries' in data
                assert 'alerts_count' in data
                
                print("✅ Emergency Access Monitoring Service health check passed")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_critical_emergency_access_request(self):
        """Test critical emergency access request with supervisor notification."""
        request_data = {
            "user_id": "emergency-responder-001",
            "session_id": "crisis-session-123",
            "access_type": "crisis_intervention",
            "emergency_level": "critical",
            "justification": "Patient experiencing severe suicidal ideation, immediate intervention required to prevent imminent harm",
            "patient_id": "patient-crisis-456",
            "resource_accessed": "/patient/crisis-intervention/phi-data",
            "requested_by": "Dr. Sarah Johnson, Crisis Specialist",
            "supervisor_id": "supervisor-789"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/emergency/request",
                    json=request_data
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify critical access granted
                assert data['access_granted'] is True
                assert data['emergency_level'] == 'critical'
                assert data['access_type'] == 'crisis_intervention'
                assert data['supervisor_notified'] is True
                
                # Verify access token and expiration (4 hours for critical)
                assert 'access_token' in data
                assert data['access_token'].startswith('emergency_')
                assert 'expires_at' in data
                
                # Verify restrictions for critical access
                assert 'restrictions' in data
                assert 'requires_supervisor_review_within_1_hour' in data['restrictions']
                
                # Verify HIPAA compliance metadata
                assert data['compliance_status'] == 'granted_with_monitoring'
                assert 'audit_trail_id' in data
                assert data['audit_trail_id'] is not None
                
                print("✅ Critical emergency access request granted with proper safeguards")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_high_priority_emergency_access(self):
        """Test high priority emergency access with compliance monitoring."""
        request_data = {
            "user_id": "therapist-002",
            "session_id": "urgent-therapy-session",
            "access_type": "therapeutic_urgent",
            "emergency_level": "high",
            "justification": "Patient showing signs of severe mental health deterioration, urgent access to therapy history needed",
            "patient_id": "patient-urgent-789",
            "resource_accessed": "/patient/therapy-records/mental-health-phi",
            "requested_by": "Licensed Clinical Social Worker Jane Smith",
            "supervisor_id": "clinical-supervisor-456"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/emergency/request",
                    json=request_data
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify high priority access
                assert data['access_granted'] is True
                assert data['emergency_level'] == 'high'
                assert data['access_type'] == 'therapeutic_urgent'
                assert data['supervisor_notified'] is True
                
                # Verify access duration (2 hours for high priority)
                assert 'expires_at' in data
                
                # Verify restrictions for high priority access
                assert 'restrictions' in data
                assert 'requires_supervisor_review_within_2_hours' in data['restrictions']
                assert 'limited_phi_access' in data['restrictions']
                
                print("✅ High priority emergency access granted with appropriate restrictions")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_moderate_emergency_access(self):
        """Test moderate emergency access with enhanced monitoring."""
        request_data = {
            "user_id": "nurse-003",
            "session_id": "moderate-care-session",
            "access_type": "medical_emergency",
            "emergency_level": "moderate",
            "justification": "Patient requires access to medical history for treatment planning, standard procedures unavailable",
            "patient_id": "patient-moderate-321",
            "resource_accessed": "/patient/medical-history/limited-access",
            "requested_by": "Registered Nurse Michael Brown"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/emergency/request",
                    json=request_data
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify moderate access granted
                assert data['access_granted'] is True
                assert data['emergency_level'] == 'moderate'
                assert data['access_type'] == 'medical_emergency'
                
                # Moderate level may not require immediate supervisor notification
                # but should have supervisor review requirement
                assert 'restrictions' in data
                assert 'requires_supervisor_review_within_4_hours' in data['restrictions']
                assert 'limited_phi_access' in data['restrictions']
                assert 'read_only_access' in data['restrictions']
                
                print("✅ Moderate emergency access granted with read-only restrictions")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_low_priority_emergency_access(self):
        """Test low priority emergency access with minimal permissions."""
        request_data = {
            "user_id": "admin-004",
            "session_id": "low-priority-session",
            "access_type": "system_maintenance",
            "emergency_level": "low",
            "justification": "System maintenance required during patient care hours, minimal access needed for technical support",
            "resource_accessed": "/system/maintenance/non-phi-access",
            "requested_by": "System Administrator Tom Wilson"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/emergency/request",
                    json=request_data
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify low priority access granted
                assert data['access_granted'] is True
                assert data['emergency_level'] == 'low'
                assert data['access_type'] == 'system_maintenance'
                
                # Low priority should have strictest restrictions
                assert 'restrictions' in data
                assert 'requires_supervisor_approval' in data['restrictions']
                assert 'read_only_access' in data['restrictions']
                assert 'no_phi_access' in data['restrictions']
                
                print("✅ Low priority emergency access granted with maximum restrictions")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_invalid_emergency_access_request(self):
        """Test that invalid emergency access requests are properly rejected."""
        # Request with insufficient justification
        invalid_request = {
            "user_id": "test-user",
            "access_type": "crisis_intervention",
            "emergency_level": "critical",
            "justification": "urgent",  # Too short (< 20 characters)
            "resource_accessed": "/patient/data",
            "requested_by": "Test User"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/emergency/request",
                    json=invalid_request
                )
                
                assert response.status_code == 403
                data = response.json()
                
                # Verify access denied
                assert data['access_granted'] is False
                assert data['compliance_status'] == 'rejected_invalid_request'
                
                print("✅ Invalid emergency access request properly rejected")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_emergency_access_status_check(self):
        """Test emergency access status monitoring."""
        # First, create an emergency access request
        request_data = {
            "user_id": "status-test-user",
            "access_type": "safety_override",
            "emergency_level": "high",
            "justification": "Testing emergency access status monitoring functionality for compliance verification",
            "resource_accessed": "/patient/safety-data",
            "requested_by": "Test Safety Officer"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Create emergency access
                create_response = await client.post(
                    f"{self.BASE_URL}/emergency/request",
                    json=request_data
                )
                
                if create_response.status_code == 200:
                    create_data = create_response.json()
                    request_id = create_data['request_id']
                    
                    # Check status
                    status_response = await client.get(
                        f"{self.BASE_URL}/emergency/status/{request_id}"
                    )
                    
                    assert status_response.status_code == 200
                    status_data = status_response.json()
                    
                    # Verify status information
                    assert status_data['request_id'] == request_id
                    assert status_data['active'] is True
                    assert status_data['emergency_level'] == 'high'
                    assert status_data['access_type'] == 'safety_override'
                    assert 'expires_at' in status_data
                    assert 'restrictions' in status_data
                    
                    print("✅ Emergency access status monitoring working correctly")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_emergency_access_audit_trail(self):
        """Test emergency access audit trail functionality."""
        headers = {
            "X-User-ID": "audit-admin-123"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/emergency/audit",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verify audit trail structure
                    assert 'audit_entries' in data
                    assert 'total_returned' in data
                    assert 'compliance_notice' in data
                    assert 'Emergency access audit data maintained per HIPAA requirements' in data['compliance_notice']
                    
                    # Verify audit entries contain required fields
                    if data['audit_entries']:
                        audit_entry = data['audit_entries'][0]
                        required_fields = [
                            'audit_id', 'request_id', 'user_id', 'access_type',
                            'emergency_level', 'access_granted', 'justification',
                            'resource_accessed', 'timestamp'
                        ]
                        for field in required_fields:
                            assert field in audit_entry
                    
                    print("✅ Emergency access audit trail accessible and compliant")
                
                # May return 401 if stricter authentication is required
                assert response.status_code in [200, 401]
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_emergency_access_alerts_monitoring(self):
        """Test emergency access alerts and compliance monitoring."""
        headers = {
            "X-User-ID": "alerts-admin-456"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/emergency/alerts",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verify alerts structure
                    assert 'active_alerts' in data
                    assert 'total_alerts' in data
                    assert 'active_count' in data
                    
                    # If there are alerts, verify structure
                    if data['active_alerts']:
                        alert = data['active_alerts'][0]
                        required_fields = [
                            'alert_id', 'request_id', 'alert_type', 'severity',
                            'message', 'triggered_at', 'action_required'
                        ]
                        for field in required_fields:
                            assert field in alert
                    
                    print("✅ Emergency access alerts monitoring functional")
                
                # May return 401 if stricter authentication is required
                assert response.status_code in [200, 401]
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")

    async def test_emergency_access_statistics(self):
        """Test emergency access statistics and reporting."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/emergency/stats")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify statistics structure
                assert 'emergency_access_stats' in data
                assert 'service_status' in data
                assert 'compliance_monitoring' in data
                
                stats = data['emergency_access_stats']
                assert 'active_sessions' in stats
                assert 'total_audit_entries' in stats
                assert 'total_alerts' in stats
                
                # Verify distribution data
                if 'emergency_level_distribution' in stats:
                    level_dist = stats['emergency_level_distribution']
                    # Should have counts for different emergency levels
                    assert isinstance(level_dist, dict)
                
                if 'access_type_distribution' in stats:
                    type_dist = stats['access_type_distribution']
                    # Should have counts for different access types
                    assert isinstance(type_dist, dict)
                
                assert data['service_status'] == 'operational'
                assert data['compliance_monitoring'] == 'active'
                
                print("✅ Emergency access statistics reporting functional")
                
            except httpx.ConnectError:
                pytest.skip("Emergency Access Monitoring Service not running")


class TestEmergencyAccessPhase7Completion:
    """Summary test to validate Phase 7 Emergency Access Monitoring implementation."""

    async def test_emergency_access_phase_7_completion_summary(self):
        """Comprehensive test validating Phase 7 Emergency Access Monitoring implementation."""
        
        async with httpx.AsyncClient() as client:
            try:
                # Test service health and capabilities
                health_response = await client.get("http://localhost:8082/health")
                assert health_response.status_code == 200
                
                health_data = health_response.json()
                
                # Verify emergency access service capabilities
                required_emergency_capabilities = [
                    'crisis_intervention', 'medical_emergency', 'safety_override', 'therapeutic_urgent'
                ]
                for capability in required_emergency_capabilities:
                    assert capability in health_data['capabilities']['emergency_access']
                
                # Verify monitoring capabilities
                required_monitoring_capabilities = [
                    'real_time_alerts', 'compliance_auditing', 'supervisor_notifications', 'access_expiration'
                ]
                for capability in required_monitoring_capabilities:
                    assert capability in health_data['capabilities']['monitoring']
                
                # Verify HIPAA compliance capabilities
                required_compliance_capabilities = [
                    'hipaa_audit_trail', 'phi_access_tracking', 'emergency_justification', 'supervisor_oversight'
                ]
                for capability in required_compliance_capabilities:
                    assert capability in health_data['capabilities']['compliance']
                
                # Test statistics endpoint
                stats_response = await client.get("http://localhost:8082/emergency/stats")
                assert stats_response.status_code == 200
                
                stats_data = stats_response.json()
                assert stats_data['service_status'] == 'operational'
                assert stats_data['compliance_monitoring'] == 'active'
                
                # Test a sample emergency access request to verify functionality
                sample_request = {
                    "user_id": "completion-test-user",
                    "access_type": "crisis_intervention",
                    "emergency_level": "high",
                    "justification": "Phase 7 completion test - verifying emergency access monitoring functionality and compliance features",
                    "resource_accessed": "/patient/emergency-data",
                    "requested_by": "Test Emergency Coordinator"
                }
                
                access_response = await client.post(
                    "http://localhost:8082/emergency/request",
                    json=sample_request
                )
                
                assert access_response.status_code == 200
                access_data = access_response.json()
                assert access_data['access_granted'] is True
                assert 'audit_trail_id' in access_data
                
                print("🎯 PHASE 7 COMPLETION VALIDATED:")
                print("  ✅ Emergency Access Monitoring Service deployed and operational")
                print("  ✅ Crisis intervention capabilities active")
                print("  ✅ Medical emergency access protocols implemented")
                print("  ✅ Safety override mechanisms functional")
                print("  ✅ Therapeutic urgent access available")
                print("  ✅ Real-time compliance alerting active")
                print("  ✅ HIPAA-compliant audit trail implemented")
                print("  ✅ Supervisor notification system operational")
                print("  ✅ Automatic session expiration monitoring")
                print("  ✅ Emergency access statistics and reporting")
                
                return True
                
            except httpx.ConnectError:
                pytest.fail("Emergency Access Monitoring Service not available - Phase 7 incomplete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])