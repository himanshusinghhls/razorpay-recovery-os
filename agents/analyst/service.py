import logging
import re
import ssl
from pathlib import Path

import yaml
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from apps.api.app.config import PROJECT_ROOT, settings
from agents.analyst.schemas import AIRecoveryDiagnosis
from agents.analyst.prompts import RECOVERY_ANALYST_PROMPT_V1
from domain.decision.models import RecoveryDecision
from domain.recovery.actions import RecoveryAction, RecoveryActionType

logger = logging.getLogger("recoveryos.agent")


def _build_ssl_context() -> ssl.SSLContext:
    """Prefer the OS trust store; fall back to certifi if truststore is absent."""
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        import httpx

        return httpx.create_ssl_context()

TAXONOMY_PATH = PROJECT_ROOT / "domain" / "policy" / "taxonomy.yaml"


def _sanitize_reason(raw: str) -> str:
    """Strip newlines, control chars, and known injection words to prevent prompt injection."""
    cleaned = re.sub(r"[\n\r\x00-\x1f]", " ", raw)
    
    injection_tokens = ["ignore", "instructions", "system", "prompt", "bypass", "override"]
    for token in injection_tokens:
        if re.search(rf"(?i)\b{token}\b", cleaned):
            return "PROMPT_INJECTION_DETECTED"
        
    return cleaned[:128]


def _taxonomy_fallback(
    payment_id: str,
    customer_id: str,
    amount: int,
    failure_reason: str,
) -> RecoveryDecision:
    """Deterministic fallback using taxonomy.yaml when Gemini is unavailable."""
    with open(TAXONOMY_PATH) as f:
        taxonomy = yaml.safe_load(f)

    classes = taxonomy.get("classes", {})
    cfg = classes.get(failure_reason, {})

    prob = cfg.get("ai_recovery_probability", 0.0)
    default_action = cfg.get("default_action", "stop_recovery")

    try:
        action_type = RecoveryActionType(default_action)
    except ValueError:
        action_type = RecoveryActionType.STOP_RECOVERY

    action = RecoveryAction(
        action_type=action_type,
        payment_id=payment_id,
        customer_id=customer_id,
        amount=amount,
        reason=f"Taxonomy fallback: {failure_reason}",
    )

    return RecoveryDecision(
        payment_id=payment_id,
        customer_id=customer_id,
        amount=amount,
        recovery_probability=prob,
        expected_recovery=min(amount * prob, amount),
        diagnosis=f"Deterministic fallback for {failure_reason}",
        confidence=prob,
        action=action,
    )


class RecoveryAnalystAgent:
    """
    AI Agent responsible for diagnosing failed payments and
    recommending bounded recovery actions using Gemini.

    Falls back to taxonomy.yaml probabilities if Gemini is unavailable.
    """

    def __init__(self) -> None:
        api_key = settings.gemini_api_key

        if not api_key or api_key == "REPLACE_ME":
            raise ValueError("GEMINI_API_KEY is not configured in the environment.")

        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                async_client_args={"verify": _build_ssl_context()},
                client_args={"verify": _build_ssl_context()},
            ),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _call_gemini(self, prompt: str) -> AIRecoveryDiagnosis:
        response = await self.client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIRecoveryDiagnosis,
                temperature=settings.gemini_temperature,
            ),
        )
        return response.parsed

    async def analyze(
        self,
        payment_id: str,
        customer_id: str,
        amount: int,
        failure_reason: str,
        customer_history: str = "No prior history",
    ) -> RecoveryDecision:
        safe_reason = _sanitize_reason(failure_reason)

        prompt = RECOVERY_ANALYST_PROMPT_V1.format(
            payment_id=payment_id,
            customer_id=customer_id,
            amount=amount,
            failure_reason=safe_reason,
            customer_history=customer_history,
        )

        try:
            ai_result = await self._call_gemini(prompt)

            action_enum = RecoveryActionType(ai_result.action.action_type)
            action = RecoveryAction(
                action_type=action_enum,
                payment_id=payment_id,
                customer_id=customer_id,
                amount=amount,
                reason=ai_result.action.reason,
            )

            expected = min(ai_result.expected_recovery, float(amount))

            return RecoveryDecision(
                payment_id=payment_id,
                customer_id=customer_id,
                amount=amount,
                recovery_probability=ai_result.recovery_probability,
                expected_recovery=expected,
                diagnosis=ai_result.diagnosis,
                confidence=ai_result.confidence,
                action=action,
                raw_prompt=prompt,
            )

        except Exception:
            logger.warning(
                "Gemini call failed for %s after retries — using taxonomy fallback", payment_id, exc_info=True
            )
            return _taxonomy_fallback(payment_id, customer_id, amount, safe_reason)
