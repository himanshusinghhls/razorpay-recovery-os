import pytest
from application.webhooks import InMemoryWebhookEventRepository, WebhookProcessor

@pytest.mark.asyncio
async def test_processor_saves_new_event():
    repo = InMemoryWebhookEventRepository()
    processor = WebhookProcessor(repo)

    payload = {"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_123"}}}}
    
    processed = await processor.process_razorpay_event("ev_123", payload)
    
    assert processed is True
    assert await repo.exists("ev_123", "razorpay") is True

@pytest.mark.asyncio
async def test_processor_ignores_duplicate_event():
    repo = InMemoryWebhookEventRepository()
    processor = WebhookProcessor(repo)

    payload = {"event": "payment.captured"}
    
    # First attempt
    await processor.process_razorpay_event("ev_123", payload)
    
    # Second attempt (duplicate webhook delivery)
    processed_again = await processor.process_razorpay_event("ev_123", payload)
    
    assert processed_again is False
