import logging
import time as _time
from datetime import datetime, timezone

from arq.connections import RedisSettings
from sqlalchemy import func, select

from agents.analyst.service import RecoveryAnalystAgent
from application.audit.repository import PostgresAuditRepository
from application.audit.service import AuditService
from application.execution.orchestrator import RecoveryExecutionOrchestrator
from application.execution.postgres_repository import PostgresExecutionRepository
from application.execution.razorpay import RazorpayRecoveryExecutor
from application.recovery.service import RecoveryApplicationService
from application.review.service import ReviewService
from apps.api.app.config import settings as app_settings
from apps.api.app.db.models import ExecutionRecord
from apps.api.app.db.session import AsyncSessionLocal, engine
from apps.api.app.schemas.recovery import RecoveryRequest
from domain.execution.models import ExecutionStatus, RecoveryExecution
from domain.policy.engine import RecoveryPolicyEngine
from integrations.razorpay.client import RazorpayClient
from integrations.razorpay.gateway import RazorpayGateway

logger = logging.getLogger("recoveryos.worker")
logging.basicConfig(level=logging.INFO)

SUSPICIOUS_REASONS = frozenset(
    {"suspected_fraud", "fraud_detected", "account_takeover"}
)


async def _get_retry_context(
    session,
    merchant_id: str,
    payment_id: str,
    customer_id: str,
) -> tuple[int, datetime | None, int]:
    retry_count = (
        await session.execute(
            select(func.count()).where(
                ExecutionRecord.merchant_id == merchant_id,
                ExecutionRecord.payment_id == payment_id,
            )
        )
    ).scalar() or 0

    first_failure_at = (
        await session.execute(
            select(ExecutionRecord.created_at)
            .where(
                ExecutionRecord.merchant_id == merchant_id,
                ExecutionRecord.payment_id == payment_id,
            )
            .order_by(ExecutionRecord.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    customer_attempts_today = (
        await session.execute(
            select(func.count()).where(
                ExecutionRecord.merchant_id == merchant_id,
                ExecutionRecord.customer_id == customer_id,
                ExecutionRecord.created_at >= today_start,
            )
        )
    ).scalar() or 0

    return retry_count, first_failure_at, customer_attempts_today


async def process_recovery_task(
    ctx,
    payload_dict: dict,
    execution_id: str,
    merchant_id: str,
    initiated_by: str | None = None,
):
    """
    Run one recovery through diagnosis → policy → execution.

    Long-lived clients come from ctx (built once at worker startup) rather than
    being reconstructed per job, which previously opened a fresh Razorpay HTTP
    connection and re-initialised the Gemini agent for every single message.
    """
    _start = _time.time()
    payload = RecoveryRequest(**payload_dict)

    agent: RecoveryAnalystAgent = ctx["agent"]
    app_service: RecoveryApplicationService = ctx["app_service"]
    orchestrator: RecoveryExecutionOrchestrator = ctx["orchestrator"]

    def _envelope(status: str, action_type: str, reference: str | None, message: str):
        return {
            "execution_id": execution_id,
            "merchant_id": merchant_id,
            "status": status,
            "action_type": action_type,
            "provider_reference": reference,
            "message": message,
            "pipeline_latency_ms": round((_time.time() - _start) * 1000, 2),
        }

    async with AsyncSessionLocal() as session:
        audit = AuditService(
            PostgresAuditRepository(session, merchant_id),
            actor=initiated_by or "worker",
        )
        review_service = ReviewService(session, merchant_id)
        repo = PostgresExecutionRepository(session, merchant_id)

        try:
            await audit.log_failure_detected(
                payment_id=payload.payment_id,
                customer_id=payload.customer_id,
                amount=payload.amount,
                failure_reason=payload.failure_reason,
            )

            history_records = (
                await session.execute(
                    select(ExecutionRecord)
                    .where(
                        ExecutionRecord.merchant_id == merchant_id,
                        ExecutionRecord.payment_id == payload.payment_id,
                    )
                    .order_by(ExecutionRecord.created_at.desc())
                    .limit(5)
                )
            ).scalars().all()

            customer_history = (
                "; ".join(
                    f"{r.action_type}:{r.status.value} at {r.created_at}"
                    for r in history_records
                )
                if history_records
                else "No prior recovery attempts"
            )

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
                    session, merchant_id, payload.payment_id, payload.customer_id
                )
            )

            authorization = app_service.authorize(
                decision=decision,
                retry_count=retry_count,
                suspicious=payload.failure_reason in SUSPICIOUS_REASONS,
                first_failure_at=first_failure_at,
                customer_attempts_today=customer_attempts_today,
            )

            action_type = (
                decision.action.action_type.value if decision.action else "unknown"
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
                reason = authorization.policy_decision.reason

                if authorization.policy_decision.requires_human_approval:
                    review = await review_service.create_review(
                        payment_id=payload.payment_id,
                        customer_id=payload.customer_id,
                        amount=payload.amount,
                        action_type=action_type,
                        policy_reason=reason,
                        ai_diagnosis=decision.diagnosis,
                        ai_confidence=decision.confidence,
                    )

                    await audit.log_escalation(
                        payment_id=payload.payment_id,
                        customer_id=payload.customer_id,
                        review_id=review.review_id,
                        reason=reason,
                    )

                    await repo.create(
                        RecoveryExecution(
                            execution_id=execution_id,
                            payment_id=payload.payment_id,
                            action_type=action_type,
                            status=ExecutionStatus.FAILED,
                            external_reference=None,
                            message=f"Escalated to human review: {reason}",
                            customer_id=payload.customer_id,
                            merchant_id=merchant_id,
                            initiated_by=initiated_by,
                        )
                    )
                    return _envelope(
                        "escalated",
                        action_type,
                        review.review_id,
                        f"Escalated to human review: {reason}",
                    )

                await audit.log_stopping_rule(
                    payment_id=payload.payment_id,
                    customer_id=payload.customer_id,
                    rule_name="policy_block",
                    reason=reason,
                )

                message = f"Policy Blocked: {reason}"
                await repo.create(
                    RecoveryExecution(
                        execution_id=execution_id,
                        payment_id=payload.payment_id,
                        action_type=action_type,
                        status=ExecutionStatus.FAILED,
                        external_reference=None,
                        message=message,
                        customer_id=payload.customer_id,
                        merchant_id=merchant_id,
                        initiated_by=initiated_by,
                    )
                )
                return _envelope(
                    ExecutionStatus.FAILED.value, action_type, None, message
                )

            execution_result = await orchestrator.execute(authorization)

            final_status = (
                ExecutionStatus.STARTED
                if execution_result.success
                else ExecutionStatus.FAILED
            )
            await repo.create(
                RecoveryExecution(
                    execution_id=execution_id,
                    payment_id=payload.payment_id,
                    action_type=execution_result.action_type,
                    status=final_status,
                    external_reference=execution_result.external_reference,
                    message=execution_result.message,
                    customer_id=payload.customer_id,
                    merchant_id=merchant_id,
                    initiated_by=initiated_by,
                )
            )

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
            return _envelope(
                final_status.value,
                execution_result.action_type,
                execution_result.external_reference,
                execution_result.message,
            )

        except Exception:
            # Leave no partial transaction on the pooled connection before arq
            # retries this job.
            await session.rollback()
            logger.exception(
                "recovery failed payment=%s merchant=%s", payload.payment_id, merchant_id
            )
            raise


async def startup(ctx):
    """Build the expensive, reusable clients once per worker process."""
    razorpay_client = RazorpayClient()
    gateway = RazorpayGateway(client=razorpay_client)

    ctx["razorpay_client"] = razorpay_client
    ctx["agent"] = RecoveryAnalystAgent()
    ctx["app_service"] = RecoveryApplicationService(
        policy_engine=RecoveryPolicyEngine()
    )
    ctx["orchestrator"] = RecoveryExecutionOrchestrator(
        executor=RazorpayRecoveryExecutor(gateway=gateway)
    )
    logger.info("worker started; redis=%s", app_settings.redis_url.split("@")[-1])


async def shutdown(ctx):
    client = ctx.get("razorpay_client")
    if client is not None:
        await client.close()
    await engine.dispose()


class WorkerSettings:
    functions = [process_recovery_task]
    on_startup = startup
    on_shutdown = shutdown

    # Honour REDIS_URL instead of a hardcoded localhost DSN.
    redis_settings = RedisSettings.from_dsn(app_settings.redis_url)

    # A recovery that keeps failing must not be retried forever; after this it
    # lands in the dead-letter state and stays visible rather than looping.
    max_tries = 3
    job_timeout = 120
    max_jobs = 20
    keep_result = 3600
