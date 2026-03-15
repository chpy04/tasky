"""Gmail connector.

Fetches recent emails that may contain actionable information:
assignment notifications, project updates, meeting requests, etc.

TODO: implement OAuth2 flow (client_id/secret from settings)
TODO: define label/query filters to avoid ingesting noise
TODO: implement incremental sync via historyId or lastFetched timestamp
TODO: strip or truncate email bodies before batch storage
"""
from app.config import settings


class GmailConnector:
    """Fetches recent actionable emails via the Gmail API."""

    def fetch(self) -> list[dict]:
        # TODO: authenticate with OAuth2 using settings.gmail_client_*
        # TODO: query inbox with configured filters
        # TODO: return list of batch dicts per email
        raise NotImplementedError
