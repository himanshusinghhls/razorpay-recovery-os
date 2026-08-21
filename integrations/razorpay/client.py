import httpx

from apps.api.app.config import settings


class RazorpayClient:
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            auth=(
                settings.razorpay_key_id,
                settings.razorpay_key_secret,
            ),
            timeout=20.0,
        )

    async def close(self):
        await self.client.aclose()

    async def fetch_payment(self, payment_id: str):
        response = await self.client.get(
            f"/payments/{payment_id}"
        )

        response.raise_for_status()

        return response.json()

    async def fetch_order(self, order_id: str):
        response = await self.client.get(
            f"/orders/{order_id}"
        )

        response.raise_for_status()

        return response.json()
