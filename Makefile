.PHONY: test dev db benchmark lint clean

# ---- Development ----

dev:
	PYTHONPATH=. uvicorn apps.api.app.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

# ---- Database ----

db:
	docker-compose up -d postgres

db-init:
	PYTHONPATH=. python scripts/init_db.py

db-reset:
	docker-compose down -v && docker-compose up -d postgres
	sleep 3
	PYTHONPATH=. python scripts/init_db.py

# ---- Testing ----

test:
	PYTHONPATH=. pytest tests/ -v

test-unit:
	PYTHONPATH=. pytest tests/unit/ -v

test-integration:
	PYTHONPATH=. pytest tests/integration/ -v

# ---- Evaluation ----

benchmark:
	PYTHONPATH=. python simulator/run_evaluation.py

# ---- Linting ----

lint:
	ruff check .

format:
	ruff format .

# ---- Cleanup ----

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
