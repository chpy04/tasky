"""Experience management API routes.

Endpoints:
    GET    /experiences          List all experiences
    POST   /experiences          Create an experience record (validates vault path)
    GET    /experiences/{id}     Get a single experience with vault context
    PATCH  /experiences/{id}     Update experience metadata (active flag, folder path)
    DELETE /experiences/{id}     Deactivate an experience (soft delete)
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.experiences import (
    ExperienceCreate,
    ExperienceDetailResponse,
    ExperienceResponse,
    ExperienceUpdate,
)
from app.services.experience_service import ExperienceService

router = APIRouter()


@router.post("/sync")
def sync_experiences(db: Session = Depends(get_db)):
    """Sync experience records with the vault filesystem."""
    svc = ExperienceService(db)
    return svc.sync_with_vault()


@router.get("", response_model=list[ExperienceResponse])
def list_experiences(
    active: bool | None = None,
    db: Session = Depends(get_db),
):
    """List experiences. Pass ?active=true to return only active ones."""
    svc = ExperienceService(db)
    return svc.list_experiences(active_only=active is True)


@router.post("", response_model=ExperienceResponse, status_code=201)
def create_experience(body: ExperienceCreate, db: Session = Depends(get_db)):
    """Create or reactivate an experience, validating the vault path."""
    svc = ExperienceService(db)
    return svc.create(folder_path=body.folder_path)


@router.get("/{experience_id}", response_model=ExperienceDetailResponse)
def get_experience(experience_id: int, db: Session = Depends(get_db)):
    """Return experience metadata plus the content of its vault markdown files."""
    svc = ExperienceService(db)
    vault_context = svc.get_vault_context(experience_id)
    exp = svc.get(experience_id)
    return ExperienceDetailResponse(
        id=exp.id,
        active=exp.active,
        folder_path=exp.folder_path,
        vault_context=vault_context,
    )


@router.patch("/{experience_id}", response_model=ExperienceResponse)
def update_experience(
    experience_id: int,
    body: ExperienceUpdate,
    db: Session = Depends(get_db),
):
    svc = ExperienceService(db)
    return svc.update(experience_id, **body.model_dump(exclude_unset=True))


@router.delete("/{experience_id}", status_code=204)
def deactivate_experience(experience_id: int, db: Session = Depends(get_db)):
    """Soft-delete an experience by setting active=False."""
    svc = ExperienceService(db)
    svc.deactivate(experience_id)
    return Response(status_code=204)
