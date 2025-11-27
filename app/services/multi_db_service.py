import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import re
import logging

from app.database.postgres_connection import postgres_manager
from app.database.postgres_models import User, AuditLog
from app.database.redis_models import CacheModel, SessionModel, AnalyticsModel
from app.database.scylla_models import ConversationHistory

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.auth_service import AuthService
    from app.services.billing_service import EnhancedBillingService

logger = logging.getLogger(__name__)


class MultiDatabaseService:
    """Coordinates operations across PostgreSQL, Redis, and ScyllaDB."""

    def __init__(
        self,
        auth_service: Optional["AuthService"] = None,
        billing_service: Optional["EnhancedBillingService"] = None,
    ):
        self.auth_service = auth_service
        self.billing_service = billing_service
        # Database connections
        self.cache_model = CacheModel()
        self.session_model = SessionModel()
        self.analytics_model = AnalyticsModel()
        self.conversation_history = ConversationHistory()

    async def process_user_message_with_auth(
        self, session_id: str, user_message: str, user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process user message with full three-database integration."""
        # 1. POSTGRESQL: Authenticate user if token provided
        user = None
        if user_token:
            token_payload = await self.auth_service.verify_token(user_token)
            if token_payload:
                user_id = token_payload.get("user_id")
                user = await self.auth_service.get_user_by_id(uuid.UUID(user_id))

                if user and not user.is_active:
                    raise PermissionError("User account is inactive")

        # 2. REDIS: Check rate limits if user is authenticated
        if user:
            await self._check_user_rate_limits(user)

        # 3. REDIS: Get/create session with user context
        session_data = self.session_model.get_session(session_id)
        if not session_data:
            user_context = (
                {"user_id": str(user.id)} if user else {"user_type": "anonymous"}
            )
            self.session_model.create_session(session_id, user_context)

        # 4. REDIS: Check cache for response
        cached_response = await self._check_message_cache(user_message)
        if cached_response:
            # Record cache hit analytics
            self.analytics_model.increment_counter("cache_hits")
            if user:
                await self._record_usage(user, "cached_message")
            return cached_response

        # 5. Generate response (this would call your existing chatbot logic)
        response = await self._generate_response(user_message)

        # 6. SCYLLADB: Store conversation for persistence
        session_uuid = uuid.UUID(session_id) if session_id else uuid.uuid4()
        await self.conversation_history.save_message(session_uuid, "user", user_message)
        await self.conversation_history.save_message(
            session_uuid, "bot", response["message"]
        )

        # 7. REDIS: Cache the response
        await self._cache_response(user_message, response)

        # 8. POSTGRESQL: Record usage and audit if user is authenticated
        if user:
            await self._record_usage(user, "message_processed")
            await self._log_user_activity(
                user, "message_sent", {"message_length": len(user_message)}
            )

        # 9. REDIS: Update session activity
        self.session_model.add_to_chat_history(
            session_id, {"actor": "user", "message": user_message}
        )
        self.session_model.add_to_chat_history(
            session_id, {"actor": "bot", "message": response["message"]}
        )

        return response

    async def start_background_task_with_auth(
        self, user_token: str, task_type: str, task_data: Dict[str, Any]
    ) -> str:
        """Start background task with full authentication and quota checking."""
        # 1. POSTGRESQL: Authenticate and authorize user
        token_payload = await self.auth_service.verify_token(user_token)
        if not token_payload:
            raise PermissionError("Invalid authentication token")

        user = await self.auth_service.get_user_by_id(
            uuid.UUID(token_payload["user_id"])
        )
        if not user or not user.is_active:
            raise PermissionError("User not authorized for background tasks")

        # 2. POSTGRESQL: Check usage quotas
        await self._check_background_task_quota(user)

        # 3. REDIS: Queue the background task (integrate with your existing background_tasks service)
        task_id = str(uuid.uuid4())

        # 4. POSTGRESQL: Record task initiation
        await self._record_usage(user, "background_task_started")
        await self._log_user_activity(
            user,
            "background_task_initiated",
            {"task_id": task_id, "task_type": task_type},
        )

        logger.info(f"Background task {task_id} started for user {user.email}")
        return task_id

    async def get_user_dashboard_data(self, user_token: str) -> Dict[str, Any]:
        """Get comprehensive user dashboard data from all three databases."""
        # 1. POSTGRESQL: Get user and subscription info
        token_payload = await self.auth_service.verify_token(user_token)
        if not token_payload:
            raise PermissionError("Invalid authentication token")

        user = await self.auth_service.get_user_by_id(
            uuid.UUID(token_payload["user_id"])
        )
        if not user:
            raise ValueError("User not found")

        # 2. POSTGRESQL: Get usage statistics
        usage_stats = await self._get_user_usage_stats(user)

        # 3. REDIS: Get session information
        session_stats = self._get_user_session_stats(str(user.id))

        # 4. SCYLLADB: Get conversation statistics (simplified for this example)
        conversation_stats = {"total_conversations": 0, "recent_activity": []}

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "subscription_plan": user.subscription_plan,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            },
            "usage": usage_stats,
            "sessions": session_stats,
            "conversations": conversation_stats,
        }

    # ===== PRIVATE HELPER METHODS =====

    async def _check_user_rate_limits(self, user: User) -> None:
        """Check if user has exceeded rate limits"""
        # Implementation would check Redis rate limiting
        pass

    async def _check_message_cache(self, message: str) -> Optional[Dict[str, Any]]:
        """Check Redis cache for message response"""
        import hashlib

        message_hash = hashlib.md5(message.lower().encode()).hexdigest()
        return self.cache_model.get_response(message_hash)

    async def _generate_response(self, message: str) -> Dict[str, Any]:
        """Generate chatbot response (integrate with your existing logic)"""
        # This would integrate with your existing chatbot_service response generation
        return {
            "message": f"Response to: {message}",
            "confidence": 0.8,
            "cached": False,
        }

    async def _cache_response(self, message: str, response: Dict[str, Any]) -> None:
        """Cache response in Redis"""
        import hashlib

        message_hash = hashlib.md5(message.lower().encode()).hexdigest()
        self.cache_model.set_response(message_hash, response)

    async def _record_usage(self, user: User, resource_type: str) -> None:
        """Record usage in PostgreSQL for billing"""
        success = await self.billing_service.record_usage(
            user=user,
            resource_type=resource_type,
            quantity=1,
            extra_data={"timestamp": datetime.now(timezone.utc).isoformat()},
        )

        if not success:
            logger.warning(f"Failed to record usage for user {user.email}")

    async def _log_user_activity(
        self, user: User, action: str, metadata: Dict[str, Any]
    ) -> None:
        """Log user activity for audit trail"""
        async with postgres_manager.get_session() as session:
            audit_log = AuditLog(
                user_id=user.id,
                action=action,
                resource_type="user_activity",
                new_values=metadata,
            )
            session.add(audit_log)

    async def _check_background_task_quota(self, user: User) -> None:
        """Check if user can start background tasks"""
        quota_info = await self.billing_service.check_user_quota(
            user, "background_tasks"
        )

        if not quota_info["has_quota"]:
            raise PermissionError(
                f"Background task quota exceeded. Used {quota_info['current_usage']}/{quota_info['max_allowed']} "
                f"for your {user.subscription_plan} plan. Upgrade for more tasks."
            )

    async def _get_user_usage_stats(self, user: User) -> Dict[str, Any]:
        """Get user usage statistics from PostgreSQL"""
        return await self.billing_service.get_usage_summary(user)

    def _get_user_session_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user session statistics from Redis"""
        # Implementation would query Redis for session data
        return {
            "active_sessions": 1,
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }


def _norm_txt(s: Optional[str]) -> str:
    return (s or "").strip()


def _to_iso(dt) -> Optional[str]:
    try:
        # Accept str, datetime, or anything with isoformat()
        if hasattr(dt, "isoformat"):
            return dt.isoformat()
        if isinstance(dt, str):
            return dt
    except Exception:
        pass
    return None


def _normalize_faq_row(item: Any) -> Dict[str, Any]:
    """
    Accept either a dict-ish object or a model with attributes and produce a normalized row:
      {scylla_key, question, answer, updated_at?, version?}
    """
    if isinstance(item, dict):
        scylla_key = item.get("scylla_key") or item.get("id") or item.get("key")
        question = item.get("question") or item.get("q") or item.get("title")
        answer = item.get("answer") or item.get("a") or item.get("content")
        updated_at = item.get("updated_at") or item.get("modified_at") or item.get("ts")
        version = item.get("version")
    else:
        # attribute-style access
        scylla_key = (
            getattr(item, "scylla_key", None)
            or getattr(item, "id", None)
            or getattr(item, "key", None)
        )
        question = getattr(item, "question", None) or getattr(item, "title", None)
        answer = getattr(item, "answer", None) or getattr(item, "content", None)
        updated_at = (
            getattr(item, "updated_at", None)
            or getattr(item, "modified_at", None)
            or getattr(item, "ts", None)
        )
        version = getattr(item, "version", None)

    return {
        "scylla_key": _norm_txt(str(scylla_key) if scylla_key is not None else ""),
        "question": _norm_txt(question),
        "answer": _norm_txt(answer),
        "updated_at": _to_iso(updated_at),
        "version": version,
    }


async def _kb_list(limit: Optional[int]) -> List[Dict[str, Any]]:
    """
    Try several common method names on a KnowledgeBase repository.
    Convert results to a uniform dict shape.
    """
    try:
        from app.database.scylla_models import KnowledgeBase  # your repo/model
    except Exception as e:
        logger.debug("KnowledgeBase not available: %s", e)
        return []

    kb = KnowledgeBase()
    # Try async then sync variants
    candidates = [
        ("list_faqs_async", True),
        ("list_faqs", False),
        ("get_all_faqs_async", True),
        ("get_all_faqs", False),
        ("fetch_all_async", True),
        ("fetch_all", False),
    ]

    for name, is_async in candidates:
        if hasattr(kb, name):
            try:
                if is_async:
                    rows = await getattr(kb, name)(limit=limit)
                else:
                    rows = getattr(kb, name)(limit=limit)
                return [_normalize_faq_row(r) for r in (rows or [])]
            except TypeError:
                # Some repos use positional `limit` or no limit at all
                try:
                    if is_async:
                        rows = await getattr(kb, name)(limit)
                    else:
                        rows = getattr(kb, name)(limit)
                    return [_normalize_faq_row(r) for r in (rows or [])]
                except Exception as e:
                    logger.warning("KnowledgeBase.%s call failed: %s", name, e)
            except Exception as e:
                logger.warning("KnowledgeBase.%s call failed: %s", name, e)

    logger.info("No suitable KnowledgeBase list method found.")
    return []


def _score_exactish(query: str, question: str, answer: str) -> float:
    """
    Cheap exact/keyword-ish score:
      - full-string containment gets a big bump
      - token overlap (Jaccard-like) as a base
    """
    q = query.lower().strip()
    if not q:
        return 0.0
    q_tokens = set(re.findall(r"[a-z0-9]+", q))
    qa = (question or "") + " " + (answer or "")
    text = qa.lower()
    t_tokens = set(re.findall(r"[a-z0-9]+", text))

    if q in text:
        bump = 0.6
    else:
        bump = 0.0

    if not q_tokens or not t_tokens:
        return bump

    overlap = len(q_tokens & t_tokens)
    union = len(q_tokens | t_tokens)
    base = (overlap / union) if union else 0.0
    return min(1.0, base + bump)


async def get_faq_seed_rows(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return FAQ data for seeding. Since we don't have Scylla connected,
    return some sample data for testing.
    """
    sample_faqs = [
        {
            "scylla_key": "faq:reset_password",
            "question": "How do I reset my password?",
            "answer": "Go to Settings → Security → Reset Password and follow the instructions.",
            "updated_at": "2025-08-08T12:00:00Z",
            "version": 1,
        },
        {
            "scylla_key": "faq:contact_support",
            "question": "How do I contact support?",
            "answer": "You can reach our support team via email at support@company.com or through the help desk.",
            "updated_at": "2025-08-08T12:00:00Z",
            "version": 1,
        },
        {
            "scylla_key": "faq:refund_policy",
            "question": "What is the refund policy?",
            "answer": "We offer full refunds within 30 days of purchase. Contact support to initiate a refund.",
            "updated_at": "2025-08-08T12:00:00Z",
            "version": 1,
        },
    ]

    if limit is not None and limit > 0:
        return sample_faqs[:limit]
    return sample_faqs


async def scylla_exact_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Exact/keyword path used by KnowledgeService for 'exact' route.
    Prefers a KnowledgeBase.search_* method if present; otherwise does a
    simple in-memory exact/keyword ranking over the FAQ list.
    Returns a list of normalized hits:
      { type: 'faq', source: 'scylla', scylla_key, question, answer, score }
    """
    # 1) Try dedicated search methods
    try:
        from app.database.scylla_models import KnowledgeBase

        kb = KnowledgeBase()
        search_variants = [
            ("search_exact_async", True),
            ("search_exact", False),
            ("search_faqs_async", True),
            ("search_faqs", False),
            ("search_async", True),
            ("search", False),
        ]
        for name, is_async in search_variants:
            if hasattr(kb, name):
                try:
                    if is_async:
                        hits = await getattr(kb, name)(query, top_k)
                    else:
                        hits = getattr(kb, name)(query, top_k)
                    out = []
                    for h in hits or []:
                        row = _normalize_faq_row(h)
                        if not row.get("scylla_key"):
                            continue
                        out.append(
                            {
                                "type": "faq",
                                "source": "scylla",
                                "scylla_key": row["scylla_key"],
                                "question": row["question"],
                                "answer": row["answer"],
                                "score": 1.0,  # repo-defined exact hits assumed
                            }
                        )
                    if out:
                        return out[:top_k]
                except Exception as e:
                    logger.warning("KnowledgeBase.%s failed, falling back: %s", name, e)
    except Exception as e:
        logger.debug("KnowledgeBase not available for exact search: %s", e)

    # 2) Fallback: pull a list and rank locally
    rows = await _kb_list(limit=None)
    if not rows:
        return []

    scored = []
    for r in rows:
        score = _score_exactish(query, r.get("question", ""), r.get("answer", ""))
        if score > 0:
            scored.append(
                (
                    score,
                    {
                        "type": "faq",
                        "source": "scylla",
                        "scylla_key": r.get("scylla_key"),
                        "question": r.get("question"),
                        "answer": r.get("answer"),
                        "score": float(score),
                    },
                )
            )
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[: max(1, top_k)]]


# Optional export hint for static importers
__all__ = ["get_faq_seed_rows", "scylla_exact_search"]


# Global multi-database service instance
multi_db_service: Optional[MultiDatabaseService] = None


def get_multi_db_service() -> "MultiDatabaseService":
    global multi_db_service
    if multi_db_service is None:
        multi_db_service = MultiDatabaseService()
    return multi_db_service
