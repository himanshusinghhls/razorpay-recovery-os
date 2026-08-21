from abc import ABC, abstractmethod

from application.execution.result import ExecutionResult
from domain.recovery.actions import RecoveryAction


class RecoveryExecutor(ABC):
    """
    Boundary for executing already-authorized recovery actions.

    Executors must not perform policy decisions.
    """

    @abstractmethod
    async def execute(
        self,
        action: RecoveryAction,
    ) -> ExecutionResult:
        """
        Execute an already-authorized recovery action.
        """
        raise NotImplementedError
