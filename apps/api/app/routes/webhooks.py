import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from application.execution.postgres_repository import (
    PostgresExecutionRepository,
    resolve_merchant_for_reference,
)
from application.webhooks.processor import WebhookProcessor
from application.webhooks.reconciler import RecoveryReconciliationService
from application.webhooks.repository import PostgresWebhookEventRepository
from integrations.razorpay.verification import RazorpaySignatureVerifier

from ..config import settings
from ..db.session import get_db_session

logger = logging.getLogger("recoveryos.webhooks")

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)

MAX_WEBHOOK_BYTES = 1_048_576


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Unauthenticated by design — Razorpay cannot present our JWT. The HMAC
    signature over the raw body is what authenticates the caller, so it is
    verified before the payload is parsed or touched.
    """
    if not settings.razorpay_webhook_secret:
        logger.error("webhook received but RAZORPAY_WEBHOOK_SECRET is not configured")
        raise HTTPException(status_code=503, detail="Webhook processing not configured")

    if not x_razorpay_signature or not x_razorpay_event_id:
        raise HTTPException(status_code=400, detail="Missing Razorpay headers")

    raw_body = await request.body()
    if len(raw_body) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")

    verifier = RazorpaySignatureVerifier(settings.razorpay_webhook_secret)
    if not verifier.verify_webhook_signature(
        raw_body=raw_body, signature=x_razorpay_signature
    ):
        logger.warning("rejected webhook with invalid signature id=%s", x_razorpay_event_id)
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    order_id = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
        .get("order_id")
    )
    merchant_id = (
        await resolve_merchant_for_reference(session, order_id) if order_id else None
    )

    webhook_repo = PostgresWebhookEventRepository(session)
    execution_repo = PostgresExecutionRepository(session, merchant_id or "")
    reconciler = RecoveryReconciliationService(execution_repo)
    processor = WebhookProcessor(repository=webhook_repo, reconciler=reconciler)

    processed = await processor.process_razorpay_event(
        event_id=x_razorpay_event_id,
        payload=payload,
    )

    return {
        "accepted": True,
        "event_id": x_razorpay_event_id,
        "duplicate": not processed,
    }
