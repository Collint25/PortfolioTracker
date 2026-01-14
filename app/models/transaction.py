from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Transaction(Base, TimestampMixin):
    """Trade or activity in an account."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    snaptrade_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))

    # Groups multi-leg options trades
    external_reference_id: Mapped[str | None] = mapped_column(String(100), index=True)

    symbol: Mapped[str | None] = mapped_column(String(20), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    settlement_date: Mapped[date | None] = mapped_column(Date)

    type: Mapped[str] = mapped_column(String(50))  # BUY, SELL, DIVIDEND, etc.
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    description: Mapped[str | None] = mapped_column(String(500))

    # Store raw API response for debugging
    _raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="transactions")
