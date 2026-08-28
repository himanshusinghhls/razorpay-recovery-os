import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

import yaml
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from application.recovery.service import RecoveryApplicationService
from domain.decision.models import RecoveryDecision
from domain.execution.models import ExecutionStatus
from domain.policy.engine import RecoveryPolicyEngine
from domain.policy.models import PolicyContext
from domain.recovery.actions import RecoveryAction, RecoveryActionType
from domain.review.models import ReviewStatus

from ..config import PROJECT_ROOT
from ..core.auth import Principal, get_current_principal
from ..db.models import AuditRecord, ExecutionRecord, ReviewRecord
from ..db.session import get_db_session

# Anchored to the project root rather than the process CWD, which previously
# made this endpoint depend on where uvicorn happened to be launched from.
TAXONOMY_PATH = PROJECT_ROOT / "domain" / "policy" / "taxonomy.yaml"


class PolicySimulateRequest(BaseModel):
    action_type: str
    amount: int = Field(ge=0, le=100_000_000)
    retry_count: int = Field(ge=0, le=100)
    suspicious: bool
    customer_attempts_today: int = Field(ge=0, le=1000)
    is_contact_action: bool
    contact_count: int = Field(ge=0, le=1000)
    hours_since_first_failure: Optional[int] = Field(default=None, ge=0, le=10_000)


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@lru_cache(maxsize=1)
def _load_taxonomy() -> dict:
    """Parsed once per process — the file is static at runtime."""
    with open(TAXONOMY_PATH, "r") as f:
        return yaml.safe_load(f) or {}


