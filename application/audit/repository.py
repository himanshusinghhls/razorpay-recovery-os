from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db.models import AuditRecord
from domain.audit.models import AuditEntry, AuditEventType


class AuditRepository(ABC):
    @abstractmethod
    async def save(self, entry: AuditEntry) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_payment_id(self, payment_id: str) -> list[AuditEntry]:
        raise NotImplementedError

    @abstractmethod
    async def get_recent(self, limit: int = 50) -> list[AuditEntry]:
        raise NotImplementedError


class PostgresAuditRepository(AuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, entry: AuditEntry) -> None:
        record = AuditRecord(
            payment_id=entry.payment_id,
            customer_id=entry.customer_id,
            event_type=entry.event_type,
            data=entry.data,
        )
        self.session.add(record)
        await self.session.flush()

    async def get_by_payment_id(self, payment_id: str) -> list[AuditEntry]:
        stmt = (
            select(AuditRecord)
            .where(AuditRecord.payment_id == payment_id)
            .order_by(AuditRecord.created_at.asc())
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [self._to_domain(r) for r in records]

    async def get_recent(self, limit: int = 50) -> list[AuditEntry]:
        stmt = (
            select(AuditRecord)
            .order_by(AuditRecord.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [self._to_domain(r) for r in records]

    @staticmethod
    def _to_domain(record: AuditRecord) -> AuditEntry:
        return AuditEntry(
            payment_id=record.payment_id,
            customer_id=record.customer_id,
            event_type=record.event_type,
            data=record.data,
            created_at=record.created_at,
        )
