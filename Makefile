.PHONY: help setup dev worker web infra db-init db-reset seed seed-db test test-unit test-integration benchmark lint format clean

PY := ./apps/api/.venv/bin/python
PIP := ./apps/api/.venv/bin/pip

help:
	@echo "RecoveryOS"
	@echo ""
	@echo "  make setup     Create the venv, install API + web dependencies"
	@echo "  make infra     Start Postgres + Redis"
	@echo "  make db-init   Run Alembic migrations"
	@echo "  make seed      Create the demo merchant and users"
	@echo "  make dev       Run the API (port 8000)"
	@echo "  make worker    Run the ARQ background worker"
	@echo "  make web       Run the dashboard (port 3000)"
	@echo "  make test      Run the test suite"
	@echo ""
	@echo "First run:  make setup && make infra && make db-init && make seed"
	@echo "Then, in three terminals: make dev / make worker / make web"

setup:
	python3 -m venv apps/api/.venv
	$(PIP) install --upgrade pip
	$(PIP) install -r apps/api/requirements.txt
	cd apps/web && npm install
	@echo "Now copy .env.example to .env and apps/web/.env.example to apps/web/.env.local"

infra:
	docker compose up -d
	@echo "waiting for Postgres and Redis to report healthy..."
	@until docker compose ps --format '{{.Service}} {{.Health}}' | grep -q 'postgres healthy'; do sleep 1; done
	@until docker compose ps --format '{{.Service}} {{.Health}}' | grep -q 'redis healthy'; do sleep 1; done
	@echo "infrastructure ready"

db: infra

db-init:
	PYTHONPATH=. $(PY) scripts/init_db.py

db-reset:
	docker compose down -v
	$(MAKE) infra
	$(MAKE) db-init
	$(MAKE) seed
	$(MAKE) seed-db

seed:
	PYTHONPATH=. $(PY) scripts/seed_users.py

seed-db:
	PYTHONPATH=. $(PY) scripts/seed_db.py

dev:
	PYTHONPATH=. ./apps/api/.venv/bin/uvicorn apps.api.app.main:app --reload --port 8000

worker:
	PYTHONPATH=. ./apps/api/.venv/bin/arq apps.api.app.worker.WorkerSettings

web:
	cd apps/web && npm run dev

test:
	PYTHONPATH=. ./apps/api/.venv/bin/pytest tests/ -v

test-unit:
	PYTHONPATH=. ./apps/api/.venv/bin/pytest tests/unit/ -v

test-integration:
	PYTHONPATH=. ./apps/api/.venv/bin/pytest tests/integration/ -v

benchmark:
	PYTHONPATH=. $(PY) simulator/run_evaluation.py

lint:
	ruff check .
	cd apps/web && npm run lint

format:
	ruff format .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
