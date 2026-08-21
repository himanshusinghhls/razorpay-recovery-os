from domain.decision.models import RecoveryDecision
from domain.policy.engine import PolicyDecision, RecoveryPolicyEngine
from domain.policy.models import PolicyContext
from domain.recovery.actions import RecoveryAction

from application.recovery.authorization import RecoveryAuthorization


class RecoveryApplicationService:
    """
    Application-level coordinator for recovery authorization.

    Responsibilities:

    1. Validate the proposed action against the recovery decision.
    2. Build explicit policy context.
    3. Pass the context through the deterministic policy engine.
    4. Return an authorization result.

    This service does NOT execute payments.
    It does NOT call Razorpay.
    It does NOT call an LLM.
    """

    def __init__(
        self,
        policy_engine: RecoveryPolicyEngine,
    ) -> None:
        self.policy_engine = policy_engine

    def authorize(
        self,
        decision: RecoveryDecision,
        retry_count: int,
        suspicious: bool,
    ) -> RecoveryAuthorization:

        action = decision.action

        if action is None:
            raise ValueError(
                "Recovery decision does not contain a proposed action"
            )

        self._validate_action_matches_decision(
            decision=decision,
            action=action,
        )

        context = PolicyContext(
            action_type=action.action_type,
            amount=action.amount,
            retry_count=retry_count,
            suspicious=suspicious,
        )

        policy_decision = self.policy_engine.evaluate(context)

        return RecoveryAuthorization(
            action=action,
            policy_decision=policy_decision,
        )

    @staticmethod
    def _validate_action_matches_decision(
        decision: RecoveryDecision,
        action: RecoveryAction,
    ) -> None:

        if action.payment_id != decision.payment_id:
            raise ValueError(
                "Recovery action payment_id does not match decision payment_id"
            )

        if action.customer_id != decision.customer_id:
            raise ValueError(
                "Recovery action customer_id does not match decision customer_id"
            )

        if action.amount != decision.amount:
            raise ValueError(
                "Recovery action amount does not match decision amount"
            )
