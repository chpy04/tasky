"""FastAPI application entrypoint.

Initialises the app, mounts all API routers, and configures
middleware (CORS for local dev, lifespan events for DB init, etc.).
"""

from fastapi import FastAPI

import app.models  # ensure all ORM models are registered before mapper init
from app.api import experiences, ingestion, prompts, proposals, tasks

app = FastAPI(title="Tasky", version="0.1.0")

# ── Routers ───────────────────────────────────────────────
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(experiences.router, prefix="/experiences", tags=["experiences"])
app.include_router(prompts.router, prefix="/prompts", tags=["prompts"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
