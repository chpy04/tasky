"""Structured output schemas for LLM proposal generation.

Defines the Pydantic models that constrain and validate model output.
The LLM returns proposals via tool calling (function calling), and the
response is validated against these schemas before persistence.
"""

from pydantic import BaseModel, Field

from app.models.task import TaskStatus
from app.models.task_proposal import ProposalType


class ProposedTask(BaseModel):
    """A single task proposal returned by the LLM."""

    proposal_type: ProposalType = Field(
        description="The type of proposal: create_task, update_task, change_status, or cancel_task"
    )
    task_id: int | None = Field(
        default=None,
        description="ID of the existing task to modify. Required for update_task, change_status, and cancel_task. Must be null for create_task.",
    )
    proposed_title: str | None = Field(
        default=None, description="Title for the task. Required for create_task."
    )
    proposed_description: str | None = Field(default=None, description="Description of the task.")
    proposed_status: TaskStatus | None = Field(
        default=None,
        description="Proposed status. Required for change_status.",
    )
    proposed_due_at: str | None = Field(
        default=None, description="Proposed due date in ISO 8601 format (e.g. 2026-03-20T17:00:00)."
    )
    proposed_external_ref: str | None = Field(
        default=None,
        description="External reference URL or identifier linking to the source (e.g. GitHub issue URL, email ID).",
    )
    reason_summary: str | None = Field(
        default=None,
        description="Brief human-readable explanation of why this proposal is being made.",
    )


class ProposalBatch(BaseModel):
    """The full structured output from one LLM call."""

    proposals: list[ProposedTask] = Field(
        description="List of task proposals generated from the ingestion data."
    )


# Tool definition with fully inlined schema (no $ref/$defs) so providers
# that don't support JSON Schema references can parse it.
PROPOSAL_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_proposals",
        "description": (
            "Submit a batch of task proposals based on the ingestion data. "
            "Each proposal should either create a new task or modify an existing one. "
            "Only propose changes that are clearly supported by the ingestion data."
        ),
        "parameters": {
            "type": "object",
            "required": ["proposals"],
            "properties": {
                "proposals": {
                    "type": "array",
                    "description": "List of task proposals generated from the ingestion data.",
                    "items": {
                        "type": "object",
                        "required": ["proposal_type"],
                        "properties": {
                            "proposal_type": {
                                "type": "string",
                                "enum": [
                                    "create_task",
                                    "update_task",
                                    "change_status",
                                    "cancel_task",
                                ],
                                "description": "The type of proposal: create_task, update_task, change_status, or cancel_task",
                            },
                            "task_id": {
                                "type": "integer",
                                "description": "ID of the existing task to modify. Required for update_task, change_status, and cancel_task. Omit for create_task.",
                            },
                            "proposed_title": {
                                "type": "string",
                                "description": "Title for the task. Required for create_task.",
                            },
                            "proposed_description": {
                                "type": "string",
                                "description": "Description of the task.",
                            },
                            "proposed_status": {
                                "type": "string",
                                "enum": [
                                    "todo",
                                    "in_progress",
                                    "blocked",
                                    "done",
                                    "cancelled",
                                ],
                                "description": "Proposed status. Required for change_status.",
                            },
                            "proposed_due_at": {
                                "type": "string",
                                "description": "Proposed due date in ISO 8601 format (e.g. 2026-03-20T17:00:00).",
                            },
                            "proposed_external_ref": {
                                "type": "string",
                                "description": "External reference URL or identifier linking to the source (e.g. GitHub issue URL, email ID).",
                            },
                            "reason_summary": {
                                "type": "string",
                                "description": "Brief human-readable explanation of why this proposal is being made.",
                            },
                        },
                    },
                },
            },
        },
    },
}
