"""IngestionBatch ORM model.

A batch holds the raw payload from one source connector within an
ingestion run. The LLM reads the payload plus system context and
produces task proposals.

Table: ingestion_batches
  id               integer primary key
  ingestion_run_id integer FK → ingestion_runs  not null
  source_type      enum    (same as IngestionRun.source_type)
  raw_payload      text    — minimally structured JSON or text from connector
  created_at       datetime not null
  processed_at     datetime nullable
  status           enum    pending | processed | failed
  error_summary    text    nullable

TODO: decide per-source normalization strategy before batch creation
      (see technical spec §11 TODO).
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SourceType(str, enum.Enum):
    slack = "slack"
    email = "email"
    github = "github"
    canvas = "canvas"


class BatchStatus(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    failed = "failed"


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingestion_runs.id"), nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus), nullable=False, default=BatchStatus.pending
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    found_new_content: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    connector_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)

    ingestion_run: Mapped["IngestionRun"] = relationship("IngestionRun", back_populates="batches")  # type: ignore[name-defined]
    proposals: Mapped[list["TaskProposal"]] = relationship(
        "TaskProposal", back_populates="ingestion_batch"
    )  # type: ignore[name-defined]
