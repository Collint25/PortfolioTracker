"""make option fields nullable for stocks

Revision ID: 931768732c0a
Revises: 748a3de0c66f
Create Date: 2026-01-18 20:56:41.808157

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '931768732c0a'
down_revision: Union[str, None] = '748a3de0c66f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make option-specific columns nullable to support stocks
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.alter_column('option_type', nullable=True)
        batch_op.alter_column('strike_price', nullable=True)
        batch_op.alter_column('expiration_date', nullable=True)


def downgrade() -> None:
    # Revert to non-nullable (only safe if no stocks exist)
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.alter_column('option_type', nullable=False)
        batch_op.alter_column('strike_price', nullable=False)
        batch_op.alter_column('expiration_date', nullable=False)
