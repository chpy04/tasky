"""Ingestion control API routes.

Endpoints:
    GET    /ingestion/preview/github   Fetch GitHub data and return raw batches (no DB write)
    GET    /ingestion/preview/gmail    Fetch Gmail data and return raw batches  (no DB write)
    GET    /ingestion/preview/slack    Fetch Slack data and return raw batches  (no DB write)
    GET    /ingestion/preview/canvas   Fetch Canvas data and return raw batches (no DB write)

    POST   /ingestion/runs             Create and execute an ingestion run
    GET    /ingestion/runs             List ingestion runs
    GET    /ingestion/runs/{id}        Get a single run with batch details
    POST   /ingestion/runs/{id}/rerun  Re-run an existing ingestion run
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connectors.base import ConnectorResult
from app.db.session import get_db

router = APIRouter()

_SINCE_DAYS = Query(default=7, ge=1, le=90)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CreateRunRequest(BaseModel):
    start_date: str  # ISO date string e.g. "2026-03-01"
    end_date: str | None = None  # ISO date string; defaults to now if omitted


class BatchResponse(BaseModel):
    id: int
    source_type: str
    raw_payload: str
    created_at: str
    status: str
    item_count: int | None
    api_calls: int | None
    duration_ms: float | None
    llm_cost: float | None
    found_new_content: bool | None
    success: bool | None
    connector_metadata: str | None


class RunSummaryResponse(BaseModel):
    id: int
    started_at: str
    finished_at: str | None
    status: str
    triggered_by: str
    range_start: str | None
    range_end: str | None
    error_summary: str | None
    batch_count: int


class RunDetailResponse(RunSummaryResponse):
    batches: list[BatchResponse]


# ---------------------------------------------------------------------------
# Preview endpoints (unchanged)
# ---------------------------------------------------------------------------


def _result_to_response(result: ConnectorResult) -> dict:
    return {
        "success": result.success,
        "found_new_content": result.found_new_content,
        "item_count": result.item_count,
        "api_calls": result.api_calls,
        "llm_cost": result.llm_cost,
        "duration_ms": result.duration_ms,
        "batches": result.payload,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/preview/github")
def preview_github(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch GitHub notifications and return ConnectorResult without persisting."""
    from app.connectors.github import GitHubConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    try:
        result = GitHubConnector().fetch(since)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _result_to_response(result)


