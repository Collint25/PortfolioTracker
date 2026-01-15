"""Add linked trades

Revision ID: b8c4d6e9f0a2
Revises: a7f3c2d5e8b1
Create Date: 2026-01-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c4d6e9f0a2'
down_revision: Union[str, None] = 'a7f3c2d5e8b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create linked_trades table
    op.create_table(
        'linked_trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('underlying_symbol', sa.String(20), nullable=False),
        sa.Column('option_type', sa.String(10), nullable=False),
        sa.Column('strike_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('realized_pl', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('is_closed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('total_opened_quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('total_closed_quantity', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('is_auto_matched', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
    )
    op.create_index('ix_linked_trades_account_id', 'linked_trades', ['account_id'])
    op.create_index('ix_linked_trades_underlying_symbol', 'linked_trades', ['underlying_symbol'])
    op.create_index('ix_linked_trades_expiration_date', 'linked_trades', ['expiration_date'])
    op.create_index('ix_linked_trades_is_closed', 'linked_trades', ['is_closed'])

    # Create linked_trade_legs table
    op.create_table(
        'linked_trade_legs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('linked_trade_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('allocated_quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('leg_type', sa.String(10), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('price_per_contract', sa.Numeric(18, 4), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['linked_trade_id'], ['linked_trades.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id']),
    )
    op.create_index('ix_linked_trade_legs_linked_trade_id', 'linked_trade_legs', ['linked_trade_id'])
    op.create_index('ix_linked_trade_legs_transaction_id', 'linked_trade_legs', ['transaction_id'])
    op.create_index('ix_linked_trade_legs_trade_date', 'linked_trade_legs', ['trade_date'])


def downgrade() -> None:
    op.drop_index('ix_linked_trade_legs_trade_date', table_name='linked_trade_legs')
    op.drop_index('ix_linked_trade_legs_transaction_id', table_name='linked_trade_legs')
    op.drop_index('ix_linked_trade_legs_linked_trade_id', table_name='linked_trade_legs')
    op.drop_table('linked_trade_legs')

    op.drop_index('ix_linked_trades_is_closed', table_name='linked_trades')
    op.drop_index('ix_linked_trades_expiration_date', table_name='linked_trades')
    op.drop_index('ix_linked_trades_underlying_symbol', table_name='linked_trades')
    op.drop_index('ix_linked_trades_account_id', table_name='linked_trades')
    op.drop_table('linked_trades')
