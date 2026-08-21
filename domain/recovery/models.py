from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class RecoveryStatus(str, Enum):
    DETECTED = "detected"
    DIAGNOSING = "diagnosing"
    READY = "ready"
    BLOCKED = "blocked"
    APPROVED = "approved"
    EXECUTING = "executing"
    RECOVERED = "recovered"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class RecoveryCase:
    id: str
    customer_id: str
    payment_id: str
    amount: Decimal
    currency: str
    reason: str
    status: RecoveryStatus
    created_at: datetime
