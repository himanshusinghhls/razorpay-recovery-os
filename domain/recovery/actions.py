from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RecoveryActionType(str, Enum):
    """
    Explicit set of actions that RecoveryOS can request.

    The executor will eventually map these actions to concrete
    Razorpay/API operations.
    """

    RETRY_PAYMENT = "retry_payment"
    SEND_PAYMENT_LINK = "send_payment_link"
    SEND_REMINDER = "send_reminder"
    ESCALATE_TO_MERCHANT = "escalate_to_merchant"
    STOP_RECOVERY = "stop_recovery"


@dataclass(frozen=True)
class RecoveryAction:
    """
    Immutable action proposed by the recovery decision layer.

    This object represents intent.

    It does NOT execute anything.
    """

    action_type: RecoveryActionType
    payment_id: Optional[str]
    customer_id: Optional[str]
    amount: int
    reason: str

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Recovery action amount must be greater than zero")

        if not self.reason.strip():
            raise ValueError("Recovery action reason cannot be empty")
