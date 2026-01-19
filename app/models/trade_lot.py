from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.lot_transaction import LotTransaction


class TradeLot(Base, TimestampMixin):
    """Tracks a batch of shares/contracts through open -> close lifecycle."""

    __tablename__ = "trade_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    # Instrument type
    instrument_type: Mapped[str] = mapped_column(String(10))  # STOCK, OPTION

    # Symbol (ticker for stocks, underlying for options)
    symbol: Mapped[str] = mapped_column(String(20), index=True)

    @property
    def underlying_symbol(self) -> str:
        """Alias for symbol (backwards compatibility, to be removed in Task 11)."""
        return self.symbol

    # Option-specific (NULL for stocks)
    option_type: Mapped[str | None] = mapped_column(String(10))  # CALL, PUT
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    expiration_date: Mapped[date | None] = mapped_column(Date, index=True)

    # Trade direction: LONG (buy first) or SHORT (sell first)
    direction: Mapped[str] = mapped_column(String(10))

    # Calculated P/L
    realized_pl: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))

    # Status tracking
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    total_opened_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    total_closed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), default=Decimal("0")
    )

    # Auto-match or manual
    is_auto_matched: Mapped[bool] = mapped_column(Boolean, default=True)

    # Optional user notes
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="trade_lots")
    legs: Mapped[list["LotTransaction"]] = relationship(
        back_populates="trade_lot",
        cascade="all, delete-orphan",
        order_by="LotTransaction.trade_date",
    )

    @property
    def contract_display(self) -> str:
        """Format contract for display."""
        if self.instrument_type == "STOCK":
            return self.symbol
        exp_str = self.expiration_date.strftime("%m/%d") if self.expiration_date else ""
        opt_char = "C" if self.option_type == "CALL" else "P"
        return f"{self.symbol} ${self.strike_price:.2f} {exp_str} {opt_char}"

    @property
    def remaining_quantity(self) -> Decimal:
        """Quantity still open (not yet closed)."""
        return self.total_opened_quantity - self.total_closed_quantity
