# RecoveryOS Architecture

Razorpay Buildathon · Track 03: AI Revenue Recovery

## Core Design Principle
**The AI Proposes. The Policy Engine Disposes. The Audit Log Remembers.**

RecoveryOS is designed around a strictly bounded AI agent. The AI is used for *intelligence* (diagnosing complex failures, extracting context), but it is never allowed to execute actions autonomously without passing through a deterministic, rule-based safety engine.

## End-to-End Pipeline

```mermaid
flowchart TB
    subgraph Detection
      A["Razorpay Checkout Fails"] --> B["Webhook / API Trigger"]
    end

    subgraph Intelligence
      B --> C["Gemini 2.5 Flash"]
      C --> D["Diagnose Failure"]
      D --> E["Propose Action & Probability"]
    end

    subgraph Safety Boundary
      E --> F{"Policy Engine"}
      F -->|"Pass"| G["Recovery Execution"]
      F -->|"Block: Suspicious/High-Value"| H["Human Review Queue"]
      F -->|"Block: Limits Exceeded"| I["Stopping Rule (Halt)"]
    end

    subgraph Execution & Audit
      G --> J["Razorpay Retry / Payment Link"]
      J --> K[("PostgreSQL Audit Log")]
      H --> K
      I --> K
    end

    subgraph Security & Environment
      L["Environment Variables (.env)"] -.->|Injected via Pydantic Field| M["Settings (FastAPI)"]
    end

    style A fill:#1e3a5f,stroke:#3b82f6,color:#fff
    style C fill:#4c1d95,stroke:#8b5cf6,color:#fff
    style F fill:#831843,stroke:#f43f5e,color:#fff
    style J fill:#14532d,stroke:#22c55e,color:#fff
    style K fill:#1e1b4b,stroke:#a78bfa,color:#fff
```

## Truth Model & State Management

RecoveryOS manages state across three distinct layers:

| Layer | Responsibility | Components |
|-------|----------------|------------|
| **Observed State** | What actually happened | Webhook events, failure reasons, amounts |
| **Decision State** | What the AI and Policy Engine decided to do | `RecoveryDecision`, `PolicyDecision`, Pending Reviews |
| **Audit/Execution State** | What was actually executed | `AuditRecord`, `ExecutionRecord` |

## Security & Graceful Degradation

- **Adversarial Resiliency:** A dedicated testing suite (`/safety/adversarial`) attacks the API with prompt injections, negative amounts, and fake fraud events to guarantee the Policy Engine boundaries hold against malicious actors.
- **Graceful Fallback:** If the Gemini API hits a rate limit (429) or fails, the application doesn't crash. It falls back to a deterministic taxonomy configuration to safely score and route failures offline.
- **Environment Isolation:** Secrets and keys are not hardcoded. Pydantic `Field(...)` requirements strictly enforce `.env` configuration prior to the backend booting.

## Package Structure

| Path | Purpose |
|------|---------|
| `apps/web/` | Next.js 15 frontend. Real-time dashboard and Razorpay Checkout integration. |
| `apps/api/` | FastAPI backend. Orchestrates the recovery pipeline and serves data to the UI. |
| `domain/` | Core business logic, pure Python models. Contains the Policy Engine and Taxonomy. |
| `integrations/` | Adapters for external services (Razorpay, Google GenAI). |
| `docs/` | Architecture, Methodology, and Compliance documentation. |

## Closed Set of Action Verbs

The AI is strictly constrained (via Structured Outputs) to propose actions from a closed set defined in `domain/policy/taxonomy.yaml`:

1. `retry_payment`: Silently retry a transient error.
2. `send_payment_link`: Generate a new checkout link for a dead instrument.
3. `escalate_human`: Immediately block and route to the escalation queue.

The AI cannot invent new verbs or bypass the `RecoveryActionType` enum.
