"""Redis data models for caching, sessions, and analytics"""

import uuid
import json
import logging
from typing import Dict, List, Optional, Any
import time
from datetime import datetime, timezone
from dataclasses import dataclass

from app.database.redis_connection import get_redis
from app.config import config

logger = logging.getLogger(__name__)


@dataclass
class CacheKey:
    """Redis key management"""

    prefix: str
    identifier: str

    def __str__(self) -> str:
        return f"{self.prefix}:{self.identifier}"


class RedisBaseModel:
    """Base class for Redis data operations"""

    def __init__(self, key_prefix: str):
        self.key_prefix = key_prefix
        self.redis = get_redis()

    def _make_key(self, identifier: str) -> str:
        """Create Redis key with prefix"""
        return f"{self.key_prefix}:{identifier}"

    @staticmethod
    def _serialize(data: Any) -> str:
        """Serialize data for Redis storage"""
        if isinstance(data, (dict, list)):
            return json.dumps(data, default=str)
        return str(data)

    @staticmethod
    def _deserialize(data: str) -> Any:
        """Deserialize data from Redis"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data


class CacheModel(RedisBaseModel):
    """FAQ response caching model"""

    def __init__(self):
        super().__init__("cache:faq")

    def set_response(
        self, question_hash: str, response: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Cache FAQ response"""
        try:
            key = self._make_key(question_hash)
            ttl = ttl or config.redis.default_cache_ttl

            cache_data = {
                "response": response,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "ttl": ttl,
            }

            return self.redis.setex(key, ttl, self._serialize(cache_data))
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")
            return False

    def get_response(self, question_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached FAQ response"""
        try:
            key = self._make_key(question_hash)
            cached_data = self.redis.get(key)

            if cached_data:
                return self._deserialize(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve cached response: {e}")
            return None

    def invalidate_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate cache entries"""
        try:
            if pattern:
                keys = self.redis.keys(f"{self.key_prefix}:{pattern}")
            else:
                keys = self.redis.keys(f"{self.key_prefix}:*")

            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0

    def cache_with_metadata(
        self,
        question_hash: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None,
        tags: List[str] = None,
    ) -> bool:
        """Cache response with metadata and tags"""
        try:
            key = self._make_key(question_hash)
            ttl = ttl or config.redis.default_cache_ttl
            tags = tags or []

            cache_data = {
                "response": response,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "ttl": ttl,
                "tags": tags,
                "access_count": 0,
            }

            success = self.redis.setex(key, ttl, self._serialize(cache_data))

            if tags and success:
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    self.redis.sadd(tag_key, key)
                    self.redis.expire(tag_key, ttl + 300)

            return success
        except Exception as e:
            logger.error(f"Failed to cache response with metadata: {e}")
            return False

    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cached items with a specific tag"""
        try:
            tag_key = f"tag:{tag}"
            keys = self.redis.smembers(tag_key)
            if keys:
                deleted = self.redis.delete(*keys)
                self.redis.delete(tag_key)
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate by tag: {e}")
            return 0


class SessionModel(RedisBaseModel):
    """User session management model"""

    def __init__(self):
        super().__init__("session:user")

    def create_session(self, session_id: str, user_data: Dict[str, Any]) -> bool:
        """Create user session"""
        try:
            key = self._make_key(session_id)
            session_data = {
                "user_data": user_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "chat_history": [],
            }

            return self.redis.setex(
                key, config.redis.session_ttl, self._serialize(session_data)
            )
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user session"""
        try:
            key = self._make_key(session_id)
            session_data = self.redis.get(key)

            if session_data:
                data = self._deserialize(session_data)
                data["last_activity"] = datetime.now(timezone.utc).isoformat()
                self.redis.setex(key, config.redis.session_ttl, self._serialize(data))
                return data
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve session: {e}")
            return None

    def add_to_chat_history(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add message to chat history"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False

            chat_history = session.get("chat_history", [])
            chat_history.append(
                {**message, "timestamp": datetime.now(timezone.utc).isoformat()}
            )

            if len(chat_history) > config.max_chat_history:
                chat_history = chat_history[-config.max_chat_history :]

            session["chat_history"] = chat_history

            key = self._make_key(session_id)
            return self.redis.setex(
                key, config.redis.session_ttl, self._serialize(session)
            )
        except Exception as e:
            logger.error(f"Failed to add to chat history: {e}")
            return False


class AnalyticsModel(RedisBaseModel):
    """Real-time analytics model"""

    def __init__(self):
        super().__init__("analytics")

    def increment_counter(self, metric: str, value: int = 1) -> int:
        """Increment analytics counter"""
        try:
            key = self._make_key(f"counter:{metric}")
            return self.redis.incr(key, value)
        except Exception as e:
            logger.error(f"Failed to increment counter: {e}")
            return 0

    def record_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Record analytics event"""
        try:
            timestamp = datetime.now(timezone.utc)
            event_key = f"event:{event_type}:{timestamp.strftime('%Y%m%d')}"
            key = self._make_key(event_key)

            event_record = {"timestamp": timestamp.isoformat(), "data": event_data}

            self.redis.lpush(key, self._serialize(event_record))
            self.redis.expire(key, config.redis.analytics_ttl)

            return True
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
            return False


class PopularityTracker(RedisBaseModel):
    """Track popular questions using Redis Sorted Sets"""

    def __init__(self):
        super().__init__("popular")

    def increment_question_popularity(self, question_hash: str, increment: float = 1.0):
        """Track question popularity"""
        current_time = time.time()

        day_key = f"day:{int(current_time // 86400)}"
        key = self._make_key(day_key)
        self.redis.zincrby(key, increment, question_hash)
        self.redis.expire(key, 172800)

        all_time_key = self._make_key("all")
        self.redis.zincrby(all_time_key, increment * 0.1, question_hash)

    def get_trending_questions(self, limit: int = 10) -> List[tuple]:
        """Get trending questions from today"""
        current_day = int(time.time() // 86400)
        day_key = self._make_key(f"day:{current_day}")
        return self.redis.zrevrange(day_key, 0, limit - 1, withscores=True)


class NotificationModel(RedisBaseModel):
    """User-specific notification queue using Redis Lists"""

    def __init__(self):
        super().__init__("notifications:user")

    def add_notification(self, user_id: str, notification: Dict[str, Any]) -> bool:
        """Add notification to user's queue"""
        try:
            key = self._make_key(user_id)

            notification_data = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": notification.get("type", "info"),
                "title": notification["title"],
                "message": notification["message"],
                "data": notification.get("data", {}),
                "read": False,
            }

            self.redis.lpush(key, self._serialize(notification_data))
            self.redis.ltrim(key, 0, 49)
            self.redis.expire(key, 604800)

            logger.info(
                f"Notification added for user {user_id}: {notification['title']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add notification for user {user_id}: {e}")
            return False

    def get_notifications(self, user_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get and remove notifications from user's queue"""
        try:
            key = self._make_key(user_id)
            notifications = []

            for _ in range(count):
                notification_data = self.redis.rpop(key)
                if not notification_data:
                    break

                notification = self._deserialize(notification_data)
                notifications.append(notification)

            logger.debug(
                f"Retrieved {len(notifications)} notifications for user {user_id}"
            )
            return notifications

        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {e}")
            return []

    def count_notifications(self, user_id: str) -> int:
        """Count pending notifications for user"""
        try:
            key = self._make_key(user_id)
            count = self.redis.llen(key)
            return count
        except Exception as e:
            logger.error(f"Failed to count notifications for user {user_id}: {e}")
            return 0

    def peek_notifications(self, user_id: str, count: int = 5) -> List[Dict[str, Any]]:
        """Preview notifications without removing them"""
        try:
            key = self._make_key(user_id)
            notification_strings = self.redis.lrange(key, -count, -1)

            notifications = []
            for notification_data in reversed(notification_strings):
                notification = self._deserialize(notification_data)
                notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"Failed to peek notifications for user {user_id}: {e}")
            return []

    def clear_notifications(self, user_id: str) -> int:
        """Clear all notifications for user"""
        try:
            key = self._make_key(user_id)
            count = self.redis.llen(key)
            self.redis.delete(key)

            logger.info(f"Cleared {count} notifications for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Failed to clear notifications for user {user_id}: {e}")
            return 0


class BillingCacheModel(RedisBaseModel):
    """Billing-specific caching model"""

    def __init__(self):
        super().__init__("billing")

    async def cache_subscription(
        self,
        user_id: str,
        subscription: Any,
        ttl: int = 300,  # 5 minutes
    ) -> bool:
        """Cache user subscription"""
        try:
            key = self._make_key(f"subscription:{user_id}")

            # Convert SQLAlchemy object to dict
            sub_data = {
                "id": str(subscription.id),
                "plan_type": subscription.plan_type,
                "status": subscription.status,
                "billing_cycle": subscription.billing_cycle,
                "started_at": subscription.started_at.isoformat(),
                "ends_at": subscription.ends_at.isoformat()
                if subscription.ends_at
                else None,
                "auto_renew": subscription.auto_renew,
                "limits": subscription.limits,
                "amount_cents": subscription.amount_cents,
                "currency": subscription.currency,
            }

            return self.redis.setex(key, ttl, self._serialize(sub_data))
        except Exception as e:
            logger.error(f"Failed to cache subscription: {e}")
            return False

    async def get_cached_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached subscription"""
        try:
            key = self._make_key(f"subscription:{user_id}")
            cached_data = self.redis.get(key)

            if cached_data:
                return self._deserialize(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached subscription: {e}")
            return None

    async def cache_quota(
        self,
        user_id: str,
        resource_type: str,
        quota_info: Dict[str, Any],
        ttl: int = 60,  # 1 minute
    ) -> bool:
        """Cache quota information"""
        try:
            key = self._make_key(f"quota:{user_id}:{resource_type}")
            return self.redis.setex(key, ttl, self._serialize(quota_info))
        except Exception as e:
            logger.error(f"Failed to cache quota: {e}")
            return False

    async def get_cached_quota(
        self, user_id: str, resource_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached quota information"""
        try:
            key = self._make_key(f"quota:{user_id}:{resource_type}")
            cached_data = self.redis.get(key)

            if cached_data:
                return self._deserialize(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached quota: {e}")
            return None

    async def cache_usage_summary(
        self,
        user_id: str,
        summary: Dict[str, Any],
        ttl: int = 300,  # 5 minutes
    ) -> bool:
        """Cache usage summary"""
        try:
            key = self._make_key(f"usage_summary:{user_id}")
            return self.redis.setex(key, ttl, self._serialize(summary))
        except Exception as e:
            logger.error(f"Failed to cache usage summary: {e}")
            return False

    async def get_cached_usage_summary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached usage summary"""
        try:
            key = self._make_key(f"usage_summary:{user_id}")
            cached_data = self.redis.get(key)

            if cached_data:
                return self._deserialize(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached usage summary: {e}")
            return None

    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all billing cache for a user"""
        try:
            patterns = [
                f"subscription:{user_id}",
                f"quota:{user_id}:*",
                f"usage_summary:{user_id}",
            ]

            deleted = 0
            for pattern in patterns:
                keys = self.redis.keys(f"{self.key_prefix}:{pattern}")
                if keys:
                    deleted += self.redis.delete(*keys)

            return deleted
        except Exception as e:
            logger.error(f"Failed to invalidate user cache: {e}")
            return 0

    async def invalidate_quota_cache(self, user_id: str, resource_type: str) -> bool:
        """Invalidate specific quota cache"""
        try:
            key = self._make_key(f"quota:{user_id}:{resource_type}")
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Failed to invalidate quota cache: {e}")
            return False
