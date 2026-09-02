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

    customer_id: str = ""

    merchant_id: str = ""

    initiated_by: Optional[str] = None
