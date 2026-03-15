.PHONY: dev backend frontend install migrate format

dev: ## Start backend and frontend concurrently
	@trap 'kill 0' SIGINT; \
	(cd backend && uv run uvicorn app.main:app --reload --port 7400) & \
	(cd frontend && npm run dev) & \
	wait

backend: ## Start backend only
	cd backend && uv run uvicorn app.main:app --reload --port 7400

frontend: ## Start frontend only
	cd frontend && npm run dev

install: ## Install all dependencies
	cd backend && uv sync --extra dev
	cd frontend && npm install

migrate: ## Run database migrations
	cd backend && uv run alembic upgrade head

format: ## Auto-format backend (ruff) and frontend (prettier)
	cd backend && uv run ruff format .
	cd frontend && npm run format
