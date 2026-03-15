"""Gmail connector.

Fetches recent emails that may contain actionable information:
assignment notifications, project updates, meeting requests, etc.

TODO: implement OAuth2 flow (client_id/secret from settings)
TODO: define label/query filters to avoid ingesting noise
TODO: implement incremental sync via historyId or lastFetched timestamp
TODO: strip or truncate email bodies before batch storage
"""

import json
import time
from datetime import datetime, timezone

from app.connectors.base import BaseConnector, ConnectorResult

_MOCK_EMAILS = [
    {
        "id": "18e4a1c2d3f00001",
        "subject": "Re: Q2 planning doc — timeline update",
        "from": "alice@example.com",
        "snippet": "Can you review the updated timeline before Thursday's sync? I've flagged the milestones that shifted.",
        "received_at": "2026-03-14T18:30:00Z",
        "labels": ["INBOX", "UNREAD"],
    },
    {
        "id": "18e4a1c2d3f00002",
        "subject": "Project kickoff — action items",
        "from": "bob@example.com",
        "snippet": "Following up on today's kickoff. You're down for the API spec draft by EOW.",
        "received_at": "2026-03-13T09:15:00Z",
        "labels": ["INBOX"],
    },
    {
        "id": "18e4a1c2d3f00003",
        "subject": "Invoice #1042 needs your approval",
        "from": "finance@example.com",
        "snippet": "Please approve the attached invoice by EOD Friday or it will be delayed to next cycle.",
        "received_at": "2026-03-12T14:00:00Z",
        "labels": ["INBOX", "UNREAD"],
    },
]


class GmailConnector(BaseConnector):
    """Fetches recent actionable emails via the Gmail API."""

    def fetch(self, since: datetime) -> ConnectorResult:
        # TODO: authenticate with OAuth2 using settings.gmail_client_*
        # TODO: query inbox with configured filters since `since`
        # TODO: replace mock below with real Gmail API calls
        start = time.monotonic()
        fetched_at = datetime.now(timezone.utc).isoformat()
        since_iso = since.isoformat()

        emails = [e for e in _MOCK_EMAILS if e["received_at"] >= since_iso]

        return ConnectorResult(
            success=True,
            found_new_content=len(emails) > 0,
            item_count=len(emails),
            api_calls=0,
            llm_cost=0.0,
            duration_ms=(time.monotonic() - start) * 1000,
            payload=[
                {
                    "source_type": "gmail",
                    "payload": json.dumps(emails, default=str),
                    "metadata": {
                        "fetched_at": fetched_at,
                        "since": since_iso,
                        "count": len(emails),
                        "kind": "emails",
                    },
                }
            ]
            if emails
            else [],
        )
