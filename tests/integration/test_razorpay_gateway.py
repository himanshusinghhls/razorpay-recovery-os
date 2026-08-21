import pytest

from integrations.razorpay.gateway import RazorpayGateway


class FakeClient:
    def __init__(self):
        self.received = None

    async def create_order(
        self,
        *,
        amount,
        currency,
        receipt,
        notes=None,
    ):
        self.received = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes,
        }

        return {
            "id": "order_test_123",
            "status": "created",
        }


@pytest.mark.asyncio
async def test_razorpay_gateway_delegates_order_creation():
    client = FakeClient()

    gateway = RazorpayGateway(
        client=client,
    )

    result = await gateway.create_retry_order(
        amount=4999,
        currency="INR",
        receipt="recovery_pay_test_123",
        notes={
            "customer_id": "cust_test_123",
        },
    )

    assert result["id"] == "order_test_123"

    assert client.received["amount"] == 4999
    assert client.received["currency"] == "INR"
    assert (
        client.received["receipt"]
        == "recovery_pay_test_123"
    )
