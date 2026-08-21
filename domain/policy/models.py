from dataclasses import dataclass

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
