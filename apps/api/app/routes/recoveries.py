import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.recovery import RecoveryRequest, RecoveryResponse
from ..db.session import get_db_session
from ..db.models import ExecutionRecord

from agents.analyst.service import RecoveryAnalystAgent
from domain.policy.engine import RecoveryPolicyEngine
from domain.policy.models import PolicyContext
from application.recovery.service import RecoveryApplicationService
from application.execution.orchestrator import RecoveryExecutionOrchestrator
from application.execution.razorpay import RazorpayRecoveryExecutor
from application.execution.postgres_repository import PostgresExecutionRepository
from application.audit.service import AuditService
from application.audit.repository import PostgresAuditRepository
from application.review.service import ReviewService
from integrations.razorpay.gateway import RazorpayGateway
from domain.execution.models import RecoveryExecution, ExecutionStatus
from apps.api.app.core.dependencies import (
    get_recovery_app_service,
    get_execution_orchestrator,
    get_audit_service,
    get_review_service,
    get_execution_repository,
    get_recovery_analyst_agent,
)
from fastapi import BackgroundTasks

router = APIRouter(
    prefix="/recoveries",
    tags=["Recoveries"],
)


async def _get_retry_context(
    session: AsyncSession,
    payment_id: str,
    customer_id: str,
) -> tuple[int, datetime | None, int]:
    """
    Query real execution history to determine:
    - retry_count: how many previous executions exist for this payment
    - first_failure_at: when the earliest execution was created
    - customer_attempts_today: how many executions this customer has today
    """
    retry_stmt = select(func.count()).where(
        ExecutionRecord.payment_id == payment_id
    )
    retry_result = await session.execute(retry_stmt)
    retry_count = retry_result.scalar() or 0

    first_stmt = (
        select(ExecutionRecord.created_at)
        .where(ExecutionRecord.payment_id == payment_id)
        .order_by(ExecutionRecord.created_at.asc())
        .limit(1)
    )
    first_result = await session.execute(first_stmt)
    first_failure_at = first_result.scalar_one_or_none()

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    daily_stmt = select(func.count()).where(
        ExecutionRecord.customer_id == customer_id,
        ExecutionRecord.created_at >= today_start,
    )
    daily_result = await session.execute(daily_stmt)
    customer_attempts_today = daily_result.scalar() or 0

    return retry_count, first_failure_at, customer_attempts_today


import time as _time

RATE_LIMIT_WINDOW = 60
MAX_REQUESTS_PER_WINDOW = 10
_ip_hits: dict[str, list[float]] = {}


