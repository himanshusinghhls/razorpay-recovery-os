from application.execution.repository import ExecutionRepository
from domain.execution.models import ExecutionStatus, RecoveryExecution

class RecoveryReconciliationService:
    """
    Reconciles asynchronous provider webhooks with internal execution state.
    """
    def __init__(self, execution_repo: ExecutionRepository) -> None:
        self.execution_repo = execution_repo

    async def reconcile_payment_captured(self, order_id: str) -> bool:
        """
        Marks a recovery execution as SUCCEEDED if the provider confirms capture.
        Returns True if reconciled, False if no matching execution was found.
        """
        execution = await self.execution_repo.get_by_external_reference(order_id)
        
        if not execution:
            return False

        updated_execution = RecoveryExecution(
            execution_id=execution.execution_id,
            payment_id=execution.payment_id,
            action_type=execution.action_type,
            status=ExecutionStatus.SUCCEEDED,
            external_reference=execution.external_reference,
            message="Payment captured and recovery succeeded via webhook",
        )

        await self.execution_repo.update(updated_execution)
        return True
