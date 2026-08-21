from dataclasses import dataclass
from typing import Optional

from domain.recovery.actions import RecoveryAction


@dataclass(frozen=True)
class RecoveryDecision:
    """
    Decision produced by the recovery analysis layer.

    This is a decision, not an execution result.
    """

    payment_id: str
    customer_id: str
    amount: int

    recovery_probability: float
    expected_recovery: float

    diagnosis: str
    confidence: float

    action: Optional[RecoveryAction]

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Decision amount must be greater than zero")

        if not 0.0 <= self.recovery_probability <= 1.0:
            raise ValueError(
                "Recovery probability must be between 0 and 1"
            )

        if self.expected_recovery < 0:
            raise ValueError(
                "Expected recovery cannot be negative"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Confidence must be between 0 and 1"
            )

        if not self.diagnosis.strip():
            raise ValueError("Diagnosis cannot be empty")
