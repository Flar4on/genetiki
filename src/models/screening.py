import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class ResultType(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    repeat_needed = "repeat_needed"


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    baby_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("babies.id"), index=True)
    result_type: Mapped[ResultType] = mapped_column(Enum(ResultType))
    disease_code: Mapped[str | None] = mapped_column(String(20))
    disease_name: Mapped[str | None] = mapped_column(String(255))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    source: Mapped[str | None] = mapped_column(String(100))

    baby = relationship("Baby", back_populates="screening_results")
    notifications = relationship("Notification", back_populates="screening_result", lazy="selectin")
