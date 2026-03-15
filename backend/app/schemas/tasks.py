"""Pydantic request/response schemas for the tasks API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    experience_id: int | None = None
    due_at: datetime | None = None
    parent_task_id: int | None = None
    external_ref: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    experience_id: int | None = None
    due_at: datetime | None = None
    parent_task_id: int | None = None
    external_ref: str | None = None


class CompleteTaskRequest(BaseModel):
    time_spent_minutes: int | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    experience_id: int | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    parent_task_id: int | None
    created_by: str
    external_ref: str | None
    # Null until the task is marked complete
    time_spent_minutes: int | None
    # Derived: max(updated_at, most recent status history change)
    last_activity_at: datetime
