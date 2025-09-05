"""
Integration tests for Comprehensive Audit Logging Service
Tests centralized HIPAA-compliant audit logging functionality
"""

import pytest
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TestAuditLoggingService:
    """Test suite for Comprehensive Audit Logging Service"""
    
    BASE_URL = "http://localhost:8085/api/v1"
    
    def setup_class(self):
        """Set up test class with service health checks"""
        # Verify audit logging service is running
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            health_data = response.json()
            assert "audit-logging-service" in health_data["service"]
            assert health_data["status"] == "healthy"
            print(f"✅ Audit Logging Service: {health_data['status']}")
        except Exception as e:
            pytest.fail(f"Audit Logging Service not available: {e}")
    
    def test_service_health_check(self):
        """Test service health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "audit-logging-service" in health_data["service"]
        assert health_data["status"] == "healthy"
        assert "total_entries" in health_data
        assert "max_entries" in health_data
        assert health_data["retention_days"] == 2555  # 7 years HIPAA compliance
        
        print(f"🏥 Service Health: {health_data['status']}")
        print(f"📊 Total Entries: {health_data['total_entries']}")
        print(f"📋 Max Entries: {health_data['max_entries']}")
        print(f"⏰ Retention: {health_data['retention_days']} days")
    
    def test_log_phi_access_audit_entry(self):
        """Test logging PHI access audit entry"""
        audit_entry = {
            "event_type": "phi_access",
            "log_level": "info",
            "service_name": "therapeutic-service",
            "user_id": "therapist_001",
            "patient_id": "patient_001",
            "session_id": "session_123",
            "request_id": "req_456",
            "event": {
                "action": "view_therapy_notes",
                "resource": "patient_therapy_session_notes",
                "resource_type": "therapy_document",
                "description": "Therapist accessed patient therapy session notes for treatment continuity",
                "success": True,
                "context": {
                    "therapy_session_id": "ts_789",
                    "access_reason": "treatment_planning",
                    "document_count": 3
                }
            },
            "client_ip": "192.168.1.100",
            "user_agent": "TherapeuticApp/1.0.0",
            "request_path": "/api/v1/therapy/sessions/notes",
            "http_method": "GET",
            "status_code": 200,
            "phi_accessed": True,
            "data_sensitivity": "high",
            "compliance_context": "therapeutic_treatment_access",
            "tags": ["phi", "therapy", "treatment_notes"],
            "metadata": {
                "session_duration": 3600,
                "notes_viewed": ["initial_assessment", "progress_notes", "treatment_plan"]
            }
        }
        
        response = requests.post(f"{self.BASE_URL}/audit-entries", json=audit_entry)
        assert response.status_code == 201
        
        result = response.json()
        assert result["message"] == "Audit entry logged successfully"
        assert "audit_id" in result
        
        print(f"✅ PHI Access Audit Entry Logged: {audit_entry['event']['action']}")
        return result.get("audit_id")
    
    def test_log_emergency_access_audit_entry(self):
        """Test logging emergency access audit entry"""
        audit_entry = {
            "event_type": "emergency_access",
            "log_level": "warning",
            "service_name": "emergency-access-service",
            "user_id": "emergency_staff_001",
            "patient_id": "patient_crisis_001",
            "request_id": "emergency_req_789",
            "event": {
                "action": "emergency_access_granted",
                "resource": "patient_crisis_intervention_records",
                "description": "Emergency access granted for crisis intervention requiring immediate patient history",
                "success": True,
                "context": {
                    "emergency_level": "critical",
                    "access_type": "crisis_intervention",
                    "justification": "Patient in immediate danger, requires access to safety protocols and emergency contacts",
                    "supervisor_notified": True,
                    "relationship_validated": False
                }
            },
            "phi_accessed": True,
            "data_sensitivity": "critical",
            "compliance_context": "emergency_crisis_intervention",
            "tags": ["emergency", "crisis", "critical_access"],
            "metadata": {
                "emergency_duration": 7200,  # 2 hours
                "protocols_accessed": ["suicide_risk_assessment", "emergency_contacts", "medication_allergies"]
            }
        }
        
        response = requests.post(f"{self.BASE_URL}/audit-entries", json=audit_entry)
        assert response.status_code == 201
        
        result = response.json()
        assert result["message"] == "Audit entry logged successfully"
        
        print(f"🚨 Emergency Access Audit Entry Logged: {audit_entry['event']['action']}")
        return result.get("audit_id")
    
    def test_log_relationship_management_audit_entry(self):
        """Test logging relationship management audit entry"""
        audit_entry = {
            "event_type": "relationship_change",
            "log_level": "info",
            "service_name": "relationship-management-service",
            "user_id": "admin_001",
            "patient_id": "patient_001",
            "event": {
                "action": "therapeutic_relationship_created",
                "resource": "therapeutic_relationship",
                "description": "New therapeutic relationship established between therapist and patient",
                "success": True,
                "changes": [
                    {
                        "field": "relationship_type",
                        "old_value": None,
                        "new_value": "primary_therapist",
                        "change_type": "create"
                    },
                    {
                        "field": "access_level",
                        "old_value": None,
                        "new_value": "full",
                        "change_type": "create"
                    }
                ],
                "context": {
                    "therapist_id": "therapist_001",
                    "relationship_id": "rel_123",
                    "permissions": ["read_notes", "write_notes", "access_history", "emergency_access"]
                }
            },
            "phi_accessed": False,
            "data_sensitivity": "medium",
            "compliance_context": "relationship_management",
            "tags": ["relationship", "therapeutic", "access_control"]
        }
        
        response = requests.post(f"{self.BASE_URL}/audit-entries", json=audit_entry)
        assert response.status_code == 201
        
        result = response.json()
        assert result["message"] == "Audit entry logged successfully"
        
        print(f"👥 Relationship Management Audit Entry Logged: {audit_entry['event']['action']}")
        return result.get("audit_id")
    
    def test_log_compliance_violation_audit_entry(self):
        """Test logging compliance violation audit entry"""
        audit_entry = {
            "event_type": "compliance_violation",
            "log_level": "critical",
            "service_name": "api-gateway-service",
            "user_id": "suspicious_user_001",
            "event": {
                "action": "unauthorized_phi_access_attempt",
                "resource": "patient_records_database",
                "description": "Attempted unauthorized access to PHI without proper authentication or relationship",
                "success": False,
                "error_message": "Access denied: No valid therapeutic relationship found",
                "context": {
                    "violation_type": "unauthorized_access",
                    "attempted_patient_ids": ["patient_001", "patient_002", "patient_003"],
                    "detection_method": "relationship_validation_check",
                    "risk_score": 95,
                    "automated_actions": ["account_suspension", "supervisor_alert", "security_log"]
                }
            },
            "client_ip": "192.168.1.200",
            "user_agent": "curl/7.68.0",
            "phi_accessed": False,
            "data_sensitivity": "critical",
            "compliance_context": "security_violation_detection",
            "tags": ["violation", "security", "unauthorized", "high_risk"],
            "metadata": {
                "previous_attempts": 5,
                "account_status": "suspended",
                "investigation_id": "inv_001"
            }
        }
        
        response = requests.post(f"{self.BASE_URL}/audit-entries", json=audit_entry)
        assert response.status_code == 201
        
        result = response.json()
        assert result["message"] == "Audit entry logged successfully"
        
        print(f"🚨 Compliance Violation Audit Entry Logged: {audit_entry['event']['action']}")
        return result.get("audit_id")
    
    def test_retrieve_audit_entries_basic(self):
        """Test basic audit entry retrieval"""
        # First, add some test entries
        self.test_log_phi_access_audit_entry()
        self.test_log_emergency_access_audit_entry()
        time.sleep(0.1)  # Ensure different timestamps
        
        response = requests.get(f"{self.BASE_URL}/audit-entries?limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "filtered" in data
        assert len(data["entries"]) > 0
        
        # Verify audit entry structure
        entry = data["entries"][0]
        required_fields = [
            "audit_id", "timestamp", "event_type", "log_level", "service_name",
            "event", "phi_accessed", "retention_policy"
        ]
        
        for field in required_fields:
            assert field in entry, f"Missing required audit field: {field}"
        
        print(f"📝 Retrieved {len(data['entries'])} audit entries (Total: {data['total']})")
        print(f"🔍 Entry Types: {set(e['event_type'] for e in data['entries'])}")
    
    def test_retrieve_audit_entries_with_filters(self):
        """Test audit entry retrieval with various filters"""
        # Add test entries first
        self.test_log_phi_access_audit_entry()
        self.test_log_compliance_violation_audit_entry()
        time.sleep(0.1)
        
        # Test filter by service
        response = requests.get(f"{self.BASE_URL}/audit-entries?service=therapeutic-service&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        for entry in data["entries"]:
            assert entry["service_name"] == "therapeutic-service"
        
        # Test filter by event type
        response = requests.get(f"{self.BASE_URL}/audit-entries?event_type=phi_access&limit=5")
        assert response.status_code == 200
        
        phi_data = response.json()
        for entry in phi_data["entries"]:
            assert entry["event_type"] == "phi_access"
        
        # Test filter by user
        response = requests.get(f"{self.BASE_URL}/audit-entries?user_id=therapist_001&limit=5")
        assert response.status_code == 200
        
        user_data = response.json()
        for entry in user_data["entries"]:
            assert entry["user_id"] == "therapist_001"
        
        # Test filter by log level
        response = requests.get(f"{self.BASE_URL}/audit-entries?level=critical&limit=5")
        assert response.status_code == 200
        
        critical_data = response.json()
        for entry in critical_data["entries"]:
            assert entry["log_level"] == "critical"
        
        # Test PHI-only filter
        response = requests.get(f"{self.BASE_URL}/audit-entries?phi_only=true&limit=5")
        assert response.status_code == 200
        
        phi_only_data = response.json()
        for entry in phi_only_data["entries"]:
            assert entry["phi_accessed"] is True
        
        print(f"🔍 Filter Tests:")
        print(f"  Service Filter: {len(data['entries'])} entries")
        print(f"  PHI Access Filter: {len(phi_data['entries'])} entries")
        print(f"  User Filter: {len(user_data['entries'])} entries")
        print(f"  Critical Level Filter: {len(critical_data['entries'])} entries")
        print(f"  PHI Only Filter: {len(phi_only_data['entries'])} entries")
    
    def test_compliance_report_generation(self):
        """Test compliance report generation"""
        # Add diverse entries for comprehensive reporting
        self.test_log_phi_access_audit_entry()
        self.test_log_emergency_access_audit_entry()
        self.test_log_relationship_management_audit_entry()
        self.test_log_compliance_violation_audit_entry()
        time.sleep(0.1)
        
        # Test hourly report
        response = requests.get(f"{self.BASE_URL}/compliance-report?type=hourly")
        assert response.status_code == 200
        
        report = response.json()
        required_report_fields = [
            "report_id", "generated_at", "report_period", "total_events",
            "events_by_type", "events_by_service", "events_by_level",
            "phi_access_events", "security_events", "compliance_score"
        ]
        
        for field in required_report_fields:
            assert field in report, f"Missing report field: {field}"
        
        assert isinstance(report["compliance_score"], (int, float))
        assert 0 <= report["compliance_score"] <= 100
        
        # Test daily report
        response = requests.get(f"{self.BASE_URL}/compliance-report?type=daily")
        assert response.status_code == 200
        daily_report = response.json()
        
        # Test weekly report
        response = requests.get(f"{self.BASE_URL}/compliance-report?type=weekly")
        assert response.status_code == 200
        weekly_report = response.json()
        
        print(f"📊 Compliance Reports Generated:")
        print(f"  Hourly: Score {report['compliance_score']:.1f}%, {report['total_events']} events")
        print(f"  Daily: Score {daily_report['compliance_score']:.1f}%, {daily_report['total_events']} events")
        print(f"  Weekly: Score {weekly_report['compliance_score']:.1f}%, {weekly_report['total_events']} events")
        
        # Verify event aggregation
        if report["total_events"] > 0:
            assert "events_by_type" in report
            assert "events_by_service" in report
            assert "events_by_level" in report
            
            print(f"  Event Types: {list(report['events_by_type'].keys())}")
            print(f"  Services: {list(report['events_by_service'].keys())}")
            print(f"  PHI Access Events: {report['phi_access_events']}")
            print(f"  Security Events: {report['security_events']}")
    
    def test_audit_entry_validation(self):
        """Test audit entry validation and error handling"""
        # Test missing required fields
        invalid_entry = {
            "log_level": "info",
            # Missing event_type, service_name, event
        }
        
        response = requests.post(f"{self.BASE_URL}/audit-entries", json=invalid_entry)
        assert response.status_code == 400
        
        # Test invalid event structure
        invalid_event_entry = {
            "event_type": "user_login",
            "log_level": "info",
            "service_name": "test-service",
            "event": "invalid_event_structure"  # Should be object, not string
        }
        
        response = requests.post(f"{self.BASE_URL}/audit-entries", json=invalid_event_entry)
        assert response.status_code == 400
        
        print("❌ Validation Tests: Invalid entries properly rejected")
    
    def test_phi_access_audit_trail(self):
        """Test PHI access audit trail specifically"""
        phi_entries = []
        
        # Create multiple PHI access entries
        for i in range(3):
            audit_entry = {
                "event_type": "phi_access",
                "log_level": "info",
                "service_name": f"phi-service-{i}",
                "user_id": f"user_{i:03d}",
                "patient_id": f"patient_{i:03d}",
                "event": {
                    "action": f"view_patient_record_{i}",
                    "resource": f"patient_medical_record_{i}",
                    "description": f"PHI access test entry {i} for audit trail verification",
                    "success": True,
                    "context": {
                        "record_type": "medical_history",
                        "access_sequence": i
                    }
                },
                "phi_accessed": True,
                "data_sensitivity": "high",
                "compliance_context": f"test_phi_access_{i}"
            }
            
            response = requests.post(f"{self.BASE_URL}/audit-entries", json=audit_entry)
            assert response.status_code == 201
            phi_entries.append(response.json()["audit_id"])
            time.sleep(0.05)  # Small delay between entries
        
        # Retrieve PHI-only entries
        response = requests.get(f"{self.BASE_URL}/audit-entries?phi_only=true&limit=10")
        assert response.status_code == 200
        
        phi_data = response.json()
        phi_count = len([e for e in phi_data["entries"] if e["phi_accessed"]])
        
        assert phi_count >= 3  # At least our test entries
        
        # Verify all retrieved entries have PHI access
        for entry in phi_data["entries"]:
            assert entry["phi_accessed"] is True
            assert entry["retention_policy"] == "hipaa_phi_7_years"
        
        print(f"🔒 PHI Access Audit Trail: {phi_count} PHI access entries verified")
        print(f"📋 All PHI entries have 7-year retention policy")
    
    def test_emergency_access_audit_trail(self):
        """Test emergency access audit trail"""
        emergency_entries = []
        
        emergency_levels = ["low", "moderate", "high", "critical"]
        for level in emergency_levels:
            audit_entry = {
                "event_type": "emergency_access",
                "log_level": "critical" if level == "critical" else "warning",
                "service_name": "emergency-access-service",
                "user_id": f"emergency_user_{level}",
                "patient_id": f"patient_emergency_{level}",
                "event": {
                    "action": f"emergency_access_{level}",
                    "resource": f"emergency_records_{level}",
                    "description": f"Emergency access test for {level} level emergency",
                    "success": True,
                    "context": {
                        "emergency_level": level,
                        "access_duration": 3600 if level == "critical" else 1800,
                        "supervisor_notified": level in ["critical", "high"]
                    }
                },
                "phi_accessed": level in ["high", "critical"],
                "data_sensitivity": "critical" if level == "critical" else "high",
                "compliance_context": f"emergency_{level}_access"
            }
            
            response = requests.post(f"{self.BASE_URL}/audit-entries", json=audit_entry)
            assert response.status_code == 201
            emergency_entries.append(response.json()["audit_id"])
            time.sleep(0.05)
        
        # Retrieve emergency access entries
        response = requests.get(f"{self.BASE_URL}/audit-entries?event_type=emergency_access&limit=10")
        assert response.status_code == 200
        
        emergency_data = response.json()
        emergency_count = len([e for e in emergency_data["entries"] if e["event_type"] == "emergency_access"])
        
        assert emergency_count >= 4  # At least our test entries
        
        print(f"🚨 Emergency Access Audit Trail: {emergency_count} emergency access entries verified")
        
        # Verify critical entries are logged at critical level
        critical_entries = [e for e in emergency_data["entries"] 
                          if e.get("event", {}).get("context", {}).get("emergency_level") == "critical"]
        
        for entry in critical_entries:
            assert entry["log_level"] == "critical"
        
        print(f"⚠️ Critical Emergency Entries: {len(critical_entries)} properly logged at critical level")
    
    def test_service_integration_simulation(self):
        """Test integration with other services through audit logging"""
        # Simulate audit entries from various services
        services = [
            ("api-gateway-service", "api_access"),
            ("therapeutic-service", "phi_access"),
            ("emergency-access-service", "emergency_access"),
            ("relationship-management-service", "relationship_change"),
            ("content-safety-service", "security_incident")
        ]
        
        integration_entries = []
        
        for service_name, event_type in services:
            audit_entry = {
                "event_type": event_type,
                "log_level": "info",
                "service_name": service_name,
                "user_id": f"integration_user_{service_name}",
                "event": {
                    "action": f"service_integration_test_{service_name}",
                    "resource": f"{service_name}_resources",
                    "description": f"Integration test audit entry from {service_name}",
                    "success": True,
                    "context": {
                        "integration_test": True,
                        "service_version": "1.0.0",
                        "test_timestamp": time.time()
                    }
                },
                "phi_accessed": event_type in ["phi_access", "emergency_access"],
                "data_sensitivity": "medium",
                "compliance_context": f"{service_name}_integration_test"
            }
            
            response = requests.post(f"{self.BASE_URL}/audit-entries", json=audit_entry)
            assert response.status_code == 201
            integration_entries.append(response.json()["audit_id"])
        
        # Verify entries from all services are logged
        response = requests.get(f"{self.BASE_URL}/audit-entries?limit=20")
        assert response.status_code == 200
        
        data = response.json()
        logged_services = set(entry["service_name"] for entry in data["entries"])
        
        for service_name, _ in services:
            assert service_name in logged_services, f"Missing entries from {service_name}"
        
        print(f"🔗 Service Integration: {len(services)} services successfully logged audit entries")
        print(f"📊 Services Verified: {', '.join(logged_services)}")
    
    def test_audit_retention_and_archival_simulation(self):
        """Test audit retention policy handling"""
        # Test different retention policies
        retention_test_entries = [
            {
                "event_type": "phi_access",
                "log_level": "info",
                "service_name": "retention-test-service",
                "event": {
                    "action": "hipaa_phi_access",
                    "description": "PHI access requiring 7-year retention",
                    "success": True
                },
                "phi_accessed": True,
                "expected_retention": "hipaa_phi_7_years"
            },
            {
                "event_type": "user_login",
                "log_level": "info",
                "service_name": "retention-test-service",
                "event": {
                    "action": "standard_login",
                    "description": "Standard user login requiring 1-year retention",
                    "success": True
                },
                "phi_accessed": False,
                "expected_retention": "standard_1_year"
            }
        ]
        
        for entry_data in retention_test_entries:
            expected_retention = entry_data.pop("expected_retention")
            
            response = requests.post(f"{self.BASE_URL}/audit-entries", json=entry_data)
            assert response.status_code == 201
            
            # Retrieve and verify retention policy
            response = requests.get(f"{self.BASE_URL}/audit-entries?service=retention-test-service&limit=10")
            assert response.status_code == 200
            
            data = response.json()
            matching_entries = [e for e in data["entries"] 
                              if e["event"]["action"] == entry_data["event"]["action"]]
            
            assert len(matching_entries) > 0
            for entry in matching_entries:
                assert entry["retention_policy"] == expected_retention
        
        print(f"🗂️ Retention Policy Test: PHI entries → 7 years, Standard entries → 1 year")
    
    def test_comprehensive_audit_functionality(self):
        """Test comprehensive audit logging functionality"""
        # Create a comprehensive test scenario
        test_scenario = {
            "scenario": "comprehensive_hipaa_audit_test",
            "description": "Full audit trail test covering all major HIPAA compliance scenarios"
        }
        
        # Log the test start
        start_entry = {
            "event_type": "system_config",
            "log_level": "info",
            "service_name": "audit-test-runner",
            "event": {
                "action": "comprehensive_test_start",
                "description": "Starting comprehensive HIPAA audit logging test",
                "success": True,
                "context": test_scenario
            },
            "phi_accessed": False,
            "compliance_context": "system_testing"
        }
        
        response = requests.post(f"{self.BASE_URL}/audit-entries", json=start_entry)
        assert response.status_code == 201
        
        # Get final health check
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        final_health = response.json()
        
        # Generate final compliance report
        response = requests.get(f"{self.BASE_URL}/compliance-report?type=hourly")
        assert response.status_code == 200
        final_report = response.json()
        
        print(f"🎯 Comprehensive Audit Test Completed:")
        print(f"  Final Entry Count: {final_health['total_entries']}")
        print(f"  Final Compliance Score: {final_report['compliance_score']:.1f}%")
        print(f"  Services Audited: {len(final_report['events_by_service'])}")
        print(f"  Event Types Logged: {len(final_report['events_by_type'])}")
        print(f"  PHI Access Events: {final_report['phi_access_events']}")

def run_all_tests():
    """Run all audit logging service tests"""
    print("🧪 Starting Comprehensive Audit Logging Service Tests")
    print("=" * 70)
    
    test_instance = TestAuditLoggingService()
    test_instance.setup_class()
    
    # Run all tests
    test_methods = [
        test_instance.test_service_health_check,
        test_instance.test_log_phi_access_audit_entry,
        test_instance.test_log_emergency_access_audit_entry,
        test_instance.test_log_relationship_management_audit_entry,
        test_instance.test_log_compliance_violation_audit_entry,
        test_instance.test_retrieve_audit_entries_basic,
        test_instance.test_retrieve_audit_entries_with_filters,
        test_instance.test_compliance_report_generation,
        test_instance.test_audit_entry_validation,
        test_instance.test_phi_access_audit_trail,
        test_instance.test_emergency_access_audit_trail,
        test_instance.test_service_integration_simulation,
        test_instance.test_audit_retention_and_archival_simulation,
        test_instance.test_comprehensive_audit_functionality
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
        print("🎉 ALL TESTS PASSED - Comprehensive Audit Logging Service is working correctly!")
        return True
    else:
        print(f"⚠️ {failed_tests} tests failed - Please review the failures above")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)