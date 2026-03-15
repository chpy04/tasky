"""Tests for task creation, editing, completion, and status history.

Covers both service-level logic (using db directly) and route-level behaviour
(using the TestClient).
"""

import pytest
from fastapi import HTTPException

from app.models.experience import Experience
from app.models.task import TaskStatus
from app.models.task_status_history import TaskStatusHistory
from app.services.task_service import TaskService

# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_create_task_defaults(db):
    svc = TaskService(db)
    task, activity = svc.create(title="Buy milk")
    assert task.id is not None
    assert task.title == "Buy milk"
    assert task.status == TaskStatus.todo
    assert task.created_by == "user"
    assert activity is not None


def test_create_task_writes_initial_status_history(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Track me")
    history = db.query(TaskStatusHistory).filter(TaskStatusHistory.task_id == task.id).all()
    assert len(history) == 1
    assert history[0].status == TaskStatus.todo


def test_get_task(db):
    svc = TaskService(db)
    created, _ = svc.create(title="Findable")
    task, activity = svc.get(created.id)
    assert task.title == "Findable"
    assert activity is not None


def test_get_task_not_found(db):
    svc = TaskService(db)
    with pytest.raises(HTTPException) as exc_info:
        svc.get(99999)
    assert exc_info.value.status_code == 404


def test_list_tasks_empty(db):
    svc = TaskService(db)
    assert svc.list_tasks() == []


def test_list_tasks_filter_by_status(db):
    svc = TaskService(db)
    svc.create(title="Todo task", status=TaskStatus.todo)
    svc.create(title="In progress task", status=TaskStatus.in_progress)
    results = svc.list_tasks(status=[TaskStatus.todo])
    assert len(results) == 1
    assert results[0][0].title == "Todo task"


def test_list_tasks_filter_by_experience(db):
    exp = Experience(folder_path="Projects/x", active=True)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    svc = TaskService(db)
    svc.create(title="Linked", experience_id=exp.id)
    svc.create(title="Unlinked")
    results = svc.list_tasks(experience_id=exp.id)
    assert len(results) == 1
    assert results[0][0].title == "Linked"


def test_update_task_title(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Old title")
    updated, _ = svc.update(task.id, title="New title")
    assert updated.title == "New title"


def test_update_task_status_appends_history(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Progress me")
    svc.update(task.id, status=TaskStatus.in_progress)
    history = db.query(TaskStatusHistory).filter(TaskStatusHistory.task_id == task.id).all()
    # Initial entry on create + one on status change
    assert len(history) == 2
    statuses = {h.status for h in history}
    assert TaskStatus.todo in statuses
    assert TaskStatus.in_progress in statuses


def test_update_task_no_status_change_does_not_append_history(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Same status")
    svc.update(task.id, title="New title")
    history = db.query(TaskStatusHistory).filter(TaskStatusHistory.task_id == task.id).all()
    assert len(history) == 1


def test_complete_task(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Finish me")
    completed, _ = svc.complete(task.id)
    assert completed.status == TaskStatus.done


def test_complete_task_records_time_spent(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Timed task")
    completed, _ = svc.complete(task.id, time_spent_minutes=45)
    assert completed.time_spent_minutes == 45


def test_complete_task_already_done_raises_409(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Already done")
    svc.complete(task.id)
    with pytest.raises(HTTPException) as exc_info:
        svc.complete(task.id)
    assert exc_info.value.status_code == 409


def test_uncomplete_task_reverts_to_todo(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Undo me")
    svc.complete(task.id)
    reverted, _ = svc.uncomplete(task.id)
    assert reverted.status == TaskStatus.todo


def test_uncomplete_task_reverts_to_prior_non_done_status(db):
    # Set up history directly with explicit timestamps: SQLite truncates changed_at
    # to second precision, so rapid service calls share the same timestamp and the
    # sort order is non-deterministic.  Explicit times make ordering deterministic.
    from datetime import datetime, timedelta

    from app.models.task import Task as TaskModel
    from app.models.task_status_history import ChangedBy

    base = datetime(2026, 1, 1, 12, 0, 0)
    task = TaskModel(
        title="Was in progress",
        status=TaskStatus.done,
        created_by="user",
        created_at=base,
        updated_at=base + timedelta(seconds=2),
    )
    db.add(task)
    db.flush()
    for i, status in enumerate([TaskStatus.todo, TaskStatus.in_progress, TaskStatus.done]):
        db.add(
            TaskStatusHistory(
                task_id=task.id,
                status=status,
                changed_at=base + timedelta(seconds=i),
                changed_by=ChangedBy.user,
            )
        )
    db.commit()
    db.expire_all()

    svc = TaskService(db)
    reverted, _ = svc.uncomplete(task.id)
    assert reverted.status == TaskStatus.in_progress


def test_uncomplete_task_not_done_raises_409(db):
    svc = TaskService(db)
    task, _ = svc.create(title="Not done yet")
    with pytest.raises(HTTPException) as exc_info:
        svc.uncomplete(task.id)
    assert exc_info.value.status_code == 409


def test_create_subtask(db):
    svc = TaskService(db)
    parent, _ = svc.create(title="Parent")
    child, _ = svc.create(title="Child", parent_task_id=parent.id)
    assert child.parent_task_id == parent.id


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


def test_api_list_tasks_empty(client):
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_api_create_task(client):
    resp = client.post("/tasks", json={"title": "Buy milk"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Buy milk"
    assert data["status"] == "todo"
    assert "id" in data
    assert "last_activity_at" in data


def test_api_create_task_with_optional_fields(client):
    resp = client.post(
        "/tasks",
        json={
            "title": "Full task",
            "description": "Do the thing",
            "status": "in_progress",
            "due_at": "2026-04-01T00:00:00",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Do the thing"
    assert data["status"] == "in_progress"


def test_api_get_task(client):
    task_id = client.post("/tasks", json={"title": "My task"}).json()["id"]
    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "My task"


def test_api_get_task_not_found(client):
    assert client.get("/tasks/99999").status_code == 404


def test_api_list_tasks_appears_after_create(client):
    client.post("/tasks", json={"title": "Task one"})
    client.post("/tasks", json={"title": "Task two"})
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_api_list_tasks_filter_by_status(client):
    client.post("/tasks", json={"title": "Todo task", "status": "todo"})
    client.post("/tasks", json={"title": "In progress task", "status": "in_progress"})
    resp = client.get("/tasks?status=todo")
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Todo task"


def test_api_list_tasks_filter_by_multiple_statuses(client):
    client.post("/tasks", json={"title": "Todo task", "status": "todo"})
    client.post("/tasks", json={"title": "In progress task", "status": "in_progress"})
    client.post("/tasks", json={"title": "Done task", "status": "done"})
    resp = client.get("/tasks?status=todo&status=in_progress")
    assert len(resp.json()) == 2


def test_api_list_tasks_filter_by_experience(client, db):
    exp = Experience(folder_path="Projects/x", active=True)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    client.post("/tasks", json={"title": "Linked", "experience_id": exp.id})
    client.post("/tasks", json={"title": "Unlinked"})
    resp = client.get(f"/tasks?experience_id={exp.id}")
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Linked"


def test_api_update_task_title(client):
    task_id = client.post("/tasks", json={"title": "Old title"}).json()["id"]
    resp = client.patch(f"/tasks/{task_id}", json={"title": "New title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New title"


def test_api_update_task_status(client, db):
    task_id = client.post("/tasks", json={"title": "Progressing"}).json()["id"]
    resp = client.patch(f"/tasks/{task_id}", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"
    history = db.query(TaskStatusHistory).filter(TaskStatusHistory.task_id == task_id).all()
    assert len(history) == 2


def test_api_complete_task(client):
    task_id = client.post("/tasks", json={"title": "Finish me"}).json()["id"]
    resp = client.post(f"/tasks/{task_id}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_api_complete_task_with_time_spent(client):
    task_id = client.post("/tasks", json={"title": "Timed task"}).json()["id"]
    resp = client.post(f"/tasks/{task_id}/complete", json={"time_spent_minutes": 45})
    assert resp.status_code == 200
    assert resp.json()["time_spent_minutes"] == 45


def test_api_complete_task_already_done_returns_409(client):
    task_id = client.post("/tasks", json={"title": "Already done"}).json()["id"]
    client.post(f"/tasks/{task_id}/complete")
    assert client.post(f"/tasks/{task_id}/complete").status_code == 409


def test_api_uncomplete_task(client):
    task_id = client.post("/tasks", json={"title": "To undo"}).json()["id"]
    client.post(f"/tasks/{task_id}/complete")
    resp = client.post(f"/tasks/{task_id}/uncomplete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "todo"


def test_api_uncomplete_task_reverts_to_prior_status(client, db):
    # See note in test_uncomplete_task_reverts_to_prior_non_done_status: set up
    # history directly with distinct timestamps to avoid second-precision collisions.
    from datetime import datetime, timedelta

    from app.models.task import Task as TaskModel
    from app.models.task_status_history import ChangedBy

    base = datetime(2026, 1, 1, 12, 0, 0)
    task = TaskModel(
        title="Prior status",
        status=TaskStatus.done,
        created_by="user",
        created_at=base,
        updated_at=base + timedelta(seconds=2),
    )
    db.add(task)
    db.flush()
    for i, status in enumerate([TaskStatus.todo, TaskStatus.in_progress, TaskStatus.done]):
        db.add(
            TaskStatusHistory(
                task_id=task.id,
                status=status,
                changed_at=base + timedelta(seconds=i),
                changed_by=ChangedBy.user,
            )
        )
    db.commit()

    resp = client.post(f"/tasks/{task.id}/uncomplete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_api_uncomplete_task_not_done_returns_409(client):
    task_id = client.post("/tasks", json={"title": "Not done"}).json()["id"]
    assert client.post(f"/tasks/{task_id}/uncomplete").status_code == 409


def test_api_create_subtask(client):
    parent_id = client.post("/tasks", json={"title": "Parent"}).json()["id"]
    resp = client.post("/tasks", json={"title": "Child", "parent_task_id": parent_id})
    assert resp.status_code == 201
    assert resp.json()["parent_task_id"] == parent_id
