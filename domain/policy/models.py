from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.recovery.actions import RecoveryActionType


@dataclass(frozen=True)
class PolicyContext:
    """
    Immutable context supplied to the policy engine.

    The policy engine makes decisions from explicit facts.
    It does not fetch data or call external services.
    """

    action_type: RecoveryActionType
    amount: int
    retry_count: int
    suspicious: bool
    first_failure_at: Optional[datetime] = None
    customer_attempts_today: int = 0
    is_contact_action: bool = False
    contact_count: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, RecoveryActionType):
            raise TypeError(
                "action_type must be a RecoveryActionType"
            )

        if self.amount <= 0:
            raise ValueError(
                "Policy amount must be greater than zero"
            )

        if self.retry_count < 0:
            raise ValueError(
                "Policy retry count cannot be negative"
            )

        if self.customer_attempts_today < 0:
            raise ValueError(
                "Customer attempts today cannot be negative"
            )

        if self.contact_count < 0:
            raise ValueError(
                "Contact count cannot be negative"
            )

