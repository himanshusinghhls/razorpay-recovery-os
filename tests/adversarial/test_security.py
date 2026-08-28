import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.config import settings

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(client):
    res = client.post("/api/v1/auth/token", json={"api_key": settings.api_key})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_missing_auth_header_blocks_mutable_endpoint(client):
    response = client.post("/api/v1/recoveries/execute", json={
        "payment_id": "pay_test",
        "customer_id": "cust_test",
        "amount": 1000,
        "failure_reason": "insufficient_funds"
    })
    assert response.status_code == 401
    assert "Authorization header" in response.json()["detail"]

def test_valid_jwt_allows_access(client, auth_headers):
    response = client.post("/api/v1/recoveries/execute", headers=auth_headers, json={
        "payment_id": "pay_test",
        "customer_id": "cust_test",
        "amount": 1000,
        "failure_reason": "insufficient_funds"
    })
    assert response.status_code != 401

def test_rate_limiting(client, auth_headers):
    responses = [
        client.post("/api/v1/recoveries/execute", headers=auth_headers, json={
            "payment_id": f"pay_test_{i}",
            "customer_id": "cust_test",
            "amount": 1000,
            "failure_reason": "insufficient_funds"
        })
        for i in range(105)
    ]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes
