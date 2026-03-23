import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Baby(Base):
    __tablename__ = "babies"

    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parents.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_hospital: Mapped[str | None] = mapped_column(String(255))
    sample_collected: Mapped[bool] = mapped_column(Boolean, default=False)

    parent = relationship("Parent", back_populates="babies")
    screening_results = relationship("ScreeningResult", back_populates="baby", lazy="selectin")
