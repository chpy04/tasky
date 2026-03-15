"""Task API routes.

Endpoints:
    GET    /tasks                  List tasks (filterable by status, experience, last-activity timeframe)
    POST   /tasks                  Create a task manually
    GET    /tasks/{id}             Get a single task
    PATCH  /tasks/{id}             Update task fields
    POST   /tasks/{id}/complete    Mark a task complete and record time spent
    POST   /tasks/{id}/uncomplete  Revert a done task to its prior status
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.task import Task, TaskStatus
from app.schemas.tasks import (
    CompleteTaskRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter()


def _to_response(task: Task, last_activity_at: datetime) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        experience_id=task.experience_id,
        due_at=task.due_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        parent_task_id=task.parent_task_id,
        created_by=task.created_by,
        external_ref=task.external_ref,
        time_spent_minutes=task.time_spent_minutes,
        last_activity_at=last_activity_at,
    )


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    status: list[TaskStatus] | None = Query(None),
    experience_id: int | None = None,
    updated_after: datetime | None = None,
    updated_before: datetime | None = None,
    db: Session = Depends(get_db),
):
    """List tasks with optional filters.

    - **status**: one or more status values (repeat the param for multiple)
    - **experience_id**: limit to tasks belonging to a specific experience
    - **updated_after**: only tasks whose last activity is after this datetime
    - **updated_before**: only tasks whose last activity is before this datetime
    """
    svc = TaskService(db)
    rows = svc.list_tasks(
        status=status,
        experience_id=experience_id,
        updated_after=updated_after,
        updated_before=updated_before,
    )
    return [_to_response(task, activity) for task, activity in rows]


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    svc = TaskService(db)
    task, activity = svc.create(**body.model_dump())
    return _to_response(task, activity)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    svc = TaskService(db)
    task, activity = svc.get(task_id)
    return _to_response(task, activity)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, body: TaskUpdate, db: Session = Depends(get_db)):
    svc = TaskService(db)
    # exclude_unset so omitted fields don't overwrite existing values with None
    task, activity = svc.update(task_id, **body.model_dump(exclude_unset=True))
    return _to_response(task, activity)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    body: CompleteTaskRequest | None = None,
    db: Session = Depends(get_db),
):
    svc = TaskService(db)
    time_spent = body.time_spent_minutes if body else None
    task, activity = svc.complete(task_id, time_spent_minutes=time_spent)
    return _to_response(task, activity)


@router.post("/{task_id}/uncomplete", response_model=TaskResponse)
def uncomplete_task(task_id: int, db: Session = Depends(get_db)):
    svc = TaskService(db)
    task, activity = svc.uncomplete(task_id)
    return _to_response(task, activity)
