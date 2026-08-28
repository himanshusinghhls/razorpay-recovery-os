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


@router.post("/execute", response_model=dict, dependencies=[Depends(check_rate_limit)])
async def execute_recovery(
    request: Request,
    payload: RecoveryRequest,
):
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    redis = request.app.state.arq_pool
    cache_key = f"idempotency:{payload.payment_id}:{idempotency_key}"
    
    cached_job_id = await redis.get(cache_key)
    if cached_job_id:
        return {"execution_id": cached_job_id.decode("utf-8"), "status": "processing", "message": "Job already queued (Idempotency match)"}

    execution_id = f"exec_{uuid.uuid4().hex[:16]}"
    
    await redis.set(cache_key, execution_id, ex=86400) # 24 hours TTL

    await redis.enqueue_job("process_recovery_task", payload.model_dump(), execution_id, _job_id=execution_id)

    return {
        "execution_id": execution_id,
        "status": "processing",
        "message": "Recovery queued for async processing"
    }

from arq.jobs import Job

@router.get("/status/{job_id}")
async def get_job_status(request: Request, job_id: str):
    redis = request.app.state.arq_pool
    job = Job(job_id, redis)
    status = await job.status()
    
    if status.value == "complete":
        result = await job.result()
        return result
    elif status.value == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    else:
        return {"execution_id": job_id, "status": "processing", "message": f"Job is {status.value}"}




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
