"""IngestionRun ORM model.

Represents one full ingestion cycle — one or more connectors run,
producing batches that are then processed into proposals.

Table: ingestion_runs
  id             integer primary key
  started_at     datetime not null
  finished_at    datetime nullable
  status         enum    running | completed | failed
  triggered_by   enum    manual | scheduled | system
  source_type    enum    slack | email | calendar | github | mixed
  error_summary  text    nullable
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RunStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class TriggeredBy(str, enum.Enum):
    manual = "manual"
    scheduled = "scheduled"
    system = "system"


class SourceType(str, enum.Enum):
    slack = "slack"
    email = "email"
    calendar = "calendar"
    github = "github"
    mixed = "mixed"


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus), nullable=False, default=RunStatus.running
    )
    triggered_by: Mapped[TriggeredBy] = mapped_column(Enum(TriggeredBy), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    batches: Mapped[list["IngestionBatch"]] = relationship(
        "IngestionBatch", back_populates="ingestion_run"
    )  # type: ignore[name-defined]
