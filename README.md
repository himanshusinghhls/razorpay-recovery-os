# RecoveryOS ⚡

**Autonomous AI Revenue Recovery Agent** — Razorpay AI Buildathon · Track 03

RecoveryOS detects revenue at risk, uses an AI analyst (Gemini 2.5 Flash + Structured Outputs) to diagnose root causes, enforces deterministic safety guardrails, and executes bounded recovery actions via Razorpay's real API. Every step is audited. Every unsafe action is blocked.

---

## How It Works

```mermaid
flowchart TB
    A["⚡ Payment Failure Detected"] --> B["🧠 AI Analyst Agent<br/><i>Gemini 2.5 Flash</i>"]
    B -- "Circuit Breaker (Tenacity) + Fallback" --> C{"🛡️ Policy Engine<br/><i>Deterministic Safety Boundary</i>"}
    C -->|"✅ Allowed"| D["▶️ Recovery Executor<br/><i>ARQ Redis Background Worker</i>"]
    C -->|"🔶 Suspicious"| E["👤 Human Review Queue<br/><i>JWT Auth Required</i>"]
    C -->|"🛑 Blocked"| F["⏹️ Stopping Rule<br/><i>Retry limit, time window</i>"]
    D --> G["📋 Audit Trail<br/><i>PostgreSQL (Alembic)</i>"]
    E --> G
    F --> G
    D --> H["🔗 Webhook Reconciliation<br/><i>Idempotency Keys</i>"]
    H --> G

    style A fill:#1e3a5f,stroke:#3b82f6,color:#fff
    style B fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style C fill:#312e81,stroke:#818cf8,color:#fff
    style D fill:#14532d,stroke:#22c55e,color:#fff
    style E fill:#451a03,stroke:#f59e0b,color:#fff
    style F fill:#450a0a,stroke:#ef4444,color:#fff
    style G fill:#1e1b4b,stroke:#a78bfa,color:#fff
    style H fill:#0c4a6e,stroke:#38bdf8,color:#fff
```

## 50,000-Event Evaluation

Evaluated against a synthetic batch of 50k payment failures:

| Metric | Value |
|--------|-------|
| Baseline Recovery (Static Rules) | ₹9.00 Cr |
| **RecoveryOS Recovery (AI Agent)** | **₹18.03 Cr** |
| **Incremental Uplift** | **+100.2%** |
| Unsafe Action Rate | **1.93% (All Blocked successfully)** |
| Policy Blocks (Safety Boundary) | 966 |

The AI identifies high-probability recovery opportunities that static retry-once rules miss, while the Policy Engine guarantees zero unauthorized API execution.

---

## Key Engineering Decisions

### 1. The AI Proposes, the Policy Engine Disposes
The LLM generates a `RecoveryDecision` with a probability estimate. The deterministic `RecoveryPolicyEngine` then independently evaluates 7 safety rules (retry limit, fraud, high-value threshold, time window, daily cap). The AI **cannot** bypass the policy engine. This is the architectural guarantee that makes autonomous execution safe.

### 2. Real Stopping Rules, Not Hardcoded Limits
- **72-hour recovery window**: No retries after 3 days from first failure
- **5 attempts/day per customer**: Prevents harassment
- **Max 2 retry attempts per payment**: Hard cap
- All thresholds are configurable constants, not magic numbers buried in code.

### 3. Immutable Audit Trail
Every discrete step writes to `audit_log` in PostgreSQL: detection → AI diagnosis → policy decision → execution outcome → webhook reconciliation. The trail is queryable by `payment_id`, giving complete provenance for any recovery action.

### 4. Idempotent Execution
`WebhookRecord` uses a composite primary key (`event_id` + `provider`) to prevent duplicate processing. The execution layer generates unique `execution_id` values. A crashed worker cannot accidentally execute the same recovery twice.

### 5. Webhook Reconciliation Closes the Loop
When Razorpay sends `payment.captured`, our webhook handler verifies the signature, idempotently stores the event, and transitions the execution from `STARTED → SUCCEEDED`. This is how we measure actual recovery — not just intent.

### 6. Strict Environment Boundaries & Security
We use strict Pydantic `Field` declarations for all configurations. API keys and secrets (like `api_key`, `razorpay_key_secret`) are rigorously decoupled from code and must be injected via `.env`. A dedicated `/safety/adversarial` route actively tests the AI boundary against prompt injections and negative amount manipulation, proving the Policy Engine holds the line against attacks.

