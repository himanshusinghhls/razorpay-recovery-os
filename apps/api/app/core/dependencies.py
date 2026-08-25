from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.app.db.session import get_db_session

from agents.analyst.service import RecoveryAnalystAgent
from domain.policy.engine import RecoveryPolicyEngine
from application.recovery.service import RecoveryApplicationService
from application.execution.orchestrator import RecoveryExecutionOrchestrator
from application.execution.razorpay import RazorpayRecoveryExecutor
from application.execution.postgres_repository import PostgresExecutionRepository
from application.audit.service import AuditService
from application.audit.repository import PostgresAuditRepository
from application.review.service import ReviewService
from integrations.razorpay.gateway import RazorpayGateway

def get_razorpay_gateway(request: Request) -> RazorpayGateway:
    return RazorpayGateway(client=request.app.state.razorpay)

_agent = None
def get_recovery_analyst_agent() -> RecoveryAnalystAgent:
    global _agent
    if _agent is None:
        _agent = RecoveryAnalystAgent()
    return _agent

_policy_engine = None
def get_policy_engine() -> RecoveryPolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = RecoveryPolicyEngine()
    return _policy_engine

def get_recovery_app_service(
    policy_engine: RecoveryPolicyEngine = Depends(get_policy_engine),
) -> RecoveryApplicationService:
    return RecoveryApplicationService(policy_engine=policy_engine)

def get_execution_orchestrator(
    gateway: RazorpayGateway = Depends(get_razorpay_gateway),
) -> RecoveryExecutionOrchestrator:
    executor = RazorpayRecoveryExecutor(gateway=gateway)
    return RecoveryExecutionOrchestrator(executor=executor)

def get_audit_service(
    session: AsyncSession = Depends(get_db_session),
) -> AuditService:
    repo = PostgresAuditRepository(session)
    return AuditService(repo)

def get_review_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReviewService:
    return ReviewService(session)

def get_execution_repository(
    session: AsyncSession = Depends(get_db_session),
) -> PostgresExecutionRepository:
    return PostgresExecutionRepository(session)
