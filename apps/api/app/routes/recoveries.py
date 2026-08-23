import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.recovery import RecoveryRequest, RecoveryResponse
from ..db.session import get_db_session

from agents.analyst.service import RecoveryAnalystAgent
from domain.policy.engine import RecoveryPolicyEngine
from application.recovery.service import RecoveryApplicationService
from application.execution.orchestrator import RecoveryExecutionOrchestrator
from application.execution.razorpay import RazorpayRecoveryExecutor
from application.execution.postgres_repository import PostgresExecutionRepository
from integrations.razorpay.gateway import RazorpayGateway
from domain.execution.models import RecoveryExecution, ExecutionStatus

router = APIRouter(
    prefix="/recoveries",
    tags=["Recoveries"],
)

@router.post("/execute", response_model=RecoveryResponse)
async def execute_recovery(
    payload: RecoveryRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    execution_id = f"exec_{uuid.uuid4().hex[:16]}"
    
    razorpay_client = request.app.state.razorpay
    gateway = RazorpayGateway(client=razorpay_client)
    executor = RazorpayRecoveryExecutor(gateway=gateway)
    
    policy_engine = RecoveryPolicyEngine()
    app_service = RecoveryApplicationService(policy_engine=policy_engine)
    orchestrator = RecoveryExecutionOrchestrator(executor=executor)
    
    repo = PostgresExecutionRepository(session=session)
    agent = RecoveryAnalystAgent()

    try:
        decision = await agent.analyze(
            payment_id=payload.payment_id,
            customer_id=payload.customer_id,
            amount=payload.amount,
            failure_reason=payload.failure_reason,
        )

        authorization = app_service.authorize(
            decision=decision,
            retry_count=0,
            suspicious=False,
        )

        if not authorization.executable:
            record = RecoveryExecution(
                execution_id=execution_id,
                payment_id=payload.payment_id,
                action_type=decision.action.action_type.value if decision.action else "unknown",
                status=ExecutionStatus.FAILED,
                external_reference=None,
                message=f"Policy Blocked: {authorization.policy_decision.reason}",
            )
            await repo.create(record)
            return RecoveryResponse(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED.value,
                action_type=record.action_type,
                provider_reference=None,
                message=record.message
            )

        execution_result = await orchestrator.execute(authorization)
        
        final_status = ExecutionStatus.STARTED if execution_result.success else ExecutionStatus.FAILED
        record = RecoveryExecution(
            execution_id=execution_id,
            payment_id=payload.payment_id,
            action_type=execution_result.action_type,
            status=final_status,
            external_reference=execution_result.external_reference,
            message=execution_result.message,
        )
        await repo.create(record)

        return RecoveryResponse(
            execution_id=execution_id,
            status=final_status.value,
            action_type=execution_result.action_type,
            provider_reference=execution_result.external_reference,
            message=execution_result.message
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    repo = PostgresExecutionRepository(session=session)
    execution = await repo.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {
        "execution_id": execution.execution_id,
        "payment_id": execution.payment_id,
        "action_type": execution.action_type,
        "status": execution.status.value,
        "external_reference": execution.external_reference,
        "message": execution.message
    }
