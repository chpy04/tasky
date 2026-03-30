"""Ingestion orchestration service.

Coordinates an ingestion run: creates the run record, calls connectors,
persists batches, then triggers LLM context assembly and proposal
generation per batch.

Responsibilities:
- create IngestionRun
- call registered connectors; persist raw payloads as IngestionBatches
- for each pending batch: assemble context → call LLM → persist proposals
- update run/batch status on success or failure

TODO: implement retry and concurrency strategy (tech spec §18 TODO)
TODO: implement per-source acquisition details (tech spec §19 TODO)
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.ingestion_batch import BatchStatus, IngestionBatch, SourceType
from app.models.ingestion_run import IngestionRun, RunStatus, TriggeredBy
from app.models.task_proposal import TaskProposal

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(
        self,
        range_start: datetime,
        range_end: datetime,
        triggered_by: TriggeredBy = TriggeredBy.manual,
    ) -> IngestionRun:
        """Create an IngestionRun record with status=running and flush (no connectors).

        Returns the run object so the caller can use run.id to dispatch a
        background job.
        """
        run = IngestionRun(
            status=RunStatus.running,
            range_start=range_start,
            range_end=range_end,
            started_at=datetime.now(timezone.utc),
            triggered_by=triggered_by,
        )
        self.db.add(run)
        self.db.flush()
        self.db.commit()
        return run

    def trigger_run(
        self,
        range_start: datetime,
        range_end: datetime,
        triggered_by: TriggeredBy = TriggeredBy.manual,
    ) -> IngestionRun:
        """Create a run record and immediately run connectors (synchronous path).

        Used by the scheduler's synchronous background thread.
        """
        run = self.create_run(range_start, range_end, triggered_by=triggered_by)
        self._run_connectors(run, set_final_status=True)
        return run

    def _run_connectors(self, run: IngestionRun, *, set_final_status: bool = True) -> None:
        connector_factories = [
            (
                "github",
                lambda: __import__(
                    "app.connectors.github", fromlist=["GitHubConnector"]
                ).GitHubConnector(),
            ),
            (
                "gmail",
                lambda: __import__(
                    "app.connectors.gmail", fromlist=["GmailConnector"]
                ).GmailConnector(),
            ),
            (
                "slack",
                lambda: __import__(
                    "app.connectors.slack", fromlist=["SlackConnector"]
                ).SlackConnector(),
            ),
            (
                "canvas",
                lambda: __import__(
                    "app.connectors.canvas", fromlist=["CanvasConnector"]
                ).CanvasConnector(),
            ),
        ]

        source_type_map = {
            "github": SourceType.github,
            "gmail": SourceType.email,
            "slack": SourceType.slack,
            "canvas": SourceType.canvas,
        }

        errors: list[str] = []

        for name, factory in connector_factories:
            try:
                try:
                    connector = factory()
                except ValueError:
                    logger.info("Connector %s is not configured, skipping", name)
                    continue

                result = connector.fetch(since=run.range_start, until=run.range_end)

                for payload_dict in result.payload:
                    batch = IngestionBatch(
                        ingestion_run_id=run.id,
                        source_type=source_type_map[name],
                        raw_payload=payload_dict["payload"],
                        created_at=datetime.now(timezone.utc),
                        status=BatchStatus.processed if result.success else BatchStatus.failed,
                        item_count=result.item_count,
                        api_calls=result.api_calls,
                        duration_ms=result.duration_ms,
                        llm_cost=result.llm_cost,
                        found_new_content=result.found_new_content,
                        success=result.success,
                        connector_metadata=json.dumps(payload_dict.get("metadata", {})),
                    )
                    self.db.add(batch)

            except Exception as exc:
                error_msg = f"{name}: {exc}"
                logger.error("Connector %s failed: %s", name, exc)
                errors.append(error_msg)
                continue

        self.db.flush()

        if set_final_status:
            run.finished_at = datetime.now(timezone.utc)

            if errors:
                batch_count = (
                    self.db.query(IngestionBatch)
                    .filter(IngestionBatch.ingestion_run_id == run.id)
                    .count()
                )
                if batch_count == 0:
                    run.status = RunStatus.failed
                    run.error_summary = "; ".join(errors)
                else:
                    run.status = RunStatus.completed
            else:
                run.status = RunStatus.completed

        self.db.commit()

    def reset_run_for_rerun(self, run_id: int) -> IngestionRun | None:
        """Delete existing batches and reset the run record to status=running.

        Returns the reset run object (no connectors run yet). Returns None if
        the run does not exist.
        """
        run = self.db.get(IngestionRun, run_id)
        if not run:
            return None

        batches = (
            self.db.query(IngestionBatch).filter(IngestionBatch.ingestion_run_id == run.id).all()
        )
        batch_ids = [b.id for b in batches]
        if batch_ids:
            self.db.query(TaskProposal).filter(
                TaskProposal.ingestion_batch_id.in_(batch_ids)
            ).update({"ingestion_batch_id": None}, synchronize_session="fetch")

            for batch in batches:
                self.db.delete(batch)
            self.db.flush()

        run.status = RunStatus.running
        run.started_at = datetime.now(timezone.utc)
        run.finished_at = None
        run.error_summary = None
        self.db.commit()
        return run

    def rerun(self, run_id: int) -> IngestionRun | None:
        """Reset a run and immediately run connectors (synchronous path)."""
        run = self.reset_run_for_rerun(run_id)
        if not run:
            return None
        self._run_connectors(run)
        return run

    def delete_run(self, run_id: int) -> bool:
        """Hard-delete a run and all its batches. Returns False if not found."""
        run = self.db.get(IngestionRun, run_id)
        if not run:
            return False

        batches = (
            self.db.query(IngestionBatch).filter(IngestionBatch.ingestion_run_id == run.id).all()
        )
        batch_ids = [b.id for b in batches]
        if batch_ids:
            self.db.query(TaskProposal).filter(
                TaskProposal.ingestion_batch_id.in_(batch_ids)
            ).update({"ingestion_batch_id": None}, synchronize_session="fetch")

            for batch in batches:
                self.db.delete(batch)

        self.db.delete(run)
        self.db.commit()
        return True

    def list_runs(self) -> list[IngestionRun]:
        return (
            self.db.query(IngestionRun)
            .options(joinedload(IngestionRun.batches))
            .order_by(IngestionRun.started_at.desc())
            .all()
        )

    def get_run(self, run_id: int) -> IngestionRun | None:
        return (
            self.db.query(IngestionRun)
            .options(joinedload(IngestionRun.batches))
            .filter(IngestionRun.id == run_id)
            .first()
        )
