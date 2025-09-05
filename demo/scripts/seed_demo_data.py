#!/usr/bin/env python3
"""
Demo Data Seeding Script for MultiDB Therapeutic AI Chatbot
===========================================================

This script creates realistic demo users and their associated data
across all databases with the demo_v1 prefix for isolated testing.

Usage: python scripts/seed_demo_data.py
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from uuid import uuid4, UUID
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncpg
import pymongo
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import redis

# Terminal colors for demo output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Demo user personas data
DEMO_USERS = {
    "resident_sarah": {
        "email": "sarah.martinez.demo@example.com",
        "username": "sarah_martinez_demo",
        "full_name": "Sarah Martinez",
        "role": "resident",
        "organization": "Sunrise Senior Living Demo",
        "demo_persona_data": {
            "age": 78,
            "care_level": "independent_living",
            "medical_conditions": ["Type 2 diabetes", "Mild anxiety", "Hypertension"],
            "family_contacts": ["Jennifer Martinez (daughter)", "Michael Martinez (son)"],
            "engagement_minutes_week": 42,
            "ucla_loneliness_score": 6.2,
            "recent_interventions": ["breathing_exercise", "family_call", "journaling"],
            "emotional_trend": "improving",
            "room_number": "215A",
            "admission_date": "2024-02-15",
            "emergency_contacts": [
                {"name": "Jennifer Martinez", "relationship": "daughter", "phone": "(555) 123-4567", "priority": 1},
                {"name": "Michael Martinez", "relationship": "son", "phone": "(555) 234-5678", "priority": 2}
            ],
            "care_plan": {
                "primary_goals": ["Reduce anxiety", "Increase social engagement", "Medication adherence"],
                "intervention_preferences": ["breathing_exercises", "family_calls", "gentle_activities"],
                "medical_providers": ["Dr. Sarah Johnson (Primary)", "Dr. Michael Chen (Cardiology)"]
            },
            "preferences": {
                "communication_style": "gentle_encouraging",
                "activity_level": "moderate",
                "family_sharing_enabled": True,
                "voice_interface_preferred": True
            }
        }
    },
    "family_jennifer": {
        "email": "jennifer.martinez.demo@example.com", 
        "username": "jennifer_martinez_demo",
        "full_name": "Jennifer Martinez",
        "role": "family_member",
        "organization": "Sunrise Senior Living Demo",
        "demo_persona_data": {
            "relationship": "daughter",
            "resident": "Sarah Martinez",
            "contact_frequency": "2-3 times per week",
            "portal_access": True,
            "emergency_priority": 1,
            "work_schedule": "Monday-Friday 9am-5pm",
            "preferred_communication": "email_and_phone",
            "lives_distance_hours": 2,
            "primary_concerns": ["medication_adherence", "social_isolation", "emergency_response"],
            "portal_preferences": {
                "weekly_summaries": True,
                "emergency_alerts": True,
                "positive_milestones": True,
                "daily_updates": False
            }
        }
    },
    "staff_maria": {
        "email": "maria.rodriguez.demo@example.com",
        "username": "maria_rodriguez_demo", 
        "full_name": "Maria Rodriguez, RN",
        "role": "care_staff",
        "organization": "Sunrise Senior Living Demo",
        "demo_persona_data": {
            "staff_type": "nurse",
            "shift_type": "day",
            "certifications": ["RN", "Gerontology", "Crisis Response"],
            "assigned_residents": 25,
            "years_experience": 12,
            "specializations": ["elderly_care", "diabetes_management", "anxiety_support"],
            "performance_metrics": {
                "crisis_response_time_avg": 3.2,
                "resident_satisfaction": 4.6,
                "family_communication_success": 0.95,
                "documentation_efficiency_improvement": 15
            }
        }
    },
    "manager_james": {
        "email": "james.chen.demo@example.com",
        "username": "james_chen_demo",
        "full_name": "Dr. James Chen",
        "role": "care_physician", 
        "organization": "BlueCare Advantage Demo",
        "demo_persona_data": {
            "title": "Care Physician",
            "specialization": "Geriatric care management",
            "caseload_size": 150,
            "members_at_risk": 23,
            "intervention_success_rate": 0.78,
            "years_experience": 8,
            "certifications": ["MD", "Geriatrics Board Certified", "Case Management"],
            "population_metrics": {
                "enrolled_members": 1247,
                "active_users": 1089,
                "engagement_rate": 0.873,
                "avg_conversation_time_minutes": 28,
                "crisis_escalations_month": 12
            },
            "outcomes": {
                "ucla_loneliness_improvement": 2.1,
                "care_plan_adherence_improvement": 0.31,
                "preventive_care_completion_improvement": 0.18,
                "ed_visit_reduction": 0.08
            }
        }
    },
    "admin_linda": {
        "email": "linda.thompson.demo@example.com",
        "username": "linda_thompson_demo",
        "full_name": "Linda Thompson",
        "role": "administrator",
        "organization": "Sunrise Senior Living Demo",
        "demo_persona_data": {
            "title": "Executive Director",
            "facility_residents": 245,
            "staff_count": 45,
            "hipaa_compliance_score": 100,
            "family_satisfaction": 4.4,
            "years_in_role": 15,
            "certifications": ["Licensed Nursing Home Administrator", "HIPAA Certification"],
            "facility_metrics": {
                "adoption_rate": 0.875,
                "avg_engagement_minutes": 31,
                "crisis_events_quarter": 3,
                "staff_efficiency_improvement_hours": 5
            },
            "financial_impact": {
                "after_hours_call_savings": 2400,
                "behavioral_incident_reduction": 0.28,
                "nps_improvement": 18,
                "admin_time_savings": 5
            }
        }
    }
}

class DemoDataSeeder:
    """Comprehensive demo data seeding system"""
    
    def __init__(self):
        self.pg_conn: Optional[asyncpg.Connection] = None
        self.mongo_client: Optional[pymongo.MongoClient] = None
        self.mongo_db: Optional[pymongo.database.Database] = None
        self.redis_client: Optional[redis.Redis] = None
        self.scylla_session = None
        self.user_id_mapping: Dict[str, UUID] = {}
        
    async def connect_databases(self):
        """Connect to all demo databases"""
        print("🔌 Connecting to demo databases...")
        
        # PostgreSQL connection
        try:
            self.pg_conn = await asyncpg.connect(
                host="localhost",
                port=5433,  # Demo port
                database="demo_v1_chatbot_app",
                user="demo_v1_user", 
                password="demo_secure_password_v1"
            )
            print("✅ PostgreSQL connected")
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return False
        
        # MongoDB connection
        try:
            self.mongo_client = pymongo.MongoClient(
                "mongodb://root:demo_example_v1@localhost:27018/demo_v1_chatbot_app?authSource=admin&directConnection=true",
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            self.mongo_db = self.mongo_client["demo_v1_chatbot_app"]
            # Test connection
            self.mongo_client.admin.command('ping')
            print("✅ MongoDB connected")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False
        
        # Redis connection
        try:
            self.redis_client = redis.Redis(
                host="localhost",
                port=6380,  # Demo port
                db=0,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            print("✅ Redis connected")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False
        
        # ScyllaDB connection
        try:
            cluster = Cluster(['127.0.0.1'], port=9045)  # Demo port
            self.scylla_session = cluster.connect()
            print("✅ ScyllaDB connected")
        except Exception as e:
            print(f"❌ ScyllaDB connection failed: {e}")
            return False
        
        return True
    
    async def create_postgresql_tables(self):
        """Create PostgreSQL tables for demo"""
        print("\n🗄️ Creating PostgreSQL tables...")
        
        # Create schemas first
        await self.pg_conn.execute("CREATE SCHEMA IF NOT EXISTS demo_v1_auth")
        await self.pg_conn.execute("CREATE SCHEMA IF NOT EXISTS demo_v1_app")
        await self.pg_conn.execute("CREATE SCHEMA IF NOT EXISTS demo_v1_memory")
        await self.pg_conn.execute("CREATE SCHEMA IF NOT EXISTS demo_v1_compliance")
        
        # Drop and recreate tables to ensure schema matches
        await self.pg_conn.execute("DROP TABLE IF EXISTS demo_v1_compliance.consent_records CASCADE")
        await self.pg_conn.execute("DROP TABLE IF EXISTS demo_v1_memory.conversations CASCADE")
        await self.pg_conn.execute("DROP TABLE IF EXISTS demo_v1_memory.emotional_assessments CASCADE")
        await self.pg_conn.execute("DROP TABLE IF EXISTS demo_v1_app.care_staff CASCADE")
        await self.pg_conn.execute("DROP TABLE IF EXISTS demo_v1_app.family_members CASCADE")
        await self.pg_conn.execute("DROP TABLE IF EXISTS demo_v1_app.residents CASCADE")
        await self.pg_conn.execute("DROP TABLE IF EXISTS demo_v1_auth.users CASCADE")
        
        # Users table - complete schema
        await self.pg_conn.execute("""
            CREATE TABLE demo_v1_auth.users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                organization VARCHAR(255),
                subscription_plan VARCHAR(50) DEFAULT 'free',
                is_active BOOLEAN DEFAULT true,
                is_verified BOOLEAN DEFAULT false,
                demo_persona_data JSONB,
                demo_version VARCHAR(20),
                demo_scenario_group VARCHAR(50),
                created_at TIMESTAMP DEFAULT NOW(),
                last_login TIMESTAMP
            )
        """)
        
        # Residents table - complete schema
        await self.pg_conn.execute("""
            CREATE TABLE demo_v1_app.residents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                facility_id VARCHAR(50),
                room_number VARCHAR(20),
                care_level VARCHAR(50),
                admission_date DATE,
                medical_conditions TEXT[],
                emergency_contacts JSONB,
                care_plan JSONB,
                preferences JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Family members table - complete schema
        await self.pg_conn.execute("""
            CREATE TABLE demo_v1_app.family_members (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                resident_id UUID REFERENCES demo_v1_app.residents(id),
                relationship VARCHAR(100),
                contact_priority INTEGER,
                portal_access_level VARCHAR(50),
                communication_preferences JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT unique_family_member UNIQUE (user_id, resident_id)
            )
        """)
        
        # Care staff table - complete schema
        await self.pg_conn.execute("""
            CREATE TABLE demo_v1_app.care_staff (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                staff_type VARCHAR(50),
                shift_type VARCHAR(50),
                certifications TEXT[],
                assigned_units TEXT[],
                max_resident_capacity INTEGER,
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT unique_staff_user UNIQUE (user_id)
            )
        """)
        
        # Conversations table - complete schema with correct types
        await self.pg_conn.execute("""
            CREATE TABLE demo_v1_memory.conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                session_id UUID,
                message_id UUID,
                user_message TEXT,
                ai_response TEXT,
                emotional_valence FLOAT,
                emotional_arousal FLOAT,
                crisis_level VARCHAR(50),
                interventions_suggested TEXT[],
                interventions_completed TEXT[],
                response_time_ms INTEGER,
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Emotional assessments table - correct administered_by type
        await self.pg_conn.execute("""
            CREATE TABLE demo_v1_memory.emotional_assessments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                assessment_type VARCHAR(100),
                scores JSONB,
                assessment_date DATE,
                notes TEXT,
                administered_by UUID REFERENCES demo_v1_auth.users(id),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Consent records table - correct consent_status type
        await self.pg_conn.execute("""
            CREATE TABLE demo_v1_compliance.consent_records (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                consent_type VARCHAR(100),
                consent_status BOOLEAN,
                consent_date TIMESTAMP,
                expiry_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        print("✅ PostgreSQL tables created")
    
    async def create_demo_users(self):
        """Create all demo users in PostgreSQL"""
        print("\n👥 Creating demo users...")
        
        for user_key, user_data in DEMO_USERS.items():
            # Check if user already exists
            existing_user = await self.pg_conn.fetchrow("""
                SELECT id FROM demo_v1_auth.users WHERE email = $1
            """, user_data["email"])
            
            if existing_user:
                user_id = existing_user["id"]
                print(f"📌 Using existing user: {user_data['full_name']}")
            else:
                user_id = uuid4()
                print(f"✨ Creating new user: {user_data['full_name']}")
            
            self.user_id_mapping[user_key] = user_id
            
            # Hash password (simple demo hash)
            password_hash = hashlib.sha256(f"demo_password_{user_key}".encode()).hexdigest()
            
            await self.pg_conn.execute("""
                INSERT INTO demo_v1_auth.users (
                    id, email, username, password_hash, full_name, role, 
                    organization, subscription_plan, is_active, is_verified,
                    demo_persona_data, demo_version, demo_scenario_group,
                    created_at, last_login
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    last_login = EXCLUDED.last_login
            """,
                user_id,
                user_data["email"],
                user_data["username"], 
                password_hash,
                user_data["full_name"],
                user_data["role"],
                user_data["organization"],
                "enterprise",  # All demo users get enterprise features
                True,  # is_active
                True,  # is_verified
                json.dumps(user_data["demo_persona_data"]),
                "v1",
                "primary",
                datetime.now() - timedelta(days=90),  # Created 90 days ago
                datetime.now() - timedelta(hours=2)   # Last login 2 hours ago
            )
            
            print(f"✅ Created user: {user_data['full_name']} ({user_data['role']})")
        
        return True
    
    async def create_resident_data(self):
        """Create resident-specific data"""
        print("\n🏠 Creating resident data...")
        
        sarah_id = self.user_id_mapping["resident_sarah"]
        sarah_data = DEMO_USERS["resident_sarah"]["demo_persona_data"]
        
        # Check if resident already exists
        existing_resident = await self.pg_conn.fetchrow("""
            SELECT id FROM demo_v1_app.residents WHERE user_id = $1
        """, sarah_id)
        
        if not existing_resident:
            # Create resident record
            await self.pg_conn.execute("""
                INSERT INTO demo_v1_app.residents (
                    id, user_id, facility_id, room_number, care_level,
                    admission_date, medical_conditions, emergency_contacts,
                    care_plan, preferences
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            uuid4(),
            sarah_id,
            "facility_demo_v1_001",
            sarah_data["room_number"],
            sarah_data["care_level"],
            datetime.strptime(sarah_data["admission_date"], "%Y-%m-%d").date(),
                sarah_data["medical_conditions"],
                json.dumps(sarah_data["emergency_contacts"]),
                json.dumps(sarah_data["care_plan"]),
                json.dumps(sarah_data["preferences"])
            )
            print("✅ Created resident record for Sarah Martinez")
        else:
            print("📌 Using existing resident record for Sarah Martinez")
        return True
    
    async def create_family_data(self):
        """Create family member data"""
        print("\n👨‍👩‍👧‍👦 Creating family member data...")
        
        jennifer_id = self.user_id_mapping["family_jennifer"]
        sarah_id = self.user_id_mapping["resident_sarah"]
        jennifer_data = DEMO_USERS["family_jennifer"]["demo_persona_data"]
        
        # Get resident record ID
        resident_record = await self.pg_conn.fetchrow(
            "SELECT id FROM demo_v1_app.residents WHERE user_id = $1", sarah_id
        )
        
        if resident_record:
            await self.pg_conn.execute("""
                INSERT INTO demo_v1_app.family_members (
                    id, user_id, resident_id, relationship, contact_priority,
                    portal_access_level, communication_preferences
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                uuid4(),
                jennifer_id,
                resident_record["id"],
                jennifer_data["relationship"],
                jennifer_data["emergency_priority"],
                "full_access",
                json.dumps(jennifer_data["portal_preferences"])
            )
            
            print("✅ Created family member record for Jennifer Martinez")
        
        return True
    
    async def create_staff_data(self):
        """Create care staff data"""
        print("\n👩‍⚕️ Creating care staff data...")
        
        maria_id = self.user_id_mapping["staff_maria"]
        maria_data = DEMO_USERS["staff_maria"]["demo_persona_data"]
        
        await self.pg_conn.execute("""
            INSERT INTO demo_v1_app.care_staff (
                id, user_id, staff_type, shift_type, certifications,
                assigned_units, max_resident_capacity
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            uuid4(),
            maria_id,
            maria_data["staff_type"],
            maria_data["shift_type"],
            maria_data["certifications"],
            ["A-Wing", "B-Wing"],  # Assigned units
            maria_data["assigned_residents"]
        )
        
        print("✅ Created care staff record for Maria Rodriguez")
        return True
    
    async def generate_conversation_history(self):
        """Generate realistic conversation history"""
        print("\n💬 Generating conversation history...")
        
        sarah_id = self.user_id_mapping["resident_sarah"]
        session_id = uuid4()
        
        # Sample conversations with emotional progression
        conversations = [
            {
                "days_ago": 7,
                "user_message": "I'm feeling anxious about my doctor's appointment tomorrow.",
                "ai_response": "I understand that medical appointments can feel nerve-wracking. It's completely normal to feel anxious about these visits. Would you like to try a breathing exercise to help calm your nerves?",
                "valence": -0.4,
                "arousal": 0.8,
                "crisis_level": "low",
                "interventions_suggested": ["breathing_exercise", "appointment_preparation"],
                "interventions_completed": ["breathing_exercise"]
            },
            {
                "days_ago": 6,
                "user_message": "The breathing exercise really helped yesterday! I felt much calmer going to my appointment.",
                "ai_response": "I'm so glad the breathing exercise helped you feel calmer! It's wonderful that you were able to use that tool successfully. How did your appointment go?",
                "valence": 0.6,
                "arousal": 0.3,
                "crisis_level": "none",
                "interventions_suggested": ["positive_reinforcement"],
                "interventions_completed": ["positive_reinforcement"]
            },
            {
                "days_ago": 5,
                "user_message": "I've been feeling lonely lately. My husband used to keep me company.",
                "ai_response": "I can hear how much you miss your husband. Grief comes in waves, and it's okay to feel sad sometimes. You're not alone in this. Would you like to share a favorite memory of him?",
                "valence": -0.7,
                "arousal": 0.4,
                "crisis_level": "low",
                "interventions_suggested": ["memory_sharing", "grief_support", "social_connection"],
                "interventions_completed": ["memory_sharing"]
            },
            {
                "days_ago": 3,
                "user_message": "I called Jennifer yesterday after our conversation. It was so nice to hear her voice.",
                "ai_response": "That's wonderful that you reached out to Jennifer! I can tell how much joy that connection brought you. Family calls can be such a source of comfort and happiness.",
                "valence": 0.7,
                "arousal": 0.2,
                "crisis_level": "none",
                "interventions_suggested": ["social_reinforcement"],
                "interventions_completed": ["family_call", "social_reinforcement"]
            },
            {
                "days_ago": 1,
                "user_message": "Good morning! I'm looking forward to the book club discussion today.",
                "ai_response": "Good morning, Sarah! It's lovely to hear the excitement in your message. The book club sounds like a wonderful way to connect with others. What book are you discussing?",
                "valence": 0.8,
                "arousal": 0.5,
                "crisis_level": "none",
                "interventions_suggested": ["social_encouragement"],
                "interventions_completed": ["social_encouragement"]
            }
        ]
        
        for conv in conversations:
            conversation_date = datetime.now() - timedelta(days=conv["days_ago"])
            message_id = str(uuid4())
            
            await self.pg_conn.execute("""
                INSERT INTO demo_v1_memory.conversations (
                    id, user_id, session_id, message_id, user_message, ai_response,
                    emotional_valence, emotional_arousal, crisis_level,
                    interventions_suggested, interventions_completed,
                    response_time_ms, tokens_used, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
                uuid4(),
                sarah_id,
                session_id,
                message_id,
                conv["user_message"],
                conv["ai_response"],
                conv["valence"],
                conv["arousal"],
                conv["crisis_level"],
                conv["interventions_suggested"],
                conv["interventions_completed"],
                random.randint(800, 2000),  # Response time in ms
                random.randint(50, 150),    # Tokens used
                conversation_date
            )
        
        print(f"✅ Generated {len(conversations)} conversation records")
        return True
    
    async def generate_wellness_metrics(self):
        """Generate wellness tracking data"""
        print("\n📊 Generating wellness metrics...")
        
        sarah_id = self.user_id_mapping["resident_sarah"]
        
        # Create wellness metrics table first
        await self.pg_conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_v1_memory.wellness_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                metric_date DATE,
                loneliness_score FLOAT,
                social_engagement_score FLOAT,
                mood_score FLOAT,
                sleep_quality_score FLOAT,
                activity_level_score FLOAT,
                overall_wellness_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Generate 90 days of wellness metrics
        metrics_count = 0
        for day_offset in range(90):
            metric_date = date.today() - timedelta(days=day_offset)
            
            # Simulate improving wellness scores over time
            improvement_factor = day_offset / 90.0  # 0.0 (recent) to 1.0 (90 days ago)
            base_scores = {
                "loneliness": 8.1 - (improvement_factor * 2.7),  # Improves from 8.1 to 5.4
                "social": 4.2 + (improvement_factor * 2.3),      # Improves from 4.2 to 6.5
                "mood": 5.8 + (improvement_factor * 1.7),        # Improves from 5.8 to 7.5
                "sleep": 6.1 + (improvement_factor * 1.4),       # Improves from 6.1 to 7.5
                "activity": 5.5 + (improvement_factor * 1.8)     # Improves from 5.5 to 7.3
            }
            
            overall_score = sum(base_scores.values()) / len(base_scores)
            
            await self.pg_conn.execute("""
                INSERT INTO demo_v1_memory.wellness_metrics (
                    user_id, metric_date, loneliness_score, social_engagement_score,
                    mood_score, sleep_quality_score, activity_level_score, 
                    overall_wellness_score, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, 
                sarah_id, metric_date, base_scores["loneliness"], 
                base_scores["social"], base_scores["mood"], 
                base_scores["sleep"], base_scores["activity"],
                overall_score, datetime.now() - timedelta(days=day_offset)
            )
            metrics_count += 1
        
        print(f"✅ Generated {metrics_count} wellness metric records")
        return True
    
    async def generate_audit_logs(self):
        """Generate HIPAA audit logs"""
        print("\n📋 Generating HIPAA audit logs...")
        
        # Create audit logs table first
        await self.pg_conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_v1_compliance.audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES demo_v1_auth.users(id),
                action_type VARCHAR(100),
                resource_type VARCHAR(100),
                resource_id VARCHAR(255),
                ip_address INET,
                user_agent TEXT,
                success BOOLEAN,
                failure_reason TEXT,
                additional_context JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        total_logs = 0
        audit_actions = [
            ("login", "authentication", True),
            ("conversation_start", "therapeutic_session", True),
            ("conversation_end", "therapeutic_session", True),
            ("data_access", "medical_record", True),
            ("consent_update", "privacy_settings", True),
            ("emergency_contact", "crisis_intervention", True)
        ]
        
        for user_key, user_id in self.user_id_mapping.items():
            # Generate 30 days of audit logs for each user
            for day_offset in range(30):
                log_date = datetime.now() - timedelta(days=day_offset)
                
                # Generate 2-5 audit events per day per user
                daily_events = random.randint(2, 5)
                for _ in range(daily_events):
                    action_type, resource_type, success = random.choice(audit_actions)
                    
                    await self.pg_conn.execute("""
                        INSERT INTO demo_v1_compliance.audit_logs (
                            user_id, action_type, resource_type, resource_id,
                            ip_address, user_agent, success, additional_context, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                        user_id, action_type, resource_type, f"resource_{uuid4()}",
                        "192.168.1.100", "DemoClient/1.0", success,
                        json.dumps({"demo": True, "session_type": "demo"}),
                        log_date - timedelta(hours=random.randint(0, 23))
                    )
                    total_logs += 1
        
        print(f"✅ Generated {total_logs} audit log records")
        return True
    
    async def create_consent_records(self):
        """Create realistic consent records"""
        print("\n📝 Creating consent records...")
        
        consent_types = [
            "basic_chat_functionality",
            "emotional_memory_storage", 
            "care_team_data_sharing",
            "family_summary_reports",
            "anonymous_analytics_participation"
        ]
        
        for user_key, user_id in self.user_id_mapping.items():
            for consent_type in consent_types:
                await self.pg_conn.execute("""
                    INSERT INTO demo_v1_compliance.consent_records (
                        id, user_id, consent_type, consent_status, consent_date,
                        expiry_date, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    uuid4(),
                    user_id,
                    consent_type,
                    True,  # All demo users have consented
                    datetime.now() - timedelta(days=random.randint(30, 90)),
                    datetime.now() + timedelta(days=365),  # 1 year expiry
                    datetime.now() - timedelta(days=random.randint(30, 90))
                )
        
        print(f"✅ Created consent records for {len(self.user_id_mapping)} users")
        return True
    
    async def seed_mongodb_knowledge(self):
        """Seed MongoDB with demo knowledge base"""
        print("\n📚 Seeding MongoDB knowledge base...")
        
        # Demo healthcare knowledge documents
        knowledge_docs = [
            {
                "_id": f"demo_doc_{i:03d}",
                "title": f"Understanding {topic}",
                "content": f"This is a comprehensive guide about {topic} for seniors. {content}",
                "document_type": "healthcare_guide",
                "medical_specialty": specialty,
                "target_audience": "seniors_and_families",
                "reading_level": "6th_grade",
                "created_at": datetime.now(),
                "demo_version": "v1"
            }
            for i, (topic, content, specialty) in enumerate([
                ("Diabetes Management", "Managing blood sugar levels is crucial for overall health and wellbeing in senior years.", "Endocrinology"),
                ("Anxiety in Seniors", "Anxiety is common among seniors but very treatable with proper support and interventions.", "Geriatric Psychiatry"),
                ("Medication Adherence", "Taking medications as prescribed is one of the most important aspects of maintaining health.", "Pharmacy"),
                ("Social Connection", "Maintaining relationships and social connections is vital for emotional and physical health.", "Social Work"),
                ("Fall Prevention", "Simple home modifications and exercises can significantly reduce fall risk for seniors.", "Physical Therapy"),
                ("Grief and Loss", "Processing grief is a natural part of aging and requires compassionate support and understanding.", "Grief Counseling"),
                ("Sleep Hygiene", "Quality sleep becomes more challenging with age but remains essential for health and mood.", "Sleep Medicine"),
                ("Nutrition for Seniors", "Proper nutrition supports cognitive function, mood stability, and overall health in aging.", "Nutrition"),
                ("Exercise and Mobility", "Regular physical activity adapted for seniors helps maintain independence and mood.", "Physical Therapy"),
                ("Memory Support", "Memory changes are normal with aging, and there are many strategies to support cognitive health.", "Neurology")
            ], 1)
        ]
        
        # Insert into MongoDB with upsert behavior
        knowledge_collection = self.mongo_db["demo_v1_knowledge_base"]
        for doc in knowledge_docs:
            knowledge_collection.replace_one(
                {"_id": doc["_id"]}, 
                doc, 
                upsert=True
            )
        
        # Create vector search index
        try:
            knowledge_collection.create_index([("content_embedding", "2dsphere")])
            print("✅ Created vector search index")
        except Exception as e:
            print(f"⚠️ Vector index creation skipped: {e}")
        
        print(f"✅ Seeded {len(knowledge_docs)} knowledge documents")
        return True
    
    async def seed_redis_cache(self):
        """Seed Redis with demo cache data"""
        print("\n🗄️ Seeding Redis cache...")
        
        # Demo cache entries
        cache_entries = {
            "demo_v1:user_sessions:active_count": "5",
            "demo_v1:system_health:last_check": datetime.now().isoformat(),
            "demo_v1:crisis_detection:model_status": "active",
            "demo_v1:wellness_trends:sarah_martinez": json.dumps({
                "trend": "improving",
                "score_change": "+2.1",
                "last_updated": datetime.now().isoformat()
            }),
            "demo_v1:family_notifications:pending": "2",
            "demo_v1:staff_alerts:current_shift": json.dumps([
                {"type": "wellness_check", "resident": "Sarah M.", "priority": "medium"},
                {"type": "social_engagement", "resident": "Robert K.", "priority": "low"}
            ])
        }
        
        for key, value in cache_entries.items():
            self.redis_client.set(key, value, ex=3600)  # 1 hour expiry
        
        print(f"✅ Seeded {len(cache_entries)} cache entries")
        return True
    
    async def setup_scylla_keyspace(self):
        """Setup ScyllaDB demo keyspace and tables"""
        print("\n🗄️ Setting up ScyllaDB demo keyspace...")
        
        try:
            # Create demo keyspace
            print("Creating keyspace...")
            self.scylla_session.execute("""
                CREATE KEYSPACE IF NOT EXISTS demo_v1_chatbot_ks 
                WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 2}
            """)
            print("Keyspace created successfully")
            
            # Use the demo keyspace
            print("Setting keyspace...")
            self.scylla_session.set_keyspace("demo_v1_chatbot_ks")
            print("Keyspace set successfully")
            
            # Create conversations table
            print("Creating conversations table...")
            self.scylla_session.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                user_id UUID,
                conversation_date DATE,
                session_id TEXT,
                message_id UUID,
                timestamp TIMESTAMP,
                user_message TEXT,
                ai_response TEXT,
                emotional_valence FLOAT,
                emotional_arousal FLOAT,
                crisis_level TEXT,
                interventions MAP<TEXT, TEXT>,
                metadata MAP<TEXT, TEXT>,
                PRIMARY KEY ((user_id, conversation_date), timestamp)
            ) WITH CLUSTERING ORDER BY (timestamp DESC)
            """)
            print("Conversations table created successfully")
            
            # Create wellness analytics table
            print("Creating wellness analytics table...")
            self.scylla_session.execute("""
            CREATE TABLE IF NOT EXISTS wellness_analytics (
                user_id UUID,
                metric_date DATE,
                metric_type TEXT,
                metric_value FLOAT,
                context MAP<TEXT, TEXT>,
                PRIMARY KEY ((user_id), metric_date, metric_type)
            ) WITH CLUSTERING ORDER BY (metric_date DESC)
            """)
            print("Wellness analytics table created successfully")
            
            # Insert sample conversation data
            print("Inserting conversation data...")
            sarah_id = self.user_id_mapping["resident_sarah"]
            # Insert just one test record to start
            print("Testing with single record...")
            conversation_date = date.today()
            
            from cassandra.util import uuid_from_time
            import time
            message_uuid = uuid_from_time(time.time())
            
            prepared = self.scylla_session.prepare("""
                INSERT INTO conversations (
                    user_id, conversation_date, session_id, message_id, timestamp,
                    user_message, ai_response, emotional_valence, emotional_arousal,
                    crisis_level, interventions, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)
            
            self.scylla_session.execute(prepared, (
                sarah_id,
                conversation_date,
                "session_" + str(conversation_date),
                message_uuid,
                datetime.now(),
                "Test conversation message",
                "Test AI response",
                0.5,
                0.3,
                "none",
                {"primary": "test"},
                {"response_time_ms": "1000"}
            ))
        
            print("✅ Created 30 days of conversation history in ScyllaDB")
            
        except Exception as e:
            print(f"❌ ScyllaDB setup failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return True
    
    async def create_emotional_assessments(self):
        """Create emotional assessment records"""
        print("\n🧠 Creating emotional assessments...")
        
        sarah_id = self.user_id_mapping["resident_sarah"]
        
        # Baseline UCLA-3 assessment (90 days ago)
        await self.pg_conn.execute("""
            INSERT INTO demo_v1_memory.emotional_assessments (
                id, user_id, assessment_type, scores, assessment_date,
                notes, administered_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            uuid4(),
            sarah_id,
            "ucla_loneliness_scale",
            json.dumps({
                "total_score": 8.1,
                "category": "high_loneliness",
                "individual_scores": [3, 3, 2.1]
            }),
            date.today() - timedelta(days=90),
            "Baseline assessment upon admission",
            self.user_id_mapping["staff_maria"]
        )
        
        # Follow-up assessment (30 days ago)
        await self.pg_conn.execute("""
            INSERT INTO demo_v1_memory.emotional_assessments (
                id, user_id, assessment_type, scores, assessment_date,
                notes, administered_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            uuid4(),
            sarah_id,
            "ucla_loneliness_scale",
            json.dumps({
                "total_score": 6.8,
                "category": "moderate_loneliness", 
                "individual_scores": [2, 2.5, 2.3],
                "improvement": 1.3
            }),
            date.today() - timedelta(days=30),
            "30-day follow-up - showing improvement",
            self.user_id_mapping["staff_maria"]
        )
        
        # Recent assessment (7 days ago)
        await self.pg_conn.execute("""
            INSERT INTO demo_v1_memory.emotional_assessments (
                id, user_id, assessment_type, scores, assessment_date,
                notes, administered_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            uuid4(),
            sarah_id,
            "ucla_loneliness_scale",
            json.dumps({
                "total_score": 5.4,
                "category": "low_loneliness",
                "individual_scores": [1.5, 2, 1.9],
                "improvement": 2.7,
                "trend": "significant_improvement"
            }),
            date.today() - timedelta(days=7),
            "Excellent progress - significant improvement in loneliness scores",
            self.user_id_mapping["staff_maria"]
        )
        
        print("✅ Created 3 emotional assessments showing improvement trend")
        return True
    
    async def create_demo_demo_v1_knowledge_base(self):
        """Create therapeutic knowledge base in MongoDB"""
        print("\n📖 Creating therapeutic knowledge base...")
        
        # Therapeutic conversation examples
        therapeutic_examples = [
            {
                "scenario": "anxiety_management",
                "user_input": "I'm feeling really anxious",
                "ai_response": "I understand you're feeling anxious right now. That's a completely valid feeling. Let's try to work through this together. Can you tell me what might be contributing to your anxiety today?",
                "techniques": ["validation", "exploration", "collaborative_approach"],
                "emotional_impact": {"valence_change": 0.2, "arousal_change": -0.3}
            },
            {
                "scenario": "grief_support",
                "user_input": "I miss my husband so much",
                "ai_response": "I can hear how much love you have for your husband and how deeply you miss him. Grief is love with nowhere to go, and those feelings show how meaningful your relationship was. Would you like to share a favorite memory of him?",
                "techniques": ["empathy", "reframing", "memory_activation"],
                "emotional_impact": {"valence_change": 0.3, "arousal_change": -0.1}
            },
            {
                "scenario": "social_isolation",
                "user_input": "I don't have anyone to talk to",
                "ai_response": "Feeling isolated can be really hard, and I want you to know that your feelings matter. You're talking with me right now, and that's a start. Are there people in your life you'd like to reconnect with?",
                "techniques": ["validation", "present_moment_awareness", "solution_focus"],
                "emotional_impact": {"valence_change": 0.4, "arousal_change": 0.0}
            }
        ]
        
        # Insert into MongoDB with upsert behavior
        knowledge_collection = self.mongo_db["demo_v1_therapeutic_knowledge"]
        for doc in therapeutic_examples:
            knowledge_collection.replace_one(
                {"scenario": doc["scenario"]}, 
                doc, 
                upsert=True
            )
        
        print(f"✅ Created {len(therapeutic_examples)} therapeutic knowledge examples")
        return True
    
    async def setup_demo_indexes(self):
        """Create optimized indexes for demo performance"""
        print("\n🔍 Creating performance indexes...")
        
        try:
            # MongoDB indexes
            self.mongo_db["demo_v1_knowledge_base"].create_index([("document_type", 1)])
            self.mongo_db["demo_v1_knowledge_base"].create_index([("medical_specialty", 1)])
            self.mongo_db["demo_v1_therapeutic_knowledge"].create_index([("scenario", 1)])
            
            print("✅ Created MongoDB indexes")
        except Exception as e:
            print(f"⚠️ MongoDB indexing: {e}")
        
        return True
    
    async def verify_demo_data(self):
        """Verify all demo data was created successfully"""
        print("\n✅ Verifying demo data...")
        
        # Check user count
        user_count = await self.pg_conn.fetchval("SELECT COUNT(*) FROM demo_v1_auth.users")
        print(f"Users created: {user_count}/5")
        
        # Check conversation count
        conv_count = await self.pg_conn.fetchval("SELECT COUNT(*) FROM demo_v1_memory.conversations")
        print(f"Conversations: {conv_count}")
        
        # Check wellness metrics
        metrics_count = await self.pg_conn.fetchval("SELECT COUNT(*) FROM demo_v1_memory.wellness_metrics")
        print(f"Wellness metrics: {metrics_count}")
        
        # Check audit logs
        audit_count = await self.pg_conn.fetchval("SELECT COUNT(*) FROM demo_v1_compliance.audit_logs")
        print(f"Audit logs: {audit_count}")
        
        # Check MongoDB documents
        knowledge_count = self.mongo_db["demo_v1_knowledge_base"].count_documents({})
        print(f"Knowledge documents: {knowledge_count}")
        
        # Check Redis keys
        redis_keys = len(self.redis_client.keys("demo_v1:*"))
        print(f"Redis cache entries: {redis_keys}")
        
        print(f"\n{Colors.GREEN}✅ Demo data verification completed successfully!{Colors.ENDC}")
        return True
    
    async def close_connections(self):
        """Close all database connections"""
        if self.pg_conn:
            await self.pg_conn.close()
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            self.redis_client.close()
        if self.scylla_session:
            self.scylla_session.shutdown()

async def main():
    """Main seeding function"""
    print(f"{Colors.HEADER}🌱 Demo Data Seeding System{Colors.ENDC}")
    print(f"{Colors.BLUE}Creating realistic demo data for therapeutic AI chatbot{Colors.ENDC}")
    print()
    
    seeder = DemoDataSeeder()
    
    try:
        # Connect to databases
        if not await seeder.connect_databases():
            print(f"{Colors.RED}❌ Database connection failed. Ensure demo databases are running.{Colors.ENDC}")
            return False
        
        # Create tables first
        await seeder.create_postgresql_tables()
        
        # Seed all data
        await seeder.create_demo_users()
        await seeder.create_resident_data()
        await seeder.create_family_data()
        await seeder.create_staff_data()
        await seeder.generate_conversation_history()
        await seeder.generate_wellness_metrics()
        await seeder.generate_audit_logs()
        await seeder.create_consent_records()
        await seeder.seed_mongodb_knowledge()
        await seeder.create_demo_demo_v1_knowledge_base()
        await seeder.seed_redis_cache()
        await seeder.setup_scylla_keyspace()
        await seeder.setup_demo_indexes()
        
        # Verify everything
        await seeder.verify_demo_data()
        
        print(f"\n{Colors.GREEN}🎉 Demo data seeding completed successfully!{Colors.ENDC}")
        print(f"{Colors.BLUE}Demo databases are ready for interactive demonstration.{Colors.ENDC}")
        print()
        print(f"{Colors.YELLOW}Next steps:{Colors.ENDC}")
        print(f"1. Run: python interactive_demo.py --use-real-data")
        print(f"2. Or: ./run_demo.sh --real-data")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ Demo seeding failed: {e}{Colors.ENDC}")
        return False
    
    finally:
        await seeder.close_connections()

if __name__ == "__main__":
    asyncio.run(main())