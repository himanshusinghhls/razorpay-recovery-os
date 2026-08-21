from domain.execution.models import RecoveryExecution

from application.execution.repository import (
    ExecutionRepository,
)


class InMemoryExecutionRepository(
    ExecutionRepository
):
    """
    Test/dev repository.

    This will later be replaced by PostgreSQL persistence.
    """

    def __init__(self) -> None:
        self.items: dict[
            str,
            RecoveryExecution,
        ] = {}

    async def create(
        self,
        execution: RecoveryExecution,
    ) -> None:
        if execution.execution_id in self.items:
            raise ValueError(
                "Execution already exists"
            )

        self.items[
            execution.execution_id
        ] = execution

    async def update(
        self,
        execution: RecoveryExecution,
    ) -> None:
        if execution.execution_id not in self.items:
            raise KeyError(
                "Execution does not exist"
            )

        self.items[
            execution.execution_id
        ] = execution

    async def get(
        self,
        execution_id: str,
    ) -> RecoveryExecution | None:
        return self.items.get(execution_id)
