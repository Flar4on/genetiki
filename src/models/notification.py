import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    delivered = "delivered"
    confirmed = "confirmed"
    escalated = "escalated"


class Notification(Base):
    __tablename__ = "notifications"

    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"), index=True)
    screening_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("screening_results.id"), index=True
    )
    message_text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.pending
    )

    parent = relationship("Parent", back_populates="notifications")
    screening_result = relationship("ScreeningResult", back_populates="notifications")
