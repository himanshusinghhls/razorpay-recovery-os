# Compliance & Guardrails

How RecoveryOS ensures safety, prevents spam, and guarantees safe AI execution.

## The Principle
**The AI proposes. The Policy Engine validates. The Gates may refuse. The Ledger audits.**

We never allow the LLM to execute money movement or customer contact without passing through a deterministic, hard-coded safety boundary.

## The Policy Engine Gates (`domain/policy/engine.py`)

Every proposed action must pass 9 sequential gates. A failure at any gate instantly blocks execution.

| Gate | Blocks When | Purpose |
|------|-------------|---------|
| `amount_sanity` | Amount <= 0 | Prevent invalid API calls |
| `retry_sanity` | Retry count < 0 | Prevent invalid state |
| `max_retry_cap` | `retry_count >= 2` | Prevent infinite retry loops and excessive gateway fees |
| `fraud_escalation`| `suspicious == True` | Never automate recovery on stolen cards; human review only |
| `high_value_cap` | Amount >= ₹25,000 | Require merchant sign-off for massive transactions |
| `recovery_window` | Time since failure > 72h | Stop harassing customers for old failures |
| `daily_attempt_cap`| `customer_attempts > 5` | Anti-spam: cap daily touches per user |
| `contact_window` | Outside IST 09:00–21:00 | **Compliance**: No midnight SMS/emails. Silent retries are still allowed. |
| `frequency_cap` | `contact_count >= 3` | **Compliance**: Strict limit on the number of messages sent per failure. |

## Audit & Idempotency

1.  **Immutable Audit Log**: Every single step (detection, AI diagnosis, policy decision, execution result) is appended to the PostgreSQL `audit_log` table. Entries are never updated or deleted.
2.  **Idempotent Execution**: Webhooks are deduplicated using a composite key (`event_id` + `provider`). The recovery executor generates unique idempotency keys for Razorpay API calls, ensuring a network blip doesn't cause a double-charge.
3.  **Comprehensive E2E Testing**: All security boundaries, role-based access controls (RBAC), and idempotency checks are continuously verified by a suite of end-to-end tests that mock infrastructure to prove API layer resilience.

## PII & Data Privacy

The `RecoveryContext` provided to the Gemini LLM only includes:
- Amount (integer)
- Failure reason code
- Retry count

It **never** includes the customer's PAN, card number, email, phone number, or physical address. The LLM cannot leak what it doesn't know.
