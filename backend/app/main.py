"""FastAPI application entrypoint.

Initialises the app, mounts all API routers, and configures
middleware (CORS for local dev, lifespan events for DB init, etc.).
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # ensure all ORM models are registered before mapper init
from app.api import auth, experiences, ingestion, proposals, tasks
from app.api.prompts import configs_router
from app.api.prompts import router as prompts_router

logger = logging.getLogger(__name__)

_SCHEDULE_INTERVAL_HOURS = 12


def _run_scheduled_pipeline() -> None:
    """Synchronous wrapper called in a thread executor every 12 hours."""
    from app.db.session import SessionLocal
    from app.jobs.ingestion_job import run_full_pipeline
    from app.models.ingestion_run import TriggeredBy

    db = SessionLocal()
    try:
        result = run_full_pipeline(db, triggered_by=TriggeredBy.scheduled)
        logger.info("Scheduled pipeline result: %s", result)
    except Exception as exc:
        logger.error("Scheduled pipeline failed: %s", exc, exc_info=True)
    finally:
        db.close()


async def _scheduler_loop() -> None:
    """Asyncio task: wait 12 hours, run the pipeline, repeat."""
    interval = _SCHEDULE_INTERVAL_HOURS * 3600
    while True:
        await asyncio.sleep(interval)
        logger.info("Scheduled pipeline triggered (every %dh)", _SCHEDULE_INTERVAL_HOURS)
        try:
            await asyncio.to_thread(_run_scheduled_pipeline)
        except Exception as exc:
            logger.error("Scheduler loop error: %s", exc, exc_info=True)


async def _reset_stale_runs() -> None:
    """Reset any IngestionRuns stuck in 'running' to 'failed' on startup.

    Prevents the concurrency guard from permanently blocking after a server
    crash or restart while a run was in progress.
    """
    from app.db.session import SessionLocal
    from app.models.ingestion_run import IngestionRun, RunStatus

    db = SessionLocal()
    try:
        stale = db.query(IngestionRun).filter(IngestionRun.status == RunStatus.running).all()
        for run in stale:
            run.status = RunStatus.failed
            run.error_summary = "server restarted while run was in progress"
        if stale:
            db.commit()
            logger.warning("Reset %d stale running runs to failed", len(stale))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _reset_stale_runs()
    task = asyncio.create_task(_scheduler_loop())
    logger.info("Background pipeline scheduler started (interval=%dh)", _SCHEDULE_INTERVAL_HOURS)
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Tasky", version="0.1.0", lifespan=lifespan)

# ── Routers ───────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(experiences.router, prefix="/experiences", tags=["experiences"])
app.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
app.include_router(configs_router, prefix="/prompt-configs", tags=["prompt-configs"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
