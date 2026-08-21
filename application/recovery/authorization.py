from dataclasses import dataclass

from domain.policy.engine import PolicyDecision
from domain.recovery.actions import RecoveryAction


@dataclass(frozen=True)
class RecoveryAuthorization:
    """
    Result of passing a recovery action through the policy boundary.

    This object authorizes an action conceptually.

    It does NOT execute the action.
    """

    action: RecoveryAction
    policy_decision: PolicyDecision

    @property
    def executable(self) -> bool:
        """
        An action is executable only when policy explicitly allows it
        and human approval is not required.
        """
        return (
            self.policy_decision.allowed
            and not self.policy_decision.requires_human_approval
        )
