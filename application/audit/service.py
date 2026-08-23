from typing import Any

from application.audit.repository import AuditRepository
from domain.audit.models import AuditEntry, AuditEventType


class AuditService:
    """
    Records every step of the recovery pipeline into the audit trail.

    Each method corresponds to a specific pipeline stage.
    The service never makes decisions — it only records facts.
    """

    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    async def log_failure_detected(
        self,
        payment_id: str,
        customer_id: str,
        amount: int,
        failure_reason: str,
    ) -> None:
        entry = AuditEntry(
            payment_id=payment_id,
            customer_id=customer_id,
            event_type=AuditEventType.FAILURE_DETECTED,
            data={
                "amount": amount,
                "failure_reason": failure_reason,
            },
        )
        await self.repository.save(entry)

    async def log_ai_diagnosis(
        self,
        payment_id: str,
        customer_id: str,
        diagnosis: str,
        confidence: float,
        recovery_probability: float,
        recommended_action: str,
        expected_recovery: float,
    ) -> None:
        entry = AuditEntry(
            payment_id=payment_id,
            customer_id=customer_id,
            event_type=AuditEventType.AI_DIAGNOSIS,
            data={
                "diagnosis": diagnosis,
                "confidence": confidence,
                "recovery_probability": recovery_probability,
                "recommended_action": recommended_action,
                "expected_recovery": expected_recovery,
            },
        )
        await self.repository.save(entry)

    async def log_policy_decision(
        self,
        payment_id: str,
        customer_id: str,
        allowed: bool,
        reason: str,
        requires_human_approval: bool,
        retry_count: int,
    ) -> None:
        entry = AuditEntry(
            payment_id=payment_id,
            customer_id=customer_id,
            event_type=AuditEventType.POLICY_DECISION,
            data={
                "allowed": allowed,
                "reason": reason,
                "requires_human_approval": requires_human_approval,
                "retry_count": retry_count,
            },
        )
        await self.repository.save(entry)

    async def log_execution_result(
        self,
        payment_id: str,
        customer_id: str,
        execution_id: str,
        success: bool,
        action_type: str,
        message: str,
        external_reference: str | None = None,
    ) -> None:
        event_type = (
            AuditEventType.EXECUTION_SUCCEEDED
            if success
            else AuditEventType.EXECUTION_FAILED
        )
        entry = AuditEntry(
            payment_id=payment_id,
            customer_id=customer_id,
            event_type=event_type,
            data={
                "execution_id": execution_id,
                "action_type": action_type,
                "message": message,
                "external_reference": external_reference,
            },
        )
        await self.repository.save(entry)

    async def log_escalation(
        self,
        payment_id: str,
        customer_id: str,
        review_id: str,
        reason: str,
    ) -> None:
        entry = AuditEntry(
            payment_id=payment_id,
            customer_id=customer_id,
            event_type=AuditEventType.ESCALATED_TO_REVIEW,
            data={
                "review_id": review_id,
                "reason": reason,
            },
        )
        await self.repository.save(entry)

    async def log_review_decision(
        self,
        payment_id: str,
        customer_id: str,
        review_id: str,
        approved: bool,
        resolved_by: str = "system",
    ) -> None:
        event_type = (
            AuditEventType.REVIEW_APPROVED
            if approved
            else AuditEventType.REVIEW_REJECTED
        )
        entry = AuditEntry(
            payment_id=payment_id,
            customer_id=customer_id,
            event_type=event_type,
            data={
                "review_id": review_id,
                "resolved_by": resolved_by,
            },
        )
        await self.repository.save(entry)

    async def log_stopping_rule(
        self,
        payment_id: str,
        customer_id: str,
        rule_name: str,
        reason: str,
    ) -> None:
        entry = AuditEntry(
            payment_id=payment_id,
            customer_id=customer_id,
            event_type=AuditEventType.STOPPING_RULE_TRIGGERED,
            data={
                "rule_name": rule_name,
                "reason": reason,
            },
        )
        await self.repository.save(entry)
