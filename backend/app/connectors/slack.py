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
  - One conversations.history pass per member channel (bounded by `since`):
      4. broadcast_mention — messages containing <!channel> or <!here>
      5. participated_thread — new replies in threads whose roots also fall
         within [since, until]. Thread roots older than `since` are not
         back-filled; they were captured in a prior poll cycle.
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
from zoneinfo import ZoneInfo

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
        self._member_channel_ids: set[str] = set()  # channels the user is a member of
        self._member_channel_types: dict[str, str] = {}  # channel_id → "im"|"mpim"|"channel"

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

        Also populates _member_channel_ids and _member_channel_types so the
        broadcast and thread-participation passes know which channels to scan.
        Called once at the start of fetch().
        """
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
                    name = (
                        ch.get("name")
                        or ch.get("user")  # im: other user's id (best we can do without extra call)
                        or ch_id
                    )
                    self._channel_cache[ch_id] = name

                    # Track membership for the history scan passes.
                    # DMs/MPIMs returned by conversations.list are always joined.
                    # Public/private channels need the is_member flag.
                    is_dm = channel_type == "mpim,im"
                    if is_dm or ch.get("is_member"):
                        self._member_channel_ids.add(ch_id)
                        if ch.get("is_im"):
                            ch_kind = "im"
                        elif ch.get("is_mpim"):
                            ch_kind = "mpim"
                        else:
                            ch_kind = "channel"
                        self._member_channel_types[ch_id] = ch_kind

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

    def _fetch_channel_history(
        self,
        channel_id: str,
        oldest_ts: str,
        latest_ts: str | None = None,
    ) -> list[dict]:
        """Fetch top-level messages in a channel between the given Unix timestamps.

        Returns an empty list (rather than raising) if the channel is
        inaccessible, so one bad channel never aborts the whole run.
        """
        messages: list[dict] = []
        cursor = None
        while True:
            params: dict[str, str] = {
                "channel": channel_id,
                "oldest": oldest_ts,
                "limit": "200",
            }
            if latest_ts:
                params["latest"] = latest_ts
            if cursor:
                params["cursor"] = cursor
            try:
                data = self._request("conversations.history", params)
            except Exception:
                break
            messages.extend(data.get("messages", []))
            if not data.get("has_more"):
                break
            meta = data.get("response_metadata", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break
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

    @staticmethod
    def _ts_to_readable(ts: str) -> str:
        """Convert a Slack epoch timestamp to a human-readable EST datetime (minutes precision)."""
        try:
            dt = datetime.fromtimestamp(float(ts), tz=ZoneInfo("America/New_York"))
            return dt.strftime("%Y-%m-%d %H:%M %Z")
        except (ValueError, TypeError):
            return ts

    def _prune_message(
        self,
        msg: dict,
        match_reason: str,
        channel_id: str | None = None,
    ) -> dict:
        """Extract the fields relevant for LLM processing from a message.

        Works for both search.messages results (which embed a `channel` sub-dict)
        and conversations.history results (which have no `channel` field — pass
        `channel_id` explicitly in that case).
        """
        channel_info = msg.get("channel", {})
        ch_id = channel_id or channel_info.get("id", "")
        channel_name = channel_info.get("name") or self._resolve_channel(ch_id)
        # search.messages embeds a `username` field on every match — seed the
        # user cache from it so _resolve_user skips the users.info API call.
        user_id = msg.get("user", "")
        if user_id and msg.get("username") and user_id not in self._user_cache:
            self._user_cache[user_id] = msg["username"]
        return {
            "channel": channel_name,
            "channel_id": ch_id,
            "author": self._resolve_user(user_id),
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
        }

    def _consolidate_threads(self, items: list[dict]) -> list[dict]:
        """Collapse multiple items from the same Slack thread into a single item.

        Any item with `thread_ts` set belongs to a thread. When the same thread
        is captured by multiple passes (search + channel history, or multiple
        replies each emitted as separate items), we keep exactly one representative
        per thread — preferring whichever item already has the full thread array
        attached — so no thread appears more than once in the output.
        """
        standalone: list[dict] = []
        thread_groups: dict[str, list[dict]] = {}

        for item in items:
            thread_ts = item.get("thread_ts")
            ch_id = item.get("channel_id", "")
            if thread_ts and ch_id:
                key = f"{ch_id}:{thread_ts}"
                thread_groups.setdefault(key, []).append(item)
            else:
                standalone.append(item)

        result = list(standalone)
        for group in thread_groups.values():
            # Prefer an item that already has the full thread array attached.
            with_thread = [i for i in group if "thread" in i]
            result.append(with_thread[0] if with_thread else group[0])

        return result

    def _postprocess_items(self, items: list[dict]) -> list[dict]:
        """Sort by timestamp (ascending) and strip fields not needed by the LLM."""
        items.sort(key=lambda x: float(x.get("ts", 0) or 0))
        result = []
        for item in items:
            cleaned: dict = {
                "channel": item["channel"],
                "author": item["author"],
                "text": item["text"],
                "ts": self._ts_to_readable(item.get("ts", "")),
                "match_reason": item["match_reason"],
            }
            if "thread" in item:
                cleaned["thread"] = item["thread"]
            result.append(cleaned)
        return result

    def _attach_thread_if_participant(
        self,
        item: dict,
        user_id: str,
        fetched_threads: set[str],
        covered_keys: set[str],
    ) -> None:
        """Fetch the thread for `item` and attach it if the user is a participant.

        Mutates `item` in place by adding a "thread" key. Updates `fetched_threads`
        to prevent duplicate fetches across callers. Populates `covered_keys` with
        every "channel_id:ts" seen in the thread so standalone duplicates can be
        filtered out later.
        """
        channel_id = item.get("channel_id", "")
        thread_ts = item.get("thread_ts")
        if not (thread_ts and channel_id):
            return
        thread_key = f"{channel_id}:{thread_ts}"
        if thread_key in fetched_threads:
            return
        fetched_threads.add(thread_key)
        raw_thread = self._fetch_thread(channel_id, thread_ts)
        for m in raw_thread:
            covered_keys.add(f"{channel_id}:{m.get('ts', '')}")
        if user_id in {m.get("user") for m in raw_thread}:
            item_ts = item.get("ts", "")
            item["thread"] = [
                self._prune_thread_msg(m) for m in raw_thread if m.get("ts") != item_ts
            ]

    # ── Public interface ──────────────────────────────────────────────────

    def fetch(self, since: datetime, until: datetime | None = None) -> ConnectorResult:
        """Fetch Slack activity relevant to the user since the given datetime.

        Covers: @mentions, @channel/@here broadcasts in member channels, keyword
        alerts, messages sent by the user (including DMs), and new replies in
        threads the user has participated in. Threads are fetched in full when
        the user is a participant (sent a reply or is the thread root author).

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

        # Bulk-load channel names and membership once.
        self._prefetch_channels()

        # search.messages only supports date-level `after:` filtering.
        oldest_date = since.strftime("%Y-%m-%d")
        newest_date = until.strftime("%Y-%m-%d") if until is not None else None

        since_ts = since.timestamp()
        until_ts = until.timestamp() if until is not None else None
        latest_ts_str = str(until_ts) if until_ts is not None else None

        # ── Search passes ────────────────────────────────────────────────
        raw_items: list[tuple[dict, str]] = []

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
        raw_items = [(m, r) for (m, r) in raw_items if float(m.get("ts", 0)) > since_ts]
        if until_ts is not None:
            raw_items = [(m, r) for (m, r) in raw_items if float(m.get("ts", 0)) < until_ts]

        # ── Deduplicate search results ────────────────────────────────────
        seen: set[str] = set()  # "channel_id:ts"
        deduped: list[tuple[dict, str]] = []
        for msg, reason in raw_items:
            key = f"{msg.get('channel', {}).get('id', '')}:{msg.get('ts', '')}"
            if key not in seen:
                seen.add(key)
                deduped.append((msg, reason))

        # ── Build items from search results ──────────────────────────────
        items: list[dict] = []
        fetched_threads: set[str] = set()
        covered_keys: set[str] = set()  # "channel_id:ts" for every msg inside a fetched thread

        for msg, reason in deduped:
            item = self._prune_message(msg, reason)
            self._attach_thread_if_participant(item, user_id, fetched_threads, covered_keys)
            items.append(item)

        # ── Channel history pass ─────────────────────────────────────────
        # Scan every member channel for (a) @channel/@here broadcasts and
        # (b) thread roots with new reply activity. Bounded by since_ts so
        # we only fetch history within the sync window — one call per channel
        # (or one per 200 messages) rather than 30 days of back-fill.
        oldest_ts_str = str(since_ts)

        for channel_id in self._member_channel_ids:
            is_dm = self._member_channel_types.get(channel_id) in ("im", "mpim")

            try:
                history = self._fetch_channel_history(channel_id, oldest_ts_str, latest_ts_str)
            except Exception:
                continue

            for msg in history:
                text = msg.get("text", "")
                msg_ts_str = msg.get("ts", "")
                msg_ts = float(msg_ts_str) if msg_ts_str else 0.0
                key = f"{channel_id}:{msg_ts_str}"

                # ── @channel / @here broadcasts (non-DM, within sync window) ──
                if (
                    not is_dm
                    and msg_ts > since_ts
                    and ("<!channel>" in text or "<!here>" in text)
                    and key not in seen
                ):
                    seen.add(key)
                    item = self._prune_message(msg, "broadcast_mention", channel_id=channel_id)
                    self._attach_thread_if_participant(item, user_id, fetched_threads, covered_keys)
                    items.append(item)

                # ── Thread roots with new reply activity ──────────────────────
                # conversations.history returns only top-level messages, so we
                # look for roots whose latest_reply falls inside the sync window.
                if not (msg.get("reply_count", 0) > 0 and msg.get("latest_reply")):
                    continue
                latest_reply = float(msg["latest_reply"])
                if latest_reply <= since_ts:
                    continue
                if until_ts is not None and latest_reply >= until_ts:
                    continue

                thread_ts = msg_ts_str
                thread_key = f"{channel_id}:{thread_ts}"
                if thread_key in fetched_threads:
                    continue
                fetched_threads.add(thread_key)

                raw_thread = self._fetch_thread(channel_id, thread_ts)
                if user_id not in {m.get("user") for m in raw_thread}:
                    continue  # user never participated in this thread

                # Mark every message in this thread so standalone duplicates
                # captured by the search passes are filtered out later.
                for m in raw_thread:
                    covered_keys.add(f"{channel_id}:{m.get('ts', '')}")

                # Emit ONE item for the entire thread using the root message.
                root = raw_thread[0]
                root_ts = root.get("ts", "")
                root_key = f"{channel_id}:{root_ts}"
                seen.add(root_key)
                thread_item = self._prune_message(
                    root, "participated_thread", channel_id=channel_id
                )
                # Exclude the root itself from the thread array since it is
                # already represented by the top-level item.
                thread_item["thread"] = [
                    self._prune_thread_msg(m) for m in raw_thread if m.get("ts") != root_ts
                ]
                items.append(thread_item)

        if not items:
            return ConnectorResult(
                success=True,
                found_new_content=False,
                item_count=0,
                api_calls=self._api_calls,
                llm_cost=0.0,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Drop standalone items whose message is already represented inside a
        # thread array, unless the item itself carries the thread context.
        items = [
            i
            for i in items
            if "thread" in i or f"{i.get('channel_id', '')}:{i.get('ts', '')}" not in covered_keys
        ]
        items = self._consolidate_threads(items)
        items = self._postprocess_items(items)

        query_types = (
            ["mention", "sent"]
            + [f"keyword:{k}" for k in keywords]
            + ["broadcast_mention", "participated_thread"]
        )

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
