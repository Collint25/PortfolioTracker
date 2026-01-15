"""Add previous_close to positions

Revision ID: c9d5e7f1a3b4
Revises: b8c4d6e9f0a2
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d5e7f1a3b4'
down_revision: Union[str, None] = 'b8c4d6e9f0a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('positions', sa.Column('previous_close', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column('positions', 'previous_close')
