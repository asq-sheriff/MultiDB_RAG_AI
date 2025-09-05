#!/usr/bin/env python3
"""
Lilo_EmotionalAI_Backend Unified Test Suite Runner
=========================================

A comprehensive, intuitive test runner for the Lilo_EmotionalAI_Backend therapeutic AI system
with automated reporting, performance benchmarking, and prescriptive guidance.

🎯 QUICK START GUIDE:
=====================

1. 📦 PRODUCTION READINESS CHECK:
   → python scripts/test_runner.py --all --report
   → Time: ~15-20 minutes | Creates: HTML report + metrics
   → Use: Before any production deployment

2. 🔧 DEVELOPMENT WORKFLOW:
   → python scripts/test_runner.py --quick
   → Time: ~3-5 minutes | Focus: Core functionality
   → Use: Daily development, before commits

3. 🏥 HIPAA COMPLIANCE AUDIT:
   → python scripts/test_runner.py --hipaa --report
   → Time: ~5 minutes | Creates: Compliance report
   → Use: Before healthcare deployments (REQUIRED)

4. 🚀 PERFORMANCE VALIDATION:
   → python scripts/test_runner.py --performance --benchmark
   → Time: ~8 minutes | Creates: Performance metrics
   → Use: Before releases, after optimization

5. 🔒 SECURITY AUDIT:
   → python scripts/test_runner.py --security --report
   → Time: ~6 minutes | Creates: Security audit report
   → Use: Weekly security checks

📋 USAGE PATTERNS:
==================

# Quick smoke test
python scripts/test_runner.py

# Full test suite with HTML report
python scripts/test_runner.py --all --report

# Specific category
python scripts/test_runner.py --unit --integration

# CI/CD mode (JSON output)
python scripts/test_runner.py --all --json --quiet

# Performance benchmarking
python scripts/test_runner.py --performance --benchmark --compare-baseline

# Debug mode with verbose output
python scripts/test_runner.py --debug --verbose
"""

import os
import sys
import asyncio
import argparse
import subprocess
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    category: str
    status: str  # 'passed', 'failed', 'skipped'
    duration: float
    output: str = ""
    error: str = ""
    metrics: Dict[str, Any] = None

@dataclass
class TestSummary:
    """Overall test summary"""
    total_tests: int
    passed: int
    failed: int
    skipped: int
    total_duration: float
    categories: Dict[str, Dict[str, int]]
    timestamp: str
    results: List[TestResult]

