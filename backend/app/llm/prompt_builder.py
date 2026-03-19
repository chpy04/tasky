"""Prompt assembly for LLM-based task proposal generation.

Builds the (system_prompt, user_prompt) pair that is passed to LLMClient.generate_proposals.

The system prompt and source-specific prefaces are loaded from the active PromptConfig
in the database (populated by migration d4e5f6g7h8i9 from vault/Prompts/).

Canvas markers in the system prompt are expanded at build time:
  [[source:X]]        → source-specific interpretation instructions
  [[experiences]]     → list of active experiences for task attribution
  [[active_tasks]]    → currently open tasks so the model avoids duplicates
  [[source_data:X]]   → raw connector batches for source X

Any marker absent from the system prompt is excluded from the final prompt entirely.
"""

import json
import logging
import re

from sqlalchemy.orm import Session

from app.models.experience import Experience
from app.models.ingestion_batch import IngestionBatch, SourceType
from app.models.ingestion_run import IngestionRun
from app.models.task import Task

logger = logging.getLogger(__name__)

_SOURCE_DISPLAY_NAMES: dict[SourceType, str] = {
    SourceType.github: "GitHub",
    SourceType.slack: "Slack",
    SourceType.email: "Email (Gmail)",
    SourceType.canvas: "Canvas",
}

# Unified marker regex: [[source:X]], [[source_data:X]], [[experiences]], [[active_tasks]]
_MARKER_RE = re.compile(r"\[\[(\w+)(?::(\w+))?\]\]")


def _expand_markers(
    system_prompt: str,
    source_prompts: dict[SourceType, str],
    experiences: list[Experience] | None = None,
    active_tasks: list[Task] | None = None,
    batches_by_source: dict[SourceType, list[IngestionBatch]] | None = None,
) -> str:
    """Replace all [[...]] markers with runtime content.

    Markers absent from the system prompt are not included anywhere — there is
    no fallback to the user prompt.  Unknown marker kinds are stripped silently.
    """

    def replacer(m: re.Match) -> str:
        marker_kind = m.group(1)
        marker_arg = m.group(2)

        if marker_kind == "source":
            try:
                st = SourceType(marker_arg)
            except (ValueError, TypeError):
                return ""
            content = source_prompts.get(st)
            if content is None:
                return ""
            display = _SOURCE_DISPLAY_NAMES.get(st, st.value)
            return f"---\n\n## {display} Instructions\n\n{content}"

        if marker_kind == "experiences":
            return _build_experiences_section(experiences or []).lstrip("\n")

        if marker_kind == "active_tasks":
            return _build_active_tasks_section(active_tasks or []).lstrip("\n")

        if marker_kind == "source_data":
            try:
                st = SourceType(marker_arg)
            except (ValueError, TypeError):
                return ""
            batches = (batches_by_source or {}).get(st, [])
            if not batches:
                return ""
            display = _SOURCE_DISPLAY_NAMES.get(st, st.value)
            parts = [f"---\n\n## {display} Data"]
            for batch in batches:
                parts.append(f"\n### Batch {batch.id}")
                parts.append(_format_payload(batch.raw_payload))
            return "\n".join(parts)

        return ""  # unknown marker kind — strip

    return _MARKER_RE.sub(replacer, system_prompt).strip()


def _get_active_prompts(db: Session) -> tuple[str, dict[SourceType, str]]:
    """Return (system_prompt_content, {source_type: content}) from the active PromptConfig.

    Raises RuntimeError if no active config exists.
    """
    from app.models.prompt import PromptConfig

    config = db.query(PromptConfig).filter(PromptConfig.is_active.is_(True)).first()
    if config is None:
        raise RuntimeError(
            "No active PromptConfig found. Run 'alembic upgrade head' to seed the database."
        )

    system_content = config.system_prompt.content
    source_prompts: dict[SourceType, str] = {
        entry.source_type: entry.prompt.content for entry in config.entries
    }
    return system_content, source_prompts


def build_proposal_prompt(
    run: IngestionRun,
    db: Session,
    active_tasks: list[Task] | None = None,
    experiences: list[Experience] | None = None,
) -> tuple[str, str]:
    """Compose the system and user prompts for a proposal generation call.

    The system prompt is built by expanding canvas markers in the active
    PromptConfig's system prompt content.  Only markers that are present in
    the stored system prompt are included; unplaced blocks are excluded.

    Args:
        run: The IngestionRun whose batches should be included.
        db: SQLAlchemy session used to load the active PromptConfig.
        active_tasks: Non-complete/cancelled tasks to expand [[active_tasks]].
        experiences: Active experiences to expand [[experiences]].

    Returns:
        A (system_prompt, user_prompt) tuple ready to pass to LLMClient.generate_proposals.

    Raises:
        RuntimeError: If no active PromptConfig exists in the database.
    """
    system_raw, source_prompts = _get_active_prompts(db)

    batches_by_source: dict[SourceType, list[IngestionBatch]] = {}
    for batch in run.batches or []:
        batches_by_source.setdefault(batch.source_type, []).append(batch)

    system_expanded = _expand_markers(
        system_raw,
        source_prompts,
        experiences=experiences or [],
        active_tasks=active_tasks or [],
        batches_by_source=batches_by_source,
    )
    user_prompt = _build_user_prompt(run)
    return system_expanded, user_prompt


def _build_user_prompt(run: IngestionRun) -> str:
    range_start = run.range_start.isoformat() if run.range_start else "unknown"
    range_end = run.range_end.isoformat() if run.range_end else "unknown"
    return (
        f"# Ingestion Run {run.id}\n\n"
        f"Time range: {range_start} → {range_end}\n\n"
        "Review the context and data in your system instructions and propose task changes."
    )


def _build_experiences_section(experiences: list[Experience]) -> str:
    """Render the experiences section so the LLM can attribute tasks to them."""
    lines: list[str] = [
        "\n\n---\n\n## Experiences",
        "",
        "Experiences are long-running contexts (projects, jobs, classes, clubs) that tasks "
        "can be attributed to. When proposing a task, set `proposed_experience_name` to the "
        "**exact name** from the list below if the task clearly belongs to that experience. "
        "Leave it unset if the task is not clearly tied to one experience.",
        "",
    ]

    if not experiences:
        lines.append("*(No active experiences configured.)*")
        return "\n".join(lines)

    for exp in experiences:
        lines.append(f"- `{exp.folder_path}`")

    return "\n".join(lines)


def _build_active_tasks_section(tasks: list[Task]) -> str:
    """Render the active-tasks section that precedes ingestion data."""
    lines: list[str] = [
        "\n\n---\n\n## Current Active Tasks",
        "",
        "The following tasks are currently open (status is not `done` or `cancelled`). "
        "When reviewing the ingestion data, **prefer proposing updates to these "
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
