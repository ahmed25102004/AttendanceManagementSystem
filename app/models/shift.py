from datetime import time

from sqlalchemy import ForeignKey, Integer, String, Time, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Shift(Base):
    __tablename__ = "shifts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    employees = relationship("Employee", back_populates="shift")
