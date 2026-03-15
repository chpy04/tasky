"""Gmail connector.

Fetches recent emails that may contain actionable information:
assignment notifications, project updates, meeting requests, etc.

Authentication: OAuth 2.0 via google-auth-oauthlib.
  Run `uv run python scripts/gmail_setup.py` once to authorize.
  Token is stored at data/gmail_token.json (gitignored) and auto-refreshed.

Sync strategy: Gmail's `after:<epoch>` search operator filters by the `since`
  timestamp. Up to _MAX_MESSAGES are fetched per run.

Each message is fetched in full mode. Plain text is extracted from the MIME
tree (stripping HTML if no text/plain part exists) and truncated to
_BODY_CHAR_LIMIT characters to keep payloads LLM-friendly.
"""

import base64
import html as html_lib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorResult

_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_TOKEN_PATH = Path(__file__).resolve().parents[3] / "data" / "gmail_token.json"
_MAX_MESSAGES = 100  # cap per run to keep API call count bounded
_BODY_CHAR_LIMIT = 2000  # truncate bodies to keep payloads LLM-friendly


class GmailConnector(BaseConnector):
    """Fetches recent actionable emails via the Gmail API."""

    def __init__(self) -> None:
        if not settings.gmail_client_id or not settings.gmail_client_secret:
            raise ValueError("GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in .env")
        if not _TOKEN_PATH.exists():
            raise ValueError(
                f"Gmail token not found at {_TOKEN_PATH}. "
                "Run `uv run python scripts/gmail_setup.py` to authorize."
            )
        self._service = self._build_service()
        self._api_calls = 0

    # ── Internal helpers ──────────────────────────────────────────────────

    def _build_service(self):
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _TOKEN_PATH.write_text(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    def _list_messages(self, query: str) -> list[dict]:
        """Return up to _MAX_MESSAGES message stubs matching the query."""
        result = (
            self._service.users()
            .messages()
            .list(userId="me", q=query, maxResults=_MAX_MESSAGES)
            .execute()
        )
        self._api_calls += 1
        return result.get("messages", [])

    def _get_message(self, msg_id: str) -> dict:
        """Fetch the full message payload (headers + body parts)."""
        msg = self._service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        self._api_calls += 1
        return msg

    @staticmethod
    def _header(headers: list[dict], name: str) -> str:
        for h in headers:
            if h["name"].lower() == name.lower():
                return h["value"]
        return ""

    @staticmethod
    def _decode_part(data: str) -> str:
        """Decode a base64url-encoded MIME part."""
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    @staticmethod
    def _strip_html(text: str) -> str:
        """Strip HTML tags and collapse whitespace for plain-text extraction."""
        text = re.sub(r"<[^>]+>", " ", text)
        text = html_lib.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Recursively walk a message payload to extract plain text.

        Prefers text/plain; falls back to stripped text/html. Returns an empty
        string if no readable part is found (e.g. attachment-only messages).
        """
        mime = payload.get("mimeType", "")

        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            return GmailConnector._decode_part(data) if data else ""

        if mime == "text/html":
            data = payload.get("body", {}).get("data", "")
            return GmailConnector._strip_html(GmailConnector._decode_part(data)) if data else ""

        if mime.startswith("multipart/"):
            parts = payload.get("parts", [])
            # Prefer text/plain, then text/html, then recurse into nested parts.
            for preferred in ("text/plain", "text/html"):
                part = next((p for p in parts if p.get("mimeType") == preferred), None)
                if part:
                    return GmailConnector._extract_body(part)
            for part in parts:
                result = GmailConnector._extract_body(part)
                if result:
                    return result

        return ""

    @staticmethod
    def _prune_message(msg: dict) -> dict:
        """Extract only the fields needed for LLM processing."""
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        body = GmailConnector._extract_body(payload).strip()
        return {
            "subject": GmailConnector._header(headers, "Subject"),
            "from": GmailConnector._header(headers, "From"),
            "to": GmailConnector._header(headers, "To"),
            "date": GmailConnector._header(headers, "Date"),
            "snippet": msg.get("snippet", ""),
            "body": body[:_BODY_CHAR_LIMIT] if body else "",
            "labels": msg.get("labelIds", []),
        }

    # ── Public interface ──────────────────────────────────────────────────

    def fetch(self, since: datetime, until: datetime | None = None) -> ConnectorResult:
        """Fetch emails received after `since` (and optionally before `until`).

        Uses Gmail's `after:<epoch>` and `before:<epoch>` query operators for
        server-side filtering. Each matching message is fetched in full mode
        (headers + body). Failures on individual messages are swallowed so one
        bad fetch doesn't drop the entire batch.
        """
        start = time.monotonic()
        fetched_at = datetime.now(timezone.utc).isoformat()
        since_iso = since.isoformat()

        query = f"after:{int(since.timestamp())}"
        if until is not None:
            query += f" before:{int(until.timestamp())}"
        stubs = self._list_messages(query)
        if not stubs:
            return ConnectorResult(
                success=True,
                found_new_content=False,
                item_count=0,
                api_calls=self._api_calls,
                llm_cost=0.0,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        messages = []
        for stub in stubs:
            try:
                msg = self._get_message(stub["id"])
                messages.append(self._prune_message(msg))
            except Exception:
                pass  # enrichment is best-effort; one failure won't drop the batch

        return ConnectorResult(
            success=True,
            found_new_content=True,
            item_count=len(messages),
            api_calls=self._api_calls,
            llm_cost=0.0,
            duration_ms=(time.monotonic() - start) * 1000,
            payload=[
                {
                    "source_type": "gmail",
                    "payload": json.dumps(messages, default=str),
                    "metadata": {
                        "fetched_at": fetched_at,
                        "since": since_iso,
                        **({"until": until.isoformat()} if until is not None else {}),
                        "raw_count": len(stubs),
                        "count": len(messages),
                        "kind": "emails",
                    },
                }
            ],
        )
