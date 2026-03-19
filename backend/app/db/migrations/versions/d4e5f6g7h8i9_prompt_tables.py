"""add prompt, prompt_config, and prompt_config_entry tables; seed from vault

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-18 00:00:00.000000

"""

import os
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Vault prompt keys and their corresponding source_type (None for system)
_PROMPT_SEEDS = [
    ("system", None, "system", "Main system prompt for the task proposal engine"),
    ("sources/github", "github", "source_context", "GitHub source context prompt"),
    ("sources/slack", "slack", "source_context", "Slack source context prompt"),
    ("sources/email", "email", "source_context", "Email (Gmail) source context prompt"),
    ("sources/canvas", "canvas", "source_context", "Canvas source context prompt"),
]


def _read_vault_prompt(key: str) -> str:
    """Read vault/Prompts/{key}.md relative to the repo root.

    Falls back to a placeholder string if the file is missing so the migration
    never hard-fails due to a missing vault file.
    """
    here = os.path.dirname(__file__)
    # versions/ → migrations/ → db/ → app/ → backend/ → repo root
    repo_root = os.path.abspath(os.path.join(here, "..", "..", "..", "..", ".."))
    path = os.path.join(repo_root, "vault", "Prompts", key + ".md")
    if os.path.exists(path):
        with open(path) as fh:
            return fh.read()
    return f"# {key}\n\nTODO: configure this prompt.\n"


def upgrade() -> None:
    # ── Create tables ──────────────────────────────────────────────────────

    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String, nullable=False, unique=True),
        sa.Column(
            "kind",
            sa.Enum("system", "source_context", name="promptkind"),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.Enum("slack", "email", "github", "canvas", name="sourcetype"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "prompt_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=False),
        sa.Column("system_prompt_id", sa.Integer, sa.ForeignKey("prompts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "prompt_config_entries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("config_id", sa.Integer, sa.ForeignKey("prompt_configs.id"), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("slack", "email", "github", "canvas", name="sourcetype"),
            nullable=False,
        ),
        sa.Column("prompt_id", sa.Integer, sa.ForeignKey("prompts.id"), nullable=False),
        sa.UniqueConstraint("config_id", "source_type", name="uq_config_source"),
    )

    # ── Seed prompt rows from vault ────────────────────────────────────────

    now = datetime.utcnow()
    conn = op.get_bind()

    prompts_t = sa.table(
        "prompts",
        sa.column("key", sa.String),
        sa.column("kind", sa.String),
        sa.column("source_type", sa.String),
        sa.column("content", sa.Text),
        sa.column("description", sa.Text),
        sa.column("updated_at", sa.DateTime),
    )

    op.bulk_insert(
        prompts_t,
        [
            {
                "key": key,
                "kind": kind,
                "source_type": source_type,
                "content": _read_vault_prompt(key),
                "description": description,
                "updated_at": now,
            }
            for key, source_type, kind, description in _PROMPT_SEEDS
        ],
    )

    # ── Create default PromptConfig ────────────────────────────────────────

    system_id = conn.execute(sa.text("SELECT id FROM prompts WHERE key = 'system'")).fetchone()[0]

    configs_t = sa.table(
        "prompt_configs",
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("system_prompt_id", sa.Integer),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        configs_t,
        [
            {
                "name": "default",
                "is_active": True,
                "system_prompt_id": system_id,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    config_id = conn.execute(
        sa.text("SELECT id FROM prompt_configs WHERE name = 'default'")
    ).fetchone()[0]

    # ── Create PromptConfigEntry rows ──────────────────────────────────────

    entries_t = sa.table(
        "prompt_config_entries",
        sa.column("config_id", sa.Integer),
        sa.column("source_type", sa.String),
        sa.column("prompt_id", sa.Integer),
    )

    entry_rows = []
    for key, source_type, _kind, _desc in _PROMPT_SEEDS:
        if source_type is None:
            continue
        row = conn.execute(
            sa.text("SELECT id FROM prompts WHERE key = :key"), {"key": key}
        ).fetchone()
        if row:
            entry_rows.append(
                {"config_id": config_id, "source_type": source_type, "prompt_id": row[0]}
            )

    if entry_rows:
        op.bulk_insert(entries_t, entry_rows)


def downgrade() -> None:
    op.drop_table("prompt_config_entries")
    op.drop_table("prompt_configs")
    op.drop_table("prompts")
