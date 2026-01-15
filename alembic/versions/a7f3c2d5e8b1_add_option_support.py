"""Add option support

Revision ID: a7f3c2d5e8b1
Revises: 1b71213d8c1a
Create Date: 2026-01-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7f3c2d5e8b1'
down_revision: Union[str, None] = '1b71213d8c1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add option columns to transactions table
    op.add_column('transactions', sa.Column('is_option', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('transactions', sa.Column('option_type', sa.String(length=10), nullable=True))
    op.add_column('transactions', sa.Column('strike_price', sa.Numeric(precision=18, scale=4), nullable=True))
    op.add_column('transactions', sa.Column('expiration_date', sa.Date(), nullable=True))
    op.add_column('transactions', sa.Column('option_ticker', sa.String(length=50), nullable=True))
    op.add_column('transactions', sa.Column('underlying_symbol', sa.String(length=20), nullable=True))
    op.add_column('transactions', sa.Column('option_action', sa.String(length=20), nullable=True))

    # Add indexes for common option queries
    op.create_index(op.f('ix_transactions_is_option'), 'transactions', ['is_option'], unique=False)
    op.create_index(op.f('ix_transactions_option_type'), 'transactions', ['option_type'], unique=False)
    op.create_index(op.f('ix_transactions_expiration_date'), 'transactions', ['expiration_date'], unique=False)
    op.create_index(op.f('ix_transactions_underlying_symbol'), 'transactions', ['underlying_symbol'], unique=False)
    op.create_index(op.f('ix_transactions_option_action'), 'transactions', ['option_action'], unique=False)

    # Add option columns to positions table
    op.add_column('positions', sa.Column('is_option', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('positions', sa.Column('option_type', sa.String(length=10), nullable=True))
    op.add_column('positions', sa.Column('strike_price', sa.Numeric(precision=18, scale=4), nullable=True))
    op.add_column('positions', sa.Column('expiration_date', sa.Date(), nullable=True))
    op.add_column('positions', sa.Column('option_ticker', sa.String(length=50), nullable=True))
    op.add_column('positions', sa.Column('underlying_symbol', sa.String(length=20), nullable=True))

    # Add indexes for common option position queries
    op.create_index(op.f('ix_positions_is_option'), 'positions', ['is_option'], unique=False)
    op.create_index(op.f('ix_positions_underlying_symbol'), 'positions', ['underlying_symbol'], unique=False)
    op.create_index(op.f('ix_positions_expiration_date'), 'positions', ['expiration_date'], unique=False)


def downgrade() -> None:
    # Drop position indexes
    op.drop_index(op.f('ix_positions_expiration_date'), table_name='positions')
    op.drop_index(op.f('ix_positions_underlying_symbol'), table_name='positions')
    op.drop_index(op.f('ix_positions_is_option'), table_name='positions')

    # Drop position columns
    op.drop_column('positions', 'underlying_symbol')
    op.drop_column('positions', 'option_ticker')
    op.drop_column('positions', 'expiration_date')
    op.drop_column('positions', 'strike_price')
    op.drop_column('positions', 'option_type')
    op.drop_column('positions', 'is_option')

    # Drop transaction indexes
    op.drop_index(op.f('ix_transactions_option_action'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_underlying_symbol'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_expiration_date'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_option_type'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_is_option'), table_name='transactions')

    # Drop transaction columns
    op.drop_column('transactions', 'option_action')
    op.drop_column('transactions', 'underlying_symbol')
    op.drop_column('transactions', 'option_ticker')
    op.drop_column('transactions', 'expiration_date')
    op.drop_column('transactions', 'strike_price')
    op.drop_column('transactions', 'option_type')
    op.drop_column('transactions', 'is_option')
