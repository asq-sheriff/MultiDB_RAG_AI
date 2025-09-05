#!/usr/bin/env python3
"""
Seed Sarah's schedule and routine data based on dashboard specifications
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_layer.connections.postgres_connection import get_postgres_manager
from data_layer.models.postgres.postgres_models import (
    User, UserActivity, DailyRoutine, ActivityType, ActivityStatus
)
from sqlalchemy import select


async def seed_sarah_schedule_data():
    """Seed Sarah's schedule and routine data"""
    
    # Get database connection
    postgres_manager = get_postgres_manager()
    await postgres_manager.initialize()
    session = postgres_manager.get_session()
    
    try:
        # Find Sarah Martinez user
        result = await session.execute(
            select(User).where(User.email == "sarah.martinez.demo@example.com")
        )
        sarah = result.scalar_one_or_none()
        
        if not sarah:
            print("❌ Sarah Martinez user not found")
            return False
        
        print(f"✅ Found Sarah Martinez (ID: {sarah.user_id})")
        
        # Create Sarah's daily routines
        routines = [
            {
                "routine_name": "Morning Routine",
                "time_of_day": "morning",
                "typical_time": "8:00 AM",
                "activities": ["Take medications", "Light breakfast", "Review daily schedule", "Check in with Lilo"],
                "importance_level": 5,
                "flexibility": "rigid",
                "preferred_location": "Room 215",
                "support_needed": "Medication reminder",
                "special_instructions": "Take Lisinopril with breakfast, check blood pressure"
            },
            {
                "routine_name": "Afternoon Activities",
                "time_of_day": "afternoon", 
                "typical_time": "2:00 PM",
                "activities": ["Social activities", "Physical therapy", "Rest period"],
                "importance_level": 4,
                "flexibility": "flexible",
                "preferred_location": "Community Room or Room 215",
                "support_needed": "Encouragement for group participation",
                "special_instructions": "Prefers chair-based exercises, social activities boost mood"
            },
            {
                "routine_name": "Evening Wind Down",
                "time_of_day": "evening",
                "typical_time": "7:00 PM", 
                "activities": ["Dinner", "Family calls", "Reflection/journaling", "Prepare for bed"],
                "importance_level": 4,
                "flexibility": "adaptable",
                "preferred_location": "Room 215",
                "support_needed": "Technology support for video calls",
                "special_instructions": "Family calls are crucial for emotional wellbeing"
            }
        ]
        
        # Get today's date for scheduling
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Create this week's activities based on dashboard data
        weekly_activities = [
            # Today's schedule
            {
                "title": "Morning Chair Yoga",
                "description": "Gentle movement session adapted for seniors",
                "activity_type": ActivityType.EXERCISE,
                "scheduled_date": today + timedelta(hours=9),
                "start_time": today + timedelta(hours=9),
                "duration_minutes": 30,
                "location": "Activity Room",
                "facilitator": "Physical Therapist",
                "status": ActivityStatus.SCHEDULED
            },
            {
                "title": "Lunch with Reading Group",
                "description": "Social meal followed by book discussion",
                "activity_type": ActivityType.SOCIAL_ACTIVITY,
                "scheduled_date": today + timedelta(hours=12),
                "start_time": today + timedelta(hours=12),
                "duration_minutes": 90,
                "location": "Dining Room",
                "facilitator": "Activities Director",
                "status": ActivityStatus.SCHEDULED
            },
            {
                "title": "Call Jennifer (Daughter)",
                "description": "Weekly check-in call with daughter",
                "activity_type": ActivityType.FAMILY_VISIT,
                "scheduled_date": today + timedelta(hours=16),
                "start_time": today + timedelta(hours=16),
                "duration_minutes": 30,
                "location": "Room 215",
                "status": ActivityStatus.SCHEDULED
            },
            
            # Tomorrow's activities
            {
                "title": "Doctor Appointment - Cardiology Follow-up",
                "description": "Routine cardiology check-up with Dr. Chen",
                "activity_type": ActivityType.MEDICAL_APPOINTMENT,
                "scheduled_date": today + timedelta(days=1, hours=14),
                "start_time": today + timedelta(days=1, hours=14),
                "duration_minutes": 45,
                "location": "Medical Center",
                "facilitator": "Dr. James Chen",
                "status": ActivityStatus.SCHEDULED,
                "care_team_notes": "Patient has pre-appointment anxiety - offer breathing exercise support"
            },
            
            # This week's recurring activities
            {
                "title": "Virtual Book Club Discussion",
                "description": "Weekly book discussion with other residents",
                "activity_type": ActivityType.SOCIAL_ACTIVITY,
                "scheduled_date": today + timedelta(days=2, hours=15),
                "start_time": today + timedelta(days=2, hours=15),
                "duration_minutes": 60,
                "location": "Community Room (Virtual)",
                "facilitator": "Library Volunteer",
                "status": ActivityStatus.SCHEDULED
            },
            {
                "title": "Virtual Gardening Workshop",
                "description": "Interactive gardening session for stress relief",
                "activity_type": ActivityType.THERAPY_SESSION,
                "scheduled_date": today + timedelta(days=4, hours=10),
                "start_time": today + timedelta(days=4, hours=10),
                "duration_minutes": 45,
                "location": "Activity Room (Virtual)",
                "facilitator": "Horticultural Therapist",
                "status": ActivityStatus.SCHEDULED
            }
        ]
        
        # Insert routines
        routine_count = 0
        for routine_data in routines:
            routine = DailyRoutine(
                user_id=sarah.user_id,
                **routine_data
            )
            session.add(routine)
            routine_count += 1
        
        # Insert activities
        activity_count = 0
        for activity_data in weekly_activities:
            activity = UserActivity(
                user_id=sarah.user_id,
                **activity_data
            )
            session.add(activity)
            activity_count += 1
        
        # Commit changes
        await session.commit()
        
        print(f"✅ Successfully seeded {routine_count} routines and {activity_count} activities for Sarah")
        return True
        
    except Exception as e:
        print(f"❌ Failed to seed Sarah's schedule data: {e}")
        await session.rollback()
        return False
    finally:
        await session.close()


if __name__ == "__main__":
    result = asyncio.run(seed_sarah_schedule_data())
    sys.exit(0 if result else 1)