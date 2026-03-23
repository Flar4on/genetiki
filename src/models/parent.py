import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Parent(Base):
    __tablename__ = "parents"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(500))  # encrypted
    phone_hash: Mapped[str | None] = mapped_column(String(64), index=True)  # SHA-256 for lookup
    full_name: Mapped[str | None] = mapped_column(String(500))  # encrypted
    region: Mapped[str | None] = mapped_column(String(100))
    registration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # OTP for portal login
    auth_code: Mapped[str | None] = mapped_column(String(6))
    auth_code_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    babies = relationship("Baby", back_populates="parent", lazy="selectin")
    notifications = relationship("Notification", back_populates="parent", lazy="selectin")
