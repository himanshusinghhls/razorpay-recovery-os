from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
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
    HIGH_VALUE_THRESHOLD = 25_000
    MAX_RECOVERY_WINDOW_DAYS = 7

    def evaluate(
        self,
        amount: int,
        retry_count: int,
        suspicious: bool,
    ) -> PolicyDecision:

        # ---------------------------------------------------------
        # 1. Validate financial amount
        # ---------------------------------------------------------
        if amount <= 0:
            return PolicyDecision(
                allowed=False,
                reason="Transaction amount must be greater than zero",
                requires_human_approval=False,
            )

        # ---------------------------------------------------------
        # 2. Validate retry count
        # ---------------------------------------------------------
        if retry_count < 0:
            return PolicyDecision(
                allowed=False,
                reason="Retry count cannot be negative",
                requires_human_approval=False,
            )

        # ---------------------------------------------------------
        # 3. Enforce retry limit
        # ---------------------------------------------------------
        if retry_count >= self.MAX_RETRY_ATTEMPTS:
            return PolicyDecision(
                allowed=False,
                reason="Maximum retry attempts exceeded",
                requires_human_approval=False,
            )

        # ---------------------------------------------------------
        # 4. Suspicious transactions require human review
        # ---------------------------------------------------------
        if suspicious:
            return PolicyDecision(
                allowed=False,
                reason="Suspicious activity requires manual review",
                requires_human_approval=True,
            )

        # ---------------------------------------------------------
        # 5. High-value transactions require merchant approval
        # ---------------------------------------------------------
        if amount >= self.HIGH_VALUE_THRESHOLD:
            return PolicyDecision(
                allowed=False,
                reason="High-value transaction requires merchant approval",
                requires_human_approval=True,
            )

        # ---------------------------------------------------------
        # 6. Otherwise the action is allowed
        # ---------------------------------------------------------
        return PolicyDecision(
            allowed=True,
            reason="Action satisfies recovery policy",
            requires_human_approval=False,
        )
