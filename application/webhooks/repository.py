from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db.models import WebhookRecord
from domain.events.models import WebhookEvent

class WebhookEventRepository(ABC):
    @abstractmethod
    async def exists(self, event_id: str, provider: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def save(self, event: WebhookEvent) -> None:
        raise NotImplementedError

class PostgresWebhookEventRepository(WebhookEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, event_id: str, provider: str) -> bool:
        stmt = select(WebhookRecord.event_id).where(
            WebhookRecord.event_id == event_id,
            WebhookRecord.provider == provider
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save(self, event: WebhookEvent) -> None:
        record = WebhookRecord(
            event_id=event.event_id,
            provider=event.provider,
            event_type=event.event_type,
            payload=event.payload,
            received_at=event.received_at,
        )
        self.session.add(record)
        await self.session.commit()
