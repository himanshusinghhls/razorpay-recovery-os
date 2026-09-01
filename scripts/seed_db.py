"""
Seed the database with demo execution and review records.

Run with:
    PYTHONPATH=. ./apps/api/.venv/bin/python scripts/seed_db.py

NOTE: Run scripts/seed_users.py first — it creates the demo merchant that
these records reference.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from apps.api.app.db.models import ExecutionRecord, ReviewRecord
from apps.api.app.db.session import AsyncSessionLocal, engine
from domain.execution.models import ExecutionStatus
from domain.recovery.actions import RecoveryActionType
from domain.review.models import ReviewStatus

DEMO_MERCHANT_ID = "mrch_demo_recoveryos"


async def seed() -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        print("Seeding execution records...")
        for i in range(15):
            status = (
                ExecutionStatus.SUCCEEDED if i < 12 else ExecutionStatus.FAILED
            )
            message = (
                "Recovery successful"
                if status == ExecutionStatus.SUCCEEDED
                else "Policy Blocked: Time window exceeded"
            )

            ex = ExecutionRecord(
                execution_id=f"exec_seed_{i}_{uuid.uuid4().hex[:6]}",
                merchant_id=DEMO_MERCHANT_ID,
                payment_id=f"pay_seed_{i}",
                customer_id=f"cust_seed_{i % 5}",
                action_type=RecoveryActionType.RETRY_PAYMENT.value,
                status=status,
                message=message,
                created_at=now - timedelta(minutes=i * 15),
            )
            session.add(ex)

        print("Seeding pending reviews...")
        rev = ReviewRecord(
            review_id=f"rev_seed_{uuid.uuid4().hex[:6]}",
            merchant_id=DEMO_MERCHANT_ID,
            payment_id="pay_seed_high_value",
            customer_id="cust_seed_vip",
            amount=5000000,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            policy_reason="High value transaction",
            ai_diagnosis="Customer is VIP",
            ai_confidence=0.98,
            status=ReviewStatus.PENDING,
            created_at=now,
        )
        session.add(rev)

        await session.commit()
        print("Database seeded successfully!")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except Exception as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
