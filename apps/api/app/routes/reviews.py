import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from application.audit.repository import PostgresAuditRepository
from application.audit.service import AuditService
from application.execution.authorization import ExecutionAuthorization
from application.execution.postgres_repository import PostgresExecutionRepository
from application.execution.razorpay import RazorpayRecoveryExecutor
from application.review.service import ReviewService
from domain.execution.models import ExecutionStatus, RecoveryExecution
from domain.recovery.actions import RecoveryAction, RecoveryActionType
from integrations.razorpay.gateway import RazorpayGateway

from ..core.auth import Principal, get_current_principal, require_role
from ..db.models import UserRole
from ..db.session import get_db_session

logger = logging.getLogger("recoveryos.reviews")

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"],
)


@router.get("/")
async def list_reviews(
    principal: Annotated[Principal, Depends(get_current_principal)],
    status: Literal["pending", "all"] = Query(default="pending"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List reviews for the caller's merchant, filterable by status.
    """
    service = ReviewService(session, principal.merchant_id)

    reviews = (
        await service.list_pending() if status == "pending" else await service.list_all()
    )

    return {
        "total": len(reviews),
        "reviews": [
            {
                "review_id": r.review_id,
                "payment_id": r.payment_id,
                "customer_id": r.customer_id,
                "amount": r.amount,
                "action_type": r.action_type,
                "policy_reason": r.policy_reason,
                "ai_diagnosis": r.ai_diagnosis,
                "ai_confidence": r.ai_confidence,
                "status": r.status.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
                "resolved_by": r.resolved_by,
            }
            for r in reviews
        ],
    }


@router.post("/{review_id}/approve")
async def approve_review(
    review_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_role(UserRole.ANALYST))],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Approve a pending review and trigger the recovery execution.

    Approving is the one place a human can authorize a real charge, so the
    approver's user id is recorded on the review and in the audit trail.
    """
    review_service = ReviewService(session, principal.merchant_id)
    audit_repo = PostgresAuditRepository(session, principal.merchant_id)
    audit_service = AuditService(audit_repo, actor=principal.user_id)

    # Atomically claims the review; a second concurrent approval gets None.
    review = await review_service.approve(review_id, resolved_by=principal.user_id)

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found or already resolved",
        )

    await audit_service.log_review_decision(
        payment_id=review.payment_id,
        customer_id=review.customer_id,
        review_id=review_id,
        approved=True,
        resolved_by=principal.user_id,
    )

    try:
        action = RecoveryAction(
            action_type=RecoveryActionType(review.action_type),
            payment_id=review.payment_id,
            customer_id=review.customer_id,
            amount=review.amount,
            reason=f"Approved via human review: {review_id}",
        )

        execution_auth = ExecutionAuthorization(
            action=action,
            authorization_reason=f"Human-approved review {review_id} by {principal.email}",
        )

        gateway = RazorpayGateway(client=request.app.state.razorpay)
        executor = RazorpayRecoveryExecutor(gateway=gateway)

        execution_result = await executor.execute(execution_auth)

        execution_id = f"exec_{uuid.uuid4().hex[:16]}"
        exec_repo = PostgresExecutionRepository(session, principal.merchant_id)
        record = RecoveryExecution(
            execution_id=execution_id,
            payment_id=review.payment_id,
            action_type=execution_result.action_type,
            status=(
                ExecutionStatus.STARTED
                if execution_result.success
                else ExecutionStatus.FAILED
            ),
            external_reference=execution_result.external_reference,
            message=execution_result.message,
            customer_id=review.customer_id,
            merchant_id=principal.merchant_id,
            initiated_by=principal.user_id,
        )
        await exec_repo.create(record)

        await audit_service.log_execution_result(
            payment_id=review.payment_id,
            customer_id=review.customer_id,
            execution_id=execution_id,
            success=execution_result.success,
            action_type=execution_result.action_type,
            message=execution_result.message,
            external_reference=execution_result.external_reference,
        )
        await session.commit()

        return {
            "review_id": review_id,
            "status": "approved",
            "execution_id": execution_id,
            "execution_success": execution_result.success,
            "message": execution_result.message,
            "provider_reference": execution_result.external_reference,
        }

    except Exception as exc:  # noqa: BLE001
        # The approval itself already committed; surface that the downstream
        # execution failed without leaking the provider's error text.
        logger.exception("execution after approval failed review=%s", review_id)
        return {
            "review_id": review_id,
            "status": "approved",
            "execution_success": False,
            "execution_error": "Recovery execution failed after approval",
        }


@router.post("/{review_id}/reject")
async def reject_review(
    review_id: str,
    principal: Annotated[Principal, Depends(require_role(UserRole.ANALYST))],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Reject a pending review and close the case.
    """
    review_service = ReviewService(session, principal.merchant_id)
    audit_repo = PostgresAuditRepository(session, principal.merchant_id)
    audit_service = AuditService(audit_repo, actor=principal.user_id)

    review = await review_service.reject(review_id, resolved_by=principal.user_id)

    if not review:
        raise HTTPException(
            status_code=404,
            detail="Review not found or already resolved",
        )

    await audit_service.log_review_decision(
        payment_id=review.payment_id,
        customer_id=review.customer_id,
        review_id=review_id,
        approved=False,
        resolved_by=principal.user_id,
    )
    await session.commit()

    return {
        "review_id": review_id,
        "status": "rejected",
        "payment_id": review.payment_id,
    }
