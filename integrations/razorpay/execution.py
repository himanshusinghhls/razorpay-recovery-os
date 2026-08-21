from typing import Any, Protocol


class RazorpayExecutionGateway(Protocol):
    """
    Provider-facing execution contract.

    Application code depends on this abstraction rather than
    Razorpay HTTP details.
    """

    async def create_retry_order(
        self,
        *,
        amount: int,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new Razorpay Order for a recovery attempt.

        This does not charge the customer.

        The returned order must subsequently be used by the
        customer-facing Razorpay Checkout/payment flow.
        """
        ...
