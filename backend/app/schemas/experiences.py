"""Pydantic request/response schemas for the experiences API."""
from pydantic import BaseModel, ConfigDict


class ExperienceCreate(BaseModel):
    folder_path: str
    active: bool = True


class ExperienceUpdate(BaseModel):
    active: bool | None = None
    folder_path: str | None = None


class ExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    active: bool
    folder_path: str


class ExperienceDetailResponse(ExperienceResponse):
    """Experience metadata plus the content of its vault markdown files."""
    vault_context: dict[str, str]
