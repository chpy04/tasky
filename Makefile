.PHONY: dev backend frontend install migrate

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
	cd backend && uv sync
	cd frontend && npm install

migrate: ## Run database migrations
	cd backend && uv run alembic upgrade head
