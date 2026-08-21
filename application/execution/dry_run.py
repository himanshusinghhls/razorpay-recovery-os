from application.execution.authorization import ExecutionAuthorization
from application.execution.executor import RecoveryExecutor
from application.execution.result import ExecutionResult


class DryRunRecoveryExecutor(RecoveryExecutor):
    """
    Safe executor used for development and testing.

    It never calls an external payment provider.
    """

    async def execute(
        self,
        authorization: ExecutionAuthorization,
    ) -> ExecutionResult:

        action = authorization.action

        return ExecutionResult(
            success=True,
            action_type=action.action_type.value,
            payment_id=action.payment_id,
            message=(
                f"Dry-run execution completed for "
                f"{action.action_type.value}"
            ),
            external_reference=None,
            response={
                "dry_run": True,
                "action_type": action.action_type.value,
                "payment_id": action.payment_id,
                "customer_id": action.customer_id,
                "amount": action.amount,
            },
        )
