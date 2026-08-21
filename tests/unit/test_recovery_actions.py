import pytest

from domain.recovery.actions import (
    RecoveryAction,
    RecoveryActionType,
)


def test_retry_payment_action_can_be_created():
    action = RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id="pay_test_123",
        customer_id="cust_123",
        amount=4999,
        reason="Temporary payment failure with high recovery probability",
    )

    assert action.action_type == RecoveryActionType.RETRY_PAYMENT
    assert action.payment_id == "pay_test_123"
    assert action.amount == 4999


def test_recovery_action_is_immutable():
    action = RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id="pay_test_123",
        customer_id="cust_123",
        amount=4999,
        reason="Temporary payment failure",
    )

    with pytest.raises(AttributeError):
        action.amount = 100


def test_zero_amount_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        RecoveryAction(
            action_type=RecoveryActionType.RETRY_PAYMENT,
            payment_id="pay_test_123",
            customer_id="cust_123",
            amount=0,
            reason="Invalid test action",
        )


def test_negative_amount_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        RecoveryAction(
            action_type=RecoveryActionType.RETRY_PAYMENT,
            payment_id="pay_test_123",
            customer_id="cust_123",
            amount=-100,
            reason="Invalid test action",
        )


def test_empty_reason_is_rejected():
    with pytest.raises(ValueError, match="reason"):
        RecoveryAction(
            action_type=RecoveryActionType.RETRY_PAYMENT,
            payment_id="pay_test_123",
            customer_id="cust_123",
            amount=4999,
            reason="   ",
        )
