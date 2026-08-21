from application.execution.executor import RecoveryExecutor
from application.execution.result import ExecutionResult
from domain.recovery.actions import RecoveryAction


class DryRunRecoveryExecutor(RecoveryExecutor):
    """
    Non-destructive executor used for development and testing.

    It records what would have happened without calling any
    external payment provider.
    """

    async def execute(
        self,
        action: RecoveryAction,
    ) -> ExecutionResult:

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
