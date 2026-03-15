"""Canvas LMS connector.

Fetches assignment data, announcements, and course updates from Canvas.

TODO: implement authentication (API key from settings)
TODO: define which courses to track
TODO: implement incremental sync (check for new/updated assignments)
TODO: map Canvas assignment due dates to task due_at field
"""

import json
import time
from datetime import datetime, timezone

from app.connectors.base import BaseConnector, ConnectorResult

_MOCK_ITEMS = [
    {
        "course": "CS 4820 — Algorithm Design",
        "type": "assignment",
        "title": "Problem Set 6: Network Flow",
        "due_at": "2026-03-18T23:59:00Z",
        "points": 100,
        "submitted": False,
        "updated_at": "2026-03-14T08:00:00Z",
    },
    {
        "course": "MATH 3110 — Real Analysis",
        "type": "assignment",
        "title": "Homework 8: Uniform Convergence",
        "due_at": "2026-03-17T23:59:00Z",
        "points": 50,
        "submitted": False,
        "updated_at": "2026-03-13T10:00:00Z",
    },
    {
        "course": "CS 4820 — Algorithm Design",
        "type": "announcement",
        "title": "Office hours moved to Thursday 4–6pm",
        "posted_at": "2026-03-13T10:00:00Z",
        "updated_at": "2026-03-13T10:00:00Z",
    },
    {
        "course": "PHIL 2200 — Ethics",
        "type": "assignment",
        "title": "Reading Response 4: Mill on Utility",
        "due_at": "2026-03-16T23:59:00Z",
        "points": 20,
        "submitted": True,
        "updated_at": "2026-03-12T09:00:00Z",
    },
]


class CanvasConnector(BaseConnector):
    """Fetches course and assignment data from Canvas LMS."""

    def fetch(self, since: datetime) -> ConnectorResult:
        # TODO: call Canvas REST API using settings.canvas_api_key and settings.canvas_base_url
        # TODO: fetch assignments/announcements updated since `since`
        # TODO: replace mock below with real Canvas API calls
        start = time.monotonic()
        fetched_at = datetime.now(timezone.utc).isoformat()
        since_iso = since.isoformat()

        items = [i for i in _MOCK_ITEMS if i["updated_at"] >= since_iso]

        return ConnectorResult(
            success=True,
            found_new_content=len(items) > 0,
            item_count=len(items),
            api_calls=0,
            llm_cost=0.0,
            duration_ms=(time.monotonic() - start) * 1000,
            payload=[
                {
                    "source_type": "canvas",
                    "payload": json.dumps(items, default=str),
                    "metadata": {
                        "fetched_at": fetched_at,
                        "since": since_iso,
                        "count": len(items),
                        "kind": "assignments",
                    },
                }
            ]
            if items
            else [],
        )
