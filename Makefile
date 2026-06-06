.PHONY: up setup test lint format

# One command runs everything (after: cp .env.example .env)
up:
	docker compose up --build

# Local development setup (Python 3.12 + Node 20+)
setup:
	cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm ci

test:
	cd backend && .venv/bin/pytest -q
	cd frontend && npm run test -- --run

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app tests
	cd frontend && npm run lint && npm run format:check && npm run typecheck

format:
	cd backend && .venv/bin/ruff check --fix . && .venv/bin/ruff format .
	cd frontend && npm run format
