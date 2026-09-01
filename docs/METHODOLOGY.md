# RecoveryOS Evaluation Methodology

This document explains how the 50,000-event benchmark simulation is calculated and what the numbers on the dashboard actually mean.

## The Goal
The benchmark exists to scientifically prove the incremental revenue uplift of an AI-driven, context-aware recovery agent versus a traditional "dumb" retry ladder.

## Simulation Parameters

- **Batch Size**: 50,000 synthetic failure events
- **Execution**: Run entirely in-memory using the `RecoveryPolicyEngine`
- **AI Probabilities**: This is a Monte Carlo simulation. We do not call the live Gemini API 50,000 times (to save costs/latency). Instead, we use statistically modeled recovery probabilities derived from our AI's typical performance, as defined in `domain/policy/taxonomy.yaml`.

## The Failure Mix

The 50k events are generated using an estimated distribution of real-world internet payment failures:

- **Insufficient Funds (40%)**: `time_shiftable`. A dumb immediate retry will fail. The AI waits for the right time or sends a link.
- **Network Timeout (40%)**: `transient`. A dumb retry often succeeds. The AI also retries immediately.
- **Card Expired (15%)**: `dead_instrument`. A dumb retry will fail 100% of the time. The AI sends a payment link for a new card.
- **Suspected Fraud (5%)**: `prohibited`. Any automated retry is dangerous. The AI halts and escalates.

## The Baselines

To measure "Uplift", we must compare RecoveryOS against a baseline.

### B1: The Traditional Baseline (Static Rules)
- **Behavior**: Blindly retries the payment if the retry count is < 2.
- **Result**: Recovers a portion of `temporary_network_timeout` errors, but fails completely on `insufficient_funds` and `card_expired`. Unsafely attempts to retry `suspected_fraud`.

### B2: RecoveryOS (AI Agent)
- **Behavior**: Uses the failure context to choose the exact right action (retry, link, or escalate).
- **Result**: Recovers transient errors *plus* successfully recovers a large percentage of NSF and Expired Card failures via intelligent payment link routing. Blocks 100% of fraud attempts.

## Metrics Defined

*   **Baseline Recovery**: The total INR recovered by the B1 static rule set.
*   **AI Recovery**: The total INR recovered by the RecoveryOS agent.
*   **Incremental Uplift**: `((AI Recovery - Baseline) / Baseline) * 100`. The percentage increase in recovered revenue.
*   **Policy Blocks**: The number of times the Policy Engine successfully intervened to stop an unsafe AI proposal or enforce a hard rule (e.g., stopping a fraud retry).
*   **Unsafe Action Rate**: The percentage of actions that violated core safety boundaries. A 0% rate proves the effectiveness of the Policy Engine.
