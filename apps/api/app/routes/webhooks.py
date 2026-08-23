import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db.session import get_db_session
from application.webhooks.processor import WebhookProcessor
from application.webhooks.repository import PostgresWebhookEventRepository
from application.webhooks.reconciler import RecoveryReconciliationService
from application.execution.postgres_repository import PostgresExecutionRepository
from integrations.razorpay.verification import RazorpaySignatureVerifier

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)

@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    if not x_razorpay_signature or not x_razorpay_event_id:
        raise HTTPException(status_code=400, detail="Missing Razorpay headers")

    raw_body = await request.body()
    verifier = RazorpaySignatureVerifier(settings.razorpay_webhook_secret)

    if not verifier.verify_webhook_signature(raw_body=raw_body, signature=x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    webhook_repo = PostgresWebhookEventRepository(session)
    execution_repo = PostgresExecutionRepository(session)
    reconciler = RecoveryReconciliationService(execution_repo)
    processor = WebhookProcessor(repository=webhook_repo, reconciler=reconciler)

    processed = await processor.process_razorpay_event(
        event_id=x_razorpay_event_id,
        payload=payload,
    )

    return {"accepted": True, "event_id": x_razorpay_event_id, "duplicate": not processed}
