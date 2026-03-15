"""Prompt assembly for LLM-based task proposal generation.

Builds the (system_prompt, user_prompt) pair that is passed to LLMClient.generate_proposals.

The system prompt comes from vault/Prompts/system.md.

The user prompt is assembled from:
- Ingestion run metadata (time range, run ID)
- For each batch: a source-specific preface from vault/Prompts/sources/{source_type}.md,
  followed by the raw payload from that batch.

Source prompt files are optional — if one is missing the section is still included
but without a preface, so the pipeline degrades gracefully.
"""

import json
import logging

from app.models.ingestion_batch import IngestionBatch, SourceType
from app.models.ingestion_run import IngestionRun
from app.models.task import Task
from app.vault.reader import VaultReader

logger = logging.getLogger(__name__)

# Maps SourceType enum values to vault prompt names under sources/
_SOURCE_PROMPT_NAMES: dict[SourceType, str] = {
    SourceType.github: "sources/github",
    SourceType.slack: "sources/slack",
    SourceType.email: "sources/email",
    SourceType.canvas: "sources/canvas",
}

_SOURCE_DISPLAY_NAMES: dict[SourceType, str] = {
    SourceType.github: "GitHub",
    SourceType.slack: "Slack",
    SourceType.email: "Email (Gmail)",
    SourceType.canvas: "Canvas",
}


def build_proposal_prompt(
    run: IngestionRun,
    vault: VaultReader,
    active_tasks: list[Task] | None = None,
) -> tuple[str, str]:
    """Compose the system and user prompts for a proposal generation call.

    Args:
        run: The IngestionRun whose batches should be included. Should be loaded
             with its `batches` relationship populated.
        vault: VaultReader instance used to load prompt files.
        active_tasks: Non-complete/cancelled tasks to include so the LLM knows
                      what already exists before proposing changes. Defaults to
                      an empty list when not provided.

    Returns:
        A (system_prompt, user_prompt) tuple ready to pass to LLMClient.generate_proposals.

    Raises:
        FileNotFoundError: If vault/Prompts/system.md is missing.
    """
    system_prompt = vault.read_prompt("system")
    user_prompt = _build_user_prompt(run, vault, active_tasks or [])
    return system_prompt, user_prompt


def _build_user_prompt(run: IngestionRun, vault: VaultReader, active_tasks: list[Task]) -> str:
    parts: list[str] = []

    # Header — give the model context about this specific run
    range_start = run.range_start.isoformat() if run.range_start else "unknown"
    range_end = run.range_end.isoformat() if run.range_end else "unknown"
    parts.append(
        f"# Ingestion Run {run.id}\n\n"
        f"Time range: {range_start} → {range_end}\n\n"
        "Review the data below from each connected source and propose task changes "
        "as described in your instructions."
    )

    # Active tasks — must appear before ingestion data so the model can
    # reference existing task IDs when proposing updates rather than
    # duplicating work that is already tracked.
    parts.append(_build_active_tasks_section(active_tasks))

    batches: list[IngestionBatch] = run.batches or []

    if not batches:
        parts.append("\n\n*(No batches were collected for this run.)*")
        return "\n".join(parts)

    # Group batches by source type so each source appears as one section
    grouped: dict[SourceType, list[IngestionBatch]] = {}
    for batch in batches:
        grouped.setdefault(batch.source_type, []).append(batch)

    for source_type, source_batches in grouped.items():
        display_name = _SOURCE_DISPLAY_NAMES.get(source_type, source_type.value)
        parts.append(f"\n\n---\n\n## {display_name}")

        # Prepend the source-specific prompt if it exists
        prompt_name = _SOURCE_PROMPT_NAMES.get(source_type)
        if prompt_name:
            try:
                source_prompt = vault.read_prompt(prompt_name)
                parts.append(f"\n{source_prompt}")
            except FileNotFoundError:
                logger.warning(
                    "Source prompt not found for %s (%s)", source_type.value, prompt_name
                )

        # Include the raw payload from each batch for this source
        for batch in source_batches:
            parts.append(f"\n### Batch {batch.id}")
            parts.append(_format_payload(batch.raw_payload))

    return "\n".join(parts)


def _build_active_tasks_section(tasks: list[Task]) -> str:
    """Render the active-tasks section that precedes ingestion data.

    The preface instructs the LLM to treat these records as the ground truth
    for what already exists, so it can propose *updates* to existing tasks
    instead of creating duplicates.
    """
    lines: list[str] = [
        "\n\n---\n\n## Current Active Tasks",
        "",
        "The following tasks are currently open (status is not `done` or `cancelled`). "
        "When reviewing the ingestion data below, **prefer proposing updates to these "
        "existing tasks** (using their `task_id`) over creating new ones for the same "
        "work item. Only propose a `create_task` when no existing task covers the new "
        "work. Use `change_status` to mark a task done or cancelled if the ingestion "
        "data indicates the work is finished or no longer relevant.",
        "",
    ]

    if not tasks:
        lines.append("*(No active tasks — all proposed changes should use `create_task`.)*")
        return "\n".join(lines)

    for task in tasks:
        due = f"  due: {task.due_at.date()}" if task.due_at else ""
        exp = f"  experience_id: {task.experience_id}" if task.experience_id else ""
        parent = f"  parent_task_id: {task.parent_task_id}" if task.parent_task_id else ""
        ext = f"  external_ref: {task.external_ref}" if task.external_ref else ""
        meta_parts = [p for p in [due, exp, parent, ext] if p]
        meta = ("  \n  " + "  \n  ".join(meta_parts)) if meta_parts else ""

        lines.append(f"- **[task_id={task.id}]** [{task.status.value}] {task.title}")
        if task.description:
            lines.append(f"  {task.description}")
        if meta:
            lines.append(meta)

    return "\n".join(lines)


def _format_payload(raw_payload: object) -> str:
    """Pretty-print the batch payload for inclusion in the prompt."""
    if raw_payload is None:
        return "*(empty)*"

    # raw_payload is stored as JSON text in the DB; try to pretty-print it
    if isinstance(raw_payload, str):
        try:
            parsed = json.loads(raw_payload)
            return f"\n```json\n{json.dumps(parsed, indent=2, default=str)}\n```"
        except (json.JSONDecodeError, ValueError):
            return f"\n```\n{raw_payload}\n```"

    # Already a dict/list (e.g. in tests)
    try:
        return f"\n```json\n{json.dumps(raw_payload, indent=2, default=str)}\n```"
    except (TypeError, ValueError):
        return f"\n```\n{raw_payload!r}\n```"
