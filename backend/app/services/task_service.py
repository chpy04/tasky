"""Task domain service.

Owns all business logic for creating, editing, and completing tasks.
Route handlers should delegate to this service rather than touching
the ORM directly.

Responsibilities:
- create a task manually (from user input)
- update task fields
- mark a task complete and record time spent
- query tasks by status, experience, and last-activity timeframe
- fetch a single task by id
- append task_status_history whenever status changes

TODO: implement task deduplication/reconciliation (tech spec §8 TODO)
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.task import Task, TaskStatus
from app.models.task_status_history import ChangedBy, TaskStatusHistory


def _last_activity_at(task: Task) -> datetime:
    """Return the most recent activity timestamp for a task.

    Considers: created_at, updated_at, and any status-history entries.
    """
    candidates = [task.created_at, task.updated_at]
    if task.status_history:
        candidates.append(max(h.changed_at for h in task.status_history))
    return max(candidates)


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return self.db.query(Task).options(joinedload(Task.status_history))

    def list_tasks(
        self,
        status: list[TaskStatus] | None = None,
        experience_id: int | None = None,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
    ) -> list[tuple[Task, datetime]]:
        """Return tasks with their last_activity_at, filtered as requested.

        updated_after / updated_before filter on last_activity_at, which is
        the latest of: created_at, updated_at, and any status-history timestamp.
        """
        query = self._base_query()

        if status:
            query = query.filter(Task.status.in_(status))
        if experience_id is not None:
            query = query.filter(Task.experience_id == experience_id)

        tasks = query.all()

        # Compute last_activity_at in Python; filter on it if requested.
        results: list[tuple[Task, datetime]] = []
        for task in tasks:
            activity = _last_activity_at(task)
            if updated_after and activity < updated_after:
                continue
            if updated_before and activity > updated_before:
                continue
            results.append((task, activity))

        return results

    def get(self, task_id: int) -> tuple[Task, datetime]:
        """Return a single task with its last_activity_at, or raise 404."""
        task = self._base_query().filter(Task.id == task_id).first()
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task, _last_activity_at(task)

    def create(
        self,
        title: str,
        created_by: str = "user",
        **kwargs,
    ) -> tuple[Task, datetime]:
        """Create a new task and write the initial status-history entry."""
        task = Task(title=title, created_by=created_by, **kwargs)
        self.db.add(task)
        self.db.flush()  # populate task.id before writing history

        history = TaskStatusHistory(
            task_id=task.id,
            status=task.status,
            changed_by=ChangedBy.user,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(task)

        return task, _last_activity_at(task)

    def update(self, task_id: int, **kwargs) -> tuple[Task, datetime]:
        """Update task fields. Appends status history if status changed."""
        task, _ = self.get(task_id)

        old_status = task.status
        for field, value in kwargs.items():
            if value is not None:
                setattr(task, field, value)

        if "status" in kwargs and kwargs["status"] is not None and kwargs["status"] != old_status:
            history = TaskStatusHistory(
                task_id=task.id,
                status=task.status,
                changed_by=ChangedBy.user,
            )
            self.db.add(history)

        self.db.commit()
        self.db.refresh(task)

        return task, _last_activity_at(task)

    def complete(
        self,
        task_id: int,
        time_spent_minutes: int | None = None,  # noqa: ARG002 — reserved for future time-tracking
    ) -> tuple[Task, datetime]:
        """Mark a task done and record the status transition."""
        task, _ = self.get(task_id)

        if task.status == TaskStatus.done:
            raise HTTPException(status_code=409, detail="Task is already done")

        task.status = TaskStatus.done
        task.time_spent_minutes = time_spent_minutes
        history = TaskStatusHistory(
            task_id=task.id,
            status=TaskStatus.done,
            changed_by=ChangedBy.user,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(task)

        return task, _last_activity_at(task)

    def uncomplete(self, task_id: int) -> tuple[Task, datetime]:
        """Revert a done task to its most recent pre-completion status (default: todo)."""
        task, _ = self.get(task_id)

        if task.status != TaskStatus.done:
            raise HTTPException(status_code=409, detail="Task is not done")

        # Walk history newest-first; skip done entries to find the prior status.
        sorted_history = sorted(task.status_history, key=lambda h: h.changed_at, reverse=True)
        previous_status = TaskStatus.todo
        for entry in sorted_history:
            if entry.status != TaskStatus.done:
                previous_status = entry.status
                break

        task.status = previous_status
        history = TaskStatusHistory(
            task_id=task.id,
            status=previous_status,
            changed_by=ChangedBy.user,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(task)

        return task, _last_activity_at(task)
