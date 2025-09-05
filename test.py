#!/usr/bin/env python3
"""
Quick Test Launcher for Lilo_EmotionalAI_Backend
========================================

Simple, intuitive test runner for common scenarios.

Usage:
  python test.py                    # Quick smoke test
  python test.py --all             # Full test suite  
  python test.py --hipaa           # HIPAA compliance
  python test.py --performance     # Performance tests
  python test.py --help            # See all options
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Forward to the main test runner with user-friendly defaults"""
    
    # Get project root
    project_root = Path(__file__).parent
    test_runner = project_root / "scripts" / "test_runner.py"
    
    # Build command
    cmd = [sys.executable, str(test_runner)]
    
    # If no args provided, run quick tests
    if len(sys.argv) == 1:
        cmd.extend(["--quick", "--report"])
        print("🚀 Running quick smoke tests...")
        print("💡 Use 'python test.py --help' to see all options")
    else:
        # Forward all arguments
        cmd.extend(sys.argv[1:])
    
    # Execute
    try:
        result = subprocess.run(cmd, cwd=project_root)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()