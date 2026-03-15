"""Slack connector.

Fetches messages relevant to the authenticated user, mirroring the content
visible in Slack's Notifications tab plus messages the user has sent.

Authentication: user OAuth token (xoxp-...) stored in settings.slack_user_token.
Required scopes: search:read, channels:history, groups:history, im:history,
                 mpim:history, users:read, channels:read, groups:read, im:read,
                 mpim:read

Sync strategy:
  - Three search passes via search.messages:
      1. to:@{me}         — direct and channel @mentions
      2. from:@{me}       — messages the user sent (including DMs)
      3. {keyword}        — one pass per keyword in settings.slack_keywords
  - search.messages only supports date-level filtering (after:YYYY-MM-DD), so
    results are post-filtered against the exact `since` timestamp using each
    message's `ts` field.
  - For any message that is part of a thread AND where the authenticated user
    is a participant (sent a message in the thread, or the thread root is
    theirs), the full thread is fetched via conversations.replies.
  - User IDs are resolved to display names with a batched users.info cache.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorResult


class SlackConnector(BaseConnector):
    """Fetches Slack activity relevant to the authenticated user."""

    BASE_URL = "https://slack.com/api"

    def __init__(self) -> None:
        if not settings.slack_user_token:
            raise ValueError("SLACK_USER_TOKEN is not set — add it to your .env file")
        self._token = settings.slack_user_token
        self._api_calls = 0
        self._user_cache: dict[str, str] = {}  # user_id → display name
        self._channel_cache: dict[str, str] = {}  # channel_id → name

    # ── Internal helpers ──────────────────────────────────────────────────

    def _request(self, method: str, params: dict[str, str] | None = None) -> dict:
        url = f"{self.BASE_URL}/{method}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        self._api_calls += 1
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Slack API HTTP error {exc.code} for {method}: {body}") from exc

        if not data.get("ok"):
            raise RuntimeError(f"Slack API error for {method}: {data.get('error', 'unknown')}")
        return data

    def _prefetch_channels(self) -> None:
        """Bulk-load all channel/DM names into _channel_cache via conversations.list.

        Called once at the start of fetch(). Uses pagination but only one API
        call per page — far cheaper than one call per message.
        """
        cursor = None
        for channel_type in ("public_channel,private_channel", "mpim,im"):
            cursor = None
            while True:
                params: dict[str, str] = {
                    "types": channel_type,
                    "exclude_archived": "true",
                    "limit": "200",
                }
                if cursor:
                    params["cursor"] = cursor
                try:
                    data = self._request("conversations.list", params)
                except Exception:
                    break
                for ch in data.get("channels", []):
                    ch_id = ch.get("id", "")
                    if not ch_id:
                        continue
                    # Named channels use "name"; DMs use the other user's name
                    name = (
                        ch.get("name")
                        or ch.get("user")  # im: other user's id (best we can do without extra call)
                        or ch_id
                    )
                    self._channel_cache[ch_id] = name
                meta = data.get("response_metadata", {})
                cursor = meta.get("next_cursor")
                if not cursor:
                    break

    def _resolve_channel(self, channel_id: str) -> str:
        """Return a human-readable name for a channel ID (uses pre-fetched cache)."""
        return self._channel_cache.get(channel_id, channel_id)

    def _resolve_user(self, user_id: str) -> str:
        """Return a human-readable name for a Slack user ID (cached)."""
        if not user_id:
            return user_id
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        try:
            data = self._request("users.info", {"user": user_id})
            profile = data.get("user", {}).get("profile", {})
            name = (
                profile.get("display_name")
                or profile.get("real_name")
                or data["user"].get("name")
                or user_id
            )
        except Exception:
            name = user_id
        self._user_cache[user_id] = name
        return name

    def _search(self, query: str, oldest_date: str, newest_date: str | None = None) -> list[dict]:
        """Run a search.messages query and return all matching messages."""
        messages: list[dict] = []
        page = 1
        search_query = f"{query} after:{oldest_date}"
        if newest_date is not None:
            search_query += f" before:{newest_date}"
        while True:
            data = self._request(
                "search.messages",
                {
                    "query": search_query,
                    "sort": "timestamp",
                    "sort_dir": "asc",
                    "count": "100",
                    "page": str(page),
                },
            )
            matches = data.get("messages", {}).get("matches", [])
            messages.extend(matches)
            paging = data.get("messages", {}).get("paging", {})
            if page >= paging.get("pages", 1):
                break
            page += 1
        return messages

    def _fetch_thread(self, channel_id: str, thread_ts: str) -> list[dict]:
        """Fetch all replies in a thread. Returns raw message dicts."""
        replies: list[dict] = []
        cursor = None
        while True:
            params: dict[str, str] = {
                "channel": channel_id,
                "ts": thread_ts,
                "limit": "200",
            }
            if cursor:
                params["cursor"] = cursor
            try:
                data = self._request("conversations.replies", params)
            except Exception:
                break
            replies.extend(data.get("messages", []))
            meta = data.get("response_metadata", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break
        return replies

    @staticmethod
    def _ts_to_iso(ts: str) -> str:
        """Convert a Slack epoch timestamp string to an ISO-8601 string."""
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
        except (ValueError, TypeError):
            return ts

    def _prune_message(self, msg: dict, match_reason: str) -> dict:
        """Extract the fields relevant for LLM processing from a search match."""
        channel_info = msg.get("channel", {})
        channel_id = channel_info.get("id", "")
        channel_name = channel_info.get("name") or self._resolve_channel(channel_id)
        return {
            "channel": channel_name,
            "channel_id": channel_id,
            "author": self._resolve_user(msg.get("user", "")),
            "text": msg.get("text", ""),
            "ts": msg.get("ts", ""),
            "ts_iso": self._ts_to_iso(msg.get("ts", "")),
            "thread_ts": msg.get("thread_ts"),
            "permalink": msg.get("permalink", ""),
            "match_reason": match_reason,
        }

    def _prune_thread_msg(self, msg: dict) -> dict:
        return {
            "author": self._resolve_user(msg.get("user", "")),
            "text": msg.get("text", ""),
            "ts": msg.get("ts", ""),
            "ts_iso": self._ts_to_iso(msg.get("ts", "")),
        }

    # ── Public interface ──────────────────────────────────────────────────

    def fetch(self, since: datetime, until: datetime | None = None) -> ConnectorResult:
        """Fetch Slack activity relevant to the user since the given datetime.

        Covers: @mentions, channel @mentions, keyword alerts, messages sent by
        the user (including DMs). Threads are fetched in full when the user is
        a participant (sent a reply or is the thread root author).

        Args:
            since: Only return items with a ts after this UTC datetime.
            until: Optional upper bound — only return items before this UTC datetime.

        Returns:
            ConnectorResult with one batch dict in payload containing all items,
            or empty payload when nothing new was found.
        """
        start = time.monotonic()
        fetched_at = datetime.now(timezone.utc).isoformat()
        since_iso = since.isoformat()

        # auth.test gives us the caller's user_id and username.
        auth = self._request("auth.test")
        user_id: str = auth["user_id"]
        username: str = auth["user"]
        self._user_cache[user_id] = username  # seed the cache

        # Bulk-load channel names once so every message can resolve id → name.
        self._prefetch_channels()

        # search.messages only supports date-level `after:` filtering.
        oldest_date = since.strftime("%Y-%m-%d")
        newest_date = until.strftime("%Y-%m-%d") if until is not None else None

        # ── Search passes ────────────────────────────────────────────────
        raw_items: list[tuple[dict, str]] = []  # (message_dict, reason)

        raw_items += [
            (m, "mention") for m in self._search(f"to:<@{user_id}>", oldest_date, newest_date)
        ]
        raw_items += [
            (m, "sent") for m in self._search(f"from:<@{user_id}>", oldest_date, newest_date)
        ]

        keywords = [k.strip() for k in settings.slack_keywords.split(",") if k.strip()]
        for kw in keywords:
            raw_items += [(m, f"keyword:{kw}") for m in self._search(kw, oldest_date, newest_date)]

        # ── Post-filter by exact timestamp ───────────────────────────────
        since_ts = since.timestamp()
        raw_items = [(m, r) for (m, r) in raw_items if float(m.get("ts", 0)) > since_ts]
        if until is not None:
            until_ts = until.timestamp()
            raw_items = [(m, r) for (m, r) in raw_items if float(m.get("ts", 0)) < until_ts]

        # ── Deduplicate (same message can match multiple queries) ─────────
        seen: set[str] = set()
        deduped: list[tuple[dict, str]] = []
        for msg, reason in raw_items:
            key = f"{msg.get('channel', {}).get('id', '')}:{msg.get('ts', '')}"
            if key not in seen:
                seen.add(key)
                deduped.append((msg, reason))

        if not deduped:
            return ConnectorResult(
                success=True,
                found_new_content=False,
                item_count=0,
                api_calls=self._api_calls,
                llm_cost=0.0,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # ── Build output items, fetching threads where user participated ──
        items: list[dict] = []
        fetched_threads: set[str] = set()  # avoid duplicate thread fetches

        for msg, reason in deduped:
            item = self._prune_message(msg, reason)
            channel_id = item["channel_id"]
            thread_ts = item.get("thread_ts")

            if thread_ts and channel_id:
                thread_key = f"{channel_id}:{thread_ts}"
                if thread_key not in fetched_threads:
                    fetched_threads.add(thread_key)
                    raw_thread = self._fetch_thread(channel_id, thread_ts)
                    # Only attach thread when the user is a participant.
                    thread_user_ids = {m.get("user") for m in raw_thread}
                    if user_id in thread_user_ids:
                        item["thread"] = [self._prune_thread_msg(m) for m in raw_thread]

            items.append(item)

        query_types = ["mention", "sent"] + [f"keyword:{k}" for k in keywords]

        return ConnectorResult(
            success=True,
            found_new_content=True,
            item_count=len(items),
            api_calls=self._api_calls,
            llm_cost=0.0,
            duration_ms=(time.monotonic() - start) * 1000,
            payload=[
                {
                    "source_type": "slack",
                    "payload": json.dumps(items, default=str),
                    "metadata": {
                        "fetched_at": fetched_at,
                        "username": username,
                        "since": since_iso,
                        **({"until": until.isoformat()} if until is not None else {}),
                        "count": len(items),
                        "kind": "messages",
                        "query_types": query_types,
                    },
                }
            ],
        )
