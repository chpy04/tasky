"""Connector base protocol.

All connectors implement a single fetch() method that returns a list of
minimally structured dicts. The ingestion service calls fetch() on each
registered connector and persists the results as IngestionBatch records.

Each returned dict should include at minimum:
  - source_type: str       (matches SourceType enum)
  - payload: str           (JSON string or raw text for LLM processing)
  - metadata: dict         (timestamps, source identifiers, links)

Connectors must not write to tasks or proposals directly.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class Connector(Protocol):
    def fetch(self) -> list[dict]:
        """Fetch new data from the external source.

        Returns a list of batch dicts ready to be persisted as
        IngestionBatch records. Each dict must have 'source_type',
        'payload', and 'metadata' keys.
        """
        ...
