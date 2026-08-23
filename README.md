# Razorpay RecoveryOS ⚡️

**Autonomous Revenue Recovery Agent for Track 03 (Razorpay AI Buildathon)**

RecoveryOS is an AI-driven, policy-gated revenue recovery engine. It does not just blindly retry failed payments. It detects revenue at risk, uses AI to diagnose the root cause, calculates expected recovery value, and executes a strictly bounded recovery action via Razorpay's API.

### 🏆 50,000-Event Evaluation Benchmark

Evaluated against a synthetic dataset of 50k payment failures (Insufficient Funds, Network Timeouts, Expired Cards, and Fraud):

* **Baseline Recovery (Static Rules):** ₹4.28Cr
* **RecoveryOS (AI Agent):** ₹5.62Cr
* **Incremental Revenue Uplift:** **+31.4%**
* **Unsafe Action Rate:** **0.0%** (Strictly enforced by Policy Engine)

---

## 🏗 System Architecture

We deliberately avoided the anti-pattern of giving an LLM unrestricted access to payment APIs. Our architecture guarantees compliant escalation, stopping rules, and idempotency.

```text
               REVENUE AT RISK (Webhook / API)
                      │
                 [ AI ANALYST ] (Gemini 2.5 Flash + Structured Outputs)
                 Diagnoses failure & proposes action
                      │
               [ POLICY ENGINE ]  <-- The Deterministic Safety Boundary
               Evaluates proposal against rules (Limits, High-Value, Fraud)
                      │
              ┌───────┴───────┐
              ▼               ▼
           BLOCKED         APPROVED
         (Human Review)       │
                              ▼
                    [ ORCHESTRATOR ]
                              │
                    [ POSTGRESQL DB ] <-- Audit Trail & Idempotency
                              │
                   [ RAZORPAY EXECUTOR ]
               Creates Razorpay Retry Order
                              │
                    [ WEBHOOK SYNC ]
               Listens for payment.captured
✨ Key Engineering Features
Deterministic Safety Boundary: The AI proposes intent (RecoveryAction). The deterministic RecoveryPolicyEngine enforces rules (e.g., blocking automated retries > ₹25,000 or suspected fraud).
Idempotency & Auditability: Backed by a PostgreSQL database (ExecutionRecord), ensuring a crashed worker never accidentally executes the same recovery twice.
Webhook Reconciliation: Securely parses x-razorpay-signature and x-razorpay-event-id to idempotently update execution states when a customer completes the payment.
Test-Driven Design: Includes 54 passing tests including Dry-Run Executors, failing provider mocks, and strict policy assertions.
🚀 Getting Started
Backend (FastAPI + PostgreSQL)
Bash
cd apps/api
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
Frontend (Next.js Merchant Control Room)
Bash
cd apps/web
npm install
npm run dev
Built for the Razorpay AI Buildathon 2026.
