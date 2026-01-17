from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction

# Association table for many-to-many relationship
trade_group_transactions = Table(
    "trade_group_transactions",
    Base.metadata,
    Column("trade_group_id", Integer, ForeignKey("trade_groups.id"), primary_key=True),
    Column("transaction_id", Integer, ForeignKey("transactions.id"), primary_key=True),
)


class TradeGroup(Base, TimestampMixin):
    """Group of related transactions (multi-leg options, spreads, etc.)."""

    __tablename__ = "trade_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    strategy_type: Mapped[str | None] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        secondary=trade_group_transactions, back_populates="trade_groups"
    )
