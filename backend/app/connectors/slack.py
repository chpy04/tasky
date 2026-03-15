"""Slack connector.

Fetches messages from configured channels and DMs that may contain
actionable information or project updates.

TODO: implement authentication (bot token from settings)
TODO: define which channels/DMs to monitor (config)
TODO: implement incremental sync (cursor-based pagination)
TODO: filter out noise (bot messages, reactions-only, etc.)
"""
import json
import time
from datetime import datetime, timezone

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorResult

_MOCK_MESSAGES = [
    {
        "channel": "#eng-backend",
        "user": "alice",
        "text": "The staging deploy failed on the db migration step — @chrispyle can you take a look?",
        "ts": "2026-03-14T20:00:00Z",
        "thread_replies": 2,
    },
    {
        "channel": "#eng-backend",
        "user": "bob",
        "text": "PR #204 is ready for review — adds rate limiting to the ingestion endpoint.",
        "ts": "2026-03-14T17:00:00Z",
        "thread_replies": 0,
    },
    {
        "channel": "#general",
        "user": "carol",
        "text": "Team lunch Thursday at noon at the usual spot. Let me know if you can make it.",
        "ts": "2026-03-13T12:00:00Z",
        "thread_replies": 5,
    },
    {
        "channel": "#eng-frontend",
        "user": "dave",
        "text": "Heads up: the design review for the proposals UI is moved to Friday 3pm.",
        "ts": "2026-03-12T11:30:00Z",
        "thread_replies": 1,
    },
]


class SlackConnector(BaseConnector):
    """Fetches Slack messages from configured channels."""

    def fetch(self, since: datetime) -> ConnectorResult:
        # TODO: authenticate using settings.slack_bot_token
        # TODO: fetch new messages from configured channel list since `since`
        # TODO: replace mock below with real Slack API calls
        start = time.monotonic()
        fetched_at = datetime.now(timezone.utc).isoformat()
        since_iso = since.isoformat()

        messages = [
            m for m in _MOCK_MESSAGES
            if m["ts"] >= since_iso
        ]

        return ConnectorResult(
            success=True,
            found_new_content=len(messages) > 0,
            item_count=len(messages),
            api_calls=0,
            llm_cost=0.0,
            duration_ms=(time.monotonic() - start) * 1000,
            payload=[
                {
                    "source_type": "slack",
                    "payload": json.dumps(messages, default=str),
                    "metadata": {
                        "fetched_at": fetched_at,
                        "since": since_iso,
                        "count": len(messages),
                        "kind": "messages",
                    },
                }
            ] if messages else [],
        )
