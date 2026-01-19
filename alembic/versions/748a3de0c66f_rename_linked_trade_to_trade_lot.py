"""rename linked_trade to trade_lot

Revision ID: 748a3de0c66f
Revises: ca8253ea5245
Create Date: 2026-01-18 18:47:43.443567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '748a3de0c66f'
down_revision: Union[str, None] = 'ca8253ea5245'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename tables
    op.rename_table('linked_trades', 'trade_lots')
    op.rename_table('linked_trade_legs', 'lot_transactions')

    # Rename columns in trade_lots
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.alter_column('underlying_symbol', new_column_name='symbol')

    # Rename columns in lot_transactions
    with op.batch_alter_table('lot_transactions') as batch_op:
        batch_op.alter_column('linked_trade_id', new_column_name='lot_id')

    # Add instrument_type column
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.add_column(sa.Column('instrument_type', sa.String(10), nullable=True))

    # Backfill existing records as OPTIONS
    op.execute("UPDATE trade_lots SET instrument_type = 'OPTION'")

    # Make column non-nullable
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.alter_column('instrument_type', nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.drop_column('instrument_type')
        batch_op.alter_column('symbol', new_column_name='underlying_symbol')

    with op.batch_alter_table('lot_transactions') as batch_op:
        batch_op.alter_column('lot_id', new_column_name='linked_trade_id')

    op.rename_table('trade_lots', 'linked_trades')
    op.rename_table('lot_transactions', 'linked_trade_legs')
