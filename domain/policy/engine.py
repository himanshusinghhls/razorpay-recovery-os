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
    this policy engine. Seven independent rules are evaluated in
    priority order. The first failing rule short-circuits.

    Gate system:
    - Retry cap: max 2 retries per payment
    - Fraud/suspicious: escalate to human
    - High-value: escalate to human
    - Recovery window: 72-hour expiry
    - Daily customer cap: max 5 attempts/day
    - Contact window: IST 09:00–21:00 for customer-facing actions
    - Frequency cap: max 3 contacts per payment
    """

    MAX_RETRY_ATTEMPTS = 2
    HIGH_VALUE_THRESHOLD = 2500000
    MAX_RECOVERY_WINDOW_HOURS = 72
    MAX_CUSTOMER_DAILY_ATTEMPTS = 5
    CONTACT_WINDOW_START_IST = 9
    CONTACT_WINDOW_END_IST = 21
    MAX_CONTACT_FREQUENCY = 3

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

        if context.is_contact_action:
            now_utc = datetime.now(timezone.utc)
            ist = timezone(timedelta(hours=5, minutes=30))
            now_ist = now_utc.astimezone(ist)
            hour_ist = now_ist.hour
            if not (self.CONTACT_WINDOW_START_IST <= hour_ist < self.CONTACT_WINDOW_END_IST):
                return PolicyDecision(
                    allowed=False,
                    reason=(
                        f"Customer contact blocked outside business hours "
                        f"(IST {self.CONTACT_WINDOW_START_IST}:00–"
                        f"{self.CONTACT_WINDOW_END_IST}:00, "
                        f"current: {now_ist.strftime('%H:%M')} IST)"
                    ),
                    requires_human_approval=False,
                )

        if context.is_contact_action and context.contact_count >= self.MAX_CONTACT_FREQUENCY:
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"Contact frequency limit reached: "
                    f"{context.contact_count} contacts sent, "
                    f"max is {self.MAX_CONTACT_FREQUENCY}"
                ),
                requires_human_approval=False,
            )

        return PolicyDecision(
            allowed=True,
            reason="Action satisfies all recovery policy gates",
            requires_human_approval=False,
        )

