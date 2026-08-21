from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RecoveryStatus(str, Enum):
    DETECTED = "detected"
    ANALYZING = "analyzing"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    RECOVERED = "recovered"
    FAILED = "failed"
    EXPIRED = "expired"


class RecoveryAction(str, Enum):
    RETRY_PAYMENT = "retry_payment"
    CREATE_PAYMENT_LINK = "create_payment_link"
    SEND_REMINDER = "send_reminder"
    ESCALATE = "escalate"
    NO_ACTION = "no_action"


@dataclass
class RecoveryCase:
    id: str
    customer_id: str
    payment_id: Optional[str]
    amount: int
    currency: str
    reason: str
    recovery_probability: float
    expected_recovery: int
    recommended_action: RecoveryAction
    status: RecoveryStatus
