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
from sqlalchemy.orm import Session


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def trigger_manual_run(self, source_types: list[str] | None = None):
        # TODO: create IngestionRun(triggered_by=manual); run connectors; process batches
        raise NotImplementedError

    def process_batch(self, batch_id: int):
        # TODO: assemble context from batch + active tasks + experience markdown; call LLM; persist proposals
        raise NotImplementedError
