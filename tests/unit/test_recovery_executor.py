import pytest

from application.execution import DryRunRecoveryExecutor
from domain.recovery.actions import (
    RecoveryAction,
    RecoveryActionType,
)


def make_action():
    return RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id="pay_test_123",
        customer_id="cust_test_123",
        amount=4999,
        reason="Temporary payment failure",
    )


@pytest.mark.asyncio
async def test_dry_run_executor_succeeds():
    executor = DryRunRecoveryExecutor()

    result = await executor.execute(make_action())

    assert result.success is True
    assert result.action_type == "retry_payment"
    assert result.payment_id == "pay_test_123"
    assert result.response["dry_run"] is True


@pytest.mark.asyncio
async def test_dry_run_executor_does_not_create_external_reference():
    executor = DryRunRecoveryExecutor()

    result = await executor.execute(make_action())

    assert result.external_reference is None


@pytest.mark.asyncio
async def test_dry_run_executor_preserves_action_identity():
    executor = DryRunRecoveryExecutor()

    action = make_action()
    result = await executor.execute(action)

    assert result.action_type == action.action_type.value
    assert result.payment_id == action.payment_id
