"""drop priority

Revision ID: a1b2c3d4e5f6
Revises: 5675bef00c60
Create Date: 2026-03-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5675bef00c60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.drop_column('priority')

    with op.batch_alter_table('task_proposals') as batch_op:
        batch_op.drop_column('proposed_priority')


def downgrade() -> None:
    with op.batch_alter_table('task_proposals') as batch_op:
        batch_op.add_column(sa.Column(
            'proposed_priority',
            sa.Enum('low', 'medium', 'high', 'urgent', name='taskpriority'),
            nullable=True,
        ))

    with op.batch_alter_table('tasks') as batch_op:
        batch_op.add_column(sa.Column(
            'priority',
            sa.Enum('low', 'medium', 'high', 'urgent', name='taskpriority'),
            nullable=False,
            server_default='medium',
        ))
