"""
Security boundary tests.

These exercise the auth layer against the real app object. They assert the
properties that matter rather than exact copy, so wording changes don't create
false failures.
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from apps.api.app.config import settings
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _token_with(**overrides) -> str:
    """Mint a token with arbitrary claims, for negative cases."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "user_nonexistent",
        "mid": "mrch_nonexistent",
        "role": "admin",
        "email": "attacker@example.com",
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=15),
        "jti": uuid.uuid4().hex,
    }
    claims.update(overrides)
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


RECOVERY_PAYLOAD = {
    "payment_id": "pay_test",
    "customer_id": "cust_test",
    "amount": 1000,
    "failure_reason": "insufficient_funds",
}


def test_missing_auth_header_blocks_write(client):
    response = client.post("/api/v1/recoveries/execute", json=RECOVERY_PAYLOAD)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/analytics/summary",
        "/api/v1/audit/",
        "/api/v1/reviews/",
        "/api/v1/safety/adversarial",
        "/api/v1/analytics/taxonomy",
    ],
)
def test_reads_require_authentication(client, path):
    """
    Regression: auth used to be middleware that returned early for every GET,
    leaving analytics, audit trails and the review queue world-readable.
    """
    assert client.get(path).status_code == 401


def test_create_order_requires_authentication(client):
    """Regression: this route was on an open-prefix allowlist."""
    response = client.post("/api/v1/recoveries/create-order?amount=100000")
    assert response.status_code == 401


def test_garbage_token_rejected(client):
    response = client.get(
        "/api/v1/analytics/summary",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


def test_token_signed_with_wrong_key_rejected(client):
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {
            "sub": "user_x",
            "mid": "mrch_x",
            "role": "admin",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        "an-attacker-chosen-secret-that-is-long-enough",
        algorithm="HS256",
    )
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {forged}"}
    )
    assert response.status_code == 401


def test_expired_token_rejected(client):
    now = datetime.now(timezone.utc)
    expired = _token_with(iat=now - timedelta(hours=2), exp=now - timedelta(hours=1))
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401


def test_valid_signature_for_unknown_user_rejected(client):
    """
    A correctly signed token is not enough — the account must still exist and
    be active, so revocation takes effect without waiting for expiry.
    """
    response = client.get(
        "/api/v1/analytics/summary",
        headers={"Authorization": f"Bearer {_token_with()}"},
    )
    assert response.status_code == 401


def test_refresh_token_rejected_as_access_token(client):
    """Token types are not interchangeable."""
    now = datetime.now(timezone.utc)
    refresh = jwt.encode(
        {
            "sub": "user_x",
            "fam": "fam_x",
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=1),
            "jti": uuid.uuid4().hex,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert response.status_code == 401


def test_alg_none_token_rejected(client):
    """Classic JWT downgrade: an unsigned token must never be accepted."""
    now = datetime.now(timezone.utc)
    unsigned = jwt.encode(
        {
            "sub": "user_x",
            "mid": "mrch_x",
            "role": "admin",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        key="",
        algorithm="none",
    )
    response = client.get(
        "/api/v1/analytics/summary", headers={"Authorization": f"Bearer {unsigned}"}
    )
    assert response.status_code == 401


def test_login_rejects_bad_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_response_does_not_reveal_whether_account_exists(client):
    """Unknown user and wrong password must be indistinguishable."""
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "definitely-not-a-user@example.com", "password": "x" * 12},
    )
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == "Incorrect email or password"


def test_refresh_without_cookie_rejected(client):
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_security_headers_present(client):
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in headers


def test_request_id_returned(client):
    assert client.get("/health").headers.get("X-Request-ID")


def test_webhook_rejects_bad_signature(client):
    response = client.post(
        "/api/v1/webhooks/razorpay",
        content=b'{"event":"payment.captured"}',
        headers={
            "X-Razorpay-Signature": "definitely-not-valid",
            "X-Razorpay-Event-Id": "evt_test_1",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code in (401, 503)
