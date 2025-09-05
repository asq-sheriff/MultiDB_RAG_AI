#!/usr/bin/env python3
"""
Interactive Demo System for MultiDB Therapeutic AI Chatbot
=========================================================

This script provides a comprehensive interactive demonstration of the 
therapeutic AI chatbot system, allowing users to explore all features
and dashboards through guided navigation menus.

Usage: python interactive_demo.py
"""

import asyncio
import getpass
import json
import os
import sys
import time

# Platform-specific imports for password masking
if os.name == 'nt':  # Windows
    import msvcrt
else:  # Unix/Linux/macOS
    import termios
    import tty
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# HTTP client for real API calls
try:
    import httpx
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False

# For demo purposes, assume real data is available if HTTP client is available
# The demo will check API availability at runtime
REAL_DATA_AVAILABLE = True

class DemoAPIClient:
    """API client for making real calls to the FastAPI application"""
    
    def __init__(self, base_url: str = "http://localhost:8000", demo_env_file: str = ".env.demo_v1"):
        self.base_url = base_url
        self.client = None
        self.auth_token = None
        self.demo_env_file = demo_env_file
        
    async def __aenter__(self):
        if HTTP_CLIENT_AVAILABLE:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def authenticate_demo_user(self, email: str, password: str) -> bool:
        """Authenticate a demo user and store auth token"""
        if not self.client:
            return False
            
        # Demo mode authentication - always succeeds for demo credentials
        if email.endswith("@example.com") and password.startswith("demo_"):
            self.auth_token = f"demo_token_{email.split('@')[0]}"
            return True
            
        # Try real auth endpoint via API Gateway if available
        try:
            response = await self.client.post("/api/v1/auth/login", json={
                "email": email,
                "password": password
            })
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                return True
        except Exception as e:
            print(f"Real authentication failed: {e}")
        return False
    
    async def send_chat_message(self, message: str, session_id: str = None, user_id: str = None, user_context: Dict = None) -> Optional[Dict]:
        """Send a real chat message to the API"""
        if not self.client:
            return None
            
        # Use demo session and user IDs if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        if not user_id:
            user_id = str(uuid.uuid4())
            
        payload = {
            "message": message,
            "session_id": session_id,
            "user_id": user_id,
            "enable_rag": True
        }
        
        # Add user context for role-based responses
        if user_context:
            payload.update({
                "user_name": user_context.get("name"),
                "user_role": user_context.get("role"),
                "care_context": user_context.get("care_context")
            })
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = await self.client.post("/internal/chat", json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Chat API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Chat request failed: {e}")
        return None
    
    async def check_api_health(self) -> bool:
        """Check if the API Gateway is running"""
        if not self.client:
            return False
            
        try:
            # Check API Gateway health directly
            response = await self.client.get("/health")
            return response.status_code == 200
        except:
            return False

# Terminal colors for better UX
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class UserRole(Enum):
    RESIDENT = "resident"
    FAMILY_MEMBER = "family_member"
    CARE_STAFF = "care_staff"
    CARE_MANAGER = "care_manager"
    ADMINISTRATOR = "administrator"
    HEALTH_PLAN_MANAGER = "health_plan_manager"

@dataclass
class DemoUser:
    """Demo user persona with realistic data"""
    name: str
    role: UserRole
    organization: str
    permissions: List[str]
    demo_data: Dict[str, Any]

@dataclass
class ConversationState:
    """Tracks conversation history and emotional state"""
    session_id: str
    messages: List[Dict[str, Any]]
    emotional_valence: float  # -1.0 to +1.0
    emotional_arousal: float  # 0.0 to 1.0
    crisis_level: str  # "none", "low", "medium", "high"
    interventions_used: List[str]

class InteractiveDemoSystem:
    """Main demo system orchestrator"""
    
    def __init__(self, use_real_data: bool = False):
        self.current_user: Optional[DemoUser] = None
        self.conversation_state: Optional[ConversationState] = None
        self.demo_users = self._create_demo_users()
        self.session_start_time = time.time()
        self.use_real_data = use_real_data and REAL_DATA_AVAILABLE and HTTP_CLIENT_AVAILABLE
        self.db_manager = None
        self.api_client = None
        
        if self.use_real_data:
            print(f"{Colors.GREEN}🗄️  Real API mode enabled{Colors.ENDC}")
        else:
            mode_reason = "no real databases" if not REAL_DATA_AVAILABLE else "no HTTP client" if not HTTP_CLIENT_AVAILABLE else "disabled"
            print(f"{Colors.YELLOW}🎭 Simulation mode ({mode_reason}){Colors.ENDC}")
        
    def _create_demo_users(self) -> Dict[str, DemoUser]:
        """Create realistic demo user personas"""
        return {
            "resident_sarah": DemoUser(
                name="Sarah Martinez",
                role=UserRole.RESIDENT,
                organization="Sunrise Senior Living",
                permissions=["chat", "view_own_data", "family_sharing"],
                demo_data={
                    "age": 78,
                    "care_level": "independent_living",
                    "medical_conditions": ["Type 2 diabetes", "Mild anxiety"],
                    "family_contacts": ["Jennifer (daughter)", "Michael (son)"],
                    "engagement_minutes_week": 42,
                    "ucla_loneliness_score": 6.2,
                    "recent_interventions": ["breathing_exercise", "family_call"],
                    "emotional_trend": "improving"
                }
            ),
            "family_jennifer": DemoUser(
                name="Jennifer Martinez",
                role=UserRole.FAMILY_MEMBER,
                organization="Sunrise Senior Living",
                permissions=["view_family_data", "emergency_contact", "weekly_summaries"],
                demo_data={
                    "relationship": "daughter",
                    "resident": "Sarah Martinez",
                    "contact_frequency": "2-3 times per week",
                    "portal_access": True,
                    "emergency_priority": 1
                }
            ),
            "staff_nurse": DemoUser(
                name="Maria Rodriguez, RN",
                role=UserRole.CARE_STAFF,
                organization="Sunrise Senior Living",
                permissions=["view_resident_status", "crisis_response", "care_documentation"],
                demo_data={
                    "shift": "day_shift",
                    "assigned_residents": 25,
                    "certifications": ["RN", "Gerontology"],
                    "crisis_response_trained": True
                }
            ),
            "manager_case": DemoUser(
                name="Dr. James Chen",
                role=UserRole.CARE_MANAGER,
                organization="BlueCare Advantage",
                permissions=["member_analytics", "care_plan_updates", "crisis_management"],
                demo_data={
                    "caseload_size": 150,
                    "specialization": "Geriatric care management",
                    "members_at_risk": 23,
                    "intervention_success_rate": 0.78
                }
            ),
            "admin_director": DemoUser(
                name="Linda Thompson",
                role=UserRole.ADMINISTRATOR,
                organization="Sunrise Senior Living",
                permissions=["full_admin", "user_management", "compliance_oversight"],
                demo_data={
                    "facility_residents": 245,
                    "staff_count": 45,
                    "hipaa_compliance_score": 100,
                    "family_satisfaction": 4.4
                }
            )
        }
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str, subtitle: str = ""):
        """Print formatted header"""
        self.clear_screen()
        print(f"{Colors.HEADER}{Colors.BOLD}")
        print("═" * 80)
        print(f"🏥  MULTIDB THERAPEUTIC AI CHATBOT - INTERACTIVE DEMO")
        print("═" * 80)
        print(f"{Colors.ENDC}")
        print(f"{Colors.CYAN}{Colors.BOLD}{title}{Colors.ENDC}")
        if subtitle:
            print(f"{Colors.BLUE}{subtitle}{Colors.ENDC}")
        print()
    
    async def get_user_id_from_database(self, email: str) -> Optional[str]:
        """Get actual user ID from PostgreSQL database"""
        try:
            import asyncpg
            conn = await asyncpg.connect(
                host="localhost",
                port=5433,  # Demo port
                database="demo_v1_chatbot_app", 
                user="demo_v1_user",
                password="demo_secure_password_v1"
            )
            
            # Query for user ID by email
            user_record = await conn.fetchrow(
                "SELECT id FROM demo_v1_auth.users WHERE email = $1", email
            )
            
            await conn.close()
            
            if user_record:
                return str(user_record['id'])
            else:
                print(f"⚠️ User not found in database: {email}")
                return None
                
        except Exception as e:
            print(f"❌ Database lookup failed: {e}")
            return None

    def print_menu(self, title: str, options: List[str], allow_back: bool = True):
        """Print interactive menu"""
        print(f"{Colors.YELLOW}{Colors.BOLD}{title}{Colors.ENDC}")
        print("─" * len(title))
        
        # Show current user info under every menu (except main menu)
        if self.current_user and title != "Select Demo Experience:":
            print(f"{Colors.CYAN}👤 Logged in as: {self.current_user.name} ({self.current_user.role.value}){Colors.ENDC}")
            print()
        
        for i, option in enumerate(options, 1):
            print(f"{Colors.GREEN}{i:2d}.{Colors.ENDC} {option}")
        
        if allow_back:
            print(f"{Colors.RED} 0.{Colors.ENDC} ← Back to Previous Menu")
        print()
    
    def get_user_choice(self, max_option: int, allow_zero: bool = True) -> int:
        """Get user menu choice with validation"""
        while True:
            try:
                choice = input(f"{Colors.CYAN}Choose an option: {Colors.ENDC}")
                choice_int = int(choice)
                
                if choice_int == 0 and allow_zero:
                    return 0
                elif 1 <= choice_int <= max_option:
                    return choice_int
                else:
                    print(f"{Colors.RED}Invalid choice. Please enter 1-{max_option}{' or 0 to go back' if allow_zero else ''}.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number.{Colors.ENDC}")
    
    def pause_for_user(self, message: str = "Press Enter to continue..."):
        """Pause and wait for user input"""
        input(f"\n{Colors.YELLOW}{message}{Colors.ENDC}")
    
    def check_permission(self, required_permission: str) -> bool:
        """Check if current user has required permission"""
        if not self.current_user:
            return False
        return required_permission in self.current_user.permissions
    
    def require_permission(self, required_permission: str, action_name: str = "this action") -> bool:
        """Check permission and show access denied message if unauthorized"""
        if not self.check_permission(required_permission):
            print(f"{Colors.RED}❌ Access Denied{Colors.ENDC}")
            print(f"{Colors.YELLOW}Your role ({self.current_user.role.value if self.current_user else 'unauthenticated'}) does not have permission for {action_name}.{Colors.ENDC}")
            print(f"{Colors.BLUE}Required permission: {required_permission}{Colors.ENDC}")
            self.pause_for_user()
            return False
        return True
    
    def get_password_masked(self, prompt: str) -> str:
        """Get password input with asterisk masking"""
        print(prompt, end='', flush=True)
        password = ""
        
        if os.name == 'nt':  # Windows
            while True:
                char = msvcrt.getch()
                if char == b'\r':  # Enter key
                    break
                elif char == b'\x08':  # Backspace
                    if len(password) > 0:
                        password = password[:-1]
                        print('\b \b', end='', flush=True)
                else:
                    password += char.decode('utf-8')
                    print('*', end='', flush=True)
        else:  # Unix/Linux/macOS
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                while True:
                    char = sys.stdin.read(1)
                    if char == '\n' or char == '\r':
                        break
                    elif char == '\x7f':  # Backspace
                        if len(password) > 0:
                            password = password[:-1]
                            print('\b \b', end='', flush=True)
                    elif ord(char) >= 32:  # Printable characters
                        password += char
                        print('*', end='', flush=True)
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        print()  # New line
        return password
    
    async def initialize_databases(self):
        """Initialize API client if using real data"""
        if self.use_real_data and not self.api_client:
            try:
                print(f"{Colors.BLUE}🔌 Initializing API client...{Colors.ENDC}")
                
                # Initialize API client
                self.api_client = DemoAPIClient()
                print(f"{Colors.BLUE}🌐 Checking API Gateway application...{Colors.ENDC}")
                
                async with self.api_client as client:
                    if await client.check_api_health():
                        print(f"{Colors.GREEN}✅ API Gateway is running{Colors.ENDC}")
                    else:
                        print(f"{Colors.YELLOW}⚠️  FastAPI application not detected - conversations will be simulated{Colors.ENDC}")
                        
                return True
            except Exception as e:
                print(f"{Colors.RED}❌ Failed to connect to demo databases: {e}{Colors.ENDC}")
                print(f"{Colors.YELLOW}📝 Falling back to simulation mode{Colors.ENDC}")
                self.use_real_data = False
                return False
        return True

    async def main_menu(self):
        """Main demo navigation menu"""
        # Initialize databases if needed
        if self.use_real_data:
            await self.initialize_databases()
        
        while True:
            self.print_header(
                "MAIN DEMO MENU",
                "Explore the complete therapeutic AI chatbot system"
            )
            
            # Show current mode
            if self.use_real_data:
                print(f"{Colors.GREEN}🌐 Mode: Real API & Database Demo (demo_v1){Colors.ENDC}")
                print(f"{Colors.BLUE}📡 Conversations will use real FastAPI endpoints when available{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}🎭 Mode: Simulation Demo{Colors.ENDC}")
                print(f"{Colors.YELLOW}💡 Use --use-real-data flag for real API integration{Colors.ENDC}")
            
            if self.current_user:
                print(f"{Colors.GREEN}Current User: {self.current_user.name} ({self.current_user.role.value}){Colors.ENDC}")
                print(f"{Colors.BLUE}Organization: {self.current_user.organization}{Colors.ENDC}")
                print()
            
            self.print_menu(
                "Select Demo Experience:",
                [
                    "🔐 User Authentication & Role Selection",
                    "👥 User Personas & Story Scenarios",
                    "💬 Live Conversation Simulation",
                    "📊 Dashboard & Analytics Views",
                    "🆘 Crisis Management Demonstration",
                    "⚙️  Administrative Features",
                    "🔗 Healthcare System Integrations",
                    "📱 Mobile & Accessibility Features",
                    "🏥 HIPAA Compliance Overview",
                    "📈 Quality Metrics & Reporting",
                    "🎯 Full End-to-End User Journey",
                    "🚪 Exit Demo"
                ],
                allow_back=False
            )
            
            choice = self.get_user_choice(12, allow_zero=False)
            
            if choice == 1:
                await self.authentication_demo()
            elif choice == 2:
                await self.user_personas_demo()
            elif choice == 3:
                await self.conversation_simulation()
            elif choice == 4:
                await self.dashboard_analytics_demo()
            elif choice == 5:
                await self.crisis_management_demo()
            elif choice == 6:
                await self.administrative_features_demo()
            elif choice == 7:
                await self.integration_demo()
            elif choice == 8:
                await self.mobile_accessibility_demo()
            elif choice == 9:
                await self.hipaa_compliance_demo()
            elif choice == 10:
                await self.quality_metrics_demo()
            elif choice == 11:
                await self.end_to_end_journey()
            elif choice == 12:
                self.show_demo_summary()
                return
    
    async def authentication_demo(self):
        """Demonstrate authentication and role-based access"""
        self.print_header("AUTHENTICATION & ROLE SELECTION", "Experience login flows for different user types")
        
        self.print_menu(
            "Select User Type to Login As:",
            [
                "👴 Senior Resident (Sarah Martinez, 78)",
                "👩 Family Member (Jennifer, Sarah's Daughter)", 
                "👩‍⚕️ Care Staff (Maria Rodriguez, RN)",
                "👨‍⚕️ Care Manager (Dr. James Chen)",
                "👩‍💼 Administrator (Linda Thompson, Director)"
            ]
        )
        
        choice = self.get_user_choice(5)
        if choice == 0:
            return
            
        user_keys = ["resident_sarah", "family_jennifer", "staff_nurse", "manager_case", "admin_director"]
        selected_user = self.demo_users[user_keys[choice - 1]]
        
        # Real authentication process
        print(f"\n{Colors.CYAN}🔐 Authentication for {selected_user.name}{Colors.ENDC}")
        print(f"{Colors.BLUE}Please enter your credentials (see README.md for demo credentials){Colors.ENDC}")
        print()
        
        # Get email
        email = input(f"{Colors.CYAN}Email: {Colors.ENDC}")
        
        # Check demo credentials
        demo_credentials = {
            "sarah.martinez.demo@example.com": "demo_password_resident_sarah",
            "jennifer.martinez.demo@example.com": "demo_password_family_jennifer", 
            "maria.rodriguez.demo@example.com": "demo_password_staff_maria",
            "james.chen.demo@example.com": "demo_password_manager_james",
            "linda.thompson.demo@example.com": "demo_password_admin_linda"
        }
        
        # Authentication retry loop
        while True:
            # Get password with asterisk masking
            password = self.get_password_masked(f"{Colors.CYAN}Password: {Colors.ENDC}")
            
            # Authenticate
            print(f"\n{Colors.BLUE}🔍 Authenticating user...{Colors.ENDC}")
            
            if email in demo_credentials and password == demo_credentials[email]:
                print(f"{Colors.GREEN}✓ Authentication successful{Colors.ENDC}")
                print(f"{Colors.GREEN}✓ Role permissions loaded: {', '.join(selected_user.permissions)}{Colors.ENDC}")
                print(f"{Colors.GREEN}✓ HIPAA compliance verified{Colors.ENDC}")
                
                # Try real API authentication if available
                if self.use_real_data and self.api_client:
                    try:
                        async with self.api_client as client:
                            auth_success = await client.authenticate_demo_user(email, password)
                            if auth_success:
                                print(f"{Colors.GREEN}✓ API authentication successful{Colors.ENDC}")
                            else:
                                print(f"{Colors.YELLOW}⚠️ API authentication failed - continuing with demo mode{Colors.ENDC}")
                    except Exception as e:
                        print(f"{Colors.YELLOW}⚠️ API unavailable - continuing with demo mode{Colors.ENDC}")
                
                self.current_user = selected_user
                break
            else:
                print(f"{Colors.RED}❌ Authentication failed{Colors.ENDC}")
                print(f"{Colors.YELLOW}Invalid credentials. Please try again.{Colors.ENDC}")
                print()
                
                self.print_menu(
                    "What would you like to do?",
                    [
                        "🔄 Try again with different credentials"
                    ]
                )
                
                retry_choice = self.get_user_choice(1)
                if retry_choice == 0:  # Back to previous menu
                    return
                elif retry_choice == 1:  # Try again
                    print(f"\n{Colors.CYAN}🔐 Authentication for {selected_user.name}{Colors.ENDC}")
                    print(f"{Colors.BLUE}Please enter your credentials (see README.md for demo credentials){Colors.ENDC}")
                    print()
                    email = input(f"{Colors.CYAN}Email: {Colors.ENDC}")
                    continue
        
        # Show role-specific welcome
        if selected_user.role == UserRole.RESIDENT:
            print(f"\n{Colors.BLUE}Welcome back, {selected_user.name}! 🌟{Colors.ENDC}")
            print(f"You have {len(selected_user.demo_data['recent_interventions'])} new wellness insights.")
            print(f"Your family has been notified of your positive progress this week.")
        elif selected_user.role == UserRole.FAMILY_MEMBER:
            print(f"\n{Colors.BLUE}Hello {selected_user.name}! 👋{Colors.ENDC}")
            print(f"Your mother Sarah is doing well - 42 minutes of engagement this week.")
            print(f"📧 You have 1 new weekly summary available.")
        elif selected_user.role == UserRole.CARE_STAFF:
            print(f"\n{Colors.BLUE}Good morning, {selected_user.name}! 🏥{Colors.ENDC}")
            print(f"👥 {selected_user.demo_data['assigned_residents']} residents on your caseload")
            print(f"🚨 2 wellness alerts require attention")
        elif selected_user.role == UserRole.CARE_MANAGER:
            print(f"\n{Colors.BLUE}Welcome, {selected_user.name}! 📋{Colors.ENDC}")
            print(f"📊 {selected_user.demo_data['members_at_risk']} members flagged for outreach")
            print(f"📈 Intervention success rate: {selected_user.demo_data['intervention_success_rate']:.1%}")
        elif selected_user.role == UserRole.ADMINISTRATOR:
            print(f"\n{Colors.BLUE}Administrator Dashboard - {selected_user.name} 🔧{Colors.ENDC}")
            print(f"🏢 {selected_user.demo_data['facility_residents']} residents, {selected_user.demo_data['staff_count']} staff")
            print(f"✅ HIPAA Compliance: {selected_user.demo_data['hipaa_compliance_score']}%")
        
        self.pause_for_user()
    
    async def user_personas_demo(self):
        """Show detailed user personas and their stories"""
        self.print_header("USER PERSONAS & STORY SCENARIOS", "Meet the users and understand their needs")
        
        # Build role-specific persona list based on permissions
        available_personas = []
        persona_functions = []
        
        # Residents can see their own persona
        if self.check_permission("view_own_data") or self.current_user.role == UserRole.RESIDENT:
            available_personas.append("👴 Sarah Martinez - Independent Living Resident")
            persona_functions.append(self._show_resident_persona)
        
        # Family members can see their persona and related resident
        if self.check_permission("view_family_data") or self.current_user.role == UserRole.FAMILY_MEMBER:
            available_personas.extend([
                "👴 Sarah Martinez - Independent Living Resident",
                "👩 Jennifer Martinez - Concerned Daughter"
            ])
            persona_functions.extend([self._show_resident_persona, self._show_family_persona])
        
        # Care staff can see resident, family, and staff personas
        if self.check_permission("view_resident_status") or self.current_user.role == UserRole.CARE_STAFF:
            if "👴 Sarah Martinez - Independent Living Resident" not in available_personas:
                available_personas.append("👴 Sarah Martinez - Independent Living Resident")
                persona_functions.append(self._show_resident_persona)
            if "👩 Jennifer Martinez - Concerned Daughter" not in available_personas:
                available_personas.append("👩 Jennifer Martinez - Concerned Daughter")
                persona_functions.append(self._show_family_persona)
            available_personas.append("👩‍⚕️ Maria Rodriguez - Day Shift Nurse")
            persona_functions.append(self._show_staff_persona)
        
        # Care managers can see resident and manager personas
        if self.check_permission("member_analytics") or self.current_user.role == UserRole.CARE_MANAGER:
            if "👴 Sarah Martinez - Independent Living Resident" not in available_personas:
                available_personas.append("👴 Sarah Martinez - Independent Living Resident")
                persona_functions.append(self._show_resident_persona)
            available_personas.append("👨‍⚕️ Dr. James Chen - Health Plan Case Manager")
            persona_functions.append(self._show_manager_persona)
        
        # Administrators can see all personas
        if self.check_permission("full_admin") or self.current_user.role == UserRole.ADMINISTRATOR:
            available_personas = [
                "👴 Sarah Martinez - Independent Living Resident",
                "👩 Jennifer Martinez - Concerned Daughter",
                "👩‍⚕️ Maria Rodriguez - Day Shift Nurse",
                "👨‍⚕️ Dr. James Chen - Health Plan Case Manager",
                "👩‍💼 Linda Thompson - Facility Administrator"
            ]
            persona_functions = [
                self._show_resident_persona,
                self._show_family_persona,
                self._show_staff_persona,
                self._show_manager_persona,
                self._show_admin_persona
            ]
        
        if not available_personas:
            print(f"{Colors.RED}❌ Access Denied{Colors.ENDC}")
            print(f"{Colors.YELLOW}Your role does not have permission to view user personas.{Colors.ENDC}") 
            self.pause_for_user()
            return
        
        self.print_menu(
            "Select Persona to Explore:",
            available_personas
        )
        
        choice = self.get_user_choice(len(available_personas))
        if choice == 0:
            return
            
        persona_functions[choice - 1]()
    
    def _show_resident_persona(self):
        """Show resident persona details"""
        user = self.demo_users["resident_sarah"]
        self.print_header("RESIDENT PERSONA", f"{user.name} - {user.demo_data['age']} years old")
        
        print(f"{Colors.BOLD}Background Story:{Colors.ENDC}")
        print("Sarah moved to Sunrise Senior Living 6 months ago after her husband passed.")
        print("She's generally independent but struggles with anxiety, especially around medical appointments.")
        print("Her daughter Jennifer lives 2 hours away and worries about her emotional wellbeing.")
        print()
        
        print(f"{Colors.BOLD}Medical Context:{Colors.ENDC}")
        for condition in user.demo_data['medical_conditions']:
            print(f"• {condition}")
        print()
        
        print(f"{Colors.BOLD}Current Wellness Metrics:{Colors.ENDC}")
        print(f"• Weekly Engagement: {user.demo_data['engagement_minutes_week']} minutes")
        print(f"• UCLA Loneliness Score: {user.demo_data['ucla_loneliness_score']}/9 (target: <6)")
        print(f"• Emotional Trend: {user.demo_data['emotional_trend'].title()}")
        print()
        
        print(f"{Colors.BOLD}Recent AI Interactions:{Colors.ENDC}")
        for intervention in user.demo_data['recent_interventions']:
            print(f"• {intervention.replace('_', ' ').title()} ✓")
        print()
        
        print(f"{Colors.BOLD}Care Goals:{Colors.ENDC}")
        print("1. Reduce anxiety around medical appointments")
        print("2. Increase family communication frequency")
        print("3. Build confidence with technology use")
        print("4. Maintain social connections within facility")
        
        self.pause_for_user()
    
    def _show_family_persona(self):
        """Show family member persona"""
        user = self.demo_users["family_jennifer"]
        self.print_header("FAMILY MEMBER PERSONA", f"{user.name} - {user.demo_data['relationship'].title()}")
        
        print(f"{Colors.BOLD}Relationship Context:{Colors.ENDC}")
        print(f"Jennifer is Sarah's daughter who lives 2 hours away and works full-time.")
        print(f"She calls her mother {user.demo_data['contact_frequency']} but worries it's not enough.")
        print(f"She has {user.demo_data['emergency_priority']} priority emergency contact status.")
        print()
        
        print(f"{Colors.BOLD}Primary Concerns:{Colors.ENDC}")
        print("• Is mom taking her medications consistently?")
        print("• How is she handling the transition to senior living?")
        print("• Will I know if she needs help or has a medical emergency?")
        print("• Is she making friends and staying socially engaged?")
        print()
        
        print(f"{Colors.BOLD}Portal Access Features:{Colors.ENDC}")
        if user.demo_data['portal_access']:
            print("✓ Weekly wellness summaries")
            print("✓ Emergency alert notifications")
            print("✓ Conversation highlights (privacy-protected)")
            print("✓ Care plan progress updates")
        
        print()
        print(f"{Colors.BOLD}Recent Family Update:{Colors.ENDC}")
        print(f"{Colors.GREEN}Mom had a great week! She used breathing exercises to manage")
        print(f"appointment anxiety and had lovely calls with Aunt Mary.{Colors.ENDC}")
        
        self.pause_for_user()
    
    def _show_staff_persona(self):
        """Show care staff persona"""
        user = self.demo_users["staff_nurse"]
        self.print_header("CARE STAFF PERSONA", f"{user.name} - Registered Nurse")
        
        print(f"{Colors.BOLD}Role & Responsibilities:{Colors.ENDC}")
        print(f"Maria works day shifts and is responsible for {user.demo_data['assigned_residents']} residents.")
        print(f"She's certified in {', '.join(user.demo_data['certifications'])} and crisis response.")
        print("She uses the Lilo system to monitor resident emotional wellbeing throughout her shift.")
        print()
        
        print(f"{Colors.BOLD}Daily Workflow with Lilo:{Colors.ENDC}")
        print("• 7:00 AM: Review overnight emotional status alerts")
        print("• 9:00 AM: Check residents who had difficult conversations")
        print("• 12:00 PM: Mid-shift wellness check for at-risk residents")
        print("• 3:00 PM: Review crisis escalations and follow-up needs")
        print("• 6:00 PM: Document shift notes for evening staff")
        print()
        
        print(f"{Colors.BOLD}Key Performance Indicators:{Colors.ENDC}")
        print("• Average crisis response time: 3.2 minutes (target: <5)")
        print("• Resident satisfaction with care: 4.6/5.0")
        print("• Family communication success: 95% families feel informed")
        print("• Documentation efficiency: 15 min/day time savings")
        
        self.pause_for_user()
    
    def _show_manager_persona(self):
        """Show care manager persona"""
        user = self.demo_users["manager_case"]
        self.print_header("CARE MANAGER PERSONA", f"{user.name} - Health Plan Case Manager")
        
        print(f"{Colors.BOLD}Population Health Focus:{Colors.ENDC}")
        print(f"Dr. Chen manages {user.demo_data['caseload_size']} Medicare Advantage members")
        print(f"identified as high-risk for loneliness and social isolation.")
        print(f"Currently {user.demo_data['members_at_risk']} members are flagged for proactive outreach.")
        print()
        
        print(f"{Colors.BOLD}Key Success Metrics:{Colors.ENDC}")
        print(f"• Intervention Success Rate: {user.demo_data['intervention_success_rate']:.1%}")
        print("• Average UCLA-3 Loneliness Improvement: 2.1 points")
        print("• Estimated ED Visit Reduction: 8% in engaged cohort")
        print("• Care Plan Adherence Improvement: 31%")
        print()
        
        print(f"{Colors.BOLD}Weekly Workflow:{Colors.ENDC}")
        print("• Monday: Review weekend crisis escalations and outcomes")
        print("• Tuesday: Analyze member engagement trends and identify gaps")
        print("• Wednesday: Proactive outreach to members with declining metrics")
        print("• Thursday: Care plan updates based on Lilo insights")
        print("• Friday: Generate outcomes reports for health plan leadership")
        
        self.pause_for_user()
    
    def _show_admin_persona(self):
        """Show administrator persona"""
        user = self.demo_users["admin_director"]
        self.print_header("ADMINISTRATOR PERSONA", f"{user.name} - Facility Director")
        
        print(f"{Colors.BOLD}Organizational Oversight:{Colors.ENDC}")
        print(f"Linda oversees Lilo implementation across {user.demo_data['facility_residents']} residents")
        print(f"and {user.demo_data['staff_count']} staff members at Sunrise Senior Living.")
        print(f"She's responsible for HIPAA compliance and family satisfaction.")
        print()
        
        print(f"{Colors.BOLD}Key Metrics Monitored:{Colors.ENDC}")
        print(f"• HIPAA Compliance Score: {user.demo_data['hipaa_compliance_score']}%")
        print(f"• Family Satisfaction: {user.demo_data['family_satisfaction']}/5.0")
        print("• System Adoption Rate: 87.5% (245/280 residents active)")
        print("• Staff Efficiency Improvement: 5 hours/week administrative time saved")
        print()
        
        print(f"{Colors.BOLD}Monthly Review Process:{Colors.ENDC}")
        print("• Quality metrics analysis with department heads")
        print("• HIPAA compliance audit and documentation review")
        print("• Family feedback compilation and response planning")
        print("• Staff training updates and competency verification")
        print("• Budget impact analysis and ROI calculation")
        
        self.pause_for_user()
    
    async def conversation_simulation(self):
        """Interactive conversation - real API or simulation"""
        if not self.current_user:
            print(f"{Colors.RED}Please select a user first (Option 1 from main menu){Colors.ENDC}")
            self.pause_for_user()
            return
        
        if self.use_real_data:
            await self._real_conversation_flow()
        else:
            await self._simulated_conversation_flow()
    
    async def _real_conversation_flow(self):
        """Real conversation using FastAPI endpoints"""
        self.print_header("LIVE CONVERSATION", f"Real AI chat as {self.current_user.name}")
        
        print(f"{Colors.BLUE}🌐 Real API Mode Instructions:{Colors.ENDC}")
        print(f"If services aren't running, start them with:")
        print(f"   {Colors.CYAN}./demo/scripts/start_local_services.sh{Colors.ENDC}")
        print(f"   (This starts all required services including AI Gateway)")
        print()
        
        # Check if API is available with retry logic
        print(f"{Colors.BLUE}🔍 Checking if API Gateway is available...{Colors.ENDC}")
        
        api_available = False
        for attempt in range(3):
            try:
                async with DemoAPIClient() as client:
                    if await client.check_api_health():
                        api_available = True
                        print(f"{Colors.GREEN}✅ API Gateway is running and healthy{Colors.ENDC}")
                        break
                    else:
                        if attempt < 2:
                            print(f"{Colors.YELLOW}🔄 API not ready, retrying... (attempt {attempt + 1}/3){Colors.ENDC}")
                            await asyncio.sleep(2)
            except Exception as e:
                if attempt < 2:
                    print(f"{Colors.YELLOW}🔄 Connection failed, retrying... (attempt {attempt + 1}/3){Colors.ENDC}")
                    await asyncio.sleep(2)
                else:
                    print(f"{Colors.RED}❌ API connection failed: {e}{Colors.ENDC}")
                    
        if not api_available:
            print(f"{Colors.RED}❌ API Gateway not available after retries{Colors.ENDC}")
            print(f"{Colors.YELLOW}💡 Please ensure services are running:{Colors.ENDC}")
            print(f"   {Colors.CYAN}./demo/scripts/start_local_services.sh{Colors.ENDC}")
            print(f"{Colors.YELLOW}📝 Falling back to simulation mode{Colors.ENDC}")
            await self._simulated_conversation_flow()
            return
        
        try:
            async with DemoAPIClient() as client:
                
                # Get demo user credentials
                user_email = None
                user_password = None
                if self.current_user.name == "Sarah Martinez":
                    user_email = "sarah.martinez.demo@example.com"
                    user_password = "demo_s_m_resident"
                elif self.current_user.name == "Jennifer Martinez":
                    user_email = "jennifer.martinez.demo@example.com"
                    user_password = "demo_j_m_family"
                elif self.current_user.name == "Maria Rodriguez, RN":
                    user_email = "maria.rodriguez.demo@example.com"
                    user_password = "demo_m_r_staff"
                elif self.current_user.name == "Dr. James Chen":
                    user_email = "james.chen.demo@example.com"
                    user_password = "demo_j_c_physician"
                elif self.current_user.name == "Linda Thompson":
                    user_email = "linda.thompson.demo@example.com"
                    user_password = "demo_l_t_admin"
                
                if not user_email:
                    print(f"{Colors.RED}❌ Demo credentials not found for {self.current_user.name}{Colors.ENDC}")
                    await self._simulated_conversation_flow()
                    return
                
                # Demo mode: Get actual user ID from database
                print(f"{Colors.BLUE}🔐 Demo user authenticated: {self.current_user.name}{Colors.ENDC}")
                
                # Get actual user ID from database for proper context
                actual_user_id = await self.get_user_id_from_database(user_email)
                if not actual_user_id:
                    print(f"{Colors.RED}❌ Could not find user ID in database for {user_email}{Colors.ENDC}")
                    await self._simulated_conversation_flow()
                    return
                
                print(f"{Colors.GREEN}✅ Ready for conversation with user ID: {actual_user_id[:8]}...{Colors.ENDC}")
                
                # Interactive conversation loop
                session_id = str(uuid.uuid4())
                user_id = actual_user_id
                print(f"\n{Colors.CYAN}💬 Starting real conversation with Lilo...{Colors.ENDC}")
                print(f"{Colors.YELLOW}Type 'quit' to end the conversation{Colors.ENDC}")
                print()
                
                while True:
                    user_input = input(f"{Colors.BOLD}{self.current_user.name}:{Colors.ENDC} ")
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break
                        
                    if not user_input.strip():
                        continue
                    
                    print(f"{Colors.BLUE}🐱 Lilo is thinking...{Colors.ENDC}")
                    
                    # Prepare user context for API
                    user_context = {
                        "name": self.current_user.name,
                        "role": self.current_user.role.value,
                        "user_id": user_id,  # Include the actual database user ID
                        "care_context": getattr(self.current_user, 'demo_data', {})
                    }
                    
                    # Send real API request with retry logic
                    response = None
                    for retry_attempt in range(3):
                        try:
                            response = await client.send_chat_message(user_input, session_id, user_id, user_context)
                            if response:
                                break
                        except Exception as e:
                            if retry_attempt < 2:
                                print(f"{Colors.YELLOW}🔄 Retrying message... (attempt {retry_attempt + 1}/3){Colors.ENDC}")
                                await asyncio.sleep(1)
                            else:
                                print(f"{Colors.RED}❌ Failed to send message after retries: {e}{Colors.ENDC}")
                    
                    if response:
                        # Try multiple response fields - API may return different formats
                        ai_message = (
                            response.get('response') or 
                            response.get('content') or 
                            response.get('message', {}).get('content') or
                            'Sorry, I had trouble processing that.'
                        )
                        
                        # Handle empty responses gracefully
                        if not ai_message or ai_message.strip() == "":
                            ai_message = "I understand you're reaching out. Let me try a different approach to help you better."
                        
                        print(f"{Colors.BLUE}🐱 Lilo:{Colors.ENDC} {ai_message}")
                        
                        # Show RAG and processing info
                        if response.get('rag_used'):
                            print(f"{Colors.CYAN}   📚 Knowledge used: {len(response.get('sources', []))} sources{Colors.ENDC}")
                        print(f"{Colors.CYAN}   ⏱️  Processing time: {response.get('processing_time_ms', 0):.0f}ms{Colors.ENDC}")
                        
                        # Show additional info if available
                        if response.get('emotional_analysis'):
                            emotional = response['emotional_analysis']
                            print(f"{Colors.CYAN}   💭 Emotional analysis: {emotional.get('mood', 'N/A')}{Colors.ENDC}")
                        
                        if response.get('crisis_detection'):
                            crisis = response['crisis_detection']
                            level = crisis.get('risk_level', 'none')
                            if level != 'none':
                                print(f"{Colors.YELLOW}   ⚠️  Crisis level: {level}{Colors.ENDC}")
                    else:
                        print(f"{Colors.RED}🐱 Lilo: I'm having trouble connecting right now. Please try again.{Colors.ENDC}")
                    
                    print()
        
        except Exception as e:
            print(f"{Colors.RED}❌ API connection error: {e}{Colors.ENDC}")
            print(f"{Colors.YELLOW}📝 Falling back to simulation mode{Colors.ENDC}")
            await self._simulated_conversation_flow()
            return
        
        self.pause_for_user("Press Enter to return to menu...")
    
    async def _simulated_conversation_flow(self):
        """Original simulated conversation flow"""
        self.print_header("LIVE CONVERSATION SIMULATION", f"Experience Lilo as {self.current_user.name}")
        
        # Initialize conversation state if not exists
        if not self.conversation_state:
            self.conversation_state = ConversationState(
                session_id=f"demo_session_{int(time.time())}",
                messages=[],
                emotional_valence=0.0,
                emotional_arousal=0.3,
                crisis_level="none",
                interventions_used=[]
            )
        
        # Role-specific conversation starters
        if self.current_user.role == UserRole.RESIDENT:
            await self._resident_conversation_flow()
        elif self.current_user.role == UserRole.FAMILY_MEMBER:
            await self._family_conversation_flow()
        elif self.current_user.role in [UserRole.CARE_STAFF, UserRole.CARE_MANAGER]:
            await self._staff_conversation_flow()
        else:
            await self._admin_conversation_flow()
    
    async def _resident_conversation_flow(self):
        """Simulate resident conversation with emotional AI"""
        print(f"{Colors.BLUE}🐱 Lilo: Good morning, Sarah! How are you feeling today?{Colors.ENDC}")
        print()
        
        self.print_menu(
            "How would you like to respond?",
            [
                "😊 I'm feeling pretty good today, thanks for asking!",
                "😰 I'm anxious about my doctor's appointment this afternoon",
                "😢 I'm feeling lonely and missing my late husband",
                "😴 I didn't sleep well last night and feel tired",
                "🤔 I'm not sure how to express how I'm feeling"
            ]
        )
        
        choice = self.get_user_choice(5)
        if choice == 0:
            return
        
        responses = [
            ("positive", 0.6, 0.2),
            ("anxious", -0.4, 0.8),
            ("grieving", -0.7, 0.4),
            ("tired", -0.3, 0.6),
            ("confused", 0.0, 0.5)
        ]
        
        emotion_type, valence, arousal = responses[choice - 1]
        self.conversation_state.emotional_valence = valence
        self.conversation_state.emotional_arousal = arousal
        
        # Show AI analysis
        print(f"\n{Colors.YELLOW}🧠 AI Emotional Analysis:{Colors.ENDC}")
        print(f"Valence: {valence:+.1f} (negative ← 0 → positive)")
        print(f"Arousal: {arousal:.1f} (calm ← 0 → excited/stressed)")
        print(f"Classification: {emotion_type.title()}")
        
        await asyncio.sleep(2)
        
        # Generate appropriate AI response
        if emotion_type == "positive":
            print(f"\n{Colors.BLUE}🐱 Lilo: That's wonderful to hear! It sounds like you're having a good start to your day.{Colors.ENDC}")
            print(f"Would you like to share what's contributing to your positive mood?")
            interventions = ["Journal about positive feelings", "Call Jennifer to share good news", "Join morning activities"]
        elif emotion_type == "anxious":
            print(f"\n{Colors.BLUE}🐱 Lilo: I understand that medical appointments can feel nerve-wracking.{Colors.ENDC}")
            print(f"It's completely normal to feel anxious about these visits.")
            interventions = ["Try 2-minute breathing exercise", "Call Jennifer for support", "Practice appointment questions"]
        elif emotion_type == "grieving":
            print(f"\n{Colors.BLUE}🐱 Lilo: I can hear how much you miss him. Grief comes in waves,{Colors.ENDC}")
            print(f"and it's okay to feel sad sometimes. You're not alone in this.")
            interventions = ["Share a favorite memory", "Look at photos together", "Call family member"]
        elif emotion_type == "tired":
            print(f"\n{Colors.BLUE}🐱 Lilo: Poor sleep can really affect how we feel during the day.{Colors.ENDC}")
            print(f"Let's see if we can help you feel more rested.")
            interventions = ["Gentle relaxation exercise", "Review sleep routine", "Check medication timing"]
        else:
            print(f"\n{Colors.BLUE}🐱 Lilo: Sometimes feelings can be hard to put into words.{Colors.ENDC}")
            print(f"Would you like to try describing what your body feels like right now?")
            interventions = ["Body awareness check-in", "Simple emotion cards", "Free-form journaling"]
        
        print()
        self.print_menu("Suggested Interventions:", interventions)
        
        intervention_choice = self.get_user_choice(len(interventions))
        if intervention_choice > 0:
            selected_intervention = interventions[intervention_choice - 1]
            await self._simulate_intervention(selected_intervention)
    
    async def _simulate_intervention(self, intervention: str):
        """Simulate an intervention experience"""
        print(f"\n{Colors.CYAN}🎯 Starting: {intervention}{Colors.ENDC}")
        print()
        
        if "breathing" in intervention.lower():
            await self._breathing_exercise_simulation()
        elif "call" in intervention.lower():
            await self._family_call_simulation()
        elif "journal" in intervention.lower():
            await self._journaling_simulation()
        else:
            print(f"{Colors.GREEN}✓ {intervention} completed successfully{Colors.ENDC}")
            print(f"User reported feeling 'somewhat better' after the intervention.")
        
        # Update emotional state
        self.conversation_state.emotional_valence += 0.3
        self.conversation_state.emotional_arousal -= 0.2
        self.conversation_state.interventions_used.append(intervention)
        
        print(f"\n{Colors.YELLOW}📊 Emotional Impact:{Colors.ENDC}")
        print(f"Mood improvement: +0.3 points")
        print(f"Stress reduction: -0.2 points")
        print(f"Intervention logged for care team review")
        
        self.pause_for_user()
    
    async def _breathing_exercise_simulation(self):
        """Simulate breathing exercise"""
        print(f"{Colors.GREEN}🫁 Guided Breathing Exercise{Colors.ENDC}")
        print("Let's take a moment to focus on your breathing...")
        print()
        
        for i in range(3):
            print(f"Breathe in slowly for 4 counts... {Colors.CYAN}1... 2... 3... 4{Colors.ENDC}")
            await asyncio.sleep(1)
            print(f"Hold for 4 counts... {Colors.YELLOW}1... 2... 3... 4{Colors.ENDC}")
            await asyncio.sleep(1)
            print(f"Breathe out slowly for 6 counts... {Colors.BLUE}1... 2... 3... 4... 5... 6{Colors.ENDC}")
            await asyncio.sleep(1)
            if i < 2:
                print()
        
        print(f"\n{Colors.GREEN}✓ Breathing exercise completed{Colors.ENDC}")
        print(f"How do you feel now? (Better/Same/Worse)")
    
    async def _family_call_simulation(self):
        """Simulate family call assistance"""
        print(f"{Colors.GREEN}📞 Family Call Assistance{Colors.ENDC}")
        print()
        print(f"I can help you connect with Jennifer. Here's what I know:")
        print(f"• She usually answers around this time")
        print(f"• Last call was 3 days ago - she'd love to hear from you")
        print(f"• You could share your positive mood with her")
        print()
        print(f"Would you like me to:")
        print(f"1. Call Jennifer now")
        print(f"2. Send her a message first")
        print(f"3. Schedule a call for later")
        print()
        print(f"{Colors.GREEN}✓ Family connection facilitated{Colors.ENDC}")
    
    async def _journaling_simulation(self):
        """Simulate journaling exercise"""
        print(f"{Colors.GREEN}📝 Guided Journaling{Colors.ENDC}")
        print()
        print(f"Let's explore your feelings through some gentle questions:")
        print()
        print(f"💭 What's one thing that brought you joy this week?")
        print(f"💭 How has your energy level been lately?")
        print(f"💭 What would help you feel more prepared for tomorrow?")
        print()
        print(f"[User provides thoughtful responses...]")
        print()
        print(f"{Colors.GREEN}✓ Journaling entry saved securely{Colors.ENDC}")
        print(f"✓ Patterns will be shared with care team (with your consent)")
    
    async def _family_conversation_flow(self):
        """Family member conversation flow"""
        print(f"{Colors.BLUE}👩‍💼 Family Portal: Welcome back, Jennifer!{Colors.ENDC}")
        print()
        print(f"Here's your mother's latest update:")
        print(f"📊 This week: 42 minutes engaged, generally positive mood")
        print(f"✅ Used breathing exercises 2 times")
        print(f"✅ Had conversation with Aunt Mary")
        print(f"⚠️ Expressed anxiety about Thursday appointment")
        print()
        
        self.print_menu(
            "What would you like to do?",
            [
                "📱 Send encouraging message to mom",
                "📞 Schedule a call with mom",
                "📧 Request detailed weekly report",
                "🚨 Review any safety alerts",
                "👩‍⚕️ Message care team"
            ]
        )
        
        choice = self.get_user_choice(5)
        if choice > 0:
            print(f"\n{Colors.GREEN}✓ Action completed successfully{Colors.ENDC}")
            print(f"Your mother will receive your caring message within minutes.")
    
    async def _staff_conversation_flow(self):
        """Staff dashboard conversation flow"""
        print(f"{Colors.BLUE}👩‍⚕️ Care Staff Dashboard - {self.current_user.name}{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}Current Shift Alerts:{Colors.ENDC}")
        print(f"🟡 Medium Priority: Sarah M. - Appointment anxiety (Room 215)")
        print(f"🟢 Low Priority: Robert K. - Social engagement request (Room 118)")
        print()
        print(f"{Colors.BOLD}Residents Requiring Check-in:{Colors.ENDC}")
        print(f"• Margaret S. (Room 203) - Missed morning conversation")
        print(f"• David L. (Room 156) - Family expressed concern")
        print()
        
        self.print_menu(
            "Select Action:",
            [
                "🔍 View Sarah's conversation details",
                "📞 Initiate wellness check call",
                "📝 Update care plan notes",
                "👨‍👩‍👧‍👦 Contact family member",
                "📊 Generate shift report"
            ]
        )
        
        choice = self.get_user_choice(5)
        if choice == 1:
            await self._show_conversation_details()
    
    async def _show_conversation_details(self):
        """Show detailed conversation analysis for staff"""
        print(f"\n{Colors.CYAN}📋 Conversation Analysis - Sarah M.{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}Session: Today 10:23 AM (15 minutes ago){Colors.ENDC}")
        print()
        print(f"Sarah: I'm feeling anxious about my doctor's appointment this afternoon")
        print(f"Lilo: I understand that medical appointments can feel nerve-wracking...")
        print(f"Sarah: Yes, I keep worrying about what they might find")
        print(f"Lilo: Would you like to try a breathing exercise to help calm your nerves?")
        print(f"Sarah: That sounds good, let's try it")
        print()
        print(f"{Colors.YELLOW}🧠 AI Analysis:{Colors.ENDC}")
        print(f"• Emotional State: Anxious (-0.4 valence, 0.8 arousal)")
        print(f"• Intervention: Breathing exercise (successful)")
        print(f"• Post-intervention: Calmer (-0.1 valence, 0.4 arousal)")
        print(f"• Risk Level: Low (appointment-specific anxiety)")
        print()
        print(f"{Colors.GREEN}✓ Recommended Action: Continue monitoring, offer pre-appointment support{Colors.ENDC}")
        
        self.pause_for_user()
    
    async def _admin_conversation_flow(self):
        """Administrator system overview"""
        print(f"{Colors.BLUE}👩‍💼 Administrator Dashboard - {self.current_user.name}{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}System Health Overview:{Colors.ENDC}")
        print(f"🟢 All services operational")
        print(f"🟢 Database connections stable")
        print(f"🟢 HIPAA compliance: 100%")
        print(f"🟡 Performance grade: B+ (target: A)")
        print()
        
        self.print_menu(
            "Administrative Functions:",
            [
                "👥 User Management & Onboarding",
                "📊 Generate Compliance Report", 
                "🔧 System Configuration",
                "📈 Performance Analytics",
                "🛡️ Security Audit Log"
            ]
        )
        
        choice = self.get_user_choice(5)
        if choice > 0:
            print(f"\n{Colors.GREEN}✓ Administrative function accessed{Colors.ENDC}")
            print(f"Full administrative capabilities available for authorized users.")
    
    async def dashboard_analytics_demo(self):
        """Demonstrate various dashboard views"""
        self.print_header("DASHBOARD & ANALYTICS VIEWS", "Explore role-specific dashboards and insights")
        
        # Build role-specific menu based on user permissions
        available_dashboards = []
        dashboard_functions = []
        
        # Resident Dashboard - only for residents or view_own_data permission
        if self.check_permission("view_own_data") or self.check_permission("chat"):
            available_dashboards.append("🏠 Resident Personal Wellness Dashboard")
            dashboard_functions.append(self._resident_wellness_dashboard)
        
        # Family Portal - only for family members or view_family_data permission
        if self.check_permission("view_family_data") or self.check_permission("weekly_summaries"):
            available_dashboards.append("👨‍👩‍👧‍👦 Family Portal Overview")
            dashboard_functions.append(self._family_portal_dashboard)
        
        # Care Staff Dashboard - only for care staff
        if self.check_permission("view_resident_status") or self.check_permission("crisis_response"):
            available_dashboards.append("👩‍⚕️ Care Staff Monitoring Dashboard")
            dashboard_functions.append(self._care_staff_dashboard)
        
        # Care Manager Analytics - only for care managers
        if self.check_permission("member_analytics") or self.check_permission("care_plan_updates"):
            available_dashboards.append("📈 Care Manager Population Health Analytics")
            dashboard_functions.append(self._population_health_dashboard)
        
        # Administrator Dashboards - only for administrators
        if self.check_permission("full_admin") or self.check_permission("user_management"):
            available_dashboards.extend([
                "🏢 Administrator Facility Overview",
                "📊 Real-time Performance Metrics",
                "🎯 Quality Assurance Dashboard"
            ])
            dashboard_functions.extend([
                self._facility_overview_dashboard,
                self._realtime_metrics_dashboard,
                self._quality_assurance_dashboard
            ])
        
        if not available_dashboards:
            print(f"{Colors.RED}❌ Access Denied{Colors.ENDC}")
            print(f"{Colors.YELLOW}Your role ({self.current_user.role.value if self.current_user else 'unauthenticated'}) does not have permission to view dashboards.{Colors.ENDC}") 
            self.pause_for_user()
            return
        
        self.print_menu(
            "Select Dashboard Type:",
            available_dashboards
        )
        
        choice = self.get_user_choice(len(available_dashboards))
        if choice == 0:
            return
            
        await dashboard_functions[choice - 1]()
    
    async def _resident_wellness_dashboard(self):
        """Show resident personal wellness dashboard"""
        self.print_header("PERSONAL WELLNESS DASHBOARD", "Sarah's Progress & Insights")
        
        print(f"{Colors.BOLD}Emotional Wellness Trend (30 Days):{Colors.ENDC}")
        print(f"📈 Anxiety Level: {Colors.GREEN}Decreased 25%{Colors.ENDC} (High → Moderate)")
        print(f"📈 Social Connection: {Colors.GREEN}Increased 40%{Colors.ENDC} (2 → 3.2 contacts/week)")
        print(f"📊 Sleep Quality: {Colors.BLUE}Stable{Colors.ENDC} (Good 6/7 nights)")
        print(f"📊 Activity Participation: {Colors.GREEN}Improved{Colors.ENDC} (60% → 80% attendance)")
        print()
        
        print(f"{Colors.BOLD}Intervention Effectiveness:{Colors.ENDC}")
        print(f"• Breathing Exercises: {Colors.GREEN}85% report feeling calmer{Colors.ENDC}")
        print(f"• Journaling: {Colors.GREEN}12 entries, positive reflection trend{Colors.ENDC}")
        print(f"• Social Prompts: {Colors.YELLOW}70% follow-through rate{Colors.ENDC}")
        print(f"• Physical Wellness: {Colors.GREEN}90% medication adherence{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Personal Goals Progress:{Colors.ENDC}")
        print(f"Goal 1: Reduce morning anxiety {Colors.GREEN}✓ Achieved{Colors.ENDC} (Target: 50% reduction)")
        print(f"Goal 2: Increase family contact {Colors.GREEN}✓ Achieved{Colors.ENDC} (Target: 2+ calls/week)")  
        print(f"Goal 3: Join group activities {Colors.YELLOW}→ In Progress{Colors.ENDC} (Target: 2+ activities/week)")
        
        self.pause_for_user()
    
    async def _family_portal_dashboard(self):
        """Show family portal dashboard"""
        self.print_header("FAMILY PORTAL DASHBOARD", "Jennifer's View of Sarah's Wellness")
        
        print(f"{Colors.GREEN}{Colors.BOLD}Mom is doing well this week! 😊{Colors.ENDC}")
        print(f"Engagement: 42 minutes | Mood: Generally positive | Safety: No concerns")
        print()
        
        print(f"{Colors.BOLD}Recent Highlights:{Colors.ENDC}")
        print(f"{Colors.GREEN}• Completed virtual book club discussion Tuesday{Colors.ENDC}")
        print(f"{Colors.GREEN}• Had a lovely phone call with Aunt Mary Wednesday{Colors.ENDC}")
        print(f"{Colors.GREEN}• Successfully used breathing exercise during anxiety Thursday{Colors.ENDC}")
        print(f"{Colors.GREEN}• Enjoyed virtual gardening workshop Friday{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}This Week's Care Notes:{Colors.ENDC}")
        print(f"{Colors.BLUE}\"Margaret showed great resilience managing appointment anxiety and{Colors.ENDC}")
        print(f"{Colors.BLUE}used her coping strategies effectively. She's been more social and{Colors.ENDC}")
        print(f"{Colors.BLUE}engaged. Continue encouraging family calls - they clearly bring her joy!\"{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Communication Preferences:{Colors.ENDC}")
        print(f"✓ Weekly summary emails (Fridays)")
        print(f"✓ Emergency alerts (Immediate)")
        print(f"✓ Positive milestone notifications (As they happen)")
        print(f"⚠ Daily updates (Disabled to avoid overwhelm)")
        
        self.pause_for_user()
    
    async def _care_staff_dashboard(self):
        """Show care staff monitoring dashboard"""
        self.print_header("CARE STAFF DASHBOARD", "Maria's Current Shift Overview")
        
        print(f"{Colors.BOLD}Real-time Resident Status ({datetime.now().strftime('%I:%M %p')}):{Colors.ENDC}")
        print()
        print(f"🟢 {Colors.GREEN}Stable (20 residents):{Colors.ENDC} Normal conversations, no alerts")
        print(f"🟡 {Colors.YELLOW}Attention Needed (3 residents):{Colors.ENDC}")
        print(f"   • Sarah M. (215) - Pre-appointment anxiety")
        print(f"   • Robert K. (118) - Requesting social activity")
        print(f"   • Margaret T. (203) - Missed morning check-in")
        print(f"🔴 {Colors.RED}Urgent (1 resident):{Colors.ENDC}")
        print(f"   • David L. (156) - Family concern, needs wellness check")
        print()
        
        print(f"{Colors.BOLD}Shift Metrics:{Colors.ENDC}")
        print(f"• Crisis Interventions Today: 0")
        print(f"• Successful Wellness Checks: 18/20 completed")
        print(f"• Family Communications: 5 updates sent")
        print(f"• Average Response Time: 3.2 minutes")
        print()
        
        print(f"{Colors.BOLD}Upcoming Actions:{Colors.ENDC}")
        print(f"• 2:00 PM: Check on Sarah before appointment")
        print(f"• 2:30 PM: Wellness call for David L.")
        print(f"• 3:00 PM: Document shift handover notes")
        
        self.pause_for_user()
    
    async def _population_health_dashboard(self):
        """Show population health analytics"""
        self.print_header("POPULATION HEALTH ANALYTICS", "Dr. Chen's Member Engagement Overview")
        
        print(f"{Colors.BOLD}Member Engagement Overview - BlueCare Advantage:{Colors.ENDC}")
        print(f"Reporting Period: Last 30 Days")
        print()
        
        print(f"{Colors.BOLD}Engagement Metrics:{Colors.ENDC}")
        print(f"• Enrolled Members: {Colors.CYAN}1,247{Colors.ENDC} (loneliness risk cohort)")
        print(f"• Active Users: {Colors.GREEN}1,089 (87.3% engagement rate){Colors.ENDC}")
        print(f"• Average Conversation Time: {Colors.GREEN}28 minutes/week{Colors.ENDC}")
        print(f"• Crisis Escalations: {Colors.GREEN}12 (100% handled appropriately){Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Health Outcomes:{Colors.ENDC}")
        print(f"• UCLA-3 Loneliness Scores: {Colors.GREEN}↓ 2.1 points average{Colors.ENDC}")
        print(f"• Care Plan Adherence: {Colors.GREEN}↑ 31% improvement{Colors.ENDC}")
        print(f"• Preventive Care Completion: {Colors.GREEN}↑ 18% increase{Colors.ENDC}")
        print(f"• Care Manager Contacts: {Colors.GREEN}↑ 25% proactive outreach{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Utilization Impact (Preliminary):{Colors.ENDC}")
        print(f"• Emergency Department Visits: {Colors.GREEN}↓ 8% in engaged cohort{Colors.ENDC}")
        print(f"• Unplanned Readmissions: {Colors.GREEN}↓ 12% reduction{Colors.ENDC}")
        print(f"• Primary Care Appointment Adherence: {Colors.GREEN}↑ 15%{Colors.ENDC}")
        print(f"• Member Satisfaction (CAHPS): {Colors.GREEN}+0.3 point improvement{Colors.ENDC}")
        
        self.pause_for_user()
    
    async def _facility_overview_dashboard(self):
        """Show facility administrator overview"""
        if not self.require_permission("full_admin", "facility overview dashboard"):
            return
        
        self.print_header("FACILITY OVERVIEW DASHBOARD", "Linda's Organizational Metrics")
        
        print(f"{Colors.BOLD}Facility Wellness Overview - Sunrise Senior Living:{Colors.ENDC}")
        print(f"Reporting Period: Q3 2025")
        print()
        
        print(f"{Colors.BOLD}Population Metrics:{Colors.ENDC}")
        print(f"• Active Users: {Colors.GREEN}245/280 residents (87.5% adoption){Colors.ENDC}")
        print(f"• Average Engagement: {Colors.GREEN}31 minutes/week per resident{Colors.ENDC}")
        print(f"• Crisis Events: {Colors.GREEN}3 (all handled within SLA){Colors.ENDC}")
        print(f"• Family Satisfaction: {Colors.GREEN}4.4/5.0 average{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Clinical Outcomes:{Colors.ENDC}")
        print(f"• Anxiety-Related Incidents: {Colors.GREEN}↓ 35% vs. baseline{Colors.ENDC}")
        print(f"• Medication Adherence: {Colors.GREEN}↑ 22% improvement{Colors.ENDC}")
        print(f"• Social Activity Participation: {Colors.GREEN}↑ 28% increase{Colors.ENDC}")
        print(f"• Family Communication: {Colors.GREEN}↑ 45% more frequent contact{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Financial Impact (Estimated):{Colors.ENDC}")
        print(f"• Reduced After-Hours Staff Calls: {Colors.GREEN}$2,400/month savings{Colors.ENDC}")
        print(f"• Decreased Behavioral Incident Reports: {Colors.GREEN}28% reduction{Colors.ENDC}")
        print(f"• Family Satisfaction Improvement: {Colors.GREEN}NPS +18 points{Colors.ENDC}")
        print(f"• Staff Efficiency Gains: {Colors.GREEN}5 hours/week administrative time{Colors.ENDC}")
        
        self.pause_for_user()
    
    async def _realtime_metrics_dashboard(self):
        """Show real-time system metrics"""
        if not self.require_permission("full_admin", "real-time performance metrics"):
            return
        
        self.print_header("REAL-TIME PERFORMANCE METRICS", "Live System Health & Performance")
        
        print(f"{Colors.BOLD}System Performance (Live):{Colors.ENDC}")
        print(f"🟢 API Response Time: {Colors.GREEN}347ms average{Colors.ENDC} (Target: <500ms)")
        print(f"🟢 Database Query Speed: {Colors.GREEN}95th percentile <200ms{Colors.ENDC}")
        print(f"🟢 Concurrent Users: {Colors.GREEN}1,089 active{Colors.ENDC} (Capacity: 5,000)")
        print(f"🟢 System Uptime: {Colors.GREEN}99.94%{Colors.ENDC} (Target: 99.9%)")
        print()
        
        print(f"{Colors.BOLD}AI Service Performance:{Colors.ENDC}")
        print(f"• Embedding Service: {Colors.GREEN}Ready{Colors.ENDC} (BGE model loaded)")
        print(f"• Generation Service: {Colors.GREEN}Ready{Colors.ENDC} (Qwen 1.7B active)")
        print(f"• Crisis Detection: {Colors.GREEN}100% accuracy{Colors.ENDC} (0 false negatives)")
        print(f"• RAG Pipeline: {Colors.YELLOW}Needs attention{Colors.ENDC} (retrieval issue)")
        print()
        
        print(f"{Colors.BOLD}Database Health:{Colors.ENDC}")
        print(f"• PostgreSQL: {Colors.GREEN}Healthy{Colors.ENDC} (5 schemas active)")
        print(f"• MongoDB Atlas: {Colors.GREEN}Connected{Colors.ENDC} (Vector search enabled)")
        print(f"• Redis Cache: {Colors.GREEN}Operational{Colors.ENDC} (Hit rate: 92%)")
        print(f"• ScyllaDB: {Colors.GREEN}Stable{Colors.ENDC} (Conversation history)")
        
        self.pause_for_user()
    
    async def _quality_assurance_dashboard(self):
        """Show quality assurance metrics"""
        if not self.require_permission("full_admin", "quality assurance dashboard"):
            return
        
        self.print_header("QUALITY ASSURANCE DASHBOARD", "Continuous Quality Monitoring")
        
        print(f"{Colors.BOLD}Conversation Quality Metrics - August 2025:{Colors.ENDC}")
        print()
        print(f"• Response Relevance: {Colors.GREEN}4.3/5.0{Colors.ENDC} (User ratings)")
        print(f"• Emotional Accuracy: {Colors.GREEN}89% correct emotion detection{Colors.ENDC}")
        print(f"• Intervention Success: {Colors.GREEN}76% users report improvement{Colors.ENDC}")
        print(f"• Safety Appropriateness: {Colors.GREEN}100% medical advice avoidance{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Technical Performance:{Colors.ENDC}")
        print(f"• System Uptime: {Colors.GREEN}99.94%{Colors.ENDC} (Target: 99.9%)")
        print(f"• Response Latency: {Colors.GREEN}347ms average{Colors.ENDC} (Target: <500ms)")
        print(f"• Error Rate: {Colors.GREEN}0.03%{Colors.ENDC} (Target: <0.1%)")
        print(f"• Data Synchronization: {Colors.GREEN}99.97% success rate{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Safety & Compliance:{Colors.ENDC}")
        print(f"• Crisis Detection Accuracy: {Colors.GREEN}100%{Colors.ENDC} (No false negatives)")
        print(f"• Escalation Response Time: {Colors.GREEN}3.2 minutes average{Colors.ENDC} (Target: <5)")
        print(f"• HIPAA Compliance: {Colors.GREEN}100% audit score{Colors.ENDC}")
        print(f"• Data Privacy: {Colors.GREEN}Zero breaches, 100% consent compliance{Colors.ENDC}")
        
        self.pause_for_user()
    
    async def crisis_management_demo(self):
        """Demonstrate crisis detection and response"""
        # Crisis management is available to residents (for their own crises), staff, and admins
        if not (self.check_permission("chat") or self.check_permission("crisis_response") or self.check_permission("full_admin")):
            self.require_permission("crisis_response", "crisis management demonstration")
            return
        
        self.print_header("CRISIS MANAGEMENT DEMONSTRATION", "Safety-first response system")
        
        print(f"{Colors.RED}{Colors.BOLD}⚠️  CRISIS SIMULATION WARNING ⚠️{Colors.ENDC}")
        print(f"This demonstration shows how the system handles mental health crises.")
        print(f"All scenarios are simulated for educational purposes only.")
        print()
        
        if not self.current_user or self.current_user.role != UserRole.RESIDENT:
            print(f"{Colors.YELLOW}Switching to resident view for crisis simulation...{Colors.ENDC}")
            self.current_user = self.demo_users["resident_sarah"]
        
        self.print_menu(
            "Crisis Scenario to Demonstrate:",
            [
                "🟡 Low Risk: General sadness/loneliness",
                "🟠 Medium Risk: Persistent negative thoughts",
                "🔴 High Risk: Suicidal ideation (emergency response)",
                "🚑 Medical Emergency: Chest pain/breathing difficulty"
            ]
        )
        
        choice = self.get_user_choice(4)
        if choice == 0:
            return
        
        scenarios = [
            ("low", "I'm feeling really sad today and lonely"),
            ("medium", "I've been having dark thoughts and don't want to be a burden"),
            ("high", "I don't think I want to be here anymore"),
            ("medical", "I'm having chest pain and can't catch my breath")
        ]
        
        risk_level, trigger_message = scenarios[choice - 1]
        await self._simulate_crisis_response(risk_level, trigger_message)
    
    async def _simulate_crisis_response(self, risk_level: str, trigger_message: str):
        """Simulate crisis detection and response"""
        print(f"\n{Colors.CYAN}🗣️  User Message: \"{trigger_message}\"{Colors.ENDC}")
        
        # Show AI analysis
        print(f"\n{Colors.YELLOW}🧠 Crisis Detection Analysis:{Colors.ENDC}")
        await asyncio.sleep(1)
        print(f"• Keyword Analysis: {Colors.RED}Crisis indicators detected{Colors.ENDC}")
        print(f"• Emotional Pattern: {Colors.RED}High negative valence + elevated arousal{Colors.ENDC}")
        print(f"• Risk Classification: {Colors.RED}{risk_level.upper()} RISK{Colors.ENDC}")
        
        await asyncio.sleep(2)
        
        if risk_level == "low":
            print(f"\n{Colors.BLUE}🐱 Lilo Response:{Colors.ENDC}")
            print(f"\"I hear that you're feeling sad and lonely today. Those feelings are")
            print(f"completely valid and I'm here to support you through this.\"")
            print()
            print(f"System Actions:")
            print(f"✓ Gentle intervention offered")
            print(f"✓ Care team notified (low priority)")
            print(f"✓ Family informed via weekly summary")
            
        elif risk_level == "medium":
            print(f"\n{Colors.YELLOW}🚨 MEDIUM RISK PROTOCOL ACTIVATED{Colors.ENDC}")
            print(f"\n{Colors.BLUE}🐱 Lilo Response:{Colors.ENDC}")
            print(f"\"I'm concerned about what you've shared with me. Your feelings matter")
            print(f"and you don't have to carry this burden alone. Let me connect you with")
            print(f"someone who can provide additional support.\"")
            print()
            print(f"System Actions:")
            print(f"✓ Care manager notified immediately")
            print(f"✓ Follow-up call scheduled within 2 hours")
            print(f"✓ Intervention resources offered")
            print(f"✓ Family contact considered (with consent)")
            
        elif risk_level == "high":
            print(f"\n{Colors.RED}🚨 HIGH RISK - EMERGENCY PROTOCOL ACTIVATED{Colors.ENDC}")
            print(f"\n{Colors.BLUE}🐱 Lilo Response:{Colors.ENDC}")
            print(f"\"I'm very concerned about what you've shared with me. Your life has")
            print(f"value and I want to make sure you get help right away. I'm connecting")
            print(f"you with Maria, your care manager, who will reach out within minutes.\"")
            print()
            print(f"{Colors.RED}IMMEDIATE SYSTEM ACTIONS:{Colors.ENDC}")
            print(f"✓ Care manager phone alert (2 minutes)")
            print(f"✓ Crisis counselor notification")
            print(f"✓ Emergency contacts notified")
            print(f"✓ 988 Lifeline information provided")
            print(f"✓ Human oversight until resolution")
            
        elif risk_level == "medical":
            print(f"\n{Colors.RED}🚨 MEDICAL EMERGENCY DETECTED{Colors.ENDC}")
            print(f"\n{Colors.BLUE}🐱 Lilo Response:{Colors.ENDC}")
            print(f"\"This sounds like it could be a medical emergency. I'm alerting")
            print(f"your care team immediately. If you feel this is life-threatening,")
            print(f"please call 911 right now or press your emergency call button.\"")
            print()
            print(f"{Colors.RED}IMMEDIATE SYSTEM ACTIONS:{Colors.ENDC}")
            print(f"✓ Nursing staff alerted (immediate)")
            print(f"✓ Medical emergency protocol activated")
            print(f"✓ Family notified (emergency override)")
            print(f"✓ Facility emergency response team dispatched")
            print(f"✓ EMS coordination if needed")
        
        print(f"\n{Colors.GREEN}✓ All crisis protocols executed successfully{Colors.ENDC}")
        print(f"✓ Complete audit trail maintained for compliance")
        
        self.pause_for_user()
    
    async def administrative_features_demo(self):
        """Show administrative capabilities"""
        if not self.require_permission("full_admin", "administrative features"):
            return
        
        self.print_header("ADMINISTRATIVE FEATURES", "System management and compliance oversight")
        
        self.print_menu(
            "Administrative Functions:",
            [
                "👥 User Management & Onboarding",
                "🔐 Privacy & Consent Management",
                "📋 HIPAA Compliance Monitoring",
                "📊 Analytics & Reporting System",
                "⚙️  System Configuration",
                "🔧 Technical Health Monitoring"
            ]
        )
        
        choice = self.get_user_choice(6)
        if choice == 0:
            return
        
        admin_functions = [
            self._user_management_demo,
            self._privacy_consent_demo, 
            self._hipaa_monitoring_demo,
            self._analytics_reporting_demo,
            self._system_configuration_demo,
            self._technical_health_demo
        ]
        
        await admin_functions[choice - 1]()
    
    async def _user_management_demo(self):
        """Show user management interface"""
        if not self.require_permission("user_management", "user management functions"):
            return
        
        self.print_header("USER MANAGEMENT SYSTEM", "Onboarding and account administration")
        
        print(f"{Colors.BOLD}Organization: Caring Hearts Senior Living{Colors.ENDC}")
        print(f"Active Users: 156 residents, 23 staff members")
        print(f"System Status: All services operational")
        print()
        
        print(f"{Colors.BOLD}Recent Activity:{Colors.ENDC}")
        print(f"• 3 new residents onboarded this week")
        print(f"• 2 family members granted portal access")
        print(f"• 1 staff member completed safety training")
        print(f"• 15 users updated communication preferences")
        print()
        
        self.print_menu(
            "User Management Actions:",
            [
                "➕ Add New Resident",
                "📥 Import from Care System",
                "📝 Bulk User Updates",
                "👁️  View Individual User Profile",
                "🔑 Reset User Password",
                "📊 User Engagement Report"
            ]
        )
        
        mgmt_choice = self.get_user_choice(6)
        if mgmt_choice == 4:
            await self._show_individual_user_profile()
    
    async def _show_individual_user_profile(self):
        """Show detailed user profile management"""
        if not self.require_permission("user_management", "viewing user profiles"):
            return
        
        print(f"\n{Colors.CYAN}👤 Individual User Profile{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}User: Margaret S. (ID: usr_456){Colors.ENDC}")
        print(f"Status: Active | Last Active: 2 hours ago")
        print(f"Role: Resident | Care Level: Independent Living")
        print()
        
        print(f"{Colors.BOLD}Account Settings:{Colors.ENDC}")
        print(f"✓ Email: margaret.s@email.com (verified)")
        print(f"✓ Phone: (555) 123-4567 (verified)")
        print(f"✓ Emergency Contact: Daughter - Jennifer S.")
        print(f"✓ Communication Preferences: Text + Voice")
        print(f"✓ Privacy Settings: Family summaries enabled")
        print()
        
        print(f"{Colors.BOLD}Care Team Access:{Colors.ENDC}")
        print(f"• Primary Care Manager: Sarah Johnson, RN")
        print(f"• Family Portal Access: Jennifer S. (daughter)")
        print(f"• Backup Emergency Contact: Dr. Michael Chen")
        
        self.pause_for_user()
    
    async def _privacy_consent_demo(self):
        """Show privacy and consent management"""
        self.print_header("PRIVACY & CONSENT MANAGEMENT", "HIPAA-compliant privacy controls")
        
        print(f"{Colors.BOLD}Privacy & Consent Center - Margaret S.{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}Current Consent Status:{Colors.ENDC}")
        print(f"✓ Basic Chat Functionality (Required)")
        print(f"✓ Emotional Memory Storage (30 days TTL)")
        print(f"✓ Care Team Data Sharing (Enabled)")
        print(f"✓ Family Summary Reports (Enabled)")
        print(f"✓ Anonymous Analytics Participation (Enabled)")
        print(f"⚠ Voice Recording Storage (Disabled - User Choice)")
        print(f"⚠ Research Data Sharing (Disabled - User Choice)")
        print()
        
        print(f"{Colors.BOLD}Data Retention Settings:{Colors.ENDC}")
        print(f"• Conversation History: 7 years (Healthcare requirement)")
        print(f"• Personal Emotional Data: 30 days (User-controlled TTL)")
        print(f"• Medical Context: Per care plan (Provider-controlled)")
        print(f"• Family Communications: 1 year (User-controlled)")
        
        self.pause_for_user()
    
    async def _hipaa_monitoring_demo(self):
        """Show HIPAA compliance monitoring"""
        self.print_header("HIPAA COMPLIANCE MONITORING", "Regulatory compliance dashboard")
        
        print(f"{Colors.BOLD}Compliance Dashboard - Caring Hearts Senior Living{Colors.ENDC}")
        print(f"Last Audit: June 2025 | Next Review: December 2025")
        print()
        
        print(f"{Colors.BOLD}Technical Safeguards Status:{Colors.ENDC}")
        print(f"✓ Access Control: Unique user IDs, automatic logoff")
        print(f"✓ Audit Controls: Complete logging, tamper protection")
        print(f"✓ Integrity Controls: Electronic signatures, version control")
        print(f"✓ Person/Entity Authentication: Multi-factor authentication")
        print(f"✓ Transmission Security: End-to-end encryption")
        print()
        
        print(f"{Colors.BOLD}Recent Audit Events - Last 24 Hours:{Colors.ENDC}")
        print(f"Total Events: 2,847 | Flagged for Review: 3")
        print()
        print(f"High Priority Events:")
        print(f"• Margaret S. requested data export (Approved - Normal)")
        print(f"• System detected unusual login pattern for User #234 (Investigating)")
        print(f"• Failed authentication attempts from IP 192.168.1.100 (Blocked)")
        
        self.pause_for_user()
    
    async def _analytics_reporting_demo(self):
        """Show analytics and reporting capabilities"""
        self.print_header("ANALYTICS & REPORTING SYSTEM", "Evidence-based outcome measurement")
        
        print(f"{Colors.BOLD}Monthly Quality Report - MultiDB Chatbot{Colors.ENDC}")
        print(f"Organization: Sunset Manor Senior Living")
        print(f"Reporting Period: August 2025")
        print()
        
        print(f"{Colors.BOLD}Safety Metrics:{Colors.ENDC}")
        print(f"✓ Zero unhandled crisis events")
        print(f"✓ 100% escalations within SLA (avg 3.2 minutes)")
        print(f"✓ 12 proactive interventions prevented escalation")
        print(f"✓ 0 adverse events related to system use")
        print()
        
        print(f"{Colors.BOLD}Effectiveness Metrics:{Colors.ENDC}")
        print(f"✓ 89% users report improved emotional wellness")
        print(f"✓ 2.3-point average UCLA-3 improvement")
        print(f"✓ 76% intervention completion rate")
        print(f"✓ 4.2/5.0 average user satisfaction")
        
        self.pause_for_user()
    
    async def _system_configuration_demo(self):
        """Show system configuration options"""
        self.print_header("SYSTEM CONFIGURATION", "Customize deployment for your organization")
        
        print(f"{Colors.BOLD}Current Configuration - Sunrise Senior Living:{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}AI Model Settings:{Colors.ENDC}")
        print(f"• Embedding Model: sentence-transformers/all-mpnet-base-v2")
        print(f"• Generation Model: Qwen 1.7B (Optimized for healthcare)")
        print(f"• Crisis Detection: Multi-layer safety monitoring enabled")
        print(f"• Response Temperature: 0.7 (balanced creativity/safety)")
        print()
        
        print(f"{Colors.BOLD}Database Configuration:{Colors.ENDC}")
        print(f"• PostgreSQL: 5 schemas (auth, compliance, app, memory, knowledge)")
        print(f"• MongoDB Atlas: Vector search enabled")
        print(f"• Redis: Session management + caching")
        print(f"• ScyllaDB: Conversation history + analytics")
        print()
        
        print(f"{Colors.BOLD}HIPAA Settings:{Colors.ENDC}")
        print(f"• Audit Level: Strict (all actions logged)")
        print(f"• Data Retention: 7 years (healthcare standard)")
        print(f"• Encryption: AES-256 at rest, TLS 1.3 in transit")
        print(f"• Access Controls: Role-based with MFA")
        
        self.pause_for_user()
    
    async def _technical_health_demo(self):
        """Show technical health monitoring"""
        self.print_header("TECHNICAL HEALTH MONITORING", "Real-time system performance")
        
        print(f"{Colors.BOLD}Service Health Check (Live):{Colors.ENDC}")
        print()
        
        services = [
            ("API Gateway", "8000", "healthy", "347ms avg response"),
            ("Search Service", "8001", "healthy", "RAG pipeline operational"),
            ("Embedding Service", "8002", "healthy", "BGE model loaded"),
            ("Generation Service", "8003", "healthy", "Qwen 1.7B active"),
            ("Content Safety", "8007", "healthy", "HIPAA validation active")
        ]
        
        for service, port, status, detail in services:
            status_color = Colors.GREEN if status == "healthy" else Colors.RED
            print(f"• {service} (:{port}): {status_color}{status.upper()}{Colors.ENDC} - {detail}")
        
        print()
        print(f"{Colors.BOLD}Database Connections:{Colors.ENDC}")
        dbs = [
            ("PostgreSQL", "healthy", "5 schemas active"),
            ("MongoDB Atlas", "healthy", "Vector search enabled"),
            ("Redis", "healthy", "92% cache hit rate"),
            ("ScyllaDB", "healthy", "Conversation history active")
        ]
        
        for db, status, detail in dbs:
            status_color = Colors.GREEN if status == "healthy" else Colors.RED
            print(f"• {db}: {status_color}{status.upper()}{Colors.ENDC} - {detail}")
        
        self.pause_for_user()
    
    async def integration_demo(self):
        """Show system integration capabilities"""
        # Integration demos are primarily for staff, managers, and admins
        if not (self.check_permission("view_resident_status") or self.check_permission("member_analytics") or self.check_permission("full_admin")):
            self.require_permission("view_resident_status", "integration demonstrations")
            return
        
        self.print_header("INTEGRATION & API DEMONSTRATIONS", "Healthcare system connectivity")
        
        self.print_menu(
            "Integration Examples:",
            [
                "🏥 Electronic Health Record (EHR) Integration",
                "📋 Care Management System Connection",
                "👨‍👩‍👧‍👦 Family Communication Hub",
                "📊 Business Intelligence Integration",
                "🔗 API Usage Examples"
            ]
        )
        
        choice = self.get_user_choice(5)
        if choice == 0:
            return
        
        integration_functions = [
            self._ehr_integration_demo,
            self._care_management_integration,
            self._family_communication_demo,
            self._bi_integration_demo,
            self._api_usage_demo
        ]
        
        await integration_functions[choice - 1]()
    
    async def _ehr_integration_demo(self):
        """Show EHR integration"""
        self.print_header("EHR INTEGRATION", "Epic MyChart Connection Example")
        
        print(f"{Colors.BOLD}EHR Integration Status - Epic MyChart Connection{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}Connected Services:{Colors.ENDC}")
        print(f"✓ Medication List (Last Sync: 2 hours ago)")
        print(f"✓ Appointment Schedule (Last Sync: 1 hour ago)")
        print(f"✓ Care Team Directory (Last Sync: Daily)")
        print(f"✓ Allergy Information (Last Sync: Daily)")
        print(f"⚠ Lab Results (Pending Provider Approval)")
        print()
        
        print(f"{Colors.BOLD}Recent Sync Events:{Colors.ENDC}")
        print(f"• New prescription added: Lisinopril 10mg daily")
        print(f"• Appointment scheduled: Cardiology follow-up Sept 15")
        print(f"• Care team update: New physical therapist assigned")
        print(f"• Medication reminder preferences updated")
        print()
        
        print(f"{Colors.BOLD}Data Sharing Permissions:{Colors.ENDC}")
        print(f"• Lilo → EHR: Wellness assessments, safety events")
        print(f"• EHR → Lilo: Medications, appointments, care notes")
        print(f"• Emergency Override: Full access during crisis escalation")
        
        self.pause_for_user()
    
    async def _care_management_integration(self):
        """Show care management system integration"""
        self.print_header("CARE MANAGEMENT INTEGRATION", "Workflow integration for providers")
        
        print(f"{Colors.BOLD}Integrated Care Manager Dashboard{Colors.ENDC}")
        print()
        print(f"Member: Robert K. | High Loneliness Risk | Case Priority: Medium")
        print()
        
        print(f"{Colors.BOLD}Lilo Insights (This Week):{Colors.ENDC}")
        print(f"• Engagement: 34 minutes (↑ from 18 minutes last week)")
        print(f"• Mood Trend: Improving (3 positive days, 1 challenging day)")
        print(f"• Interventions: 2 breathing exercises, 1 social call completed")
        print(f"• Alerts: Expressed financial anxiety Wednesday")
        print()
        
        print(f"{Colors.BOLD}Recommended Actions:{Colors.ENDC}")
        print(f"1. Schedule financial counselor consultation")
        print(f"2. Continue current emotional support interventions")
        print(f"3. Explore community resource referrals")
        print(f"4. Follow up on daughter's visit schedule")
        
        self.pause_for_user()
    
    async def _family_communication_demo(self):
        """Show family communication hub"""
        self.print_header("FAMILY COMMUNICATION HUB", "Multi-channel family engagement")
        
        print(f"{Colors.BOLD}Family Portal - Jennifer S. (Margaret's Daughter){Colors.ENDC}")
        print()
        print(f"{Colors.GREEN}Mom is doing well this week! 😊{Colors.ENDC}")
        print(f"Engagement: 42 minutes | Mood: Generally positive | Safety: No concerns")
        print()
        
        print(f"{Colors.BOLD}Communication Preferences:{Colors.ENDC}")
        print(f"✓ Weekly summary emails (Fridays)")
        print(f"✓ Emergency alerts (Immediate)")
        print(f"✓ Positive milestone notifications (As they happen)")
        print(f"⚠ Daily updates (Disabled to avoid overwhelm)")
        print()
        
        print(f"{Colors.BOLD}Available Actions:{Colors.ENDC}")
        print(f"[Schedule Family Call] [Send Message to Mom] [Update Contact Info]")
        
        self.pause_for_user()
    
    async def _bi_integration_demo(self):
        """Show business intelligence integration"""
        self.print_header("BUSINESS INTELLIGENCE INTEGRATION", "Analytics system connectivity")
        
        print(f"{Colors.BOLD}Power BI Dashboard Integration{Colors.ENDC}")
        print()
        print(f"📊 Real-time data feeds from Lilo to organizational BI systems:")
        print()
        print(f"• Resident engagement metrics (anonymized)")
        print(f"• Intervention effectiveness data")
        print(f"• Safety event statistics")
        print(f"• Family satisfaction trends")
        print(f"• Staff efficiency improvements")
        print()
        print(f"{Colors.GREEN}✓ All data exported with privacy protections{Colors.ENDC}")
        print(f"✓ Automated report generation for leadership")
        print(f"✓ Trend analysis and predictive insights")
        
        self.pause_for_user()
    
    async def _api_usage_demo(self):
        """Show API usage examples"""
        self.print_header("API USAGE EXAMPLES", "Integration endpoints for developers")
        
        print(f"{Colors.BOLD}Available API Endpoints:{Colors.ENDC}")
        print()
        print(f"{Colors.CYAN}Authentication:{Colors.ENDC}")
        print(f"POST /auth/login - User authentication")
        print(f"GET /auth/profile - Get user profile")
        print()
        print(f"{Colors.CYAN}Chat & Messaging:{Colors.ENDC}")
        print(f"POST /api/v1/chat/message - Send chat message with AI response")
        print(f"GET /api/v1/chat/history - Retrieve conversation history")
        print(f"POST /api/v1/chat/feedback - Submit feedback on AI responses")
        print()
        print(f"{Colors.CYAN}Search & Knowledge:{Colors.ENDC}")
        print(f"POST /api/v1/search/semantic - Perform semantic/hybrid search")
        print(f"GET /api/v1/search/suggestions - Get autocomplete suggestions")
        print()
        print(f"{Colors.CYAN}Health & Admin:{Colors.ENDC}")
        print(f"GET /health - Basic system health check")
        print(f"GET /health/detailed - Comprehensive health status")
        print(f"POST /admin/seed-enhanced - Trigger data seeding")
        
        self.pause_for_user()
    
    async def mobile_accessibility_demo(self):
        """Show mobile and accessibility features"""
        # Mobile and accessibility features are available to all authenticated users
        if not self.current_user:
            print(f"{Colors.RED}Please select a user first (Option 1 from main menu){Colors.ENDC}")
            self.pause_for_user()
            return
        
        self.print_header("MOBILE & ACCESSIBILITY FEATURES", "Inclusive design for all users")
        
        print(f"{Colors.BOLD}Mobile Interface Preview:{Colors.ENDC}")
        print()
        print("┌─────────────────────────┐")
        print("│    🏥 Lilo Companion    │  ← Large, clear branding")
        print("├─────────────────────────┤")
        print("│                         │")
        print("│  👋 Good morning!       │  ← Large fonts (18pt minimum)")
        print("│                         │")
        print("│  How are you feeling    │  ← High contrast colors")
        print("│  today?                 │")
        print("│                         │")
        print("│  [😊] [😐] [😢] [😰]      │  ← Emoji quick responses")
        print("│                         │")
        print("├─────────────────────────┤")
        print("│  [🎤 Voice] [✏️ Type]     │  ← Voice-first design")
        print("└─────────────────────────┘")
        print("│  [🆘 Emergency Help]     │  ← Always-visible emergency")
        print("└─────────────────────────┘")
        print()
        
        print(f"{Colors.BOLD}Accessibility Features:{Colors.ENDC}")
        print(f"✓ WCAG 2.1 AA Compliance")
        print(f"✓ High contrast mode (4.5:1 minimum ratio)")
        print(f"✓ Large text options (up to 200% scaling)")
        print(f"✓ Voice control support")
        print(f"✓ Screen reader compatibility")
        print(f"✓ Simple gesture alternatives")
        
        self.pause_for_user()
    
    async def hipaa_compliance_demo(self):
        """Show HIPAA compliance overview"""
        # HIPAA compliance overview is available to staff, managers, and admins
        if not (self.check_permission("view_resident_status") or self.check_permission("member_analytics") or self.check_permission("full_admin") or self.check_permission("compliance_oversight")):
            self.require_permission("view_resident_status", "HIPAA compliance overview")
            return
        
        self.print_header("HIPAA COMPLIANCE OVERVIEW", "Healthcare privacy and security")
        
        print(f"{Colors.BOLD}HIPAA Safeguards Implementation:{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}Administrative Safeguards:{Colors.ENDC}")
        print(f"✓ Security Officer: John Smith, HIPAA Officer")
        print(f"✓ Workforce Training: 100% completion rate")
        print(f"✓ Information Access Management: Role-based permissions")
        print(f"✓ Security Awareness: Monthly updates, incident protocols")
        print(f"✓ Contingency Plan: Disaster recovery tested quarterly")
        print()
        
        print(f"{Colors.BOLD}Physical Safeguards:{Colors.ENDC}")
        print(f"✓ Facility Access Controls: Secure server environment")
        print(f"✓ Workstation Use: Compliant devices only")
        print(f"✓ Device Controls: Encrypted storage, remote wipe capability")
        print()
        
        print(f"{Colors.BOLD}Technical Safeguards:{Colors.ENDC}")
        print(f"✓ Access Control: Unique user IDs, automatic logoff")
        print(f"✓ Audit Controls: Complete logging, tamper protection")
        print(f"✓ Integrity Controls: Electronic signatures, version control")
        print(f"✓ Transmission Security: End-to-end encryption")
        
        self.pause_for_user()
    
    async def quality_metrics_demo(self):
        """Show quality metrics and KPIs"""
        # Quality metrics are available to managers and admins
        if not (self.check_permission("member_analytics") or self.check_permission("full_admin") or self.check_permission("compliance_oversight")):
            self.require_permission("member_analytics", "quality metrics and reporting")
            return
        
        self.print_header("QUALITY METRICS & REPORTING", "Evidence-based performance measurement")
        
        print(f"{Colors.BOLD}Core Quality Indicators:{Colors.ENDC}")
        print()
        
        print(f"{Colors.BOLD}1. Engagement Quality:{Colors.ENDC}")
        print(f"• Conversation minutes per week: {Colors.GREEN}31 avg{Colors.ENDC} (target: ≥25)")
        print(f"• User-initiated conversations: {Colors.GREEN}68%{Colors.ENDC} (higher = better)")
        print(f"• Response relevance ratings: {Colors.GREEN}4.3/5.0{Colors.ENDC}")
        print(f"• Feature utilization rates: {Colors.GREEN}76%{Colors.ENDC} try interventions")
        print()
        
        print(f"{Colors.BOLD}2. Clinical Effectiveness:{Colors.ENDC}")
        print(f"• UCLA-3 Loneliness improvements: {Colors.GREEN}2.1 points avg{Colors.ENDC}")
        print(f"• Emotional regulation success: {Colors.GREEN}89%{Colors.ENDC} arousal reduction")
        print(f"• Intervention completion rates: {Colors.GREEN}76%{Colors.ENDC}")
        print(f"• Self-reported wellness: {Colors.GREEN}89%{Colors.ENDC} report improvement")
        print()
        
        print(f"{Colors.BOLD}3. Safety Performance:{Colors.ENDC}")
        print(f"• Crisis detection accuracy: {Colors.GREEN}100%{Colors.ENDC} (no false negatives)")
        print(f"• Escalation response times: {Colors.GREEN}3.2 min avg{Colors.ENDC} (target: <5)")
        print(f"• Adverse event prevention: {Colors.GREEN}100%{Colors.ENDC}")
        print(f"• Safety protocol compliance: {Colors.GREEN}100%{Colors.ENDC}")
        
        self.pause_for_user()
    
    async def end_to_end_journey(self):
        """Complete end-to-end user journey demonstration"""
        # End-to-end journey is available to staff, managers, and admins (for training/education)
        if not (self.check_permission("view_resident_status") or self.check_permission("member_analytics") or self.check_permission("full_admin")):
            self.require_permission("view_resident_status", "end-to-end user journey demonstration")
            return
        
        self.print_header("COMPLETE END-TO-END USER JOURNEY", "Full experience walkthrough")
        
        print(f"{Colors.BOLD}This demonstration will walk through a complete user journey{Colors.ENDC}")
        print(f"from initial onboarding through ongoing care coordination.")
        print()
        
        journey_steps = [
            "👤 New Resident Onboarding",
            "🏠 First Conversation with Lilo",
            "😰 Emotional Challenge & AI Response", 
            "🆘 Crisis Detection & Staff Intervention",
            "👨‍👩‍👧‍👦 Family Communication & Updates",
            "📊 Care Team Review & Plan Updates",
            "📈 Outcome Measurement & Reporting"
        ]
        
        self.print_menu("Journey Steps:", journey_steps, allow_back=False)
        
        print(f"\n{Colors.YELLOW}Would you like to walk through all steps automatically?{Colors.ENDC}")
        print(f"1. Yes - Full walkthrough (10 minutes)")
        print(f"2. No - Select specific step")
        print(f"0. Back to main menu")
        
        choice = self.get_user_choice(2)
        
        if choice == 1:
            await self._full_journey_walkthrough()
        elif choice == 2:
            step_choice = self.get_user_choice(len(journey_steps))
            if step_choice > 0:
                await self._individual_journey_step(step_choice - 1)
    
    async def _full_journey_walkthrough(self):
        """Complete journey walkthrough"""
        steps = [
            ("New Resident Onboarding", self._onboarding_step),
            ("First Lilo Conversation", self._first_conversation_step),
            ("Emotional Challenge", self._emotional_challenge_step),
            ("Crisis Detection", self._crisis_detection_step),
            ("Family Communication", self._family_update_step),
            ("Care Team Review", self._care_review_step),
            ("Outcome Measurement", self._outcome_measurement_step)
        ]
        
        for i, (step_name, step_function) in enumerate(steps, 1):
            self.print_header(f"STEP {i}/7: {step_name.upper()}", "Complete user journey demonstration")
            await step_function()
            
            if i < len(steps):
                print(f"\n{Colors.CYAN}Proceeding to next step...{Colors.ENDC}")
                await asyncio.sleep(2)
    
    async def _onboarding_step(self):
        """Simulate resident onboarding"""
        print(f"{Colors.BOLD}New Resident: Margaret S. moving to Sunrise Senior Living{Colors.ENDC}")
        print()
        print(f"1. {Colors.GREEN}✓{Colors.ENDC} Administrator creates account")
        print(f"2. {Colors.GREEN}✓{Colors.ENDC} Medical information imported from EHR")
        print(f"3. {Colors.GREEN}✓{Colors.ENDC} Family portal access granted to daughter")
        print(f"4. {Colors.GREEN}✓{Colors.ENDC} Emergency contacts configured")
        print(f"5. {Colors.GREEN}✓{Colors.ENDC} HIPAA consent completed")
        print(f"6. {Colors.GREEN}✓{Colors.ENDC} Baseline wellness assessment scheduled")
        print()
        print(f"{Colors.GREEN}Onboarding completed in 8 minutes{Colors.ENDC}")
        
        self.pause_for_user()
    
    async def _first_conversation_step(self):
        """Simulate first conversation"""
        print(f"{Colors.BOLD}Margaret's First Conversation with Lilo{Colors.ENDC}")
        print()
        print(f"{Colors.BLUE}🐱 Lilo: Hello Margaret! I'm Lilo, your AI wellness companion.{Colors.ENDC}")
        print(f"I'm here to support you as you settle into your new home.")
        print()
        print(f"{Colors.CYAN}Margaret: Hello... I'm still getting used to everything here.{Colors.ENDC}")
        print()
        print(f"{Colors.BLUE}🐱 Lilo: That's completely understandable. Moving to a new place{Colors.ENDC}")
        print(f"is a big change, even when it's a positive one. How are you feeling about it?")
        print()
        print(f"{Colors.CYAN}Margaret: A bit overwhelmed, but the staff seems nice.{Colors.ENDC}")
        print()
        print(f"{Colors.GREEN}✓ Emotional baseline established{Colors.ENDC}")
        print(f"✓ Trust-building conversation successful")
        print(f"✓ Care plan insights generated")
        
        self.pause_for_user()
    
    async def _emotional_challenge_step(self):
        """Simulate emotional challenge response"""
        print(f"{Colors.BOLD}Week 3: Margaret Experiences Emotional Challenge{Colors.ENDC}")
        print()
        print(f"{Colors.CYAN}Margaret: I'm really missing my old home today. Everything feels different.{Colors.ENDC}")
        print()
        print(f"{Colors.YELLOW}🧠 AI Analysis: Grief/adjustment (-0.6 valence, 0.5 arousal){Colors.ENDC}")
        print()
        print(f"{Colors.BLUE}🐱 Lilo: I can hear how much your old home meant to you.{Colors.ENDC}")
        print(f"It's natural to feel sad about leaving a place full of memories.")
        print(f"Would you like to tell me about a favorite memory from your old home?")
        print()
        print(f"{Colors.GREEN}✓ Empathetic response provided{Colors.ENDC}")
        print(f"✓ Memory-sharing intervention offered")
        print(f"✓ Emotional support successful")
        
        self.pause_for_user()
    
    async def _crisis_detection_step(self):
        """Simulate crisis detection"""
        print(f"{Colors.BOLD}Month 2: Crisis Detection & Response{Colors.ENDC}")
        print()
        print(f"{Colors.CYAN}Margaret: I don't think I belong anywhere anymore...{Colors.ENDC}")
        print()
        print(f"{Colors.RED}🚨 CRISIS DETECTED - Medium Risk Level{Colors.ENDC}")
        print(f"Keywords: existential despair, belonging")
        print(f"Pattern: Sustained negative mood")
        print()
        print(f"{Colors.BLUE}🐱 Lilo: Margaret, I'm concerned about what you've shared.{Colors.ENDC}")
        print(f"Your feelings matter, and I want to make sure you get support.")
        print(f"I'm connecting you with Maria, your care manager.")
        print()
        print(f"{Colors.GREEN}✓ Care staff notified in 2.1 minutes{Colors.ENDC}")
        print(f"✓ Human intervention successful")
        print(f"✓ Crisis resolved with counseling referral")
        
        self.pause_for_user()
    
    async def _family_update_step(self):
        """Simulate family communication"""
        print(f"{Colors.BOLD}Family Communication & Updates{Colors.ENDC}")
        print()
        print(f"{Colors.BLUE}📧 Automated Weekly Summary to Jennifer:{Colors.ENDC}")
        print()
        print(f"\"Your mother Margaret had a challenging but ultimately positive week.")
        print(f"She worked through some difficult emotions about her transition with")
        print(f"the help of our care team. She's shown great resilience and is")
        print(f"engaging more with other residents.\"")
        print()
        print(f"{Colors.GREEN}✓ Family informed with appropriate privacy protection{Colors.ENDC}")
        print(f"✓ Positive developments highlighted")
        print(f"✓ Care team coordination transparent")
        
        self.pause_for_user()
    
    async def _care_review_step(self):
        """Simulate care team review"""
        print(f"{Colors.BOLD}Care Team Review & Plan Updates{Colors.ENDC}")
        print()
        print(f"{Colors.BLUE}👩‍⚕️ Care Manager Maria's Review:{Colors.ENDC}")
        print()
        print(f"Lilo Insights for Margaret S.:")
        print(f"• Adjustment period: Longer than typical (8 weeks vs 4-6)")
        print(f"• Emotional pattern: Grief processing with positive trajectory")
        print(f"• Intervention response: Excellent (90% completion rate)")
        print(f"• Social engagement: Improving (isolated → participating)")
        print()
        print(f"{Colors.BOLD}Care Plan Updates:{Colors.ENDC}")
        print(f"1. Continue grief counseling sessions")
        print(f"2. Increase social activity encouragement")
        print(f"3. Family visit coordination")
        print(f"4. Transition support group referral")
        print()
        print(f"{Colors.GREEN}✓ Care plan updated with AI insights{Colors.ENDC}")
        
        self.pause_for_user()
    
    async def _outcome_measurement_step(self):
        """Simulate outcome measurement"""
        self.print_header("OUTCOME MEASUREMENT", "Evidence-based results tracking")
        
        print(f"{Colors.BOLD}Margaret's 90-Day Outcome Report{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}Quantitative Improvements:{Colors.ENDC}")
        print(f"• UCLA-3 Loneliness Score: {Colors.GREEN}8.1 → 5.4{Colors.ENDC} (2.7 point improvement)")
        print(f"• Weekly Engagement: {Colors.GREEN}12 → 38 minutes{Colors.ENDC}")
        print(f"• Social Connections: {Colors.GREEN}0 → 4 regular contacts{Colors.ENDC}")
        print(f"• Crisis Events: {Colors.GREEN}1 → 0{Colors.ENDC} (successfully resolved)")
        print()
        
        print(f"{Colors.BOLD}Qualitative Outcomes:{Colors.ENDC}")
        print(f"• Margaret reports feeling \"more at home\" at the facility")
        print(f"• Family satisfaction improved from 3.2 → 4.7/5.0")
        print(f"• Staff notes significant improvement in mood and participation")
        print(f"• No medication changes needed (emotional stability maintained)")
        print()
        
        print(f"{Colors.GREEN}✓ Successful transition and ongoing wellness achieved{Colors.ENDC}")
        print(f"✓ Evidence-based care model validated")
        print(f"✓ Family and resident satisfaction high")
        
        self.pause_for_user()
    
    async def _individual_journey_step(self, step_index: int):
        """Run individual journey step"""
        step_functions = [
            self._onboarding_step,
            self._first_conversation_step,
            self._emotional_challenge_step,
            self._crisis_detection_step,
            self._family_update_step,
            self._care_review_step,
            self._outcome_measurement_step
        ]
        
        await step_functions[step_index]()
    
    def show_demo_summary(self):
        """Show demo session summary"""
        self.print_header("DEMO SESSION SUMMARY", "Thank you for exploring the system!")
        
        session_duration = time.time() - self.session_start_time
        
        print(f"{Colors.BOLD}Session Summary:{Colors.ENDC}")
        print(f"• Duration: {session_duration/60:.1f} minutes")
        print(f"• User Explored: {self.current_user.name if self.current_user else 'Multiple personas'}")
        print(f"• Features Demonstrated: Interactive conversation, crisis management, dashboards")
        print()
        
        print(f"{Colors.BOLD}Key System Capabilities Shown:{Colors.ENDC}")
        print(f"✓ Multi-role user interface with appropriate permissions")
        print(f"✓ Real-time emotional AI with contextual interventions")
        print(f"✓ Crisis detection with immediate human escalation")
        print(f"✓ Comprehensive dashboard analytics for all user types")
        print(f"✓ HIPAA-compliant privacy controls and audit logging")
        print(f"✓ Healthcare integration with EHR and care management systems")
        print()
        
        print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}")
        print(f"• Review technical documentation for implementation details")
        print(f"• Contact development team for customization requirements")
        print(f"• Schedule pilot deployment planning session")
        print(f"• Prepare staff training and change management plan")
        print()
        
        print(f"{Colors.GREEN}{Colors.BOLD}Thank you for exploring the MultiDB Therapeutic AI Chatbot!{Colors.ENDC}")


async def main():
    """Main demo entry point"""
    # Check for real data flag
    use_real_data = "--use-real-data" in sys.argv or "--real-data" in sys.argv
    
    if use_real_data and not REAL_DATA_AVAILABLE:
        print(f"{Colors.RED}❌ Real data mode requested but demo_database_manager not available{Colors.ENDC}")
        print(f"{Colors.YELLOW}💡 Install required packages: pip install asyncpg pymongo redis scylla-driver{Colors.ENDC}")
        use_real_data = False
    
    demo = InteractiveDemoSystem(use_real_data=use_real_data)
    
    try:
        await demo.main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user{Colors.ENDC}")
    finally:
        if demo.use_real_data and demo.db_manager:
            await cleanup_demo_database_manager()
        demo.show_demo_summary()


if __name__ == "__main__":
    print("Starting MultiDB Therapeutic AI Chatbot Interactive Demo...")
    asyncio.run(main())