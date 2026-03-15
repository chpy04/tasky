"""Tests for IngestionService.

All connector classes are mocked — no real API calls are made.
Each test creates its own in-memory SQLite database.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.connectors.base import ConnectorResult
from app.models.base import Base
from app.models.experience import Experience  # noqa: F401
from app.models.ingestion_batch import BatchStatus, IngestionBatch, SourceType
from app.models.ingestion_run import RunStatus
from app.models.task import Task  # noqa: F401
from app.models.task_proposal import (
    ProposalCreatedBy,
    ProposalStatus,
    ProposalType,
    TaskProposal,
)
from app.models.task_status_history import TaskStatusHistory  # noqa: F401
from app.services.ingestion_service import IngestionService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _mock_result(source_type="github", item_count=3, kind="notifications"):
    return ConnectorResult(
        success=True,
        found_new_content=True,
        item_count=item_count,
        api_calls=2,
        llm_cost=0.0,
        duration_ms=150.0,
        payload=[
            {
                "source_type": source_type,
                "payload": json.dumps([{"item": i} for i in range(item_count)]),
                "metadata": {"kind": kind, "count": item_count},
            }
        ],
    )


def _range():
    return (
        datetime(2026, 3, 1, tzinfo=timezone.utc),
        datetime(2026, 3, 15, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# 1. trigger_run creates run and batches
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_trigger_run_creates_run_and_batches(MockGH, MockGmail, MockSlack, MockCanvas, db):
    MockGH.return_value.fetch.return_value = _mock_result("github")
    MockGmail.return_value.fetch.return_value = _mock_result("gmail", kind="emails")
    MockSlack.return_value.fetch.return_value = _mock_result("slack", kind="messages")
    MockCanvas.return_value.fetch.return_value = _mock_result("canvas", kind="assignments")

    svc = IngestionService(db)
    since, until = _range()
    run = svc.trigger_run(since, until)

    assert run.status == RunStatus.completed

    batches = db.query(IngestionBatch).filter_by(ingestion_run_id=run.id).all()
    assert len(batches) == 4

    for batch in batches:
        assert batch.item_count == 3
        assert batch.api_calls == 2
        assert batch.duration_ms == 150.0
        assert batch.status == BatchStatus.processed
        assert batch.success is True
        assert batch.found_new_content is True


# ---------------------------------------------------------------------------
# 2. trigger_run skips unconfigured connectors (ValueError on __init__)
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_trigger_run_skips_unconfigured_connectors(MockGH, MockGmail, MockSlack, MockCanvas, db):
    # GitHub and Canvas configured; Gmail and Slack raise ValueError
    MockGH.return_value.fetch.return_value = _mock_result("github")
    MockGmail.side_effect = ValueError("GMAIL_* not set")
    MockSlack.side_effect = ValueError("SLACK_* not set")
    MockCanvas.return_value.fetch.return_value = _mock_result("canvas", kind="assignments")

    svc = IngestionService(db)
    since, until = _range()
    run = svc.trigger_run(since, until)

    assert run.status == RunStatus.completed

    batches = db.query(IngestionBatch).filter_by(ingestion_run_id=run.id).all()
    assert len(batches) == 2

    source_types = {b.source_type for b in batches}
    assert SourceType.github in source_types
    assert SourceType.canvas in source_types


# ---------------------------------------------------------------------------
# 3. trigger_run handles connector fetch errors gracefully
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_trigger_run_handles_connector_errors(MockGH, MockGmail, MockSlack, MockCanvas, db):
    MockGH.return_value.fetch.return_value = _mock_result("github")
    MockGmail.return_value.fetch.side_effect = RuntimeError("API timeout")
    MockSlack.return_value.fetch.return_value = _mock_result("slack", kind="messages")
    MockCanvas.return_value.fetch.return_value = _mock_result("canvas", kind="assignments")

    svc = IngestionService(db)
    since, until = _range()
    run = svc.trigger_run(since, until)

    assert run.status == RunStatus.completed

    batches = db.query(IngestionBatch).filter_by(ingestion_run_id=run.id).all()
    assert len(batches) == 3


# ---------------------------------------------------------------------------
# 4. trigger_run — all connectors fail (non-ValueError)
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_trigger_run_all_fail(MockGH, MockGmail, MockSlack, MockCanvas, db):
    MockGH.return_value.fetch.side_effect = RuntimeError("fail 1")
    MockGmail.return_value.fetch.side_effect = RuntimeError("fail 2")
    MockSlack.return_value.fetch.side_effect = RuntimeError("fail 3")
    MockCanvas.return_value.fetch.side_effect = RuntimeError("fail 4")

    svc = IngestionService(db)
    since, until = _range()
    run = svc.trigger_run(since, until)

    assert run.status == RunStatus.failed
    assert run.error_summary is not None
    assert "fail 1" in run.error_summary
    assert "fail 4" in run.error_summary


# ---------------------------------------------------------------------------
# 5. rerun deletes old batches and creates new ones
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_rerun_deletes_old_batches(MockGH, MockGmail, MockSlack, MockCanvas, db):
    MockGH.return_value.fetch.return_value = _mock_result("github")
    MockGmail.side_effect = ValueError("not configured")
    MockSlack.side_effect = ValueError("not configured")
    MockCanvas.side_effect = ValueError("not configured")

    svc = IngestionService(db)
    since, until = _range()
    run = svc.trigger_run(since, until)

    old_batches = db.query(IngestionBatch).filter_by(ingestion_run_id=run.id).all()
    assert len(old_batches) == 1
    old_item_count = old_batches[0].item_count
    assert old_item_count == 3

    # Now rerun with 2 connectors available (different item_counts to distinguish)
    MockGH.side_effect = None
    MockGH.return_value.fetch.return_value = _mock_result("github", item_count=5)
    MockGmail.side_effect = None
    MockGmail.return_value = MagicMock()
    MockGmail.return_value.fetch.return_value = _mock_result("gmail", item_count=7, kind="emails")

    # Expire the run so the ORM reloads the batches relationship
    db.expire(run)

    run2 = svc.rerun(run.id)
    assert run2 is not None
    assert run2.id == run.id
    assert run2.status == RunStatus.completed

    # Expire all to force fresh DB reads
    db.expire_all()

    # New batches should replace old ones — verify by item_count
    new_batches = db.query(IngestionBatch).filter_by(ingestion_run_id=run.id).all()
    assert len(new_batches) == 2
    new_item_counts = sorted(b.item_count for b in new_batches)
    assert new_item_counts == [5, 7]  # old batch had item_count=3, confirming replacement


# ---------------------------------------------------------------------------
# 6. rerun nullifies proposal batch ids
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_rerun_nullifies_proposal_batch_ids(MockGH, MockGmail, MockSlack, MockCanvas, db):
    MockGH.return_value.fetch.return_value = _mock_result("github")
    MockGmail.side_effect = ValueError("not configured")
    MockSlack.side_effect = ValueError("not configured")
    MockCanvas.side_effect = ValueError("not configured")

    svc = IngestionService(db)
    since, until = _range()
    run = svc.trigger_run(since, until)

    batch = db.query(IngestionBatch).filter_by(ingestion_run_id=run.id).first()
    assert batch is not None

    # Link a proposal to this batch
    proposal = TaskProposal(
        proposal_type=ProposalType.create_task,
        status=ProposalStatus.pending,
        created_at=datetime.now(timezone.utc),
        created_by=ProposalCreatedBy.ai,
        ingestion_batch_id=batch.id,
    )
    db.add(proposal)
    db.commit()

    assert proposal.ingestion_batch_id == batch.id

    # Rerun
    MockGH.return_value.fetch.return_value = _mock_result("github", item_count=1)
    svc.rerun(run.id)

    db.refresh(proposal)
    assert proposal.ingestion_batch_id is None


# ---------------------------------------------------------------------------
# 7. rerun returns None for non-existent id
# ---------------------------------------------------------------------------
def test_rerun_not_found(db):
    svc = IngestionService(db)
    result = svc.rerun(99999)
    assert result is None


# ---------------------------------------------------------------------------
# 8. list_runs returns runs in descending started_at order
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_list_runs(MockGH, MockGmail, MockSlack, MockCanvas, db):
    MockGH.return_value.fetch.return_value = _mock_result("github")
    MockGmail.side_effect = ValueError("not configured")
    MockSlack.side_effect = ValueError("not configured")
    MockCanvas.side_effect = ValueError("not configured")

    svc = IngestionService(db)

    since1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
    since2 = datetime(2026, 3, 5, tzinfo=timezone.utc)
    since3 = datetime(2026, 3, 10, tzinfo=timezone.utc)
    until = datetime(2026, 3, 15, tzinfo=timezone.utc)

    svc.trigger_run(since1, until)
    svc.trigger_run(since2, until)
    svc.trigger_run(since3, until)

    runs = svc.list_runs()
    assert len(runs) == 3
    # Most recent first
    assert runs[0].started_at >= runs[1].started_at >= runs[2].started_at


# ---------------------------------------------------------------------------
# 9. until (range_end) parameter is forwarded to connectors
# ---------------------------------------------------------------------------
@patch("app.connectors.canvas.CanvasConnector")
@patch("app.connectors.slack.SlackConnector")
@patch("app.connectors.gmail.GmailConnector")
@patch("app.connectors.github.GitHubConnector")
def test_until_param_forwarded(MockGH, MockGmail, MockSlack, MockCanvas, db):
    MockGH.return_value.fetch.return_value = _mock_result("github")
    MockGmail.side_effect = ValueError("not configured")
    MockSlack.side_effect = ValueError("not configured")
    MockCanvas.side_effect = ValueError("not configured")

    svc = IngestionService(db)
    since = datetime(2026, 3, 1, tzinfo=timezone.utc)
    until = datetime(2026, 3, 15, tzinfo=timezone.utc)
    svc.trigger_run(since, until)

    MockGH.return_value.fetch.assert_called_once_with(since=since, until=until)
