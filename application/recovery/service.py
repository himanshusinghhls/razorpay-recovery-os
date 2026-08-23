from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from application.execution.authorization import ExecutionAuthorization
from domain.decision.models import RecoveryDecision
from domain.policy.engine import PolicyDecision, RecoveryPolicyEngine
from domain.policy.models import PolicyContext
from domain.recovery.actions import RecoveryAction, RecoveryActionType


@dataclass(frozen=True)
class RecoveryAuthorization:
    """
    Result of attempting to authorize a recovery decision.

    If executable is True, execution_authorization will contain
    explicit authorization for the exact action.
    """

    action: RecoveryAction | None
    policy_decision: PolicyDecision
    executable: bool
    execution_authorization: ExecutionAuthorization | None = None


class RecoveryApplicationService:
    """
    Coordinates recovery decisions and the policy boundary.

    This service does not execute external payment operations.
    """

    def __init__(
        self,
        policy_engine: RecoveryPolicyEngine,
    ):
        self.policy_engine = policy_engine

    def authorize(
        self,
        decision: RecoveryDecision,
        retry_count: int,
        suspicious: bool,
        first_failure_at: Optional[datetime] = None,
        customer_attempts_today: int = 0,
    ) -> RecoveryAuthorization:

        action = decision.action

        if action is None:
            policy_decision = PolicyDecision(
                allowed=False,
                reason="Recovery decision contains no executable action",
                requires_human_approval=False,
            )

            return RecoveryAuthorization(
                action=None,
                policy_decision=policy_decision,
                executable=False,
                execution_authorization=None,
            )

        context = PolicyContext(
            action_type=action.action_type,
            amount=decision.amount,
            retry_count=retry_count,
            suspicious=suspicious,
            first_failure_at=first_failure_at,
            customer_attempts_today=customer_attempts_today,
        )

        policy_decision = self.policy_engine.evaluate(context)

        if not policy_decision.allowed:
            return RecoveryAuthorization(
                action=action,
                policy_decision=policy_decision,
                executable=False,
                execution_authorization=None,
            )

        execution_authorization = ExecutionAuthorization(
            action=action,
            authorization_reason=policy_decision.reason,
        )

        return RecoveryAuthorization(
            action=action,
            policy_decision=policy_decision,
            executable=True,
            execution_authorization=execution_authorization,
        )
