"""Ingestion control API routes.

Endpoints:
    POST   /ingestion/run              Trigger a manual ingestion run
    GET    /ingestion/runs             List ingestion runs
    GET    /ingestion/runs/{id}        Get a single run with status
    GET    /ingestion/batches/{id}     Get batch payload and processing state

TODO: implement route handlers using IngestionService
"""
from fastapi import APIRouter

router = APIRouter()


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
