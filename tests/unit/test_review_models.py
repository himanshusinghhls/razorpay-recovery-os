import pytest

from domain.review.models import PendingReview, ReviewStatus
from datetime import datetime, timezone


def test_pending_review_can_be_created():
    review = PendingReview(
        review_id="review_001",
        payment_id="pay_123",
        customer_id="cust_456",
        amount=2500000,
        action_type="retry_payment",
        policy_reason="High-value transaction requires merchant approval",
        ai_diagnosis="Temporary insufficient funds",
        ai_confidence=0.92,
        status=ReviewStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    assert review.review_id == "review_001"
    assert review.status == ReviewStatus.PENDING
    assert review.resolved_at is None


def test_pending_review_is_immutable():
    review = PendingReview(
        review_id="review_001",
        payment_id="pay_123",
        customer_id="cust_456",
        amount=2500000,
        action_type="retry_payment",
        policy_reason="High-value transaction",
        ai_diagnosis="Test",
        ai_confidence=0.9,
        status=ReviewStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(AttributeError):
        review.status = ReviewStatus.APPROVED


def test_review_status_values():
    assert ReviewStatus.PENDING.value == "pending"
    assert ReviewStatus.APPROVED.value == "approved"
    assert ReviewStatus.REJECTED.value == "rejected"
