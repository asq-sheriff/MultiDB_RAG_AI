#!/usr/bin/env python3
"""
Deployment Integration Test Runner

This script runs comprehensive end-to-end tests for both local and Docker deployment modes,
validating that the unified configuration system works correctly across environments.

Usage:
    python scripts/run_deployment_tests.py [--mode local|docker|both] [--verbose]
"""

import argparse
import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.integration.test_deployment_modes import DeploymentTester


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


async def run_tests(mode: str = "both", verbose: bool = False):
    """Run deployment integration tests."""
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    tester = DeploymentTester()
    results = {}
    
    try:
        logger.info("🏁 Starting deployment integration test suite...")
        logger.info(f"📋 Test mode: {mode}")
        
        modes_to_test = []
        if mode in ["local", "both"]:
            modes_to_test.append("local")
        if mode in ["docker", "both"]:
            modes_to_test.append("docker")
        
        for test_mode in modes_to_test:
            logger.info(f"\n{'='*70}")
            logger.info(f"🧪 TESTING {test_mode.upper()} DEPLOYMENT MODE")
            logger.info(f"{'='*70}")
            
            try:
                results[test_mode] = await tester.run_comprehensive_test(test_mode)
                
                # Show immediate results
                success = results[test_mode].get("overall_success", False)
                logger.info(f"✅ {test_mode.upper()} deployment test: {'PASSED' if success else 'FAILED'}")
                
            except Exception as e:
                logger.error(f"❌ {test_mode.upper()} deployment test failed with exception: {e}")
                results[test_mode] = {"overall_success": False, "error": str(e)}
            
            # Brief pause between tests
            if len(modes_to_test) > 1:
                await asyncio.sleep(3)
        
        # Generate comprehensive report
        if results:
            logger.info(f"\n{'='*70}")
            logger.info("📊 GENERATING COMPREHENSIVE TEST REPORT")
            logger.info(f"{'='*70}")
            
            report = tester.generate_test_report(results)
            print(f"\n{report}")
            
            # Save to file
            timestamp = asyncio.get_event_loop().time()
            report_file = Path(f"deployment_test_report_{int(timestamp)}.txt")
            with open(report_file, "w") as f:
                f.write(report)
            
            logger.info(f"📄 Detailed report saved to: {report_file}")
            
            # Calculate final result
            total_tests = len(results)
            passed_tests = sum(1 for r in results.values() if r.get("overall_success", False))
            
            logger.info(f"\n🎯 FINAL SUMMARY:")
            logger.info(f"   Deployment modes tested: {total_tests}")
            logger.info(f"   Successful deployments: {passed_tests}")
            logger.info(f"   Success rate: {(passed_tests/total_tests)*100:.1f}%")
            
            if passed_tests == total_tests:
                logger.info("🎉 ALL DEPLOYMENT TESTS PASSED!")
                return True
            else:
                logger.error("⚠️ SOME DEPLOYMENT TESTS FAILED!")
                return False
        
        else:
            logger.error("❌ No tests were run successfully")
            return False
            
    except KeyboardInterrupt:
        logger.warning("⚠️ Tests interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False
    finally:
        # Ensure cleanup
        logger.info("🧹 Cleaning up test environment...")
        tester.stop_local_services()
        tester.stop_docker_services()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run deployment integration tests for MultiDB Chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Test both local and Docker deployments
    python scripts/run_deployment_tests.py
    
    # Test only local deployment
    python scripts/run_deployment_tests.py --mode local
    
    # Test only Docker deployment  
    python scripts/run_deployment_tests.py --mode docker
    
    # Verbose output
    python scripts/run_deployment_tests.py --verbose
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["local", "docker", "both"],
        default="both", 
        help="Deployment mode to test (default: both)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Run tests
    success = asyncio.run(run_tests(args.mode, args.verbose))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()