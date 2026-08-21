from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ProviderExecutionOutcome:
    """
    Provider-neutral representation of an execution attempt.
    """

    success: bool
    external_reference: Optional[str]
    message: str
    response: Optional[Any] = None
