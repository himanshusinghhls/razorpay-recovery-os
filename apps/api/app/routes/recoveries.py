import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from arq.jobs import Job
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.execution.postgres_repository import PostgresExecutionRepository
from integrations.razorpay.gateway import RazorpayGateway

from ..config import settings
from ..core.auth import Principal, client_ip, get_current_principal, require_role
from ..core.ratelimit import check_rate_limit
from ..db.models import ExecutionRecord, Merchant, UserRole
from ..db.session import get_db_session
from ..schemas.recovery import RecoveryRequest

logger = logging.getLogger("recoveryos.recoveries")

router = APIRouter(
    prefix="/recoveries",
    tags=["Recoveries"],
)

IDEMPOTENCY_TTL_SECONDS = 24 * 3600
MIN_ORDER_PAISE = 100          # ₹1
MAX_ORDER_PAISE = 100_000_000  # ₹10,00,000


async def _get_retry_context(
    session: AsyncSession,
    merchant_id: str,
    payment_id: str,
    customer_id: str,
) -> tuple[int, datetime | None, int]:
    """
    Query real execution history to determine:
    - retry_count: how many previous executions exist for this payment
    - first_failure_at: when the earliest execution was created
    - customer_attempts_today: how many executions this customer has today
    """
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


@router.post("/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_recovery(
    request: Request,
    payload: RecoveryRequest,
    principal: Annotated[Principal, Depends(require_role(UserRole.ANALYST))],
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """
    Queue a recovery for asynchronous processing.

    Returns 202 with an execution id the caller polls via /status/{job_id}.
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key header is required"
        )
    if len(idempotency_key) > 200:
        raise HTTPException(status_code=400, detail="Idempotency-Key too long")

    redis = getattr(request.app.state, "redis", None)

    # Writes that can move real money get a tighter, per-user budget than the
    # coarse per-IP ceiling in middleware.
    verdict = await check_rate_limit(
        redis,
        identity=principal.user_id,
        scope="recovery-write",
        limit=settings.rate_limit_write_per_minute,
    )
    if not verdict.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Recovery rate limit exceeded.",
            headers={"Retry-After": str(verdict.reset_after)},
        )

    execution_id = f"exec_{uuid.uuid4().hex[:16]}"

    # Namespaced by merchant so one tenant's idempotency key can never collide
    # with — or read back — another's.
    cache_key = (
        f"idem:{principal.merchant_id}:{payload.payment_id}:{idempotency_key}"
    )

    if redis is not None:
        # SET NX is atomic: exactly one concurrent caller wins the key. The
        # previous GET-then-SET let two simultaneous retries both see an empty
        # cache and both enqueue a job against the same payment.
        won = await redis.set(
            cache_key, execution_id, ex=IDEMPOTENCY_TTL_SECONDS, nx=True
        )
        if not won:
            existing = await redis.get(cache_key)
            if existing:
                return {
                    "execution_id": existing.decode("utf-8"),
                    "status": "processing",
                    "message": "Job already queued (Idempotency match)",
                }

    await request.app.state.arq_pool.enqueue_job(
        "process_recovery_task",
        payload.model_dump(),
        execution_id,
        principal.merchant_id,
        principal.user_id,
        _job_id=execution_id,
    )

    logger.info(
        "recovery queued exec=%s payment=%s merchant=%s by=%s",
        execution_id,
        payload.payment_id,
        principal.merchant_id,
        principal.user_id,
    )

    return {
        "execution_id": execution_id,
        "status": "processing",
        "message": "Recovery queued for async processing",
    }


@router.get("/status/{job_id}")
async def get_job_status(
    request: Request,
    job_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: AsyncSession = Depends(get_db_session),
):
    job = Job(job_id, request.app.state.arq_pool)
    job_status = await job.status()

    if job_status.value == "complete":
        result = await job.result()
        # The queue itself is not tenant-aware, so confirm the finished job's
        # own merchant before handing its result back.
        if isinstance(result, dict) and result.get("merchant_id") not in (
            None,
            principal.merchant_id,
        ):
            raise HTTPException(status_code=404, detail="Job not found")
        return result

    if job_status.value == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "execution_id": job_id,
        "status": "processing",
        "message": f"Job is {job_status.value}",
    }


@router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: AsyncSession = Depends(get_db_session),
):
    repo = PostgresExecutionRepository(session, principal.merchant_id)
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
        "customer_id": execution.customer_id,
        "initiated_by": execution.initiated_by,
    }


@router.post("/create-order")
async def create_razorpay_order(
    request: Request,
    principal: Annotated[Principal, Depends(require_role(UserRole.ANALYST))],
    amount: int = Query(..., ge=MIN_ORDER_PAISE, le=MAX_ORDER_PAISE),
    currency: str = Query(default="INR", pattern="^[A-Z]{3}$"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Creates a real Razorpay order for the frontend Checkout flow.

    Previously this was reachable without credentials and accepted an unbounded
    amount, so anyone could mint orders of any size against the merchant's key.
    """
    merchant = await session.get(Merchant, principal.merchant_id)
    if merchant is not None and amount > merchant.max_auto_recovery_amount:
        raise HTTPException(
            status_code=400,
            detail="Amount exceeds this merchant's configured recovery ceiling",
        )

    gateway = RazorpayGateway(client=request.app.state.razorpay)

    try:
        receipt = f"rcvry_{uuid.uuid4().hex[:12]}"
        order = await gateway.create_retry_order(
            amount=amount,
            currency=currency,
            receipt=receipt,
            notes={
                "source": "recovery_os_dashboard",
                "merchant_id": principal.merchant_id,
                "initiated_by": principal.user_id,
            },
        )

        return {
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "receipt": receipt,
            "key_id": settings.razorpay_key_id,
        }
    except Exception:
        logger.exception("failed to create order merchant=%s", principal.merchant_id)
        raise HTTPException(
            status_code=502,
            detail="Failed to create Razorpay order",
        )
