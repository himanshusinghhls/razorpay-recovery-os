from datetime import datetime, timezone
from typing import Any

from application.webhooks.repository import WebhookEventRepository
from domain.events.models import WebhookEvent

class WebhookProcessor:
    """
    Idempotent webhook event processor.
    """

    def __init__(self, repository: WebhookEventRepository) -> None:
        self.repository = repository

    async def process_razorpay_event(
        self,
        event_id: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        Returns True if the event was processed and saved.
        Returns False if the event was a duplicate (already exists).
        """
        if await self.repository.exists(event_id=event_id, provider="razorpay"):
            return False

        event = WebhookEvent(
            event_id=event_id,
            provider="razorpay",
            event_type=payload.get("event", "unknown"),
            payload=payload,
            received_at=datetime.now(timezone.utc),
        )

        await self.repository.save(event)
        return True
