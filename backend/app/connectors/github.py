"""GitHub connector.

Fetches activity from tracked repositories: new issues, PRs, comments,
review requests, and commit summaries relevant to the user.

TODO: implement authentication (personal access token from settings)
TODO: define which repos to track (config or experience-linked)
TODO: implement incremental sync (track last-fetched timestamp or cursor)
TODO: filter to events relevant to the user
"""
from app.config import settings


class GitHubConnector:
    """Fetches GitHub activity for tracked repositories."""

    def fetch(self) -> list[dict]:
        # TODO: call GitHub REST/GraphQL API using settings.github_token
        # TODO: return list of batch dicts per repo/event type
        raise NotImplementedError
