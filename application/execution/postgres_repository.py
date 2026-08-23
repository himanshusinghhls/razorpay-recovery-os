from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.execution.repository import ExecutionRepository
from apps.api.app.db.models import ExecutionRecord
from domain.execution.models import RecoveryExecution

class PostgresExecutionRepository(ExecutionRepository):
    """
    Production PostgreSQL persistence for recovery executions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        execution: RecoveryExecution,
    ) -> None:
        
        # Enforce application-level uniqueness constraint
        existing = await self.get(execution.execution_id)
        if existing:
            raise ValueError("Execution already exists")

        record = ExecutionRecord(
            execution_id=execution.execution_id,
            payment_id=execution.payment_id,
            action_type=execution.action_type,
            status=execution.status,
            external_reference=execution.external_reference,
            message=execution.message,
        )
        self.session.add(record)
        await self.session.commit()

    async def update(
        self,
        execution: RecoveryExecution,
    ) -> None:
        
        stmt = select(ExecutionRecord).where(
            ExecutionRecord.execution_id == execution.execution_id
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise KeyError("Execution does not exist")

        record.status = execution.status
        record.external_reference = execution.external_reference
        record.message = execution.message

        await self.session.commit()

    async def get(
        self,
        execution_id: str,
    ) -> RecoveryExecution | None:
        
        stmt = select(ExecutionRecord).where(
            ExecutionRecord.execution_id == execution_id
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return None

        return RecoveryExecution(
            execution_id=record.execution_id,
            payment_id=record.payment_id,
            action_type=record.action_type,
            status=record.status,
            external_reference=record.external_reference,
            message=record.message,
        )
