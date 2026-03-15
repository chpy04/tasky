"""Ingestion job entrypoint.

Supports both manual triggers (called from the API) and scheduled runs.
For the MVP this is a simple synchronous function; scheduling can be
wired to a cron trigger or in-process scheduler later.

TODO: implement scheduling mechanism (tech spec §18 TODO)
TODO: implement graceful failure isolation per connector
TODO: implement rerun support for failed batches without destroying history
"""
from sqlalchemy.orm import Session

from app.services.ingestion_service import IngestionService


def run_ingestion(db: Session, source_types: list[str] | None = None) -> int:
    """Run a full ingestion cycle.

    Args:
        db: database session
        source_types: optional list of source types to run; defaults to all configured

    Returns:
        The ID of the created IngestionRun.

    TODO: implement using IngestionService
    """
    service = IngestionService(db)
    raise NotImplementedError
