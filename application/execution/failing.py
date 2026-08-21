from application.execution.authorization import ExecutionAuthorization
from application.execution.result import ExecutionResult
from application.execution.executor import RecoveryExecutor


class FailingRecoveryExecutor(RecoveryExecutor):
    """
    Deterministic executor used to test execution failure handling.

    It simulates a provider/executor failure without making
    any external network call.
    """

    async def execute(
        self,
        authorization: ExecutionAuthorization,
    ) -> ExecutionResult:

        action = authorization.action

        return ExecutionResult(
            success=False,
            action_type=action.action_type.value,
            payment_id=action.payment_id,
            message="Simulated execution failure",
            external_reference=None,
            response={
                "dry_run": False,
                "simulated_failure": True,
            },
        )
