import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_missing_api_key_blocks_mutable_endpoint(client):
    response = client.post("/api/v1/recoveries/execute", json={
        "payment_id": "pay_test",
        "customer_id": "cust_test",
        "amount": 1000,
        "failure_reason": "insufficient_funds"
    })
    assert response.status_code == 401
    assert "API key" in response.json()["detail"]

def test_valid_api_key_allows_access(client):
    headers = {"X-API-Key": "ros_demo_key_2026"}
    response = client.post("/api/v1/recoveries/execute", headers=headers, json={
        "payment_id": "pay_test",
        "customer_id": "cust_test",
        "amount": 1000,
        "failure_reason": "insufficient_funds"
    })
    assert response.status_code != 401

def test_rate_limiting(client):
    headers = {"X-API-Key": "ros_demo_key_2026"}
    responses = [
        client.post("/api/v1/recoveries/execute", headers=headers, json={
            "payment_id": f"pay_test_{i}",
            "customer_id": "cust_test",
            "amount": 1000,
            "failure_reason": "insufficient_funds"
        })
        for i in range(15)
    ]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes
