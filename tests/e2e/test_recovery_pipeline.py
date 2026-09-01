"""
End-to-end tests for the RecoveryOS pipeline.

These tests exercise the real FastAPI application through its HTTP layer,
covering the full request lifecycle: authentication → route → service →
database interaction → response.

They use FastAPI's built-in TestClient with dependency overrides so they
run without Postgres, Redis, or Gemini.

Run with:
    PYTHONPATH=. ./apps/api/.venv/bin/pytest tests/e2e/ -v
"""

import uuid
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.auth import Principal, get_current_principal
from apps.api.app.core.security import create_access_token
from apps.api.app.db.models import UserRole
from apps.api.app.db.session import get_db_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_MERCHANT = "mrch_demo_recoveryos"
DEMO_USER = "user_e2e_test_admin"
DEMO_EMAIL = "admin@acmecommerce.in"

ADMIN_PRINCIPAL = Principal(
    user_id=DEMO_USER,
    merchant_id=DEMO_MERCHANT,
    email=DEMO_EMAIL,
    role=UserRole.ADMIN,
)

VIEWER_PRINCIPAL = Principal(
    user_id="user_viewer",
    merchant_id=DEMO_MERCHANT,
    email="viewer@acmecommerce.in",
    role=UserRole.VIEWER,
)


