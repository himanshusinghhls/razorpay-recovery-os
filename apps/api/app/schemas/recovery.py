from pydantic import BaseModel, Field
from typing import Optional

class RecoveryRequest(BaseModel):
    payment_id: str = Field(..., description="The ID of the failed payment")
    customer_id: str = Field(..., description="The ID of the customer")
    amount: int = Field(..., gt=0, description="Amount in paise")
    failure_reason: str = Field(..., description="Reason for the payment failure")

class RecoveryResponse(BaseModel):
    execution_id: str
    status: str
    action_type: str
    provider_reference: Optional[str]
    message: str
