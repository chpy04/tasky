"""Experience ORM model.

An experience represents a long-running context such as a class, job,
project, or club. The database stores only operational metadata; all
narrative content lives in the corresponding vault folder.

Table: experiences
  id          integer primary key
  active      boolean — whether this experience is loaded into LLM context
  folder_path text    — path to the experience folder within vault/Experiences/

TODO: extend with slug, display_name, category, or ordering once UI
      needs are clearer (see technical spec §7 TODO).
"""
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    folder_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="experience")  # type: ignore[name-defined]
