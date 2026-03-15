"""Application configuration.

Settings are loaded from environment variables (and .env if present).
All secrets and runtime paths are configured here so nothing else in
the application imports os.environ directly.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ is two levels up from this file (backend/app/config.py)
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"), env_file_encoding="utf-8"
    )

    database_url: str = f"sqlite:///{_REPO_ROOT / 'data' / 'app.db'}"
    vault_path: str = str(_REPO_ROOT / "vault")

    # LLM
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"

    # Connectors (optional at startup — validated when connector is used)
    github_token: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = ""
    slack_user_token: str = ""
    slack_keywords: str = ""  # comma-separated list of keyword alert terms
    canvas_api_key: str = ""
    canvas_base_url: str = ""


settings = Settings()
