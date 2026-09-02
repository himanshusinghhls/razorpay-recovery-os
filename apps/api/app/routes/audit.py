import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.audit.repository import PostgresAuditRepository
from domain.audit.models import AuditEntry, AuditEventType
from domain.execution.models import ExecutionStatus

from ..core.auth import Principal, get_current_principal, require_role
from ..db.models import ExecutionRecord, UserRole
from ..db.session import get_db_session

router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
)


class SuccessLogRequest(BaseModel):
    payment_id: str = Field(min_length=1, max_length=128)
    amount: int = Field(ge=0, le=100_000_000)
    customer_id: str = Field(default="cust_direct", max_length=128)


@router.get("/{payment_id}")
async def get_audit_trail(
    payment_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns the complete audit trail for a specific payment.

    Each entry records one step of the recovery pipeline:
    detection → AI diagnosis → policy decision → execution → reconciliation.
    """
    repo = PostgresAuditRepository(session, principal.merchant_id)
    entries = await repo.get_by_payment_id(payment_id)

    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"No audit trail found for payment {payment_id}",
        )

    return {
        "payment_id": payment_id,
        "total_entries": len(entries),
        "trail": [
            {
                "event_type": e.event_type.value,
                "data": e.data,
                "actor": e.actor,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }


@router.get("/")
async def get_recent_audit(
    principal: Annotated[Principal, Depends(get_current_principal)],
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns the most recent audit log entries for the caller's merchant.
    """
    repo = PostgresAuditRepository(session, principal.merchant_id)
    entries = await repo.get_recent(limit=limit)

    return {
        "total_entries": len(entries),
        "entries": [
            {
                "payment_id": e.payment_id,
                "customer_id": e.customer_id,
                "event_type": e.event_type.value,
                "data": e.data,
                "actor": e.actor,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }


@router.post("/log-success")
async def log_success_audit(
    request: SuccessLogRequest,
    principal: Annotated[Principal, Depends(require_role(UserRole.ANALYST))],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Logs a successful original payment so it appears in the audit trail.
    Also creates an ExecutionRecord so it appears in the Analytics dashboard.
    """
    repo = PostgresAuditRepository(session, principal.merchant_id)
    entry = AuditEntry(
        payment_id=request.payment_id,
        customer_id=request.customer_id,
        event_type=AuditEventType.EXECUTION_SUCCEEDED,
        data={
            "amount": request.amount,
            "status": "success",
            "message": "Original payment succeeded. No recovery required.",
        },
    )
    await repo.save(entry, actor=principal.user_id)

    session.add(
        ExecutionRecord(
            execution_id=f"exec_direct_{uuid.uuid4().hex[:8]}",
            merchant_id=principal.merchant_id,
            payment_id=request.payment_id,
            customer_id=request.customer_id,
            action_type="direct_success",
            status=ExecutionStatus.SUCCEEDED,
            message="Original payment succeeded.",
            external_reference=request.payment_id,
            initiated_by=principal.user_id,
        )
    )
    await session.commit()

    return {"status": "logged"}
