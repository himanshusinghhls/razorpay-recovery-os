import pytest

from application.recovery.service import RecoveryApplicationService
from domain.decision.models import RecoveryDecision
from domain.policy.engine import RecoveryPolicyEngine
from domain.recovery.actions import (
    RecoveryAction,
    RecoveryActionType,
)


def make_action(
    amount=4999,
    action_type=RecoveryActionType.RETRY_PAYMENT,
):
    return RecoveryAction(
        action_type=action_type,
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


def test_normal_recovery_is_authorized():
    service = make_service()

    authorization = service.authorize(
        decision=make_decision(),
        retry_count=0,
        suspicious=False,
    )

    assert authorization.executable is True
    assert authorization.policy_decision.allowed is True
    assert authorization.policy_decision.requires_human_approval is False


def test_retry_limit_prevents_execution():
    service = make_service()

    authorization = service.authorize(
        decision=make_decision(),
        retry_count=2,
        suspicious=False,
    )

    assert authorization.executable is False
    assert authorization.policy_decision.allowed is False
    assert "retry" in authorization.policy_decision.reason.lower()


def test_suspicious_recovery_requires_human_approval():
    service = make_service()

    authorization = service.authorize(
        decision=make_decision(),
        retry_count=0,
        suspicious=True,
    )

    assert authorization.executable is False
    assert authorization.policy_decision.allowed is False
    assert authorization.policy_decision.requires_human_approval is True


def test_high_value_recovery_requires_human_approval():
    action = make_action(amount=25_000)
    decision = make_decision(
        action=action,
        amount=25_000,
    )

    service = make_service()

    authorization = service.authorize(
        decision=decision,
        retry_count=0,
        suspicious=False,
    )

    assert authorization.executable is False
    assert authorization.policy_decision.requires_human_approval is True


def test_missing_action_is_rejected():
    decision = RecoveryDecision(
        payment_id="pay_test_123",
        customer_id="cust_test_123",
        amount=4999,
        recovery_probability=0.82,
        expected_recovery=4099.18,
        diagnosis="Temporary payment failure",
        confidence=0.91,
        action=None,
    )

    service = make_service()

    with pytest.raises(
        ValueError,
        match="does not contain a proposed action",
    ):
        service.authorize(
            decision=decision,
            retry_count=0,
            suspicious=False,
        )


def test_action_payment_id_must_match_decision():
    action = RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id="pay_DIFFERENT",
        customer_id="cust_test_123",
        amount=4999,
        reason="Temporary payment failure",
    )

    decision = make_decision(action=action)

    service = make_service()

    with pytest.raises(
        ValueError,
        match="payment_id",
    ):
        service.authorize(
            decision=decision,
            retry_count=0,
            suspicious=False,
        )


def test_action_customer_id_must_match_decision():
    action = RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id="pay_test_123",
        customer_id="cust_DIFFERENT",
        amount=4999,
        reason="Temporary payment failure",
    )

    decision = make_decision(action=action)

    service = make_service()

    with pytest.raises(
        ValueError,
        match="customer_id",
    ):
        service.authorize(
            decision=decision,
            retry_count=0,
            suspicious=False,
        )


def test_action_amount_must_match_decision():
    action = make_action(amount=4999)

    decision = make_decision(
        action=action,
        amount=10_000,
    )

    service = make_service()

    with pytest.raises(
        ValueError,
        match="amount",
    ):
        service.authorize(
            decision=decision,
            retry_count=0,
            suspicious=False,
        )


def test_authorization_is_immutable():
    service = make_service()

    authorization = service.authorize(
        decision=make_decision(),
        retry_count=0,
        suspicious=False,
    )

    with pytest.raises(AttributeError):
        authorization.action = make_action()
