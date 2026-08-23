import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from application.review.service import ReviewService
from application.audit.service import AuditService
from application.audit.repository import PostgresAuditRepository
from application.execution.orchestrator import RecoveryExecutionOrchestrator
from application.execution.razorpay import RazorpayRecoveryExecutor
from application.execution.authorization import ExecutionAuthorization
from application.execution.postgres_repository import PostgresExecutionRepository
from integrations.razorpay.gateway import RazorpayGateway
from domain.execution.models import RecoveryExecution, ExecutionStatus
from domain.recovery.actions import RecoveryAction, RecoveryActionType

from fastapi import Request

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"],
)


@router.get("/")
async def list_reviews(
    status: str = "pending",
    session: AsyncSession = Depends(get_db_session),
):
    """
    List reviews, filterable by status.
    """
    service = ReviewService(session)

    if status == "pending":
        reviews = await service.list_pending()
    else:
        reviews = await service.list_all()

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
    session: AsyncSession = Depends(get_db_session),
):
    """
    Approve a pending review and trigger the recovery execution.
    """
    review_service = ReviewService(session)
    audit_repo = PostgresAuditRepository(session)
    audit_service = AuditService(audit_repo)

    review = await review_service.approve(review_id)

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
        resolved_by="merchant",
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
            authorization_reason=f"Human-approved review {review_id}",
        )

        razorpay_client = request.app.state.razorpay
        gateway = RazorpayGateway(client=razorpay_client)
        executor = RazorpayRecoveryExecutor(gateway=gateway)

        execution_result = await executor.execute(execution_auth)

        execution_id = f"exec_{uuid.uuid4().hex[:16]}"
        exec_repo = PostgresExecutionRepository(session)
        final_status = (
            ExecutionStatus.STARTED
            if execution_result.success
            else ExecutionStatus.FAILED
        )
        record = RecoveryExecution(
            execution_id=execution_id,
            payment_id=review.payment_id,
            action_type=execution_result.action_type,
            status=final_status,
            external_reference=execution_result.external_reference,
            message=execution_result.message,
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

        return {
            "review_id": review_id,
            "status": "approved",
            "execution_id": execution_id,
            "execution_success": execution_result.success,
            "message": execution_result.message,
            "provider_reference": execution_result.external_reference,
        }

    except Exception as e:
        return {
            "review_id": review_id,
            "status": "approved",
            "execution_error": str(e),
        }


@router.post("/{review_id}/reject")
async def reject_review(
    review_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Reject a pending review and close the case.
    """
    review_service = ReviewService(session)
    audit_repo = PostgresAuditRepository(session)
    audit_service = AuditService(audit_repo)

    review = await review_service.reject(review_id)

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
        resolved_by="merchant",
    )

    return {
        "review_id": review_id,
        "status": "rejected",
        "payment_id": review.payment_id,
    }
