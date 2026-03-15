"""Experience management service.

Manages experience records and their corresponding vault folders.
Creating an experience scaffolds the vault folder with template
files so the user can fill in context immediately.

Responsibilities:
- list experiences (all or active-only)
- create an experience: DB record + vault folder scaffold
- update experience metadata (active flag, folder path)
- fetch a single experience by id
- load vault context for an experience (overview.md, current_status.md)

TODO: extend experience metadata model when UI needs evolve (tech spec §7 TODO)
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.vault.reader import VaultReader


class ExperienceService:
    def __init__(self, db: Session, vault: VaultReader | None = None) -> None:
        self.db = db
        self.vault = vault or VaultReader()

    def list_experiences(self, active_only: bool = False) -> list[Experience]:
        query = self.db.query(Experience)
        if active_only:
            query = query.filter(Experience.active.is_(True))
        return query.all()

    def get(self, experience_id: int) -> Experience:
        exp = self.db.query(Experience).filter(Experience.id == experience_id).first()
        if exp is None:
            raise HTTPException(status_code=404, detail=f"Experience {experience_id} not found")
        return exp

    def create(self, folder_path: str) -> Experience:
        """Create or reactivate an experience, validating the vault path on new records."""
        existing = (
            self.db.query(Experience)
            .filter(Experience.folder_path == folder_path)
            .first()
        )
        if existing:
            if existing.active:
                raise HTTPException(status_code=409, detail="Experience already active")
            existing.active = True
            self.db.commit()
            self.db.refresh(existing)
            return existing

        if not self.vault.experience_path_exists(folder_path):
            raise HTTPException(status_code=400, detail="Vault path does not exist")

        exp = Experience(folder_path=folder_path, active=True)
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def deactivate(self, experience_id: int) -> Experience:
        """Set active=False. Tasks linked to this experience are unaffected."""
        exp = self.get(experience_id)
        exp.active = False
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def update(self, experience_id: int, **kwargs) -> Experience:
        """Update active flag, folder_path, or other metadata fields."""
        exp = self.get(experience_id)
        for field, value in kwargs.items():
            if value is not None:
                setattr(exp, field, value)
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def get_vault_context(self, experience_id: int) -> dict[str, str]:
        """Return overview.md and current_status.md content keyed by filename."""
        exp = self.get(experience_id)
        return {
            filename: self.vault.read_experience_file(exp.folder_path, filename)
            for filename in ("overview.md", "current_status.md")
        }