@router.get("/preview/gmail")
def preview_gmail(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch Gmail emails and return ConnectorResult without persisting."""
    from app.connectors.gmail import GmailConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    result = GmailConnector().fetch(since)
    return _result_to_response(result)


@router.get("/preview/slack")
def preview_slack(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch Slack messages and return ConnectorResult without persisting."""
    from app.connectors.slack import SlackConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    try:
        result = SlackConnector().fetch(since)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _result_to_response(result)


@router.get("/preview/canvas")
def preview_canvas(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch Canvas assignments and return ConnectorResult without persisting."""
    from app.connectors.canvas import CanvasConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    result = CanvasConnector().fetch(since)
    return _result_to_response(result)


# ---------------------------------------------------------------------------
# Run endpoints
# ---------------------------------------------------------------------------


def _utc_iso(dt) -> str:
    """Return an ISO string with explicit UTC offset so JS parses it as UTC."""
    return dt.replace(tzinfo=timezone.utc).isoformat()


def _run_to_summary(run) -> dict:
    return {
        "id": run.id,
        "started_at": _utc_iso(run.started_at),
        "finished_at": _utc_iso(run.finished_at) if run.finished_at else None,
        "status": run.status.value,
        "triggered_by": run.triggered_by.value,
        "range_start": _utc_iso(run.range_start) if run.range_start else None,
        "range_end": _utc_iso(run.range_end) if run.range_end else None,
        "error_summary": run.error_summary,
        "batch_count": len(run.batches),
        "total_chars": sum(len(b.raw_payload) for b in run.batches),
        "proposal_count": sum(len(b.proposals) for b in run.batches),
    }


def _run_to_detail(run) -> dict:
    summary = _run_to_summary(run)
    summary["batches"] = [
        {
            "id": b.id,
            "source_type": b.source_type.value,
            "raw_payload": b.raw_payload,
            "created_at": b.created_at.isoformat(),
            "status": b.status.value,
            "item_count": b.item_count,
            "api_calls": b.api_calls,
            "duration_ms": b.duration_ms,
            "llm_cost": b.llm_cost,
            "found_new_content": b.found_new_content,
            "success": b.success,
            "connector_metadata": b.connector_metadata,
            "payload_chars": len(b.raw_payload),
        }
        for b in run.batches
    ]
    return summary


@router.post("/runs")
async def create_run(body: CreateRunRequest, db: Session = Depends(get_db)):
    from app.jobs.ingestion_job import _run_full_pipeline_bg
    from app.jobs.run_tracker import claim_run, has_active_run
    from app.models.ingestion_run import IngestionRun, RunStatus
    from app.services.ingestion_service import IngestionService

    existing = db.query(IngestionRun).filter(IngestionRun.status == RunStatus.running).first()
    if has_active_run() or existing:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    range_start = datetime.fromisoformat(body.start_date)
    range_end = (
        datetime.fromisoformat(body.end_date) if body.end_date else datetime.now(timezone.utc)
    )
    svc = IngestionService(db)
    run = svc.create_run(range_start, range_end)
    if not claim_run(run.id):
        raise HTTPException(status_code=409, detail="A run is already in progress")
    asyncio.create_task(asyncio.to_thread(_run_full_pipeline_bg, run.id))
    return _run_to_summary(run)


@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    from app.services.ingestion_service import IngestionService

    runs = IngestionService(db).list_runs()
    return [_run_to_summary(r) for r in runs]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    from app.services.ingestion_service import IngestionService

    run = IngestionService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_detail(run)


@router.post("/runs/{run_id}/rerun")
async def rerun(run_id: int, db: Session = Depends(get_db)):
    from app.jobs.ingestion_job import _run_full_pipeline_bg
    from app.jobs.run_tracker import claim_run, has_active_run
    from app.models.ingestion_run import IngestionRun, RunStatus
    from app.services.ingestion_service import IngestionService

    existing = db.query(IngestionRun).filter(IngestionRun.status == RunStatus.running).first()
    if has_active_run() or existing:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    run = IngestionService(db).reset_run_for_rerun(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not claim_run(run.id):
        raise HTTPException(status_code=409, detail="A run is already in progress")
    asyncio.create_task(asyncio.to_thread(_run_full_pipeline_bg, run.id))
    return _run_to_summary(run)


@router.post("/sync")
async def sync(db: Session = Depends(get_db)):
    """Kick off a full ingestion + LLM pipeline asynchronously.

    Returns immediately with {run_id, status: "running"}.
    Poll GET /ingestion/runs/{run_id} for live status.
    Returns 409 if a run is already in progress.
    """
    from app.jobs.ingestion_job import _run_full_pipeline_bg, run_full_pipeline_async
    from app.jobs.run_tracker import claim_run, has_active_run
    from app.models.ingestion_run import IngestionRun, RunStatus, TriggeredBy

    existing = db.query(IngestionRun).filter(IngestionRun.status == RunStatus.running).first()
    if has_active_run() or existing:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    run = run_full_pipeline_async(db, triggered_by=TriggeredBy.manual)
    if not claim_run(run.id):
        raise HTTPException(status_code=409, detail="A run is already in progress")
    asyncio.create_task(asyncio.to_thread(_run_full_pipeline_bg, run.id))
    return {"run_id": run.id, "status": "running"}


@router.delete("/runs/{run_id}")
def delete_run(run_id: int, db: Session = Depends(get_db)):
    from app.services.ingestion_service import IngestionService

    deleted = IngestionService(db).delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Proposal endpoints (per-run)
# ---------------------------------------------------------------------------


def _proposal_to_dict(p) -> dict:
    return {
        "id": p.id,
        "proposal_type": p.proposal_type.value,
        "status": p.status.value,
        "task_id": p.task_id,
        "proposed_title": p.proposed_title,
        "proposed_description": p.proposed_description,
        "proposed_status": p.proposed_status.value if p.proposed_status else None,
        "proposed_due_at": p.proposed_due_at.isoformat() if p.proposed_due_at else None,
        "proposed_external_ref": p.proposed_external_ref,
        "reason_summary": p.reason_summary,
        "created_at": p.created_at.isoformat(),
    }


@router.get("/runs/{run_id}/proposals")
def get_run_proposals(run_id: int, db: Session = Depends(get_db)):
    """Return all proposals associated with a run's batches."""
    from app.models.task_proposal import TaskProposal
    from app.services.ingestion_service import IngestionService

    run = IngestionService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    batch_ids = [b.id for b in run.batches]
    if not batch_ids:
        return []

    proposals = db.query(TaskProposal).filter(TaskProposal.ingestion_batch_id.in_(batch_ids)).all()
    return [_proposal_to_dict(p) for p in proposals]


@router.post("/runs/{run_id}/propose")
async def propose_tasks(run_id: int, db: Session = Depends(get_db)):
    """Kick off LLM proposal generation for a run asynchronously.

    Returns immediately with {run_id, status: "running"}.
    Poll GET /ingestion/runs/{run_id}/proposals for results.
    Returns 409 if a propose job is already running for this run.
    """
    from app.jobs.propose_job import run_propose_bg
    from app.jobs.run_tracker import claim_propose
    from app.services.ingestion_service import IngestionService

    run = IngestionService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if not claim_propose(run_id):
        raise HTTPException(status_code=409, detail="Proposal already in progress for this run")

    asyncio.create_task(asyncio.to_thread(run_propose_bg, run_id))
    return {"run_id": run_id, "status": "running"}


# ---------------------------------------------------------------------------
# Prompt & LLM preview endpoints
# ---------------------------------------------------------------------------


@router.get("/runs/{run_id}/prompt-preview")
def prompt_preview(run_id: int, db: Session = Depends(get_db)):
    import tiktoken

    from app.llm.prompt_builder import build_proposal_prompt
    from app.models.experience import Experience
    from app.models.task import Task, TaskStatus
    from app.services.ingestion_service import IngestionService

    run = IngestionService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    active_tasks = (
        db.query(Task).filter(Task.status.notin_([TaskStatus.done, TaskStatus.cancelled])).all()
    )
    active_experiences = db.query(Experience).filter(Experience.active.is_(True)).all()

    system_prompt, user_prompt = build_proposal_prompt(run, db, active_tasks, active_experiences)

    enc = tiktoken.encoding_for_model("gpt-4o")
    token_count = len(enc.encode(system_prompt + user_prompt))

    return {
        "run_id": run.id,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "token_count": token_count,
    }


@router.post("/runs/{run_id}/llm-preview")
def llm_preview(run_id: int, db: Session = Depends(get_db)):
    from app.llm.client import LLMClient, LLMError
    from app.llm.prompt_builder import build_proposal_prompt
    from app.models.experience import Experience
    from app.models.task import Task, TaskStatus
    from app.models.task_proposal import ProposalCreatedBy, ProposalType, TaskProposal
    from app.services.ingestion_service import IngestionService

    run = IngestionService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    active_tasks = (
        db.query(Task).filter(Task.status.notin_([TaskStatus.done, TaskStatus.cancelled])).all()
    )
    active_experiences = db.query(Experience).filter(Experience.active.is_(True)).all()
    experience_name_to_id = {exp.folder_path: exp.id for exp in active_experiences}

    system_prompt, user_prompt = build_proposal_prompt(run, db, active_tasks, active_experiences)

    try:
        t0 = time.monotonic()
        result = LLMClient().generate_proposals_with_meta(system_prompt, user_prompt)
        duration_ms = round((time.monotonic() - t0) * 1000)
    except LLMError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Persist proposals to the database so the Proposals page can show them.
    # Use the first batch of the run as the ingestion_batch_id reference (best effort).
    batch_id = run.batches[0].id if run.batches else None
    now = datetime.now(timezone.utc)
    saved = []
    for p in result.batch.proposals:
        due_at = None
        if p.proposed_due_at:
            from datetime import datetime as dt

            try:
                due_at = dt.fromisoformat(p.proposed_due_at.replace("Z", "+00:00"))
            except ValueError:
                pass
        experience_id = (
            experience_name_to_id.get(p.proposed_experience_name)
            if p.proposed_experience_name
            else None
        )
        proposal = TaskProposal(
            proposal_type=ProposalType(p.proposal_type),
            status="pending",
            task_id=p.task_id,
            proposed_title=p.proposed_title,
            proposed_description=p.proposed_description,
            proposed_status=p.proposed_status,
            proposed_experience_id=experience_id,
            proposed_due_at=due_at,
            proposed_external_ref=p.proposed_external_ref,
            reason_summary=p.reason_summary,
            created_at=now,
            created_by=ProposalCreatedBy.ai,
            ingestion_batch_id=batch_id,
        )
        db.add(proposal)
        saved.append(proposal)
    db.commit()

    return {
        "run_id": run.id,
        "model": result.model,
        "proposals": [p.model_dump() for p in result.batch.proposals],
        "content": result.content,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "duration_ms": duration_ms,
        "saved_count": len(saved),
    }
