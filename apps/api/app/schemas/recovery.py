from pydantic import BaseModel, Field
from typing import Optional

class RecoveryRequest(BaseModel):
    payment_id: str = Field(..., min_length=1, max_length=64, description="The ID of the failed payment")
    customer_id: str = Field(..., min_length=1, max_length=64, description="The ID of the customer")
    amount: int = Field(..., gt=0, le=100_000_000, description="Amount in paise (max ₹10,00,000)")
    failure_reason: str = Field(..., min_length=1, max_length=128, description="Reason for the payment failure")

class RecoveryResponse(BaseModel):
    execution_id: str
    status: str
    action_type: str
    provider_reference: Optional[str]
    message: str
    pipeline_latency_ms: Optional[float] = None
