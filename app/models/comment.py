from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class Comment(Base, TimestampMixin):
    """User comment on a transaction."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    text: Mapped[str] = mapped_column(Text)

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="comments")
