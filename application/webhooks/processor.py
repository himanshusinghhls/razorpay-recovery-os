from datetime import datetime, timezone
from typing import Any

from application.webhooks.repository import WebhookEventRepository
from application.webhooks.reconciler import RecoveryReconciliationService
from domain.events.models import WebhookEvent

class WebhookProcessor:
    """
    Idempotent webhook event processor that triggers reconciliation.
    """

    def __init__(
        self, 
        repository: WebhookEventRepository,
        reconciler: RecoveryReconciliationService
    ) -> None:
        self.repository = repository
        self.reconciler = reconciler

    async def process_razorpay_event(
        self,
        event_id: str,
        payload: dict[str, Any],
    ) -> bool:
        if await self.repository.exists(event_id=event_id, provider="razorpay"):
            return False

        event_type = payload.get("event", "unknown")
        
        event = WebhookEvent(
            event_id=event_id,
            provider="razorpay",
            event_type=event_type,
            payload=payload,
            received_at=datetime.now(timezone.utc),
        )

        # Save event idempotently
        await self.repository.save(event)

        # Reconcile business state
        if event_type == "payment.captured":
            order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
            if order_id:
                await self.reconciler.reconcile_payment_captured(order_id)

        return True
