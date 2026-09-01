from typing import Annotated

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..core.auth import Principal, get_current_principal
from integrations.razorpay.verification import (
    RazorpaySignatureVerifier,
)


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str = Field(min_length=1)
    razorpay_payment_id: str = Field(min_length=1)
    razorpay_signature: str = Field(min_length=1)


@router.post("/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    verifier = RazorpaySignatureVerifier(
        settings.razorpay_key_secret,
    )

    valid = verifier.verify_payment_signature(
        order_id=request.razorpay_order_id,
        payment_id=request.razorpay_payment_id,
        signature=request.razorpay_signature,
    )

    if not valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature",
        )

    return {
        "verified": True,
        "order_id": request.razorpay_order_id,
        "payment_id": request.razorpay_payment_id,
    }