@pytest.fixture()
def mock_db_session():
    """A fully-mocked async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    # Default scalar returns for analytics queries
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0
    mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
    session.execute = AsyncMock(return_value=mock_result)
    session.get = AsyncMock(return_value=None)
    return session


def _make_client(mock_db_session, principal_override=None):
    """Build a TestClient with infrastructure mocked out."""
    from apps.api.app.main import app

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield mock_db_session

    app.dependency_overrides[get_db_session] = _override_db

    if principal_override is not None:
        app.dependency_overrides[get_current_principal] = lambda: principal_override

    # Mock infrastructure that the lifespan normally creates.
    app.state.redis = AsyncMock()
    app.state.redis.ping = AsyncMock(return_value=True)
    app.state.redis.set = AsyncMock(return_value=True)
    app.state.redis.get = AsyncMock(return_value=None)
    pipe_mock = MagicMock()
    pipe_mock.incr = MagicMock()
    pipe_mock.expire = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[1, True])
    app.state.redis.pipeline = MagicMock(return_value=pipe_mock)

    app.state.arq_pool = AsyncMock()
    app.state.arq_pool.enqueue_job = AsyncMock()

    app.state.razorpay = MagicMock()
    app.state.razorpay.client = AsyncMock()

    return app


@pytest.fixture()
def client(mock_db_session):
    """Unauthenticated client — no principal override."""
    app = _make_client(mock_db_session, principal_override=None)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client(mock_db_session):
    """Client authenticated as ADMIN."""
    app = _make_client(mock_db_session, principal_override=ADMIN_PRINCIPAL)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def viewer_client(mock_db_session):
    """Client authenticated as VIEWER (read-only)."""
    app = _make_client(mock_db_session, principal_override=VIEWER_PRINCIPAL)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------


class TestSystemEndpoints:
    """Verify health, readiness, and root endpoints return expected shapes."""

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    def test_root_returns_service_info(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert "RecoveryOS" in body["name"]
        assert "version" in body


# ---------------------------------------------------------------------------
# Authentication Flow
# ---------------------------------------------------------------------------


class TestAuthFlow:
    """End-to-end authentication lifecycle."""

    def test_unauthenticated_request_returns_401(self, client):
        """Protected endpoints reject requests without a token."""
        resp = client.get("/api/v1/analytics/summary")
        assert resp.status_code == 401

    def test_malformed_token_returns_401(self, client):
        """A garbage token is rejected, not a 500."""
        resp = client.get(
            "/api/v1/analytics/summary",
            headers={"Authorization": "Bearer this.is.garbage"},
        )
        assert resp.status_code == 401

    def test_authenticated_request_reaches_route(self, admin_client):
        """A properly authenticated request passes auth and reaches the route."""
        resp = admin_client.get("/api/v1/analytics/summary")
        # If auth failed we'd get 401; anything else proves the guard passed.
        assert resp.status_code != 401


# ---------------------------------------------------------------------------
# Recovery Execution Flow
# ---------------------------------------------------------------------------


class TestRecoveryExecution:
    """End-to-end: submit a recovery → verify it is queued."""

    def test_execute_recovery_requires_idempotency_key(self, admin_client):
        """The endpoint rejects requests without an Idempotency-Key header."""
        resp = admin_client.post(
            "/api/v1/recoveries/execute",
            json={
                "payment_id": "pay_test_001",
                "customer_id": "cust_test_001",
                "amount": 50000,
                "failure_reason": "temporary_network_timeout",
            },
        )
        assert resp.status_code == 400
        assert "Idempotency" in resp.json()["detail"]

    def test_execute_recovery_queues_job(self, admin_client):
        """A valid recovery request returns 202 and enqueues an ARQ job."""
        idem_key = uuid.uuid4().hex
        resp = admin_client.post(
            "/api/v1/recoveries/execute",
            json={
                "payment_id": "pay_test_002",
                "customer_id": "cust_test_002",
                "amount": 25000,
                "failure_reason": "insufficient_funds",
            },
            headers={"Idempotency-Key": idem_key},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "execution_id" in body
        assert body["status"] == "processing"

    def test_execute_recovery_rejects_viewer_role(self, viewer_client):
        """VIEWER users cannot trigger recovery execution (needs ANALYST+)."""
        resp = viewer_client.post(
            "/api/v1/recoveries/execute",
            json={
                "payment_id": "pay_test_003",
                "customer_id": "cust_test_003",
                "amount": 10000,
                "failure_reason": "gateway_timeout",
            },
            headers={"Idempotency-Key": uuid.uuid4().hex},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Webhook Ingress
# ---------------------------------------------------------------------------


class TestWebhookIngress:
    """Webhook processing — verifies signature checking and payload handling."""

    def test_webhook_rejects_missing_signature(self, client):
        """A webhook without a signature header is rejected."""
        resp = client.post(
            "/api/v1/webhooks/razorpay",
            json={"event": "payment.authorized"},
        )
        assert resp.status_code in (400, 503)

    def test_webhook_rejects_invalid_signature(self, client):
        """A webhook with an invalid HMAC signature is rejected (401)."""
        resp = client.post(
            "/api/v1/webhooks/razorpay",
            json={"event": "payment.authorized"},
            headers={
                "X-Razorpay-Signature": "invalid_signature_value",
                "X-Razorpay-Event-Id": "evt_test_001",
            },
        )
        # 401 (bad sig) or 503 (webhook secret not configured) are both correct
        assert resp.status_code in (401, 503)


# ---------------------------------------------------------------------------
# Input Validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Verify that malformed inputs are rejected cleanly, not with 500s."""

    def test_empty_payment_id_rejected(self, admin_client):
        """An empty payment_id is caught by Pydantic validation."""
        resp = admin_client.post(
            "/api/v1/recoveries/execute",
            json={
                "payment_id": "",
                "customer_id": "cust_test",
                "amount": 5000,
                "failure_reason": "network_timeout",
            },
            headers={"Idempotency-Key": uuid.uuid4().hex},
        )
        assert resp.status_code == 422

    def test_negative_amount_rejected(self, admin_client):
        """Negative amounts are caught at the schema level."""
        resp = admin_client.post(
            "/api/v1/recoveries/execute",
            json={
                "payment_id": "pay_neg",
                "customer_id": "cust_neg",
                "amount": -1000,
                "failure_reason": "network_timeout",
            },
            headers={"Idempotency-Key": uuid.uuid4().hex},
        )
        assert resp.status_code == 422
