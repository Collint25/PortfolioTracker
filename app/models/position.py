from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Position(Base, TimestampMixin):
    """Current holding in an account."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    snaptrade_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))

    symbol: Mapped[str] = mapped_column(String(20), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    average_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Store raw API response for debugging
    _raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="positions")
