from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ..core.auth import Principal, require_role
from ..db.models import UserRole

router = APIRouter(prefix="/razorpay", tags=["Razorpay"])


@router.get("/health")
async def razorpay_health(
    request: Request,
    principal: Annotated[Principal, Depends(require_role(UserRole.ADMIN))],
):
    """
    Confirms the platform's Razorpay credentials still authenticate.

    Admin-only: it reports on the validity of a shared secret, and an
    unauthenticated version would let anyone probe credential state.
    """
    response = await request.app.state.razorpay.client.get("/payments")

    return {
        "authenticated": response.status_code == 200,
        "status_code": response.status_code,
    }
