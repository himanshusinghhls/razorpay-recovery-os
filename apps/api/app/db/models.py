from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Enum as SQLEnum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from domain.execution.models import ExecutionStatus

class Base(DeclarativeBase):
    pass

class ExecutionRecord(Base):
    __tablename__ = "executions"

    execution_id: Mapped[str] = mapped_column(String, primary_key=True)
    payment_id: Mapped[str] = mapped_column(String, index=True)
    action_type: Mapped[str] = mapped_column(String)
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus, name="execution_status")
    )
    external_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

class WebhookRecord(Base):
    __tablename__ = "webhook_events"

    # Composite primary key prevents duplicate events from the same provider
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, primary_key=True)
    
    event_type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
