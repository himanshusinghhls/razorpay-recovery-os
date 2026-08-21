from typing import Any

from application.execution.authorization import ExecutionAuthorization
from application.execution.executor import RecoveryExecutor
from application.execution.result import ExecutionResult
from integrations.razorpay.execution import RazorpayExecutionGateway


class RazorpayRecoveryExecutor(RecoveryExecutor):
    """
    Recovery executor backed by a Razorpay execution gateway.

    The executor performs an already-authorized recovery action.

    It does not:
    - make policy decisions,
    - authorize actions,
    - charge a customer directly,
    - invoke Razorpay Checkout.

    For RETRY_PAYMENT, it creates a new Razorpay Order that can
    subsequently be presented to the customer through Checkout.
    """

    def __init__(
        self,
        gateway: RazorpayExecutionGateway,
    ) -> None:
        self.gateway = gateway

    async def execute(
        self,
        authorization: ExecutionAuthorization,
    ) -> ExecutionResult:

        action = authorization.action

        if action.payment_id is None:
            return ExecutionResult(
                success=False,
                action_type=action.action_type.value,
                payment_id=None,
                message="Recovery action requires a payment ID",
            )

        if action.amount is None:
            return ExecutionResult(
                success=False,
                action_type=action.action_type.value,
                payment_id=action.payment_id,
                message="Recovery action requires an amount",
            )

        try:
            response: dict[str, Any] = (
                await self.gateway.create_retry_order(
                    amount=action.amount,
                    currency="INR",
                    receipt=(
                        f"recovery_{action.payment_id}"
                    ),
                    notes={
                        "recovery_payment_id": (
                            action.payment_id
                        ),
                        "customer_id": (
                            action.customer_id
                        ),
                    },
                )
            )

        except Exception as exc:
            return ExecutionResult(
                success=False,
                action_type=action.action_type.value,
                payment_id=action.payment_id,
                message=(
                    f"Razorpay order creation failed: {exc}"
                ),
                external_reference=None,
            )

        external_reference = response.get("id")

        return ExecutionResult(
            success=True,
            action_type=action.action_type.value,
            payment_id=action.payment_id,
            message=(
                "Razorpay recovery order created"
            ),
            external_reference=external_reference,
            response=response,
        )
