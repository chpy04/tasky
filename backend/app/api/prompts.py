"""Prompt management API routes.

Endpoints:
    GET    /prompts                      List all prompts
    GET    /prompts/{prompt_id}          Get a single prompt
    PATCH  /prompts/{prompt_id}          Update a prompt's content / description

    GET    /prompt-configs               List all PromptConfigs
    GET    /prompt-configs/active        Get the active PromptConfig with entries
    POST   /prompt-configs/{config_id}/activate  Set a config as the active one
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PromptResponse(BaseModel):
    id: int
    key: str
    kind: str
    source_type: str | None
    content: str
    description: str | None
    updated_at: str


class PromptUpdateRequest(BaseModel):
    content: str | None = None
    description: str | None = None


class PromptConfigEntryResponse(BaseModel):
    id: int
    source_type: str
    prompt_id: int
    prompt_key: str
    prompt_content: str


class PromptConfigResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    system_prompt_id: int
    system_prompt_key: str
    created_at: str
    updated_at: str
    entries: list[PromptConfigEntryResponse]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prompt_to_dict(p) -> dict:
    return {
        "id": p.id,
        "key": p.key,
        "kind": p.kind.value,
        "source_type": p.source_type.value if p.source_type else None,
        "content": p.content,
        "description": p.description,
        "updated_at": p.updated_at.isoformat(),
    }


def _config_to_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "is_active": c.is_active,
        "system_prompt_id": c.system_prompt_id,
        "system_prompt_key": c.system_prompt.key,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
        "entries": [
            {
                "id": e.id,
                "source_type": e.source_type.value,
                "prompt_id": e.prompt_id,
                "prompt_key": e.prompt.key,
                "prompt_content": e.prompt.content,
            }
            for e in c.entries
        ],
    }


# ---------------------------------------------------------------------------
# Prompt CRUD
# ---------------------------------------------------------------------------


@router.get("")
def list_prompts(db: Session = Depends(get_db)) -> list[dict]:
    from app.models.prompt import Prompt

    prompts = db.query(Prompt).order_by(Prompt.key).all()
    return [_prompt_to_dict(p) for p in prompts]


@router.get("/{prompt_id}")
def get_prompt(prompt_id: int, db: Session = Depends(get_db)) -> dict:
    from app.models.prompt import Prompt

    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _prompt_to_dict(prompt)


@router.patch("/{prompt_id}")
def update_prompt(prompt_id: int, body: PromptUpdateRequest, db: Session = Depends(get_db)) -> dict:
    from app.models.prompt import Prompt

    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if body.content is not None:
        prompt.content = body.content
    if body.description is not None:
        prompt.description = body.description
    prompt.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(prompt)
    return _prompt_to_dict(prompt)


# ---------------------------------------------------------------------------
# PromptConfig routes (mounted under /prompt-configs via a separate router
# that main.py registers — see below)
# ---------------------------------------------------------------------------

configs_router = APIRouter()


@configs_router.get("")
def list_configs(db: Session = Depends(get_db)) -> list[dict]:
    from app.models.prompt import PromptConfig

    configs = db.query(PromptConfig).order_by(PromptConfig.id).all()
    return [_config_to_dict(c) for c in configs]


@configs_router.get("/active")
def get_active_config(db: Session = Depends(get_db)) -> dict:
    from app.models.prompt import PromptConfig

    config = db.query(PromptConfig).filter(PromptConfig.is_active.is_(True)).first()
    if not config:
        raise HTTPException(status_code=404, detail="No active PromptConfig found")
    return _config_to_dict(config)


@configs_router.post("/{config_id}/activate")
def activate_config(config_id: int, db: Session = Depends(get_db)) -> dict:
    from app.models.prompt import PromptConfig

    target = db.get(PromptConfig, config_id)
    if not target:
        raise HTTPException(status_code=404, detail="PromptConfig not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Deactivate all others
    db.query(PromptConfig).filter(PromptConfig.id != config_id).update(
        {"is_active": False, "updated_at": now}
    )
    target.is_active = True
    target.updated_at = now

    db.commit()
    db.refresh(target)
    return _config_to_dict(target)
