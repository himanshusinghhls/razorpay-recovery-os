import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.db.models import ReviewRecord
from domain.review.models import PendingReview, ReviewStatus


class ReviewService:
    """
    Manages the human-review escalation queue.

    When the policy engine blocks an action with requires_human_approval,
    a PendingReview is created. Merchants can approve or reject.

    The service is bound to one merchant at construction, so every query it
    issues is tenant-scoped by construction rather than by remembering to add a
    filter at each call site.
    """

    def __init__(self, session: AsyncSession, merchant_id: str) -> None:
        self.session = session
        self.merchant_id = merchant_id

    async def create_review(
        self,
        payment_id: str,
        customer_id: str,
        amount: int,
        action_type: str,
        policy_reason: str,
        ai_diagnosis: str = "",
        ai_confidence: float = 0.0,
    ) -> PendingReview:
        review_id = f"review_{uuid.uuid4().hex[:16]}"

        record = ReviewRecord(
            review_id=review_id,
            merchant_id=self.merchant_id,
            payment_id=payment_id,
            customer_id=customer_id,
            amount=amount,
            action_type=action_type,
            policy_reason=policy_reason,
            ai_diagnosis=ai_diagnosis,
            ai_confidence=ai_confidence,
            status=ReviewStatus.PENDING,
        )
        self.session.add(record)
        await self.session.commit()

        return self._to_domain(record)

    async def list_pending(self) -> list[PendingReview]:
        stmt = (
            select(ReviewRecord)
            .where(
                ReviewRecord.merchant_id == self.merchant_id,
                ReviewRecord.status == ReviewStatus.PENDING,
            )
            .order_by(ReviewRecord.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def list_all(self, limit: int = 100) -> list[PendingReview]:
        stmt = (
            select(ReviewRecord)
            .where(ReviewRecord.merchant_id == self.merchant_id)
            .order_by(ReviewRecord.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get(self, review_id: str) -> PendingReview | None:
        stmt = select(ReviewRecord).where(
            ReviewRecord.review_id == review_id,
            ReviewRecord.merchant_id == self.merchant_id,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        return self._to_domain(record) if record else None

    async def _resolve(
        self, review_id: str, new_status: ReviewStatus, resolved_by: str
    ) -> PendingReview | None:
        """
        Claim a pending review and move it to a terminal state.

        SELECT ... FOR UPDATE holds a row lock for the rest of the transaction.
        Without it, two concurrent approvals could both read status=PENDING and
        both go on to execute the recovery — a double charge against a real
        payment method.
        """
        stmt = (
            select(ReviewRecord)
            .where(
                ReviewRecord.review_id == review_id,
                ReviewRecord.merchant_id == self.merchant_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record or record.status != ReviewStatus.PENDING:
            await self.session.rollback()
            return None

        record.status = new_status
        record.resolved_at = datetime.now(timezone.utc)
        record.resolved_by = resolved_by
        await self.session.commit()

        return self._to_domain(record)

    async def approve(self, review_id: str, resolved_by: str) -> PendingReview | None:
        return await self._resolve(review_id, ReviewStatus.APPROVED, resolved_by)

    async def reject(self, review_id: str, resolved_by: str) -> PendingReview | None:
        return await self._resolve(review_id, ReviewStatus.REJECTED, resolved_by)

    @staticmethod
    def _to_domain(record: ReviewRecord) -> PendingReview:
        return PendingReview(
            review_id=record.review_id,
            payment_id=record.payment_id,
            customer_id=record.customer_id,
            amount=record.amount,
            action_type=record.action_type,
            policy_reason=record.policy_reason,
            ai_diagnosis=record.ai_diagnosis,
            ai_confidence=record.ai_confidence,
            status=record.status,
            created_at=record.created_at,
            resolved_at=record.resolved_at,
            resolved_by=record.resolved_by,
        )
