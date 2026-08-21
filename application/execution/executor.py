from abc import ABC, abstractmethod

from application.execution.authorization import ExecutionAuthorization
from application.execution.result import ExecutionResult


class RecoveryExecutor(ABC):
    """
    Boundary for executing already-authorized recovery actions.

    Executors do not make policy decisions.

    They receive explicit execution authorization.
    """

    @abstractmethod
    async def execute(
        self,
        authorization: ExecutionAuthorization,
    ) -> ExecutionResult:
        """
        Execute an already-authorized recovery action.
        """
        raise NotImplementedError
