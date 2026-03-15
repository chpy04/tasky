"""Canvas LMS connector.

Fetches assignment data, announcements, and course updates from Canvas.

TODO: implement authentication (API key from settings)
TODO: define which courses to track
TODO: implement incremental sync (check for new/updated assignments)
TODO: map Canvas assignment due dates to task due_at field
"""
from app.config import settings


class CanvasConnector:
    """Fetches course and assignment data from Canvas LMS."""

    def fetch(self) -> list[dict]:
        # TODO: call Canvas REST API using settings.canvas_api_key and settings.canvas_base_url
        # TODO: return list of batch dicts per course/assignment group
        raise NotImplementedError
