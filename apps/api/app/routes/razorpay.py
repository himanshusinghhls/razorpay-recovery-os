from fastapi import APIRouter, Request

router = APIRouter(prefix="/razorpay", tags=["Razorpay"])


@router.get("/health")
async def razorpay_health(request: Request):
    client = request.app.state.razorpay

    response = await client.client.get("/payments")

    return {
        "authenticated": response.status_code == 200,
        "status_code": response.status_code,
    }
