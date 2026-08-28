import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,

)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from domain.audit.models import AuditEventType
from domain.execution.models import ExecutionStatus
from domain.review.models import ReviewStatus


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tenancy & identity
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    """
    Ordered least- to most-privileged. `require_role` compares by rank, so a
    higher role always satisfies a lower requirement.
    """

    VIEWER = "viewer"    # read dashboards and audit trails
    ANALYST = "analyst"  # + trigger recoveries, approve/reject reviews
    ADMIN = "admin"      # + manage users and merchant settings


ROLE_RANK: dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.ANALYST: 1,
    UserRole.ADMIN: 2,
}


class Merchant(Base):
    """
    A tenant. Every payment, execution, audit row and review belongs to exactly
    one merchant, mirroring how Razorpay isolates merchant accounts.
    """

    __tablename__ = "merchants"

    merchant_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"mrch_{uuid.uuid4().hex[:16]}"
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    # Per-tenant Razorpay credentials. Null falls back to the platform-level keys.
    razorpay_key_id: Mapped[str | None] = mapped_column(String, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Tenant-level recovery guardrails, overriding the platform defaults.
    daily_recovery_cap: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    max_auto_recovery_amount: Mapped[int] = mapped_column(
        Integer, default=50_000_00, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: f"user_{uuid.uuid4().hex[:16]}"
    )
    merchant_id: Mapped[str] = mapped_column(
        ForeignKey("merchants.merchant_id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Globally unique so that login can resolve an account from the email
    # alone, with no merchant picker step. A person needing access to two
    # merchants gets two accounts.
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, default="", nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"), default=UserRole.VIEWER, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Online brute-force protection: cleared on every successful login.
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RefreshTokenRecord(Base):
    """
    One row per issued refresh token, stored as SHA-256.

    Tokens rotate on use: the old row is marked used and a new one issued in the
    same family. Presenting an already-used token means it leaked, so the entire
    family is revoked.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_family_active", "family_id", "revoked_at"),
    )

    jti: Mapped[str] = mapped_column(String, primary_key=True)
    family_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )

    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user_agent: Mapped[str] = mapped_column(String, default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String, default="", nullable=False)


# ---------------------------------------------------------------------------
# Recovery pipeline
# ---------------------------------------------------------------------------

class ExecutionRecord(Base):
    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_merchant_created", "merchant_id", "created_at"),
        Index("ix_executions_merchant_payment", "merchant_id", "payment_id"),
        Index("ix_executions_merchant_customer_created", "merchant_id", "customer_id", "created_at"),
    )

    execution_id: Mapped[str] = mapped_column(String, primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        ForeignKey("merchants.merchant_id", ondelete="CASCADE"), index=True, nullable=False
    )
    payment_id: Mapped[str] = mapped_column(String, index=True)
    customer_id: Mapped[str] = mapped_column(String, index=True, default="")
    action_type: Mapped[str] = mapped_column(String)
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus, name="execution_status")
    )
    external_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String)

    # Who/what initiated this recovery — null for system-driven runs.
    initiated_by: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
    )


class WebhookRecord(Base):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, primary_key=True)

    event_type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )


class AuditRecord(Base):
    """
    Immutable audit log entry.

    Every step of the recovery pipeline writes one row here,
    forming a complete, queryable audit trail per payment.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_merchant_payment", "merchant_id", "payment_id"),
        Index("ix_audit_merchant_created", "merchant_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: f"audit_{uuid.uuid4().hex[:16]}",
    )
    merchant_id: Mapped[str] = mapped_column(
        ForeignKey("merchants.merchant_id", ondelete="CASCADE"), index=True, nullable=False
    )
    payment_id: Mapped[str] = mapped_column(String, index=True)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[AuditEventType] = mapped_column(
        SQLEnum(AuditEventType, name="audit_event_type")
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Identity of the human or system component responsible for this entry.
    actor: Mapped[str] = mapped_column(String, default="system", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )


class ReviewRecord(Base):
    """
    Escalation queue for recovery actions that require human approval.

    Created when the policy engine blocks an action with
    requires_human_approval=True.
    """

    __tablename__ = "pending_reviews"
    __table_args__ = (
        Index("ix_reviews_merchant_status", "merchant_id", "status"),
    )

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        ForeignKey("merchants.merchant_id", ondelete="CASCADE"), index=True, nullable=False
    )
    payment_id: Mapped[str] = mapped_column(String, index=True)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    action_type: Mapped[str] = mapped_column(String)
    policy_reason: Mapped[str] = mapped_column(String)
    ai_diagnosis: Mapped[str] = mapped_column(String, default="")
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(ReviewStatus, name="review_status"),
        default=ReviewStatus.PENDING,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
