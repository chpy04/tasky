"""TaskStatusHistory ORM model.

Append-only log of every status transition for a task. Written whenever
a task status changes — whether from a user action or an approved proposal.

Table: task_status_history
  id          integer primary key
  task_id     integer FK → tasks  not null
  status      enum    (same values as Task.status)
  changed_at  datetime not null
  changed_by  enum    user | ai | system

Note: changed_by = 'ai' may be set when an approved AI proposal caused
the change. This may be revisited during implementation (see tech spec §9).
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.task import TaskStatus


class ChangedBy(str, enum.Enum):
    user = "user"
    ai = "ai"
    system = "system"


class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    changed_by: Mapped[ChangedBy] = mapped_column(Enum(ChangedBy), nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="status_history")  # type: ignore[name-defined]
