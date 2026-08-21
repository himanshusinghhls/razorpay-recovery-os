import hashlib
import hmac

from integrations.razorpay.verification import (
    RazorpaySignatureVerifier,
)


def test_payment_signature_is_valid():
    secret = "test_secret"

    verifier = RazorpaySignatureVerifier(secret)

    order_id = "order_test"
    payment_id = "pay_test"

    message = f"{order_id}|{payment_id}"

    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    assert verifier.verify_payment_signature(
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
    )


def test_payment_signature_rejects_tampering():
    verifier = RazorpaySignatureVerifier(
        "test_secret",
    )

    assert not verifier.verify_payment_signature(
        order_id="order_test",
        payment_id="pay_test",
        signature="invalid",
    )


def test_webhook_signature_is_valid():
    secret = "webhook_secret"

    verifier = RazorpaySignatureVerifier(secret)

    body = b'{"event":"payment.captured"}'

    signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    assert verifier.verify_webhook_signature(
        raw_body=body,
        signature=signature,
    )


def test_webhook_signature_rejects_modified_body():
    secret = "webhook_secret"

    verifier = RazorpaySignatureVerifier(secret)

    body = b'{"event":"payment.captured"}'

    signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    modified_body = b'{"event":"payment.failed"}'

    assert not verifier.verify_webhook_signature(
        raw_body=modified_body,
        signature=signature,
    )
