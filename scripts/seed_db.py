import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, ".")
from apps.api.app.config import settings
from apps.api.app.db.models import ExecutionRecord, ReviewRecord, AuditRecord, AuditEventType
from domain.execution.models import ExecutionStatus
from domain.recovery.actions import RecoveryActionType
from domain.review.models import ReviewStatus

async def seed():
    db_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://")
    engine = create_async_engine(db_url)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    now = datetime.now(timezone.utc)
    
    async with AsyncSessionLocal() as session:
        print("Seeding execution records...")
        for i in range(15):
            status = ExecutionStatus.SUCCEEDED if i < 12 else ExecutionStatus.FAILED
            message = "Recovery successful" if status == ExecutionStatus.SUCCEEDED else "Policy Blocked: Time window exceeded"
            
            ex = ExecutionRecord(
                execution_id=f"exec_seed_{i}_{uuid.uuid4().hex[:6]}",
                payment_id=f"pay_seed_{i}",
                customer_id=f"cust_seed_{i%5}",
                action_type=RecoveryActionType.RETRY_PAYMENT.value,
                status=status,
                message=message,
                created_at=now - timedelta(minutes=i*15)
            )
            session.add(ex)
            

            
        print("Seeding pending reviews...")
        rev = ReviewRecord(
            review_id=f"rev_seed_{uuid.uuid4().hex[:6]}",
            payment_id="pay_seed_high_value",
            customer_id="cust_seed_vip",
            amount=5000000,
            action_type=RecoveryActionType.RETRY_PAYMENT.value,
            policy_reason="High value transaction",
            ai_diagnosis="Customer is VIP",
            ai_confidence=0.98,
            status=ReviewStatus.PENDING,
            created_at=now
        )
        session.add(rev)
        
        await session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
