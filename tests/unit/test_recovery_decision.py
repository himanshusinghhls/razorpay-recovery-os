import pytest

from domain.decision.models import RecoveryDecision
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


def test_valid_recovery_decision():
    decision = RecoveryDecision(
        payment_id="pay_test_123",
        customer_id="cust_123",
        amount=4999,
        recovery_probability=0.82,
        expected_recovery=4099.18,
        diagnosis="Temporary payment failure",
        confidence=0.91,
        action=make_action(),
    )

    assert decision.recovery_probability == 0.82
    assert decision.expected_recovery == 4099.18
    assert decision.action is not None


def test_probability_cannot_exceed_one():
    with pytest.raises(ValueError, match="between 0 and 1"):
        RecoveryDecision(
            payment_id="pay_test_123",
            customer_id="cust_123",
            amount=4999,
            recovery_probability=1.2,
            expected_recovery=4999,
            diagnosis="Temporary failure",
            confidence=0.9,
            action=make_action(),
        )


def test_probability_cannot_be_negative():
    with pytest.raises(ValueError, match="between 0 and 1"):
        RecoveryDecision(
            payment_id="pay_test_123",
            customer_id="cust_123",
            amount=4999,
            recovery_probability=-0.1,
            expected_recovery=0,
            diagnosis="Temporary failure",
            confidence=0.9,
            action=make_action(),
        )


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValueError, match="between 0 and 1"):
        RecoveryDecision(
            payment_id="pay_test_123",
            customer_id="cust_123",
            amount=4999,
            recovery_probability=0.8,
            expected_recovery=3999,
            diagnosis="Temporary failure",
            confidence=1.5,
            action=make_action(),
        )


def test_empty_diagnosis_is_rejected():
    with pytest.raises(ValueError, match="Diagnosis"):
        RecoveryDecision(
            payment_id="pay_test_123",
            customer_id="cust_123",
            amount=4999,
            recovery_probability=0.8,
            expected_recovery=3999,
            diagnosis="   ",
            confidence=0.9,
            action=make_action(),
        )