class TestRunner:
    """Unified test runner for Lilo_EmotionalAI_Backend"""
    
    def __init__(self, args):
        self.args = args
        self.project_root = PROJECT_ROOT
        self.reports_dir = self.project_root / "test_reports"
        self.results: List[TestResult] = []
        
        # Setup logging
        level = logging.DEBUG if args.verbose else logging.INFO
        if args.quiet:
            level = logging.WARNING
            
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.reports_dir / "test_run.log", mode='w')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Ensure reports directory exists
        self.reports_dir.mkdir(exist_ok=True)
    
    def print_header(self, title: str):
        """Print formatted section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{title.center(60)}{Colors.NC}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.NC}\n")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.RED}❌ {message}{Colors.NC}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, 
                   timeout: int = 300) -> Tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return 1, "", str(e)
    
    async def run_pytest_category(self, category: str, path: str, 
                                markers: Optional[str] = None) -> TestResult:
        """Run pytest for a specific category"""
        start_time = time.time()
        
        cmd = ["python", "-m", "pytest", path, "-v"]
        if markers:
            cmd.extend(["-m", markers])
        if self.args.quiet:
            cmd.append("-q")
        if not self.args.verbose:
            cmd.append("--tb=short")
        
        # Add coverage if requested
        if self.args.coverage:
            cmd.extend([
                "--cov=app",
                "--cov=ai_services", 
                "--cov=data_layer",
                f"--cov-report=html:{self.reports_dir}/coverage_{category}",
                f"--cov-report=json:{self.reports_dir}/coverage_{category}.json"
            ])
        
        # Add junit XML for CI
        if self.args.json or self.args.report:
            cmd.extend([f"--junit-xml={self.reports_dir}/junit_{category}.xml"])
        
        self.logger.info(f"Running {category} tests: {' '.join(cmd)}")
        
        exit_code, stdout, stderr = self.run_command(cmd)
        duration = time.time() - start_time
        
        status = "passed" if exit_code == 0 else "failed"
        
        return TestResult(
            name=f"{category}_tests",
            category=category,
            status=status,
            duration=duration,
            output=stdout,
            error=stderr
        )
    
    async def run_go_tests(self) -> TestResult:
        """Run Go microservices tests"""
        start_time = time.time()
        
        # Use the existing Go test runner
        go_script = self.project_root / "scripts" / "run_go_tests.sh"
        if not go_script.exists():
            return TestResult(
                name="go_tests",
                category="go",
                status="skipped",
                duration=0,
                error="Go test script not found"
            )
        
        cmd = ["bash", str(go_script)]
        exit_code, stdout, stderr = self.run_command(cmd)
        duration = time.time() - start_time
        
        status = "passed" if exit_code == 0 else "failed"
        
        return TestResult(
            name="go_tests",
            category="go",
            status=status,
            duration=duration,
            output=stdout,
            error=stderr
        )
    
    async def run_performance_tests(self) -> TestResult:
        """Run performance and benchmark tests"""
        start_time = time.time()
        
        perf_tests = self.project_root / "tests" / "performance"
        if not perf_tests.exists():
            return TestResult(
                name="performance_tests",
                category="performance",
                status="skipped",
                duration=0,
                error="Performance tests directory not found"
            )
        
        cmd = [
            "python", "-m", "pytest", 
            str(perf_tests),
            "-v", "--benchmark-only"
        ]
        
        if self.args.benchmark:
            cmd.extend([
                f"--benchmark-json={self.reports_dir}/benchmark.json",
                "--benchmark-histogram"
            ])
        
        exit_code, stdout, stderr = self.run_command(cmd, timeout=600)
        duration = time.time() - start_time
        
        status = "passed" if exit_code == 0 else "failed"
        
        return TestResult(
            name="performance_tests", 
            category="performance",
            status=status,
            duration=duration,
            output=stdout,
            error=stderr
        )
    
    async def run_hipaa_tests(self) -> TestResult:
        """Run HIPAA compliance tests"""
        hipaa_markers = "hipaa or compliance or audit or security"
        return await self.run_pytest_category(
            "hipaa", 
            "tests/integration", 
            markers=hipaa_markers
        )
    
    async def run_security_tests(self) -> TestResult:
        """Run security-focused tests"""
        security_markers = "security or auth or rbac"
        return await self.run_pytest_category(
            "security",
            "tests",
            markers=security_markers
        )
    
    async def run_database_tests(self) -> TestResult:
        """Run database connectivity and functionality tests"""
        return await self.run_pytest_category(
            "database",
            "tests/system/test_databases.py"
        )
    
    async def run_ai_quality_tests(self) -> TestResult:
        """Run AI quality and accuracy tests"""
        return await self.run_pytest_category(
            "ai_quality",
            "tests/system/test_ai_quality.py"
        )
    
    async def run_terraform_tests(self) -> TestResult:
        """Run Terraform infrastructure tests"""
        start_time = time.time()
        
        terraform_dir = self.project_root / "terraform" / "local"
        if not terraform_dir.exists():
            return TestResult(
                name="terraform_tests",
                category="terraform",
                status="skipped", 
                duration=0,
                error="Terraform directory not found"
            )
        
        # Test Terraform configuration
        tests = []
        
        # 1. Test terraform init
        init_code, init_out, init_err = self.run_command(
            ["terraform", "init", "-upgrade"], cwd=terraform_dir
        )
        tests.append(("init", init_code == 0, init_err))
        
        # 2. Test terraform validate
        validate_code, validate_out, validate_err = self.run_command(
            ["terraform", "validate"], cwd=terraform_dir
        )
        tests.append(("validate", validate_code == 0, validate_err))
        
        # 3. Test terraform plan (dry run)
        plan_code, plan_out, plan_err = self.run_command(
            ["terraform", "plan"], cwd=terraform_dir
        )
        tests.append(("plan", plan_code == 0, plan_err))
        
        duration = time.time() - start_time
        
        # Check if all tests passed
        all_passed = all(test[1] for test in tests)
        status = "passed" if all_passed else "failed"
        
        # Combine all output
        output = "\n".join([f"{test[0]}: {'PASS' if test[1] else 'FAIL'}" for test in tests])
        error = "\n".join([test[2] for test in tests if test[2]])
        
        return TestResult(
            name="terraform_tests",
            category="terraform", 
            status=status,
            duration=duration,
            output=output,
            error=error
        )
    
    def determine_test_suite(self) -> List[str]:
        """Determine which tests to run based on arguments"""
        if self.args.all:
            return ["unit", "integration", "system", "performance", "go", "hipaa", "security", "terraform"]
        elif self.args.quick:
            return ["unit", "database"] 
        elif self.args.hipaa:
            return ["hipaa", "security"]
        elif self.args.performance:
            return ["performance", "ai_quality"]
        elif self.args.security:
            return ["security", "hipaa"]
        elif self.args.terraform:
            return ["terraform"]
        else:
            # Default: essential tests
            suite = []
            if self.args.unit:
                suite.append("unit")
            if self.args.integration:
                suite.append("integration") 
            if self.args.system:
                suite.append("system")
            if self.args.go:
                suite.append("go")
            if self.args.terraform:
                suite.append("terraform")
            
            return suite if suite else ["unit", "integration"]
    
    async def run_tests(self) -> TestSummary:
        """Run the determined test suite"""
        test_suite = self.determine_test_suite()
        
        self.print_header("Lilo_EmotionalAI_Backend Test Suite")
        self.print_info(f"Running test categories: {', '.join(test_suite)}")
        
        start_time = time.time()
        tasks = []
        
        # Map test categories to runner methods
        test_runners = {
            "unit": lambda: self.run_pytest_category("unit", "tests/unit"),
            "integration": lambda: self.run_pytest_category("integration", "tests/integration"),
            "system": lambda: self.run_pytest_category("system", "tests/system"),
            "performance": self.run_performance_tests,
            "go": self.run_go_tests,
            "hipaa": self.run_hipaa_tests,
            "security": self.run_security_tests,
            "database": self.run_database_tests,
            "ai_quality": self.run_ai_quality_tests,
            "terraform": self.run_terraform_tests
        }
        
        # Run tests concurrently where possible
        for category in test_suite:
            if category in test_runners:
                tasks.append(test_runners[category]())
        
        # Execute tests
        results = []
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            self.results.append(result)
            
            # Print immediate feedback
            if result.status == "passed":
                self.print_success(f"{result.category} tests completed ({result.duration:.1f}s)")
            elif result.status == "failed":
                self.print_error(f"{result.category} tests failed ({result.duration:.1f}s)")
            else:
                self.print_warning(f"{result.category} tests skipped")
        
        total_duration = time.time() - start_time
        
        # Calculate summary statistics
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed") 
        skipped = sum(1 for r in results if r.status == "skipped")
        
        # Category breakdown
        categories = {}
        for result in results:
            cat = result.category
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "skipped": 0}
            categories[cat][result.status] += 1
        
        return TestSummary(
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            total_duration=total_duration,
            categories=categories,
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=results
        )
    
    def generate_html_report(self, summary: TestSummary):
        """Generate HTML test report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Lilo_EmotionalAI_Backend Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f8ff; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 15px; border-radius: 5px; }}
        .passed {{ background: #d4edda; color: #155724; }}
        .failed {{ background: #f8d7da; color: #721c24; }}
        .skipped {{ background: #fff3cd; color: #856404; }}
        .results {{ margin-top: 20px; }}
        .result {{ margin: 10px 0; padding: 10px; border-left: 4px solid; }}
        .result.passed {{ border-left-color: #28a745; background: #f8fff9; }}
        .result.failed {{ border-left-color: #dc3545; background: #fff8f8; }}
        .result.skipped {{ border-left-color: #ffc107; background: #fffbf0; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Lilo_EmotionalAI_Backend Test Report</h1>
        <p class="timestamp">Generated: {summary.timestamp}</p>
        <p>Duration: {summary.total_duration:.2f}s</p>
    </div>
    
    <div class="summary">
        <div class="metric passed">
            <h3>{summary.passed}</h3>
            <p>Passed</p>
        </div>
        <div class="metric failed">
            <h3>{summary.failed}</h3>
            <p>Failed</p>
        </div>
        <div class="metric skipped">
            <h3>{summary.skipped}</h3>
            <p>Skipped</p>
        </div>
    </div>
    
    <div class="results">
        <h2>Test Results</h2>
"""
        
        for result in summary.results:
            status_class = result.status
            html_content += f"""
        <div class="result {status_class}">
            <h3>{result.name} ({result.category})</h3>
            <p><strong>Status:</strong> {result.status.upper()}</p>
            <p><strong>Duration:</strong> {result.duration:.2f}s</p>
            {f'<details><summary>Output</summary><pre>{result.output}</pre></details>' if result.output else ''}
            {f'<details><summary>Error</summary><pre>{result.error}</pre></details>' if result.error else ''}
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        report_path = self.reports_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path.write_text(html_content)
        self.print_success(f"HTML report generated: {report_path}")
        return report_path
    
    def generate_json_report(self, summary: TestSummary):
        """Generate JSON test report"""
        report_data = asdict(summary)
        report_path = self.reports_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.print_success(f"JSON report generated: {report_path}")
        return report_path
    
    def print_summary(self, summary: TestSummary):
        """Print test summary to console"""
        self.print_header("Test Summary")
        
        print(f"Total Tests: {summary.total_tests}")
        print(f"Duration: {summary.total_duration:.2f}s")
        print()
        
        if summary.passed > 0:
            self.print_success(f"Passed: {summary.passed}")
        if summary.failed > 0:
            self.print_error(f"Failed: {summary.failed}")
        if summary.skipped > 0:
            self.print_warning(f"Skipped: {summary.skipped}")
        
        print("\nCategory Breakdown:")
        for category, stats in summary.categories.items():
            total = sum(stats.values())
            print(f"  {category}: {total} tests ({stats['passed']}✅ {stats['failed']}❌ {stats['skipped']}⚠️)")
        
        # Overall status
        if summary.failed == 0:
            self.print_success("🎉 ALL TESTS PASSED!")
            if summary.total_tests > 10:
                self.print_success("✅ System is ready for deployment")
        else:
            self.print_error(f"💥 {summary.failed} tests failed - fix before deployment")
    
    async def main(self):
        """Main test runner entry point"""
        try:
            # Run tests
            summary = await self.run_tests()
            
            # Generate reports
            if self.args.report:
                self.generate_html_report(summary)
            
            if self.args.json:
                self.generate_json_report(summary)
            
            # Print summary
            if not self.args.quiet:
                self.print_summary(summary)
            
            # Exit with appropriate code
            return 0 if summary.failed == 0 else 1
            
        except Exception as e:
            self.logger.exception("Test runner failed")
            self.print_error(f"Test runner failed: {e}")
            return 1

def create_parser():
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="Lilo_EmotionalAI_Backend Unified Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test selection
    parser.add_argument('--all', action='store_true', 
                       help='Run all test categories (production readiness)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick smoke tests (~5 min)')
    parser.add_argument('--unit', action='store_true',
                       help='Run unit tests')
    parser.add_argument('--integration', action='store_true', 
                       help='Run integration tests')
    parser.add_argument('--system', action='store_true',
                       help='Run system tests')
    parser.add_argument('--performance', action='store_true',
                       help='Run performance/benchmark tests')
    parser.add_argument('--go', action='store_true',
                       help='Run Go microservices tests')
    parser.add_argument('--hipaa', action='store_true',
                       help='Run HIPAA compliance tests')
    parser.add_argument('--security', action='store_true',
                       help='Run security audit tests')
    parser.add_argument('--terraform', action='store_true',
                       help='Run Terraform infrastructure tests')
    
    # Output and reporting  
    parser.add_argument('--report', action='store_true',
                       help='Generate HTML test report')
    parser.add_argument('--json', action='store_true',
                       help='Generate JSON test report')
    parser.add_argument('--coverage', action='store_true',
                       help='Generate coverage reports')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run performance benchmarks')
    
    # Verbosity
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--debug', action='store_true',
                       help='Debug output')
    
    return parser

async def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set debug if requested
    if args.debug:
        args.verbose = True
    
    runner = TestRunner(args)
    exit_code = await runner.main()
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())