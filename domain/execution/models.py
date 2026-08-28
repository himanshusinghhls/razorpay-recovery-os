from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExecutionStatus(str, Enum):
    CREATED = "created"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RecoveryExecution:
    """
    Immutable record describing one recovery execution attempt.
    """

    execution_id: str
    payment_id: str
    action_type: str
    status: ExecutionStatus
    external_reference: Optional[str]
    message: str

    # Required for the per-customer daily stopping rule to work. Previously
    # this was never persisted, so the rule counted attempts against an empty
    # customer_id and could never fire.
    customer_id: str = ""

    # Owning tenant. Set by the caller from the authenticated principal.
    merchant_id: str = ""

    # User id when a human triggered the recovery, else None.
    initiated_by: Optional[str] = None
