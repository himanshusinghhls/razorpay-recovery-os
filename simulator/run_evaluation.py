"""
RecoveryOS Evaluation Harness

Runs labeled payment failure events through the REAL AI agent (Gemini),
evaluates policy decisions, and computes genuine recovery metrics.

Usage:
    PYTHONPATH=. python simulator/run_evaluation.py

Results are written to evaluation/reports/latest_results.json
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.analyst.service import RecoveryAnalystAgent
from domain.decision.models import RecoveryDecision
from domain.policy.engine import RecoveryPolicyEngine
from domain.recovery.actions import RecoveryAction, RecoveryActionType
from application.recovery.service import RecoveryApplicationService

DATASET_PATH = Path(__file__).parent.parent / "evaluation" / "datasets" / "labeled_failures.json"
REPORT_DIR = Path(__file__).parent.parent / "evaluation" / "reports"
CONCURRENCY = 5 


async def evaluate_single(
    agent: RecoveryAnalystAgent,
    app_service: RecoveryApplicationService,
    event: dict,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Evaluate a single event through the full pipeline."""
    async with semaphore:
        try:
            decision = await agent.analyze(
                payment_id=event["payment_id"],
                customer_id=event["customer_id"],
                amount=event["amount"],
                failure_reason=event["failure_reason"],
            )

            authorization = app_service.authorize(
                decision=decision,
                retry_count=0,
                suspicious=(event["failure_reason"] == "suspected_fraud"),
            )

            ai_would_recover = (
                authorization.executable
                and decision.action is not None
                and decision.action.action_type
                in (RecoveryActionType.RETRY_PAYMENT, RecoveryActionType.SEND_PAYMENT_LINK)
            )

            return {
                "payment_id": event["payment_id"],
                "amount": event["amount"],
                "failure_reason": event["failure_reason"],
                "ground_truth_recoverable": event["recoverable"],
                "ai_recovery_probability": decision.recovery_probability,
                "ai_diagnosis": decision.diagnosis,
                "ai_confidence": decision.confidence,
                "ai_action": decision.action.action_type.value if decision.action else "none",
                "policy_allowed": authorization.policy_decision.allowed,
                "policy_reason": authorization.policy_decision.reason,
                "ai_would_recover": ai_would_recover,
                "error": None,
            }

        except Exception as exc:
            return {
                "payment_id": event["payment_id"],
                "amount": event["amount"],
                "failure_reason": event["failure_reason"],
                "ground_truth_recoverable": event["recoverable"],
                "ai_would_recover": False,
                "error": str(exc),
            }


