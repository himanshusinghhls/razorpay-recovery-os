import pytest

from application.execution.authorization import ExecutionAuthorization
from application.execution.razorpay import RazorpayRecoveryExecutor
from domain.recovery.actions import (
    RecoveryAction,
    RecoveryActionType,
)


class FakeRazorpayGateway:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.received_amount = None
        self.received_currency = None
        self.received_receipt = None
        self.received_notes = None

    async def create_retry_order(
        self,
        *,
        amount: int,
        currency: str,
        receipt: str,
        notes=None,
    ):
        self.received_amount = amount
        self.received_currency = currency
        self.received_receipt = receipt
        self.received_notes = notes

        if self.error is not None:
            raise self.error

        return self.response


def make_authorization(
    payment_id="pay_test_123",
    amount=4999,
):
    action = RecoveryAction(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        payment_id=payment_id,
        customer_id="cust_test_123",
        amount=amount,
        reason="Temporary payment failure",
    )

    return ExecutionAuthorization(
        action=action,
        authorization_reason=(
            "Action satisfies recovery policy"
        ),
    )


@pytest.mark.asyncio
async def test_razorpay_executor_creates_retry_order():
    gateway = FakeRazorpayGateway(
        response={
            "id": "order_retry_123",
            "status": "created",
        }
    )

    executor = RazorpayRecoveryExecutor(
        gateway=gateway,
    )

    result = await executor.execute(
        make_authorization()
    )

    assert result.success is True
    assert result.external_reference == "order_retry_123"

    assert gateway.received_amount == 4999
    assert gateway.received_currency == "INR"


@pytest.mark.asyncio
async def test_razorpay_executor_generates_recovery_receipt():
    gateway = FakeRazorpayGateway(
        response={
            "id": "order_retry_456",
            "status": "created",
        }
    )

    executor = RazorpayRecoveryExecutor(
        gateway=gateway,
    )

    await executor.execute(
        make_authorization()
    )

    assert (
        gateway.received_receipt
        == "recovery_pay_test_123"
    )


@pytest.mark.asyncio
async def test_razorpay_executor_attaches_recovery_metadata():
    gateway = FakeRazorpayGateway(
        response={
            "id": "order_retry_789",
            "status": "created",
        }
    )

    executor = RazorpayRecoveryExecutor(
        gateway=gateway,
    )

    await executor.execute(
        make_authorization()
    )

    assert (
        gateway.received_notes["recovery_payment_id"]
        == "pay_test_123"
    )

    assert (
        gateway.received_notes["customer_id"]
        == "cust_test_123"
    )


@pytest.mark.asyncio
async def test_razorpay_executor_maps_provider_failure():
    gateway = FakeRazorpayGateway(
        error=RuntimeError("provider unavailable")
    )

    executor = RazorpayRecoveryExecutor(
        gateway=gateway,
    )

    result = await executor.execute(
        make_authorization()
    )

    assert result.success is False
    assert "provider unavailable" in result.message
    assert result.external_reference is None


@pytest.mark.asyncio
async def test_razorpay_executor_rejects_missing_payment_id():
    gateway = FakeRazorpayGateway()

    executor = RazorpayRecoveryExecutor(
        gateway=gateway,
    )

    result = await executor.execute(
        make_authorization(payment_id=None)
    )

    assert result.success is False
    assert "payment ID" in result.message


@pytest.mark.asyncio
async def test_razorpay_executor_rejects_missing_amount():
    gateway = FakeRazorpayGateway()

    executor = RazorpayRecoveryExecutor(
        gateway=gateway,
    )

    result = await executor.execute(
        make_authorization(amount=None)
    )

    assert result.success is False
    assert "amount" in result.message


def test_razorpay_executor_accepts_gateway_abstraction():
    gateway = FakeRazorpayGateway()

    executor = RazorpayRecoveryExecutor(
        gateway=gateway,
    )

    assert executor.gateway is gateway
