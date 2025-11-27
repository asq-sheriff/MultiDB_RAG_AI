import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    ARRAY,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, JSONB


class DatabaseBase(DeclarativeBase):
    """Base class for all PostgreSQL models"""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Organization(DatabaseBase, TimestampMixin):
    """Organization management for multi-tenant support"""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    users: Mapped[List["User"]] = relationship("User", back_populates="organization")


class User(DatabaseBase, TimestampMixin):
    """User management and authentication"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_plan: Mapped[str] = mapped_column(String(50), default="free")

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )

    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="users"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    usage_records: Mapped[List["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )


class Subscription(DatabaseBase, TimestampMixin):
    """User subscription and billing information"""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly")

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)

    limits: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")


class UsageRecord(DatabaseBase, TimestampMixin):
    """Track resource usage for billing and quotas"""

    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    billing_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    billing_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    user: Mapped["User"] = relationship("User", back_populates="usage_records")

    __table_args__ = (
        Index(
            "idx_usage_user_period",
            "user_id",
            "billing_period_start",
            "billing_period_end",
        ),
        Index("idx_usage_resource_type", "resource_type"),
    )


class AuditLog(DatabaseBase, TimestampMixin):
    """Audit trail for compliance and security monitoring"""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id")
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))

    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)

    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_timestamp", "created_at"),
    )


class FeatureFlag(DatabaseBase, TimestampMixin):
    """Feature flags for gradual rollouts and A/B testing"""

    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    rollout_percentage: Mapped[int] = mapped_column(Integer, default=0)
    target_user_segments: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    conditions: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)


class SystemSetting(DatabaseBase, TimestampMixin):
    """System-wide configuration and settings"""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id")
    )
