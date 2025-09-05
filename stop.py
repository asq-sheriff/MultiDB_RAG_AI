#!/usr/bin/env python3
"""
Lilo_EmotionalAI_Backend Stop Script
===========================

Gracefully stops all running services.

Usage:
    python stop.py                     # Stop all services
    python stop.py --databases         # Stop only databases
    python stop.py --force             # Force stop all services
"""

import subprocess
import argparse
import signal
import os
from pathlib import Path


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'


class StopManager:
    """Manages graceful service shutdown"""
    
    def __init__(self, args):
        self.args = args
        self.project_root = Path(__file__).parent
    
    def print_header(self):
        print(f"{Colors.CYAN}🛑 Lilo_EmotionalAI_Backend Service Shutdown{Colors.NC}")
        print("=" * 40)
    
    def print_success(self, message: str):
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")
    
    def print_info(self, message: str):
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")
    
    def stop_docker_services(self):
        """Stop database containers"""
        print(f"\n{Colors.YELLOW}🐳 Stopping database containers...{Colors.NC}")
        
        try:
            subprocess.run(["docker-compose", "down"], check=True, capture_output=True)
            self.print_success("Database containers stopped")
            return True
        except subprocess.CalledProcessError:
            self.print_info("Database containers already stopped")
            return True
        except FileNotFoundError:
            self.print_info("Docker not available")
            return False
    
    def stop_python_services(self):
        """Stop Python services by finding and killing processes"""
        print(f"\n{Colors.YELLOW}🐍 Stopping Python services...{Colors.NC}")
        
        # Find Python processes related to our services
        service_ports = [8000, 8001, 8005, 8006, 8007, 8008]
        
        for port in service_ports:
            try:
                # Find process using the port
                result = subprocess.run(
                    ["lsof", "-ti", f"tcp:{port}"], 
                    capture_output=True, text=True
                )
                
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            self.print_success(f"Stopped service on port {port}")
                        except (ValueError, ProcessLookupError):
                            pass
            except:
                pass  # lsof may not be available on all systems
    
    def stop_go_services(self):
        """Stop Go microservices"""
        print(f"\n{Colors.YELLOW}🔧 Stopping Go microservices...{Colors.NC}")
        
        # Find Go processes
        try:
            result = subprocess.run(
                ["pgrep", "-f", "go.*main.go"],
                capture_output=True, text=True
            )
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        self.print_success(f"Stopped Go service (PID: {pid})")
                    except (ValueError, ProcessLookupError):
                        pass
        except:
            self.print_info("No Go processes found or pgrep not available")
    
    def force_cleanup(self):
        """Force cleanup of all services"""
        print(f"\n{Colors.RED}🔥 FORCE CLEANUP{Colors.NC}")
        print("=" * 20)
        
        # Kill all Python processes related to our project
        try:
            subprocess.run(["pkill", "-f", "uvicorn.*app"], capture_output=True)
            subprocess.run(["pkill", "-f", "python.*embed_server"], capture_output=True)
            subprocess.run(["pkill", "-f", "python.*llama_server"], capture_output=True)
            self.print_success("Force stopped all Python services")
        except:
            self.print_info("Force cleanup completed (some tools may not be available)")
        
        # Force stop Docker
        try:
            subprocess.run(["docker-compose", "kill"], capture_output=True)
            subprocess.run(["docker-compose", "down", "-v"], capture_output=True)
            self.print_success("Force stopped all Docker services")
        except:
            pass
    
    def run(self):
        """Main execution"""
        self.print_header()
        
        if self.args.force:
            self.force_cleanup()
            return
        
        if self.args.databases:
            self.stop_docker_services()
        else:
            # Stop all services
            print(f"\n{Colors.BLUE}Stopping all Lilo_EmotionalAI_Backend services...{Colors.NC}")
            
            self.stop_python_services()
            self.stop_go_services() 
            self.stop_docker_services()
        
        print(f"\n{Colors.GREEN}🎉 Shutdown complete!{Colors.NC}")
        self.print_info("All services have been stopped gracefully")


def create_parser():
    parser = argparse.ArgumentParser(
        description="Lilo_EmotionalAI_Backend Stop Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--databases', action='store_true',
                       help='Stop only database containers')
    parser.add_argument('--force', action='store_true',
                       help='Force stop all services')
    
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    
    manager = StopManager(args)
    manager.run()