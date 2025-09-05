"""
User Context Router - Routes user queries to role-specific data
Handles semantic matching for dashboard and profile queries
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from sqlalchemy import text

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Classification of user query intents"""
    RESIDENT_MANAGEMENT = "resident_management"     # "residents in my care", "caseload"
    WELLNESS_ALERTS = "wellness_alerts"             # "alerts", "who needs attention"
    DASHBOARD_DATA = "dashboard_data"               # "my metrics", "performance"
    CONVERSATION_HISTORY = "conversation_history"   # "recent conversations", "chat history"
    CRISIS_MANAGEMENT = "crisis_management"         # "emergencies", "crisis situations"
    CARE_PLANNING = "care_planning"                 # "care plans", "treatment updates"
    GENERAL_THERAPEUTIC = "general_therapeutic"     # Generic therapeutic questions

@dataclass
class UserContextQuery:
    """Represents a user query with context"""
    original_query: str
    user_id: str
    user_role: str
    user_name: str
    intent: QueryIntent
    semantic_match_score: float
    care_context: Dict[str, Any] = None

class UserContextRouter:
    """Routes user queries to appropriate role-based data sources"""
    
    def __init__(self, postgres_manager=None):
        self.postgres_manager = postgres_manager
        
        # Semantic patterns for query intent classification
        self.intent_patterns = {
            QueryIntent.RESIDENT_MANAGEMENT: [
                r"residents?\s+(in\s+my\s+care|assigned|caseload|case\s*load)",
                r"(who\s+are\s+the|list\s+of)\s+residents",
                r"my\s+(residents|patients|members|caseload)",
                r"(25|150|\d+)\s+residents",
                r"assigned\s+(residents|patients|members)",
                r"(tell\s+me\s+about|show\s+me)\s+.*residents",
                r"(which|what)\s+(residents|patients)\s+(am\s+I|are\s+we)\s+(assigned|responsible)",
                r"residents?\s+(I\s+)?(am\s+)?(responsible\s+for|caring\s+for|managing)",
                r"(people|individuals)\s+(in\s+my\s+care|under\s+my\s+supervision)",
                r"(current|active)\s+caseload",
                r"residents?\s+(on\s+my\s+list|I\s+oversee|under\s+my\s+care)",
                r"(which|what)\s+residents\s+am\s+I\s+assigned\s+to",
                r"(what|which)\s+individuals\s+am\s+I\s+responsible\s+for",
                r"(list|show)\s+residents\s+I\s+oversee",
                r"residents\s+am\s+I\s+assigned\s+to",
                r"am\s+I\s+assigned\s+to",
                r"responsible\s+for",
                r"I\s+oversee",
                r"residents\s+I\s+oversee",
                r"(how\s+am\s+I|am\s+I)\s+performing",
                r"performing"
            ],
            QueryIntent.WELLNESS_ALERTS: [
                r"wellness\s+(alerts|checks?|warnings?)",
                r"who\s+needs\s+(attention|help|care)",
                r"(2|\d+)\s+(alerts?|warnings?|issues?)",
                r"residents?\s+(requiring|needing)\s+attention", 
                r"health\s+(alerts?|concerns?|issues?)",
                r"urgent\s+(care|attention|intervention)",
                r"who\s+needs\s+(my\s+)?attention\s+(today|now|currently)?",
                r"(any|which)\s+(alerts?|warnings?|concerns?)",
                r"residents?\s+(at\s+risk|in\s+danger|concerning)",
                r"(flag|flagged)\s+(residents?|patients?|cases?)",
                r"(immediate|urgent|priority)\s+(cases?|residents?)",
                r"(which|what)\s+(patients?|residents?)\s+(are\s+)?at\s+risk",
                r"(any|which)\s+flagged\s+(residents?|cases?)",
                r"(least|most)\s+(active|engaged)\s+(patients?|residents?)",
                r"(low|high)\s+(activity|engagement)\s+(patients?|residents?)",
                r"(inactive|disengaged)\s+(patients?|residents?)"
            ],
            QueryIntent.DASHBOARD_DATA: [
                r"my\s+(metrics|dashboard|statistics|stats)",
                r"performance\s+(data|metrics|scores?)",
                r"success\s+rate",
                r"intervention\s+(success|rate|outcomes?)",
                r"(show\s+me\s+my|what\s+are\s+my)\s+(numbers|metrics|stats)",
                r"dashboard\s+(data|information|summary)",
                r"analytics\s+(data|information)",
                r"(how\s+am\s+I|how\s+are\s+we)\s+performing",
                r"(my|our)\s+(performance|outcomes|results)",
                r"(overview|summary)\s+of\s+my\s+(work|performance)",
                r"show\s+me\s+my\s+(analytics|performance)",
                r"what\s+are\s+my\s+(outcomes|results)"
            ],
            QueryIntent.CONVERSATION_HISTORY: [
                r"recent\s+(conversations?|chats?|interactions?)",
                r"conversation\s+(history|log)",
                r"who\s+(have\s+I\s+talked\s+to|did\s+I\s+speak\s+with)",
                r"latest\s+(messages?|conversations?)",
                r"(past|previous)\s+(conversations?|interactions?)",
                r"(chat|conversation)\s+(logs?|records?)",
                r"who\s+(have\s+I\s+)?(been\s+)?(speaking|talking)\s+(with|to)",
                r"recent\s+(activity|communications?)",
                r"who\s+have\s+I\s+been\s+talking\s+with",
                r"(chat|conversation)\s+records",
                r"I\s+(have\s+)?(been\s+)?(talking|speaking)\s+with",
                r"been\s+(talking|speaking)\s+with"
            ],
            QueryIntent.CRISIS_MANAGEMENT: [
                r"(crisis|emergency|urgent)\s+(situations?|cases?|alerts?)",
                r"escalations?",
                r"immediate\s+(attention|intervention|care)",
                r"safety\s+(concerns?|issues?|incidents?)",
                r"emergency\s+(protocols?|procedures?|response)",
                r"(critical|severe)\s+(situations?|cases?)",
                r"break\s+glass\s+(access|procedures?)"
            ],
            QueryIntent.CARE_PLANNING: [
                r"care\s+(plans?|updates?|notes?)",
                r"treatment\s+(plans?|updates?)",
                r"medical\s+(updates?|changes?|notes?)",
                r"medication\s+(changes?|updates?)",
                r"care\s+(coordination|management)",
                r"treatment\s+(goals?|objectives?)",
                r"(therapy|rehabilitation)\s+plans?"
            ]
        }
    
    def classify_query_intent(self, query: str, user_role: str) -> Tuple[QueryIntent, float]:
        """Classify the query intent based on semantic patterns"""
        query_lower = query.lower()
        best_intent = QueryIntent.GENERAL_THERAPEUTIC
        best_score = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    # Calculate semantic match score (higher for more specific matches)
                    score = len(match.group()) / len(query_lower)
                    
                    # Boost score based on role appropriateness
                    if self._is_intent_appropriate_for_role(intent, user_role):
                        score *= 1.5
                    
                    if score > best_score:
                        best_intent = intent
                        best_score = score
        
        return best_intent, best_score
    
    def _is_intent_appropriate_for_role(self, intent: QueryIntent, user_role: str) -> bool:
        """Check if query intent is appropriate for user role"""
        role_intents = {
            "care_staff": [QueryIntent.RESIDENT_MANAGEMENT, QueryIntent.WELLNESS_ALERTS, QueryIntent.CONVERSATION_HISTORY],
            "care_physician": [QueryIntent.RESIDENT_MANAGEMENT, QueryIntent.WELLNESS_ALERTS, QueryIntent.CRISIS_MANAGEMENT, QueryIntent.DASHBOARD_DATA],
            "care_manager": [QueryIntent.RESIDENT_MANAGEMENT, QueryIntent.DASHBOARD_DATA, QueryIntent.CARE_PLANNING],
            "administrator": [QueryIntent.DASHBOARD_DATA, QueryIntent.CRISIS_MANAGEMENT, QueryIntent.WELLNESS_ALERTS],
            "resident": [QueryIntent.CONVERSATION_HISTORY, QueryIntent.CARE_PLANNING],
            "family_member": [QueryIntent.CONVERSATION_HISTORY, QueryIntent.WELLNESS_ALERTS]
        }
        
        return intent in role_intents.get(user_role, [QueryIntent.GENERAL_THERAPEUTIC])
    
    async def route_user_context_query(self, query_context: UserContextQuery) -> Dict[str, Any]:
        """Route query to appropriate data source based on intent and role"""
        
        if query_context.intent == QueryIntent.RESIDENT_MANAGEMENT:
            return await self._query_user_residents(query_context)
        elif query_context.intent == QueryIntent.WELLNESS_ALERTS:
            return await self._query_wellness_alerts(query_context)
        elif query_context.intent == QueryIntent.DASHBOARD_DATA:
            return await self._query_user_dashboard(query_context)
        elif query_context.intent == QueryIntent.CONVERSATION_HISTORY:
            return await self._query_conversation_history(query_context)
        elif query_context.intent == QueryIntent.CRISIS_MANAGEMENT:
            return await self._query_crisis_data(query_context)
        elif query_context.intent == QueryIntent.CARE_PLANNING:
            return await self._query_care_plans(query_context)
        else:
            # Fall back to general therapeutic search
            return {"intent": "general", "use_therapeutic_search": True}
    
    async def _query_user_residents(self, query_context: UserContextQuery) -> Dict[str, Any]:
        """Query residents assigned to this user"""
        if not self.postgres_manager:
            return {"error": "Database not available"}
            
        try:
            async with self.postgres_manager.get_session() as session:
                
                if query_context.user_role in ["care_staff", "care_physician"]:
                    # Get residents assigned to this staff member
                    sql = text("""
                    SELECT 
                        r.room_number,
                        u.full_name as resident_name,
                        r.care_level,
                        r.medical_conditions,
                        r.emergency_contacts,
                        w.loneliness_score,
                        w.overall_wellness_score,
                        w.mood_score,
                        w.social_engagement_score
                    FROM demo_v1_app.residents r
                    JOIN demo_v1_auth.users u ON r.user_id = u.id
                    LEFT JOIN demo_v1_memory.wellness_metrics w ON r.user_id = w.user_id 
                        AND w.metric_date = CURRENT_DATE
                    WHERE u.role = 'resident'
                    AND EXISTS (
                        SELECT 1 FROM demo_v1_auth.users staff 
                        WHERE staff.id = :user_id 
                        AND (staff.role = 'care_staff' OR staff.role = 'care_physician')
                    )
                    ORDER BY w.overall_wellness_score ASC NULLS LAST, r.room_number
                    """)
                    
                    result = await session.execute(sql, {"user_id": query_context.user_id})
                    residents = result.fetchall()
                    
                    return {
                        "intent": "resident_management",
                        "residents": [dict(r._mapping) for r in residents],
                        "count": len(residents),
                        "user_role": query_context.user_role
                    }
                
                elif query_context.user_role == "care_manager":
                    # Get member analytics for care manager
                    sql = text("""
                    SELECT 
                        u.full_name,
                        u.demo_persona_data->>'members_at_risk' as at_risk_count,
                        u.demo_persona_data->>'intervention_success_rate' as success_rate,
                        u.demo_persona_data->>'caseload_size' as total_members
                    FROM demo_v1_auth.users u
                    WHERE u.id = :user_id AND u.role = 'care_physician'
                    """)
                    
                    result = await session.execute(sql, {"user_id": query_context.user_id})
                    manager_data = result.fetchone()
                    
                    return {
                        "intent": "member_management",
                        "manager_data": dict(manager_data._mapping) if manager_data else None,
                        "user_role": query_context.user_role
                    }
                    
        except Exception as e:
            logger.error(f"❌ Failed to query user residents: {e}")
            return {"error": f"Database query failed: {e}"}
    
    async def _query_wellness_alerts(self, query_context: UserContextQuery) -> Dict[str, Any]:
        """Query wellness alerts for this user's residents"""
        if not self.postgres_manager:
            return {"error": "Database not available"}
            
        try:
            async with self.postgres_manager.get_session() as session:
                # Get residents needing attention
                sql = text("""
                SELECT 
                    u.full_name as resident_name,
                    r.room_number,
                    w.loneliness_score,
                    w.overall_wellness_score,
                    w.mood_score,
                    w.social_engagement_score,
                    w.metric_date
                FROM demo_v1_memory.wellness_metrics w
                JOIN demo_v1_auth.users u ON w.user_id = u.id
                JOIN demo_v1_app.residents r ON w.user_id = r.user_id
                WHERE (w.loneliness_score > 7 OR w.overall_wellness_score < 4 OR w.mood_score < 4)
                AND w.metric_date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY w.overall_wellness_score ASC, w.metric_date DESC
                LIMIT 10
                """)
                
                result = await session.execute(sql)
                alerts = result.fetchall()
                
                return {
                    "intent": "wellness_alerts",
                    "alerts": [dict(alert._mapping) for alert in alerts],
                    "count": len(alerts),
                    "user_role": query_context.user_role
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to query wellness alerts: {e}")
            return {"error": f"Wellness query failed: {e}"}
    
    async def _query_user_dashboard(self, query_context: UserContextQuery) -> Dict[str, Any]:
        """Query dashboard metrics for this user"""
        if not self.postgres_manager:
            return {"error": "Database not available"}
            
        try:
            async with self.postgres_manager.get_session() as session:
                # Get user's dashboard data from persona
                sql = text("""
                SELECT 
                    u.full_name,
                    u.role,
                    u.demo_persona_data
                FROM demo_v1_auth.users u
                WHERE u.id = :user_id
                """)
                
                result = await session.execute(sql, {"user_id": query_context.user_id})
                user_data = result.fetchone()
                
                if user_data:
                    return {
                        "intent": "dashboard_data", 
                        "user_metrics": dict(user_data._mapping),
                        "user_role": query_context.user_role
                    }
                
        except Exception as e:
            logger.error(f"❌ Failed to query user dashboard: {e}")
            return {"error": f"Dashboard query failed: {e}"}
    
    async def _query_conversation_history(self, query_context: UserContextQuery) -> Dict[str, Any]:
        """Query recent conversation history for this user"""
        # This would typically query ScyllaDB, but for demo we'll query PostgreSQL
        return {"intent": "conversation_history", "implementation": "pending"}
    
    async def _query_crisis_data(self, query_context: UserContextQuery) -> Dict[str, Any]:
        """Query crisis management data for this user"""
        return {"intent": "crisis_management", "implementation": "pending"}
    
    async def _query_care_plans(self, query_context: UserContextQuery) -> Dict[str, Any]:
        """Query care plan data for this user"""
        return {"intent": "care_planning", "implementation": "pending"}