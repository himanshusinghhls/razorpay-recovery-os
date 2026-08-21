from abc import ABC, abstractmethod

from domain.execution.models import RecoveryExecution


class ExecutionRepository(ABC):
    """
    Persistence boundary for recovery executions.

    The application layer does not depend on PostgreSQL,
    Redis, or any concrete storage implementation.
    """

    @abstractmethod
    async def create(
        self,
        execution: RecoveryExecution,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        execution: RecoveryExecution,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        execution_id: str,
    ) -> RecoveryExecution | None:
        raise NotImplementedError
