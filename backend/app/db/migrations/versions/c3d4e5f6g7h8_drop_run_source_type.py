"""drop source_type from ingestion_runs

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-03-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_runs") as batch_op:
        batch_op.drop_column("source_type")


def downgrade() -> None:
    with op.batch_alter_table("ingestion_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_type",
                sa.Enum(
                    "slack",
                    "email",
                    "calendar",
                    "github",
                    "canvas",
                    "mixed",
                    name="sourcetype",
                ),
                nullable=True,
                server_default="mixed",
            )
        )
