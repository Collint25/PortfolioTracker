from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SecurityInfo(Base, TimestampMixin):
    """Cached metadata for securities/tickers."""

    __tablename__ = "securities"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    security_type: Mapped[str | None] = mapped_column(String(50))  # STOCK, ETF, OPTION
    exchange: Mapped[str | None] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Store raw API response for debugging
    _raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
