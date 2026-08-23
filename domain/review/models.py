from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class PendingReview:
    """
    Immutable record of a recovery action that requires human approval.

    Created when the policy engine blocks an action with
    requires_human_approval=True.
    """

    review_id: str
    payment_id: str
    customer_id: str
    amount: int
    action_type: str
    policy_reason: str
    ai_diagnosis: str
    ai_confidence: float
    status: ReviewStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
