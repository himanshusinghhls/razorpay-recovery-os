from pydantic import BaseModel, Field

class AIActionProposal(BaseModel):
    action_type: str = Field(
        description="Must be one of: retry_payment, send_payment_link, send_reminder, escalate_to_merchant, stop_recovery"
    )
    reason: str = Field(description="Explanation of why this action was chosen")

class AIRecoveryDiagnosis(BaseModel):
    recovery_probability: float = Field(ge=0.0, le=1.0, description="Probability of successful recovery (0.0 to 1.0)")
    expected_recovery: float = Field(ge=0.0, description="Expected monetary value of recovery")
    diagnosis: str = Field(description="Detailed diagnosis of why the payment failed based on the context")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this diagnosis (0.0 to 1.0)")
    action: AIActionProposal
