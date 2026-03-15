"""GitHub connector.

Fetches notification threads relevant to the authenticated user.

Authentication: personal access token (settings.github_token)
Sync strategy: uses the `since` datetime passed to fetch().
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorResult


class GitHubConnector(BaseConnector):
    """Fetches GitHub notifications for the authenticated user."""

    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        if not settings.github_token:
            raise ValueError("GITHUB_TOKEN is not set — add it to your .env file")
        self._token = settings.github_token
        self._api_calls = 0

    # ── Internal helpers ──────────────────────────────────────────────────

    def _request(self, path: str, params: dict[str, str] | None = None) -> object:
        # Accept either a relative path ("/user") or a full URL for enrichment fetches.
        url = path if path.startswith("https://") else f"{self.BASE_URL}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "tasky-connector/0.1",
            },
        )
        try:
            self._api_calls += 1
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API error {exc.code} for {path}: {body}") from exc

    # ── Public interface ──────────────────────────────────────────────────

    # Notification reasons that are never actionable as tasks.
    EXCLUDED_REASONS: frozenset[str] = frozenset({"ci_activity"})

    @staticmethod
    def _to_html_url(api_url: str | None) -> str | None:
        """Convert a GitHub API resource URL to its human-readable HTML equivalent.

        e.g. https://api.github.com/repos/owner/repo/pulls/1
          -> https://github.com/owner/repo/pull/1
        """
        if not api_url:
            return None
        url = api_url.replace("https://api.github.com/repos/", "https://github.com/")
        url = url.replace("/pulls/", "/pull/")
        url = url.replace("/commits/", "/commit/")
        return url

    @staticmethod
    def _prune_notification(n: dict) -> dict:
        """Strip fields that add no value for LLM processing.

        Removes all internal API URLs, numeric IDs, redundant flags, and the
        owner sub-object. What remains is the minimum needed to understand
        what happened and why.
        """
        return {
            "id": n["id"],
            "reason": n["reason"],
            "updated_at": n["updated_at"],
            "subject": {
                "title": n["subject"]["title"],
                "type": n["subject"]["type"],
                "url": GitHubConnector._to_html_url(n["subject"].get("url")),
            },
            "repository": {
                "full_name": n["repository"]["full_name"],
                "description": n["repository"].get("description"),
            },
        }

    def _enrich_notification(self, n: dict) -> dict:
        """Prune a notification and attach the most relevant content.

        For PRs you authored: fetches the reviews endpoint directly, since
        latest_comment_url either points to the PR object itself (not a review)
        or is absent entirely.

        For everything else: fetches latest_comment_url when present to get
        the body of the most recent issue comment, PR comment, or review.

        Makes one extra API call per notification. Failures are silently
        swallowed so one bad fetch doesn't drop the whole batch.
        """
        pruned = self._prune_notification(n)

        try:
            if n.get("reason") == "author" and n["subject"]["type"] == "PullRequest":
                pr_url = n["subject"].get("url")
                if pr_url:
                    reviews: list = self._request(f"{pr_url}/reviews", params={"per_page": "10"})  # type: ignore[assignment]
                    submitted = [r for r in reviews if r.get("state") != "PENDING"]
                    if submitted:
                        review = max(submitted, key=lambda r: r.get("submitted_at", ""))
                        latest: dict = {}
                        user = review.get("user")
                        if isinstance(user, dict) and user.get("login"):
                            latest["author"] = user["login"]
                        if review.get("body"):
                            latest["body"] = review["body"][:150]
                        if review.get("state"):
                            latest["state"] = review["state"]
                        if review.get("submitted_at"):
                            latest["submitted_at"] = review["submitted_at"]
                        if latest:
                            pruned["latest_content"] = latest
            else:
                comment_url = n["subject"].get("latest_comment_url")
                if comment_url:
                    content = self._request(comment_url)
                    if isinstance(content, dict):
                        latest = {}
                        user = content.get("user")
                        if isinstance(user, dict) and user.get("login"):
                            latest["author"] = user["login"]
                        if content.get("body"):
                            latest["body"] = content["body"][:150]
                        if content.get("state"):
                            latest["state"] = content["state"]
                        ts = content.get("submitted_at") or content.get("created_at")
                        if ts:
                            latest["submitted_at"] = ts
                        if latest:
                            pruned["latest_content"] = latest
        except Exception:
            pass  # enrichment is best-effort

        return pruned

    def fetch(self, since: datetime) -> ConnectorResult:
        """Fetch all notifications (read and unread) since the given datetime.

        Args:
            since: Only return notifications updated after this UTC datetime.

        Returns:
            ConnectorResult with a single batch dict in payload, or an empty
            payload when there are no matching notifications.
        """
        start = time.monotonic()
        fetched_at = datetime.now(timezone.utc).isoformat()
        since_iso = since.isoformat()

        user = self._request("/user")
        username: str = user["login"]  # type: ignore[index]

        notifications: list = self._request(  # type: ignore[assignment]
            "/notifications",
            params={
                "all": "true",  # read and unread
                "since": since_iso,
                "per_page": "50",
            },
        )

        if not notifications:
            return ConnectorResult(
                success=True,
                found_new_content=False,
                item_count=0,
                api_calls=self._api_calls,
                llm_cost=0.0,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        filtered = [n for n in notifications if n.get("reason") not in self.EXCLUDED_REASONS]
        pruned = [self._enrich_notification(n) for n in filtered]

        return ConnectorResult(
            success=True,
            found_new_content=True,
            item_count=len(pruned),
            api_calls=self._api_calls,
            llm_cost=0.0,
            duration_ms=(time.monotonic() - start) * 1000,
            payload=[
                {
                    "source_type": "github",
                    "payload": json.dumps(pruned, default=str),
                    "metadata": {
                        "fetched_at": fetched_at,
                        "username": username,
                        "since": since_iso,
                        "raw_count": len(notifications),
                        "count": len(pruned),
                        "kind": "notifications",
                    },
                }
            ],
        )
