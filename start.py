#!/usr/bin/env python3
"""
Lilo_EmotionalAI_Backend Startup Script
==============================

Intelligent startup script that detects your environment and starts the appropriate services.

Usage:
    python start.py                    # Smart startup (detects what to start)
    python start.py --databases        # Start only databases
    python start.py --services         # Start only application services  
    python start.py --all              # Start everything
    python start.py --dev              # Development mode with hot reload
"""

import os
import sys
import subprocess
import time
import signal
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json
import requests


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'


class ServiceManager:
    """Manages service startup and health checking"""
    
    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent
        self.processes: List[subprocess.Popen] = []
        
        # Service definitions for the new structure
        self.services = {
            "databases": {
                "docker-compose": {"cmd": ["docker-compose", "up", "-d"], "check_cmd": ["docker-compose", "ps"]},
            },
            "host_services": {
                "bge_server": {"cmd": ["python3", "host_services/embed_server.py"], "port": 8008, "health": "/health"},
                "generation_server": {"cmd": ["python3", "host_services/generation_server.py"], "port": 8007, "health": "/health"},
            },
            "go_microservices": {
                "auth_rbac": {"cmd": ["go", "run", "main.go"], "cwd": "microservices/auth-rbac", "port": 8090},
                "chat_history": {"cmd": ["go", "run", "main.go"], "cwd": "microservices/chat-history", "port": 8091},
                "billing": {"cmd": ["go", "run", "main.go"], "cwd": "microservices/billing", "port": 8092},
            },
            "python_services": {
                "search_service": {
                    "cmd": ["uvicorn", "ai_services.search.main:app", "--host", "0.0.0.0", "--port", "8001"],
                    "port": 8001, "health": "/health"
                },
                "embedding_service": {
                    "cmd": ["uvicorn", "ai_services.embedding.main_hybrid:app", "--host", "0.0.0.0", "--port", "8005"],
                    "port": 8005, "health": "/health"
                },
                "generation_service": {
                    "cmd": ["uvicorn", "ai_services.generation.main_hybrid:app", "--host", "0.0.0.0", "--port", "8006"],
                    "port": 8006, "health": "/health"
                },
                "ai_services": {
                    "cmd": ["uvicorn", "ai_services.main:app", "--host", "0.0.0.0", "--port", "8000"],
                    "port": 8000, "health": "/health"
                },
            }
        }
    
    def print_header(self):
        """Print startup header"""
        header = """
╔════════════════════════════════════════════════════════════════╗
║          🚀 Lilo_EmotionalAI_Backend Service Manager                   ║
║               Intelligent Service Startup                     ║
╚════════════════════════════════════════════════════════════════╝
        """
        print(f"{Colors.CYAN}{header}{Colors.NC}")
    
    def print_success(self, message: str):
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")
    
    def print_error(self, message: str):
        print(f"{Colors.RED}❌ {message}{Colors.NC}")
    
    def print_info(self, message: str):
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")
    
    def print_warning(self, message: str):
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")
    
    def check_service_health(self, port: int, health_path: str = "/health", timeout: int = 5) -> bool:
        """Check if a service is healthy"""
        try:
            response = requests.get(f"http://localhost:{port}{health_path}", timeout=timeout)
            return response.status_code == 200
        except:
            return False
    
    def start_docker_services(self):
        """Start database containers"""
        print(f"\n{Colors.YELLOW}🐳 Starting database containers...{Colors.NC}")
        
        try:
            result = subprocess.run(["docker-compose", "up", "-d"], 
                                  capture_output=True, text=True, check=True)
            self.print_success("Database containers started")
            
            # Wait for databases to be ready
            print(f"{Colors.BLUE}⏳ Waiting for databases to initialize...{Colors.NC}")
            time.sleep(10)
            self.print_success("Databases ready")
            
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to start Docker containers: {e.stderr}")
            return False
        except FileNotFoundError:
            self.print_error("Docker or docker-compose not found")
            return False
    
    def start_service_category(self, category: str):
        """Start a category of services"""
        if category not in self.services:
            return
        
        print(f"\n{Colors.YELLOW}🚀 Starting {category.replace('_', ' ')}...{Colors.NC}")
        
        for service_name, config in self.services[category].items():
            if service_name == "docker-compose":
                continue  # Handled separately
            
            print(f"  Starting {service_name}...")
            
            # Prepare environment
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)
            
            # Set working directory
            cwd = self.project_root
            if "cwd" in config:
                cwd = self.project_root / config["cwd"]
            
            # Add reload flag for development
            cmd = config["cmd"].copy()
            if self.args.dev and "uvicorn" in cmd[0]:
                cmd.append("--reload")
            
            try:
                if category == "host_services" and not self.args.auto:
                    # Host services should run in separate terminals
                    self.print_info(f"Start {service_name} in separate terminal:")
                    self.print_info(f"  cd {cwd}")
                    self.print_info(f"  {' '.join(cmd)}")
                else:
                    # Start in background
                    process = subprocess.Popen(
                        cmd, cwd=cwd, env=env,
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE
                    )
                    self.processes.append(process)
                    
                    # Quick health check for services with ports
                    if "port" in config:
                        time.sleep(2)
                        if self.check_service_health(config["port"], config.get("health", "/health")):
                            self.print_success(f"{service_name} started on port {config['port']}")
                        else:
                            self.print_warning(f"{service_name} starting on port {config['port']} (may take a moment)")
                    else:
                        self.print_success(f"{service_name} started")
                        
            except Exception as e:
                self.print_error(f"Failed to start {service_name}: {e}")
    
    def show_status_dashboard(self):
        """Show service status dashboard"""
        print(f"\n{Colors.CYAN}📊 SERVICE STATUS DASHBOARD{Colors.NC}")
        print("=" * 50)
        
        # Check database containers
        print(f"\n{Colors.YELLOW}🐳 Database Containers:{Colors.NC}")
        try:
            result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
            if "Up" in result.stdout:
                self.print_success("Database containers running")
            else:
                self.print_warning("Some database containers may not be running")
        except:
            self.print_warning("Cannot check Docker status")
        
        # Check service endpoints
        print(f"\n{Colors.YELLOW}🌐 Service Health:{Colors.NC}")
        
        health_checks = [
            ("API Gateway", 8000, "/health"),
            ("Search Service", 8001, "/health"),
            ("Embedding Service", 8005, "/health"),
            ("Generation Service", 8006, "/health"),
            ("BGE Host Server", 8008, "/health"),
            ("Generation Host Server", 8007, "/health"),
        ]
        
        for name, port, path in health_checks:
            if self.check_service_health(port, path):
                print(f"  {Colors.GREEN}✅ {name} (:{port}){Colors.NC}")
            else:
                print(f"  {Colors.RED}❌ {name} (:{port}){Colors.NC}")
    
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        print(f"\n{Colors.YELLOW}🛑 Shutting down services...{Colors.NC}")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        
        print(f"{Colors.GREEN}✅ All services stopped{Colors.NC}")
        sys.exit(0)
    
    def run(self):
        """Main execution"""
        self.print_header()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        # Determine what to start
        if self.args.databases:
            self.start_docker_services()
        elif self.args.services:
            self.start_service_category("python_services")
        elif self.args.all:
            self.start_docker_services()
            self.start_service_category("host_services")
            self.start_service_category("go_microservices")
            self.start_service_category("python_services")
        else:
            # Smart startup - detect what's needed
            print(f"{Colors.CYAN}🧠 Smart Startup Mode{Colors.NC}")
            print("Detecting what needs to be started...")
            
            self.start_docker_services()
            
            if not self.args.auto:
                print(f"\n{Colors.YELLOW}Start additional services?{Colors.NC}")
                print("  • Host GPU services (BGE, Qwen)")
                print("  • Go microservices")  
                print("  • Python AI services")
                response = input("Start all services? (y/N): ").lower().strip()
                
                if response in ['y', 'yes']:
                    self.start_service_category("host_services")
                    self.start_service_category("python_services")
            else:
                self.start_service_category("host_services")
                self.start_service_category("python_services")
        
        # Show status
        time.sleep(3)
        self.show_status_dashboard()
        
        # Keep running if we started any background processes
        if self.processes:
            print(f"\n{Colors.CYAN}🏃 Services running in background{Colors.NC}")
            print(f"{Colors.BLUE}Press Ctrl+C to stop all services{Colors.NC}")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.handle_shutdown(None, None)
        else:
            print(f"\n{Colors.CYAN}💡 Use 'make services-status' to check service health{Colors.NC}")


def create_parser():
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="Lilo_EmotionalAI_Backend Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--databases', action='store_true',
                       help='Start only database containers')
    parser.add_argument('--services', action='store_true',
                       help='Start only application services')
    parser.add_argument('--all', action='store_true',
                       help='Start all services (databases + applications)')
    parser.add_argument('--dev', action='store_true',
                       help='Development mode with auto-reload')
    parser.add_argument('--auto', action='store_true',
                       help='Automated startup without prompts')
    
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    
    manager = ServiceManager(args)
    manager.run()