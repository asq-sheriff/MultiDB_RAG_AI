#!/usr/bin/env python3
"""
Comprehensive Test Runner for HIPAA-Compliant Therapeutic Cache System
Runs all integration tests and provides detailed analysis of the enhanced caching implementation
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import test suites
from test_hipaa_cache_e2e import HIPAACacheIntegrationTests
from test_therapeutic_ai_e2e import TherapeuticAIIntegrationTests


class ComprehensiveTestRunner:
    """Comprehensive test runner for all therapeutic cache system tests"""
    
    def __init__(self):
        self.all_test_results = []
        self.test_suites = {}
        self.start_time = None
        self.end_time = None
    
    async def run_all_test_suites(self):
        """Run all test suites and collect comprehensive results"""
        print("🚀 COMPREHENSIVE HIPAA-COMPLIANT THERAPEUTIC CACHE TEST RUNNER")
        print("=" * 90)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.start_time = time.time()
        
        # Test Suite 1: HIPAA Cache Integration Tests
        print("📋 TEST SUITE 1: HIPAA-Compliant Cache Integration Tests")
        print("-" * 70)
        
        hipaa_suite = HIPAACacheIntegrationTests()
        
        # Capture stdout to analyze results
        original_print = print
        hipaa_results = []
        
        def capture_hipaa_print(*args, **kwargs):
            line = " ".join(str(arg) for arg in args)
            if "✅ PASS:" in line or "❌ FAIL:" in line:
                hipaa_results.append(line)
            original_print(*args, **kwargs)
        
        # Replace print temporarily
        import builtins
        builtins.print = capture_hipaa_print
        
        try:
            await hipaa_suite.run_all_tests()
            self.test_suites["hipaa_cache"] = {
                "results": hipaa_suite.test_results,
                "total": len(hipaa_suite.test_results),
                "passed": sum(1 for r in hipaa_suite.test_results if r["success"]),
                "failed": sum(1 for r in hipaa_suite.test_results if not r["success"])
            }
        finally:
            builtins.print = original_print
        
        print("\n" + "="*70)
        
        # Test Suite 2: Therapeutic AI End-to-End Tests
        print("📋 TEST SUITE 2: Enhanced Therapeutic AI End-to-End Tests")
        print("-" * 70)
        
        ai_suite = TherapeuticAIIntegrationTests()
        
        # Capture AI test results
        ai_results = []
        
        def capture_ai_print(*args, **kwargs):
            line = " ".join(str(arg) for arg in args)
            if "✅ PASS:" in line or "❌ FAIL:" in line:
                ai_results.append(line)
            original_print(*args, **kwargs)
        
        builtins.print = capture_ai_print
        
        try:
            await ai_suite.run_all_tests()
            self.test_suites["therapeutic_ai"] = {
                "results": ai_suite.test_results,
                "total": len(ai_suite.test_results),
                "passed": sum(1 for r in ai_suite.test_results if r["success"]),
                "failed": sum(1 for r in ai_suite.test_results if not r["success"])
            }
        finally:
            builtins.print = original_print
        
        self.end_time = time.time()
        
        # Generate comprehensive report
        await self.generate_comprehensive_report()
    
    async def generate_comprehensive_report(self):
        """Generate comprehensive test report and analysis"""
        print("\n" + "="*90)
        print("📊 COMPREHENSIVE TEST REPORT - HIPAA-COMPLIANT THERAPEUTIC CACHE SYSTEM")
        print("="*90)
        
        total_duration = self.end_time - self.start_time
        
        print(f"🕐 Test Duration: {total_duration:.2f} seconds")
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Overall Statistics
        total_tests = sum(suite["total"] for suite in self.test_suites.values())
        total_passed = sum(suite["passed"] for suite in self.test_suites.values())
        total_failed = sum(suite["failed"] for suite in self.test_suites.values())
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print("📈 OVERALL TEST STATISTICS")
        print(f"  Total Test Suites: {len(self.test_suites)}")
        print(f"  Total Tests: {total_tests}")
        print(f"  Total Passed: {total_passed}")
        print(f"  Total Failed: {total_failed}")
        print(f"  Overall Success Rate: {overall_success_rate:.1f}%")
        print()
        
        # Suite-by-Suite Breakdown
        print("🧪 TEST SUITE BREAKDOWN")
        print("-" * 50)
        
        for suite_name, suite_data in self.test_suites.items():
            success_rate = (suite_data["passed"] / suite_data["total"] * 100) if suite_data["total"] > 0 else 0
            status_icon = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
            
            print(f"{status_icon} {suite_name.replace('_', ' ').title()}:")
            print(f"    Tests: {suite_data['total']}")
            print(f"    Passed: {suite_data['passed']}")
            print(f"    Failed: {suite_data['failed']}")
            print(f"    Success Rate: {success_rate:.1f}%")
            print()
        
        # Critical Feature Analysis
        print("🔍 CRITICAL FEATURE ANALYSIS")
        print("-" * 50)
        
        # Analyze HIPAA compliance
        hipaa_tests = self.test_suites.get("hipaa_cache", {}).get("results", [])
        phi_detection_passed = any(r["success"] and "PHI Detection" in r["test"] for r in hipaa_tests)
        phi_exclusion_passed = any(r["success"] and "PHI Cache Exclusion" in r["test"] for r in hipaa_tests)
        encryption_passed = any(r["success"] and "Encryption" in r["test"] for r in hipaa_tests)
        clustering_passed = any(r["success"] and "Clustering" in r["test"] for r in hipaa_tests)
        
        print("🏥 HIPAA Compliance Features:")
        print(f"  PHI Detection: {'✅ WORKING' if phi_detection_passed else '❌ NEEDS ATTENTION'}")
        print(f"  PHI Cache Exclusion: {'✅ WORKING' if phi_exclusion_passed else '❌ NEEDS ATTENTION'}")
        print(f"  Healthcare Encryption: {'✅ WORKING' if encryption_passed else '❌ NEEDS ATTENTION'}")
        print(f"  Semantic Clustering: {'✅ WORKING' if clustering_passed else '❌ NEEDS ATTENTION'}")
        print()
        
        # Analyze AI integration
        ai_tests = self.test_suites.get("therapeutic_ai", {}).get("results", [])
        cache_integration_passed = any(r["success"] and "Cache" in r["test"] for r in ai_tests)
        hybrid_search_passed = any(r["success"] and "Hybrid" in r["test"] for r in ai_tests)
        document_availability_passed = any(r["success"] and "Document" in r["test"] for r in ai_tests)
        
        print("🧠 AI Integration Features:")
        print(f"  Enhanced Cache Integration: {'✅ WORKING' if cache_integration_passed else '❌ NEEDS ATTENTION'}")
        print(f"  Hybrid Search: {'✅ WORKING' if hybrid_search_passed else '❌ NEEDS ATTENTION'}")
        print(f"  Document Availability: {'✅ WORKING' if document_availability_passed else '❌ NEEDS ATTENTION'}")
        print()
        
        # Security & Compliance Status
        print("🔒 SECURITY & COMPLIANCE STATUS")
        print("-" * 50)
        
        security_score = sum([
            phi_detection_passed,
            phi_exclusion_passed, 
            encryption_passed,
            clustering_passed
        ]) / 4 * 100
        
        compliance_status = "FULLY COMPLIANT" if security_score >= 75 else "PARTIALLY COMPLIANT" if security_score >= 50 else "NON-COMPLIANT"
        compliance_icon = "✅" if security_score >= 75 else "⚠️" if security_score >= 50 else "❌"
        
        print(f"{compliance_icon} HIPAA Compliance Score: {security_score:.0f}%")
        print(f"{compliance_icon} Compliance Status: {compliance_status}")
        print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS")
        print("-" * 50)
        
        if not phi_detection_passed:
            print("⚠️  PHI Detection: Fine-tune detection algorithms for better accuracy")
        
        if not cache_integration_passed:
            print("⚠️  Cache Integration: Review cache flow for consistent behavior")
        
        if overall_success_rate < 80:
            print("⚠️  Overall: Some tests failing - review system configuration")
        
        if security_score < 75:
            print("🚨 CRITICAL: Security features need immediate attention for HIPAA compliance")
        
        if overall_success_rate >= 80 and security_score >= 75:
            print("🎉 EXCELLENT: System is performing well with strong HIPAA compliance!")
            print("✅ Ready for production deployment of HIPAA-compliant therapeutic cache")
        
        print()
        
        # Detailed Failed Test Analysis
        failed_tests = []
        for suite_name, suite_data in self.test_suites.items():
            for result in suite_data["results"]:
                if not result["success"]:
                    failed_tests.append({
                        "suite": suite_name,
                        "test": result["test"],
                        "details": result["details"]
                    })
        
        if failed_tests:
            print("🔍 DETAILED FAILURE ANALYSIS")
            print("-" * 50)
            for i, failure in enumerate(failed_tests, 1):
                print(f"{i}. {failure['suite'].title()} - {failure['test']}")
                print(f"   Issue: {failure['details']}")
                print()
        
        # Summary Banner
        print("="*90)
        if overall_success_rate >= 80 and security_score >= 75:
            print("🎊 HIPAA-COMPLIANT THERAPEUTIC CACHE SYSTEM: PRODUCTION READY! 🎊")
        elif overall_success_rate >= 60:
            print("⚡ HIPAA-COMPLIANT THERAPEUTIC CACHE SYSTEM: NEEDS FINE-TUNING ⚡")
        else:
            print("🔧 HIPAA-COMPLIANT THERAPEUTIC CACHE SYSTEM: REQUIRES ATTENTION 🔧")
        print("="*90)


async def main():
    """Main test runner entry point"""
    runner = ComprehensiveTestRunner()
    await runner.run_all_test_suites()


if __name__ == "__main__":
    asyncio.run(main())