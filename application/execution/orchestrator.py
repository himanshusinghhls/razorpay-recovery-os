from application.execution.executor import RecoveryExecutor
from application.execution.result import ExecutionResult
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.recovery.service import RecoveryAuthorization


class RecoveryExecutionOrchestrator:
    """
    Coordinates execution of an already-authorized recovery action.

    Responsibilities:

    1. Accept the result of the recovery authorization boundary.
    2. Refuse execution when policy did not authorize the action.
    3. Pass explicit ExecutionAuthorization to the executor.
    4. Return the executor's ExecutionResult.

    This class does NOT:
    - make policy decisions,
    - call an LLM,
    - modify recovery decisions,
    - construct execution authorization itself.
    """

    def __init__(
        self,
        executor: RecoveryExecutor,
    ) -> None:
        self.executor = executor

    async def execute(
        self,
        authorization: "RecoveryAuthorization",
    ) -> ExecutionResult:

        if not authorization.executable:
            raise PermissionError(
                "Recovery action is not authorized for execution"
            )

        execution_authorization = (
            authorization.execution_authorization
        )

        if execution_authorization is None:
            raise PermissionError(
                "Executable recovery authorization is missing "
                "execution authorization"
            )

        return await self.executor.execute(
            execution_authorization
        )
