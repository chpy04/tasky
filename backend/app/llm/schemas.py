"""Structured output schemas for LLM proposal generation.

Defines the Pydantic models that constrain and validate model output.
The LLM must return proposal objects that conform to these schemas
before they are persisted to task_proposals.

TODO: finalise schema fields and required vs optional constraints
TODO: decide whether to use tool_use, JSON mode, or response_format
      for schema enforcement (tech spec §12 TODO)
"""
from pydantic import BaseModel

from app.models.task import TaskStatus
from app.models.task_proposal import ProposalType


class ProposedTask(BaseModel):
    """A single task proposal returned by the LLM."""

    proposal_type: ProposalType
    task_id: int | None = None  # required for update/change_status/cancel
    proposed_title: str | None = None
    proposed_description: str | None = None
    proposed_status: TaskStatus | None = None
    proposed_due_at: str | None = None  # ISO 8601 string; parsed before persistence
    proposed_external_ref: str | None = None
    reason_summary: str | None = None


class ProposalBatch(BaseModel):
    """The full structured output from one LLM call."""

    proposals: list[ProposedTask]
