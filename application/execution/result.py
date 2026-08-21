from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ExecutionResult:
    """
    Immutable result of attempting to execute a recovery action.

    This represents execution outcome, not policy authorization.
    """

    success: bool
    action_type: str
    payment_id: Optional[str]
    message: str
    external_reference: Optional[str] = None
    response: Optional[Any] = None
