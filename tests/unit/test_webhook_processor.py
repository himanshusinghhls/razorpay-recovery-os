import pytest
from application.webhooks import InMemoryWebhookEventRepository, WebhookProcessor, RecoveryReconciliationService
from application.execution.in_memory_repository import InMemoryExecutionRepository
from domain.execution.models import RecoveryExecution, ExecutionStatus

@pytest.fixture
def repos():
    return InMemoryWebhookEventRepository(), InMemoryExecutionRepository()

@pytest.mark.asyncio
async def test_processor_saves_event_and_reconciles(repos):
    webhook_repo, exec_repo = repos
    
    exec_record = RecoveryExecution(
        execution_id="exec_123",
        payment_id="pay_failed",
        action_type="retry_payment",
        status=ExecutionStatus.STARTED,
        external_reference="order_success",
        message="Started"
    )
    await exec_repo.create(exec_record)

    reconciler = RecoveryReconciliationService(exec_repo)
    processor = WebhookProcessor(webhook_repo, reconciler)

    payload = {
        "event": "payment.captured", 
        "payload": {"payment": {"entity": {"order_id": "order_success"}}}
    }
    
    processed = await processor.process_razorpay_event("ev_123", payload)
    
    assert processed is True
    
    updated_exec = await exec_repo.get("exec_123")
    assert updated_exec.status == ExecutionStatus.SUCCEEDED

@pytest.mark.asyncio
async def test_processor_ignores_duplicate_event(repos):
    webhook_repo, exec_repo = repos
    reconciler = RecoveryReconciliationService(exec_repo)
    processor = WebhookProcessor(webhook_repo, reconciler)

    payload = {"event": "payment.captured"}
    
    await processor.process_razorpay_event("ev_123", payload)
    processed_again = await processor.process_razorpay_event("ev_123", payload)
    
    assert processed_again is False
