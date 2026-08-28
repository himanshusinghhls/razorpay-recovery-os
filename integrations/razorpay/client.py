import logging
import ssl
from typing import Any

import httpx

from apps.api.app.config import settings

logger = logging.getLogger("recoveryos.razorpay")


def _build_ssl_context() -> ssl.SSLContext:
    """
    Trust the operating system's certificate store when available.

    certifi alone does not know about the private root CAs that corporate TLS
    proxies present, so on those networks every outbound call to Razorpay fails
    with CERTIFICATE_VERIFY_FAILED. truststore delegates to the OS trust store
    (macOS Keychain, Windows CryptoAPI, system CAs on Linux), which does. Note
    this changes which CAs are trusted, never whether verification happens.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        logger.debug("truststore unavailable; using certifi bundle")
        return httpx.create_ssl_context()


class RazorpayClient:
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            verify=_build_ssl_context(),
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
