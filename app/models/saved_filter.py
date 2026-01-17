from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SavedFilter(Base, TimestampMixin):
    """Saved filter configuration for quick access."""

    __tablename__ = "saved_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    page: Mapped[str] = mapped_column(String(50), index=True)  # e.g., "transactions"
    filter_json: Mapped[str] = mapped_column(Text)  # JSON string of filter params
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
