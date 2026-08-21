from dataclasses import dataclass

from domain.recovery.actions import RecoveryAction


@dataclass(frozen=True)
class ExecutionAuthorization:
    """
    Immutable proof that a specific recovery action has passed
    the application policy boundary.

    Executors should receive this object rather than relying on
    an arbitrary boolean supplied by callers.
    """

    action: RecoveryAction
    authorization_reason: str

    def __post_init__(self) -> None:
        if not self.authorization_reason.strip():
            raise ValueError(
                "Authorization reason cannot be empty"
            )
