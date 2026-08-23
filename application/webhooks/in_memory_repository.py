from application.webhooks.repository import WebhookEventRepository
from domain.events.models import WebhookEvent

class InMemoryWebhookEventRepository(WebhookEventRepository):
    """
    Test/dev repository for webhook events.
    """

    def __init__(self) -> None:
        self.events: dict[tuple[str, str], WebhookEvent] = {}

    async def exists(self, event_id: str, provider: str) -> bool:
        return (event_id, provider) in self.events

    async def save(self, event: WebhookEvent) -> None:
        self.events[(event.event_id, event.provider)] = event
