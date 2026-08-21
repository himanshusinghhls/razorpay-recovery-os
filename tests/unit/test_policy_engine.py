from domain.policy.engine import RecoveryPolicyEngine
from domain.policy.models import PolicyContext
from domain.recovery.actions import RecoveryActionType


def make_context(
    amount=4999,
    retry_count=0,
    suspicious=False,
):
    return PolicyContext(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount=amount,
        retry_count=retry_count,
        suspicious=suspicious,
    )


def test_normal_recovery_is_allowed():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        make_context()
    )

    assert decision.allowed is True
    assert decision.requires_human_approval is False


def test_retry_limit_blocks_action():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        make_context(retry_count=2)
    )

    assert decision.allowed is False
    assert "retry" in decision.reason.lower()


def test_suspicious_transaction_requires_human():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        make_context(suspicious=True)
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is True


def test_high_value_transaction_requires_human():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        make_context(amount=25_000)
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is True


def test_invalid_amount_is_blocked():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        make_context(amount=0)
    )

    assert decision.allowed is False


def test_negative_retry_count_is_blocked():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        make_context(retry_count=-1)
    )

    assert decision.allowed is False
    assert "negative" in decision.reason.lower()
