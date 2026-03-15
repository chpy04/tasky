"""Connector base class and result type.

All connectors subclass BaseConnector and implement fetch(since) to return a
ConnectorResult. The ingestion service calls fetch() on each registered
connector and persists the result as IngestionBatch records.

ConnectorResult fields:
  - success:    bool           whether the fetch completed without error
  - item_count: int            number of logical items collected (definition
                               varies per source, e.g. notifications, emails)
  - api_calls:  int            number of external HTTP calls made (0 for
                               LLM-based scrapers that don't call an API)
  - llm_cost:   float          USD cost of any LLM calls (0.0 for deterministic
                               API sources)
  - payload:    list[dict]     batch dicts ready to be stored as IngestionBatch
                               records; each dict must have 'source_type',
                               'payload', and 'metadata' keys

Connectors must not write to tasks or proposals directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConnectorResult:
    success: bool
    found_new_content: bool
    item_count: int
    api_calls: int
    llm_cost: float
    duration_ms: float
    payload: list[dict] = field(default_factory=list)


class BaseConnector(ABC):
    @abstractmethod
    def fetch(self, since: datetime, until: datetime | None = None) -> ConnectorResult:
        """Fetch data from the external source since the given UTC datetime.

        Args:
            since: Only return items updated/created after this timestamp (UTC).
            until: If set, exclude items updated/created after this timestamp
                   (UTC). Useful for bounding a fetch to a specific time window.

        Returns:
            A ConnectorResult with the fetched batch dicts in payload.
        """
        ...
