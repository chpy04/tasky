"""OAuth authentication routes.

GET  /auth/gmail/connect   → returns the Google authorization URL
GET  /auth/gmail/callback  → exchanges code for tokens, saves to disk, redirects to frontend
GET  /auth/gmail/status    → returns { "connected": bool }
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings

router = APIRouter()

_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Holds in-flight OAuth flows keyed by `state` so the callback can reuse the
# same Flow instance (and its PKCE code_verifier) that generated the auth URL.
_pending_flows: dict[str, Flow] = {}
_TOKEN_PATH = Path(__file__).resolve().parents[3] / "data" / "gmail_token.json"

# Where Google sends the user after granting access. Must match what's registered
# in Google Cloud Console under "Authorized redirect URIs".
_DEFAULT_REDIRECT_URI = "http://localhost:7400/auth/gmail/callback"

# Where the backend sends the user after saving the token.
_FRONTEND_SUCCESS_URL = "http://localhost:7401/ingestion?gmail=connected"


def _redirect_uri() -> str:
    return settings.gmail_redirect_uri or _DEFAULT_REDIRECT_URI


def _flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_redirect_uri()],
        }
    }
    return Flow.from_client_config(client_config, scopes=_SCOPES, redirect_uri=_redirect_uri())


@router.get("/gmail/connect")
def gmail_connect():
    """Return the Google OAuth authorization URL for the frontend to redirect to."""
    if not settings.gmail_client_id or not settings.gmail_client_secret:
        return JSONResponse(
            status_code=400,
            content={"error": "GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in .env"},
        )
    flow = _flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # always prompt so we get a refresh_token
    )
    _pending_flows[state] = flow
    return {"url": auth_url}


@router.get("/gmail/callback")
def gmail_callback(code: str, state: str = ""):
    """Exchange the OAuth code for tokens, persist them, and redirect to the frontend."""
    flow = _pending_flows.pop(state, None) or _flow()
    flow.fetch_token(code=code)
    _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_PATH.write_text(flow.credentials.to_json())
    return RedirectResponse(_FRONTEND_SUCCESS_URL)


@router.get("/gmail/status")
def gmail_status():
    """Return whether valid Gmail credentials are stored on disk."""
    if not _TOKEN_PATH.exists():
        return {"connected": False}
    try:
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)
        return {"connected": creds.valid or bool(creds.refresh_token)}
    except Exception:
        return {"connected": False}
