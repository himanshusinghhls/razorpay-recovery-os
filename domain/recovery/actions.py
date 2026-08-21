from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RecoveryActionType(str, Enum):
    RETRY_PAYMENT = "retry_payment"
    SEND_PAYMENT_LINK = "send_payment_link"
    SEND_REMINDER = "send_reminder"
    ESCALATE = "escalate"
    STOP = "stop"


@dataclass
class RecoveryAction:
    action_type: RecoveryActionType
    reason: str
    expected_recovery: int
    requires_human_approval: bool
    idempotency_key: Optional[str] = None
