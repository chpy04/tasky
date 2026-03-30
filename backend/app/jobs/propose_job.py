"""Background job: LLM proposal generation for an existing IngestionRun.

`run_propose_bg(run_id)` is dispatched via `asyncio.create_task(asyncio.to_thread(...))`
from the `POST /ingestion/runs/{id}/propose` endpoint. It opens its own DB
session, calls the LLM, persists proposals, and releases the propose tracker
slot when done.
"""

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def run_propose_bg(run_id: int) -> None:
    """Run LLM proposal generation for an existing IngestionRun in the background.

    Opens its own DB session. Updates run.status to failed on error.
    Always calls release_propose(run_id) in a finally block.
    """
    from app.db.session import SessionLocal
    from app.jobs.run_tracker import release_propose
    from app.llm.client import LLMClient, LLMError
    from app.llm.prompt_builder import build_proposal_prompt
    from app.models.experience import Experience
    from app.models.ingestion_run import IngestionRun, RunStatus
    from app.models.task import Task, TaskStatus
    from app.models.task_proposal import ProposalCreatedBy, ProposalType, TaskProposal

    db = SessionLocal()
    try:
        from sqlalchemy.orm import joinedload

        run = (
            db.query(IngestionRun)
            .options(joinedload(IngestionRun.batches))
            .filter(IngestionRun.id == run_id)
            .first()
        )
        if not run:
            logger.error("Propose job: run %d not found", run_id)
            return

        # Mark run as running so the frontend poller sees the transition.
        # Preserve the original finished_at from the connector phase so the
        # duration display remains accurate after re-proposing.
        original_finished_at = run.finished_at
        run.status = RunStatus.running
        run.finished_at = None
        db.commit()

        batch_ids = [b.id for b in run.batches]

        active_tasks = (
            db.query(Task).filter(Task.status.notin_([TaskStatus.done, TaskStatus.cancelled])).all()
        )
        active_experiences = db.query(Experience).filter(Experience.active.is_(True)).all()
        experience_name_to_id = {exp.folder_path: exp.id for exp in active_experiences}

        system_prompt, user_prompt = build_proposal_prompt(
            run, db, active_tasks, active_experiences
        )

        try:
            t0 = time.monotonic()
            result = LLMClient().generate_proposals_with_meta(system_prompt, user_prompt)
            duration_ms = round((time.monotonic() - t0) * 1000)
        except LLMError as exc:
            logger.error("Propose job LLM call failed for run %d: %s", run_id, exc)
            run.status = RunStatus.failed
            run.error_summary = str(exc)
            db.commit()
            return

        # Delete old proposals only after LLM succeeds, so they're preserved on failure.
        if batch_ids:
            db.query(TaskProposal).filter(TaskProposal.ingestion_batch_id.in_(batch_ids)).delete(
                synchronize_session=False
            )

        batch_id = run.batches[0].id if run.batches else None
        now = datetime.now(timezone.utc)
        saved_count = 0
        for p in result.batch.proposals:
            due_at = None
            if p.proposed_due_at:
                try:
                    due_at = datetime.fromisoformat(p.proposed_due_at.replace("Z", "+00:00"))
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

        run.status = RunStatus.completed
        run.finished_at = original_finished_at or datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Propose job complete: run=%d proposals=%d duration=%dms",
            run_id,
            saved_count,
            duration_ms,
        )
    except Exception as exc:
        logger.error("Propose job unexpected error for run %d: %s", run_id, exc, exc_info=True)
        try:
            run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
            if run and run.status == RunStatus.running:
                run.status = RunStatus.failed
                run.error_summary = f"Unexpected error: {exc}"
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
        release_propose(run_id)
