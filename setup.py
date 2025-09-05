#!/usr/bin/env python3
"""
Lilo_EmotionalAI_Backend Setup Script
============================

Comprehensive setup script for the Lilo_EmotionalAI_Backend therapeutic AI system.
Handles environment setup, dependency installation, and initial configuration.

Usage:
    python setup.py                    # Interactive setup
    python setup.py --auto             # Automated setup
    python setup.py --dev              # Development setup only
    python setup.py --production       # Production setup
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse
import platform


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'


class SetupManager:
    """Manages the setup process for Lilo_EmotionalAI_Backend"""
    
    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent
        os.chdir(self.project_root)
        
    def print_header(self):
        """Print setup header"""
        header = """
╔════════════════════════════════════════════════════════════════╗
║          🏥 MultiDB Therapeutic AI Chatbot Setup              ║
║               Restructured Hybrid Architecture                ║
╚════════════════════════════════════════════════════════════════╝
        """
        print(f"{Colors.CYAN}{header}{Colors.NC}")
        
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
        
    def print_step(self, step: int, description: str):
        """Print step header"""
        print(f"\n{Colors.YELLOW}📋 Step {step}: {description}...{Colors.NC}")
    
    def run_command(self, cmd: list, check: bool = True) -> subprocess.CompletedProcess:
        """Run a command with error handling"""
        try:
            return subprocess.run(cmd, check=check, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            if check:
                self.print_error(f"Command failed: {' '.join(cmd)}")
                print(f"Error: {e.stderr}")
                return None
            return e
    
    def check_system_requirements(self) -> bool:
        """Check system requirements"""
        self.print_step(1, "Checking system requirements")
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            self.print_error(f"Python 3.8+ required, found {python_version.major}.{python_version.minor}")
            return False
        self.print_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} found")
        
        # Check platform
        system_info = platform.system()
        self.print_info(f"Platform: {system_info} {platform.machine()}")
        
        # Check Docker (optional)
        docker_result = self.run_command(["docker", "--version"], check=False)
        if docker_result and docker_result.returncode == 0:
            self.print_success("Docker found")
        else:
            self.print_warning("Docker not found (optional for development)")
        
        # Check Go (optional)
        go_result = self.run_command(["go", "version"], check=False)
        if go_result and go_result.returncode == 0:
            self.print_success("Go found (for microservices development)")
        else:
            self.print_info("Go not found (only needed for microservices development)")
        
        return True
    
    def setup_virtual_environment(self):
        """Set up Python virtual environment"""
        self.print_step(2, "Setting up virtual environment")
        
        venv_path = self.project_root / ".venv"
        
        if venv_path.exists():
            self.print_info("Virtual environment already exists")
        else:
            result = self.run_command([sys.executable, "-m", "venv", str(venv_path)])
            if result:
                self.print_success("Virtual environment created")
            else:
                self.print_error("Failed to create virtual environment")
                return False
        
        return True
    
    def install_dependencies(self):
        """Install Python dependencies"""
        self.print_step(3, "Installing Python dependencies")
        
        venv_python = self.project_root / ".venv" / "bin" / "python"
        venv_pip = self.project_root / ".venv" / "bin" / "pip"
        
        # On Windows, use Scripts instead of bin
        if platform.system() == "Windows":
            venv_python = self.project_root / ".venv" / "Scripts" / "python.exe"
            venv_pip = self.project_root / ".venv" / "Scripts" / "pip.exe"
        
        if not venv_pip.exists():
            self.print_error("Virtual environment not properly created")
            return False
        
        # Upgrade pip
        result = self.run_command([str(venv_pip), "install", "--upgrade", "pip"])
        if not result:
            return False
        
        # Install requirements
        requirements_file = "requirements.txt"
        if self.args.dev:
            # Check if dev requirements exist
            if Path("requirements.dev.txt").exists():
                requirements_file = "requirements.dev.txt"
        
        result = self.run_command([str(venv_pip), "install", "-r", requirements_file])
        if result:
            self.print_success("Dependencies installed")
        else:
            self.print_warning("Some dependencies may have issues - check manually")
        
        return True
    
    def setup_configuration(self):
        """Set up configuration files"""
        self.print_step(4, "Setting up configuration")
        
        # Setup .env file
        if not Path(".env").exists():
            if Path("config/defaults/.env.example").exists():
                shutil.copy("config/defaults/.env.example", ".env")
                self.print_success(".env file created from example")
                self.print_info("Please review and update .env file with your settings")
            else:
                self.print_warning("config/defaults/.env.example not found - create .env file manually")
        else:
            self.print_info(".env file already exists")
        
        return True
    
    def validate_project_structure(self):
        """Validate the restructured project structure"""
        self.print_step(5, "Validating project structure")
        
        required_dirs = [
            "app", "microservices", "ai_services", "data_layer", "tests"
        ]
        
        for directory in required_dirs:
            if Path(directory).exists():
                self.print_success(f"{directory}/ directory found")
            else:
                self.print_error(f"{directory}/ directory missing")
                return False
        
        # Check key files
        key_files = ["pytest.ini", "docker-compose.yml", "requirements.txt"]
        for file_name in key_files:
            if Path(file_name).exists():
                self.print_success(f"{file_name} found")
            else:
                self.print_warning(f"{file_name} missing")
        
        return True
    
    def test_imports(self):
        """Test critical imports"""
        self.print_step(6, "Testing Python imports")
        
        venv_python = self.project_root / ".venv" / "bin" / "python"
        if platform.system() == "Windows":
            venv_python = self.project_root / ".venv" / "Scripts" / "python.exe"
        
        # Test data layer imports
        result = self.run_command([
            str(venv_python), "-c",
            "import sys; sys.path.append('.'); from data_layer.models.postgres.postgres_models import User"
        ], check=False)
        
        if result and result.returncode == 0:
            self.print_success("Data layer imports work")
        else:
            self.print_error("Data layer import issues")
            return False
        
        # Test AI services imports
        result = self.run_command([
            str(venv_python), "-c", 
            "import sys; sys.path.append('.'); from ai_services.search.services.search import SearchService"
        ], check=False)
        
        if result and result.returncode == 0:
            self.print_success("AI services imports work")
        else:
            self.print_warning("AI services import issues - may need service dependencies")
        
        return True
    
    def setup_databases(self):
        """Setup database configuration"""
        if self.args.production:
            self.print_info("Production setup - skipping local database setup")
            return True
            
        self.print_step(7, "Setting up local databases")
        
        if not self.args.auto:
            response = input("Start Docker databases? (y/N): ").lower().strip()
            if response not in ['y', 'yes']:
                self.print_info("Skipping database setup")
                return True
        
        # Check if Docker compose exists
        if Path("docker-compose.yml").exists():
            result = self.run_command(["docker-compose", "up", "-d"], check=False)
            if result and result.returncode == 0:
                self.print_success("Database containers started")
            else:
                self.print_warning("Failed to start Docker containers - start manually if needed")
        else:
            self.print_warning("docker-compose.yml not found")
        
        return True
    
    def create_welcome_guide(self):
        """Create a welcome guide for new users"""
        welcome_content = f"""
# Welcome to Lilo_EmotionalAI_Backend! 🏥

## Quick Start Guide

You've successfully set up the Lilo_EmotionalAI_Backend therapeutic AI system. Here's how to get started:

### 1. Start Services
```bash
make services-start    # Start all required services
```

### 2. Run Tests  
```bash
make test             # Quick validation tests
make test-all         # Full test suite
make test-hipaa       # HIPAA compliance (required for healthcare)
```

### 3. Start Development
```bash
make dev-start        # Start development environment
```

## Key Commands

- `make help` - Show all available commands
- `make validate` - Validate system setup
- `make demo` - Run interactive demo
- `make clean` - Clean temporary files

## Project Structure

Your restructured project:
```
Lilo_EmotionalAI_Backend/
├── microservices/     # Go microservices (auth, billing, etc.)
├── ai_services/       # Python AI services (search, embedding, etc.)  
├── data_layer/        # Unified database layer
├── app/              # Main FastAPI application
└── tests/            # Comprehensive test suite
```

## Next Steps

1. Review the documentation in `docs/`
2. Check the test results in `test_reports/`
3. Explore the API documentation at http://localhost:8000/docs (after starting services)

## Need Help?

- Run `make help` for all commands
- Check `tests/README.md` for testing guide
- Review `docs/README.md` for detailed documentation

Happy coding! 🚀
"""
        
        welcome_file = self.project_root / "WELCOME.md"
        welcome_file.write_text(welcome_content)
        self.print_success("Welcome guide created: WELCOME.md")
    
    def run_setup(self) -> bool:
        """Run the complete setup process"""
        self.print_header()
        
        print(f"\n{Colors.CYAN}🚀 Starting Lilo_EmotionalAI_Backend Setup{Colors.NC}")
        print("=" * 50)
        
        if not self.args.auto:
            print(f"\n{Colors.YELLOW}This will set up the Lilo_EmotionalAI_Backend development environment.{Colors.NC}")
            print(f"{Colors.BLUE}The setup includes:{Colors.NC}")
            print("  • Python virtual environment")
            print("  • Project dependencies")
            print("  • Configuration files")
            print("  • Project structure validation")
            print("  • Database setup (optional)")
            print()
            response = input("Continue? (Y/n): ").lower().strip()
            if response in ['n', 'no']:
                print("Setup cancelled.")
                return False
        
        steps = [
            self.check_system_requirements,
            self.setup_virtual_environment,
            self.install_dependencies, 
            self.setup_configuration,
            self.validate_project_structure,
            self.test_imports,
        ]
        
        if not self.args.dev:
            steps.append(self.setup_databases)
        
        # Run all steps
        for step in steps:
            if not step():
                self.print_error("Setup failed at step")
                return False
        
        # Create welcome guide
        self.create_welcome_guide()
        
        print(f"\n{Colors.GREEN}🎉 Setup Complete!{Colors.NC}")
        print("=" * 50)
        print()
        print(f"{Colors.CYAN}Next steps:{Colors.NC}")
        if not self.args.dev:
            print(f"  1. {Colors.WHITE}make services-start{Colors.NC}    - Start all services")
        print(f"  2. {Colors.WHITE}make test{Colors.NC}              - Validate setup")
        print(f"  3. {Colors.WHITE}make dev-start{Colors.NC}         - Start development")
        print()
        print(f"{Colors.BLUE}📖 See WELCOME.md for detailed next steps{Colors.NC}")
        print(f"{Colors.CYAN}💡 Use 'make help' to see all available commands{Colors.NC}")
        
        return True


def create_parser():
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="Lilo_EmotionalAI_Backend Setup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--auto', action='store_true',
                       help='Run setup without interactive prompts')
    parser.add_argument('--dev', action='store_true',
                       help='Development setup only (skip database setup)')
    parser.add_argument('--production', action='store_true',
                       help='Production setup (minimal local dependencies)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    setup_manager = SetupManager(args)
    
    try:
        success = setup_manager.run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Setup interrupted by user{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Setup failed: {e}{Colors.NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()