from fastapi import APIRouter

from integrations.razorpay.client import RazorpayClient

router = APIRouter(prefix="/razorpay", tags=["Razorpay"])


@router.get("/health")
async def razorpay_health():
    client = RazorpayClient()

    try:
        response = await client.client.get("/payments")

        return {
            "authenticated": response.status_code == 200,
            "status_code": response.status_code,
        }

    finally:
        await client.close()
