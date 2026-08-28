import os
import uuid
import time as _time
from datetime import datetime, timezone
import logging

from arq.connections import RedisSettings
from sqlalchemy import select, func

from apps.api.app.config import settings as app_settings
from apps.api.app.db.session import AsyncSessionLocal
from apps.api.app.db.models import ExecutionRecord

from agents.analyst.service import RecoveryAnalystAgent
from domain.policy.engine import RecoveryPolicyEngine
from application.recovery.service import RecoveryApplicationService
from application.execution.orchestrator import RecoveryExecutionOrchestrator
from application.execution.razorpay import RazorpayRecoveryExecutor
from application.execution.postgres_repository import PostgresExecutionRepository
from application.audit.service import AuditService
from application.audit.repository import PostgresAuditRepository
from application.review.service import ReviewService
from integrations.razorpay.client import RazorpayClient
from integrations.razorpay.gateway import RazorpayGateway
from domain.execution.models import RecoveryExecution, ExecutionStatus
from apps.api.app.schemas.recovery import RecoveryRequest, RecoveryResponse

logger = logging.getLogger("recoveryos.worker")
logging.basicConfig(level=logging.INFO)

async def _get_retry_context(
    session,
    payment_id: str,
    customer_id: str,
):
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


async def process_recovery_task(ctx, payload_dict: dict, execution_id: str):
    _start = _time.time()
    payload = RecoveryRequest(**payload_dict)
    
    razorpay_client = RazorpayClient(
        key_id=app_settings.razorpay_key_id,
        key_secret=app_settings.razorpay_key_secret,
    )
    gateway = RazorpayGateway(client=razorpay_client)
    agent = RecoveryAnalystAgent()
    policy_engine = RecoveryPolicyEngine()
    app_service = RecoveryApplicationService(policy_engine=policy_engine)
    executor = RazorpayRecoveryExecutor(gateway=gateway)
    orchestrator = RecoveryExecutionOrchestrator(executor=executor)

    async with AsyncSessionLocal() as session:
        audit_repo = PostgresAuditRepository(session)
        audit = AuditService(audit_repo)
        review_service = ReviewService(session)
        repo = PostgresExecutionRepository(session)

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

            retry_count, first_failure_at, customer_attempts_today = await _get_retry_context(
                session, payload.payment_id, payload.customer_id
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
                            decision.action.action_type.value if decision.action else "unknown"
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
                            decision.action.action_type.value if decision.action else "unknown"
                        ),
                        status=ExecutionStatus.FAILED,
                        external_reference=None,
                        message=f"Escalated to human review: {authorization.policy_decision.reason}",
                    )
                    await repo.create(record)
                    await session.commit()
                    return {
                        "execution_id": execution_id,
                        "status": "escalated",
                        "action_type": record.action_type,
                        "provider_reference": review.review_id,
                        "message": f"Escalated to human review: {authorization.policy_decision.reason}",
                        "pipeline_latency_ms": round((_time.time() - _start) * 1000, 2),
                    }

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
                        decision.action.action_type.value if decision.action else "unknown"
                    ),
                    status=ExecutionStatus.FAILED,
                    external_reference=None,
                    message=f"Policy Blocked: {authorization.policy_decision.reason}",
                )
                await repo.create(record)
                await session.commit()
                return {
                    "execution_id": execution_id,
                    "status": ExecutionStatus.FAILED.value,
                    "action_type": record.action_type,
                    "provider_reference": None,
                    "message": record.message,
                    "pipeline_latency_ms": round((_time.time() - _start) * 1000, 2),
                }

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
            return {
                "execution_id": execution_id,
                "status": final_status.value,
                "action_type": execution_result.action_type,
                "provider_reference": execution_result.external_reference,
                "message": execution_result.message,
                "pipeline_latency_ms": round((_time.time() - _start) * 1000, 2),
            }

        except Exception as e:
            logger.exception("Recovery execution failed for %s", payload.payment_id)
            raise e

class WorkerSettings:
    functions = [process_recovery_task]
    redis_settings = RedisSettings.from_dsn("redis://localhost:6379/0")
