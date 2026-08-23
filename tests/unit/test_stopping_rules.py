import pytest
from datetime import datetime, timedelta, timezone

from domain.policy.engine import RecoveryPolicyEngine
from domain.policy.models import PolicyContext
from domain.recovery.actions import RecoveryActionType


def make_context(
    amount=4999,
    retry_count=0,
    suspicious=False,
    first_failure_at=None,
    customer_attempts_today=0,
):
    return PolicyContext(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount=amount,
        retry_count=retry_count,
        suspicious=suspicious,
        first_failure_at=first_failure_at,
        customer_attempts_today=customer_attempts_today,
    )


class TestTimeWindowStoppingRule:
    """
    Recovery should be blocked after MAX_RECOVERY_WINDOW_HOURS (72h).
    """

    def test_within_time_window_is_allowed(self):
        engine = RecoveryPolicyEngine()

        first_failure = datetime.now(timezone.utc) - timedelta(hours=24)
        context = make_context(first_failure_at=first_failure)

        decision = engine.evaluate(context)
        assert decision.allowed is True

    def test_at_boundary_is_allowed(self):
        engine = RecoveryPolicyEngine()

        first_failure = datetime.now(timezone.utc) - timedelta(hours=71)
        context = make_context(first_failure_at=first_failure)

        decision = engine.evaluate(context)
        assert decision.allowed is True

    def test_expired_window_is_blocked(self):
        engine = RecoveryPolicyEngine()

        first_failure = datetime.now(timezone.utc) - timedelta(hours=73)
        context = make_context(first_failure_at=first_failure)

        decision = engine.evaluate(context)
        assert decision.allowed is False
        assert "expired" in decision.reason.lower()
        assert decision.requires_human_approval is False

    def test_no_first_failure_skips_check(self):
        engine = RecoveryPolicyEngine()

        context = make_context(first_failure_at=None)

        decision = engine.evaluate(context)
        assert decision.allowed is True


class TestCustomerDailyCapRule:
    """
    No more than MAX_CUSTOMER_DAILY_ATTEMPTS per customer per day.
    """

    def test_under_daily_cap_is_allowed(self):
        engine = RecoveryPolicyEngine()

        context = make_context(customer_attempts_today=3)

        decision = engine.evaluate(context)
        assert decision.allowed is True

    def test_at_daily_cap_is_blocked(self):
        engine = RecoveryPolicyEngine()

        context = make_context(customer_attempts_today=5)

        decision = engine.evaluate(context)
        assert decision.allowed is False
        assert "daily" in decision.reason.lower()

    def test_over_daily_cap_is_blocked(self):
        engine = RecoveryPolicyEngine()

        context = make_context(customer_attempts_today=10)

        decision = engine.evaluate(context)
        assert decision.allowed is False

    def test_negative_attempts_rejected(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            make_context(customer_attempts_today=-1)


class TestRulePriorityOrder:
    """
    Ensure rules are evaluated in the correct priority order.
    """

    def test_retry_limit_takes_priority_over_time_window(self):
        engine = RecoveryPolicyEngine()

        context = make_context(
            retry_count=3,
            first_failure_at=datetime.now(timezone.utc) - timedelta(hours=100),
        )

        decision = engine.evaluate(context)
        assert decision.allowed is False
        assert "retry" in decision.reason.lower()

    def test_suspicious_takes_priority_over_daily_cap(self):
        engine = RecoveryPolicyEngine()

        context = make_context(
            suspicious=True,
            customer_attempts_today=10,
        )

        decision = engine.evaluate(context)
        assert decision.allowed is False
        assert decision.requires_human_approval is True
        assert "suspicious" in decision.reason.lower()
