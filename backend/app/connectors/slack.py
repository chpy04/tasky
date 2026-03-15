"""Slack connector.

Fetches messages from configured channels and DMs that may contain
actionable information or project updates.

TODO: implement authentication (bot token from settings)
TODO: define which channels/DMs to monitor (config)
TODO: implement incremental sync (cursor-based pagination)
TODO: filter out noise (bot messages, reactions-only, etc.)
"""
from app.config import settings


class SlackConnector:
    """Fetches Slack messages from configured channels."""

    def fetch(self) -> list[dict]:
        # TODO: authenticate using settings.slack_bot_token
        # TODO: fetch new messages from configured channel list
        # TODO: return list of batch dicts per channel segment
        raise NotImplementedError
