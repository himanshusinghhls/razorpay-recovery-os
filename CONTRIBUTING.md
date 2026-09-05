# Contributing to RecoveryOS

Thank you for your interest in RecoveryOS! This guide will help you get started.

## Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/himanshusinghhls/razorpay-recovery-os.git
cd razorpay-recovery-os

# 2. Set up the project
make setup

# 3. Configure environment
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
# Edit both files with your credentials

# 4. Start infrastructure
make infra

# 5. Initialize database
make db-init && make seed

# 6. Run (in 3 separate terminals)
make dev       # Terminal 1: API server (port 8000)
make worker    # Terminal 2: Background worker
make web       # Terminal 3: Dashboard (port 3000)
```

## Running Tests

```bash
make test           # All 107 tests
make test-unit      # Unit tests only
make test-integration # Integration tests only
make lint           # Python + JS linting
```

## Architecture

RecoveryOS follows **Hexagonal Architecture**. Before contributing, please understand the layer boundaries:

- **`domain/`** — Pure business logic. No external dependencies. Never import from other layers.
- **`application/`** — Orchestration services. Imports only from `domain/`.
- **`agents/`** — AI integration (Gemini). Imports from `domain/`.
- **`integrations/`** — External service adapters (Razorpay).
- **`apps/api/`** — FastAPI HTTP layer. Imports from all layers above.
- **`apps/web/`** — Next.js dashboard. Communicates only via HTTP API.

## Code Standards

- **Python**: Formatted with `ruff`. Type hints required. All new code must have tests.
- **TypeScript**: ESLint enforced. No `any` types. Use the design system variables from `globals.css`.
- **Security**: Never store secrets in code. All auth is per-route via `Depends()`. No `NEXT_PUBLIC_*` secrets.
- **Tests**: Every new feature requires unit tests. Security-sensitive features require adversarial tests.

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for your changes
4. Ensure `make test` and `make lint` pass with zero errors
5. Submit a pull request with a clear description

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
