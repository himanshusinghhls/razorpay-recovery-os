from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AuditEventType(str, Enum):
    """
    Every discrete step in the recovery pipeline that must be recorded.
    """

    FAILURE_DETECTED = "failure_detected"
    AI_DIAGNOSIS = "ai_diagnosis"
    POLICY_DECISION = "policy_decision"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_SUCCEEDED = "execution_succeeded"
    EXECUTION_FAILED = "execution_failed"
    ESCALATED_TO_REVIEW = "escalated_to_review"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    WEBHOOK_RECEIVED = "webhook_received"
    RECOVERY_RECONCILED = "recovery_reconciled"
    STOPPING_RULE_TRIGGERED = "stopping_rule_triggered"


@dataclass(frozen=True)
class AuditEntry:
    """
    Immutable audit record for a single step in the recovery pipeline.

    Every recovery action produces a sequence of these entries,
    forming a complete, queryable trail.
    """

    payment_id: str
    customer_id: str
    event_type: AuditEventType
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    # Who caused this entry: a user id for human actions, or a component name
    # ("system", "worker", "webhook") for automated ones.
    actor: str = "system"
