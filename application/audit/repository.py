from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db.models import AuditRecord
from domain.audit.models import AuditEntry, AuditEventType


class AuditRepository(ABC):
    @abstractmethod
    async def save(self, entry: AuditEntry, *, actor: str = "system") -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_payment_id(self, payment_id: str) -> list[AuditEntry]:
        raise NotImplementedError

    @abstractmethod
    async def get_recent(self, limit: int = 50) -> list[AuditEntry]:
        raise NotImplementedError


class PostgresAuditRepository(AuditRepository):
    """
    Bound to a single merchant so reads can never cross a tenant boundary and
    writes are always stamped with the owning merchant.
    """

    def __init__(self, session: AsyncSession, merchant_id: str) -> None:
        self.session = session
        self.merchant_id = merchant_id

    async def save(self, entry: AuditEntry, *, actor: str = "system") -> None:
        record = AuditRecord(
            merchant_id=self.merchant_id,
            payment_id=entry.payment_id,
            customer_id=entry.customer_id,
            event_type=entry.event_type,
            data=entry.data,
            actor=actor,
        )
        self.session.add(record)
        await self.session.flush()

    async def get_by_payment_id(self, payment_id: str) -> list[AuditEntry]:
        stmt = (
            select(AuditRecord)
            .where(
                AuditRecord.merchant_id == self.merchant_id,
                AuditRecord.payment_id == payment_id,
            )
            .order_by(AuditRecord.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_recent(self, limit: int = 50) -> list[AuditEntry]:
        stmt = (
            select(AuditRecord)
            .where(AuditRecord.merchant_id == self.merchant_id)
            .order_by(AuditRecord.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    @staticmethod
    def _to_domain(record: AuditRecord) -> AuditEntry:
        return AuditEntry(
            payment_id=record.payment_id,
            customer_id=record.customer_id,
            event_type=record.event_type,
            data=record.data,
            created_at=record.created_at,
            actor=record.actor,
        )