def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = _time.time()
    _ip_hits[ip] = [t for t in _ip_hits.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
    if len(_ip_hits[ip]) >= MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    _ip_hits[ip].append(now)


@router.post("/execute", response_model=RecoveryResponse, dependencies=[Depends(check_rate_limit)])
async def execute_recovery(
    payload: RecoveryRequest,
    session: AsyncSession = Depends(get_db_session),
    app_service: RecoveryApplicationService = Depends(get_recovery_app_service),
    orchestrator: RecoveryExecutionOrchestrator = Depends(get_execution_orchestrator),
    audit: AuditService = Depends(get_audit_service),
    review_service: ReviewService = Depends(get_review_service),
    repo: PostgresExecutionRepository = Depends(get_execution_repository),
    agent: RecoveryAnalystAgent = Depends(get_recovery_analyst_agent),
):
    execution_id = f"exec_{uuid.uuid4().hex[:16]}"
    _start = _time.time()

    try:
        await audit.log_failure_detected(
            payment_id=payload.payment_id,
            customer_id=payload.customer_id,
            amount=payload.amount,
            failure_reason=payload.failure_reason,
        )

        prev_executions = await session.execute(
            select(ExecutionRecord)
            .where(ExecutionRecord.payment_id == payload.payment_id)
            .order_by(ExecutionRecord.created_at.desc())
            .limit(5)
        )
        history_records = prev_executions.scalars().all()
        if history_records:
            customer_history = "; ".join(
                f"{r.action_type}:{r.status.value} at {r.created_at}"
                for r in history_records
            )
        else:
            customer_history = "No prior recovery attempts"

        decision = await agent.analyze(
            payment_id=payload.payment_id,
            customer_id=payload.customer_id,
            amount=payload.amount,
            failure_reason=payload.failure_reason,
            customer_history=customer_history,
        )

        await audit.log_ai_diagnosis(
            payment_id=payload.payment_id,
            customer_id=payload.customer_id,
            diagnosis=decision.diagnosis,
            confidence=decision.confidence,
            recovery_probability=decision.recovery_probability,
            recommended_action=(
                decision.action.action_type.value if decision.action else "none"
            ),
            expected_recovery=decision.expected_recovery,
            raw_prompt=decision.raw_prompt,
        )

        retry_count, first_failure_at, customer_attempts_today = (
            await _get_retry_context(
                session, payload.payment_id, payload.customer_id
            )
        )

        is_suspicious = payload.failure_reason in (
            "suspected_fraud",
            "fraud_detected",
            "account_takeover",
        )

        authorization = app_service.authorize(
            decision=decision,
            retry_count=retry_count,
            suspicious=is_suspicious,
            first_failure_at=first_failure_at,
            customer_attempts_today=customer_attempts_today,
        )

        await audit.log_policy_decision(
            payment_id=payload.payment_id,
            customer_id=payload.customer_id,
            allowed=authorization.policy_decision.allowed,
            reason=authorization.policy_decision.reason,
            requires_human_approval=authorization.policy_decision.requires_human_approval,
            retry_count=retry_count,
        )

        if not authorization.executable:
            if authorization.policy_decision.requires_human_approval:
                review = await review_service.create_review(
                    payment_id=payload.payment_id,
                    customer_id=payload.customer_id,
                    amount=payload.amount,
                    action_type=(
                        decision.action.action_type.value
                        if decision.action
                        else "unknown"
                    ),
                    policy_reason=authorization.policy_decision.reason,
                    ai_diagnosis=decision.diagnosis,
                    ai_confidence=decision.confidence,
                )

                await audit.log_escalation(
                    payment_id=payload.payment_id,
                    customer_id=payload.customer_id,
                    review_id=review.review_id,
                    reason=authorization.policy_decision.reason,
                )

                record = RecoveryExecution(
                    execution_id=execution_id,
                    payment_id=payload.payment_id,
                    action_type=(
                        decision.action.action_type.value
                        if decision.action
                        else "unknown"
                    ),
                    status=ExecutionStatus.FAILED,
                    external_reference=None,
                    message=(
                        f"Escalated to human review: "
                        f"{authorization.policy_decision.reason}"
                    ),
                )
                await repo.create(record)

                await session.commit()
                return RecoveryResponse(
                    execution_id=execution_id,
                    status="escalated",
                    action_type=record.action_type,
                    provider_reference=review.review_id,
                    message=(
                        f"Escalated to human review: "
                        f"{authorization.policy_decision.reason}"
                    ),
                    pipeline_latency_ms=round((_time.time() - _start) * 1000, 2),
                )

            await audit.log_stopping_rule(
                payment_id=payload.payment_id,
                customer_id=payload.customer_id,
                rule_name="policy_block",
                reason=authorization.policy_decision.reason,
            )

            record = RecoveryExecution(
                execution_id=execution_id,
                payment_id=payload.payment_id,
                action_type=(
                    decision.action.action_type.value
                    if decision.action
                    else "unknown"
                ),
                status=ExecutionStatus.FAILED,
                external_reference=None,
                message=(
                    f"Policy Blocked: {authorization.policy_decision.reason}"
                ),
            )
            await repo.create(record)

            await session.commit()
            return RecoveryResponse(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED.value,
                action_type=record.action_type,
                provider_reference=None,
                message=record.message,
                pipeline_latency_ms=round((_time.time() - _start) * 1000, 2),
            )

        execution_result = await orchestrator.execute(authorization)

        final_status = (
            ExecutionStatus.STARTED
            if execution_result.success
            else ExecutionStatus.FAILED
        )
        record = RecoveryExecution(
            execution_id=execution_id,
            payment_id=payload.payment_id,
            action_type=execution_result.action_type,
            status=final_status,
            external_reference=execution_result.external_reference,
            message=execution_result.message,
        )
        await repo.create(record)

        await audit.log_execution_result(
            payment_id=payload.payment_id,
            customer_id=payload.customer_id,
            execution_id=execution_id,
            success=execution_result.success,
            action_type=execution_result.action_type,
            message=execution_result.message,
            external_reference=execution_result.external_reference,
        )

        await session.commit()
        return RecoveryResponse(
            execution_id=execution_id,
            status=final_status.value,
            action_type=execution_result.action_type,
            provider_reference=execution_result.external_reference,
            message=execution_result.message,
            pipeline_latency_ms=round((_time.time() - _start) * 1000, 2),
        )

    except Exception as e:
        import logging
        logger = logging.getLogger("recoveryos.api")
        logger.exception("Recovery execution failed for %s", payload.payment_id)
        raise HTTPException(
            status_code=500,
            detail="Recovery execution failed. Check server logs for details.",
        )


@router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    repo = PostgresExecutionRepository(session)
    execution = await repo.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {
        "execution_id": execution.execution_id,
        "payment_id": execution.payment_id,
        "action_type": execution.action_type,
        "status": execution.status.value,
        "external_reference": execution.external_reference,
        "message": execution.message,
    }


from ..config import settings

@router.post("/create-order")
async def create_razorpay_order(
    request: Request,
    amount: int,
    currency: str = "INR",
):
    """
    Creates a real Razorpay order for the frontend Checkout flow.
    This enables the realistic payment experience on the dashboard.
    """
    razorpay_client = request.app.state.razorpay
    gateway = RazorpayGateway(client=razorpay_client)

    try:
        receipt = f"rcvry_{uuid.uuid4().hex[:12]}"
        order = await gateway.create_retry_order(
            amount=amount,
            currency=currency,
            receipt=receipt,
            notes={"source": "recovery_os_dashboard"},
        )

        return {
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "receipt": receipt,
            "key_id": settings.razorpay_key_id,
        }
    except Exception:
        import logging
        logging.getLogger("recoveryos.api").exception("Failed to create order")
        raise HTTPException(
            status_code=500,
            detail="Failed to create Razorpay order",
        )
