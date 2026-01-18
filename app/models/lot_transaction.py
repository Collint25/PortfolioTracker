from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.trade_lot import TradeLot
    from app.models.transaction import Transaction


class LotTransaction(Base, TimestampMixin):
    """Association between TradeLot and Transaction with quantity allocation."""

    __tablename__ = "lot_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("trade_lots.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"), index=True
    )

    # How many shares/contracts from this transaction allocated to this lot
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))

    # Leg type
    leg_type: Mapped[str] = mapped_column(String(10))  # OPEN or CLOSE

    # Denormalized for display
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    price_per_contract: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    # Relationships
    trade_lot: Mapped["TradeLot"] = relationship(back_populates="legs")
    transaction: Mapped["Transaction"] = relationship(
        back_populates="lot_transactions"
    )

    @property
    def cash_impact(self) -> Decimal:
        """Calculate cash impact for this leg."""
        return self.allocated_quantity * self.price_per_contract * Decimal("100")
