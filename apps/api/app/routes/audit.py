from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from application.audit.repository import PostgresAuditRepository

router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
)


@router.get("/{payment_id}")
async def get_audit_trail(
    payment_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns the complete audit trail for a specific payment.

    Each entry records one step of the recovery pipeline:
    detection → AI diagnosis → policy decision → execution → reconciliation.
    """
    repo = PostgresAuditRepository(session)
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
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }


@router.get("/")
async def get_recent_audit(
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns the most recent audit log entries across all payments.
    """
    repo = PostgresAuditRepository(session)
    entries = await repo.get_recent(limit=limit)

    return {
        "total_entries": len(entries),
        "entries": [
            {
                "payment_id": e.payment_id,
                "customer_id": e.customer_id,
                "event_type": e.event_type.value,
                "data": e.data,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }
