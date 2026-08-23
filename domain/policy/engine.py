from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from domain.policy.models import PolicyContext


@dataclass(frozen=True)
class PolicyDecision:
    """
    Immutable result of a policy evaluation.

    The policy engine is a deterministic safety boundary.
    """

    allowed: bool
    reason: str
    requires_human_approval: bool


class RecoveryPolicyEngine:
    """
    Deterministic safety boundary for autonomous recovery actions.

    The LLM/agent may propose an action, but it cannot override
    this policy engine.
    """

    MAX_RETRY_ATTEMPTS = 2
    HIGH_VALUE_THRESHOLD = 2500000
    MAX_RECOVERY_WINDOW_HOURS = 72
    MAX_CUSTOMER_DAILY_ATTEMPTS = 5

    def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyDecision:

        if context.amount <= 0:
            return PolicyDecision(
                allowed=False,
                reason="Transaction amount must be greater than zero",
                requires_human_approval=False,
            )

        if context.retry_count < 0:
            return PolicyDecision(
                allowed=False,
                reason="Retry count cannot be negative",
                requires_human_approval=False,
            )

        if context.retry_count >= self.MAX_RETRY_ATTEMPTS:
            return PolicyDecision(
                allowed=False,
                reason="Maximum retry attempts exceeded",
                requires_human_approval=False,
            )

        if context.suspicious:
            return PolicyDecision(
                allowed=False,
                reason="Suspicious activity requires manual review",
                requires_human_approval=True,
            )

        if context.amount >= self.HIGH_VALUE_THRESHOLD:
            return PolicyDecision(
                allowed=False,
                reason="High-value transaction requires merchant approval",
                requires_human_approval=True,
            )

        if context.first_failure_at is not None:
            now = datetime.now(timezone.utc)
            failure_time = context.first_failure_at
            if failure_time.tzinfo is None:
                failure_time = failure_time.replace(tzinfo=timezone.utc)

            elapsed = now - failure_time
            if elapsed > timedelta(hours=self.MAX_RECOVERY_WINDOW_HOURS):
                return PolicyDecision(
                    allowed=False,
                    reason=(
                        f"Recovery window expired: "
                        f"{elapsed.total_seconds() / 3600:.0f}h elapsed, "
                        f"max is {self.MAX_RECOVERY_WINDOW_HOURS}h"
                    ),
                    requires_human_approval=False,
                )

        if context.customer_attempts_today >= self.MAX_CUSTOMER_DAILY_ATTEMPTS:
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"Customer daily attempt limit reached: "
                    f"{context.customer_attempts_today} attempts today, "
                    f"max is {self.MAX_CUSTOMER_DAILY_ATTEMPTS}"
                ),
                requires_human_approval=False,
            )

        return PolicyDecision(
            allowed=True,
            reason="Action satisfies recovery policy",
            requires_human_approval=False,
        )

