"""TaskProposal ORM model.

The central trust boundary. AI produces proposals; users review them;
approved proposals mutate tasks. Proposals are never deleted — rejected
and superseded ones remain for audit and tuning.

Table: task_proposals
  id                      integer primary key
  proposal_type           enum    create_task | update_task | change_status | cancel_task
  status                  enum    pending | approved | rejected | superseded
  task_id                 integer FK → tasks (nullable — null for create_task proposals)
  proposed_*              nullable fields mirroring Task columns
  reason_summary          text    nullable — AI-generated rationale shown to reviewer
  created_at              datetime not null
  reviewed_at             datetime nullable
  reviewed_by             enum    nullable — user | system
  created_by              enum    ai | system
  ingestion_batch_id      integer FK → ingestion_batches (nullable)

TODO: add edit-before-approve mechanics once UX is designed (tech spec §10 TODO).
TODO: implement proposal conflict/staleness detection (tech spec §20 TODO).
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.task import TaskStatus


class ProposalType(str, enum.Enum):
    create_task = "create_task"
    update_task = "update_task"
    change_status = "change_status"
    cancel_task = "cancel_task"


class ProposalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class ProposalReviewedBy(str, enum.Enum):
    user = "user"
    system = "system"


class ProposalCreatedBy(str, enum.Enum):
    ai = "ai"
    system = "system"


class TaskProposal(Base):
    __tablename__ = "task_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proposal_type: Mapped[ProposalType] = mapped_column(Enum(ProposalType), nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(Enum(ProposalStatus), nullable=False, default=ProposalStatus.pending)
    task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=True)
    proposed_title: Mapped[str | None] = mapped_column(String, nullable=True)
    proposed_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_status: Mapped[TaskStatus | None] = mapped_column(Enum(TaskStatus), nullable=True)
    proposed_experience_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("experiences.id"), nullable=True)
    proposed_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    proposed_parent_task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=True)
    proposed_external_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    reason_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[ProposalReviewedBy | None] = mapped_column(Enum(ProposalReviewedBy), nullable=True)
    created_by: Mapped[ProposalCreatedBy] = mapped_column(Enum(ProposalCreatedBy), nullable=False)
    ingestion_batch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ingestion_batches.id"), nullable=True)

    task: Mapped["Task | None"] = relationship("Task", foreign_keys=[task_id], back_populates="proposals")  # type: ignore[name-defined]
    ingestion_batch: Mapped["IngestionBatch | None"] = relationship("IngestionBatch", back_populates="proposals")  # type: ignore[name-defined]
