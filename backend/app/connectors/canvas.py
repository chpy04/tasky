"""Canvas LMS connector.

Fetches assignments, announcements, and submissions for favorited courses.

Authentication: API token (settings.canvas_api_key)
Base URL: settings.canvas_base_url (e.g. https://canvas.instructure.com)

Sync strategy:
  - Assignments: updated_since={since}
  - Announcements: start_date={since}
  - Submissions: submitted_since={since}, filtered to only those with new
    instructor feedback (graded or new submission comments after `since`)

Scoping: only courses the user has favorited (GET /users/self/favorites/courses
with enrollment_state=active).
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorResult


class CanvasConnector(BaseConnector):
    """Fetches course data from Canvas LMS for favorited courses."""

    def __init__(self) -> None:
        if not settings.canvas_api_key:
            raise ValueError("CANVAS_API_KEY is not set — add it to your .env file")
        if not settings.canvas_base_url:
            raise ValueError("CANVAS_BASE_URL is not set — add it to your .env file")
        self._token = settings.canvas_api_key
        self._base = settings.canvas_base_url.rstrip("/")
        self._api_calls = 0

    # ── Internal helpers ──────────────────────────────────────────────────

    def _request(self, path: str, params: dict[str, str | list[str]] | None = None) -> object:
        """Make a GET request and follow pagination automatically.

        Returns the full list of results across all pages for list endpoints,
        or a single dict for object endpoints.
        """
        url = path if path.startswith("https://") else f"{self._base}/api/v1{path}"

        all_results: list = []
        is_list = True  # assume list until we see a dict response

        while url:
            full_url = url
            if params:
                full_url = f"{url}?{self._encode_params(params)}"
                params = None  # only apply to first page; subsequent pages carry their own params

            req = urllib.request.Request(
                full_url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/json",
                },
            )
            try:
                self._api_calls += 1
                with urllib.request.urlopen(req, timeout=20) as resp:
                    body = json.loads(resp.read())
                    link_header = resp.headers.get("Link", "")

                if isinstance(body, list):
                    all_results.extend(body)
                    url = self._next_page(link_header)
                else:
                    is_list = False
                    return body
            except urllib.error.HTTPError as exc:
                body_text = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Canvas API error {exc.code} for {full_url}: {body_text}"
                ) from exc

        return all_results if is_list else all_results

    @staticmethod
    def _encode_params(params: dict) -> str:
        """URL-encode params, supporting list values as repeated keys."""
        parts: list[tuple[str, str]] = []
        for k, v in params.items():
            if isinstance(v, list):
                for item in v:
                    parts.append((k, item))
            else:
                parts.append((k, v))
        return urllib.parse.urlencode(parts)

    @staticmethod
    def _next_page(link_header: str) -> str | None:
        """Parse a Canvas Link header and return the next-page URL, or None."""
        if not link_header:
            return None
        for part in link_header.split(","):
            segments = [s.strip() for s in part.split(";")]
            if len(segments) == 2 and segments[1] == 'rel="next"':
                return segments[0].strip("<>")
        return None

    # ── Pruning helpers ───────────────────────────────────────────────────

    @staticmethod
    def _prune_assignment(a: dict, course_name: str) -> dict:
        submission = a.get("submission") or {}
        out: dict = {
            "course": course_name,
            "title": a.get("name"),
            "due_at": a.get("due_at"),
            "points_possible": a.get("points_possible"),
            "updated_at": a.get("updated_at"),
            "submission_types": a.get("submission_types", []),
        }
        if submission:
            out["submission"] = {
                "state": submission.get("workflow_state"),
                "submitted_at": submission.get("submitted_at"),
                "late": submission.get("late", False),
                "missing": submission.get("missing", False),
                "score": submission.get("score"),
                "grade": submission.get("grade"),
            }
        return out

    @staticmethod
    def _prune_announcement(a: dict, course_name: str) -> dict:
        body = a.get("message") or ""
        # Truncate long HTML bodies — LLM only needs the gist
        if len(body) > 500:
            body = body[:500] + "…"
        return {
            "course": course_name,
            "title": a.get("title"),
            "posted_at": a.get("posted_at"),
            "body": body,
        }

    @staticmethod
    def _prune_submission(s: dict, since_iso: str, until_iso: str | None = None) -> dict | None:
        """Return a pruned submission dict only if it has new instructor feedback.

        'New feedback' means either:
          - workflow_state == 'graded' and graded_at >= since, or
          - at least one submission_comment posted after since by someone
            other than the submitting user.
        """
        state = s.get("workflow_state")
        graded_at = s.get("graded_at") or ""
        submitter_id = s.get("user_id")

        new_grade = state == "graded" and graded_at >= since_iso
        if new_grade and until_iso and graded_at > until_iso:
            new_grade = False

        new_comments = [
            c
            for c in (s.get("submission_comments") or [])
            if (c.get("created_at") or "") >= since_iso
            and c.get("author_id") != submitter_id
            and (not until_iso or (c.get("created_at") or "") <= until_iso)
        ]

        if not new_grade and not new_comments:
            return None

        assignment = s.get("assignment") or {}
        out: dict = {
            "course": assignment.get("course_id"),  # replaced with name in fetch()
            "assignment_title": assignment.get("name"),
            "due_at": assignment.get("due_at"),
            "points_possible": assignment.get("points_possible"),
            "submitted_at": s.get("submitted_at"),
            "state": state,
        }
        if new_grade:
            out["grade"] = s.get("grade")
            out["score"] = s.get("score")
            out["graded_at"] = graded_at
        if new_comments:
            out["new_comments"] = [
                {
                    "author": c.get("author", {}).get("display_name"),
                    "posted_at": c.get("created_at"),
                    "body": (c.get("comment") or "")[:300],
                }
                for c in new_comments
            ]
        return out

    # ── Public interface ──────────────────────────────────────────────────

    def fetch(self, since: datetime, until: datetime | None = None) -> ConnectorResult:
        start = time.monotonic()
        fetched_at = datetime.now(timezone.utc).isoformat()
        since_iso = since.isoformat()
        until_iso = until.isoformat() if until else None

        # 1. Favorite courses (scoping)
        courses: list = self._request(  # type: ignore[assignment]
            "/users/self/favorites/courses",
            params={"enrollment_state": "active", "per_page": "50"},
        )
        if not courses:
            return ConnectorResult(
                success=True,
                found_new_content=False,
                item_count=0,
                api_calls=self._api_calls,
                llm_cost=0.0,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        course_id_to_name: dict[int, str] = {c["id"]: c.get("name", str(c["id"])) for c in courses}
        course_ids = list(course_id_to_name.keys())

        # 2. Assignments updated since `since`.
        # Canvas's updated_since param is a hint but not always reliable, so
        # we also filter client-side on updated_at as a safety net.
        assignments: list[dict] = []
        for cid in course_ids:
            raw: list = self._request(  # type: ignore[assignment]
                f"/courses/{cid}/assignments",
                params={
                    "updated_since": since_iso,
                    "include[]": "submission",
                    "per_page": "50",
                },
            )
            for a in raw:
                updated = a.get("updated_at") or ""
                if updated >= since_iso and (not until_iso or updated <= until_iso):
                    assignments.append(self._prune_assignment(a, course_id_to_name[cid]))

        # 3. Announcements (all favorited courses, single call).
        # Canvas's start_date param is date-only (no time component), so items
        # from earlier the same day can leak through — filter client-side on
        # the full ISO timestamp.
        context_codes = [f"course_{cid}" for cid in course_ids]
        raw_announcements: list = self._request(  # type: ignore[assignment]
            "/announcements",
            params={
                "context_codes[]": context_codes,
                "start_date": since_iso[:10],  # date portion only, as Canvas expects
                "per_page": "50",
            },
        )
        announcements: list[dict] = []
        for a in raw_announcements:
            posted = a.get("posted_at") or ""
            if posted < since_iso:
                continue
            if until_iso and posted > until_iso:
                continue
            ctx = a.get("context_code", "")  # e.g. "course_12345"
            try:
                cid = int(ctx.split("_", 1)[1])
                cname = course_id_to_name.get(cid, ctx)
            except (IndexError, ValueError):
                cname = ctx
            announcements.append(self._prune_announcement(a, cname))

        # 4. Submissions with new instructor feedback.
        # We don't use submitted_since here because that filters on when the
        # student submitted, not when feedback arrived. Instead we fetch all
        # submissions and let _prune_submission filter by graded_at / comment
        # created_at against since_iso.
        submissions: list[dict] = []
        for cid in course_ids:
            raw_subs: list = self._request(  # type: ignore[assignment]
                f"/courses/{cid}/students/submissions",
                params={
                    "student_ids[]": "self",
                    "include[]": ["submission_comments", "assignment"],
                    "per_page": "50",
                },
            )
            for s in raw_subs:
                pruned = self._prune_submission(s, since_iso, until_iso)
                if pruned is not None:
                    pruned["course"] = course_id_to_name[cid]
                    submissions.append(pruned)

        # Tag each item with its kind and merge into a single list
        for item in assignments:
            item["kind"] = "assignment"
        for item in announcements:
            item["kind"] = "announcement"
        for item in submissions:
            item["kind"] = "graded_submission"

        all_items = assignments + announcements + submissions

        base_meta: dict[str, str] = {"fetched_at": fetched_at, "since": since_iso}
        if until_iso:
            base_meta["until"] = until_iso

        return ConnectorResult(
            success=True,
            found_new_content=len(all_items) > 0,
            item_count=len(all_items),
            api_calls=self._api_calls,
            llm_cost=0.0,
            duration_ms=(time.monotonic() - start) * 1000,
            payload=[
                {
                    "source_type": "canvas",
                    "payload": json.dumps(all_items, default=str),
                    "metadata": {
                        **base_meta,
                        "kind": "mixed",
                        "count": len(all_items),
                    },
                }
            ]
            if all_items
            else [],
        )
