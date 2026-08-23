import uuid
from datetime import datetime, timezone
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
    
    # 1. Initialize Dependencies
    razorpay_client = request.app.state.razorpay
    gateway = RazorpayGateway(client=razorpay_client)
    executor = RazorpayRecoveryExecutor(gateway=gateway)
    
    policy_engine = RecoveryPolicyEngine()
    app_service = RecoveryApplicationService(policy_engine=policy_engine)
    orchestrator = RecoveryExecutionOrchestrator(executor=executor)
    
    repo = PostgresExecutionRepository(session=session)
    agent = RecoveryAnalystAgent()

    try:
        # 2. AI Analysis
        decision = await agent.analyze(
            payment_id=payload.payment_id,
            customer_id=payload.customer_id,
            amount=payload.amount,
            failure_reason=payload.failure_reason,
        )

        # 3. Policy Authorization
        authorization = app_service.authorize(
            decision=decision,
            retry_count=0,
            suspicious=False,
        )

        if not authorization.executable:
            # Policy blocked the action
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

        # 4. Execution
        execution_result = await orchestrator.execute(authorization)
        
        # 5. Persistence
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

        # 6. Response
        return RecoveryResponse(
            execution_id=execution_id,
            status=final_status.value,
            action_type=execution_result.action_type,
            provider_reference=execution_result.external_reference,
            message=execution_result.message
        )

    except Exception as e:
        # Failsafe for unhandled errors
        raise HTTPException(status_code=500, detail=str(e))
