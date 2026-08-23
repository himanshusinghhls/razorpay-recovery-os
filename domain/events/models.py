from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class WebhookEvent:
    """
    Immutable representation of an incoming provider webhook.
    """
    event_id: str
    provider: str
    event_type: str
    payload: dict[str, Any]
    received_at: datetime
