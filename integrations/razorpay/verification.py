import hashlib
import hmac


class RazorpaySignatureVerifier:
    def __init__(self, secret: str) -> None:
        self.secret = secret

    def verify_payment_signature(
        self,
        *,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:

        message = f"{order_id}|{payment_id}"

        expected = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            expected,
            signature,
        )

    def verify_webhook_signature(
        self,
        *,
        raw_body: bytes,
        signature: str,
    ) -> bool:

        expected = hmac.new(
            self.secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            expected,
            signature,
        )
