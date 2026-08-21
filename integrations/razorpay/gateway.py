from typing import Any

from integrations.razorpay.client import RazorpayClient


class RazorpayGateway:
    """
    Concrete Razorpay provider gateway.

    This is the only layer that knows how the application
    talks to Razorpay's HTTP API.
    """

    def __init__(
        self,
        client: RazorpayClient,
    ) -> None:
        self.client = client

    async def create_retry_order(
        self,
        *,
        amount: int,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self.client.create_order(
            amount=amount,
            currency=currency,
            receipt=receipt,
            notes=notes,
        )
