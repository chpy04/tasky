"""ingestion refactor

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ingestion_runs") as batch_op:
        batch_op.add_column(sa.Column("range_start", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("range_end", sa.DateTime(), nullable=True))

    with op.batch_alter_table("ingestion_batches") as batch_op:
        batch_op.add_column(sa.Column("item_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("api_calls", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("duration_ms", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("llm_cost", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("found_new_content", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("success", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("connector_metadata", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ingestion_batches") as batch_op:
        batch_op.drop_column("connector_metadata")
        batch_op.drop_column("success")
        batch_op.drop_column("found_new_content")
        batch_op.drop_column("llm_cost")
        batch_op.drop_column("duration_ms")
        batch_op.drop_column("api_calls")
        batch_op.drop_column("item_count")

    with op.batch_alter_table("ingestion_runs") as batch_op:
        batch_op.drop_column("range_end")
        batch_op.drop_column("range_start")
