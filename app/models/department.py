from datetime import time

from sqlalchemy import Integer, String, ForeignKey, Boolean, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attendance_policy: Mapped[str] = mapped_column(String(50), default="default", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Doctors department shift settings
    # Basic shift settings
    shift_start_time: Mapped[time] = mapped_column(Time, default=time(8, 0), nullable=False)
    shift_end_time: Mapped[time] = mapped_column(Time, default=time(15, 0), nullable=False)
    shift_hours: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    
    # Late calculation settings
    late_start_time: Mapped[time] = mapped_column(Time, default=time(8, 30), nullable=False)
    attendance_end_time: Mapped[time] = mapped_column(Time, default=time(11, 0), nullable=False)
    
    # Overtime settings
    overtime_start_time: Mapped[time] = mapped_column(Time, default=time(15, 0), nullable=False)
    
    # Evening shift (optional)
    evening_shift_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    evening_shift_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    evening_shift_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Keep old fields for backward compatibility
    half_shift_start_time: Mapped[time] = mapped_column(Time, default=time(8, 0), nullable=False)
    half_shift_end_time: Mapped[time] = mapped_column(Time, default=time(15, 0), nullable=False)
    half_shift_hours: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    full_shift_start_time: Mapped[time] = mapped_column(Time, default=time(8, 0), nullable=False)
    full_shift_end_time: Mapped[time] = mapped_column(Time, default=time(22, 0), nullable=False)
    full_shift_hours: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    branch = relationship("Branch", back_populates="departments")
    employees = relationship("Employee", back_populates="department")
