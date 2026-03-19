"""Ingestion job: full pipeline (ingest + LLM proposals).

`run_full_pipeline` is the single entry point used by both the scheduled
background task (every 12 h) and the manual sync API endpoint.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun, TriggeredBy
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

_DEFAULT_LOOKBACK_HOURS = 24
_MAX_LOOKBACK_DAYS = 7


def _get_pipeline_range_start(db: Session) -> datetime:
    """Return the range_start for the next pipeline run.

    Uses the range_end of the most recently completed run; falls back to
    24 hours ago if no prior runs exist. Always capped at 7 days ago so
    a long gap never produces an enormous ingestion window.
    """
    floor = datetime.now(timezone.utc) - timedelta(days=_MAX_LOOKBACK_DAYS)

    latest = (
        db.query(IngestionRun)
        .filter(IngestionRun.range_end.isnot(None))
        .order_by(IngestionRun.range_end.desc())
        .first()
    )
    if latest and latest.range_end:
        ts = latest.range_end
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return max(ts, floor)

    return datetime.now(timezone.utc) - timedelta(hours=_DEFAULT_LOOKBACK_HOURS)


def run_full_pipeline(
    db: Session,
    triggered_by: TriggeredBy = TriggeredBy.scheduled,
) -> dict:
    """Run ingestion then LLM proposal generation in one shot.

    Steps:
    1. Determine range_start from the most recent run's range_end.
    2. Run all configured connectors (IngestionService.trigger_run).
    3. Build prompt from run batches and call the LLM.
    4. Persist resulting TaskProposals with status=pending.

    Returns a summary dict: run_id, status, proposals_saved, plus token/timing info.
    """
    from app.llm.client import LLMClient, LLMError
    from app.llm.prompt_builder import build_proposal_prompt
    from app.models.experience import Experience
    from app.models.task import Task, TaskStatus
    from app.models.task_proposal import ProposalCreatedBy, ProposalType, TaskProposal

    range_start = _get_pipeline_range_start(db)
    range_end = datetime.now(timezone.utc)

    logger.info(
        "Full pipeline starting: %s → %s (triggered_by=%s)",
        range_start.isoformat(),
        range_end.isoformat(),
        triggered_by.value,
    )

    svc = IngestionService(db)
    run = svc.trigger_run(range_start, range_end, triggered_by=triggered_by)

    if not run.batches:
        logger.warning("Run %d produced no batches — skipping LLM step", run.id)
        return {"run_id": run.id, "status": run.status.value, "proposals_saved": 0}

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
    except LLMError as exc:
        logger.error("LLM call failed for run %d: %s", run.id, exc)
        return {"run_id": run.id, "status": "llm_failed", "proposals_saved": 0, "error": str(exc)}

    batch_id = run.batches[0].id if run.batches else None
    now = datetime.now(timezone.utc)
    saved_count = 0
    for p in result.batch.proposals:
        due_at = None
        if p.proposed_due_at:
            try:
                from datetime import datetime as dt

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
        saved_count += 1
    db.commit()

    logger.info(
        "Full pipeline complete: run=%d proposals=%d duration=%dms",
        run.id,
        saved_count,
        duration_ms,
    )
    return {
        "run_id": run.id,
        "status": "completed",
        "proposals_saved": saved_count,
        "duration_ms": duration_ms,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }
