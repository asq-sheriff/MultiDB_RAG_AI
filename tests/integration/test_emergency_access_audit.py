"""
Integration tests for Enhanced Emergency Access Service with Audit Trail
Tests HIPAA-compliant emergency access with therapeutic relationship integration
"""

import pytest
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TestEmergencyAccessAuditEnhanced:
    """Test suite for Enhanced Emergency Access Service with comprehensive audit trail"""
    
    BASE_URL = "http://localhost:8084/api/v1"
    RELATIONSHIP_SERVICE_URL = "http://localhost:8083/api/v1"
    
    def setup_class(self):
        """Set up test class with service health checks"""
        # Verify emergency access service is running
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            health_data = response.json()
            assert health_data["service"] == "emergency_access_audit_enhanced"
            assert health_data["status"] == "healthy"
            print(f"✅ Emergency Access Audit Service: {health_data['status']}")
        except Exception as e:
            pytest.fail(f"Emergency Access Audit Service not available: {e}")
    
    def test_service_health_check(self):
        """Test service health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["service"] == "emergency_access_audit_enhanced"
        assert health_data["status"] == "healthy"
        assert "active_sessions" in health_data
        assert "audit_entries" in health_data
        assert "alerts_count" in health_data
        assert health_data["compliance_enabled"] is True
        assert health_data["relationship_service"] == "http://localhost:8083"
        
        print(f"🏥 Service Health: {health_data['status']}")
        print(f"📊 Active Sessions: {health_data['active_sessions']}")
        print(f"📝 Audit Entries: {health_data['audit_entries']}")
    
    def test_emergency_access_crisis_intervention(self):
        """Test emergency access for crisis intervention"""
        emergency_request = {
            "user_id": "crisis_therapist_001",
            "access_type": "crisis_intervention",
            "emergency_level": "critical",
            "justification": "Patient in immediate suicide risk requiring urgent crisis intervention access to safety protocols and emergency contacts",
            "patient_id": "patient_crisis_001",
            "resource_accessed": "crisis_intervention_protocols",
            "requested_by": "Dr. Emergency Response",
            "supervisor_id": "crisis_supervisor_001"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=emergency_request)
        assert response.status_code == 200
        
        access_data = response.json()
        assert access_data["access_granted"] is True
        assert access_data["emergency_level"] == "critical"
        assert access_data["access_type"] == "crisis_intervention"
        assert access_data["supervisor_notified"] is True
        assert "access_token" in access_data
        assert "audit_trail_id" in access_data
        assert access_data["compliance_status"] == "granted_with_monitoring"
        
        # Verify critical access has proper restrictions
        restrictions = access_data["restrictions"]
        assert "requires_supervisor_review_within_1_hour" in restrictions
        assert "full_audit_required" in restrictions
        
        print(f"🚨 Crisis Intervention Access: {access_data['request_id'][:8]}")
        print(f"⏰ Expires: {access_data['expires_at']}")
        print(f"🔒 Restrictions: {len(restrictions)} applied")
        
        return access_data["request_id"]
    
    def test_emergency_access_relationship_override(self):
        """Test emergency access with relationship override (no validation)"""
        emergency_request = {
            "user_id": "therapist_override_001",
            "access_type": "relationship_override",
            "emergency_level": "high",
            "justification": "Patient therapy session disrupted by technical issues requiring immediate access to session notes and treatment continuity protocols",
            "patient_id": "patient_override_001",
            "resource_accessed": "patient_therapy_session_data",
            "requested_by": "Dr. Relationship Override",
            "supervisor_id": "supervisor_override_001",
            "relationship_context": "primary_therapist_assumed",
            "override_reason": "System outage preventing normal relationship validation process"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=emergency_request)
        assert response.status_code == 200
        
        access_data = response.json()
        assert access_data["access_granted"] is True
        assert access_data["relationship_validated"] is False  # No relationship service validation
        assert access_data["permission_level"] == "none"
        assert access_data["supervisor_notified"] is True
        
        # Should have additional restrictions due to no relationship validation
        restrictions = access_data["restrictions"]
        assert "no_relationship_validation" in restrictions
        assert "high_audit_scrutiny" in restrictions
        
        print(f"🔄 Relationship Override Access: {access_data['request_id'][:8]}")
        print(f"⚠️ Relationship Validated: {access_data['relationship_validated']}")
        print(f"📋 Additional Restrictions: {len([r for r in restrictions if 'relationship' in r])}")
        
        return access_data["request_id"]
    
    def test_emergency_access_medical_emergency(self):
        """Test medical emergency access"""
        emergency_request = {
            "user_id": "medical_staff_001",
            "access_type": "medical_emergency",
            "emergency_level": "critical",
            "justification": "Patient experiencing medical emergency requiring immediate access to medication history and allergy information for safe treatment",
            "patient_id": "patient_medical_001",
            "resource_accessed": "patient_medical_history",
            "requested_by": "Dr. Medical Emergency",
            "supervisor_id": "medical_supervisor_001"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=emergency_request)
        assert response.status_code == 200
        
        access_data = response.json()
        assert access_data["access_granted"] is True
        assert access_data["access_type"] == "medical_emergency"
        assert access_data["emergency_level"] == "critical"
        
        print(f"🏥 Medical Emergency Access: {access_data['request_id'][:8]}")
        return access_data["request_id"]
    
    def test_emergency_access_validation_failures(self):
        """Test emergency access request validation failures"""
        # Test missing required fields
        invalid_request = {
            "user_id": "",  # Empty user ID
            "access_type": "crisis_intervention",
            "emergency_level": "high",
            "justification": "",  # Empty justification
            "resource_accessed": "",  # Empty resource
            "requested_by": ""  # Empty requester
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=invalid_request)
        assert response.status_code == 400
        
        # Test insufficient justification length
        insufficient_justification_request = {
            "user_id": "test_user",
            "access_type": "crisis_intervention",
            "emergency_level": "high",
            "justification": "Short",  # Too short (< 30 characters)
            "resource_accessed": "test_resource",
            "requested_by": "Test User"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=insufficient_justification_request)
        assert response.status_code == 403
        
        access_data = response.json()
        assert access_data["access_granted"] is False
        assert access_data["compliance_status"] == "rejected_invalid_request"
        
        print("❌ Validation Failures: Properly rejected invalid requests")
    
    def test_emergency_access_invalid_relationship_override(self):
        """Test relationship override without patient ID (should fail)"""
        invalid_override_request = {
            "user_id": "therapist_invalid_001",
            "access_type": "relationship_override",
            "emergency_level": "high",
            "justification": "This should fail because relationship override requires patient_id but none provided here",
            "resource_accessed": "patient_data",
            "requested_by": "Dr. Invalid Override"
            # Missing patient_id for relationship_override
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=invalid_override_request)
        assert response.status_code == 403
        
        access_data = response.json()
        assert access_data["access_granted"] is False
        assert access_data["compliance_status"] == "rejected_invalid_request"
        
        print("❌ Invalid Relationship Override: Properly rejected (no patient_id)")
    
    def test_audit_trail_retrieval(self):
        """Test audit trail retrieval and filtering"""
        # First, create some emergency access requests to have audit data
        self.test_emergency_access_crisis_intervention()
        time.sleep(1)  # Ensure different timestamps
        self.test_emergency_access_relationship_override()
        
        # Test basic audit trail retrieval
        response = requests.get(f"{self.BASE_URL}/audit-trail?limit=10")
        assert response.status_code == 200
        
        audit_data = response.json()
        assert "entries" in audit_data
        assert "total" in audit_data
        assert "filtered" in audit_data
        assert len(audit_data["entries"]) > 0
        
        # Verify audit entry structure
        entry = audit_data["entries"][0]
        required_fields = [
            "audit_id", "request_id", "user_id", "access_type", "emergency_level",
            "access_granted", "justification", "resource_accessed", "phi_accessed",
            "compliance_violation", "supervisor_notified", "relationship_validated",
            "actions_performed", "data_accessed", "timestamp", "client_ip",
            "user_agent", "risk_score", "review_required"
        ]
        
        for field in required_fields:
            assert field in entry, f"Missing required audit field: {field}"
        
        # Test filtering by user
        user_id = entry["user_id"]
        response = requests.get(f"{self.BASE_URL}/audit-trail?user_id={user_id}&limit=5")
        assert response.status_code == 200
        
        filtered_data = response.json()
        for entry in filtered_data["entries"]:
            assert entry["user_id"] == user_id
        
        # Test filtering by emergency level
        response = requests.get(f"{self.BASE_URL}/audit-trail?emergency_level=critical&limit=5")
        assert response.status_code == 200
        
        critical_data = response.json()
        for entry in critical_data["entries"]:
            assert entry["emergency_level"] == "critical"
        
        print(f"📝 Audit Trail: {audit_data['total']} total entries")
        print(f"🔍 Filtering: User filter returned {len(filtered_data['entries'])} entries")
        print(f"⚠️ Critical Access: {len(critical_data['entries'])} critical entries")
    
    def test_compliance_report_generation(self):
        """Test compliance report generation"""
        # Generate daily report
        response = requests.get(f"{self.BASE_URL}/compliance-report?type=daily")
        assert response.status_code == 200
        
        report_data = response.json()
        required_report_fields = [
            "report_id", "generated_at", "report_period", "total_accesses",
            "compliance_score", "violation_count", "high_risk_accesses",
            "audit_findings", "recommendations", "summary"
        ]
        
        for field in required_report_fields:
            assert field in report_data, f"Missing report field: {field}"
        
        # Verify summary structure
        summary = report_data["summary"]
        summary_fields = [
            "overall_compliance", "critical_findings", "medium_findings", "low_findings",
            "trends_and_patterns", "compliance_metrics", "recommended_actions"
        ]
        
        for field in summary_fields:
            assert field in summary, f"Missing summary field: {field}"
        
        # Verify compliance metrics
        metrics = summary["compliance_metrics"]
        metric_fields = [
            "access_grant_rate", "violation_rate", "high_risk_rate",
            "avg_risk_score", "relationship_validation_rate"
        ]
        
        for field in metric_fields:
            assert field in metrics, f"Missing metric field: {field}"
        
        print(f"📊 Compliance Report: {report_data['report_id'][:8]}")
        print(f"⭐ Compliance Score: {report_data['compliance_score']:.1f}")
        print(f"🔍 Audit Findings: {len(report_data['audit_findings'])}")
        print(f"📈 Overall Compliance: {summary['overall_compliance']}")
        
        # Test weekly report
        response = requests.get(f"{self.BASE_URL}/compliance-report?type=weekly")
        assert response.status_code == 200
        weekly_data = response.json()
        assert "weekly" in weekly_data["report_period"]
        
        print(f"📅 Weekly Report: {weekly_data['compliance_score']:.1f} compliance score")
    
    def test_active_session_management(self):
        """Test active session retrieval and management"""
        # Create an emergency access request
        emergency_request = {
            "user_id": "session_test_001",
            "access_type": "therapeutic_urgent",
            "emergency_level": "moderate",
            "justification": "Testing active session management functionality for audit trail system validation",
            "resource_accessed": "therapy_session_notes",
            "requested_by": "Dr. Session Test"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=emergency_request)
        assert response.status_code == 200
        access_data = response.json()
        request_id = access_data["request_id"]
        
        # Test session retrieval
        response = requests.get(f"{self.BASE_URL}/emergency-access/{request_id}")
        assert response.status_code == 200
        
        session_data = response.json()
        assert session_data["request_id"] == request_id
        assert session_data["access_granted"] is True
        assert "expires_at" in session_data
        
        # Test session revocation
        response = requests.delete(f"{self.BASE_URL}/emergency-access/{request_id}")
        assert response.status_code == 200
        
        revocation_data = response.json()
        assert revocation_data["request_id"] == request_id
        assert "revoked" in revocation_data["message"].lower()
        
        # Verify session no longer exists
        response = requests.get(f"{self.BASE_URL}/emergency-access/{request_id}")
        assert response.status_code == 404
        
        print(f"🔄 Session Management: Created, retrieved, and revoked {request_id[:8]}")
    
    def test_compliance_alerts_system(self):
        """Test compliance alerts generation"""
        response = requests.get(f"{self.BASE_URL}/alerts")
        assert response.status_code == 200
        
        alerts_data = response.json()
        assert "active_alerts" in alerts_data
        assert "total_alerts" in alerts_data
        
        # Create multiple high-risk accesses to trigger alerts
        for i in range(3):
            high_risk_request = {
                "user_id": "high_risk_user_001",
                "access_type": "system_maintenance",
                "emergency_level": "high",
                "justification": f"High risk system maintenance access number {i+1} for testing alert generation system",
                "resource_accessed": "system_configuration",
                "requested_by": f"Admin User {i+1}"
            }
            
            response = requests.post(f"{self.BASE_URL}/emergency-access", json=high_risk_request)
            assert response.status_code == 200
            time.sleep(0.1)  # Small delay between requests
        
        # Check if alerts were generated
        response = requests.get(f"{self.BASE_URL}/alerts")
        assert response.status_code == 200
        
        updated_alerts_data = response.json()
        
        print(f"⚠️ Compliance Alerts: {len(updated_alerts_data['active_alerts'])} active")
        print(f"📊 Total Alerts: {updated_alerts_data['total_alerts']}")
        
        # Verify alert structure if any alerts exist
        if updated_alerts_data["active_alerts"]:
            alert = updated_alerts_data["active_alerts"][0]
            alert_fields = [
                "alert_id", "request_id", "alert_type", "severity", "message",
                "triggered_at", "action_required", "compliance_impact",
                "escalation_level", "automated_actions"
            ]
            
            for field in alert_fields:
                assert field in alert, f"Missing alert field: {field}"
            
            print(f"🔔 Sample Alert: {alert['alert_type']} (Severity: {alert['severity']})")
    
    def test_risk_assessment_integration(self):
        """Test risk assessment functionality"""
        # Test low risk access
        low_risk_request = {
            "user_id": "low_risk_user_001",
            "access_type": "compliance_audit",
            "emergency_level": "low",
            "justification": "Routine compliance audit access for monthly HIPAA compliance review and documentation verification process",
            "resource_accessed": "audit_logs",
            "requested_by": "Compliance Officer",
            "supervisor_id": "compliance_supervisor_001"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=low_risk_request)
        assert response.status_code == 200
        access_data = response.json()
        
        # Test high risk access
        high_risk_request = {
            "user_id": "high_risk_user_002",
            "access_type": "safety_override",
            "emergency_level": "critical",
            "justification": "Safety override access required but insufficient justification provided here",  # Short justification increases risk
            "resource_accessed": "system_security_controls",
            "requested_by": "Unknown User"  # No supervisor increases risk
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=high_risk_request)
        assert response.status_code == 200
        high_risk_data = response.json()
        
        # Verify risk assessment through audit trail
        response = requests.get(f"{self.BASE_URL}/audit-trail?limit=2")
        assert response.status_code == 200
        
        audit_data = response.json()
        entries = audit_data["entries"]
        
        # Find the entries for our test requests
        low_risk_entry = None
        high_risk_entry = None
        
        for entry in entries:
            if entry["user_id"] == "low_risk_user_001":
                low_risk_entry = entry
            elif entry["user_id"] == "high_risk_user_002":
                high_risk_entry = entry
        
        if low_risk_entry and high_risk_entry:
            assert low_risk_entry["risk_score"] < high_risk_entry["risk_score"]
            assert high_risk_entry["review_required"] is True
            
            print(f"📊 Risk Assessment: Low Risk = {low_risk_entry['risk_score']}, High Risk = {high_risk_entry['risk_score']}")
            print(f"🔍 Review Required: Low = {low_risk_entry['review_required']}, High = {high_risk_entry['review_required']}")
    
    def test_phi_detection_and_logging(self):
        """Test PHI detection and proper logging"""
        phi_request = {
            "user_id": "phi_test_user_001",
            "access_type": "medical_emergency",
            "emergency_level": "high",
            "justification": "Medical emergency requiring access to patient health information including diagnosis and treatment records",
            "resource_accessed": "patient_medical_records",
            "requested_by": "Dr. PHI Test"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=phi_request)
        assert response.status_code == 200
        
        # Check audit trail for PHI detection
        response = requests.get(f"{self.BASE_URL}/audit-trail?user_id=phi_test_user_001&limit=1")
        assert response.status_code == 200
        
        audit_data = response.json()
        assert len(audit_data["entries"]) > 0
        
        phi_entry = audit_data["entries"][0]
        assert phi_entry["phi_accessed"] is True
        assert phi_entry["resource_accessed"] == "patient_medical_records"
        
        print(f"🔒 PHI Detection: {phi_entry['phi_accessed']} for {phi_entry['resource_accessed']}")
    
    def test_supervisor_notification_system(self):
        """Test supervisor notification requirements"""
        # Test critical access (should notify supervisor)
        critical_request = {
            "user_id": "critical_user_001",
            "access_type": "crisis_intervention",
            "emergency_level": "critical",
            "justification": "Critical patient crisis intervention requiring immediate supervisor notification and oversight for safety protocols",
            "resource_accessed": "crisis_protocols",
            "requested_by": "Crisis Team Lead",
            "supervisor_id": "crisis_supervisor_002"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=critical_request)
        assert response.status_code == 200
        
        critical_data = response.json()
        assert critical_data["supervisor_notified"] is True
        
        # Test low access (should not notify supervisor)
        low_request = {
            "user_id": "low_user_001",
            "access_type": "compliance_audit",
            "emergency_level": "low",
            "justification": "Low priority compliance audit access that should not trigger supervisor notification under normal circumstances",
            "resource_accessed": "compliance_documents",
            "requested_by": "Audit Team"
        }
        
        response = requests.post(f"{self.BASE_URL}/emergency-access", json=low_request)
        assert response.status_code == 200
        
        low_data = response.json()
        # Low access might still notify supervisor if risk assessment determines it's needed
        
        print(f"👨‍⚕️ Supervisor Notifications: Critical = {critical_data['supervisor_notified']}, Low = {low_data['supervisor_notified']}")
    
    def test_comprehensive_audit_trail_features(self):
        """Test comprehensive audit trail features"""
        # Create diverse access requests
        access_types = [
            ("crisis_intervention", "critical"),
            ("medical_emergency", "high"),
            ("therapeutic_urgent", "moderate"),
            ("compliance_audit", "low")
        ]
        
        request_ids = []
        for access_type, emergency_level in access_types:
            request = {
                "user_id": f"audit_user_{access_type}",
                "access_type": access_type,
                "emergency_level": emergency_level,
                "justification": f"Comprehensive audit trail testing for {access_type} access with {emergency_level} emergency level requiring detailed logging",
                "resource_accessed": f"{access_type}_resources",
                "requested_by": f"Dr. {access_type.title()}"
            }
            
            response = requests.post(f"{self.BASE_URL}/emergency-access", json=request)
            assert response.status_code == 200
            request_ids.append(response.json()["request_id"])
            time.sleep(0.1)
        
        # Test comprehensive audit trail retrieval
        response = requests.get(f"{self.BASE_URL}/audit-trail?limit=20")
        assert response.status_code == 200
        
        audit_data = response.json()
        assert audit_data["total"] >= len(access_types)
        
        # Verify audit entries have comprehensive information
        for entry in audit_data["entries"][:4]:  # Check first 4 entries
            assert len(entry["actions_performed"]) >= 1
            assert len(entry["data_accessed"]) >= 1
            assert entry["risk_score"] >= 0
            assert entry["compliance_violation"] is False  # Should be false for valid requests
            assert entry["timestamp"] is not None
            
            # Verify specific actions were logged
            if entry["access_granted"]:
                assert "access_granted" in entry["actions_performed"]
                assert "token_generated" in entry["actions_performed"]
            
            print(f"📋 Audit Entry: {entry['audit_id'][:8]} | Risk: {entry['risk_score']} | Actions: {len(entry['actions_performed'])}")
        
        print(f"✅ Comprehensive Audit Trail: {audit_data['total']} total entries with full logging")

def run_all_tests():
    """Run all emergency access audit tests"""
    print("🧪 Starting Enhanced Emergency Access Service Audit Trail Tests")
    print("=" * 70)
    
    test_instance = TestEmergencyAccessAuditEnhanced()
    test_instance.setup_class()
    
    # Run all tests
    test_methods = [
        test_instance.test_service_health_check,
        test_instance.test_emergency_access_crisis_intervention,
        test_instance.test_emergency_access_relationship_override,
        test_instance.test_emergency_access_medical_emergency,
        test_instance.test_emergency_access_validation_failures,
        test_instance.test_emergency_access_invalid_relationship_override,
        test_instance.test_audit_trail_retrieval,
        test_instance.test_compliance_report_generation,
        test_instance.test_active_session_management,
        test_instance.test_compliance_alerts_system,
        test_instance.test_risk_assessment_integration,
        test_instance.test_phi_detection_and_logging,
        test_instance.test_supervisor_notification_system,
        test_instance.test_comprehensive_audit_trail_features
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_method in test_methods:
        try:
            print(f"\n🔬 Running: {test_method.__name__}")
            test_method()
            print(f"✅ PASSED: {test_method.__name__}")
            passed_tests += 1
        except Exception as e:
            print(f"❌ FAILED: {test_method.__name__} - {str(e)}")
            failed_tests += 1
    
    print("\n" + "=" * 70)
    print(f"🎯 TEST SUMMARY:")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Success Rate: {(passed_tests/(passed_tests+failed_tests)*100):.1f}%")
    
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED - Enhanced Emergency Access Service with Audit Trail is working correctly!")
        return True
    else:
        print(f"⚠️ {failed_tests} tests failed - Please review the failures above")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)