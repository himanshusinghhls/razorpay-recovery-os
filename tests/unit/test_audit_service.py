import pytest
from unittest.mock import AsyncMock

from application.audit.service import AuditService
from domain.audit.models import AuditEntry, AuditEventType


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def audit_service(mock_repo):
    return AuditService(repository=mock_repo)


@pytest.mark.asyncio
async def test_log_failure_detected(audit_service, mock_repo):
    await audit_service.log_failure_detected(
        payment_id="pay_123",
        customer_id="cust_456",
        amount=50000,
        failure_reason="insufficient_funds",
    )

    mock_repo.save.assert_called_once()
    entry = mock_repo.save.call_args[0][0]
    assert isinstance(entry, AuditEntry)
    assert entry.event_type == AuditEventType.FAILURE_DETECTED
    assert entry.payment_id == "pay_123"
    assert entry.data["amount"] == 50000
    assert entry.data["failure_reason"] == "insufficient_funds"


@pytest.mark.asyncio
async def test_log_ai_diagnosis(audit_service, mock_repo):
    await audit_service.log_ai_diagnosis(
        payment_id="pay_123",
        customer_id="cust_456",
        diagnosis="Temporary insufficient funds",
        confidence=0.92,
        recovery_probability=0.85,
        recommended_action="retry_payment",
        expected_recovery=42500.0,
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.AI_DIAGNOSIS
    assert entry.data["confidence"] == 0.92
    assert entry.data["recommended_action"] == "retry_payment"


@pytest.mark.asyncio
async def test_log_policy_decision(audit_service, mock_repo):
    await audit_service.log_policy_decision(
        payment_id="pay_123",
        customer_id="cust_456",
        allowed=False,
        reason="High-value transaction requires merchant approval",
        requires_human_approval=True,
        retry_count=1,
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.POLICY_DECISION
    assert entry.data["allowed"] is False
    assert entry.data["requires_human_approval"] is True


@pytest.mark.asyncio
async def test_log_execution_success(audit_service, mock_repo):
    await audit_service.log_execution_result(
        payment_id="pay_123",
        customer_id="cust_456",
        execution_id="exec_abc",
        success=True,
        action_type="retry_payment",
        message="Razorpay order created",
        external_reference="order_xyz",
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.EXECUTION_SUCCEEDED
    assert entry.data["execution_id"] == "exec_abc"
    assert entry.data["external_reference"] == "order_xyz"


@pytest.mark.asyncio
async def test_log_execution_failure(audit_service, mock_repo):
    await audit_service.log_execution_result(
        payment_id="pay_123",
        customer_id="cust_456",
        execution_id="exec_fail",
        success=False,
        action_type="retry_payment",
        message="Provider unavailable",
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.EXECUTION_FAILED


@pytest.mark.asyncio
async def test_log_escalation(audit_service, mock_repo):
    await audit_service.log_escalation(
        payment_id="pay_123",
        customer_id="cust_456",
        review_id="review_abc",
        reason="High-value transaction",
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.ESCALATED_TO_REVIEW
    assert entry.data["review_id"] == "review_abc"


@pytest.mark.asyncio
async def test_log_review_approved(audit_service, mock_repo):
    await audit_service.log_review_decision(
        payment_id="pay_123",
        customer_id="cust_456",
        review_id="review_abc",
        approved=True,
        resolved_by="merchant",
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.REVIEW_APPROVED


@pytest.mark.asyncio
async def test_log_review_rejected(audit_service, mock_repo):
    await audit_service.log_review_decision(
        payment_id="pay_123",
        customer_id="cust_456",
        review_id="review_abc",
        approved=False,
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.REVIEW_REJECTED


@pytest.mark.asyncio
async def test_log_stopping_rule(audit_service, mock_repo):
    await audit_service.log_stopping_rule(
        payment_id="pay_123",
        customer_id="cust_456",
        rule_name="time_window",
        reason="Recovery window expired",
    )

    entry = mock_repo.save.call_args[0][0]
    assert entry.event_type == AuditEventType.STOPPING_RULE_TRIGGERED
    assert entry.data["rule_name"] == "time_window"
