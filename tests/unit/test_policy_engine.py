from domain.policy.engine import RecoveryPolicyEngine


def test_normal_recovery_is_allowed():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=4999,
        retry_count=0,
        suspicious=False,
    )

    assert decision.allowed is True
    assert decision.requires_human_approval is False


def test_retry_limit_blocks_action():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=4999,
        retry_count=2,
        suspicious=False,
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is False
    assert "retry" in decision.reason.lower()


def test_suspicious_transaction_requires_human():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=4999,
        retry_count=0,
        suspicious=True,
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is True


def test_high_value_transaction_requires_human():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=25000,
        retry_count=0,
        suspicious=False,
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is True


def test_invalid_amount_is_blocked():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=0,
        retry_count=0,
        suspicious=False,
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is False


def test_negative_amount_is_blocked():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=-100,
        retry_count=0,
        suspicious=False,
    )

    assert decision.allowed is False


def test_negative_retry_count_is_blocked():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=4999,
        retry_count=-1,
        suspicious=False,
    )

    assert decision.allowed is False


def test_amount_just_below_high_value_threshold_is_allowed():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=24999,
        retry_count=0,
        suspicious=False,
    )

    assert decision.allowed is True
    assert decision.requires_human_approval is False


def test_high_value_threshold_is_inclusive():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=25000,
        retry_count=0,
        suspicious=False,
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is True


def test_second_retry_is_allowed():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=4999,
        retry_count=1,
        suspicious=False,
    )

    assert decision.allowed is True


def test_suspicious_takes_priority_over_high_value():
    engine = RecoveryPolicyEngine()

    decision = engine.evaluate(
        amount=50000,
        retry_count=0,
        suspicious=True,
    )

    assert decision.allowed is False
    assert decision.requires_human_approval is True
    assert "suspicious" in decision.reason.lower()
