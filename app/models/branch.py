from sqlalchemy import Boolean, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Branch Settings
    check_in_open_time: Mapped[str] = mapped_column(String(8), default="08:00:00", nullable=False)
    check_in_close_time: Mapped[str] = mapped_column(String(8), default="11:00:00", nullable=False)
    check_out_open_time: Mapped[str] = mapped_column(String(8), default="16:00:00", nullable=False)
    check_out_close_time: Mapped[str] = mapped_column(String(8), default="22:00:00", nullable=False)
    allowed_late_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    departments = relationship("Department", back_populates="branch")
    employees = relationship("Employee", back_populates="branch")
    devices = relationship("Device", back_populates="branch", cascade="all, delete-orphan")
    users = relationship("User", back_populates="branch")
