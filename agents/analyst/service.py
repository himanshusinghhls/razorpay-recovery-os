from google import genai
from google.genai import types

from apps.api.app.config import settings
from agents.analyst.schemas import AIRecoveryDiagnosis
from domain.decision.models import RecoveryDecision
from domain.recovery.actions import RecoveryAction, RecoveryActionType

class RecoveryAnalystAgent:
    """
    AI Agent responsible for diagnosing failed payments and
    recommending bounded recovery actions using Gemini.
    """
    def __init__(self) -> None:
        api_key = settings.gemini_api_key
        
        if not api_key or api_key == "REPLACE_ME":
            raise ValueError("GEMINI_API_KEY is not configured in the environment.")
            
        self.client = genai.Client(api_key=api_key)

    async def analyze(
        self, 
        payment_id: str, 
        customer_id: str, 
        amount: int, 
        failure_reason: str,
        customer_history: str = "No prior history"
    ) -> RecoveryDecision:
        
        prompt = f"""
        You are a senior revenue recovery analyst AI for Razorpay. You maximize expected recovery value while minimizing friction.
        
        Analyze the following payment failure and recommend a recovery action.
        Payment ID: {payment_id}
        Customer ID: {customer_id}
        Amount (in paise): {amount}
        Failure Reason: {failure_reason}
        Customer History: {customer_history}
        
        Determine the root cause, calculate the expected recovery probability, 
        and select the optimal bounded action.
        """

        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIRecoveryDiagnosis,
                temperature=0.2,
            ),
        )
        
        ai_result = response.parsed

        action_enum = RecoveryActionType(ai_result.action.action_type)
        action = RecoveryAction(
            action_type=action_enum,
            payment_id=payment_id,
            customer_id=customer_id,
            amount=amount,
            reason=ai_result.action.reason
        )

        return RecoveryDecision(
            payment_id=payment_id,
            customer_id=customer_id,
            amount=amount,
            recovery_probability=ai_result.recovery_probability,
            expected_recovery=ai_result.expected_recovery,
            diagnosis=ai_result.diagnosis,
            confidence=ai_result.confidence,
            action=action
        )
