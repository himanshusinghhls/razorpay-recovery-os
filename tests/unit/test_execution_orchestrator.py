import pytest

from application.execution import (
    DryRunRecoveryExecutor,
    FailingRecoveryExecutor,
    RecoveryExecutionOrchestrator,
)
from application.recovery.service import RecoveryApplicationService
from domain.decision.models import RecoveryDecision
from domain.policy.engine import RecoveryPolicyEngine
from domain.recovery.actions import (
    RecoveryAction,
    RecoveryActionType,
)


def make_action(amount=4999):
    return RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id="pay_test_123",
        customer_id="cust_test_123",
        amount=amount,
        reason="Temporary payment failure",
    )


def make_decision(
    action=None,
    amount=4999,
):
    if action is None:
        action = make_action(amount=amount)

    return RecoveryDecision(
        payment_id="pay_test_123",
        customer_id="cust_test_123",
        amount=amount,
        recovery_probability=0.82,
        expected_recovery=4099.18,
        diagnosis="Temporary payment failure",
        confidence=0.91,
        action=action,
    )


def make_service():
    return RecoveryApplicationService(
        policy_engine=RecoveryPolicyEngine()
    )


def make_authorization(
    *,
    retry_count=0,
    suspicious=False,
    amount=4999,
):
    service = make_service()

    return service.authorize(
        decision=make_decision(
            action=make_action(amount=amount),
            amount=amount,
        ),
        retry_count=retry_count,
        suspicious=suspicious,
    )


@pytest.mark.asyncio
async def test_authorized_action_is_executed():
    authorization = make_authorization()

    orchestrator = RecoveryExecutionOrchestrator(
        executor=DryRunRecoveryExecutor()
    )

    result = await orchestrator.execute(authorization)

    assert result.success is True
    assert result.action_type == "retry_payment"
    assert result.payment_id == "pay_test_123"
    assert result.response["dry_run"] is True


@pytest.mark.asyncio
async def test_denied_action_is_not_executed():
    authorization = make_authorization(
        suspicious=True,
    )

    orchestrator = RecoveryExecutionOrchestrator(
        executor=DryRunRecoveryExecutor()
    )

    with pytest.raises(
        PermissionError,
        match="not authorized",
    ):
        await orchestrator.execute(authorization)


@pytest.mark.asyncio
async def test_retry_limit_prevents_execution():
    authorization = make_authorization(
        retry_count=2,
    )

    orchestrator = RecoveryExecutionOrchestrator(
        executor=DryRunRecoveryExecutor()
    )

    with pytest.raises(
        PermissionError,
        match="not authorized",
    ):
        await orchestrator.execute(authorization)


@pytest.mark.asyncio
async def test_high_value_action_is_not_executed():
    authorization = make_authorization(
        amount=2500000,
    )

    orchestrator = RecoveryExecutionOrchestrator(
        executor=DryRunRecoveryExecutor()
    )

    with pytest.raises(
        PermissionError,
        match="not authorized",
    ):
        await orchestrator.execute(authorization)


@pytest.mark.asyncio
async def test_authorized_execution_preserves_execution_identity():
    authorization = make_authorization()

    orchestrator = RecoveryExecutionOrchestrator(
        executor=DryRunRecoveryExecutor()
    )

    result = await orchestrator.execute(authorization)

    assert result.action_type == (
        authorization.execution_authorization
        .action.action_type.value
    )

    assert result.payment_id == (
        authorization.execution_authorization
        .action.payment_id
    )


@pytest.mark.asyncio
async def test_executor_failure_is_returned_as_execution_result():
    authorization = make_authorization()

    orchestrator = RecoveryExecutionOrchestrator(
        executor=FailingRecoveryExecutor()
    )

    result = await orchestrator.execute(authorization)

    assert result.success is False
    assert result.action_type == "retry_payment"
    assert result.payment_id == "pay_test_123"
    assert result.message == "Simulated execution failure"


@pytest.mark.asyncio
async def test_failed_execution_has_no_external_reference():
    authorization = make_authorization()

    orchestrator = RecoveryExecutionOrchestrator(
        executor=FailingRecoveryExecutor()
    )

    result = await orchestrator.execute(authorization)

    assert result.success is False
    assert result.external_reference is None


@pytest.mark.asyncio
async def test_failed_execution_contains_provider_failure_metadata():
    authorization = make_authorization()

    orchestrator = RecoveryExecutionOrchestrator(
        executor=FailingRecoveryExecutor()
    )

    result = await orchestrator.execute(authorization)

    assert result.response["simulated_failure"] is True