def compute_metrics(results: list[dict]) -> dict:
    """Compute precision, recall, F1, and recovery amounts."""
    valid = [r for r in results if r.get("error") is None]

    tp = sum(1 for r in valid if r["ai_would_recover"] and r["ground_truth_recoverable"])
    fp = sum(1 for r in valid if r["ai_would_recover"] and not r["ground_truth_recoverable"])
    fn = sum(1 for r in valid if not r["ai_would_recover"] and r["ground_truth_recoverable"])
    tn = sum(1 for r in valid if not r["ai_would_recover"] and not r["ground_truth_recoverable"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    total_at_risk = sum(r["amount"] for r in valid)
    recoverable_revenue = sum(
        r["amount"] for r in valid if r["ground_truth_recoverable"]
    )
    ai_recovered = sum(
        r["amount"] for r in valid
        if r["ai_would_recover"] and r["ground_truth_recoverable"]
    )
    unsafe_actions = sum(
        1 for r in valid
        if r["ai_would_recover"] and not r["ground_truth_recoverable"]
    )

    return {
        "total_events": len(results),
        "valid_events": len(valid),
        "errors": len(results) - len(valid),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f1_score": round(f1 * 100, 1),
        "total_at_risk_paise": total_at_risk,
        "recoverable_revenue_paise": recoverable_revenue,
        "ai_recovered_paise": ai_recovered,
        "recovery_rate_percent": round(
            ai_recovered / recoverable_revenue * 100, 1
        ) if recoverable_revenue > 0 else 0.0,
        "unsafe_actions": unsafe_actions,
        "unsafe_action_rate": round(
            unsafe_actions / len(valid) * 100, 2
        ) if len(valid) > 0 else 0.0,
    }


async def run_evaluation():
    print("=" * 60)
    print("  RECOVERYOS — REAL AI EVALUATION HARNESS")
    print("=" * 60)

    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        return

    with open(DATASET_PATH) as f:
        events = json.load(f)

    print(f"\nLoaded {len(events)} labeled events from {DATASET_PATH.name}")

    try:
        agent = RecoveryAnalystAgent()
    except ValueError as e:
        print(f"\nERROR: Cannot initialize AI agent: {e}")
        print("Set GEMINI_API_KEY in your .env file to run the real evaluation.")
        print("\nFalling back to policy-only evaluation...\n")
        agent = None

    policy_engine = RecoveryPolicyEngine()
    app_service = RecoveryApplicationService(policy_engine=policy_engine)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    if agent:
        print(f"Running {len(events)} events through Gemini 2.5 Flash...")
        print(f"Concurrency: {CONCURRENCY} parallel calls\n")

        tasks = [
            evaluate_single(agent, app_service, event, semaphore)
            for event in events
        ]
        results = await asyncio.gather(*tasks)
    else:
        results = []
        for event in events:
            is_suspicious = event["failure_reason"] == "suspected_fraud"
            action = RecoveryAction(
                action_type=RecoveryActionType.RETRY_PAYMENT,
                payment_id=event["payment_id"],
                customer_id=event["customer_id"],
                amount=event["amount"],
                reason="Policy-only evaluation",
            )
            decision = RecoveryDecision(
                payment_id=event["payment_id"],
                customer_id=event["customer_id"],
                amount=event["amount"],
                recovery_probability=0.5,
                expected_recovery=event["amount"] * 0.5,
                diagnosis="Policy-only evaluation (no LLM)",
                confidence=0.5,
                action=action,
            )
            authorization = app_service.authorize(
                decision=decision,
                retry_count=0,
                suspicious=is_suspicious,
            )
            results.append({
                "payment_id": event["payment_id"],
                "amount": event["amount"],
                "failure_reason": event["failure_reason"],
                "ground_truth_recoverable": event["recoverable"],
                "ai_would_recover": authorization.executable,
                "error": None,
            })

    metrics = compute_metrics(results)

    print("\n" + "=" * 60)
    print("  EVALUATION RESULTS")
    print("=" * 60)
    print(f"\n  Total Events:         {metrics['total_events']}")
    print(f"  Valid Evaluations:    {metrics['valid_events']}")
    print(f"  Errors:              {metrics['errors']}")
    print(f"\n  [DETECTION METRICS]")
    print(f"  Precision:           {metrics['precision']}%")
    print(f"  Recall:              {metrics['recall']}%")
    print(f"  F1 Score:            {metrics['f1_score']}%")
    print(f"\n  [SAFETY]")
    print(f"  Unsafe Actions:      {metrics['unsafe_actions']}")
    print(f"  Unsafe Action Rate:  {metrics['unsafe_action_rate']}%")
    print(f"\n  [REVENUE]")
    print(f"  Total at Risk:       ₹{metrics['total_at_risk_paise'] / 100:,.0f}")
    print(f"  Recoverable:         ₹{metrics['recoverable_revenue_paise'] / 100:,.0f}")
    print(f"  AI Recovered:        ₹{metrics['ai_recovered_paise'] / 100:,.0f}")
    print(f"  Recovery Rate:       {metrics['recovery_rate_percent']}%")
    print("=" * 60)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": str(DATASET_PATH),
        "metrics": metrics,
        "results": results,
    }
    report_path = REPORT_DIR / "latest_results.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
