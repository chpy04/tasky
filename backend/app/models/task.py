"""Task ORM model.

Tasks are the main actionable records. They may optionally belong to
an experience and support simple subtask nesting via parent_task_id.

Table: tasks
  id               integer primary key
  title            text    not null
  description      text    nullable
  status           enum    todo | in_progress | blocked | done | cancelled
  experience_id    integer FK → experiences (nullable)
  due_at           datetime nullable
  created_at       datetime not null
  updated_at       datetime not null
  parent_task_id   integer FK → tasks (nullable, for subtasks)
  created_by       text    — 'user' | 'system' | 'ai' (origin of task)
  external_ref     text    nullable — link to external system identifier

TODO: clarify exact created_by semantics (see technical spec §8).
TODO: implement deduplication/reconciliation rules (see technical spec §8 TODO).
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"
    cancelled = "cancelled"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), nullable=False, default=TaskStatus.todo
    )
    experience_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("experiences.id"), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    parent_task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String, nullable=False, default="user")
    external_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    time_spent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    experience: Mapped["Experience | None"] = relationship("Experience", back_populates="tasks")  # type: ignore[name-defined]
    subtasks: Mapped[list["Task"]] = relationship("Task", foreign_keys=[parent_task_id])
    status_history: Mapped[list["TaskStatusHistory"]] = relationship(
        "TaskStatusHistory", back_populates="task"
    )  # type: ignore[name-defined]
    proposals: Mapped[list["TaskProposal"]] = relationship(
        "TaskProposal", foreign_keys="TaskProposal.task_id", back_populates="task"
    )  # type: ignore[name-defined]
