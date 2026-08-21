from dataclasses import dataclass


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    requires_human_approval: bool


class RecoveryPolicyEngine:

    MAX_RETRY_ATTEMPTS = 2
    HIGH_VALUE_THRESHOLD = 25_000
    MAX_RECOVERY_WINDOW_DAYS = 7

    def evaluate(
        self,
        amount: int,
        retry_count: int,
        suspicious: bool,
    ) -> PolicyDecision:

        if retry_count >= self.MAX_RETRY_ATTEMPTS:
            return PolicyDecision(
                allowed=False,
                reason="Maximum retry attempts exceeded",
                requires_human_approval=False,
            )

        if suspicious:
            return PolicyDecision(
                allowed=False,
                reason="Suspicious activity requires manual review",
                requires_human_approval=True,
            )

        if amount >= self.HIGH_VALUE_THRESHOLD:
            return PolicyDecision(
                allowed=False,
                reason="High-value transaction requires merchant approval",
                requires_human_approval=True,
            )

        return PolicyDecision(
            allowed=True,
            reason="Action satisfies recovery policy",
            requires_human_approval=False,
        )
