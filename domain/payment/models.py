from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class PaymentStatus(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"

@dataclass(frozen=True)
class Payment:
    payment_id: str
    customer_id: str
    amount: int
    currency: str
    status: PaymentStatus
    error_code: Optional[str]
    error_description: Optional[str]
    created_at: datetime
