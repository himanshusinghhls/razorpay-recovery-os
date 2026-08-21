from application.recovery.service import RecoveryApplicationService
from domain.decision.models import RecoveryDecision
from domain.policy.engine import RecoveryPolicyEngine
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


def make_decision():
    action = make_action()

    return RecoveryDecision(
        payment_id="pay_test_123",
        customer_id="cust_123",
        amount=4999,
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


def test_allowed_action_gets_execution_authorization():
    service = make_service()

    authorization = service.authorize(
        decision=make_decision(),
        retry_count=0,
        suspicious=False,
    )

    assert authorization.executable is True
    assert authorization.policy_decision.allowed is True
    assert authorization.execution_authorization is not None


def test_execution_authorization_contains_exact_action():
    service = make_service()
    decision = make_decision()

    authorization = service.authorize(
        decision=decision,
        retry_count=0,
        suspicious=False,
    )

    assert authorization.execution_authorization is not None
    assert authorization.execution_authorization.action is decision.action


def test_suspicious_action_gets_no_execution_authorization():
    service = make_service()

    authorization = service.authorize(
        decision=make_decision(),
        retry_count=0,
        suspicious=True,
    )

    assert authorization.executable is False
    assert authorization.execution_authorization is None
    assert authorization.policy_decision.requires_human_approval is True


def test_retry_limit_gets_no_execution_authorization():
    service = make_service()

    authorization = service.authorize(
        decision=make_decision(),
        retry_count=2,
        suspicious=False,
    )

    assert authorization.executable is False
    assert authorization.execution_authorization is None


def test_decision_without_action_cannot_execute():
    decision = RecoveryDecision(
        payment_id="pay_test_123",
        customer_id="cust_123",
        amount=4999,
        recovery_probability=0.82,
        expected_recovery=4099.18,
        diagnosis="Temporary payment failure",
        confidence=0.91,
        action=None,
    )

    service = make_service()

    authorization = service.authorize(
        decision=decision,
        retry_count=0,
        suspicious=False,
    )

    assert authorization.executable is False
    assert authorization.execution_authorization is None
    assert authorization.policy_decision.allowed is False
