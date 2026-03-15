"""Ingestion control API routes.

Endpoints:
    GET    /ingestion/preview/github   Fetch GitHub data and return raw batches (no DB write)
    GET    /ingestion/preview/gmail    Fetch Gmail data and return raw batches  (no DB write)
    GET    /ingestion/preview/slack    Fetch Slack data and return raw batches  (no DB write)
    GET    /ingestion/preview/canvas   Fetch Canvas data and return raw batches (no DB write)

    POST   /ingestion/run              Trigger a manual ingestion run        [TODO]
    GET    /ingestion/runs             List ingestion runs                   [TODO]
    GET    /ingestion/runs/{id}        Get a single run with status          [TODO]
    GET    /ingestion/batches/{id}     Get batch payload and processing state [TODO]
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from app.connectors.base import ConnectorResult

router = APIRouter()

_SINCE_DAYS = Query(default=7, ge=1, le=90)


def _result_to_response(result: ConnectorResult) -> dict:
    return {
        "success": result.success,
        "found_new_content": result.found_new_content,
        "item_count": result.item_count,
        "api_calls": result.api_calls,
        "llm_cost": result.llm_cost,
        "duration_ms": result.duration_ms,
        "batches": result.payload,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/preview/github")
def preview_github(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch GitHub notifications and return ConnectorResult without persisting."""
    from app.connectors.github import GitHubConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    try:
        result = GitHubConnector().fetch(since)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _result_to_response(result)


@router.get("/preview/gmail")
def preview_gmail(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch Gmail emails and return ConnectorResult without persisting."""
    from app.connectors.gmail import GmailConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    result = GmailConnector().fetch(since)
    return _result_to_response(result)


@router.get("/preview/slack")
def preview_slack(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch Slack messages and return ConnectorResult without persisting."""
    from app.connectors.slack import SlackConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    result = SlackConnector().fetch(since)
    return _result_to_response(result)


@router.get("/preview/canvas")
def preview_canvas(since_days: int = _SINCE_DAYS) -> dict:
    """Fetch Canvas assignments and return ConnectorResult without persisting."""
    from app.connectors.canvas import CanvasConnector

    since = datetime.now(timezone.utc) - timedelta(days=since_days)
    result = CanvasConnector().fetch(since)
    return _result_to_response(result)


@router.post("/run")
def trigger_run():
    # TODO: delegate to IngestionService.trigger_manual_run
    raise NotImplementedError


@router.get("/runs")
def list_runs():
    # TODO: return ingestion run history
    raise NotImplementedError


@router.get("/runs/{run_id}")
def get_run(run_id: int):
    # TODO: return run with batch summary
    raise NotImplementedError


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int):
    # TODO: return raw batch payload and processing metadata
    raise NotImplementedError
