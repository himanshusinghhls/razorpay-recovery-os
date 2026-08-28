from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from application.execution.repository import ExecutionRepository
from apps.api.app.db.models import ExecutionRecord
from domain.execution.models import RecoveryExecution


class PostgresExecutionRepository(ExecutionRepository):
    """
    Bound to one merchant. Reads filter on it, writes stamp it.
    """

    def __init__(self, session: AsyncSession, merchant_id: str) -> None:
        self.session = session
        self.merchant_id = merchant_id

    async def create(self, execution: RecoveryExecution) -> None:
        record = ExecutionRecord(
            execution_id=execution.execution_id,
            merchant_id=execution.merchant_id or self.merchant_id,
            payment_id=execution.payment_id,
            customer_id=execution.customer_id,
            action_type=execution.action_type,
            status=execution.status,
            external_reference=execution.external_reference,
            message=execution.message,
            initiated_by=execution.initiated_by,
        )
        self.session.add(record)
        try:
            await self.session.commit()
        except IntegrityError:
            # The primary key already exists. Relying on the constraint rather
            # than a preceding SELECT closes the window where two workers both
            # read "not found" and both insert.
            await self.session.rollback()
            raise ValueError("Execution already exists")

    async def update(self, execution: RecoveryExecution) -> None:
        stmt = select(ExecutionRecord).where(
            ExecutionRecord.execution_id == execution.execution_id,
            ExecutionRecord.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            raise KeyError("Execution does not exist")

        record.status = execution.status
        record.external_reference = execution.external_reference
        record.message = execution.message

        await self.session.commit()

    async def get(self, execution_id: str) -> RecoveryExecution | None:
        stmt = select(ExecutionRecord).where(
            ExecutionRecord.execution_id == execution_id,
            ExecutionRecord.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        return self._to_domain(record) if record else None

    async def get_by_external_reference(self, reference: str) -> RecoveryExecution | None:
        stmt = select(ExecutionRecord).where(
            ExecutionRecord.external_reference == reference,
            ExecutionRecord.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        return self._to_domain(record) if record else None

    @staticmethod
    def _to_domain(record: ExecutionRecord) -> RecoveryExecution:
        return RecoveryExecution(
            execution_id=record.execution_id,
            payment_id=record.payment_id,
            action_type=record.action_type,
            status=record.status,
            external_reference=record.external_reference,
            message=record.message,
            customer_id=record.customer_id,
            merchant_id=record.merchant_id,
            initiated_by=record.initiated_by,
        )


async def resolve_merchant_for_reference(
    session: AsyncSession, reference: str
) -> str | None:
    """
    Find which tenant owns a provider reference, ignoring merchant scoping.

    This is the one deliberate cross-tenant read in the system. Razorpay's
    webhook callback carries an order id and no notion of our merchants, so the
    ingress path has to resolve the owner before it can do anything scoped.
    Everything downstream of this call uses a repository bound to the merchant
    returned here.
    """
    result = await session.execute(
        select(ExecutionRecord.merchant_id).where(
            ExecutionRecord.external_reference == reference
        )
    )
    return result.scalar_one_or_none()
