"""Pydantic request/response schemas for the proposals API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngestionRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    status: str
    triggered_by: str
    range_start: datetime | None
    range_end: datetime | None


class IngestionBatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    status: str
    item_count: int | None
    ingestion_run: IngestionRunSummary | None


class TaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: str
    experience_id: int | None
    due_at: datetime | None
    external_ref: str | None


class ProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proposal_type: str
    status: str
    task_id: int | None
    proposed_title: str | None
    proposed_description: str | None
    proposed_status: str | None
    proposed_experience_id: int | None
    proposed_due_at: datetime | None
    proposed_parent_task_id: int | None
    proposed_external_ref: str | None
    reason_summary: str | None
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None
    created_by: str
    ingestion_batch_id: int | None
    task: TaskSummary | None
    ingestion_batch: IngestionBatchSummary | None


class ApproveProposalRequest(BaseModel):
    proposed_title: str | None = None
    proposed_description: str | None = None
    proposed_status: str | None = None
    proposed_experience_id: int | None = None
    proposed_due_at: datetime | None = None
    proposed_external_ref: str | None = None


class BatchRejectRequest(BaseModel):
    ingestion_run_id: int
