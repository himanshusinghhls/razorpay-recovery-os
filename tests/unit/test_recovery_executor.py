import pytest

from application.execution.authorization import ExecutionAuthorization
from application.execution.dry_run import DryRunRecoveryExecutor
from domain.recovery.actions import (
    RecoveryAction,
    RecoveryActionType,
)


def make_action():
    return RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id="pay_test_123",
        customer_id="cust_123",
        amount=4999,
        reason="Temporary payment failure",
    )


def make_authorization():
    return ExecutionAuthorization(
        action=make_action(),
        authorization_reason="Action satisfies recovery policy",
    )


@pytest.mark.asyncio
async def test_dry_run_executor_succeeds():
    executor = DryRunRecoveryExecutor()

    result = await executor.execute(
        make_authorization()
    )

    assert result.success is True
    assert result.action_type == "retry_payment"
    assert result.payment_id == "pay_test_123"
    assert result.external_reference is None
    assert result.response["dry_run"] is True


@pytest.mark.asyncio
async def test_dry_run_executor_does_not_create_external_reference():
    executor = DryRunRecoveryExecutor()

    result = await executor.execute(
        make_authorization()
    )

    assert result.external_reference is None


@pytest.mark.asyncio
async def test_dry_run_executor_preserves_action_identity():
    executor = DryRunRecoveryExecutor()

    authorization = make_authorization()

    result = await executor.execute(authorization)

    assert result.action_type == (
        authorization.action.action_type.value
    )

    assert result.payment_id == (
        authorization.action.payment_id
    )