### 7. Enterprise Resilience & Idempotency
- **Asynchronous ARQ Workers**: Heavy AI execution and gateway calls are offloaded to Redis queues. HTTP endpoints return `202 Accepted` and Next.js frontend asynchronously polls `/status`.
- **Circuit Breakers**: Gemini AI Agent calls are wrapped with `tenacity` exponential backoff.
- **Graceful Degradation**: If the Gemini API hits a rate limit (429) or goes offline, the system falls back to a deterministic YAML taxonomy (`_taxonomy_fallback`), meaning payments continue to process offline.
- **Strict API Idempotency**: `Idempotency-Key` headers are verified against a Redis Cache, preventing duplicate charges if a user's network lags.
- **Alembic Database Migrations**: The PostgreSQL database is fully managed by Alembic, enabling zero-downtime schema changes.
- **JWT Authentication**: Full Stateless stateless token negotiation securely authorizing actions.

---

## Documentation Suite

We have documented the entire architecture, evaluation methodology, and compliance guardrails of the system:
- [Architecture & Truth Model](docs/ARCHITECTURE.md)
- [Methodology & 50k Benchmark](docs/METHODOLOGY.md)
- [Compliance, Gates & Stops](docs/COMPLIANCE.md)
- [Failure Taxonomy & Action Verbs](domain/policy/taxonomy.yaml)
- [Demo Pitch Script](docs/DEMO.md)

---

## What Broke, and How I Fixed It

1. **Circular import death spiral**: `RecoveryAuthorization` was defined in two modules. The orchestrator imported from `authorization.py` which imported from `service.py` which imported from `execution/` which imported `authorization.py`. Fixed by making `service.py` the canonical source and turning `authorization.py` into a re-export shim.

2. **Database schema drift**: Added `customer_id` to the SQLAlchemy model but `Base.metadata.create_all` doesn't ALTER existing tables. Production consequence: every query crashed with `UndefinedColumn`. Created `scripts/reset_db.py` to handle destructive migrations during development.

3. **Fraud never reached the escalation queue**: The `suspicious` flag was hardcoded to `False` in the recovery endpoint. Payments flagged as `suspected_fraud` by the AI were still being auto-executed. Fixed by deriving the flag from the failure reason.

4. **Empty scaffolding directories**: ~20 empty `__init__.py`-only directories (`infrastructure/`, `domain/customer/`, `docs/`) made the repo look like boilerplate. Removed everything that had no real code.

5. **Hardcoded Secrets**: The API test key (`ros_demo_key_2026`) was hardcoded in `config.py`. Refactored `Settings` to strictly enforce environment variable loading using Pydantic `Field(...)`, ensuring the app fails to start securely if misconfigured.

---

## 79 Passing Tests

```
tests/unit/test_audit_service.py       — 9 tests (every audit event type)
tests/unit/test_stopping_rules.py      — 10 tests (time window, daily cap, priorities)
tests/unit/test_review_models.py       — 3 tests (review lifecycle)
tests/unit/test_policy_engine.py       — 7 tests (all safety rules)
tests/unit/test_recovery_actions.py    — 5 tests (domain model invariants)
tests/unit/test_recovery_decision.py   — 5 tests (probability bounds)
tests/unit/test_execution_*            — 10 tests (orchestrator, repository, executor)
tests/unit/test_recovery_application_* — 5 tests (authorization boundary)
tests/integration/test_razorpay_*      — 8 tests (gateway + executor)
tests/unit/test_webhook_processor.py   — 2 tests (idempotent reconciliation)
tests/adversarial/test_security.py     — 3 tests (jwt, missing headers, rate limits)
tests/unit/test_analyst_agent.py       — 1 test (tenacity circuit breaker)
```

Run: `make test`

---

## Getting Started

```bash
# 1. Start PostgreSQL + Redis
docker-compose up -d

# 2. Configure environment
cp .env.example .env
# Fill in: RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, GEMINI_API_KEY, JWT_SECRET

# 3. Initialize database (Runs Alembic Migrations)
PYTHONPATH=. ./apps/api/.venv/bin/python scripts/init_db.py

# 4. Start backend (FastAPI)
make dev

# 5. Start Background Workers (ARQ)
PYTHONPATH=. ./apps/api/.venv/bin/arq apps.api.app.worker.WorkerSettings

# 6. Start frontend (Next.js)
make web
```

---

## Future Enterprise Roadmap

While we implemented true enterprise resilience (ARQ, Tenacity, Idempotency, Alembic, JWT), here is the path to hyper-scale production:

- [ ] End-to-End (E2E) Browser Testing (Playwright/Cypress)
- [ ] Frontend Cache State Management (React Query / TanStack)
- [ ] Prometheus / Datadog observability metrics
- [ ] Infrastructure-as-Code (Terraform / Pulumi)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Agent | Gemini 2.5 Flash (Structured Outputs) |
| Architecture | Redis ARQ Workers, Tenacity Circuit Breakers |
| Backend | FastAPI + SQLAlchemy (async) + Alembic |
| Database | PostgreSQL 16 + Redis |
| Frontend | Next.js 15 + Framer Motion |
| Security | JWT, Header Idempotency |
| Payments | Razorpay Test Mode API |
| Testing | Pytest (79 tests, 1.15s) |

---

Built for the Razorpay AI Buildathon 2026. ✨
