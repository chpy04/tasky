"""Tests for experience management.

Covers both service-level logic (using db directly) and route-level behaviour
(using the TestClient). VaultReader is always stubbed via the mock_vault fixture.
"""

import pytest
from fastapi import HTTPException

from app.models.experience import Experience
from app.services.experience_service import ExperienceService

# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_list_experiences_empty(db, mock_vault):
    svc = ExperienceService(db, vault=mock_vault)
    assert svc.list_experiences() == []


def test_list_experiences_returns_all(db, mock_vault):
    db.add(Experience(folder_path="Projects/alpha", active=True))
    db.add(Experience(folder_path="Projects/beta", active=False))
    db.commit()

    svc = ExperienceService(db, vault=mock_vault)
    assert len(svc.list_experiences()) == 2


def test_list_experiences_active_only(db, mock_vault):
    db.add(Experience(folder_path="Projects/alpha", active=True))
    db.add(Experience(folder_path="Projects/beta", active=False))
    db.commit()

    svc = ExperienceService(db, vault=mock_vault)
    results = svc.list_experiences(active_only=True)
    assert len(results) == 1
    assert results[0].folder_path == "Projects/alpha"


def test_create_experience(db, mock_vault):
    mock_vault.experience_path_exists.return_value = True
    svc = ExperienceService(db, vault=mock_vault)
    exp = svc.create("Projects/new")
    assert exp.id is not None
    assert exp.folder_path == "Projects/new"
    assert exp.active is True


def test_create_experience_vault_path_missing(db, mock_vault):
    mock_vault.experience_path_exists.return_value = False
    svc = ExperienceService(db, vault=mock_vault)
    with pytest.raises(HTTPException) as exc_info:
        svc.create("Projects/ghost")
    assert exc_info.value.status_code == 400


def test_create_experience_already_active_raises_409(db, mock_vault):
    db.add(Experience(folder_path="Projects/existing", active=True))
    db.commit()
    svc = ExperienceService(db, vault=mock_vault)
    with pytest.raises(HTTPException) as exc_info:
        svc.create("Projects/existing")
    assert exc_info.value.status_code == 409


def test_create_experience_reactivates_inactive(db, mock_vault):
    db.add(Experience(folder_path="Projects/dormant", active=False))
    db.commit()
    svc = ExperienceService(db, vault=mock_vault)
    exp = svc.create("Projects/dormant")
    assert exp.active is True


def test_get_experience(db, mock_vault):
    db.add(Experience(folder_path="Projects/alpha", active=True))
    db.commit()
    svc = ExperienceService(db, vault=mock_vault)
    exp_id = svc.list_experiences()[0].id
    exp = svc.get(exp_id)
    assert exp.folder_path == "Projects/alpha"


def test_get_experience_not_found(db, mock_vault):
    svc = ExperienceService(db, vault=mock_vault)
    with pytest.raises(HTTPException) as exc_info:
        svc.get(999)
    assert exc_info.value.status_code == 404


def test_deactivate_experience(db, mock_vault):
    db.add(Experience(folder_path="Projects/alpha", active=True))
    db.commit()
    svc = ExperienceService(db, vault=mock_vault)
    exp_id = svc.list_experiences()[0].id
    svc.deactivate(exp_id)
    assert svc.get(exp_id).active is False


def test_deactivate_experience_not_found(db, mock_vault):
    svc = ExperienceService(db, vault=mock_vault)
    with pytest.raises(HTTPException) as exc_info:
        svc.deactivate(999)
    assert exc_info.value.status_code == 404


def test_get_vault_context(db, mock_vault):
    mock_vault.read_experience_file.side_effect = lambda folder, fname: f"content of {fname}"
    db.add(Experience(folder_path="Projects/alpha", active=True))
    db.commit()
    svc = ExperienceService(db, vault=mock_vault)
    exp_id = svc.list_experiences()[0].id
    context = svc.get_vault_context(exp_id)
    assert context["overview.md"] == "content of overview.md"
    assert context["current_status.md"] == "content of current_status.md"


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


def test_api_list_experiences_empty(client):
    resp = client.get("/experiences")
    assert resp.status_code == 200
    assert resp.json() == []


def test_api_create_experience(client):
    resp = client.post("/experiences", json={"folder_path": "Projects/myproject"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["folder_path"] == "Projects/myproject"
    assert data["active"] is True
    assert "id" in data


def test_api_create_experience_vault_path_missing(client, mock_vault):
    mock_vault.experience_path_exists.return_value = False
    resp = client.post("/experiences", json={"folder_path": "Projects/ghost"})
    assert resp.status_code == 400


def test_api_create_experience_already_active_returns_409(client):
    client.post("/experiences", json={"folder_path": "Projects/dup"})
    resp = client.post("/experiences", json={"folder_path": "Projects/dup"})
    assert resp.status_code == 409


def test_api_create_experience_reactivates_inactive(client, db):
    db.add(Experience(folder_path="Projects/dormant", active=False))
    db.commit()
    resp = client.post("/experiences", json={"folder_path": "Projects/dormant"})
    assert resp.status_code == 201
    assert resp.json()["active"] is True


def test_api_get_experience(client, mock_vault):
    mock_vault.read_experience_file.return_value = "# Overview"
    create_resp = client.post("/experiences", json={"folder_path": "Projects/demo"})
    exp_id = create_resp.json()["id"]
    resp = client.get(f"/experiences/{exp_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["folder_path"] == "Projects/demo"
    assert "vault_context" in data
    assert "overview.md" in data["vault_context"]


def test_api_get_experience_not_found(client):
    resp = client.get("/experiences/9999")
    assert resp.status_code == 404


def test_api_deactivate_experience(client):
    create_resp = client.post("/experiences", json={"folder_path": "Projects/toremove"})
    exp_id = create_resp.json()["id"]
    resp = client.delete(f"/experiences/{exp_id}")
    assert resp.status_code == 204
    # Should no longer appear in active-only list
    active = [e["id"] for e in client.get("/experiences?active=true").json()]
    assert exp_id not in active


def test_api_deactivate_experience_not_found(client):
    resp = client.delete("/experiences/9999")
    assert resp.status_code == 404


def test_api_update_experience(client):
    create_resp = client.post("/experiences", json={"folder_path": "Projects/toupdate"})
    exp_id = create_resp.json()["id"]
    resp = client.patch(f"/experiences/{exp_id}", json={"active": False})
    assert resp.status_code == 200
    assert resp.json()["active"] is False


def test_api_list_experiences_shows_all_by_default(client):
    client.post("/experiences", json={"folder_path": "Projects/a"})
    client.post("/experiences", json={"folder_path": "Projects/b"})
    resp = client.get("/experiences")
    assert len(resp.json()) == 2


def test_api_list_experiences_active_filter(client, db):
    db.add(Experience(folder_path="Projects/inactive", active=False))
    db.commit()
    client.post("/experiences", json={"folder_path": "Projects/active"})
    resp = client.get("/experiences?active=true")
    paths = [e["folder_path"] for e in resp.json()]
    assert "Projects/active" in paths
    assert "Projects/inactive" not in paths
