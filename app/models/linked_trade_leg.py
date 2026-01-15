from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.linked_trade import LinkedTrade
    from app.models.transaction import Transaction


class LinkedTradeLeg(Base, TimestampMixin):
    """Association between LinkedTrade and Transaction with quantity allocation."""

    __tablename__ = "linked_trade_legs"

    id: Mapped[int] = mapped_column(primary_key=True)
    linked_trade_id: Mapped[int] = mapped_column(
        ForeignKey("linked_trades.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"), index=True
    )

    # How many contracts from this transaction are allocated to this linked trade
    # Enables partial allocation when one transaction closes multiple opens
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))

    # Leg type for clarity
    leg_type: Mapped[str] = mapped_column(String(10))  # OPEN or CLOSE

    # Denormalized for display (avoids join for list views)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    price_per_contract: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    # Relationships
    linked_trade: Mapped["LinkedTrade"] = relationship(back_populates="legs")
    transaction: Mapped["Transaction"] = relationship(back_populates="linked_trade_legs")

    @property
    def cash_impact(self) -> Decimal:
        """Calculate cash impact for this leg (quantity * price * 100 for options)."""
        # Note: Actual calculation depends on whether this is an open or close
        # and whether the position is long or short
        return self.allocated_quantity * self.price_per_contract * Decimal("100")
