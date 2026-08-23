import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.analyst.service import RecoveryAnalystAgent
from agents.analyst.schemas import AIRecoveryDiagnosis, AIActionProposal
from domain.decision.models import RecoveryDecision

@pytest.fixture
def mock_openai_response():
    # Construct the exact Pydantic object the OpenAI SDK would return
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
    
    # Build the deeply nested mock structure matching the OpenAI SDK response
    mock_message = MagicMock()
    mock_message.parsed = mock_parsed
    
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    return mock_response

@pytest.mark.asyncio
@patch("agents.analyst.service.settings")
@patch("agents.analyst.service.AsyncOpenAI")
async def test_analyst_agent_returns_valid_decision(mock_async_openai, mock_settings, mock_openai_response):
    # 1. Setup mock environment
    mock_settings.openai_api_key = "sk-test-key"
    
    # 2. Wire the mocked OpenAI client to return our fake parsed response
    mock_client_instance = MagicMock()
    mock_client_instance.beta.chat.completions.parse = AsyncMock(return_value=mock_openai_response)
    mock_async_openai.return_value = mock_client_instance

    # 3. Initialize Agent
    agent = RecoveryAnalystAgent()
    
    # 4. Execute
    decision = await agent.analyze(
        payment_id="pay_fail_123",
        customer_id="cust_456",
        amount=50000,
        failure_reason="insufficient_funds"
    )
    
    # 5. Assertions
    assert isinstance(decision, RecoveryDecision)
    assert decision.payment_id == "pay_fail_123"
    assert decision.action is not None
    assert decision.action.amount == 50000
    assert decision.recovery_probability == 0.85
    
    # Prove our agent actually called the LLM with the right structure
    mock_client_instance.beta.chat.completions.parse.assert_called_once()
