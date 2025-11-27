"""Enhanced Billing and subscription management service"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import logging

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres_models import User, Subscription, UsageRecord
from app.database.redis_models import BillingCacheModel

logger = logging.getLogger(__name__)


class EnhancedBillingService:
    """Enhanced billing and subscription management service with caching."""

    def __init__(self):
        self.cache = BillingCacheModel()
        self._plan_definitions = self._load_plan_definitions()

    def _load_plan_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load subscription plan definitions"""
        return {
            "free": {
                "name": "Free Plan",
                "limits": {
                    "messages": 10,
                    "background_tasks": 5,
                    "api_calls": 20,
                    "storage_mb": 100,
                },
                "features": [
                    "Basic chat functionality",
                    "Standard response time",
                    "Community support",
                ],
                "pricing": {"monthly": 0, "yearly": 0},
            },
            "pro": {
                "name": "Pro Plan",
                "limits": {
                    "messages": 1000,
                    "background_tasks": 50,
                    "api_calls": 500,
                    "storage_mb": 1000,
                },
                "features": [
                    "Advanced chat features",
                    "Priority response time",
                    "Email support",
                    "Custom integrations",
                ],
                "pricing": {
                    "monthly": 2900,  # $29.00 in cents
                    "yearly": 29000,  # $290.00 in cents (2 months free)
                },
            },
            "enterprise": {
                "name": "Enterprise Plan",
                "limits": {
                    "messages": 10000,
                    "background_tasks": 1000,
                    "api_calls": 50000,
                    "storage_mb": 10000,
                },
                "features": [
                    "Unlimited chat features",
                    "Instant response time",
                    "24/7 phone support",
                    "Custom integrations",
                    "Dedicated account manager",
                    "SLA guarantee",
                ],
                "pricing": {
                    "monthly": 9900,  # $99.00 in cents
                    "yearly": 99000,  # $990.00 in cents (2 months free)
                },
            },
        }

    async def get_active_subscription(
        self, user: User, session: AsyncSession
    ) -> Optional[Subscription]:
        """Get user's active subscription"""
        try:
            # Check cache first
            cached = await self.cache.get_cached_subscription(str(user.id))
            if cached:
                return cached

            # Query database
            stmt = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user.id,
                        Subscription.status.in_(["active", "trialing"]),
                    )
                )
                .order_by(Subscription.created_at.desc())
            )

            result = await session.execute(stmt)
            subscription = result.scalar_one_or_none()

            if not subscription:
                # Create subscription based on user's subscription_plan field
                subscription = await self.create_default_subscription(user, session)

            # Cache the result
            if subscription:
                await self.cache.cache_subscription(str(user.id), subscription)

            return subscription

        except Exception as e:
            logger.error(f"Failed to get active subscription: {e}")
            return None

    async def create_default_subscription(
        self, user: User, session: AsyncSession
    ) -> Subscription:
        """Create default free subscription for new user"""
        try:
            plan_type = user.subscription_plan or "free"

            plan_def = self._plan_definitions.get(
                plan_type, self._plan_definitions["free"]
            )

            subscription = Subscription(
                user_id=user.id,
                plan_type=plan_type,
                status="active",
                billing_cycle="monthly",
                amount_cents=plan_def["pricing"]["monthly"],
                currency="USD",
                started_at=datetime.now(timezone.utc),
                auto_renew=True,
                limits=plan_def["limits"],
            )

            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)

            # Clear cache
            await self.cache.invalidate_user_cache(str(user.id))

            logger.info(f"Created {plan_type} subscription for user {user.email}")
            return subscription

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create default subscription: {e}")
            raise

    async def create_subscription(
        self, user: User, plan_type: str, billing_cycle: str, session: AsyncSession
    ) -> Optional[Subscription]:
        """Create a new subscription for a user - FIXED method added."""
        try:
            plan_def = self._plan_definitions.get(
                plan_type, self._plan_definitions["free"]
            )

            subscription = Subscription(
                user_id=user.id,
                plan_type=plan_type,
                status="active",
                billing_cycle=billing_cycle,
                amount_cents=plan_def["pricing"][billing_cycle],
                currency="USD",
                started_at=datetime.now(timezone.utc),
                auto_renew=True,
                limits=plan_def["limits"],
            )

            # Update user's plan
            user.subscription_plan = plan_type

            session.add(subscription)
            session.add(user)
            await session.commit()
            await session.refresh(subscription)

            # Clear cache
            await self.cache.invalidate_user_cache(str(user.id))

            logger.info(f"Created {plan_type} subscription for user {user.email}")
            return subscription

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create subscription: {e}")
            return None

    async def can_change_plan(
        self, user: User, new_plan: str, session: AsyncSession
    ) -> tuple[bool, str]:
        """Check if user can change to a new plan"""
        try:
            # Get current subscription
            current_sub = await self.get_active_subscription(user, session)
            if not current_sub:
                return True, "No active subscription"

            # Handle both dict (from cache) and object (from DB)
            if isinstance(current_sub, dict):
                current_plan = current_sub.get("plan_type", "free")
                status = current_sub.get("status", "active")
            else:
                current_plan = current_sub.plan_type
                status = current_sub.status

            # Check if subscription is active
            if status != "active":
                return False, "Subscription is not active"

            # Check if it's the same plan
            if current_plan == new_plan:
                return False, "Already on this plan"

            # Check if downgrade is allowed
            if self._is_downgrade(current_plan, new_plan):
                # Check if there are pending charges or usage over new plan limits
                # For now, allow all downgrades
                pass

            return True, "Plan change allowed"

        except Exception as e:
            logger.error(f"Failed to check plan change eligibility: {e}")
            return False, str(e)

    async def update_subscription_plan(
        self, user: User, new_plan: str, billing_cycle: str, session: AsyncSession
    ) -> Optional[Subscription]:
        """Update a user's subscription plan - FIXED to handle cached objects."""
        try:
            # FIXED: Always fetch a fresh subscription from the database
            # Don't rely on get_active_subscription which might return cached data
            stmt = (
                select(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user.id,
                        Subscription.status.in_(["active", "trialing"]),
                    )
                )
                .order_by(Subscription.created_at.desc())
            )

            result = await session.execute(stmt)
            current_sub = result.scalar_one_or_none()

            if not current_sub:
                logger.warning(
                    f"No active subscription found for user {user.id} to update."
                )
                # If no subscription exists, create a new one
                return await self.create_subscription(
                    user, new_plan, billing_cycle, session
                )

            # Update the existing subscription object's attributes
            current_sub.plan_type = new_plan
            current_sub.billing_cycle = billing_cycle
            current_sub.limits = self._get_plan_limits(new_plan)
            current_sub.amount_cents = self._get_plan_price(new_plan, billing_cycle)
            current_sub.updated_at = datetime.now(timezone.utc)

            # The user's plan should also be updated to stay in sync
            user.subscription_plan = new_plan

            session.add(current_sub)
            session.add(user)
            await session.commit()
            await session.refresh(current_sub)

            # Invalidate cache after successful DB operation
            await self.cache.invalidate_user_cache(str(user.id))
            logger.info(f"Updated subscription for user {user.email} to {new_plan}")
            return current_sub

        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            await session.rollback()
            return None

    async def cancel_subscription(
        self, user: User, session: AsyncSession
    ) -> Dict[str, Any]:
        """Cancel user's subscription at end of billing period"""
        try:
            subscription = await self.get_active_subscription(user, session)

            if not subscription:
                return {"success": False, "reason": "No active subscription"}

            if subscription.plan_type == "free":
                return {"success": False, "reason": "Cannot cancel free plan"}

            # Set to cancel at period end
            subscription.status = "pending_cancellation"
            subscription.auto_renew = False

            # Calculate end date if not set
            if not subscription.ends_at:
                if subscription.billing_cycle == "monthly":
                    subscription.ends_at = subscription.started_at + timedelta(days=30)
                else:  # yearly
                    subscription.ends_at = subscription.started_at + timedelta(days=365)

            await session.commit()

            # Clear cache
            await self.cache.invalidate_user_cache(str(user.id))

            logger.info(f"Scheduled cancellation for user {user.email}")

            return {
                "success": True,
                "message": "Subscription will be cancelled at end of billing period",
                "ends_at": subscription.ends_at.isoformat(),
            }

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to cancel subscription: {e}")
            return {"success": False, "reason": str(e)}

    async def check_user_quota(
        self,
        user: User,
        resource_type: str,
        session: AsyncSession,  # FIXED: session is required
    ) -> Dict[str, Any]:
        """Check if user has quota for a resource - session parameter is required."""
        try:
            # Check cache first
            cached = await self.cache.get_cached_quota(str(user.id), resource_type)
            if cached:
                return cached

            # Get current billing period
            now = datetime.now(timezone.utc)
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Calculate period end properly
            if now.month == 12:
                period_end = datetime(
                    now.year + 1, 1, 1, tzinfo=timezone.utc
                ) - timedelta(seconds=1)
            else:
                period_end = datetime(
                    now.year, now.month + 1, 1, tzinfo=timezone.utc
                ) - timedelta(seconds=1)

            # Get usage for current period
            result = await session.execute(
                select(func.sum(UsageRecord.quantity)).where(
                    UsageRecord.user_id == user.id,
                    UsageRecord.resource_type == resource_type,
                    UsageRecord.billing_period_start >= period_start,
                    UsageRecord.billing_period_end <= period_end,
                )
            )
            current_usage = result.scalar() or 0

            # Use user's subscription_plan field directly for limits
            plan_type = user.subscription_plan or "free"
            limits = self._get_plan_limits(plan_type)
            max_allowed = limits.get(resource_type, 1000)

            has_quota = int(current_usage) < max_allowed

            quota_info = {
                "has_quota": has_quota,
                "current_usage": int(current_usage),
                "max_allowed": max_allowed,
                "remaining": max(0, max_allowed - int(current_usage)),
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            }

            # Cache the result
            await self.cache.cache_quota(
                str(user.id),
                resource_type,
                quota_info,
                ttl=300,  # 5 minutes
            )

            return quota_info

        except Exception as e:
            logger.error(f"Failed to check quota: {e}")
            # Return permissive quota on error
            return {
                "has_quota": True,
                "current_usage": 0,
                "max_allowed": 1000,
                "remaining": 1000,
                "period_start": datetime.now(timezone.utc).replace(day=1).isoformat(),
                "period_end": datetime.now(timezone.utc).isoformat(),
            }

    async def record_usage(
        self,
        user: User,
        resource_type: str,
        session: AsyncSession,  # FIXED: session is required
        quantity: int = 1,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record resource usage for billing - session parameter is required."""
        try:
            now = datetime.now(timezone.utc)
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(
                seconds=1
            )

            usage_record = UsageRecord(
                user_id=user.id,
                resource_type=resource_type,
                quantity=quantity,
                billing_period_start=period_start,
                billing_period_end=period_end,
                extra_data=extra_data or {},
            )

            session.add(usage_record)
            await session.commit()

            # Invalidate quota cache
            await self.cache.invalidate_quota_cache(str(user.id), resource_type)

            logger.debug(
                f"Recorded usage: {quantity} {resource_type} for user {user.email}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            await session.rollback()
            return False

    async def get_usage_summary(
        self,
        user: User,
        session: AsyncSession,  # FIXED: session is required
    ) -> Dict[str, Any]:
        """Get usage summary for user dashboard - session parameter is required."""
        try:
            # Check cache first
            cached_summary = await self.cache.get_cached_usage_summary(str(user.id))
            if cached_summary:
                return cached_summary

            now = datetime.now(timezone.utc)
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Calculate period end properly
            import calendar

            last_day = calendar.monthrange(now.year, now.month)[1]
            period_end = now.replace(
                day=last_day, hour=23, minute=59, second=59, microsecond=999999
            )

            # Get all usage for current period
            usage_query = (
                select(
                    UsageRecord.resource_type,
                    func.coalesce(func.sum(UsageRecord.quantity), 0).label("total"),
                )
                .where(
                    UsageRecord.user_id == user.id,
                    UsageRecord.billing_period_start >= period_start,
                    UsageRecord.billing_period_end <= period_end,
                )
                .group_by(UsageRecord.resource_type)
            )

            result = await session.execute(usage_query)
            usage_data = {}
            for row in result:
                # Safely convert to int
                total = row.total if row.total is not None else 0
                usage_data[row.resource_type] = int(total)

            # Use user's subscription_plan field directly
            plan_type = user.subscription_plan or "free"
            limits = self._get_plan_limits(plan_type)

            summary = {
                "messages_this_month": usage_data.get("messages", 0),
                "background_tasks_this_month": usage_data.get("background_tasks", 0),
                "api_calls_this_month": usage_data.get("api_calls", 0),
                "quota_remaining": max(
                    0, limits.get("messages", 0) - usage_data.get("messages", 0)
                ),
                "limits": limits,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "plan_type": plan_type,
            }

            # Cache the summary
            try:
                await self.cache.cache_usage_summary(str(user.id), summary)
            except Exception:
                pass  # Cache is optional

            return summary

        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}", exc_info=True)

            # Return safe defaults on error
            return {
                "messages_this_month": 0,
                "background_tasks_this_month": 0,
                "api_calls_this_month": 0,
                "quota_remaining": 1000,
                "limits": self._get_plan_limits(user.subscription_plan or "free"),
                "period_start": datetime.now(timezone.utc).replace(day=1).isoformat(),
                "period_end": datetime.now(timezone.utc).isoformat(),
                "plan_type": user.subscription_plan or "free",
            }

    async def get_billing_history(
        self, user: User, session: AsyncSession, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's billing history"""
        try:
            # Get all subscriptions
            stmt = (
                select(Subscription)
                .where(Subscription.user_id == user.id)
                .order_by(Subscription.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)
            subscriptions = result.scalars().all()

            # Count total
            count_stmt = (
                select(func.count())
                .select_from(Subscription)
                .where(Subscription.user_id == user.id)
            )
            total_result = await session.execute(count_stmt)
            total = total_result.scalar()

            # Format history items
            items = []
            for sub in subscriptions:
                items.append(
                    {
                        "date": sub.created_at,
                        "description": f"{sub.plan_type.title()} Plan - {sub.billing_cycle.title()}",
                        "amount_cents": sub.amount_cents,
                        "currency": sub.currency,
                        "status": sub.status,
                        "invoice_url": None,  # Would be populated with actual invoice URLs
                    }
                )

            return {"total": total, "items": items}

        except Exception as e:
            logger.error(f"Failed to get billing history: {e}")
            return {"total": 0, "items": []}

    async def get_detailed_usage(
        self,
        user: User,
        session: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        resource_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get detailed usage breakdown"""
        try:
            # Default to current month if no dates provided
            if not start_date:
                start_date = datetime.now(timezone.utc).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            if not end_date:
                end_date = datetime.now(timezone.utc)

            # Build query
            conditions = [
                UsageRecord.user_id == user.id,
                UsageRecord.created_at >= start_date,
                UsageRecord.created_at <= end_date,
            ]

            if resource_type:
                conditions.append(UsageRecord.resource_type == resource_type)

            # Get usage records
            stmt = (
                select(UsageRecord)
                .where(and_(*conditions))
                .order_by(UsageRecord.created_at.desc())
            )

            result = await session.execute(stmt)
            records = result.scalars().all()

            # Aggregate by resource type
            aggregated = {}
            for record in records:
                if record.resource_type not in aggregated:
                    aggregated[record.resource_type] = {"total": 0, "records": []}

                aggregated[record.resource_type]["total"] += record.quantity
                aggregated[record.resource_type]["records"].append(
                    {
                        "timestamp": record.created_at.isoformat(),
                        "quantity": record.quantity,
                        "metadata": record.extra_data,
                    }
                )

            return {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "usage_by_type": aggregated,
                "total_records": len(records),
            }

        except Exception as e:
            logger.error(f"Failed to get detailed usage: {e}")
            return {"error": str(e), "usage_by_type": {}, "total_records": 0}

    def get_available_plans(self) -> Dict[str, Any]:
        """Get all available subscription plans with details"""
        plans = []
        for plan_id, plan_data in self._plan_definitions.items():
            plans.append(
                {
                    "id": plan_id,
                    "name": plan_data["name"],
                    "limits": plan_data["limits"],
                    "features": plan_data["features"],
                    "pricing": plan_data["pricing"],
                }
            )

        return {"plans": plans, "currency": "USD"}

    def _get_plan_limits(self, plan_type: str) -> Dict[str, int]:
        """Get resource limits for subscription plan"""
        return self._plan_definitions.get(plan_type, self._plan_definitions["free"])[
            "limits"
        ]

    def _is_downgrade(self, current_plan: str, new_plan: str) -> bool:
        """Check if plan change is a downgrade"""
        plan_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
        return plan_hierarchy.get(new_plan, 0) < plan_hierarchy.get(current_plan, 0)

    async def _check_downgrade_eligibility(
        self, user: User, current_plan: str, new_plan: str
    ) -> bool:
        """Check if user's current usage allows downgrade"""
        try:
            # Get current usage
            usage_summary = await self.get_usage_summary(user)
            new_limits = self._get_plan_limits(new_plan)

            # Check each resource type
            for resource, current_usage in [
                ("messages", usage_summary["messages_this_month"]),
                ("background_tasks", usage_summary["background_tasks_this_month"]),
                ("api_calls", usage_summary["api_calls_this_month"]),
            ]:
                if current_usage > new_limits.get(resource, 0):
                    return False

            return True

        except Exception as e:
            logger.error(f"Failed to check downgrade eligibility: {e}")
            return False

    def _get_plan_price(self, plan_type: str, billing_cycle: str = "monthly") -> int:
        """Get plan price in cents"""
        plan_def = self._plan_definitions.get(plan_type, self._plan_definitions["free"])
        return plan_def["pricing"][billing_cycle]


# Global billing service instance
billing_service: Optional[EnhancedBillingService] = None


def get_billing_service() -> EnhancedBillingService:
    """Get or create the billing service singleton."""
    global billing_service
    if billing_service is None:
        billing_service = EnhancedBillingService()
    return billing_service


# For backward compatibility
def reset_billing_service():
    """Reset the billing service - useful for testing."""
    global billing_service
    billing_service = None
