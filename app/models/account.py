from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Account(Base, TimestampMixin):
    """Brokerage account synced from SnapTrade."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    snaptrade_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    account_number: Mapped[str] = mapped_column(String(50))
    account_type: Mapped[str | None] = mapped_column(String(50))  # e.g., "TFSA", "RRSP"
    institution_name: Mapped[str] = mapped_column(String(100), default="Fidelity")

    # Store raw API response for debugging
    _raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    positions: Mapped[list["Position"]] = relationship(back_populates="account")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
