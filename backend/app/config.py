"""Application configuration.

Settings are loaded from environment variables (and .env if present).
All secrets and runtime paths are configured here so nothing else in
the application imports os.environ directly.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is three levels up from this file (backend/app/config.py)
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"), env_file_encoding="utf-8"
    )

    database_url: str = f"sqlite:///{_REPO_ROOT / 'data' / 'app.db'}"
    vault_path: str = str(_REPO_ROOT / "vault")

    # LLM
    anthropic_api_key: str = ""

    # Connectors (optional at startup — validated when connector is used)
    github_token: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = ""
    slack_bot_token: str = ""
    canvas_api_key: str = ""
    canvas_base_url: str = ""


settings = Settings()
