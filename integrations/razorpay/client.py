from typing import Any

import httpx

from apps.api.app.config import settings


class RazorpayClient:
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            auth=(
                settings.razorpay_key_id,
                settings.razorpay_key_secret,
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=20.0,
                write=20.0,
                pool=5.0,
            ),
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
            ),
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def fetch_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        response = await self.client.get(
            f"/payments/{payment_id}"
        )
        response.raise_for_status()
        return response.json()

    async def fetch_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        response = await self.client.get(
            f"/orders/{order_id}"
        )
        response.raise_for_status()
        return response.json()

    async def create_order(
        self,
        *,
        amount: int,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:

        payload: dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
        }

        if notes:
            payload["notes"] = notes

        response = await self.client.post(
            "/orders",
            json=payload,
        )

        response.raise_for_status()

        return response.json()