@router.get("/summary")
async def get_analytics_summary(
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Real-time analytics summary powered by actual PostgreSQL data.

    Every aggregate is scoped to the caller's merchant, so one tenant can never
    see another's recovery volume or transactions.
    """
    mid = principal.merchant_id

    # One round trip for the execution-status breakdown instead of three
    # separate COUNT queries against the same table.
    status_rows = await session.execute(
        select(ExecutionRecord.status, func.count())
        .where(ExecutionRecord.merchant_id == mid)
        .group_by(ExecutionRecord.status)
    )
    by_status = {status: count for status, count in status_rows.all()}

    total_executions = sum(by_status.values())
    successful = by_status.get(ExecutionStatus.STARTED, 0) + by_status.get(
        ExecutionStatus.SUCCEEDED, 0
    )
    failed = by_status.get(ExecutionStatus.FAILED, 0)

    pending_reviews = (
        await session.execute(
            select(func.count()).where(
                ReviewRecord.merchant_id == mid,
                ReviewRecord.status == ReviewStatus.PENDING,
            )
        )
    ).scalar() or 0

    total_audit_entries = (
        await session.execute(
            select(func.count()).where(AuditRecord.merchant_id == mid)
        )
    ).scalar() or 0

    recovery_rate = (
        round(successful / total_executions * 100, 1) if total_executions > 0 else 0.0
    )

    recent_result = await session.execute(
        select(ExecutionRecord)
        .where(ExecutionRecord.merchant_id == mid)
        .order_by(ExecutionRecord.created_at.desc())
        .limit(20)
    )
    recent_records = recent_result.scalars().all()

    recent_transactions = [
        {
            "execution_id": r.execution_id,
            "payment_id": r.payment_id,
            "action_type": r.action_type,
            "status": r.status.value,
            "message": r.message,
            "external_reference": r.external_reference,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent_records
    ]

    policy_blocks = (
        await session.execute(
            select(func.count()).where(
                ExecutionRecord.merchant_id == mid,
                ExecutionRecord.status == ExecutionStatus.FAILED,
                ExecutionRecord.message.ilike("%policy%"),
            )
        )
    ).scalar() or 0

    unsafe_rate = (
        round(policy_blocks / total_executions * 100, 2) if total_executions > 0 else 0.0
    )

    # Amount actually put back in play, from the reviews the tenant escalated.
    recovered_paise = (
        await session.execute(
            select(func.coalesce(func.sum(ReviewRecord.amount), 0)).where(
                ReviewRecord.merchant_id == mid,
                ReviewRecord.status == ReviewStatus.APPROVED,
            )
        )
    ).scalar() or 0

    return {
        "merchant_id": mid,
        "total_executions": total_executions,
        "successful_recoveries": successful,
        "failed_recoveries": failed,
        "recovery_rate_percent": recovery_rate,
        "pending_reviews": pending_reviews,
        "total_audit_entries": total_audit_entries,
        "unsafe_action_rate": unsafe_rate,
        "approved_recovery_paise": int(recovered_paise),
        "recent_transactions": recent_transactions,
    }


# Fixed so the published figures are reproducible. The benchmark is a
# measurement, not a lottery: with the module-level `random` it drew a fresh
# batch every call, so the headline numbers moved on every run and could never
# be checked against the ones in the README.
DEFAULT_BENCHMARK_SEED = 20260824


def _run_benchmark(count: int = 50_000, seed: int = DEFAULT_BENCHMARK_SEED) -> dict:
    """
    Pure-CPU batch evaluation over a deterministic synthetic batch.

    Deliberately synchronous and executed off the event loop by the caller —
    running this inline blocked every other request for the duration.
    """
    rng = random.Random(seed)
    taxonomy = _load_taxonomy()
    classes = taxonomy.get("classes", {})

    reasons: list[str] = []
    weights: list[float] = []
    prob_map: dict[str, float] = {}

    for reason, cfg in classes.items():
        reasons.append(reason)
        weights.append(cfg.get("simulation_weight", 0.0))
        prob_map[reason] = cfg.get("ai_recovery_probability", 0.0)

    policy_engine = RecoveryPolicyEngine()
    app_service = RecoveryApplicationService(policy_engine=policy_engine)

    baseline_recovered = 0.0
    ai_recovered = 0.0
    policy_blocks = 0
    escalations = 0

    picks = rng.choices(reasons, weights=weights, k=count)

    for i in range(count):
        reason = picks[i]
        amount = rng.randint(100, 24_000) * 100
        retry_count = rng.randint(0, 3)

        if reason in ("temporary_network_timeout", "insufficient_funds") and retry_count < 2:
            baseline_recovered += amount * 0.5

        ai_prob = prob_map.get(reason, 0.0)
        is_suspicious = reason == "suspected_fraud"

        hallucinated = rng.random() < 0.04
        should_retry = ai_prob > 0 and (retry_count < 2 or hallucinated)

        action = RecoveryAction(
            action_type=(
                RecoveryActionType.RETRY_PAYMENT
                if should_retry
                else RecoveryActionType.STOP_RECOVERY
            ),
            payment_id=f"pay_synth_{i}",
            customer_id=f"cust_synth_{i}",
            amount=amount,
            reason="Simulated AI decision",
        )

        decision = RecoveryDecision(
            payment_id=action.payment_id,
            customer_id=action.customer_id,
            amount=amount,
            recovery_probability=ai_prob,
            expected_recovery=amount * ai_prob,
            diagnosis="Simulated batch evaluation",
            confidence=0.9,
            action=action,
        )

        authorization = app_service.authorize(
            decision=decision,
            retry_count=retry_count,
            suspicious=is_suspicious,
        )

        if not authorization.executable:
            if action.action_type != RecoveryActionType.STOP_RECOVERY:
                policy_blocks += 1
            if authorization.policy_decision.requires_human_approval:
                escalations += 1
        elif ai_prob > 0:
            ai_recovered += amount * ai_prob

    uplift = (
        ((ai_recovered - baseline_recovered) / baseline_recovered) * 100
        if baseline_recovered > 0
        else 0
    )

    return {
        "total_events": count,
        "seed": seed,
        "baseline_recovery_paise": baseline_recovered,
        "ai_recovery_paise": ai_recovered,
        "incremental_uplift_percent": round(uplift, 1),
        "policy_blocks": policy_blocks,
        "escalations": escalations,
        "unsafe_action_rate": round(policy_blocks / count * 100, 2) if count else 0.0,
    }


@router.post("/simulate-benchmark")
async def run_benchmark_simulation(
    principal: Annotated[Principal, Depends(get_current_principal)],
    seed: int = Query(
        default=DEFAULT_BENCHMARK_SEED,
        description="Change to draw a different synthetic batch",
    ),
):
    """
    50,000 event benchmark simulation against the deterministic policy engine.

    Same seed always yields the same figures. Offloaded to a worker thread so
    the API stays responsive while it runs.
    """
    return await run_in_threadpool(_run_benchmark, 50_000, seed)


@router.post("/simulate-policy")
async def simulate_policy(
    req: PolicySimulateRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    """
    Playground endpoint: evaluate context against the deterministic policy engine.
    """
    first_failure = None
    if req.hours_since_first_failure is not None:
        first_failure = datetime.now(timezone.utc) - timedelta(
            hours=req.hours_since_first_failure
        )

    try:
        action_enum = RecoveryActionType(req.action_type)
    except ValueError:
        return {"error": f"Invalid action_type: {req.action_type}"}

    context = PolicyContext(
        action_type=action_enum,
        amount=req.amount,
        retry_count=req.retry_count,
        suspicious=req.suspicious,
        first_failure_at=first_failure,
        customer_attempts_today=req.customer_attempts_today,
        is_contact_action=req.is_contact_action,
        contact_count=req.contact_count,
    )

    decision = RecoveryPolicyEngine().evaluate(context)

    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "requires_human_approval": decision.requires_human_approval,
    }


@router.get("/taxonomy")
async def get_taxonomy(
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    try:
        return _load_taxonomy()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "classes": {}}
