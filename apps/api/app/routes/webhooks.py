import json

from fastapi import APIRouter, Header, HTTPException, Request

from ..config import settings
from integrations.razorpay.verification import (
    RazorpaySignatureVerifier,
)


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(
        default=None,
    ),
    x_razorpay_event_id: str | None = Header(
        default=None,
    ),
):
    if not x_razorpay_signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay signature",
        )

    if not x_razorpay_event_id:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay event ID",
        )

    raw_body = await request.body()

    verifier = RazorpaySignatureVerifier(
        settings.razorpay_webhook_secret,
    )

    valid = verifier.verify_webhook_signature(
        raw_body=raw_body,
        signature=x_razorpay_signature,
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid Razorpay webhook signature",
        )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    event = payload.get("event")

    return {
        "accepted": True,
        "event_id": x_razorpay_event_id,
        "event": event,
    }
