from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.linked_trade_leg import LinkedTradeLeg


class LinkedTrade(Base, TimestampMixin):
    """Links opening and closing transactions for the same option contract."""

    __tablename__ = "linked_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    # Option contract identifier
    underlying_symbol: Mapped[str] = mapped_column(String(20), index=True)
    option_type: Mapped[str] = mapped_column(String(10))  # CALL, PUT
    strike_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    expiration_date: Mapped[date] = mapped_column(Date, index=True)

    # Trade direction: LONG (BUY_TO_OPEN -> SELL_TO_CLOSE)
    #                  SHORT (SELL_TO_OPEN -> BUY_TO_CLOSE)
    direction: Mapped[str] = mapped_column(String(10))

    # Calculated P/L (sum of all leg amounts)
    realized_pl: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0")
    )

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
    account: Mapped["Account"] = relationship(back_populates="linked_trades")
    legs: Mapped[list["LinkedTradeLeg"]] = relationship(
        back_populates="linked_trade",
        cascade="all, delete-orphan",
        order_by="LinkedTradeLeg.trade_date",
    )

    @property
    def contract_display(self) -> str:
        """Format contract for display: AAPL $150 01/17 CALL"""
        exp_str = self.expiration_date.strftime("%m/%d") if self.expiration_date else ""
        opt_char = "C" if self.option_type == "CALL" else "P"
        return f"{self.underlying_symbol} ${self.strike_price:.2f} {exp_str} {opt_char}"

    @property
    def remaining_quantity(self) -> Decimal:
        """Quantity still open (not yet closed)."""
        return self.total_opened_quantity - self.total_closed_quantity
