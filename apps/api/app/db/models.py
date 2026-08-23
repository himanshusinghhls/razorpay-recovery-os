import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Enum as SQLEnum, String, Float, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from domain.audit.models import AuditEventType
from domain.execution.models import ExecutionStatus
from domain.review.models import ReviewStatus


class Base(DeclarativeBase):
    pass


class ExecutionRecord(Base):
    __tablename__ = "executions"

    execution_id: Mapped[str] = mapped_column(String, primary_key=True)
    payment_id: Mapped[str] = mapped_column(String, index=True)
    customer_id: Mapped[str] = mapped_column(String, index=True, default="")
    action_type: Mapped[str] = mapped_column(String)
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus, name="execution_status")
    )
    external_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class WebhookRecord(Base):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, primary_key=True)

    event_type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class AuditRecord(Base):
    """
    Immutable audit log entry.

    Every step of the recovery pipeline writes one row here,
    forming a complete, queryable audit trail per payment.
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: f"audit_{uuid.uuid4().hex[:16]}",
    )
    payment_id: Mapped[str] = mapped_column(String, index=True)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[AuditEventType] = mapped_column(
        SQLEnum(AuditEventType, name="audit_event_type")
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ReviewRecord(Base):
    """
    Escalation queue for recovery actions that require human approval.

    Created when the policy engine blocks an action with
    requires_human_approval=True.
    """

    __tablename__ = "pending_reviews"

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
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
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
