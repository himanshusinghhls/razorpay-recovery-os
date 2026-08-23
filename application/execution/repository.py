from abc import ABC, abstractmethod

from domain.execution.models import RecoveryExecution

class ExecutionRepository(ABC):
    @abstractmethod
    async def create(self, execution: RecoveryExecution) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, execution: RecoveryExecution) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, execution_id: str) -> RecoveryExecution | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_external_reference(self, reference: str) -> RecoveryExecution | None:
        raise NotImplementedError
