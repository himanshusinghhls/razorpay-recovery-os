import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.analyst.service import RecoveryAnalystAgent
from agents.analyst.schemas import AIRecoveryDiagnosis, AIActionProposal
from domain.decision.models import RecoveryDecision

@pytest.fixture
def mock_gemini_response():
    mock_parsed = AIRecoveryDiagnosis(
        recovery_probability=0.85,
        expected_recovery=50000.0,
        diagnosis="Insufficient funds, likely temporary.",
        confidence=0.90,
        action=AIActionProposal(
            action_type="retry_payment",
            reason="Standard automated retry for temporary failure."
        )
    )
    
    mock_response = MagicMock()
    mock_response.parsed = mock_parsed
    return mock_response

@pytest.mark.asyncio
@patch("agents.analyst.service.settings")
@patch("agents.analyst.service.genai.Client")
async def test_analyst_agent_returns_valid_decision(mock_genai_client, mock_settings, mock_gemini_response):
    mock_settings.gemini_api_key = "dummy-key"
    
    # Wire the mocked Gemini client to return our fake parsed response
    mock_client_instance = MagicMock()
    mock_client_instance.aio.models.generate_content = AsyncMock(return_value=mock_gemini_response)
    mock_genai_client.return_value = mock_client_instance

    agent = RecoveryAnalystAgent()
    
    decision = await agent.analyze(
        payment_id="pay_fail_123",
        customer_id="cust_456",
        amount=50000,
        failure_reason="insufficient_funds"
    )
    
    assert isinstance(decision, RecoveryDecision)
    assert decision.payment_id == "pay_fail_123"
    assert decision.action is not None
    assert decision.action.amount == 50000
    assert decision.recovery_probability == 0.85
    
    mock_client_instance.aio.models.generate_content.assert_called_once()
